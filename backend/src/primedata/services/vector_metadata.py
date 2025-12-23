"""
Vector metadata service for PrimeData.

Manages document and vector metadata for tracking chunk-level information.
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from loguru import logger

from primedata.db.models import DocumentMetadata, VectorMetadata


def create_document_metadata(
    db: Session,
    product_id: UUID,
    version: int,
    chunk_id: str,
    score: Optional[float],
    source_file: Optional[str],
    page_number: Optional[int],
    section: Optional[str],
    field_name: Optional[str],
    extra_tags: Optional[Dict[str, Any]] = None,
) -> DocumentMetadata:
    """
    Create a document metadata record.
    
    Args:
        db: Database session
        product_id: Product ID
        version: Version number
        chunk_id: Chunk identifier
        score: AI Trust Score for chunk
        source_file: Source file name
        page_number: Page number (if applicable)
        section: Section name
        field_name: Field name
        extra_tags: Additional tags as JSON
        
    Returns:
        Created DocumentMetadata instance
    """
    doc_meta = DocumentMetadata(
        product_id=product_id,
        version=version,
        chunk_id=chunk_id,
        score=score,
        source_file=source_file,
        page_number=page_number,
        section=section,
        field_name=field_name,
        extra_tags=extra_tags,
    )
    db.add(doc_meta)
    return doc_meta


def create_vector_metadata(
    db: Session,
    product_id: UUID,
    version: int,
    collection_id: str,
    chunk_id: str,
    page_number: Optional[int],
    section: Optional[str],
    field_name: Optional[str],
    tags: Optional[Dict[str, Any]] = None,
) -> VectorMetadata:
    """
    Create a vector metadata record.
    
    Args:
        db: Database session
        product_id: Product ID
        version: Version number
        collection_id: Qdrant collection name
        chunk_id: Chunk identifier
        page_number: Page number (if applicable)
        section: Section name
        field_name: Field name (for ACL field_scope)
        tags: Tags as JSON
        
    Returns:
        Created VectorMetadata instance
    """
    vec_meta = VectorMetadata(
        product_id=product_id,
        version=version,
        collection_id=collection_id,
        chunk_id=chunk_id,
        page_number=page_number,
        section=section,
        field_name=field_name,
        tags=tags,
    )
    db.add(vec_meta)
    return vec_meta


def get_chunk_metadata(
    db: Session,
    product_id: UUID,
    version: Optional[int] = None,
    section: Optional[str] = None,
    field_name: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[DocumentMetadata]:
    """
    Get chunk metadata for a product with optional filters.
    
    Args:
        db: Database session
        product_id: Product ID
        version: Optional version filter
        section: Optional section filter
        field_name: Optional field name filter
        limit: Maximum number of results
        offset: Offset for pagination
        
    Returns:
        List of DocumentMetadata instances
    """
    query = db.query(DocumentMetadata).filter(DocumentMetadata.product_id == product_id)
    
    if version is not None:
        query = query.filter(DocumentMetadata.version == version)
    
    if section:
        query = query.filter(DocumentMetadata.section == section)
    
    if field_name:
        query = query.filter(DocumentMetadata.field_name == field_name)
    
    return query.order_by(DocumentMetadata.created_at.desc()).limit(limit).offset(offset).all()


def get_vector_metadata_by_chunk(
    db: Session,
    product_id: UUID,
    chunk_id: str,
    version: Optional[int] = None,
) -> Optional[VectorMetadata]:
    """
    Get vector metadata for a specific chunk.
    
    Args:
        db: Database session
        product_id: Product ID
        chunk_id: Chunk identifier
        version: Optional version filter
        
    Returns:
        VectorMetadata instance or None
    """
    query = db.query(VectorMetadata).filter(
        VectorMetadata.product_id == product_id,
        VectorMetadata.chunk_id == chunk_id,
    )
    
    if version is not None:
        query = query.filter(VectorMetadata.version == version)
    
    return query.first()




