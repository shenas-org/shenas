from pathlib import Path

from garminconnect import Garmin


def build_client(email: str | None = None, password: str | None = None, token_store: str | None = None) -> Garmin:
    token_path = Path(token_store) if token_store else Path(".dlt") / "garmin_tokens"

    # Try token-only login if saved tokens exist
    if token_path.exists() and any(token_path.iterdir()):
        client = Garmin()
        try:
            client.login(str(token_path))
            return client
        except Exception:
            pass

    # Fall back to credential login
    if not email or not password:
        raise RuntimeError(f"No valid tokens found at {token_path}. Run 'shenas pipe garmin auth' first.")

    token_path.mkdir(parents=True, exist_ok=True)
    client = Garmin(email=email, password=password)
    try:
        client.login(str(token_path))
    except Exception:
        client.login()
        client.garth.dump(str(token_path))

    return client
