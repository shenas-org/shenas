"""Config CRUD API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models import ConfigEntry, ConfigItem, ConfigSetRequest, ConfigValueResponse, OkResponse
from shenas_pipes.core.store import DataclassStore

router = APIRouter(prefix="/config", tags=["config"])

_config = DataclassStore("config")
_CONFIG_CLASSES: dict[str, type] = {}


def _discover_config_classes() -> dict[str, type]:
    if _CONFIG_CLASSES:
        return _CONFIG_CLASSES

    from importlib.metadata import entry_points

    from shenas_pipes.core.base_config import PipeConfig

    for ep in entry_points(group="shenas.pipes"):
        try:
            cls = ep.load()
            pipe = cls()
            if pipe.Config is not PipeConfig:
                _CONFIG_CLASSES[pipe.Config.__table__] = pipe.Config
        except Exception:
            continue

    return _CONFIG_CLASSES


def _resolve_table(kind: str, name: str) -> str:
    return f"{kind}_{name}"


def _get_config_class(kind: str, name: str) -> type:
    table_name = _resolve_table(kind, name)
    classes = _discover_config_classes()
    if table_name not in classes:
        raise HTTPException(status_code=404, detail=f"Unknown config: {kind} {name}")
    return classes[table_name]


@router.get("")
def list_configs(kind: str | None = None, name: str | None = None) -> list[ConfigItem]:
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
        row = _config.get(cls)
        meta = _config.metadata(cls)
        parts = table_name.split("_", 1)
        entries = []
        for col in meta["columns"]:
            if col["name"] == "id":
                continue
            val = row.get(col["name"]) if row else None
            is_secret = col.get("category") == "secret"
            display_val = "********" if (is_secret and val) else (str(val) if val is not None else None)
            entries.append(
                ConfigEntry(
                    key=col["name"],
                    label=col["name"].replace("_", " ").title(),
                    value=display_val,
                    description=col.get("description", ""),
                )
            )
        result.append(ConfigItem(kind=parts[0], name=parts[1] if len(parts) > 1 else parts[0], entries=entries))

    return result


@router.get("/{kind}/{name}/{key}")
def get_config_value(kind: str, name: str, key: str) -> ConfigValueResponse:
    cls = _get_config_class(kind, name)
    val = _config.get_value(cls, key)
    if val is None:
        raise HTTPException(status_code=404, detail=f"Not set: {kind} {name}.{key}")
    return ConfigValueResponse(key=key, value=str(val))


@router.put("/{kind}/{name}")
def set_config(kind: str, name: str, body: ConfigSetRequest) -> OkResponse:
    cls = _get_config_class(kind, name)
    value = body.value
    if value is not None:
        meta = _config.metadata(cls)
        for col in meta["columns"]:
            if col["name"] == body.key:
                db_type = col.get("db_type", "").upper()
                if db_type == "INTEGER":
                    value = int(value)
                elif db_type in ("FLOAT", "DOUBLE", "REAL"):
                    value = float(value)
                break
    _config.set(cls, **{body.key: value})
    return OkResponse(ok=True)


@router.delete("/{kind}/{name}")
def delete_config_all(kind: str, name: str) -> OkResponse:
    cls = _get_config_class(kind, name)
    _config.delete(cls)
    return OkResponse(ok=True)


@router.delete("/{kind}/{name}/{key}")
def delete_config_key(kind: str, name: str, key: str) -> OkResponse:
    cls = _get_config_class(kind, name)
    _config.set(cls, **{key: None})
    return OkResponse(ok=True)
