"""OAuth 2.0 authorization-code + PKCE against Kanidm for the desktop/CLI app.

Kanidm v1.10.x stable does not expose the device-authorization-grant endpoint
(the `dev-oauth2-device-flow` Cargo feature is non-default and marked as
still-in-development), so the native-app flow uses RFC 6749 + RFC 7636 + RFC
8252: open the system browser, capture the code on a loopback redirect, and
exchange the code for an access token at the token endpoint.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient

from app.config import (
    KANIDM_CLIENT_ID,
    KANIDM_CLIENT_SECRET,
    KANIDM_REDIRECT_URI,
    KANIDM_SCOPE,
    KANIDM_URL,
)

_PENDING_TTL_SECONDS = 600
_AUTHORIZE_PATH = "/ui/oauth2"
_TOKEN_PATH = "/oauth2/token"
_JWT_ALGORITHMS = ["ES256"]
_JWKS_CACHE_TTL = 600

Status = Literal["pending", "authorized", "error"]

_jwks_client: PyJWKClient | None = None
_jwks_client_at: float = 0.0
_jwks_client_lock = threading.Lock()


def _pkce_pair() -> tuple[str, str]:
    """Return a (code_verifier, code_challenge) S256 pair per RFC 7636."""
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _get_jwks_client() -> PyJWKClient:
    """Return a cached PyJWKClient pointed at the configured Kanidm client's JWKS endpoint."""
    global _jwks_client, _jwks_client_at
    with _jwks_client_lock:
        now = time.monotonic()
        if _jwks_client is not None and now - _jwks_client_at < _JWKS_CACHE_TTL:
            return _jwks_client
        if not KANIDM_URL or not KANIDM_CLIENT_ID:
            raise RuntimeError("KANIDM_URL and KANIDM_CLIENT_ID must be configured")
        jwks_uri = f"{KANIDM_URL}/oauth2/openid/{KANIDM_CLIENT_ID}/public_key.jwk"
        _jwks_client = PyJWKClient(jwks_uri, cache_keys=True, lifespan=_JWKS_CACHE_TTL)
        _jwks_client_at = now
        return _jwks_client


def validate_kanidm_jwt(token: str) -> dict | None:
    """Verify *token*'s ES256 signature against Kanidm's JWKS and return its claims, or None.

    The desktop client does not round-trip the token through shenas.ai for
    validation: it owns the trust relationship with Kanidm directly. Audience
    is not enforced here -- Kanidm sets `aud` to the client_id, and we know we
    requested the token ourselves, so signature + expiry is sufficient.
    """
    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        return jwt.decode(token, signing_key.key, algorithms=_JWT_ALGORITHMS, options={"verify_aud": False})
    except Exception:
        return None


def fetch_userinfo(access_token: str) -> dict | None:
    """Fetch OIDC userinfo for *access_token* and return the claims dict, or None.

    Identity claims (`email`, `name`, `preferred_username`, `picture`) live on
    the userinfo endpoint per OIDC -- access tokens carry only `sub` plus
    standard JWT claims. Caller is expected to have already validated the
    token's signature via `validate_kanidm_jwt`.
    """
    if not KANIDM_URL or not KANIDM_CLIENT_ID:
        return None
    try:
        resp = httpx.get(
            f"{KANIDM_URL}/oauth2/openid/{KANIDM_CLIENT_ID}/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
            verify=False,
        )
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


@dataclass
class PendingAuth:
    """Server-side state for an in-flight authorization-code request."""

    code_verifier: str
    redirect_uri: str
    created_at: float = field(default_factory=time.monotonic)
    status: Status = "pending"
    error: str | None = None
    access_token: str | None = None


class PendingAuthStore:
    """Module-singleton, thread-safe store keyed by the OAuth2 `state` value."""

    def __init__(self) -> None:
        self._entries: dict[str, PendingAuth] = {}
        self._lock = threading.Lock()

    def put(self, state: str, entry: PendingAuth) -> None:
        with self._lock:
            self._gc_locked()
            self._entries[state] = entry

    def get(self, state: str) -> PendingAuth | None:
        with self._lock:
            self._gc_locked()
            return self._entries.get(state)

    def pop(self, state: str) -> PendingAuth | None:
        with self._lock:
            self._gc_locked()
            return self._entries.pop(state, None)

    def _gc_locked(self) -> None:
        cutoff = time.monotonic() - _PENDING_TTL_SECONDS
        stale = [state for state, entry in self._entries.items() if entry.created_at < cutoff]
        for state in stale:
            del self._entries[state]


pending_auth_store = PendingAuthStore()


def build_authorization_url() -> tuple[str, str]:
    """Start a new auth-code flow and return (authorization_url, state).

    The state is also a handle the UI uses to poll for completion via
    `/api/auth/status`. The PKCE verifier and redirect URI are stashed in the
    module-level pending store so the loopback callback can complete the
    exchange.
    """
    if not KANIDM_URL:
        raise RuntimeError("KANIDM_URL is not configured")
    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = _pkce_pair()
    pending_auth_store.put(
        state,
        PendingAuth(code_verifier=code_verifier, redirect_uri=KANIDM_REDIRECT_URI),
    )
    params = {
        "response_type": "code",
        "client_id": KANIDM_CLIENT_ID,
        "redirect_uri": KANIDM_REDIRECT_URI,
        "scope": KANIDM_SCOPE,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{KANIDM_URL}{_AUTHORIZE_PATH}?{urlencode(params)}", state


def exchange_code(code: str, code_verifier: str, redirect_uri: str) -> dict:
    """Exchange an authorization code for an access token.

    Kanidm requires HTTP Basic auth on the token endpoint for confidential
    clients; public clients (no secret) send the code_verifier alone.
    """
    if not KANIDM_URL:
        raise RuntimeError("KANIDM_URL is not configured")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": KANIDM_CLIENT_ID,
        "code_verifier": code_verifier,
    }
    auth = (KANIDM_CLIENT_ID, KANIDM_CLIENT_SECRET) if KANIDM_CLIENT_SECRET else None
    resp = httpx.post(
        f"{KANIDM_URL}{_TOKEN_PATH}",
        data=data,
        auth=auth,
        timeout=10,
        verify=False,
    )
    if resp.status_code != 200:
        try:
            err = resp.json().get("error", f"http_{resp.status_code}")
        except Exception:
            err = f"http_{resp.status_code}"
        raise ValueError(f"Token exchange failed: {err}")
    return resp.json()


def is_legacy_token(token: str) -> bool:
    """Return True if *token* looks like an old opaque shenas.ai session token (not a JWT)."""
    return token.count(".") < 2
