"""
NextAuth token verification module.
"""

import base64
import json
from typing import Any, Dict, Optional

import jwt
from primedata.core.settings import get_settings

try:
    import hashlib
    import time

    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from jose import jwe
    from jose.constants import ALGORITHMS

    JWE_AVAILABLE = True
except ImportError:
    JWE_AVAILABLE = False


# NextAuth.js uses HKDF with this specific info string for JWE key derivation
NEXTAUTH_INFO = b"NextAuth.js Generated Encryption Key"


def _b64url_decode(s: str) -> bytes:
    """Decode base64url string to bytes."""
    s = s + "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def derive_nextauth_jwe_key(secret: str, salt: str = "") -> bytes:
    """
    NextAuth derives the CEK using HKDF(SHA-256) with info 'NextAuth.js Generated Encryption Key'.
    This matches NextAuth.js's key derivation method exactly.
    """
    secret_bytes = secret.encode("utf-8")
    salt_bytes = salt.encode("utf-8") if salt else b""
    
    info = NEXTAUTH_INFO
    
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # A256GCM needs 32 bytes
        salt=salt_bytes,
        info=info,
    )
    return hkdf.derive(secret_bytes)


def decrypt_nextauth_session_jwe(token: str, secret: str) -> Dict[str, Any]:
    """
    Decrypt NextAuth JWE (compact) and return payload dict.
    Tries common salt variants because deployments differ.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Common salt candidates
    salt_candidates = [
        "",  # often works
        "next-auth.session-token",
        "__Secure-next-auth.session-token",
        "authjs.session-token",
        "__Secure-authjs.session-token",
    ]
    
    last_err = None
    for salt in salt_candidates:
        try:
            key = derive_nextauth_jwe_key(secret, salt=salt)
            logger.info(f"Trying HKDF key derivation with salt: '{salt}'")
            
            # Try python-jose directly first
            plaintext = jwe.decrypt(token, key)  # returns bytes
            try:
                payload = json.loads(plaintext.decode("utf-8"))
                logger.info(f"✅ JWE decrypted successfully with salt: '{salt}'")
                return payload
            except json.JSONDecodeError:
                # In rare cases plaintext might be another JWT string
                txt = plaintext.decode("utf-8", errors="ignore")
                logger.warning(f"Decrypted payload is not JSON, treating as raw text")
                return {"_raw": txt}
        except Exception as e:
            logger.debug(f"Decryption failed with salt '{salt}': {str(e)}")
            last_err = e
    
    raise last_err if last_err else Exception("All HKDF salt variants failed")


def verify_nextauth_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify HS256 NextAuth token using NEXTAUTH_SECRET.

    Args:
        token: The JWT token to verify

    Returns:
        Normalized claims dict with email, name, picture, provider, google_sub
        or None if verification fails
    """
    import logging

    logger = logging.getLogger(__name__)

    settings = get_settings()

    # Validate that NEXTAUTH_SECRET is set and not default
    if (
        not settings.NEXTAUTH_SECRET
        or settings.NEXTAUTH_SECRET == "REPLACE_WITH_64_CHAR_RANDOM_STRING_FOR_PRODUCTION_USE_ONLY"
    ):
        logger.error("NEXTAUTH_SECRET is not set or using default value. Please set NEXTAUTH_SECRET in backend .env file.")
        logger.error("The NEXTAUTH_SECRET must match the value in ui/.env.local")
        return None

    # Log secret info for debugging (first 10 chars only for security)
    logger.info(f"Backend NEXTAUTH_SECRET info:")
    logger.info(f"  - Length: {len(settings.NEXTAUTH_SECRET)} characters")
    logger.info(f"  - First 10 chars: {settings.NEXTAUTH_SECRET[:10]}...")
    logger.info(f"  - Last 10 chars: ...{settings.NEXTAUTH_SECRET[-10:]}")
    logger.info(f"  - Key derived length: {len(hashlib.sha256(settings.NEXTAUTH_SECRET.encode('utf-8')).digest())} bytes")

    try:
        # Check token format - JWT has 3 parts, JWE has 5 parts
        if not token:
            logger.error("Token is empty")
            return None

        token_parts = token.split(".")
        num_parts = len(token_parts)

        # Decode the header to determine token type
        try:
            header_part = token_parts[0]
            # Add padding if needed for base64 decoding
            padding = 4 - len(header_part) % 4
            if padding != 4:
                header_part += "=" * padding

            header_json = base64.urlsafe_b64decode(header_part)
            header = json.loads(header_json)

            token_algorithm = header.get("alg")
            token_encryption = header.get("enc")

            logger.info(
                f"Token type detected - Parts: {num_parts}, Algorithm: {token_algorithm}, Encryption: {token_encryption}"
            )
            logger.debug(f"Token header: {header}")

            # Check if this is a JWE (encrypted JWT) - NextAuth v4+ uses encrypted tokens
            if token_encryption or token_algorithm == "dir":
                logger.info("Token is a JWE (encrypted JWT). Attempting to decrypt with HKDF...")

                if not JWE_AVAILABLE:
                    logger.error("python-jose is not available. Cannot decrypt JWE tokens.")
                    logger.error("Please install: pip install python-jose[cryptography]")
                    return None

                # Decrypt the JWE token using HKDF (NextAuth.js standard)
                # NextAuth uses "dir" algorithm with A256GCM encryption
                # The decrypted payload is JSON, not a JWT string
                try:
                    # Use HKDF-based decryption (NextAuth.js standard)
                    payload = decrypt_nextauth_session_jwe(token, settings.NEXTAUTH_SECRET)
                    
                    # Validate expiration
                    now = int(time.time())
                    exp = payload.get("exp")
                    if exp and int(exp) < now:
                        logger.warning("Token has expired")
                        return None
                    
                    # Extract claims directly from JSON payload
                    claims = {
                        "email": payload.get("email"),
                        "name": payload.get("name"),
                        "picture": payload.get("picture"),
                        "provider": payload.get("provider"),
                        "google_sub": payload.get("google_sub"),
                        "sub": payload.get("sub"),
                        "iat": payload.get("iat"),
                        "exp": payload.get("exp"),
                        "iss": payload.get("iss"),
                    }
                    
                    # Validate required fields
                    if not claims["email"]:
                        logger.warning("Token decoded but missing required 'email' field")
                        return None
                    
                    logger.info(f"✅ JWE token decrypted and verified successfully for user: {claims['email']}")
                    return claims
                    
                except Exception as e:
                    logger.error("=" * 60)
                    logger.error("❌ JWE DECRYPTION FAILED (HKDF)")
                    logger.error("=" * 60)
                    logger.error(f"Error: {str(e)}")
                    logger.error(f"Error type: {type(e).__name__}")
                    logger.error("")
                    logger.error("This might indicate:")
                    logger.error("  1. NEXTAUTH_SECRET doesn't match between frontend and backend")
                    logger.error("  2. Token encryption format is not supported")
                    logger.error("  3. Token was encrypted with a different secret")
                    logger.error("")
                    logger.error("Debugging info:")
                    logger.error(f"  - Secret length: {len(settings.NEXTAUTH_SECRET)} characters")
                    logger.error(f"  - Secret first 10: {settings.NEXTAUTH_SECRET[:10]}...")
                    logger.error(f"  - Secret last 10: ...{settings.NEXTAUTH_SECRET[-10:]}")
                    logger.error(f"  - Token parts: {len(token.split('.'))}")
                    logger.error("")
                    logger.error("Full traceback:")
                    import traceback

                    logger.error(traceback.format_exc())
                    logger.error("=" * 60)
                    return None

            # If token is not JWE, continue with JWT verification below
            # (JWE tokens return early above)

            # Verify non-JWE tokens (regular JWT)
            # Check token format - JWT has 3 parts
            if num_parts != 3:
                logger.error(f"Token doesn't appear to be a valid JWT (expected 3 parts, got {num_parts})")
                logger.error(f"Token preview (first 50 chars): {token[:50] if token else 'None'}")
                return None

            # Get the algorithm from the token
            unverified_header = jwt.get_unverified_header(token)
            token_algorithm = unverified_header.get("alg")
            logger.info(f"JWT algorithm in header: {token_algorithm}")

            # Check if algorithm is supported (NextAuth uses HS256)
            if token_algorithm not in ["HS256", "HS384", "HS512"]:
                logger.error(f"Token uses unsupported algorithm: {token_algorithm}. Expected HS256/HS384/HS512")
                logger.error(f"Full token header: {unverified_header}")
                return None

        except Exception as e:
            logger.error(f"Failed to decode token header: {str(e)}")
            logger.error("Token might not be a valid JWT or JWE")
            logger.error(f"Token preview (first 100 chars): {token[:100] if token else 'None'}")
            return None

        # Decode and verify the token
        # NextAuth uses HS256 by default, but we'll try multiple algorithms for compatibility
        # Try the algorithm from the token header first, then fallback to HS256
        allowed_algorithms = []
        if token_algorithm in ["HS256", "HS384", "HS512"]:
            allowed_algorithms = [token_algorithm]
        else:
            # If algorithm is not in expected list, try all HMAC algorithms
            allowed_algorithms = ["HS256", "HS384", "HS512"]
            logger.warning(f"Token algorithm '{token_algorithm}' not in expected list, trying all HMAC algorithms")

        payload = jwt.decode(
            token,
            settings.NEXTAUTH_SECRET,
            algorithms=allowed_algorithms,
            options={
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
            },
        )

        logger.debug(f"Token decoded successfully. Payload keys: {list(payload.keys())}")

        # Check issuer if configured
        if settings.API_SESSION_EXCHANGE_ALLOWED_ISS:
            token_iss = payload.get("iss")
            if token_iss != settings.API_SESSION_EXCHANGE_ALLOWED_ISS:
                logger.warning(
                    f"Issuer mismatch. Token issuer: {token_iss}, Expected: {settings.API_SESSION_EXCHANGE_ALLOWED_ISS}"
                )
                return None

        # Extract and normalize claims
        claims = {
            "email": payload.get("email"),
            "name": payload.get("name"),
            "picture": payload.get("picture"),
            "provider": payload.get("provider"),
            "google_sub": payload.get("google_sub"),
            "sub": payload.get("sub"),
            "iat": payload.get("iat"),
            "exp": payload.get("exp"),
            "iss": payload.get("iss"),
        }

        # Validate required fields
        if not claims["email"]:
            logger.warning("Token decoded but missing required 'email' field")
            return None

        logger.debug(f"Token verified successfully for user: {claims['email']}")
        return claims

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidSignatureError:
        logger.error(
            "Token signature is invalid. This usually means NEXTAUTH_SECRET doesn't match between frontend and backend."
        )
        logger.error(f"Backend NEXTAUTH_SECRET length: {len(settings.NEXTAUTH_SECRET)}")
        logger.error("Please ensure NEXTAUTH_SECRET in backend/.env matches NEXTAUTH_SECRET in ui/.env.local")
        return None
    except jwt.DecodeError as e:
        logger.error(f"Token decode error: {str(e)}")
        logger.error("This might indicate the token format is incorrect or NEXTAUTH_SECRET is wrong")
        return None
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {str(e)}", exc_info=True)
        return None
