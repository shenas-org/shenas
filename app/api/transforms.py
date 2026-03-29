"""Transform management API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.transforms import (
    create_transform,
    delete_transform,
    get_transform,
    list_transforms,
    set_transform_enabled,
    test_transform,
    update_transform,
)

router = APIRouter(prefix="/transforms", tags=["transforms"])


class TransformCreate(BaseModel):
    source_duckdb_schema: str
    source_duckdb_table: str
    target_duckdb_schema: str
    target_duckdb_table: str
    source_plugin: str
    sql: str


class TransformUpdate(BaseModel):
    sql: str


@router.get("")
def list_all(source: str | None = None) -> list[dict[str, Any]]:
    """List transforms, optionally filtered by source plugin."""
    return list_transforms(source)


@router.get("/{transform_id}")
def get_one(transform_id: int) -> dict[str, Any]:
    """Get a single transform."""
    t = get_transform(transform_id)
    if not t:
        raise HTTPException(status_code=404, detail="Transform not found")
    return t


@router.post("")
def create(body: TransformCreate) -> dict[str, Any]:
    """Create a new transform."""
    return create_transform(
        source_duckdb_schema=body.source_duckdb_schema,
        source_duckdb_table=body.source_duckdb_table,
        target_duckdb_schema=body.target_duckdb_schema,
        target_duckdb_table=body.target_duckdb_table,
        source_plugin=body.source_plugin,
        sql=body.sql,
    )


@router.put("/{transform_id}")
def update(transform_id: int, body: TransformUpdate) -> dict[str, Any]:
    """Update a transform's SQL."""
    t = update_transform(transform_id, body.sql)
    if not t:
        raise HTTPException(status_code=404, detail="Transform not found")
    return t


@router.delete("/{transform_id}")
def delete(transform_id: int) -> dict[str, Any]:
    """Delete a transform. Default transforms cannot be deleted."""
    t = get_transform(transform_id)
    if not t:
        raise HTTPException(status_code=404, detail="Transform not found")
    if not delete_transform(transform_id):
        raise HTTPException(status_code=400, detail="Cannot delete a default transform. Disable it instead.")
    return {"ok": True, "message": f"Deleted transform {transform_id}"}


@router.post("/{transform_id}/enable")
def enable(transform_id: int) -> dict[str, Any]:
    """Enable a transform."""
    t = set_transform_enabled(transform_id, True)
    if not t:
        raise HTTPException(status_code=404, detail="Transform not found")
    return t


@router.post("/{transform_id}/disable")
def disable(transform_id: int) -> dict[str, Any]:
    """Disable a transform."""
    t = set_transform_enabled(transform_id, False)
    if not t:
        raise HTTPException(status_code=404, detail="Transform not found")
    return t


@router.post("/{transform_id}/test")
def test(transform_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """Dry-run a transform's SQL and return preview rows."""
    t = get_transform(transform_id)
    if not t:
        raise HTTPException(status_code=404, detail="Transform not found")
    try:
        return test_transform(transform_id, limit)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"SQL error: {exc}")
