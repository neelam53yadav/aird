"""
NextAuth token verification module.
"""

import jwt
import base64
import json
from typing import Dict, Any, Optional
from primedata.core.settings import get_settings

try:
    from jose import jwe
    from jose.constants import ALGORITHMS
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.backends import default_backend
    import hashlib

    JWE_AVAILABLE = True
except ImportError:
    JWE_AVAILABLE = False


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
                logger.info("Token is a JWE (encrypted JWT). Attempting to decrypt...")

                if not JWE_AVAILABLE:
                    logger.error("python-jose is not available. Cannot decrypt JWE tokens.")
                    logger.error("Please install: pip install python-jose[cryptography]")
                    return None

                # Decrypt the JWE token
                # NextAuth uses "dir" algorithm with A256GCM encryption
                # Format can be:
                # - 5 parts: header.encrypted_key.iv.ciphertext.tag (standard JWE)
                # - 4 parts: header..combined_iv_ciphertext_tag (NextAuth compact format)
                try:
                    if num_parts == 4:
                        # NextAuth compact JWE format: header..iv.ciphertext+tag
                        # Format: header.empty_key.iv.ciphertext+tag
                        logger.info("Detected NextAuth compact JWE format (4 parts)")
                        logger.debug(f"Token parts lengths: {[len(p) for p in token_parts]}")

                        jwe_header = token_parts[0]
                        encrypted_key_part = token_parts[1]  # Empty for "dir" algorithm
                        iv_part = token_parts[2]  # IV (base64url encoded)
                        ciphertext_tag_part = token_parts[3]  # Ciphertext + Tag (base64url encoded, combined)

                        # Decode IV
                        iv_bytes = base64.urlsafe_b64decode(iv_part + "=" * (4 - len(iv_part) % 4))
                        logger.debug(f"IV length: {len(iv_bytes)} bytes (expected 12 for GCM)")

                        # Decode ciphertext+tag
                        ciphertext_tag_bytes = base64.urlsafe_b64decode(
                            ciphertext_tag_part + "=" * (4 - len(ciphertext_tag_part) % 4)
                        )
                        logger.debug(f"Ciphertext+Tag length: {len(ciphertext_tag_bytes)} bytes")

                        # For AES-256-GCM:
                        # - Tag is last 16 bytes
                        # - Ciphertext is the rest
                        tag_length = 16
                        if len(ciphertext_tag_bytes) < tag_length:
                            logger.error(
                                f"Ciphertext+tag too short: {len(ciphertext_tag_bytes)} bytes, need at least {tag_length}"
                            )
                            return None

                        tag_bytes = ciphertext_tag_bytes[-tag_length:]
                        ciphertext_bytes = ciphertext_tag_bytes[:-tag_length]

                        logger.info(
                            f"Extracted - IV: {len(iv_bytes)} bytes, Ciphertext: {len(ciphertext_bytes)} bytes, Tag: {len(tag_bytes)} bytes"
                        )

                        # Derive 32-byte key from NEXTAUTH_SECRET
                        # NextAuth uses SHA-256 of the secret for "dir" algorithm with A256GCM
                        secret = settings.NEXTAUTH_SECRET
                        if isinstance(secret, str):
                            secret_bytes = secret.encode("utf-8")
                        else:
                            secret_bytes = secret

                        # Derive 32-byte key using SHA-256 (NextAuth standard)
                        key = hashlib.sha256(secret_bytes).digest()
                        logger.info("=" * 60)
                        logger.info("🔑 KEY DERIVATION INFO")
                        logger.info("=" * 60)
                        logger.info(f"Secret (NEXTAUTH_SECRET):")
                        logger.info(f"  - Length: {len(secret_bytes)} bytes")
                        logger.info(f"  - First 10 chars: {secret[:10]}...")
                        logger.info(f"  - Last 10 chars: ...{secret[-10:]}")
                        logger.info(f"Derived Key (SHA-256 of secret):")
                        logger.info(f"  - Length: {len(key)} bytes (32 bytes for AES-256)")
                        logger.info(f"  - First 8 bytes (hex): {key[:8].hex()}")
                        logger.info("=" * 60)

                        # Combine ciphertext and tag for AES-GCM decryption
                        encrypted_data = ciphertext_bytes + tag_bytes

                        # Decrypt using AES-256-GCM
                        aesgcm = AESGCM(key)
                        decrypted_payload = aesgcm.decrypt(iv_bytes, encrypted_data, None)

                        # The decrypted payload should be a JWT (3 parts)
                        token = decrypted_payload.decode("utf-8")
                        logger.info("JWE token decrypted successfully (4-part format)")
                        token_parts = token.split(".")
                        num_parts = len(token_parts)

                    elif num_parts == 5:
                        # Standard JWE format: header.encrypted_key.iv.ciphertext.tag
                        logger.info("Detected standard JWE format (5 parts)")
                        logger.info(f"Token parts lengths: {[len(p) for p in token_parts]}")

                        jwe_header = token_parts[0]
                        encrypted_key = token_parts[1]  # Empty for "dir" algorithm
                        iv = token_parts[2]
                        ciphertext = token_parts[3]
                        tag = token_parts[4]

                        logger.info(
                            f"JWE parts - Header: {len(jwe_header)}, Key: {len(encrypted_key)}, IV: {len(iv)}, Ciphertext: {len(ciphertext)}, Tag: {len(tag)}"
                        )

                        # Try using python-jose library first (handles NextAuth format correctly)
                        secret = settings.NEXTAUTH_SECRET
                        if isinstance(secret, str):
                            secret_bytes = secret.encode("utf-8")
                        else:
                            secret_bytes = secret

                        logger.info("=" * 60)
                        logger.info("🔑 KEY DERIVATION INFO (5-part format)")
                        logger.info("=" * 60)
                        logger.info(f"Secret (NEXTAUTH_SECRET):")
                        logger.info(f"  - Length: {len(secret_bytes)} bytes")
                        logger.info(f"  - First 10 chars: {secret[:10]}...")
                        logger.info(f"  - Last 10 chars: ...{secret[-10:]}")

                        # Try jose library first (should handle NextAuth format)
                        try:
                            from jose import jwe

                            # For "dir" algorithm, NextAuth might use the secret directly or derive it
                            # Try SHA-256 derivation first (most common)
                            key_sha256 = hashlib.sha256(secret_bytes).digest()
                            logger.info(f"Trying jose.decrypt with SHA-256 derived key...")
                            logger.info(f"  - Key length: {len(key_sha256)} bytes")
                            logger.info(f"  - Key first 8 bytes (hex): {key_sha256[:8].hex()}")

                            decrypted_payload = jwe.decrypt(token, key_sha256)
                            token = decrypted_payload.decode("utf-8")
                            logger.info("✅ JWE token decrypted successfully using jose library (SHA-256 key)")
                            token_parts = token.split(".")
                            num_parts = len(token_parts)
                        except Exception as jose_error:
                            logger.warning(f"jose library decryption failed: {jose_error}")
                            logger.info("Trying manual decryption with different key methods...")

                            # Decode base64url parts
                            iv_bytes = base64.urlsafe_b64decode(iv + "=" * (4 - len(iv) % 4))
                            ciphertext_bytes = base64.urlsafe_b64decode(ciphertext + "=" * (4 - len(ciphertext) % 4))
                            tag_bytes = base64.urlsafe_b64decode(tag + "=" * (4 - len(tag) % 4))

                            logger.info(
                                f"Decoded - IV: {len(iv_bytes)} bytes, Ciphertext: {len(ciphertext_bytes)} bytes, Tag: {len(tag_bytes)} bytes"
                            )

                            # Method 1: SHA-256 (standard for NextAuth)
                            key_sha256 = hashlib.sha256(secret_bytes).digest()
                            logger.info(f"Method 1 - SHA-256 derived key:")
                            logger.info(f"  - Length: {len(key_sha256)} bytes")
                            logger.info(f"  - First 8 bytes (hex): {key_sha256[:8].hex()}")

                            # Try decryption with SHA-256 derived key
                            encrypted_data = ciphertext_bytes + tag_bytes
                            aesgcm = AESGCM(key_sha256)

                            # For JWE, AAD (Additional Authenticated Data) is the base64url-encoded header
                            aad = jwe_header.encode("utf-8")

                            try:
                                decrypted_payload = aesgcm.decrypt(iv_bytes, encrypted_data, aad)
                                token = decrypted_payload.decode("utf-8")
                                logger.info("✅ JWE token decrypted successfully using SHA-256 derived key")
                                token_parts = token.split(".")
                                num_parts = len(token_parts)
                            except Exception as decrypt_error:
                                logger.warning(f"Decryption with SHA-256 key failed: {decrypt_error}")
                                last_error = decrypt_error

                                # Method 2: Try SHA-256 of secret string (not bytes)
                                try:
                                    key_str_sha256 = hashlib.sha256(secret.encode("utf-8")).digest()
                                    logger.info("=" * 60)
                                    logger.info("🔑 Trying Method 2: SHA-256 of secret string")
                                    logger.info("=" * 60)
                                    logger.info(f"  - Key length: {len(key_str_sha256)} bytes")
                                    logger.info(f"  - Key first 8 bytes (hex): {key_str_sha256[:8].hex()}")

                                    aesgcm = AESGCM(key_str_sha256)
                                    aad = jwe_header.encode("utf-8")
                                    decrypted_payload = aesgcm.decrypt(iv_bytes, encrypted_data, aad)
                                    token = decrypted_payload.decode("utf-8")
                                    logger.info("✅ SUCCESS: JWE decrypted using Method 2")
                                    token_parts = token.split(".")
                                    num_parts = len(token_parts)
                                except Exception as e2:
                                    logger.warning(f"Method 2 failed: {str(e2)}")

                                    # Method 3: Try using secret directly if it's 32 bytes
                                    e3 = None
                                    if len(secret_bytes) == 32:
                                        try:
                                            logger.info("=" * 60)
                                            logger.info("🔑 Trying Method 3: Direct secret (32 bytes)")
                                            logger.info("=" * 60)
                                            logger.info(f"  - Key first 8 bytes (hex): {secret_bytes[:8].hex()}")

                                            aesgcm_direct = AESGCM(secret_bytes)
                                            aad = jwe_header.encode("utf-8")
                                            decrypted_payload = aesgcm_direct.decrypt(iv_bytes, encrypted_data, aad)
                                            token = decrypted_payload.decode("utf-8")
                                            logger.info("✅ SUCCESS: JWE decrypted using Method 3")
                                            token_parts = token.split(".")
                                            num_parts = len(token_parts)
                                        except Exception as e3_exc:
                                            e3 = e3_exc
                                            logger.warning(f"Method 3 failed: {str(e3)}")
                                            last_error = e3

                                    # Method 4: Try base64url decoding the secret
                                    if num_parts != 3:
                                        try:
                                            # NextAuth might store secret as base64url
                                            secret_b64url_decoded = base64.urlsafe_b64decode(secret + "==")
                                            if len(secret_b64url_decoded) >= 32:
                                                key_b64url = secret_b64url_decoded[:32]
                                                logger.info("=" * 60)
                                                logger.info("🔑 Trying Method 4: Base64URL decoded secret")
                                                logger.info("=" * 60)
                                                logger.info(f"  - Key length: {len(key_b64url)} bytes")
                                                logger.info(f"  - Key first 8 bytes (hex): {key_b64url[:8].hex()}")

                                                aesgcm = AESGCM(key_b64url)
                                                aad = jwe_header.encode("utf-8")
                                                decrypted_payload = aesgcm.decrypt(iv_bytes, encrypted_data, aad)
                                                token = decrypted_payload.decode("utf-8")
                                                logger.info("✅ SUCCESS: JWE decrypted using Method 4")
                                                token_parts = token.split(".")
                                                num_parts = len(token_parts)
                                        except Exception as e4:
                                            logger.warning(f"Method 4 failed: {str(e4)}")

                                            # Method 5: Try base64 decoding
                                            try:
                                                secret_b64_decoded = base64.b64decode(secret + "==")
                                                if len(secret_b64_decoded) >= 32:
                                                    key_b64 = secret_b64_decoded[:32]
                                                    logger.info("=" * 60)
                                                    logger.info("🔑 Trying Method 5: Base64 decoded secret")
                                                    logger.info("=" * 60)
                                                    logger.info(f"  - Key length: {len(key_b64)} bytes")
                                                    logger.info(f"  - Key first 8 bytes (hex): {key_b64[:8].hex()}")

                                                    aesgcm = AESGCM(key_b64)
                                                    aad = jwe_header.encode("utf-8")
                                                    decrypted_payload = aesgcm.decrypt(iv_bytes, encrypted_data, aad)
                                                    token = decrypted_payload.decode("utf-8")
                                                    logger.info("✅ SUCCESS: JWE decrypted using Method 5")
                                                    token_parts = token.split(".")
                                                    num_parts = len(token_parts)
                                            except Exception as e5:
                                                logger.error("=" * 60)
                                                logger.error("❌ ALL DECRYPTION METHODS FAILED")
                                                logger.error("=" * 60)
                                                logger.error("Tried methods:")
                                                logger.error(f"  1. SHA-256(bytes): {decrypt_error}")
                                                logger.error(f"  2. SHA-256(string): {e2}")
                                                if len(secret_bytes) == 32:
                                                    e3_str = str(e3) if e3 is not None else "N/A"
                                                    logger.error(f"  3. Direct 32-byte: {e3_str}")
                                                logger.error(f"  4. Base64URL decode: {e4}")
                                                logger.error(f"  5. Base64 decode: {e5}")
                                                logger.error("")
                                                logger.error("This strongly suggests NEXTAUTH_SECRET mismatch!")
                                                logger.error("Even if they look the same, check for:")
                                                logger.error("  - Hidden characters (spaces, newlines)")
                                                logger.error("  - Different encoding")
                                                logger.error("  - Old token encrypted with different secret")
                                                logger.error("")
                                                logger.error(
                                                    "SOLUTION: Clear browser cookies and sign in again with matching secrets"
                                                )
                                                raise last_error if last_error else e5

                                    if num_parts != 3:
                                        raise last_error if last_error else Exception("All decryption methods failed")

                        logger.info("=" * 60)
                    else:
                        logger.error(f"JWE token should have 4 or 5 parts, got {num_parts}")
                        return None
                except Exception as e:
                    logger.error("=" * 60)
                    logger.error("❌ JWE DECRYPTION FAILED")
                    logger.error("=" * 60)
                    logger.error(f"Error: {str(e)}")
                    logger.error(f"Error type: {type(e).__name__}")
                    logger.error("")
                    logger.error("This might indicate:")
                    logger.error("  1. NEXTAUTH_SECRET doesn't match between frontend and backend")
                    logger.error("  2. Key derivation method is incorrect")
                    logger.error("  3. Token encryption format is not supported")
                    logger.error("")
                    logger.error("Debugging info:")
                    logger.error(f"  - Secret length: {len(settings.NEXTAUTH_SECRET)} characters")
                    logger.error(f"  - Secret first 10: {settings.NEXTAUTH_SECRET[:10]}...")
                    logger.error(f"  - Secret last 10: ...{settings.NEXTAUTH_SECRET[-10:]}")
                    logger.error(f"  - Token parts: {num_parts}")
                    if num_parts >= 3:
                        logger.error(f"  - IV part length: {len(token_parts[2])}")
                        logger.error(f"  - Ciphertext part length: {len(token_parts[3]) if num_parts > 3 else 'N/A'}")
                        logger.error(f"  - Tag part length: {len(token_parts[4]) if num_parts > 4 else 'N/A'}")
                    logger.error("")
                    logger.error("Full traceback:")
                    import traceback

                    logger.error(traceback.format_exc())
                    logger.error("=" * 60)
                    return None

            # After decryption (if JWE), we should have a JWT with 3 parts
            if num_parts != 3:
                logger.error(f"Token doesn't appear to be a valid JWT after processing (expected 3 parts, got {num_parts})")
                logger.error(f"Token preview (first 50 chars): {token[:50] if token else 'None'}")
                return None

            # Get the algorithm from the (possibly decrypted) token
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
