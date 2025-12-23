"""
Path helper functions for organizing data in MinIO storage.
"""

from typing import Union
import uuid


def raw_prefix(workspace_id: Union[str, uuid.UUID], product_id: Union[str, uuid.UUID], version: int) -> str:
    """Generate prefix for raw data storage.
    
    Args:
        workspace_id: Workspace identifier
        product_id: Product identifier  
        version: Version number
        
    Returns:
        Storage prefix string like "ws/{ws}/prod/{prod}/v/{version}/raw/"
    """
    return f"ws/{workspace_id}/prod/{product_id}/v/{version}/raw/"


def clean_prefix(workspace_id: Union[str, uuid.UUID], product_id: Union[str, uuid.UUID], version: int) -> str:
    """Generate prefix for cleaned data storage.
    
    Args:
        workspace_id: Workspace identifier
        product_id: Product identifier
        version: Version number
        
    Returns:
        Storage prefix string like "ws/{ws}/prod/{prod}/v/{version}/clean/"
    """
    return f"ws/{workspace_id}/prod/{product_id}/v/{version}/clean/"


def chunk_prefix(workspace_id: Union[str, uuid.UUID], product_id: Union[str, uuid.UUID], version: int) -> str:
    """Generate prefix for chunked data storage.
    
    Args:
        workspace_id: Workspace identifier
        product_id: Product identifier
        version: Version number
        
    Returns:
        Storage prefix string like "ws/{ws}/prod/{prod}/v/{version}/chunk/"
    """
    return f"ws/{workspace_id}/prod/{product_id}/v/{version}/chunk/"


def embed_prefix(workspace_id: Union[str, uuid.UUID], product_id: Union[str, uuid.UUID], version: int) -> str:
    """Generate prefix for embedded data storage.
    
    Args:
        workspace_id: Workspace identifier
        product_id: Product identifier
        version: Version number
        
    Returns:
        Storage prefix string like "ws/{ws}/prod/{prod}/v/{version}/embed/"
    """
    return f"ws/{workspace_id}/prod/{product_id}/v/{version}/embed/"


def export_prefix(workspace_id: Union[str, uuid.UUID], product_id: Union[str, uuid.UUID], version: int) -> str:
    """Generate prefix for exported data storage.
    
    Args:
        workspace_id: Workspace identifier
        product_id: Product identifier
        version: Version number
        
    Returns:
        Storage prefix string like "ws/{ws}/prod/{prod}/v/{version}/export/"
    """
    return f"ws/{workspace_id}/prod/{product_id}/v/{version}/export/"


def safe_filename(filename: str) -> str:
    """Convert filename to safe storage key by removing/replacing unsafe characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename for storage
    """
    import re
    # Replace unsafe characters with underscores
    safe = re.sub(r'[^\w\-_\.]', '_', filename)
    # Remove multiple consecutive underscores
    safe = re.sub(r'_+', '_', safe)
    # Remove leading/trailing underscores
    safe = safe.strip('_')
    return safe or 'unnamed_file'
