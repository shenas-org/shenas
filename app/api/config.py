"""Config CRUD API endpoints."""

from __future__ import annotations

import importlib

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import connect

router = APIRouter(prefix="/config", tags=["config"])

_CONFIG_CLASSES: dict[str, type] = {}


def _discover_config_classes() -> dict[str, type]:
    if _CONFIG_CLASSES:
        return _CONFIG_CLASSES

    for module_path, class_name in [
        ("shenas_pipes.garmin.config", "GarminConfig"),
        ("shenas_pipes.lunchmoney.config", "LunchMoneyConfig"),
        ("shenas_pipes.obsidian.config", "ObsidianConfig"),
        ("shenas_pipes.gmail.config", "GmailConfig"),
    ]:
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            _CONFIG_CLASSES[cls.__table__] = cls
        except (ImportError, AttributeError):
            pass

    return _CONFIG_CLASSES


def _resolve_table(kind: str, name: str) -> str:
    return f"{kind}_{name}"


def _get_config_class(kind: str, name: str) -> type:
    table_name = _resolve_table(kind, name)
    classes = _discover_config_classes()
    if table_name not in classes:
        raise HTTPException(status_code=404, detail=f"Unknown config: {kind} {name}")
    return classes[table_name]


class ConfigSetRequest(BaseModel):
    key: str
    value: str


@router.get("")
def list_configs(kind: str | None = None, name: str | None = None) -> list[dict[str, object]]:
    from shenas_pipes.core.config import config_metadata, get_config

    con = connect(read_only=True)
    classes = _discover_config_classes()

    if kind and name:
        table_name = _resolve_table(kind, name)
        if table_name not in classes:
            raise HTTPException(status_code=404, detail=f"Unknown config: {kind} {name}")
        classes = {table_name: classes[table_name]}
    elif kind:
        classes = {k: v for k, v in classes.items() if k.startswith(f"{kind}_")}

    result = []
    for table_name, cls in sorted(classes.items()):
        row = get_config(con, cls)
        meta = config_metadata(cls)
        parts = table_name.split("_", 1)
        entries = []
        for col in meta["columns"]:
            if col["name"] == "id":
                continue
            val = row.get(col["name"]) if row else None
            is_secret = col.get("category") == "secret"
            display_val = "********" if (is_secret and val) else (str(val) if val is not None else None)
            entries.append(
                {
                    "key": col["name"],
                    "value": display_val,
                    "description": col.get("description", ""),
                }
            )
        result.append({"kind": parts[0], "name": parts[1] if len(parts) > 1 else parts[0], "entries": entries})

    return result


@router.get("/{kind}/{name}/{key}")
def get_config_value(kind: str, name: str, key: str) -> dict[str, str]:
    from shenas_pipes.core.config import get_config_value as _get_value

    cls = _get_config_class(kind, name)
    con = connect(read_only=True)
    val = _get_value(con, cls, key)
    if val is None:
        raise HTTPException(status_code=404, detail=f"Not set: {kind} {name}.{key}")
    return {"key": key, "value": str(val)}


@router.put("/{kind}/{name}")
def set_config(kind: str, name: str, body: ConfigSetRequest) -> dict[str, bool]:
    from shenas_pipes.core.config import set_config as _set_config

    cls = _get_config_class(kind, name)
    con = connect()
    _set_config(con, cls, **{body.key: body.value})
    return {"ok": True}


@router.delete("/{kind}/{name}")
def delete_config_all(kind: str, name: str) -> dict[str, bool]:
    from shenas_pipes.core.config import delete_config

    cls = _get_config_class(kind, name)
    con = connect()
    delete_config(con, cls)
    return {"ok": True}


@router.delete("/{kind}/{name}/{key}")
def delete_config_key(kind: str, name: str, key: str) -> dict[str, bool]:
    from shenas_pipes.core.config import set_config as _set_config

    cls = _get_config_class(kind, name)
    con = connect()
    _set_config(con, cls, **{key: None})
    return {"ok": True}
