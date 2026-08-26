"""
Standalone Supabase JWT verification for the customer service agent.

Deliberately independent of the website's backend code -- this agent is a
separate deployable service, so it carries its own copy of JWT verification
rather than importing from the site's repo.
"""
from __future__ import annotations

import os
from functools import lru_cache

import jwt
from jwt import PyJWKClient

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_JWKS_URL = os.environ.get(
    "SUPABASE_JWKS_URL",
    f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else "",
)


@lru_cache(maxsize=1)
def _get_jwk_client() -> PyJWKClient:
    if not SUPABASE_JWKS_URL:
        raise RuntimeError("SUPABASE_URL or SUPABASE_JWKS_URL must be set.")
    return PyJWKClient(SUPABASE_JWKS_URL, cache_keys=True, cache_jwk_set=True)


def verify_token(token: str) -> dict | None:
    """
    Verify a Supabase JWT. Returns the decoded payload on success, or None
    if the token is missing, malformed, or invalid -- callers should treat
    None as "anonymous", not raise, since the agent supports guest chat.
    """
    if not token:
        return None
    try:
        jwk_client = _get_jwk_client()
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
        )
        return payload
    except Exception:
        return None


def get_customer_email(authorization_header: str | None) -> str | None:
    """
    Extract the verified customer email from an `Authorization: Bearer <token>`
    header. Returns None for anonymous/invalid requests -- never raises, so
    a bad token just degrades to guest mode rather than breaking the chat.
    """
    if not authorization_header or not authorization_header.lower().startswith("bearer "):
        return None
    token = authorization_header.split(" ", 1)[1].strip()
    payload = verify_token(token)
    if not payload:
        return None
    email = (payload.get("email") or "").strip().lower()
    return email or None
