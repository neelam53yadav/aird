"""
Authentication API router.
"""

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from primedata.core.jwt_keys import sign_jwt
from primedata.core.nextauth_verify import verify_nextauth_token
from primedata.core.password import hash_password, verify_password
from primedata.core.security import get_current_user
from primedata.db.database import get_db
from primedata.db.models import AuthProvider, User, Workspace, WorkspaceMember, WorkspaceRole
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter()


class SessionExchangeRequest(BaseModel):
    """Request model for session exchange."""

    token: str


class SessionExchangeResponse(BaseModel):
    """Response model for session exchange."""

    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    default_workspace_id: str


class UserResponse(BaseModel):
    """User response model."""

    id: str
    email: str
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    timezone: Optional[str] = None
    roles: List[str]
    picture_url: Optional[str] = None


class WorkspaceResponse(BaseModel):
    """Workspace response model."""

    id: str
    name: str
    role: str
    created_at: str


class SignupRequest(BaseModel):
    """Signup request model."""

    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    """Login request model."""

    email: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""

    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    default_workspace_id: str


@router.post("/api/v1/auth/signup", response_model=LoginResponse)
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """
    Register a new user with email and password.
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this email already exists")

    # Create new user
    password_hash = hash_password(request.password)
    user = User(
        email=request.email,
        name=request.name,
        password_hash=password_hash,
        auth_provider=AuthProvider.SIMPLE,
        roles=["viewer"],
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create default workspace
    workspace = Workspace(name=f"{user.name}'s Workspace")
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    # Add user as owner
    membership = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.OWNER)
    db.add(membership)
    db.commit()

    # Sign JWT token
    payload = {"sub": str(user.id), "email": user.email, "roles": user.roles, "workspaces": [str(workspace.id)]}
    access_token = sign_jwt(payload, exp_s=3600)

    return LoginResponse(
        access_token=access_token,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "roles": user.roles,
            "picture_url": user.picture_url,
        },
        default_workspace_id=str(workspace.id),
    )


@router.post("/api/v1/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # Verify password
    if not user.password_hash or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # Check if user is active
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    # Get workspace memberships
    workspace_memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).all()

    if not workspace_memberships:
        # Create default workspace if none exists
        workspace = Workspace(name=f"{user.name}'s Workspace")
        db.add(workspace)
        db.commit()
        db.refresh(workspace)

        membership = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.OWNER)
        db.add(membership)
        db.commit()
        default_workspace_id = str(workspace.id)
        workspace_ids = [default_workspace_id]
    else:
        default_workspace_id = str(workspace_memberships[0].workspace_id)
        workspace_ids = [str(m.workspace_id) for m in workspace_memberships]

    # Sign JWT token
    payload = {"sub": str(user.id), "email": user.email, "roles": user.roles, "workspaces": workspace_ids}
    access_token = sign_jwt(payload, exp_s=3600)

    return LoginResponse(
        access_token=access_token,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "roles": user.roles,
            "picture_url": user.picture_url,
        },
        default_workspace_id=default_workspace_id,
    )


def normalize_auth_provider(provider: str | None) -> AuthProvider:
    """
    Normalize NextAuth provider string to AuthProvider enum.

    NextAuth may send "credentials" for username/password auth.
    We map that to SIMPLE in our backend enum.
    """
    if not provider:
        return AuthProvider.NONE

    p = provider.lower().strip()

    # NextAuth credentials provider (email/password)
    if p in {"credentials", "email"}:
        return AuthProvider.SIMPLE

    # OAuth providers
    if p == "google":
        return AuthProvider.GOOGLE

    # Future-proofing
    if p == "github":
        return AuthProvider.SIMPLE  # or create AuthProvider.GITHUB later

    # Unknown provider
    return AuthProvider.NONE


@router.post("/api/v1/auth/session/exchange", response_model=SessionExchangeResponse)
async def exchange_session(request: SessionExchangeRequest, db: Session = Depends(get_db)):
    """
    Exchange NextAuth token for backend JWT.

    Args:
        request: Session exchange request with NextAuth token
        db: Database session

    Returns:
        Backend JWT token and user information
    """
    # Verify NextAuth token
    claims = verify_nextauth_token(request.token)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired NextAuth token")

    email = claims["email"]
    name = claims["name"]
    picture = claims["picture"]
    provider = claims["provider"]
    google_sub = claims.get("google_sub")

    # Upsert user
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Create new user
        user = User(
            email=email,
            name=name,
            picture_url=picture,
            auth_provider=normalize_auth_provider(provider),
            google_sub=google_sub,
            roles=["viewer"],
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update existing user
        user.name = name
        user.picture_url = picture
        user.auth_provider = normalize_auth_provider(provider)
        if google_sub:
            user.google_sub = google_sub
        db.commit()

    # Check if user has any workspace memberships
    workspace_memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).all()

    default_workspace_id = None

    if not workspace_memberships:
        # Create default workspace and add user as owner
        workspace = Workspace(name=f"{user.name}'s Workspace")
        db.add(workspace)
        db.commit()
        db.refresh(workspace)

        # Add user as owner
        membership = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.OWNER)
        db.add(membership)
        db.commit()

        default_workspace_id = str(workspace.id)
    else:
        # Use the first workspace as default
        default_workspace_id = str(workspace_memberships[0].workspace_id)

    # Gather workspace IDs
    workspace_ids = [str(m.workspace_id) for m in workspace_memberships]

    # Sign backend JWT
    payload = {"sub": str(user.id), "email": user.email, "roles": user.roles, "workspaces": workspace_ids}

    access_token = sign_jwt(payload, exp_s=3600)

    return SessionExchangeResponse(
        access_token=access_token,
        user={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "roles": user.roles,
            "picture_url": user.picture_url,
        },
        default_workspace_id=default_workspace_id,
    )


@router.get("/api/v1/users/me", response_model=UserResponse)
async def get_current_user_info(user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get current user information.

    Args:
        user: Current authenticated user
        db: Database session

    Returns:
        User information
    """
    user_id = uuid.UUID(user["sub"])
    db_user = db.query(User).filter(User.id == user_id).first()

    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Convert roles from JSON format (e.g., {"global": ["admin"]}) to flat list
    roles_list = []
    if db_user.roles:
        if isinstance(db_user.roles, dict):
            # Extract all roles from nested structure
            for role_group in db_user.roles.values():
                if isinstance(role_group, list):
                    roles_list.extend(role_group)
                elif isinstance(role_group, str):
                    roles_list.append(role_group)
        elif isinstance(db_user.roles, list):
            roles_list = db_user.roles
        elif isinstance(db_user.roles, str):
            roles_list = [db_user.roles]

    return UserResponse(
        id=str(db_user.id),
        email=db_user.email,
        name=db_user.name,
        first_name=db_user.first_name,
        last_name=db_user.last_name,
        timezone=db_user.timezone,
        roles=roles_list,
        picture_url=db_user.picture_url,
    )


