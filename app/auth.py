"""
Authentication: Apple Sign In + development bypass.

Production flow
---------------
1. The frontend loads Apple's JS SDK and shows a "Sign in with Apple" button.
2. The user authenticates; Apple returns an ``identityToken`` (a signed JWT)
   and (optionally) a ``user`` object with name/email on the first sign-in.
3. The frontend POSTs ``{ identity_token, user }`` to ``/auth/apple/verify``.
4. This module validates the JWT against Apple's published public keys, then
   writes the Apple subject (``sub``) into the Flask session.

Development bypass
------------------
Set ``DEV_AUTH_BYPASS=1`` in your environment (or .env file).
When active, every request is treated as authenticated with a synthetic user
identity – no Apple credentials are required.  This flag never appears in
production config.

Apple credentials needed in .env (production only)
---------------------------------------------------
APPLE_CLIENT_ID   – the Services ID or App Bundle ID registered with Apple
APPLE_TEAM_ID     – your 10-character Apple Developer Team ID
"""

import os
import time
from functools import wraps

import jwt
import requests
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.backends import default_backend
from flask import session, jsonify, request
import base64
import json

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

# Simple in-process cache: (keys_dict, fetched_at_unix_ts)
_jwks_cache: tuple[dict, float] = ({}, 0.0)
_JWKS_TTL = 3600  # re-fetch keys once per hour


def _fetch_apple_keys() -> dict:
    """Return Apple's current JWKS as a ``{kid: public_key}`` dict.

    Keys are cached in memory for one hour to avoid hammering Apple's endpoint.
    """
    global _jwks_cache
    keys, fetched_at = _jwks_cache
    if time.time() - fetched_at < _JWKS_TTL and keys:
        return keys

    resp = requests.get(APPLE_JWKS_URL, timeout=10)
    resp.raise_for_status()
    jwks = resp.json()

    def _b64_to_int(b64: str) -> int:
        # URL-safe base64 without padding
        padding = "=" * (-len(b64) % 4)
        raw = base64.urlsafe_b64decode(b64 + padding)
        return int.from_bytes(raw, "big")

    result: dict = {}
    for key_data in jwks.get("keys", []):
        if key_data.get("kty") != "RSA":
            continue
        n = _b64_to_int(key_data["n"])
        e = _b64_to_int(key_data["e"])
        pub_numbers = RSAPublicNumbers(e, n)
        pub_key = pub_numbers.public_key(default_backend())
        result[key_data["kid"]] = pub_key

    _jwks_cache = (result, time.time())
    return result


def verify_apple_token(identity_token: str) -> dict:
    """Validate an Apple identity token and return its claims.

    Raises ValueError with a human-readable message on validation failure so
    the caller can forward it to the client.
    """
    client_id = os.environ.get("APPLE_CLIENT_ID", "")

    # Peek at the header to find which key to use.
    try:
        header = jwt.get_unverified_header(identity_token)
    except jwt.exceptions.DecodeError as exc:
        raise ValueError(f"Malformed token header: {exc}") from exc

    kid = header.get("kid")
    keys = _fetch_apple_keys()
    pub_key = keys.get(kid)
    if pub_key is None:
        raise ValueError(f"Unknown key id '{kid}' – Apple may have rotated keys")

    try:
        claims = jwt.decode(
            identity_token,
            pub_key,
            algorithms=["RS256"],
            audience=client_id if client_id else None,
            issuer=APPLE_ISSUER,
            options={"verify_aud": bool(client_id)},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise ValueError(f"Token validation failed: {exc}") from exc

    return claims


def dev_bypass_active() -> bool:
    """Return True when the development auth bypass is enabled."""
    return os.environ.get("DEV_AUTH_BYPASS", "").strip() in ("1", "true", "yes")


def is_authenticated() -> bool:
    """Return True if the current request belongs to an authenticated user."""
    if dev_bypass_active():
        return True
    return "user_sub" in session


def require_auth(f):
    """Decorator: reject unauthenticated requests with 401 JSON response."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_authenticated():
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated


def current_user() -> dict:
    """Return a dict describing the current user.

    In dev-bypass mode a synthetic identity is returned so callers don't have
    to handle the None case.
    """
    if dev_bypass_active():
        return {"sub": "dev-user", "email": "dev@local", "name": "Dev User"}
    return {
        "sub": session.get("user_sub", ""),
        "email": session.get("user_email", ""),
        "name": session.get("user_name", ""),
    }
