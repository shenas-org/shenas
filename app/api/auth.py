"""Auth API endpoints -- thin wrappers around Source ABC auth methods."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Request

from app.models import AuthField, AuthFieldsResponse, AuthRequest, AuthResponse

router = APIRouter(prefix="/auth", tags=["auth"])

log = logging.getLogger(f"shenas.{__name__}")


def _build_callback_uri(request: Request, source_name: str) -> str:
    """Build the OAuth callback URI using the browser's origin.

    Behind a reverse proxy (e.g. Vite dev server), request.base_url
    reflects the backend port, not the port the user is browsing on.
    The Origin or Referer header preserves the real host+port.
    """
    origin = request.headers.get("origin")
    if not origin:
        referer = request.headers.get("referer")
        if referer:
            parsed = urlparse(referer)
            origin = f"{parsed.scheme}://{parsed.netloc}"
    if not origin:
        origin = str(request.base_url).rstrip("/")
    return f"{origin}/api/auth/source/{source_name}/callback"


@router.post("/{source_name}")
def auth_source(source_name: str, request: Request, body: AuthRequest | None = None) -> AuthResponse:
    """Start or continue a source's auth flow."""

    from shenas_sources.core.source import Source

    body = body or AuthRequest()
    source = Source.load_by_name(source_name)()  # ty: ignore[call-non-callable]
    # Build callback URL for OAuth redirect flow
    redirect_uri = None
    if source.supports_oauth_redirect:
        redirect_uri = _build_callback_uri(request, source_name)
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
