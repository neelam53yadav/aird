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

        # Allow OPTIONS requests (CORS preflight) to pass through without auth
        if request.method == "OPTIONS":
            return await call_next(request)

        # Check if route allows anonymous access (before any auth checks)
        if self._is_anonymous_route(path):
            # Skip all authentication for anonymous routes
            # This is critical for /api/v1/auth/session/exchange as it's the first-time auth endpoint
            return await call_next(request)

        # Extract Bearer token from Authorization header OR cookie
        auth_header = request.headers.get("authorization")
        
        # #region agent log
        import json
        import logging
        logger = logging.getLogger(__name__)
        log_data = {
            "location": "auth_middleware.py:51",
            "message": "Auth header check",
            "data": {
                "path": path,
                "has_auth_header": bool(auth_header),
                "auth_header_prefix": auth_header[:30] if auth_header else None,
                "method": request.method,
            },
            "timestamp": int(__import__("time").time() * 1000),
            "sessionId": "debug-session",
            "runId": "run3",
            "hypothesisId": "F"
        }
        logger.info(f"AUTH_MIDDLEWARE: {json.dumps(log_data)}")
        try:
            with open("/Users/atul7717/Desktop/Code/aird/.cursor/debug.log", "a") as f:
                f.write(json.dumps(log_data) + "\n")
        except Exception as e:
            logger.error(f"Failed to write debug log: {e}")
        # #endregion
        
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
        
        # #region agent log
        import logging
        logger = logging.getLogger(__name__)
        log_data = {
            "location": "auth_middleware.py:75",
            "message": "Token extraction result",
            "data": {
                "path": path,
                "has_token": bool(token),
                "token_length": len(token) if token else 0,
                "token_source": "header" if (auth_header and auth_header.startswith("Bearer ")) else "cookie" if cookie_token else "none",
                "token_prefix": token[:30] + "..." if token else None,
            },
            "timestamp": int(__import__("time").time() * 1000),
            "sessionId": "debug-session",
            "runId": "run3",
            "hypothesisId": "F"
        }
        logger.info(f"AUTH_MIDDLEWARE_TOKEN: {json.dumps(log_data)}")
        try:
            with open("/Users/atul7717/Desktop/Code/aird/.cursor/debug.log", "a") as f:
                f.write(json.dumps(log_data) + "\n")
        except Exception as e:
            logger.error(f"Failed to write debug log: {e}")
        # #endregion
        
        if not token:
            
            # Ensure CORS headers are included in error response
            # Get allowed origins from settings
            cors_origins = self.settings.CORS_ORIGINS
            if isinstance(cors_origins, str):
                cors_origins = [cors_origins]
            elif not isinstance(cors_origins, list):
                cors_origins = list(cors_origins) if cors_origins else []
            
            origin = request.headers.get("origin")
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Authentication required"},
                headers={"WWW-Authenticate": "Bearer"},
            )
            # Add CORS headers if origin is in allowed list
            if origin and (origin in cors_origins or "*" in cors_origins):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response

        # Verify token (already extracted above)
        payload = verify_rs256_token(token)
        
        # #region agent log
        import logging
        logger = logging.getLogger(__name__)
        log_data = {
            "location": "auth_middleware.py:96",
            "message": "Token verification result",
            "data": {
                "path": path,
                "token_valid": bool(payload),
                "has_payload": bool(payload),
                "payload_keys": list(payload.keys()) if payload else [],
            },
            "timestamp": int(__import__("time").time() * 1000),
            "sessionId": "debug-session",
            "runId": "run3",
            "hypothesisId": "F"
        }
        logger.info(f"AUTH_MIDDLEWARE_VERIFY: {json.dumps(log_data)}")
        try:
            with open("/Users/atul7717/Desktop/Code/aird/.cursor/debug.log", "a") as f:
                f.write(json.dumps(log_data) + "\n")
        except Exception as e:
            logger.error(f"Failed to write debug log: {e}")
        # #endregion
        
        if not payload:
            
            # Ensure CORS headers are included in error response
            # Get allowed origins from settings
            cors_origins = self.settings.CORS_ORIGINS
            if isinstance(cors_origins, str):
                cors_origins = [cors_origins]
            elif not isinstance(cors_origins, list):
                cors_origins = list(cors_origins) if cors_origins else []
            
            origin = request.headers.get("origin")
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )
            # Add CORS headers if origin is in allowed list
            if origin and (origin in cors_origins or "*" in cors_origins):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response

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
