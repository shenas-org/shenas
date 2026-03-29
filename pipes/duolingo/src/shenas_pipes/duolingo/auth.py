"""Duolingo JWT token management via OS keyring."""

from __future__ import annotations

from shenas_pipes.duolingo.client import DuolingoClient

KEYRING_SERVICE = "shenas"
KEYRING_KEY = "duolingo_jwt"

AUTH_FIELDS: list[dict[str, str | bool]] = [
    {"name": "username", "prompt": "Username or email", "hide": False},
    {"name": "password", "prompt": "Password", "hide": True},
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
    """Authenticate with Duolingo using username/password.

    Stores the resulting JWT in the OS keyring.
    """
    username = credentials.get("username")
    password = credentials.get("password")
    if not username or not password:
        raise ValueError("username and password are required")

    jwt = DuolingoClient.login(username, password)
    # Verify the token works
    client = DuolingoClient(jwt)
    try:
        client.get_user()
    finally:
        client.close()
    _store_jwt(jwt)
