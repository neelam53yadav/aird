"""
RAG Playground API endpoints for querying product-specific vector data.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..core.scope import ensure_product_access
from ..core.security import get_current_user
from ..core.user_utils import get_user_id
from ..db.database import get_db
from ..db.models import Product
from ..indexing.qdrant_client import QdrantClient
from ..storage.minio_client import MinIOClient

logger = logging.getLogger(__name__)

router = APIRouter()


def get_current_user_from_request(request: Request) -> Dict[str, Any]:
    """Get current user from request state (set by auth middleware)."""
    if not hasattr(request.state, "user") or not request.state.user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return request.state.user


class PlaygroundQuery(BaseModel):
    product_id: str = Field(..., description="Product ID to query")
    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    use: Optional[str] = Field(
        default="current", description="Use 'current' for current version or 'prod' for production alias"
    )


class PlaygroundResult(BaseModel):
    text: str = Field(..., description="Chunk text content")
    score: float = Field(..., description="Similarity score")
    doc_path: str = Field(..., description="Source document path")
    section: Optional[str] = Field(None, description="Document section")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    presigned_url: Optional[str] = Field(None, description="Presigned URL for document access")


class PlaygroundResponse(BaseModel):
    results: List[PlaygroundResult] = Field(..., description="Search results")
    latency_ms: float = Field(..., description="Query latency in milliseconds")
    collection_name: str = Field(..., description="Qdrant collection name used")
    total_results: int = Field(..., description="Total number of results found")
    acl_applied: bool = Field(default=False, description="Whether ACL filtering was applied (M5)")


@router.post("/api/v1/playground/query", response_model=PlaygroundResponse)
async def query_playground(
    query_data: PlaygroundQuery,
    request: Request,
    current_user: dict = Depends(get_current_user_from_request),
    db=Depends(get_db),
):
    """
    Query the RAG playground for a specific product.

    This endpoint performs semantic search on the product's vector data
    and returns the most relevant chunks with metadata and presigned URLs.
    """
    start_time = time.time()

    try:
        # Ensure user has access to the product
        from uuid import UUID

        product = ensure_product_access(db=db, request=request, product_id=UUID(query_data.product_id))

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or access denied")

        # Initialize Qdrant client first
        qdrant_client = QdrantClient()
        if not qdrant_client.is_connected():
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Vector database connection failed")

        # Determine which collection to use and which version
        version_to_use = None
        if query_data.use == "prod":
            # Check if product has a promoted version
            if not product.promoted_version:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No production version available. Please promote a version first.",
                )

            version_to_use = product.promoted_version

            # Use production alias
            collection_name = qdrant_client.get_prod_alias_collection(
                workspace_id=str(product.workspace_id), product_id=str(product.id), product_name=product.name
            )

            if not collection_name:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Production alias not found. Please promote a version first."
                )
        else:
            # Use current version (default behavior)
            if product.current_version <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No data available. Please run a pipeline first to index data.",
                )

            version_to_use = product.current_version

            # Find collection name (checks both product name and product_id formats for backward compatibility)
            collection_name = qdrant_client.find_collection_name(
                workspace_id=str(product.workspace_id),
                product_id=str(product.id),
                version=product.current_version,
                product_name=product.name,
            )

            if not collection_name:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=f"Collection not found. Please run a pipeline first."
                )

        # Generate query embedding using the product's embedding configuration
        from ..indexing.embeddings import EmbeddingGenerator

        # Get embedding configuration from product
        embedding_config = product.embedding_config or {}
        model_name = embedding_config.get("embedder_name", "minilm")
        dimension = embedding_config.get("embedding_dimension", 384)

        logger.info(f"Generating query embedding for product {product.id} using model {model_name} with dimension {dimension}")

        # Initialize embedding generator with product's config and workspace context for API keys
        embedding_generator = EmbeddingGenerator(
            model_name=model_name, dimension=dimension, workspace_id=product.workspace_id, db=db
        )

        # Check which model is actually being used
        model_info = embedding_generator.get_model_info()
        logger.info(f"Query embedding model info: {model_info}")

        if model_info.get("fallback_mode"):
            logger.warning(f"⚠️ CRITICAL: Query embedding is using hash-based fallback! Search results will be poor.")
            logger.warning(
                f"Model: {model_name}, is_openai: {model_info.get('is_openai')}, fallback_mode: {model_info.get('fallback_mode')}"
            )
        else:
            logger.info(f"✅ Query embedding using {model_info.get('model_type')} model (not fallback)")

        query_embedding = embedding_generator.embed(query_data.query)
        logger.info(f"Generated query embedding with dimension {len(query_embedding)}")

        # Apply ACL filtering (M5) - using Qdrant as single source of truth
        acl_applied = False
        filter_conditions = None

        try:
            from ..services.acl import apply_acl_filter_to_payloads, get_acls_for_user, get_allowed_chunk_ids_from_payloads

            # Get user's ACLs for this product
            user_id = get_user_id(current_user)
            user_acls = get_acls_for_user(db, user_id, product.id)

            if user_acls:
                # Get all points from Qdrant for this product/version (using scroll API)
                # Filter by product_id and version in Qdrant
                qdrant_filter = {
                    "product_id": str(product.id),
                    "version": product.current_version,
                }

                # Scroll through all points to get chunk metadata
                all_points = []
                offset = None
                scroll_limit = 1000  # Process in batches

                while True:
                    scroll_result = qdrant_client.scroll_points(
                        collection_name=collection_name,
                        limit=scroll_limit,
                        offset=offset,
                        filter_conditions=qdrant_filter,
                        with_payload=True,
                        with_vector=False,
                    )

                    points = scroll_result.get("points", [])
                    all_points.extend(points)

                    offset = scroll_result.get("next_page_offset")
                    if not offset or len(points) < scroll_limit:
                        break

                logger.info(f"Retrieved {len(all_points)} points from Qdrant for ACL filtering")

                # Apply ACL filter to Qdrant payloads
                allowed_payloads = apply_acl_filter_to_payloads(all_points, user_acls, product.id)
                allowed_chunk_ids = get_allowed_chunk_ids_from_payloads(allowed_payloads)

                if allowed_chunk_ids:
                    # Build Qdrant filter for allowed chunk IDs
                    filter_conditions = {"chunk_id": list(allowed_chunk_ids)}
                    acl_applied = True
                    logger.info(f"ACL filtering applied: {len(allowed_chunk_ids)} chunks allowed")
                else:
                    # No chunks allowed - return empty results
                    logger.warning(f"ACL filtering: no chunks allowed for user {user_id}")
                    return PlaygroundResponse(
                        results=[],
                        latency_ms=(time.time() - start_time) * 1000,
                        collection_name=collection_name,
                        total_results=0,
                    )
        except Exception as e:
            logger.warning(f"ACL filtering failed, proceeding without filter: {e}", exc_info=True)
            # Continue without ACL filtering if there's an error

        # Verify collection info matches query embedding dimension
        collection_info = qdrant_client.get_collection_info(collection_name)
        if collection_info:
            stored_dimension = collection_info.get("config", {}).get("params", {}).get("vectors", {}).get("size")
            query_dimension = len(query_embedding)
            logger.info(
                f"Collection: {collection_name}, Stored dimension: {stored_dimension}, Query dimension: {query_dimension}"
            )
            if stored_dimension and stored_dimension != query_dimension:
                logger.error(f"⚠️ DIMENSION MISMATCH! Stored vectors: {stored_dimension}, Query embedding: {query_dimension}")
                logger.error(f"This will cause poor search results. Verify both use the same embedding model.")
            else:
                logger.info(f"✅ Dimensions match: {query_dimension}")
        else:
            logger.warning(f"Could not get collection info for {collection_name}")

        # Search in Qdrant
        logger.info(f"Searching collection {collection_name} with query: '{query_data.query[:50]}...'")
        search_results = qdrant_client.search_points(
            collection_name=collection_name,
            query_vector=query_embedding.tolist(),
            limit=query_data.top_k,
            score_threshold=0.0,  # Return all results, let user see scores
            filter_conditions=filter_conditions,  # M5: ACL filter
        )
        logger.info(f"Found {len(search_results)} search results")

        # Initialize MinIO client for presigned URLs
        minio_client = MinIOClient()

        # Process results
        results = []
        for result in search_results:
            payload = result.get("payload", {})
            text = payload.get("text", "")
            filename = payload.get("filename", "")  # Use filename from payload
            source_file = payload.get("source_file", filename)  # Fallback to filename
            chunk_index = payload.get("chunk_index", 0)
            chunk_id = payload.get("chunk_id", "")
            page = payload.get("page", 0)
            section = payload.get("section", "general")
            token_est = payload.get("token_est", 0)
            text_length = payload.get("text_length", len(text))

            # If text was truncated, note it in metadata
            is_truncated = text_length > len(text)

            # Generate presigned URL for the source document
            presigned_url = None
            if filename or source_file:
                try:
                    # Use clean_prefix helper to ensure correct path format
                    from primedata.storage.paths import clean_prefix

                    file_to_use = source_file if source_file else filename
                    if not file_to_use.startswith("ws/"):
                        # Construct path using clean_prefix helper: "ws/{ws}/prod/{prod}/v/{version}/clean/{filename}"
                        clean_path_prefix = clean_prefix(
                            workspace_id=product.workspace_id, product_id=product.id, version=version_to_use
                        )
                        file_to_use = f"{clean_path_prefix}{file_to_use}"

                    logger.debug(f"Generating presigned URL for: bucket=primedata-clean, key={file_to_use}")
                    presigned_url = minio_client.presign(
                        bucket="primedata-clean",
                        key=file_to_use,
                        expiry=3600,  # 1 hour
                        inline=True,  # Display in browser instead of downloading
                    )
                    if presigned_url:
                        logger.debug(f"Successfully generated presigned URL for {file_to_use}")
                    else:
                        logger.warning(f"Failed to generate presigned URL (returned None) for {file_to_use}")
                except Exception as e:
                    logger.warning(
                        f"Failed to generate presigned URL for {file_to_use if 'file_to_use' in locals() else filename}: {e}",
                        exc_info=True,
                    )

            # Create section label with better information
            section_label = f"{section}"
            if page:
                section_label += f" (Page {page})"
            if token_est:
                section_label += f" - {token_est} tokens"

            # Create result object
            playground_result = PlaygroundResult(
                text=text,
                score=result.get("score", 0.0),
                doc_path=filename or source_file,
                section=section_label,
                meta={
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                    "filename": filename,
                    "source_file": source_file,
                    "page": page,
                    "section": section,
                    "token_est": token_est,
                    "text_length": text_length,
                    "is_truncated": is_truncated,
                },
                presigned_url=presigned_url,
            )
            results.append(playground_result)

        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        return PlaygroundResponse(
            results=results,
            latency_ms=latency_ms,
            collection_name=collection_name,
            total_results=len(results),
            acl_applied=acl_applied,  # M5
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Playground query failed: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Query failed: {str(e)}")


@router.get("/api/v1/playground/status/{product_id}")
async def get_playground_status(
    product_id: str, request: Request, current_user: dict = Depends(get_current_user_from_request), db=Depends(get_db)
):
    """
    Get the playground status for a product (whether it's ready for queries).
    """
    try:
        # Ensure user has access to the product
        from uuid import UUID

        product = ensure_product_access(db=db, request=request, product_id=UUID(product_id))

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or access denied")

        # Check if product has a current version
        if product.current_version <= 0:
            return {
                "ready": False,
                "reason": "No data available. Please run a pipeline first to index data.",
                "current_version": product.current_version,
                "promoted_version": product.promoted_version,
            }

        # Check if collection exists in Qdrant
        qdrant_client = QdrantClient()
        if not qdrant_client.is_connected():
            return {
                "ready": False,
                "reason": "Vector database connection failed",
                "current_version": product.current_version,
                "promoted_version": product.promoted_version,
            }

        # Find collection name (checks both product name and product_id formats for backward compatibility)
        collection_name = qdrant_client.find_collection_name(
            workspace_id=str(product.workspace_id),
            product_id=str(product.id),
            version=product.current_version,
            product_name=product.name,
        )

        if not collection_name:
            return {
                "ready": False,
                "reason": f"Collection not found. Please run a pipeline first.",
                "current_version": product.current_version,
                "promoted_version": product.promoted_version,
            }

        # Get collection info
        collection_info = qdrant_client.get_collection_info(collection_name)

        return {
            "ready": True,
            "current_version": product.current_version,
            "promoted_version": product.promoted_version,
            "collection_name": collection_name,
            "points_count": collection_info.get("points_count", 0),
            "vectors_count": collection_info.get("vectors_count", 0),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Playground status check failed: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Status check failed: {str(e)}")
