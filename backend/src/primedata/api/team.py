"""
Team/Workspace Members API endpoints for PrimeData.

This module provides endpoints for managing workspace team members,
including listing, inviting, updating roles, and removing members.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..core.scope import ensure_workspace_access
from ..core.security import get_current_user
from ..db.database import get_db
from ..db.models import InvitationStatus, User, Workspace, WorkspaceInvitation, WorkspaceMember, WorkspaceRole
from ..services.email_service import send_invitation_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workspaces", tags=["Team"])


class TeamMemberResponse(BaseModel):
    """Team member response model."""

    id: str
    user_id: str
    email: str
    name: str
    role: str
    created_at: str


class InviteMemberRequest(BaseModel):
    """Invite team member request model."""

    email: EmailStr
    role: str  # "admin", "editor", or "viewer"


class UpdateMemberRoleRequest(BaseModel):
    """Update member role request model."""

    role: str  # "admin", "editor", or "viewer"


class InvitationResponse(BaseModel):
    """Invitation response model."""

    id: str
    email: str
    role: str
    status: str
    invited_by: str
    invited_by_name: str
    expires_at: str
    created_at: str
    accepted_at: Optional[str] = None


@router.get("/{workspace_id}/members", response_model=List[TeamMemberResponse])
async def list_workspace_members(
    workspace_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List all members of a workspace.

    Args:
        workspace_id: Workspace ID
        request: FastAPI request object
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of workspace members
    """
    # Ensure user has access to the workspace
    ensure_workspace_access(db, request, workspace_id)

    # Get all workspace members with user details
    members = (
        db.query(WorkspaceMember, User)
        .join(User, WorkspaceMember.user_id == User.id)
        .filter(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.created_at)
        .all()
    )

    result = []
    for membership, user in members:
        result.append(
            TeamMemberResponse(
                id=str(membership.id),
                user_id=str(user.id),
                email=user.email,
                name=user.name,
                role=membership.role.value,
                created_at=membership.created_at.isoformat(),
            )
        )

    return result


