"""
User utility functions for handling user ID extraction in dev/prod modes.
"""

from typing import Dict, Any, Optional
from uuid import UUID
from .settings import get_settings


def get_user_id(current_user: Optional[Dict[str, Any]] = None) -> UUID:
    """
    Get the current user ID, using dev user if configured, otherwise from authenticated user.
    
    Args:
        current_user: Current user dictionary from authentication (may be None)
        
    Returns:
        UUID of the user ID
        
    Raises:
        ValueError: If user ID cannot be determined in production mode
    """
    settings = get_settings()
    
    # If dev mode is enabled, use the default dev user ID
    if settings.USE_DEV_USER:
        try:
            return UUID(settings.DEV_USER_ID)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid DEV_USER_ID in settings: {settings.DEV_USER_ID}") from e
    
    # Production mode: extract from authenticated user
    if not current_user:
        raise ValueError("No authenticated user available and USE_DEV_USER is False")
    
    # Try 'sub' first (JWT standard), then 'id' as fallback
    user_id_str = current_user.get("sub") or current_user.get("id")
    
    if not user_id_str:
        raise ValueError("User ID not found in current_user (neither 'sub' nor 'id' present)")
    
    try:
        return UUID(user_id_str)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid user ID format: {user_id_str}") from e


def get_user_id_safe(current_user: Optional[Dict[str, Any]] = None) -> Optional[UUID]:
    """
    Get the current user ID safely, returning None if not available.
    Useful for optional user tracking.
    
    Args:
        current_user: Current user dictionary from authentication (may be None)
        
    Returns:
        UUID of the user ID, or None if not available
    """
    try:
        return get_user_id(current_user)
    except (ValueError, TypeError):
        return None

