"""Lunch Money API key management via OS keyring."""

from lunchable import LunchMoney

KEYRING_SERVICE = "shenas"
KEYRING_KEY = "lunchmoney_api_key"

AUTH_FIELDS = [
    {"name": "api_key", "prompt": "API key", "hide": True},
]


def _get_stored_key() -> str | None:
    """Read API key from OS keyring."""
    try:
        import keyring

        return keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
    except Exception:
        return None


def _store_key(api_key: str) -> None:
    """Write API key to OS keyring."""
    import keyring

    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_KEY)
    except Exception:
        pass
    keyring.set_password(KEYRING_SERVICE, KEYRING_KEY, api_key)


def build_client(api_key: str | None = None, **_kwargs: str) -> LunchMoney:
    """Build a Lunch Money client from provided key or OS keyring."""
    if api_key:
        _store_key(api_key)
        return LunchMoney(access_token=api_key)

    stored = _get_stored_key()
    if stored:
        return LunchMoney(access_token=stored)

    raise RuntimeError("No API key found. Run 'shenasctl pipe lunchmoney auth' first.")


def authenticate(credentials: dict[str, str]) -> None:
    """Authenticate with Lunch Money using an API key.

    Expected keys: api_key (or password as alias).
    """
    api_key = credentials.get("api_key") or credentials.get("password")
    if not api_key:
        raise ValueError("api_key is required")

    client = build_client(api_key=api_key)
    client.get_user()  # verify the key works
