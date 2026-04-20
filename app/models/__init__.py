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


class AuthField(BaseModel):
    name: str
    prompt: str
    hide: bool = False


class AuthFieldsResponse(BaseModel):
    fields: list[AuthField] = []
    instructions: str = ""
    stored: list[str] = []


# --- Auth ---


class AuthRequest(BaseModel):
    credentials: dict[str, str] = {}


class AuthResponse(BaseModel):
    ok: bool = False
    message: str = ""
    error: str | None = None
    needs_mfa: bool = False
    oauth_url: str | None = None
    oauth_redirect: str | None = None


# --- Config ---


class ConfigEntry(BaseModel):
    key: str
    label: str = ""
    value: str | None = None
    description: str = ""


class ConfigSetRequest(BaseModel):
    key: str
    value: str


class ConfigValueResponse(BaseModel):
    key: str
    value: str


# --- Plugins ---


class PluginInfo(BaseModel):
    name: str
    display_name: str = ""
    package: str = ""
    version: str = ""
    signature: str = ""
    description: str = ""
    commands: list[str] = []
    enabled: bool = True
    has_config: bool = False
    has_data: bool = False
    has_auth: bool = False
    has_entities: bool = False
    is_authenticated: bool | None = None
    sync_frequency: int | None = None
    entity_types: list[str] = []
    entity_uuids: list[str] = []
    tables: list[str] = []
    total_rows: int = 0
    config_entries: list[ConfigEntry] = []
    added_at: str | None = None
    updated_at: str | None = None
    status_changed_at: str | None = None
    synced_at: str | None = None


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


class ScheduleInfo(BaseModel):
    name: str
    sync_frequency: int | None = None
    synced_at: str | None = None
    is_due: bool = False


class SSEEvent(BaseModel):
    event_type: str = "message"
    source: str | None = None
    message: str = ""


# --- Takeout ---


class ArchiveInfo(BaseModel):
    id: str
    name: str
    size: int = 0
    created_time: str = ""
    mime_type: str = ""
