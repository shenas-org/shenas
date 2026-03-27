"""Lunch Money API key management."""

from pathlib import Path

from lunchable import LunchMoney


def build_client(api_key: str | None = None, token_store: str | None = None) -> LunchMoney:
    """Build a Lunch Money client from stored API key or provided key."""
    token_path = Path(token_store) if token_store else Path(".dlt") / "lunchmoney_token"

    if api_key:
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(api_key)
        return LunchMoney(access_token=api_key)

    if token_path.exists():
        stored_key = token_path.read_text().strip()
        if stored_key:
            return LunchMoney(access_token=stored_key)

    raise RuntimeError(f"No API key found at {token_path}. Run 'shenas pipe lunchmoney auth' first.")
