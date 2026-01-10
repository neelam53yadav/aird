"""
Authentication API router.
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import dns.resolver
from email_validator import validate_email, EmailNotValidError
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from primedata.core.jwt_keys import sign_jwt
from primedata.core.nextauth_verify import verify_nextauth_token
from primedata.core.password import hash_password, verify_password
from primedata.core.security import get_current_user
from primedata.db.database import get_db
from primedata.db.models import AuthProvider, User, Workspace, WorkspaceMember, WorkspaceRole
from primedata.services.email_service import send_verification_email, send_password_reset_email
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
    first_name: str
    last_name: str


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


class SignupResponse(BaseModel):
    """Response model for signup."""

    message: str
    email: str
    requires_verification: bool = True


class EmailValidationRequest(BaseModel):
    """Request model for email validation."""

    email: str


class EmailValidationResponse(BaseModel):
    """Response model for email validation."""

    valid: bool
    message: str
    domain_valid: Optional[bool] = None
    address_verified: Optional[bool] = None


class VerifyEmailRequest(BaseModel):
    """Request model for email verification."""

    token: str


class ForgotPasswordRequest(BaseModel):
    """Request model for forgot password."""
    
    email: str


class ForgotPasswordResponse(BaseModel):
    """Response model for forgot password."""
    
    message: str


class ResetPasswordRequest(BaseModel):
    """Request model for password reset."""
    
    token: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    """Response model for password reset."""
    
    message: str


class ResendVerificationRequest(BaseModel):
    """Request model for resend verification."""
    
    email: str


class ResendVerificationResponse(BaseModel):
    """Response model for resend verification."""
    
    message: str


@router.post("/api/v1/auth/validate-email", response_model=EmailValidationResponse)
async def validate_email_endpoint(request: EmailValidationRequest, db: Session = Depends(get_db)):
    """
    Validate email format and check if domain exists (has MX records).
    """
    email = request.email.strip().lower()
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    
    try:
        # Validate email format using email-validator
        validation = validate_email(email, check_deliverability=True)
        email = validation.normalized
        
        # Additional check: verify domain has MX records
        domain = email.split("@")[1]
        try:
            mx_records = dns.resolver.resolve(domain, "MX")
            has_mx = len(mx_records) > 0
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.Timeout):
            has_mx = False
        
        if not has_mx:
            return EmailValidationResponse(
                valid=False,
                message="Email domain does not exist or cannot receive emails",
                domain_valid=False,
                address_verified=None
            )
        
        return EmailValidationResponse(
            valid=True,
            message="Email format and domain are valid",
            domain_valid=True,
            address_verified=None  # Cannot verify specific address without sending email
        )
        
    except EmailNotValidError as e:
        return EmailValidationResponse(
            valid=False,
            message=str(e),
            domain_valid=None,
            address_verified=None
        )
    except Exception as e:
        logger.error(f"Email validation error: {e}")
        return EmailValidationResponse(
            valid=False,
            message="Unable to validate email. Please try again.",
            domain_valid=None,
            address_verified=None
        )


@router.post("/api/v1/auth/signup", response_model=SignupResponse)
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """
    Register a new user with email and password.
    Creates account but requires email verification.
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this email already exists")

    # Validate email format and domain
    try:
        validation = validate_email(request.email, check_deliverability=True)
        email = validation.normalized
    except EmailNotValidError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Create new user (marked as unverified)
    password_hash = hash_password(request.password)
    verification_token = secrets.token_urlsafe(32)  # Generate unique token
    verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)  # 24 hour expiry
    
    # Construct full name from first and last name
    full_name = f"{request.first_name} {request.last_name}".strip()
    
    user = User(
        email=email,
        name=full_name,  # Store full name in name field for backward compatibility
        first_name=request.first_name,
        last_name=request.last_name,
        password_hash=password_hash,
        auth_provider=AuthProvider.SIMPLE,
        roles=["viewer"],
        email_verified=False,
        verification_token=verification_token,
        verification_token_expires=verification_expires,
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

    # Send verification email (use first name for personalization)
    email_sent = send_verification_email(user.email, verification_token, user.first_name)
    if not email_sent:
        logger.warning(f"Failed to send verification email to {user.email}, but account created")

    return SignupResponse(
        message="Account created successfully. Please check your email to verify your account.",
        email=user.email,
        requires_verification=True
    )


@router.post("/api/v1/auth/verify-email")
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    Verify user's email address using verification token.
    """
    if not request.token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification token is required")

    # Log the received token for debugging
    logger.info(f"Verification attempt - token length: {len(request.token)}, token preview: {request.token[:20]}...")

    # Find user by verification token
    user = db.query(User).filter(User.verification_token == request.token).first()
    
    # If token not found, check if user might already be verified
    # This handles the case where the token was already used (idempotent operation)
    if not user:
        # Check if there's a recently verified user (within last 5 minutes)
        # This is a fallback for when token was already used
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        recently_verified = db.query(User).filter(
            User.email_verified == True,
            User.updated_at >= recent_time
        ).first()
        
        if recently_verified:
            logger.info(f"Token not found, but found recently verified user: {recently_verified.email}")
            return {
                "message": "Email already verified",
                "email": recently_verified.email,
                "verified": True
            }
        
        unverified_count = db.query(User).filter(User.email_verified == False).count()
        logger.warning(f"Token not found. Total unverified users: {unverified_count}")
        # Also log a sample of existing tokens for debugging (first 20 chars only)
        sample_tokens = db.query(User.verification_token).filter(
            User.verification_token.isnot(None),
            User.email_verified == False
        ).limit(3).all()
        if sample_tokens:
            logger.debug(f"Sample existing tokens: {[t[0][:20] + '...' if t[0] else None for t in sample_tokens]}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token. If you already verified your email, please try signing in."
        )
    
    # Check if token has expired
    if user.verification_token_expires and user.verification_token_expires < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new verification email."
        )
    
    # Check if already verified (idempotent check)
    if user.email_verified:
        logger.info(f"User {user.email} already verified, returning success")
        return {
            "message": "Email already verified",
            "email": user.email,
            "verified": True
        }
    
    # Verify the email
    user.email_verified = True
    user.verification_token = None  # Clear token after verification
    user.verification_token_expires = None
    db.commit()
    
    logger.info(f"Email verified for user: {user.email}")
    
    return {
        "message": "Email verified successfully",
        "email": user.email,
        "verified": True
    }


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
    
    # Check if email is verified (only for email/password auth)
    if user.auth_provider == AuthProvider.SIMPLE and not user.email_verified:
        # Check if verification token expired
        token_expired = (
            user.verification_token_expires and 
            user.verification_token_expires < datetime.now(timezone.utc)
        )
        
        if token_expired:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your verification link has expired. Please request a new verification email.",
                headers={"X-Verification-Expired": "true"}  # Flag for frontend
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email address before logging in. Check your inbox for the verification email.",
                headers={"X-Verification-Pending": "true"}  # Flag for frontend
            )

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


@router.post("/api/v1/auth/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Request password reset email.
    """
    email = request.email.strip().lower()
    
    # Find user by email
    user = db.query(User).filter(User.email == email).first()
    
    # Check if user exists
    if not user:
        logger.warning(f"Password reset requested for non-existent email: {email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email address."
        )
    
    # Only allow password reset for email/password users
    if user.auth_provider != AuthProvider.SIMPLE:
        logger.warning(f"Password reset requested for OAuth user: {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset is not available for accounts signed in with Google. Please use Google sign-in instead."
        )
    
    # Check if email is verified
    if not user.email_verified:
        logger.warning(f"Password reset requested for unverified email: {email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before resetting your password. Check your inbox for the verification email."
        )
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    
    # Save reset token to user
    user.password_reset_token = reset_token
    user.password_reset_token_expires = reset_token_expires
    db.commit()
    
    # Send password reset email
    email_sent = send_password_reset_email(user.email, reset_token, user.first_name or user.name)
    if not email_sent:
        logger.warning(f"Failed to send password reset email to {user.email}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to send password reset email. Please try again later."
        )
    
    logger.info(f"Password reset email sent to {user.email}")
    return ForgotPasswordResponse(
        message="Password reset link has been sent to your email address. Please check your inbox."
    )


@router.post("/api/v1/auth/resend-verification", response_model=ResendVerificationResponse)
async def resend_verification(request: ResendVerificationRequest, db: Session = Depends(get_db)):
    """
    Resend verification email for unverified users.
    """
    email = request.email.strip().lower()
    
    # Find user by email
    user = db.query(User).filter(User.email == email).first()
    
    # Always return success message (don't reveal if email exists - security best practice)
    if not user:
        logger.warning(f"Resend verification requested for non-existent email: {email}")
        return ResendVerificationResponse(
            message="If an account exists with this email and it's unverified, a verification email has been sent."
        )
    
    # Only for email/password auth
    if user.auth_provider != AuthProvider.SIMPLE:
        logger.warning(f"Resend verification requested for OAuth user: {email}")
        return ResendVerificationResponse(
            message="If an account exists with this email and it's unverified, a verification email has been sent."
        )
    
    # If already verified, don't resend
    if user.email_verified:
        logger.info(f"Resend verification requested for already verified user: {email}")
        return ResendVerificationResponse(
            message="Your email is already verified. You can log in now."
        )
    
    # Generate new verification token
    verification_token = secrets.token_urlsafe(32)
    verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    
    user.verification_token = verification_token
    user.verification_token_expires = verification_expires
    db.commit()
    
    # Send verification email
    email_sent = send_verification_email(
        user.email, 
        verification_token, 
        user.first_name or user.name
    )
    
    if not email_sent:
        logger.warning(f"Failed to send verification email to {user.email}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to send verification email. Please try again later."
        )
    
    logger.info(f"Verification email resent to {user.email}")
    return ResendVerificationResponse(
        message="Verification email has been sent. Please check your inbox."
    )


@router.post("/api/v1/auth/reset-password", response_model=ResetPasswordResponse)
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using reset token.
    """
    if not request.token or not request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token and new password are required"
        )
    
    # Find user by reset token
    user = db.query(User).filter(User.password_reset_token == request.token).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Check if token has expired
    if user.password_reset_token_expires and user.password_reset_token_expires < datetime.now(timezone.utc):
        # Clear expired token
        user.password_reset_token = None
        user.password_reset_token_expires = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new password reset."
        )
    
    # Validate password complexity (same as signup)
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Hash new password
    password_hash = hash_password(request.new_password)
    
    # Update password and clear reset token
    user.password_hash = password_hash
    user.password_reset_token = None
    user.password_reset_token_expires = None
    db.commit()
    
    logger.info(f"Password reset successful for user: {user.email}")
    
    return ResetPasswordResponse(
        message="Password reset successfully. You can now sign in with your new password."
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


@router.get("/api/v1/workspaces/", response_model=List[WorkspaceResponse])
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


@router.post("/api/v1/workspaces/", response_model=WorkspaceCreateResponse)
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
