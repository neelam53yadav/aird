"""
Security utilities for JWT handling and user authentication.
"""

import time
from functools import lru_cache
from typing import Any, Dict, List, Optional

import jwt
from fastapi import Depends, HTTPException, status
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
        
        # #region agent log
        import json
        import logging
        logger = logging.getLogger(__name__)
        log_data = {
            "location": "security.py:35",
            "message": "Token header and unverified payload",
            "data": {
                "has_kid": bool(kid),
                "kid": kid,
                "unverified_iss": unverified_payload.get("iss"),
                "unverified_aud": unverified_payload.get("aud"),
                "unverified_exp": unverified_payload.get("exp"),
                "expected_iss": settings.JWT_ISSUER,
                "expected_aud": settings.JWT_AUDIENCE,
                "payload_keys": list(unverified_payload.keys()),
            },
            "timestamp": int(__import__("time").time() * 1000),
            "sessionId": "debug-session",
            "runId": "run3",
            "hypothesisId": "G"
        }
        logger.info(f"TOKEN_VERIFY_HEADER: {json.dumps(log_data)}")
        try:
            with open("/Users/atul7717/Desktop/Code/aird/.cursor/debug.log", "a") as f:
                f.write(json.dumps(log_data) + "\n")
        except Exception as e:
            logger.error(f"Failed to write debug log: {e}")
        # #endregion

        if not kid:
            return None

        # Get JWKS and find the key
        jwks = get_cached_jwks()
        key = None

        for jwk in jwks.get("keys", []):
            if jwk.get("kid") == kid:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                break

        if not key:
            # #region agent log
            log_data = {
                "location": "security.py:51",
                "message": "Key not found in JWKS",
                "data": {
                    "kid": kid,
                    "jwks_keys_count": len(jwks.get("keys", [])),
                },
                "timestamp": int(__import__("time").time() * 1000),
                "sessionId": "debug-session",
                "runId": "run3",
                "hypothesisId": "G"
            }
            try:
                with open("/Users/atul7717/Desktop/Code/aird/.cursor/debug.log", "a") as f:
                    f.write(json.dumps(log_data) + "\n")
            except: pass
            # #endregion
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
            
            # #region agent log
            import json
            log_data = {
                "location": "security.py:54",
                "message": "Token verification successful",
                "data": {
                    "has_payload": bool(payload),
                    "payload_keys": list(payload.keys()) if payload else [],
                    "audience": settings.JWT_AUDIENCE,
                    "issuer": settings.JWT_ISSUER,
                },
                "timestamp": int(__import__("time").time() * 1000),
                "sessionId": "debug-session",
                "runId": "run3",
                "hypothesisId": "G"
            }
            try:
                with open("/Users/atul7717/Desktop/Code/aird/.cursor/debug.log", "a") as f:
                    f.write(json.dumps(log_data) + "\n")
            except: pass
            # #endregion
            
            return payload
        except jwt.ExpiredSignatureError as e:
            # #region agent log
            log_data = {
                "location": "security.py:71",
                "message": "Token expired",
                "data": {
                    "error": str(e),
                },
                "timestamp": int(__import__("time").time() * 1000),
                "sessionId": "debug-session",
                "runId": "run3",
                "hypothesisId": "G"
            }
            try:
                with open("/Users/atul7717/Desktop/Code/aird/.cursor/debug.log", "a") as f:
                    f.write(json.dumps(log_data) + "\n")
            except: pass
            # #endregion
            return None
        except jwt.InvalidTokenError as e:
            # #region agent log
            import logging
            logger = logging.getLogger(__name__)
            log_data = {
                "location": "security.py:73",
                "message": "Invalid token",
                "data": {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "audience": settings.JWT_AUDIENCE,
                    "issuer": settings.JWT_ISSUER,
                },
                "timestamp": int(__import__("time").time() * 1000),
                "sessionId": "debug-session",
                "runId": "run3",
                "hypothesisId": "G"
            }
            logger.error(f"TOKEN_VERIFY_INVALID: {json.dumps(log_data)}")
            try:
                with open("/Users/atul7717/Desktop/Code/aird/.cursor/debug.log", "a") as f:
                    f.write(json.dumps(log_data) + "\n")
            except Exception as file_err:
                logger.error(f"Failed to write debug log: {file_err}")
            # #endregion
            return None
        except Exception as e:
            # #region agent log
            log_data = {
                "location": "security.py:75",
                "message": "Token verification exception",
                "data": {
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                "timestamp": int(__import__("time").time() * 1000),
                "sessionId": "debug-session",
                "runId": "run3",
                "hypothesisId": "G"
            }
            try:
                with open("/Users/atul7717/Desktop/Code/aird/.cursor/debug.log", "a") as f:
                    f.write(json.dumps(log_data) + "\n")
            except: pass
            # #endregion
            return None


def get_current_user(token: str = Depends(lambda: None)) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user.

    Args:
        token: Bearer token from Authorization header

    Returns:
        User information dict

    Raises:
        HTTPException: If authentication fails
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_rs256_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
        "workspaces": payload.get("workspaces", []),
    }


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
