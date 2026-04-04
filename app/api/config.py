"""Config CRUD API endpoints -- delegates to Plugin.has_config / Pipe config methods."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.pipes import _load_plugin, _load_plugins
from app.models import ConfigEntry, ConfigItem, ConfigSetRequest, ConfigValueResponse, OkResponse
from shenas_pipes.core.abc import Plugin

router = APIRouter(prefix="/config", tags=["config"])

CONFIGURABLE_KINDS = ("pipe",)


def _resolve_plugin(kind: str, name: str) -> Plugin:
    cls = _load_plugin(kind, name)
    if not cls:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {kind}/{name}")
    plugin = cls()
    if not plugin.has_config:
        raise HTTPException(status_code=404, detail=f"No config for {kind}/{name}")
    return plugin


@router.get("")
def list_configs(kind: str | None = None, name: str | None = None) -> list[ConfigItem]:
    result = []
    for k in CONFIGURABLE_KINDS:
        if kind and kind != k:
            continue
        for plugin_cls in _load_plugins(k, base=Plugin):
            plugin = plugin_cls()
            if not plugin.has_config:
                continue
            if name and name != plugin.name:
                continue
            entries = [
                ConfigEntry(
                    key=str(e["key"]),
                    label=str(e.get("label") or ""),
                    value=e.get("value"),
                    description=str(e.get("description") or ""),
                )
                for e in plugin.get_config_entries()
            ]
            if entries:
                result.append(ConfigItem(kind=k, name=plugin.name, entries=entries))
    return result


@router.get("/{kind}/{name}/{key}")
def get_config_value(kind: str, name: str, key: str) -> ConfigValueResponse:
    plugin = _resolve_plugin(kind, name)
    val = plugin.get_config_value(key)
    if val is None:
        raise HTTPException(status_code=404, detail=f"Not set: {kind} {name}.{key}")
    return ConfigValueResponse(key=key, value=str(val))


@router.put("/{kind}/{name}")
def set_config(kind: str, name: str, body: ConfigSetRequest) -> OkResponse:
    plugin = _resolve_plugin(kind, name)
    plugin.set_config_value(body.key, body.value)
    return OkResponse(ok=True)


@router.delete("/{kind}/{name}")
def delete_config_all(kind: str, name: str) -> OkResponse:
    plugin = _resolve_plugin(kind, name)
    plugin.delete_config()
    return OkResponse(ok=True)


@router.delete("/{kind}/{name}/{key}")
def delete_config_key(kind: str, name: str, key: str) -> OkResponse:
    plugin = _resolve_plugin(kind, name)
    plugin.set_config_value(key, None)
    return OkResponse(ok=True)
