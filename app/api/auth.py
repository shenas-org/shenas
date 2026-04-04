"""Auth API endpoints -- thin wrappers around Pipe ABC auth methods."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.api.pipes import _load_pipe
from app.models import AuthField, AuthFieldsResponse, AuthRequest, AuthResponse

router = APIRouter(prefix="/auth", tags=["auth"])

log = logging.getLogger(f"shenas.{__name__}")


@router.post("/{pipe_name}")
def auth_pipe(pipe_name: str, body: AuthRequest | None = None) -> AuthResponse:
    """Start or continue a pipe's auth flow."""
    body = body or AuthRequest()
    pipe = _load_pipe(pipe_name)
    result = pipe.handle_auth(body.credentials)
    if result.get("ok"):
        log.info("Auth success: %s", pipe_name)
    else:
        log.warning("Auth issue: %s - %s", pipe_name, result.get("error") or result.get("message"))
    return AuthResponse(**result)


@router.get("/{pipe_name}/fields")
def auth_fields(pipe_name: str) -> AuthFieldsResponse:
    """Get credential fields, instructions, and stored credential status."""
    try:
        pipe = _load_pipe(pipe_name)
    except Exception:
        return AuthFieldsResponse()

    if not pipe.has_auth:
        return AuthFieldsResponse()

    return AuthFieldsResponse(
        fields=[
            AuthField(name=str(f["name"]), prompt=str(f["prompt"]), hide=bool(f.get("hide", False))) for f in pipe.auth_fields
        ],
        instructions=pipe.auth_instructions,
        stored=pipe.stored_credentials,
    )
