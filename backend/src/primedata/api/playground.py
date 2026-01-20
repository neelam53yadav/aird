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
    compat_mode: Optional[bool] = Field(
        default=False,
        description="If true, allow dimension mismatch and use collection's embedding model (for debugging)"
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

        # Get embedding configuration for the specific version being queried
        # Priority: PipelineRun metrics > Collection dimension > Product config (with validation)
        from ..indexing.embeddings import EmbeddingGenerator
        from ..db.models import PipelineRun
        
        # Try to get embedding_config from PipelineRun for this version
        version_embedding_config = None
        pipeline_run = None
        if version_to_use:
            pipeline_run = db.query(PipelineRun).filter(
                PipelineRun.product_id == product.id,
                PipelineRun.version == version_to_use
            ).first()
            
            if pipeline_run and pipeline_run.metrics:
                # Check if embedding_config is stored in metrics
                indexing_stage = pipeline_run.metrics.get("aird_stages", {}).get("indexing", {})
                if indexing_stage:
                    # Try to get from stage metrics
                    embedding_model = indexing_stage.get("metrics", {}).get("embedding_model")
                    if embedding_model:
                        # We have the model name, need to get dimension
                        from ..core.embedding_config import get_embedding_model_config
                        model_config = get_embedding_model_config(embedding_model)
                        if model_config:
                            version_embedding_config = {
                                "embedder_name": embedding_model,
                                "embedding_dimension": model_config.dimension
                            }
                            logger.info(
                                f"Found embedding config from PipelineRun v{version_to_use}: "
                                f"{version_embedding_config['embedder_name']} ({version_embedding_config['embedding_dimension']} dims)"
                            )
        
        # Get collection info to determine actual dimension (source of truth)
        collection_info = qdrant_client.get_collection_info(collection_name)
        if not collection_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection {collection_name} not found or could not be accessed."
            )
        
        # Get the actual dimension from the collection (source of truth)
        # get_collection_info returns: {"config": {"vector_size": 1024, "distance": "Cosine"}}
        stored_dimension = collection_info.get("config", {}).get("vector_size")
        if not stored_dimension:
            # Fallback: try alternative paths (for backward compatibility)
            stored_dimension = collection_info.get("config", {}).get("params", {}).get("vectors", {}).get("size")
        
        if not stored_dimension:
            # Last resort: try top-level vector_size (shouldn't happen but be safe)
            stored_dimension = collection_info.get("vector_size")
        
        if not stored_dimension:
            # Log the actual structure for debugging
            logger.error(f"Collection info structure: {collection_info}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not determine vector dimension for collection {collection_name}. Collection info keys: {list(collection_info.keys()) if collection_info else 'None'}"
            )
        
        logger.info(f"Collection {collection_name} uses dimension {stored_dimension}")
        
        # Get current product embedding config (for comparison)
        product_embedding_config = product.embedding_config or {}
        product_model_name = product_embedding_config.get("embedder_name", "minilm")
        product_dimension = product_embedding_config.get("embedding_dimension", 384)
        
        # Determine which embedding config to use
        use_version_config = False
        embedding_config_to_use = None
        
        if version_embedding_config:
            # We have version-specific config - validate it matches collection
            version_dimension = version_embedding_config.get("embedding_dimension")
            if version_dimension == stored_dimension:
                # Perfect match - use version config
                embedding_config_to_use = version_embedding_config
                use_version_config = True
                logger.info(
                    f"✅ Using embedding config from PipelineRun v{version_to_use}: "
                    f"{embedding_config_to_use['embedder_name']} (matches collection dimension {stored_dimension})"
                )
            else:
                logger.warning(
                    f"⚠️ Version embedding config dimension ({version_dimension}) doesn't match collection ({stored_dimension}). "
                    f"Will use collection dimension to determine model."
                )
        
        # If we don't have version config or it doesn't match, determine from collection dimension
        if not embedding_config_to_use:
            # Map dimension to model (fallback - not ideal but necessary for backward compatibility)
            dimension_to_model = {
                384: "minilm",
                768: "mpnet",
                1024: "e5-large",
            }
            
            model_name = dimension_to_model.get(stored_dimension)
            
            if not model_name:
                # Unknown dimension - try to find matching model from registry
                logger.warning(f"Dimension {stored_dimension} not in standard mapping. Searching registry...")
                from ..core.embedding_config import EmbeddingModelRegistry
                matching_model = None
                for model_id, model_config in EmbeddingModelRegistry.MODELS.items():
                    if model_config.dimension == stored_dimension:
                        matching_model = model_id
                        break
                
                if matching_model:
                    model_name = matching_model
                    logger.info(f"Found matching model for dimension {stored_dimension}: {model_name}")
                else:
                    # No matching model found
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Collection '{collection_name}' uses dimension {stored_dimension}, "
                            f"but no matching embedding model found. "
                            f"Product is configured for {product_model_name} (dimension {product_dimension}). "
                            f"Please re-index the collection with a supported embedding model."
                        )
                    )
            
            embedding_config_to_use = {
                "embedder_name": model_name,
                "embedding_dimension": stored_dimension
            }
            logger.info(
                f"Using dimension-based model lookup: {model_name} (dimension {stored_dimension}) "
                f"to match collection {collection_name}"
            )
        
        # STRICT MODE: Check if product config differs from collection config
        # This prevents silent mismatches
        compat_mode = query_data.compat_mode or (query_data.use == "current")  # Allow compat mode for current version queries
        strict_mode = query_data.use == "prod" and not query_data.compat_mode  # Strict mode for production queries
        
        if strict_mode and not use_version_config:
            # Production queries should use the exact config that was used to index
            if product_dimension != stored_dimension:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Configuration mismatch: Production collection (v{version_to_use}) was indexed with "
                        f"dimension {stored_dimension} ({embedding_config_to_use['embedder_name']}), "
                        f"but product is currently configured for dimension {product_dimension} ({product_model_name}). "
                        f"To fix: Either re-index and promote a new version with the current configuration, "
                        f"or update the product configuration to match the production collection. "
                        f"Query will use {embedding_config_to_use['embedder_name']} to match the collection."
                    )
                )
        elif product_dimension != stored_dimension:
            # Log warning but allow (compat mode for current version)
            logger.warning(
                f"⚠️ Dimension mismatch: Collection uses {stored_dimension} ({embedding_config_to_use['embedder_name']}), "
                f"but product config specifies {product_dimension} ({product_model_name}). "
                f"Using collection's dimension for query compatibility."
            )
        
        # Generate query embedding using the determined config
        model_name = embedding_config_to_use["embedder_name"]
        dimension = embedding_config_to_use["embedding_dimension"]
        
        logger.info(
            f"Generating query embedding using model {model_name} with dimension {dimension} "
            f"to match collection {collection_name}"
        )
        
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
        query_dimension = len(query_embedding)
        logger.info(f"Generated query embedding with dimension {query_dimension}")
        
        # Final validation - should always match now
        if query_dimension != stored_dimension:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Embedding dimension mismatch: Generated query embedding has dimension {query_dimension}, "
                    f"but collection requires {stored_dimension}. This should not happen - please report this error."
                )
            )
        
        logger.info(f"✅ Query embedding dimension ({query_dimension}) matches collection dimension ({stored_dimension})")

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

        # Note: Dimension validation is already done above before generating the embedding
        # This section is kept for backward compatibility but should not be needed
        # since we validate dimensions upfront and ensure they match

        # Search in Qdrant
        logger.info(f"Searching collection {collection_name} with query: '{query_data.query[:50]}...'")
        try:
            search_results = qdrant_client.search_points(
                collection_name=collection_name,
                query_vector=query_embedding.tolist(),
                limit=query_data.top_k,
                score_threshold=0.0,  # Return all results, let user see scores
                filter_conditions=filter_conditions,  # M5: ACL filter
            )
            logger.info(f"Found {len(search_results)} search results")
        except ConnectionError as e:
            logger.error(f"Qdrant connection error during search: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Vector database connection failed: {str(e)}"
            )
        except RuntimeError as e:
            logger.error(f"Search operation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Search failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Search operation failed: {str(e)}"
            )

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

        # If find_collection_name didn't find it, try to get collection info directly
        # This handles cases where list_collections() might not be up-to-date
        if not collection_name:
            # Try both naming formats directly
            if product.name:
                sanitized_name = qdrant_client._sanitize_collection_name(product.name)
                collection_name_candidate = f"ws_{product.workspace_id}__{sanitized_name}__v_{product.current_version}"
                # Try to get collection info directly - if it exists, this will succeed
                collection_info = qdrant_client.get_collection_info(collection_name_candidate)
                if collection_info and collection_info.get("points_count", 0) > 0:
                    collection_name = collection_name_candidate
            
            # If still not found, try product_id format
            if not collection_name:
                collection_name_candidate = f"ws_{product.workspace_id}__prod_{product.id}__v_{product.current_version}"
                collection_info = qdrant_client.get_collection_info(collection_name_candidate)
                if collection_info and collection_info.get("points_count", 0) > 0:
                    collection_name = collection_name_candidate

        if not collection_name:
            return {
                "ready": False,
                "reason": f"Collection not found. Please run a pipeline first.",
                "current_version": product.current_version,
                "promoted_version": product.promoted_version,
            }

        # Get collection info
        collection_info = qdrant_client.get_collection_info(collection_name)
        
        # Handle case where collection_info is None (e.g., version mismatch or collection doesn't exist)
        if collection_info is None:
            logger.warning(f"Could not retrieve collection info for {collection_name}. This may indicate a Qdrant version mismatch.")
            return {
                "ready": False,
                "current_version": product.current_version,
                "promoted_version": product.promoted_version,
                "collection_name": collection_name,
                "points_count": 0,
                "vectors_count": 0,
                "reason": "Could not retrieve collection information. Check Qdrant server and client version compatibility.",
            }

        # Check if collection has any points
        points_count = collection_info.get("points_count", 0)
        if points_count == 0:
            return {
                "ready": False,
                "reason": "Collection exists but has no indexed data. Please run a pipeline first.",
                "current_version": product.current_version,
                "promoted_version": product.promoted_version,
                "collection_name": collection_name,
                "points_count": 0,
                "vectors_count": 0,
            }

        return {
            "ready": True,
            "current_version": product.current_version,
            "promoted_version": product.promoted_version,
            "collection_name": collection_name,
            "points_count": points_count,
            "vectors_count": collection_info.get("vectors_count", 0),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Playground status check failed: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Status check failed: {str(e)}")
