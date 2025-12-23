"""
ACL service for PrimeData.

Manages access control lists for fine-grained access control at product, document, and field levels.
"""

from typing import List, Optional, Set
from uuid import UUID
from sqlalchemy.orm import Session
from loguru import logger

from primedata.db.models import ACL, ACLAccessType, VectorMetadata, DocumentMetadata


def create_acl(
    db: Session,
    user_id: UUID,
    product_id: UUID,
    access_type: ACLAccessType,
    index_scope: Optional[str] = None,
    doc_scope: Optional[str] = None,
    field_scope: Optional[str] = None,
) -> ACL:
    """
    Create an ACL entry.
    
    Args:
        db: Database session
        user_id: User ID
        product_id: Product ID
        access_type: Access type (full/index/document/field)
        index_scope: Optional comma-separated index IDs
        doc_scope: Optional comma-separated document IDs
        field_scope: Optional comma-separated field names
        
    Returns:
        Created ACL instance
    """
    acl = ACL(
        user_id=user_id,
        product_id=product_id,
        access_type=access_type,
        index_scope=index_scope,
        doc_scope=doc_scope,
        field_scope=field_scope,
    )
    db.add(acl)
    db.commit()
    db.refresh(acl)
    logger.info(f"Created ACL: user={user_id}, product={product_id}, type={access_type}")
    return acl


def get_acls_for_user(
    db: Session,
    user_id: UUID,
    product_id: Optional[UUID] = None,
) -> List[ACL]:
    """
    Get ACLs for a user, optionally filtered by product.
    
    Args:
        db: Database session
        user_id: User ID
        product_id: Optional product ID filter
        
    Returns:
        List of ACL instances
    """
    query = db.query(ACL).filter(ACL.user_id == user_id)
    if product_id:
        query = query.filter(ACL.product_id == product_id)
    return query.all()


def get_acls_for_product(
    db: Session,
    product_id: UUID,
    user_id: Optional[UUID] = None,
) -> List[ACL]:
    """
    Get ACLs for a product, optionally filtered by user.
    
    Args:
        db: Database session
        product_id: Product ID
        user_id: Optional user ID filter
        
    Returns:
        List of ACL instances
    """
    query = db.query(ACL).filter(ACL.product_id == product_id)
    if user_id:
        query = query.filter(ACL.user_id == user_id)
    return query.all()


def delete_acls(
    db: Session,
    acl_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    product_id: Optional[UUID] = None,
) -> int:
    """
    Delete ACLs matching the given criteria.
    
    Args:
        db: Database session
        acl_id: Optional specific ACL ID
        user_id: Optional user ID filter
        product_id: Optional product ID filter
        
    Returns:
        Number of deleted ACLs
    """
    query = db.query(ACL)
    
    if acl_id:
        query = query.filter(ACL.id == acl_id)
    if user_id:
        query = query.filter(ACL.user_id == user_id)
    if product_id:
        query = query.filter(ACL.product_id == product_id)
    
    count = query.delete(synchronize_session=False)
    db.commit()
    logger.info(f"Deleted {count} ACLs: acl_id={acl_id}, user_id={user_id}, product_id={product_id}")
    return count


def apply_acl_filter(
    all_vectors: List[VectorMetadata],
    user_acls: List[ACL],
) -> List[VectorMetadata]:
    """
    Filter vector metadata based on user ACLs.
    
    Args:
        all_vectors: All vector metadata for a product
        user_acls: User's ACLs for the product
        
    Returns:
        Filtered list of vector metadata
    """
    if not user_acls:
        return []
    
    allowed = []
    allowed_chunk_ids: Set[str] = set()
    
    for v in all_vectors:
        for acl in user_acls:
            # Full access - allow everything
            if acl.access_type == ACLAccessType.FULL:
                allowed.append(v)
                allowed_chunk_ids.add(v.chunk_id)
                break
            
            # Index scope - match by product_id (index_scope is product_id in AIRD)
            if acl.access_type == ACLAccessType.INDEX:
                if acl.index_scope:
                    # index_scope can be comma-separated product IDs
                    scope_ids = [s.strip() for s in acl.index_scope.split(",")]
                    if str(v.product_id) in scope_ids:
                        allowed.append(v)
                        allowed_chunk_ids.add(v.chunk_id)
                        break
            
            # Document scope - match by document_id (from doc_scope)
            if acl.access_type == ACLAccessType.DOCUMENT:
                if acl.doc_scope:
                    # doc_scope is comma-separated document IDs
                    # We need to match against document_id from vector metadata
                    # For now, we'll use source_file or section as a proxy
                    # In practice, this should match against a document_id field
                    scope_docs = [s.strip() for s in acl.doc_scope.split(",")]
                    # Check if any scope doc matches (would need document_id in VectorMetadata)
                    # For now, skip document-level filtering if not available
                    pass
            
            # Field scope - match by field_name
            if acl.access_type == ACLAccessType.FIELD:
                if acl.field_scope and v.field_name:
                    scope_fields = [s.strip().lower() for s in acl.field_scope.split(",")]
                    field_lower = v.field_name.strip().lower()
                    if any(scope_field in field_lower or field_lower in scope_field for scope_field in scope_fields):
                        allowed.append(v)
                        allowed_chunk_ids.add(v.chunk_id)
                        break
    
    # Remove duplicates
    seen = set()
    unique_allowed = []
    for v in allowed:
        if v.chunk_id not in seen:
            seen.add(v.chunk_id)
            unique_allowed.append(v)
    
    return unique_allowed


def get_allowed_chunk_ids(vectors: List[VectorMetadata]) -> Set[str]:
    """
    Extract allowed chunk IDs from vector metadata.
    
    Args:
        vectors: List of vector metadata
        
    Returns:
        Set of chunk IDs
    """
    return {v.chunk_id for v in vectors}




