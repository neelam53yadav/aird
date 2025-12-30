"""
Authentication middleware for FastAPI.
"""

import re
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
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
        ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Check if route allows anonymous access (before any auth checks)
        if self._is_anonymous_route(path):
            # Skip all authentication for anonymous routes
            # This is critical for /api/v1/auth/session/exchange as it's the first-time auth endpoint
            return await call_next(request)

        # Extract Bearer token
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Verify token
        payload = verify_rs256_token(token)
        if not payload:
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
        normalized_path = path.rstrip("/")

        for pattern in self.anonymous_routes:
            if re.match(pattern, normalized_path):
                return True
        return False
