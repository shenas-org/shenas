"""Development-mode state seeding from a local JSON file.

When running in dev mode (not a PyInstaller bundle), source auth/config
and the entity graph can be read from ``data/dev_credentials.json`` at
startup. This avoids re-authenticating every source and rebuilding the
entity graph after a DB flush.

The JSON format is::

    {
      "sources": {
        "garmin": {
          "auth": {"username": "...", "password": "..."},
          "config": {"sync_frequency": 60}
        },
        "spotify": {
          "auth": {"access_token": "...", "refresh_token": "..."}
        }
      },
      "entities": {
        "entity_types": [...],
        "entity_relationship_types": [...],
        "entities": [...],
        "entity_relationships": [...],
        "entity_index": [...]
      }
    }

Legacy flat shape ``{source_name: {auth, config}}`` is still accepted
on read for backward compatibility.

Only populated in dev mode (no ``sys._MEIPASS``).
"""

from __future__ import annotations

import dataclasses
import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.table import Table

log = logging.getLogger("shenas.dev_credentials")

_CREDENTIALS_FILE = Path("data/dev_credentials.json")


def is_dev_mode() -> bool:
    return getattr(sys, "_MEIPASS", None) is None


def _is_legacy_shape(data: dict[str, Any]) -> bool:
    """Heuristic: legacy shape has no 'sources' key and no 'entities' key."""
    return "sources" not in data and "entities" not in data


def load_dev_state() -> dict[str, Any]:
    """Read dev_credentials.json, returning {} if missing or in prod.

    Normalizes legacy flat shape to the nested ``{"sources": {...}}`` form.
    """
    if not is_dev_mode():
        return {}
    if not _CREDENTIALS_FILE.exists():
        return {}
    try:
        data = json.loads(_CREDENTIALS_FILE.read_text())
    except Exception:
        log.warning("Failed to read %s", _CREDENTIALS_FILE)
        return {}
    if _is_legacy_shape(data):
        return {"sources": data}
    return data


def save_dev_state(data: dict[str, Any]) -> None:
    """Write current dev state (sources + entities) to dev_credentials.json."""
    _CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CREDENTIALS_FILE.write_text(json.dumps(data, indent=2, default=str))
    log.info("Saved dev state to %s", _CREDENTIALS_FILE)


def seed_from_json() -> int:
    """Seed source auth/config and entity tables from dev_credentials.json.

    Skips sources that already have auth populated. Returns the number of
    sources seeded (entity seeding is best-effort and not counted).
    """
    state = load_dev_state()
    if not state:
        return 0

    seeded = _seed_sources(state.get("sources", {}))
    _seed_entities(state.get("entities", {}))
    return seeded


def _seed_sources(creds: dict[str, dict[str, Any]]) -> int:
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

        if "auth" in entry and src.has_auth and not src.is_authenticated:
            try:
                src.Auth.write_row(**entry["auth"])  # ty: ignore[unresolved-attribute]
                log.info("Seeded auth for %s", name)
                seeded += 1
            except Exception:
                log.warning("Failed to seed auth for %s", name, exc_info=True)

        if "config" in entry and src.has_config:
            try:
                src.Config.write_row(**entry["config"])  # ty: ignore[unresolved-attribute]
                log.info("Seeded config for %s", name)
            except Exception:
                log.warning("Failed to seed config for %s", name, exc_info=True)

    return seeded


def _seed_entities(data: dict[str, list[dict[str, Any]]]) -> None:
    """Best-effort restore of entity tables. Skips already-populated tables."""
    if not data:
        return

    from app.database import cursor
    from app.entity import (
        Entity,
        EntityIndex,
        EntityRelationship,
        EntityRelationshipType,
        EntityType,
    )

    table_map: list[tuple[str, type[Table]]] = [
        ("entity_types", EntityType),
        ("entity_relationship_types", EntityRelationshipType),
        ("entities", Entity),
        ("entity_relationships", EntityRelationship),
        ("entity_index", EntityIndex),
    ]

    for key, cls in table_map:
        rows = data.get(key) or []
        if not rows:
            continue
        try:
            existing = cls.all(limit=1)
            if existing:
                log.info("Skipping %s seed: table already has rows", key)
                continue
            with cursor(database=cls._resolve_database()) as cur:
                cols = cls._column_names()
                placeholders = ", ".join(["?"] * len(cols))
                sql = f"INSERT INTO {cls._qualified()} ({', '.join(cols)}) VALUES ({placeholders})"
                for row in rows:
                    cur.execute(sql, [row.get(c) for c in cols])
            log.info("Seeded %d row(s) into %s", len(rows), key)
        except Exception:
            log.warning("Failed to seed %s", key, exc_info=True)


def export_current_state() -> dict[str, Any]:
    """Export per-source auth/config plus the entity graph."""
    return {
        "sources": export_current_credentials(),
        "entities": export_current_entities(),
    }


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


def export_current_entities() -> dict[str, list[dict[str, Any]]]:
    """Export the entity graph (types, entities, relationships, index)."""
    from app.entity import (
        Entity,
        EntityIndex,
        EntityRelationship,
        EntityRelationshipType,
        EntityType,
    )

    result: dict[str, list[dict[str, Any]]] = {}
    for key, cls in [
        ("entity_types", EntityType),
        ("entity_relationship_types", EntityRelationshipType),
        ("entities", Entity),
        ("entity_relationships", EntityRelationship),
        ("entity_index", EntityIndex),
    ]:
        try:
            result[key] = [dataclasses.asdict(row) for row in cls.all()]
        except Exception:
            log.warning("Failed to export %s", key, exc_info=True)
            result[key] = []
    return result
