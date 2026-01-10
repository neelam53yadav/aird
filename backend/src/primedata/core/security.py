"""
Security utilities for JWT handling and user authentication.
"""

import time
from functools import lru_cache
from typing import Any, Dict, List, Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from loguru import logger
from primedata.core.jwt_keys import get_jwks
from primedata.core.settings import get_settings


@lru_cache(maxsize=1)
def get_cached_jwks():
    """Cache JWKS for 10 minutes."""
    return get_jwks()


def verify_rs256_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify RS256 JWT token using JWKS.

    Args:
        token: The JWT token to verify

    Returns:
        Token payload if valid, None otherwise
    """
    settings = get_settings()

    try:
        # Get the header to find the key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        # Decode token without verification to see claims
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        
        logger.info(
            f"Verifying token - kid: {kid}, "
            f"iss: {unverified_payload.get('iss')}, "
            f"aud: {unverified_payload.get('aud')}, "
            f"exp: {unverified_payload.get('exp')}, "
            f"expected_iss: {settings.JWT_ISSUER}, "
            f"expected_aud: {settings.JWT_AUDIENCE}"
        )

        if not kid:
            logger.error("Token missing 'kid' in header")
            return None

        # Get JWKS and find the key
        jwks = get_cached_jwks()
        key = None

        for jwk in jwks.get("keys", []):
            if jwk.get("kid") == kid:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                break

        if not key:
            available_kids = [k.get("kid") for k in jwks.get("keys", [])]
            logger.error(f"Key with kid '{kid}' not found in JWKS. Available kids: {available_kids}, JWKS keys count: {len(jwks.get('keys', []))}")
            return None

        # Verify the token
        try:
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=settings.JWT_AUDIENCE,
                issuer=settings.JWT_ISSUER,
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )
            logger.info(f"Token verification successful for user: {payload.get('sub')}")
            return payload
            
        except jwt.ExpiredSignatureError as e:
            logger.error(f"Token expired: {e}. Token exp: {unverified_payload.get('exp')}, Current time: {int(time.time())}")
            return None
            
        except jwt.InvalidAudienceError as e:
            logger.error(
                f"Invalid audience: {e}. "
                f"Expected: {settings.JWT_AUDIENCE}, "
                f"Got: {unverified_payload.get('aud')}"
            )
            return None
            
        except jwt.InvalidIssuerError as e:
            logger.error(
                f"Invalid issuer: {e}. "
                f"Expected: {settings.JWT_ISSUER}, "
                f"Got: {unverified_payload.get('iss')}"
            )
            return None
            
        except jwt.InvalidSignatureError as e:
            logger.error(f"Invalid signature: {e}. Token may be signed with a different key.")
            return None
            
        except jwt.InvalidTokenError as e:
            logger.exception(f"Invalid token error: {type(e).__name__}: {e}")
            return None
            
        except Exception as e:
            logger.exception(f"Unexpected error during token verification: {type(e).__name__}: {e}")
            return None
            
    except Exception as e:
        logger.exception(f"Unexpected error in verify_rs256_token: {type(e).__name__}: {e}")
        return None


def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from request state.
    
    AuthMiddleware already verifies the token and sets request.state.user.
    This dependency just extracts it - no token re-parsing or re-verification.

    Args:
        request: FastAPI Request object

    Returns:
        User information dict with sub, email, roles, workspaces

    Raises:
        HTTPException: If authentication fails (user not in request.state)
    """
    # Add logging for debugging (can be removed later if not needed)
    logger.debug(f"get_current_user - state.user exists? {hasattr(request.state, 'user')}, value={getattr(request.state, 'user', None)}")
    
    user = getattr(request.state, "user", None)
    if not user:
        logger.error("get_current_user - request.state.user is missing or None. Middleware may not have authenticated the request.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"get_current_user - returning user: {user.get('sub')}")
    return user


def require_roles(required_roles: List[str]):
    """
    Dependency factory to require specific roles.

    Args:
        required_roles: List of required roles

    Returns:
        Dependency function
    """

    def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_roles = user.get("roles", [])

        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {required_roles}",
            )

        return user

    return role_checker


def require_scopes(required_scopes: List[str]):
    """
    Dependency factory to require specific scopes.

    Args:
        required_scopes: List of required scopes

    Returns:
        Dependency function
    """

    def scope_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_scopes = user.get("scopes", [])

        if not any(scope in user_scopes for scope in required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required scopes: {required_scopes}",
            )

        return user

    return scope_checker
