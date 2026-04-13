"""Development-mode credential seeding from a local JSON file.

When running in dev mode (not a PyInstaller bundle), source auth and
config values can be read from ``data/dev_credentials.json`` at startup.
This avoids re-authenticating every source after a DB flush.

The JSON format is::

    {
      "garmin": {
        "auth": {"username": "...", "password": "..."},
        "config": {"sync_frequency": 60}
      },
      "spotify": {
        "auth": {"access_token": "...", "refresh_token": "..."}
      }
    }

Only populated in dev mode (no ``sys._MEIPASS``).
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger("shenas.dev_credentials")

_CREDENTIALS_FILE = Path("data/dev_credentials.json")


def is_dev_mode() -> bool:
    return getattr(sys, "_MEIPASS", None) is None


def load_dev_credentials() -> dict[str, dict[str, Any]]:
    """Read dev_credentials.json, returning {} if missing or in prod."""
    if not is_dev_mode():
        return {}
    if not _CREDENTIALS_FILE.exists():
        return {}
    try:
        return json.loads(_CREDENTIALS_FILE.read_text())
    except Exception:
        log.warning("Failed to read %s", _CREDENTIALS_FILE)
        return {}


def save_dev_credentials(data: dict[str, dict[str, Any]]) -> None:
    """Write current auth/config to dev_credentials.json."""
    _CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CREDENTIALS_FILE.write_text(json.dumps(data, indent=2, default=str))
    log.info("Saved dev credentials to %s", _CREDENTIALS_FILE)


def seed_from_json() -> int:
    """Seed source auth/config tables from dev_credentials.json.

    Skips sources that already have auth populated. Returns the
    number of sources seeded.
    """
    creds = load_dev_credentials()
    if not creds:
        return 0

    from shenas_sources.core.source import Source

    seeded = 0
    for source_cls in Source.load_all():
        src = source_cls()
        name = src.name
        if name not in creds:
            continue

        entry = creds[name]

        # Seed auth if present and not already authenticated
        if "auth" in entry and src.has_auth and not src.is_authenticated:
            try:
                src.Auth.write_row(**entry["auth"])  # ty: ignore[unresolved-attribute]
                log.info("Seeded auth for %s", name)
                seeded += 1
            except Exception:
                log.warning("Failed to seed auth for %s", name, exc_info=True)

        # Seed config if present
        if "config" in entry and src.has_config:
            try:
                src.Config.write_row(**entry["config"])  # ty: ignore[unresolved-attribute]
                log.info("Seeded config for %s", name)
            except Exception:
                log.warning("Failed to seed config for %s", name, exc_info=True)

    return seeded


def export_current_credentials() -> dict[str, dict[str, Any]]:
    """Export all current source auth/config to a dict."""
    from shenas_sources.core.source import Source

    result: dict[str, dict[str, Any]] = {}

    for source_cls in Source.load_all():
        src = source_cls()
        entry: dict[str, Any] = {}

        if src.has_auth:
            try:
                row = src.Auth.read_row()  # ty: ignore[unresolved-attribute]
                if row:
                    entry["auth"] = {k: v for k, v in row.items() if k != "id" and v is not None}
            except Exception:
                pass

        if src.has_config:
            try:
                row = src.Config.read_row()  # ty: ignore[unresolved-attribute]
                if row:
                    entry["config"] = {k: v for k, v in row.items() if k != "id" and v is not None}
            except Exception:
                pass

        if entry:
            result[src.name] = entry

    return result
