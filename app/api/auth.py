"""Auth API endpoints -- thin wrappers around Source ABC auth methods."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.api.sources import _load_source
from app.models import AuthField, AuthFieldsResponse, AuthRequest, AuthResponse

router = APIRouter(prefix="/auth", tags=["auth"])

log = logging.getLogger(f"shenas.{__name__}")


@router.post("/{source_name}")
def auth_source(source_name: str, body: AuthRequest | None = None) -> AuthResponse:
    """Start or continue a source's auth flow."""
    body = body or AuthRequest()
    source = _load_source(source_name)
    result = source.handle_auth(body.credentials)
    if result.get("ok"):
        log.info("Auth success: %s", source_name)
    else:
        log.warning("Auth issue: %s - %s", source_name, result.get("error") or result.get("message"))
    return AuthResponse(**result)


@router.get("/{source_name}/fields")
def auth_fields(source_name: str) -> AuthFieldsResponse:
    """Get credential fields, instructions, and stored credential status."""
    try:
        source = _load_source(source_name)
    except Exception:
        return AuthFieldsResponse()

    if not source.has_auth:
        return AuthFieldsResponse()

    return AuthFieldsResponse(
        fields=[
            AuthField(name=str(f["name"]), prompt=str(f["prompt"]), hide=bool(f.get("hide", False)))
            for f in source.auth_fields
        ],
        instructions=source.auth_instructions,
        stored=source.stored_credentials,
    )
