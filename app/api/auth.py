"""Auth API endpoints -- handle multi-step auth flows via Pipe ABC."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from app.api.pipes import _load_pipe
from app.models import AuthField, AuthFieldsResponse, AuthRequest, AuthResponse
from shenas_pipes.core.store import DataclassStore

router = APIRouter(prefix="/auth", tags=["auth"])

log = logging.getLogger(f"shenas.{__name__}")


@router.post("/{pipe_name}")
def auth_pipe(pipe_name: str, body: AuthRequest | None = None) -> AuthResponse:  # noqa: PLR0911
    """Start or continue a pipe's auth flow."""
    body = body or AuthRequest()
    pipe = _load_pipe(pipe_name)

    # MFA completion step
    if "mfa_code" in body.credentials:
        try:
            # Retrieve pending state from the pipe's auth module
            state = _get_pending_state(pipe_name)
            if state is None:
                return AuthResponse(ok=False, error="No pending MFA session. Start auth again.")
            pipe.complete_mfa(state, body.credentials["mfa_code"])
            log.info("Auth (MFA) success: %s", pipe_name)
            return AuthResponse(ok=True, message=f"Authenticated {pipe_name}")
        except Exception as exc:
            log.exception("Auth (MFA) failed: %s", pipe_name)
            return AuthResponse(ok=False, error=str(exc))

    # OAuth completion step
    if "auth_complete" in body.credentials:
        try:
            pipe.authenticate(body.credentials)
            log.info("Auth (OAuth) success: %s", pipe_name)
            return AuthResponse(ok=True, message=f"Authenticated {pipe_name}")
        except Exception as exc:
            log.exception("Auth (OAuth) failed: %s", pipe_name)
            return AuthResponse(ok=False, error=str(exc))

    # Initial auth step
    try:
        pipe.authenticate(body.credentials)
        log.info("Auth success: %s", pipe_name)
        return AuthResponse(ok=True, message=f"Authenticated {pipe_name}")
    except ValueError as exc:
        msg = str(exc)
        if "MFA code required" in msg:
            return AuthResponse(ok=False, needs_mfa=True, message="MFA code required")
        if msg.startswith("OAUTH_URL:"):
            auth_url = msg.removeprefix("OAUTH_URL:")
            return AuthResponse(ok=False, oauth_url=auth_url, message="Open this URL in your browser to authorize")
        return AuthResponse(ok=False, error=msg)
    except Exception as exc:
        log.exception("Auth failed: %s", pipe_name)
        return AuthResponse(ok=False, error=str(exc))


@router.get("/{pipe_name}/fields")
def auth_fields(pipe_name: str) -> AuthFieldsResponse:
    """Get the credential fields, instructions, and stored credential status."""
    try:
        pipe = _load_pipe(pipe_name)
    except Exception:
        return AuthFieldsResponse()

    if not pipe.has_auth:
        return AuthFieldsResponse()

    stored: list[str] = []
    try:
        _auth = DataclassStore("auth")
        row = _auth.get(pipe.Auth)
        meta = _auth.metadata(pipe.Auth)
        for col in meta["columns"]:
            if col["name"] == "id":
                continue
            val = row.get(col["name"]) if row else None
            if val:
                stored.append(col["name"].replace("_", " ").title())
    except Exception:
        pass

    return AuthFieldsResponse(
        fields=[
            AuthField(name=str(f["name"]), prompt=str(f["prompt"]), hide=bool(f.get("hide", False))) for f in pipe.auth_fields
        ],
        instructions=pipe.auth_instructions,
        stored=stored,
    )


def _get_pending_state(pipe_name: str) -> dict[str, Any] | None:
    """Look up pending MFA/OAuth state from the pipe's auth module."""
    try:
        # Google pipes use pending_oauth from core
        try:
            from shenas_pipes.core.google_auth import pending_oauth

            if pipe_name in pending_oauth:
                return pending_oauth.pop(pipe_name)
        except ImportError:
            pass
        # Garmin uses its own pending_mfa dict
        import importlib

        mod = importlib.import_module(f"shenas_pipes.{pipe_name}.auth")
        pending = getattr(mod, "pending_mfa", None)
        if pending and pipe_name in pending:
            return pending.pop(pipe_name)
    except Exception:
        pass
    return None