@router.post("/{workspace_id}/members/invite", response_model=InvitationResponse)
async def invite_workspace_member(
    workspace_id: UUID,
    request_body: InviteMemberRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Invite a user to join the workspace.

    Creates a WorkspaceInvitation and sends an invitation email.

    Args:
        workspace_id: Workspace ID
        request_body: Invite member request with email and role
        request: FastAPI request object
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created invitation
    """
    # Ensure user has access to the workspace and is admin/owner
    workspace = ensure_workspace_access(db, request, workspace_id, roles=["admin", "owner"])

    # Validate role
    try:
        role = WorkspaceRole(request_body.role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {request_body.role}. Must be one of: owner, admin, editor, viewer",
        )

    # Don't allow inviting as owner (only existing owners can be owners)
    if role == WorkspaceRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot invite users as owner. Owners must be assigned directly.",
        )

    # Check if user is already a member
    user = db.query(User).filter(User.email == request_body.email).first()
    if user:
        existing_membership = (
            db.query(WorkspaceMember)
            .filter(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user.id)
            .first()
        )
        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {request_body.email} is already a member of this workspace",
            )

    # Check for existing pending invitation
    existing_invitation = (
        db.query(WorkspaceInvitation)
        .filter(
            WorkspaceInvitation.workspace_id == workspace_id,
            WorkspaceInvitation.email == request_body.email,
            WorkspaceInvitation.status == InvitationStatus.PENDING,
        )
        .first()
    )

    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pending invitation already exists for {request_body.email}",
        )

    # Generate invitation token and set expiration
    invitation_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    user_id = UUID(current_user["sub"])

    # Create invitation
    invitation = WorkspaceInvitation(
        workspace_id=workspace_id,
        email=request_body.email,
        role=role,
        invitation_token=invitation_token,
        invited_by=user_id,
        status=InvitationStatus.PENDING,
        expires_at=expires_at,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    # Get inviter details
    inviter = db.query(User).filter(User.id == user_id).first()
    inviter_name = inviter.name if inviter else "Team Admin"

    # Send invitation email
    email_sent = send_invitation_email(
        email=request_body.email,
        invitation_token=invitation_token,
        workspace_name=workspace.name,
        inviter_name=inviter_name,
        role=role.value,
    )

    if not email_sent:
        logger.warning(f"Failed to send invitation email to {request_body.email}, but invitation created")

    logger.info(f"Created invitation for {request_body.email} to workspace {workspace_id} with role {role.value}")

    return InvitationResponse(
        id=str(invitation.id),
        email=invitation.email,
        role=invitation.role.value,
        status=invitation.status.value,
        invited_by=str(invitation.invited_by),
        invited_by_name=inviter_name,
        expires_at=invitation.expires_at.isoformat(),
        created_at=invitation.created_at.isoformat(),
        accepted_at=invitation.accepted_at.isoformat() if invitation.accepted_at else None,
    )


@router.patch("/{workspace_id}/members/{member_id}", response_model=TeamMemberResponse)
async def update_member_role(
    workspace_id: UUID,
    member_id: UUID,
    request_body: UpdateMemberRoleRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Update a workspace member's role.

    Args:
        workspace_id: Workspace ID
        member_id: Workspace member ID
        request_body: Update role request
        request: FastAPI request object
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated workspace membership
    """
    # Ensure user has access to the workspace and is admin/owner
    ensure_workspace_access(db, request, workspace_id, roles=["admin", "owner"])

    # Find the membership
    membership = (
        db.query(WorkspaceMember).filter(WorkspaceMember.id == member_id, WorkspaceMember.workspace_id == workspace_id).first()
    )

    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace member not found")

    # Don't allow changing owner role
    if membership.role == WorkspaceRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change owner role. Owners must be assigned directly.",
        )

    # Validate new role
    try:
        new_role = WorkspaceRole(request_body.role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {request_body.role}. Must be one of: admin, editor, viewer",
        )

    # Don't allow setting owner role via update
    if new_role == WorkspaceRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot set owner role via update. Owners must be assigned directly.",
        )

    # Update role
    membership.role = new_role
    db.commit()
    db.refresh(membership)

    # Get user details
    user = db.query(User).filter(User.id == membership.user_id).first()

    logger.info(f"Updated member {member_id} role to {new_role.value} in workspace {workspace_id}")

    return TeamMemberResponse(
        id=str(membership.id),
        user_id=str(user.id),
        email=user.email,
        name=user.name,
        role=membership.role.value,
        created_at=membership.created_at.isoformat(),
    )


