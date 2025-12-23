"""
Workspace access control and scoping utilities.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session
from primedata.db.models import Workspace, Product, WorkspaceMember, WorkspaceRole


def allowed_workspaces(request: Request) -> List[UUID]:
    """
    Get list of workspace IDs that the current user has access to.
    
    Args:
        request: FastAPI request object with user state
        
    Returns:
        List of workspace UUIDs the user can access
    """
    if not hasattr(request.state, 'user') or not request.state.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    user_workspaces = request.state.user.get('workspaces', [])
    # Handle both string and UUID workspace IDs
    result = []
    for ws_id in user_workspaces:
        if isinstance(ws_id, str):
            try:
                result.append(UUID(ws_id))
            except ValueError:
                # Skip invalid UUID strings
                continue
        elif isinstance(ws_id, UUID):
            result.append(ws_id)
    return result


def ensure_workspace_access(
    db: Session, 
    request: Request, 
    workspace_id: UUID, 
    roles: Optional[List[str]] = None
) -> Workspace:
    """
    Ensure the current user has access to the specified workspace.
    
    Args:
        db: Database session
        request: FastAPI request object with user state
        workspace_id: UUID of the workspace to check access for
        roles: Optional list of required roles (if None, any role is sufficient)
        
    Returns:
        Workspace object if access is granted
        
    Raises:
        HTTPException: 403 if access is denied, 404 if workspace not found
    """
    if not hasattr(request.state, 'user') or not request.state.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    user_id = UUID(request.state.user['sub'])
    allowed_workspace_ids = allowed_workspaces(request)
    
    # Check if workspace is in allowed list
    if workspace_id not in allowed_workspace_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace"
        )
    
    # Get workspace
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        # Auto-create workspace if DISABLE_AUTH is enabled (development mode)
        from primedata.core.settings import get_settings
        settings = get_settings()
        if settings.DISABLE_AUTH:
            # Create the workspace
            workspace = Workspace(
                id=workspace_id,
                name="Default Workspace"
            )
            db.add(workspace)
            # Also create workspace membership for the user
            from primedata.db.models import WorkspaceMember, WorkspaceRole
            membership = WorkspaceMember(
                workspace_id=workspace_id,
                user_id=user_id,
                role=WorkspaceRole.OWNER
            )
            db.add(membership)
            db.commit()
            db.refresh(workspace)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
    
    # If specific roles are required, check user's role in this workspace
    if roles:
        membership = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id
        ).first()
        
        if not membership or membership.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role not found. Required: {roles}"
            )
    
    return workspace


def ensure_product_access(db: Session, request: Request, product_id: UUID) -> Product:
    """
    Ensure the current user has access to the specified product.
    
    Args:
        db: Database session
        request: FastAPI request object with user state
        product_id: UUID of the product to check access for
        
    Returns:
        Product object if access is granted
        
    Raises:
        HTTPException: 403 if access is denied, 404 if product not found
    """
    if not hasattr(request.state, 'user') or not request.state.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    
    # Get the product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check workspace access
    ensure_workspace_access(db, request, product.workspace_id)
    
    return product
