"""
Authentication middleware for FastAPI.
"""

import re
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from loguru import logger
from primedata.core.security import verify_rs256_token
from primedata.core.settings import get_settings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware that handles JWT verification."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        # Routes that allow anonymous access
        self.anonymous_routes = [
            r"^/health$",
            r"^/openapi\.json$",
            r"^/docs.*",
            r"^/redoc.*",
            r"^/\.well-known/jwks\.json$",
            r"^/api/v1/auth/session/exchange$",  # Token exchange endpoint - must be anonymous
            r"^/api/v1/auth/session/exchange/$",  # With trailing slash
            r"^/api/v1/auth/signup$",  # Signup endpoint
            r"^/api/v1/auth/signup/$",  # With trailing slash
            r"^/api/v1/auth/login$",  # Login endpoint
            r"^/api/v1/auth/login/$",  # With trailing slash
            r"^/api/v1/auth/validate-email$",  # Email validation endpoint - must be anonymous
            r"^/api/v1/auth/validate-email/$",  # With trailing slash
            r"^/api/v1/auth/verify-email$",  # Email verification endpoint - must be anonymous
            r"^/api/v1/auth/verify-email/$",  # With trailing slash
            r"^/api/v1/auth/resend-verification$",  # Resend verification endpoint - must be anonymous
            r"^/api/v1/auth/resend-verification/$",  # With trailing slash
            r"^/api/v1/auth/forgot-password$",  # Forgot password endpoint - must be anonymous
            r"^/api/v1/auth/forgot-password/$",  # With trailing slash
            r"^/api/v1/auth/reset-password$",  # Reset password endpoint - must be anonymous
            r"^/api/v1/auth/reset-password/$",  # With trailing slash
            r"^/api/v1/invitations/validate$",  # Invitation validation endpoint - must be anonymous
            r"^/api/v1/invitations/validate/$",  # With trailing slash
            r"^/api/v1/contact/submit$",  # Contact form endpoint - must be anonymous
            r"^/api/v1/contact/submit/$",  # With trailing slash
        ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow OPTIONS requests (CORS preflight) to pass through without auth
        if request.method == "OPTIONS":
            return await call_next(request)

        # Check if route allows anonymous access (before any auth checks)
        # IMPORTANT: Do this check BEFORE extracting any tokens/cookies
        if self._is_anonymous_route(path):
            # Skip all authentication for anonymous routes
            # Don't even check for tokens or cookies
            logger.debug(f"Skipping auth check for anonymous route: {path}")
            return await call_next(request)

        # Extract Bearer token from Authorization header OR cookie
        auth_header = request.headers.get("authorization")

        # Log auth header check
        logger.debug(f"Auth header check - path: {path}, has_auth_header: {bool(auth_header)}, method: {request.method}")

        # Also check for token in cookie (for httpOnly cookies that JS can't read)
        cookie_token = None
        if not auth_header or not auth_header.startswith("Bearer "):
            # Try to get token from cookie
            cookie_header = request.headers.get("cookie", "")
            if cookie_header:
                for cookie in cookie_header.split("; "):
                    if cookie.startswith("primedata_api_token="):
                        cookie_token = cookie.split("=", 1)[1]
                        break

        # Use Authorization header if present, otherwise fall back to cookie
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
        elif cookie_token:
            token = cookie_token

        # Log token extraction
        token_source = "header" if (auth_header and auth_header.startswith("Bearer ")) else "cookie" if cookie_token else "none"
        logger.debug(f"Token extraction - path: {path}, has_token: {bool(token)}, token_length: {len(token) if token else 0}, source: {token_source}")

        if not token:
            # CORSMiddleware will handle CORS headers automatically
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify token (already extracted above)
        payload = verify_rs256_token(token)

        # Log token verification result
        if payload:
            logger.debug(f"Token verification successful - path: {path}, user: {payload.get('sub')}")
        else:
            logger.warning(f"Token verification failed - path: {path}")

        if not payload:
            # CORSMiddleware will handle CORS headers automatically
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Attach user info to request state
        request.state.user = {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
            "workspaces": payload.get("workspaces", []),
        }

        return await call_next(request)

    def _is_anonymous_route(self, path: str) -> bool:
        """Check if the given path allows anonymous access."""
        # Normalize path (remove trailing slash, handle query params)
        # Split on '?' to remove query parameters
        path_without_query = path.split('?')[0]
        normalized_path = path_without_query.rstrip("/")
        
        # Add debug logging
        logger.debug(f"Checking if route is anonymous - path: {path}, normalized: {normalized_path}")

        for pattern in self.anonymous_routes:
            if re.match(pattern, normalized_path):
                logger.debug(f"Route matched anonymous pattern: {pattern}")
                return True
        logger.debug(f"Route did not match any anonymous patterns")
        return False