@router.delete("/{workspace_id}/members/{member_id}")
async def remove_workspace_member(
    workspace_id: UUID,
    member_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Remove a member from the workspace.

    Args:
        workspace_id: Workspace ID
        member_id: Workspace member ID
        request: FastAPI request object
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success response
    """
    # Ensure user has access to the workspace and is admin/owner
    ensure_workspace_access(db, request, workspace_id, roles=["admin", "owner"])

    # Find the membership
    membership = (
        db.query(WorkspaceMember).filter(WorkspaceMember.id == member_id, WorkspaceMember.workspace_id == workspace_id).first()
    )

    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace member not found")

    # Don't allow removing owners
    if membership.role == WorkspaceRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove owner from workspace. Transfer ownership first.",
        )

    # Get user details for logging
    user = db.query(User).filter(User.id == membership.user_id).first()
    user_email = user.email if user else "unknown"

    # Remove membership
    db.delete(membership)
    db.commit()

    logger.info(f"Removed member {member_id} ({user_email}) from workspace {workspace_id}")

    return {"status": "success", "message": f"Member {user_email} has been removed from the workspace"}


@router.get("/{workspace_id}/invitations", response_model=List[InvitationResponse])
async def list_workspace_invitations(
    workspace_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List all invitations for a workspace.

    Args:
        workspace_id: Workspace ID
        request: FastAPI request object
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of workspace invitations
    """
    # Ensure user has access to the workspace and is admin/owner
    ensure_workspace_access(db, request, workspace_id, roles=["admin", "owner"])

    # Get all invitations for the workspace
    invitations = (
        db.query(WorkspaceInvitation, User)
        .join(User, WorkspaceInvitation.invited_by == User.id)
        .filter(WorkspaceInvitation.workspace_id == workspace_id)
        .order_by(WorkspaceInvitation.created_at.desc())
        .all()
    )

    result = []
    for invitation, inviter in invitations:
        result.append(
            InvitationResponse(
                id=str(invitation.id),
                email=invitation.email,
                role=invitation.role.value,
                status=invitation.status.value,
                invited_by=str(invitation.invited_by),
                invited_by_name=inviter.name if inviter else "Unknown",
                expires_at=invitation.expires_at.isoformat(),
                created_at=invitation.created_at.isoformat(),
                accepted_at=invitation.accepted_at.isoformat() if invitation.accepted_at else None,
            )
        )

    return result


@router.post("/{workspace_id}/invitations/{invitation_id}/cancel")
async def cancel_invitation(
    workspace_id: UUID,
    invitation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Cancel a pending invitation.

    Args:
        workspace_id: Workspace ID
        invitation_id: Invitation ID
        request: FastAPI request object
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success response
    """
    # Ensure user has access to the workspace and is admin/owner
    ensure_workspace_access(db, request, workspace_id, roles=["admin", "owner"])

    # Find invitation
    invitation = (
        db.query(WorkspaceInvitation)
        .filter(WorkspaceInvitation.id == invitation_id, WorkspaceInvitation.workspace_id == workspace_id)
        .first()
    )

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    # Only cancel pending invitations
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel invitation with status: {invitation.status.value}",
        )

    # Cancel invitation
    invitation.status = InvitationStatus.CANCELLED
    db.commit()

    logger.info(f"Cancelled invitation {invitation_id} for {invitation.email}")

    return {"status": "success", "message": f"Invitation for {invitation.email} has been cancelled"}


@router.post("/{workspace_id}/invitations/{invitation_id}/resend")
async def resend_invitation(
    workspace_id: UUID,
    invitation_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Resend invitation email.

    Generates a new token and extends expiration to 7 days from now.

    Args:
        workspace_id: Workspace ID
        invitation_id: Invitation ID
        request: FastAPI request object
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success response with new expiration date
    """
    # Ensure user has access to the workspace and is admin/owner
    workspace = ensure_workspace_access(db, request, workspace_id, roles=["admin", "owner"])

    # Find invitation
    invitation = (
        db.query(WorkspaceInvitation)
        .filter(WorkspaceInvitation.id == invitation_id, WorkspaceInvitation.workspace_id == workspace_id)
        .first()
    )

    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    # Only resend pending invitations
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resend invitation with status: {invitation.status.value}",
        )

    # Check if expired
    if invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired. Please create a new invitation.",
        )

    # Generate new token and extend expiration
    invitation.invitation_token = secrets.token_urlsafe(32)
    invitation.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    invitation.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Get inviter details
    inviter = db.query(User).filter(User.id == invitation.invited_by).first()
    inviter_name = inviter.name if inviter else "Team Admin"

    # Resend email
    email_sent = send_invitation_email(
        email=invitation.email,
        invitation_token=invitation.invitation_token,
        workspace_name=workspace.name,
        inviter_name=inviter_name,
        role=invitation.role.value,
    )

    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to send invitation email. Please try again later.",
        )

    logger.info(f"Resent invitation {invitation_id} to {invitation.email}")

    return {
        "status": "success",
        "message": f"Invitation email resent to {invitation.email}",
        "expires_at": invitation.expires_at.isoformat(),
    }
