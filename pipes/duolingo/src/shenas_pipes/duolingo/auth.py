"""Duolingo JWT token management via OS keyring.

Duolingo has no official API and blocks programmatic login with CAPTCHA.
Authentication requires a JWT token extracted from the browser:

1. Log into duolingo.com
2. Open DevTools console (F12)
3. Run: document.cookie.match(new RegExp('(^| )jwt_token=([^;]+)'))[0].slice(11)
4. Paste the token when prompted
"""

from __future__ import annotations

from shenas_pipes.duolingo.client import DuolingoClient

KEYRING_SERVICE = "shenas"
KEYRING_KEY = "duolingo_jwt"

AUTH_FIELDS: list[dict[str, str | bool]] = [
    {"name": "jwt_token", "prompt": "JWT token (from browser DevTools)", "hide": True},
]


def _get_stored_jwt() -> str | None:
    """Read JWT from OS keyring."""
    try:
        import keyring

        return keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
    except Exception:
        return None


def _store_jwt(jwt: str) -> None:
    """Write JWT to OS keyring."""
    import keyring

    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_KEY)
    except Exception:
        pass
    keyring.set_password(KEYRING_SERVICE, KEYRING_KEY, jwt)


def build_client() -> DuolingoClient:
    """Build a Duolingo client from a stored JWT token."""
    jwt = _get_stored_jwt()
    if not jwt:
        raise RuntimeError("No JWT token found. Run 'shenasctl pipe duolingo auth' first.")
    return DuolingoClient(jwt)


def authenticate(credentials: dict[str, str]) -> None:
    """Store a Duolingo JWT token extracted from the browser.

    Expected keys: jwt_token.
    """
    jwt = credentials.get("jwt_token")
    if not jwt:
        raise ValueError("jwt_token is required")

    # Verify the token works
    client = DuolingoClient(jwt)
    try:
        client.get_user()
    finally:
        client.close()
    _store_jwt(jwt)
