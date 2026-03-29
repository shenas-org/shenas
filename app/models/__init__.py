"""Shared Pydantic models for API requests, responses, and internal data structures."""

from __future__ import annotations

from pydantic import BaseModel


# --- Generic responses ---


class OkResponse(BaseModel):
    ok: bool
    message: str = ""


class ErrorResponse(BaseModel):
    ok: bool = False
    error: str


# --- Health & Query ---


class HealthResponse(BaseModel):
    status: str


class TableInfo(BaseModel):
    schema_name: str
    table: str


# --- Pipes ---


class PipeOption(BaseModel):
    name: str
    default: str | int | float | bool | None = None
    help: str = ""


class PipeCommand(BaseModel):
    name: str
    options: list[PipeOption] = []


class PipeInfo(BaseModel):
    name: str
    version: str = ""
    signature: str = ""
    commands: list[PipeCommand] = []


class AuthField(BaseModel):
    name: str
    prompt: str
    hide: bool = False


class AuthFieldsResponse(BaseModel):
    fields: list[AuthField] = []
    instructions: str = ""


# --- Auth ---


class AuthRequest(BaseModel):
    credentials: dict[str, str] = {}


class AuthResponse(BaseModel):
    ok: bool = False
    message: str = ""
    error: str | None = None
    needs_mfa: bool = False
    oauth_url: str | None = None


# --- Config ---


class ConfigEntry(BaseModel):
    key: str
    value: str | None = None
    description: str = ""


class ConfigItem(BaseModel):
    kind: str
    name: str
    entries: list[ConfigEntry] = []


class ConfigSetRequest(BaseModel):
    key: str
    value: str


class ConfigValueResponse(BaseModel):
    key: str
    value: str


# --- DB ---


class TableStats(BaseModel):
    name: str
    rows: int = 0
    earliest: str | None = None
    latest: str | None = None
    cols: int = 0


class SchemaInfo(BaseModel):
    name: str
    tables: list[TableStats] = []


class DBStatusResponse(BaseModel):
    key_source: str
    db_path: str
    size_mb: float | None = None
    schemas: list[SchemaInfo] = []


# --- Packages ---


class PackageInfo(BaseModel):
    name: str
    package: str
    version: str
    signature: str = ""


class InstallResult(BaseModel):
    name: str
    ok: bool
    message: str = ""


class InstallRequest(BaseModel):
    names: list[str]
    index_url: str | None = None
    skip_verify: bool = False


class InstallResponse(BaseModel):
    results: list[InstallResult]


class RemoveResponse(BaseModel):
    ok: bool
    message: str = ""


# --- Sync ---


class SyncRequest(BaseModel):
    start_date: str | None = None
    full_refresh: bool = False
    extra: dict[str, str | int | bool] = {}


class SSEEvent(BaseModel):
    event_type: str = "message"
    pipe: str | None = None
    message: str = ""


# --- Takeout ---


class ArchiveInfo(BaseModel):
    id: str
    name: str
    size: int = 0
    created_time: str = ""
    mime_type: str = ""
