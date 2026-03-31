"""Auth API endpoints -- handle multi-step auth flows via REST."""

from __future__ import annotations

import importlib
import logging
import sys
import types

from typing import Any

from fastapi import APIRouter

from app.models import AuthFieldsResponse, AuthRequest, AuthResponse

router = APIRouter(prefix="/auth", tags=["auth"])

log = logging.getLogger(f"shenas.{__name__}")

# Server-side pending auth state. Survives module reimports of pipe auth modules.
# Keys are pipe names, values are dicts with thread + state from OAuth/MFA flows.
_pending_flows: dict[str, dict[str, Any]] = {}


def _get_pending_state(pipe_name: str) -> dict[str, object] | None:
    """Look up pending MFA/OAuth state from the pipe's auth module."""
    try:
        mod = _load_auth_module(pipe_name)
        # Google pipes use pending_oauth from core
        try:
            from shenas_pipes.core.google_auth import pending_oauth

            if pipe_name in pending_oauth:
                return pending_oauth.pop(pipe_name)
        except ImportError:
            pass
        # Garmin uses its own pending_mfa dict
        pending = getattr(mod, "pending_mfa", None)
        if pending and pipe_name in pending:
            return pending.pop(pipe_name)
    except Exception:
        pass
    return None


@router.post("/{pipe_name}")
def auth_pipe(pipe_name: str, body: AuthRequest | None = None) -> AuthResponse:
    """Start or continue a pipe's auth flow."""
    body = body or AuthRequest()

    # OAuth completion step -- use server-side pending state
    if "auth_complete" in body.credentials:
        return _complete_oauth(pipe_name)

    # MFA completion step -- use cached module to preserve pending state
    if "mfa_code" in body.credentials:
        mod = _get_cached_auth_module(pipe_name)
        return _complete_mfa(pipe_name, mod, body.credentials["mfa_code"])

    mod = _load_auth_module(pipe_name)
    auth_fn = getattr(mod, "authenticate", None)
    if auth_fn is None:
        return AuthResponse(ok=False, error=f"Pipe {pipe_name} has no authenticate() function")

    try:
        auth_fn(body.credentials)
        log.info("Auth success: %s", pipe_name)
        return AuthResponse(ok=True, message=f"Authenticated {pipe_name}")
    except ValueError as exc:
        msg = str(exc)
        if "MFA code required" in msg:
            return AuthResponse(ok=False, needs_mfa=True, message="MFA code required")
        if msg.startswith("OAUTH_URL:"):
            auth_url = msg.removeprefix("OAUTH_URL:")
            # Grab the pending state from the pipe module before it gets reimported
            mod = _get_cached_auth_module(pipe_name)
            pending = getattr(mod, "_pending_auth", {})
            if pipe_name in pending:
                _pending_flows[pipe_name] = pending.pop(pipe_name)
            return AuthResponse(ok=False, oauth_url=auth_url, message="Open this URL in your browser to authorize")
        return AuthResponse(ok=False, error=msg)
    except Exception as exc:
        log.error("Auth failed: %s - %s", pipe_name, exc)
        return AuthResponse(ok=False, error=str(exc))


def _complete_oauth(pipe_name: str) -> AuthResponse:
    """Complete a pending OAuth flow using server-side state."""
    state = _pending_flows.pop(pipe_name, None)
    if state is None:
        # Try pipe module state as fallback (Google auth stores in core module)
        mod = _get_cached_auth_module(pipe_name)
        auth_fn = getattr(mod, "authenticate", None)
        if auth_fn:
            try:
                auth_fn({"auth_complete": "true"})
                return AuthResponse(ok=True, message=f"Authenticated {pipe_name}")
            except Exception as exc:
                return AuthResponse(ok=False, error=str(exc))
        return AuthResponse(ok=False, error="No pending auth flow. Start auth again.")

    thread = state.get("thread")
    if thread:
        thread.join(timeout=120)
    if state.get("error"):
        return AuthResponse(ok=False, error=state["error"])
    return AuthResponse(ok=True, message=f"Authenticated {pipe_name}")


def _complete_mfa(pipe_name: str, mod: object, mfa_code: str) -> AuthResponse:
    """Complete an MFA auth flow using stored session state."""
    complete_fn = getattr(mod, "complete_mfa", None)
    if complete_fn is None:
        return AuthResponse(ok=False, error=f"Pipe {pipe_name} does not support MFA completion")

    state = _get_pending_state(pipe_name)
    if state is None:
        return AuthResponse(ok=False, error="No pending MFA session. Start auth again.")

    try:
        complete_fn(state, mfa_code)
        return AuthResponse(ok=True, message=f"Authenticated {pipe_name}")
    except Exception as exc:
        return AuthResponse(ok=False, error=str(exc))


@router.get("/{pipe_name}/fields")
def auth_fields(pipe_name: str) -> AuthFieldsResponse:
    """Get the credential fields and instructions for a pipe's auth flow."""
    try:
        mod = _load_auth_module(pipe_name)
    except ModuleNotFoundError:
        return AuthFieldsResponse()
    return AuthFieldsResponse(
        fields=getattr(mod, "AUTH_FIELDS", []),
        instructions=getattr(mod, "AUTH_INSTRUCTIONS", ""),
    )


def _get_cached_auth_module(pipe_name: str) -> types.ModuleType:
    """Get the auth module without reimporting (preserves in-memory state)."""
    module_name = f"shenas_pipes.{pipe_name}.auth"
    if module_name in sys.modules:
        return sys.modules[module_name]
    return importlib.import_module(module_name)


def _load_auth_module(pipe_name: str) -> types.ModuleType:
    importlib.invalidate_caches()
    for key in list(sys.modules):
        if key.startswith(f"shenas_pipes.{pipe_name}"):
            del sys.modules[key]
    return importlib.import_module(f"shenas_pipes.{pipe_name}.auth")
