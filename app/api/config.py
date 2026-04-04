"""Config CRUD API endpoints -- thin wrappers around Pipe ABC config methods."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.pipes import _load_pipe
from app.models import ConfigEntry, ConfigItem, ConfigSetRequest, ConfigValueResponse, OkResponse

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def list_configs(kind: str | None = None, name: str | None = None) -> list[ConfigItem]:
    from app.api.pipes import _load_plugins
    from shenas_pipes.core.abc import Pipe

    pipes = _load_plugins("pipe", base=Pipe)
    result = []
    for pipe_cls in pipes:
        pipe = pipe_cls()
        if not pipe.has_config:
            continue
        if kind and kind != "pipe":
            continue
        if name and name != pipe.name:
            continue
        entries = [
            ConfigEntry(
                key=str(e["key"]),
                label=str(e.get("label") or ""),
                value=e.get("value"),
                description=str(e.get("description") or ""),
            )
            for e in pipe.get_config_entries()
        ]
        if entries:
            result.append(ConfigItem(kind="pipe", name=pipe.name, entries=entries))
    return result


@router.get("/{kind}/{name}/{key}")
def get_config_value(kind: str, name: str, key: str) -> ConfigValueResponse:
    if kind != "pipe":
        raise HTTPException(status_code=404, detail=f"Unknown config: {kind} {name}")
    pipe = _load_pipe(name)
    val = pipe.get_config_value(key)
    if val is None:
        raise HTTPException(status_code=404, detail=f"Not set: {kind} {name}.{key}")
    return ConfigValueResponse(key=key, value=str(val))


@router.put("/{kind}/{name}")
def set_config(kind: str, name: str, body: ConfigSetRequest) -> OkResponse:
    if kind != "pipe":
        raise HTTPException(status_code=404, detail=f"Unknown config: {kind} {name}")
    pipe = _load_pipe(name)
    pipe.set_config_value(body.key, body.value)
    return OkResponse(ok=True)


@router.delete("/{kind}/{name}")
def delete_config_all(kind: str, name: str) -> OkResponse:
    if kind != "pipe":
        raise HTTPException(status_code=404, detail=f"Unknown config: {kind} {name}")
    pipe = _load_pipe(name)
    pipe.delete_config()
    return OkResponse(ok=True)


@router.delete("/{kind}/{name}/{key}")
def delete_config_key(kind: str, name: str, key: str) -> OkResponse:
    if kind != "pipe":
        raise HTTPException(status_code=404, detail=f"Unknown config: {kind} {name}")
    pipe = _load_pipe(name)
    pipe.set_config_value(key, None)
    return OkResponse(ok=True)
