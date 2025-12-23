"""
RAG Playground API endpoints for querying product-specific vector data.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import time
import logging

from ..core.security import get_current_user
from ..core.scope import ensure_product_access
from ..core.user_utils import get_user_id
from ..indexing.qdrant_client import QdrantClient
from ..storage.minio_client import MinIOClient
from ..db.database import get_db
from ..db.models import Product

logger = logging.getLogger(__name__)

router = APIRouter()

def get_current_user_from_request(request: Request) -> Dict[str, Any]:
    """Get current user from request state (set by auth middleware)."""
    if not hasattr(request.state, 'user') or not request.state.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return request.state.user

class PlaygroundQuery(BaseModel):
    product_id: str = Field(..., description="Product ID to query")
    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    use: Optional[str] = Field(default="current", description="Use 'current' for current version or 'prod' for production alias")

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
    db = Depends(get_db)
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
        product = ensure_product_access(
            db=db,
            request=request,
            product_id=UUID(query_data.product_id)
        )
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found or access denied"
            )
        
        # Determine which collection to use
        if query_data.use == "prod":
            # Check if product has a promoted version
            if not product.promoted_version:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No production version available. Please promote a version first."
                )
            
            # Use production alias
            from ..indexing.qdrant_client import qdrant_client as qdrant_client_instance
            collection_name = qdrant_client_instance.get_prod_alias_collection(
                workspace_id=str(product.workspace_id),
                product_id=str(product.id)
            )
            
            if not collection_name:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Production alias not found. Please promote a version first."
                )
        else:
            # Use current version (default behavior)
            if product.current_version <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No data available. Please run a pipeline first to index data."
                )
            
            # Construct collection name for current version
            collection_name = f"ws_{product.workspace_id}__prod_{product.id}__v_{product.current_version}"
        
        # Initialize Qdrant client
        qdrant_client = QdrantClient()
        if not qdrant_client.is_connected():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Vector database connection failed"
            )
        
        # Check if collection exists
        collections = qdrant_client.list_collections()
        if collection_name not in collections:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection {collection_name} not found. Please run a pipeline first."
            )
        
        # Generate query embedding
        from ..indexing.embeddings import EmbeddingGenerator
        embedding_generator = EmbeddingGenerator()
        query_embedding = embedding_generator.embed(query_data.query)
        
        # Apply ACL filtering (M5)
        acl_applied = False
        filter_conditions = None
        
        try:
            from ..services.acl import get_acls_for_user, apply_acl_filter, get_allowed_chunk_ids
            from ..db.models import VectorMetadata
            
            # Get user's ACLs for this product
            user_id = get_user_id(current_user)
            user_acls = get_acls_for_user(db, user_id, product.id)
            
            if user_acls:
                # Get all vector metadata for this product
                all_vectors = db.query(VectorMetadata).filter(
                    VectorMetadata.product_id == product.id,
                    VectorMetadata.version == product.current_version
                ).all()
                
                # Apply ACL filter
                allowed_vectors = apply_acl_filter(all_vectors, user_acls)
                allowed_chunk_ids = get_allowed_chunk_ids(allowed_vectors)
                
                if allowed_chunk_ids:
                    # Build Qdrant filter for allowed chunk IDs
                    from qdrant_client.http import models
                    filter_conditions = {
                        "must": [
                            {
                                "key": "chunk_id",
                                "match": {
                                    "any": list(allowed_chunk_ids)
                                }
                            }
                        ]
                    }
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
        
        # Search in Qdrant
        search_results = qdrant_client.search_points(
            collection_name=collection_name,
            query_vector=query_embedding.tolist(),
            limit=query_data.top_k,
            score_threshold=0.0,  # Return all results, let user see scores
            filter_conditions=filter_conditions  # M5: ACL filter
        )
        
        # Initialize MinIO client for presigned URLs
        minio_client = MinIOClient()
        
        # Process results
        results = []
        for result in search_results:
            payload = result.get('payload', {})
            text = payload.get('text', '')
            source_file = payload.get('source_file', '')
            chunk_index = payload.get('chunk_index', 0)
            start_char = payload.get('start_char', 0)
            end_char = payload.get('end_char', 0)
            
            # Generate presigned URL for the source document
            presigned_url = None
            if source_file:
                try:
                    # Extract the file path from the source_file
                    # source_file format: "ws/{workspace_id}/prod/{product_id}/v/{version}/clean/{filename}"
                    presigned_url = minio_client.presign(
                        bucket="primedata-clean",
                        key=source_file,
                        expiry=3600  # 1 hour
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate presigned URL for {source_file}: {e}")
            
            # Create result object
            playground_result = PlaygroundResult(
                text=text,
                score=result.get('score', 0.0),
                doc_path=source_file,
                section=f"Chunk {chunk_index} (chars {start_char}-{end_char})",
                meta={
                    'chunk_index': chunk_index,
                    'start_char': start_char,
                    'end_char': end_char,
                    'source_file': source_file
                },
                presigned_url=presigned_url
            )
            results.append(playground_result)
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        return PlaygroundResponse(
            results=results,
            latency_ms=latency_ms,
            collection_name=collection_name,
            total_results=len(results),
            acl_applied=acl_applied  # M5
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Playground query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}"
        )

@router.get("/api/v1/playground/status/{product_id}")
async def get_playground_status(
    product_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user_from_request),
    db = Depends(get_db)
):
    """
    Get the playground status for a product (whether it's ready for queries).
    """
    try:
        # Ensure user has access to the product
        from uuid import UUID
        product = ensure_product_access(
            db=db,
            request=request,
            product_id=UUID(product_id)
        )
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found or access denied"
            )
        
        # Check if product has a current version
        if product.current_version <= 0:
            return {
                "ready": False,
                "reason": "No data available. Please run a pipeline first to index data.",
                "current_version": product.current_version,
                "promoted_version": product.promoted_version
            }
        
        # Construct collection name
        collection_name = f"ws_{product.workspace_id}__prod_{product.id}__v_{product.current_version}"
        
        # Check if collection exists in Qdrant
        qdrant_client = QdrantClient()
        if not qdrant_client.is_connected():
            return {
                "ready": False,
                "reason": "Vector database connection failed",
                "current_version": product.current_version,
                "promoted_version": product.promoted_version
            }
        
        collections = qdrant_client.list_collections()
        if collection_name not in collections:
            return {
                "ready": False,
                "reason": f"Collection {collection_name} not found. Please run a pipeline first.",
                "current_version": product.current_version,
                "promoted_version": product.promoted_version
            }
        
        # Get collection info
        collection_info = qdrant_client.get_collection_info(collection_name)
        
        return {
            "ready": True,
            "current_version": product.current_version,
            "promoted_version": product.promoted_version,
            "collection_name": collection_name,
            "points_count": collection_info.get('points_count', 0),
            "vectors_count": collection_info.get('vectors_count', 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Playground status check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(e)}"
        )