@router.get("/api/v1/workspaces", response_model=List[WorkspaceResponse])
async def get_user_workspaces(user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get user's workspaces.

    Args:
        user: Current authenticated user
        db: Database session

    Returns:
        List of user's workspaces
    """
    user_id = uuid.UUID(user["sub"])

    # Get workspace memberships with workspace details
    memberships = (
        db.query(WorkspaceMember, Workspace)
        .join(Workspace, WorkspaceMember.workspace_id == Workspace.id)
        .filter(WorkspaceMember.user_id == user_id)
        .all()
    )

    workspaces = []
    for membership, workspace in memberships:
        workspaces.append(
            WorkspaceResponse(
                id=str(workspace.id),
                name=workspace.name,
                role=membership.role.value,
                created_at=workspace.created_at.isoformat(),
            )
        )

    return workspaces


class WorkspaceCreateRequest(BaseModel):
    """Workspace creation request model."""

    name: Optional[str] = None  # Optional name, defaults to "{user.name}'s Workspace"


class WorkspaceCreateResponse(BaseModel):
    """Workspace creation response model."""

    id: str
    name: str
    created_at: str


@router.post("/api/v1/workspaces", response_model=WorkspaceCreateResponse)
async def create_workspace(
    request_body: WorkspaceCreateRequest, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Create a new workspace for the current user.

    If user already has workspaces, returns the first one.
    Otherwise, creates a new workspace and adds user as owner.
    """
    from primedata.core.user_utils import get_user_id
    from primedata.db.models import Workspace, WorkspaceMember, WorkspaceRole

    user_id = get_user_id(user)

    # Check if user already has workspaces
    existing_memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user_id).all()

    if existing_memberships:
        # Return the first existing workspace
        workspace = db.query(Workspace).filter(Workspace.id == existing_memberships[0].workspace_id).first()

        if workspace:
            return WorkspaceCreateResponse(
                id=str(workspace.id), name=workspace.name, created_at=workspace.created_at.isoformat()
            )

    # Create new workspace
    workspace_name = request_body.name or f"{user.get('name', 'User')}'s Workspace"
    workspace = Workspace(name=workspace_name)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    # Add user as owner
    membership = WorkspaceMember(workspace_id=workspace.id, user_id=user_id, role=WorkspaceRole.OWNER)
    db.add(membership)
    db.commit()

    return WorkspaceCreateResponse(id=str(workspace.id), name=workspace.name, created_at=workspace.created_at.isoformat())


class UserProfileUpdateRequest(BaseModel):
    """User profile update request model."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    timezone: Optional[str] = None


class UserProfileResponse(BaseModel):
    """User profile response model."""

    id: str
    email: str
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    timezone: Optional[str] = None
    picture_url: Optional[str] = None


@router.put("/api/v1/user/profile", response_model=UserProfileResponse)
async def update_user_profile(
    request_body: UserProfileUpdateRequest, user: Dict[str, Any] = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Update user profile information.

    Args:
        request_body: Profile update request
        user: Current authenticated user
        db: Database session

    Returns:
        Updated user profile information
    """
    user_id = uuid.UUID(user["sub"])
    db_user = db.query(User).filter(User.id == user_id).first()

    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update user profile fields
    if request_body.first_name is not None:
        db_user.first_name = request_body.first_name

    if request_body.last_name is not None:
        db_user.last_name = request_body.last_name

    if request_body.timezone is not None:
        db_user.timezone = request_body.timezone

    # Update the name field if first_name or last_name changed
    if request_body.first_name is not None or request_body.last_name is not None:
        first_name = request_body.first_name if request_body.first_name is not None else db_user.first_name
        last_name = request_body.last_name if request_body.last_name is not None else db_user.last_name

        if first_name and last_name:
            db_user.name = f"{first_name} {last_name}"
        elif first_name:
            db_user.name = first_name
        elif last_name:
            db_user.name = last_name

    db.commit()
    db.refresh(db_user)

    return UserProfileResponse(
        id=str(db_user.id),
        email=db_user.email,
        name=db_user.name,
        first_name=db_user.first_name,
        last_name=db_user.last_name,
        timezone=db_user.timezone,
        picture_url=db_user.picture_url,
    )
