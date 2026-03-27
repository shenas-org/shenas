"""Lunch Money API key management via OS keyring."""

from lunchable import LunchMoney

KEYRING_SERVICE = "shenas"
KEYRING_KEY = "lunchmoney_api_key"


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

    raise RuntimeError("No API key found. Run 'shenas pipe lunchmoney auth' first.")
