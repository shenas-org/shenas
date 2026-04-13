"""Auth API endpoints -- thin wrappers around Source ABC auth methods."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.models import AuthField, AuthFieldsResponse, AuthRequest, AuthResponse

router = APIRouter(prefix="/auth", tags=["auth"])

log = logging.getLogger(f"shenas.{__name__}")


@router.post("/{source_name}")
def auth_source(source_name: str, request: Request, body: AuthRequest | None = None) -> AuthResponse:
    """Start or continue a source's auth flow."""

    from shenas_sources.core.source import Source

    body = body or AuthRequest()
    source = Source.load_by_name(source_name)()  # ty: ignore[call-non-callable]
    # Build callback URL for OAuth redirect flow
    redirect_uri = None
    if source.supports_oauth_redirect:
        redirect_uri = str(request.url_for("source_auth_callback", name=source_name)).replace("://localhost", "://127.0.0.1")
    result = source.handle_auth(body.credentials, redirect_uri=redirect_uri)
    if result.get("ok"):
        log.info("Auth success: %s", source_name)
    else:
        log.warning("Auth issue: %s - %s", source_name, result.get("error") or result.get("message"))
    return AuthResponse(**result)


@router.get("/{source_name}/fields")
def auth_fields(source_name: str) -> AuthFieldsResponse:
    """Get credential fields, instructions, and stored credential status."""
    from shenas_sources.core.source import Source

    try:
        source = Source.load_by_name(source_name)()  # ty: ignore[call-non-callable]
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
