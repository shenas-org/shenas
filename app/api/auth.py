"""Auth API endpoints -- handle multi-step auth flows via REST."""

import importlib
import sys

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory store for pending MFA sessions (pipe_name -> state)
_pending_mfa: dict[str, object] = {}


class AuthRequest(BaseModel):
    credentials: dict[str, str] = {}


@router.post("/{pipe_name}")
def auth_pipe(pipe_name: str, body: AuthRequest | None = None) -> dict:
    """Start or continue a pipe's auth flow.

    Step 1: Send credentials (email, password). Returns {"ok": true} or {"needs_mfa": true}.
    Step 2: If MFA needed, send {"credentials": {"mfa_code": "123456"}} to complete.
    """
    body = body or AuthRequest()

    mod = _load_auth_module(pipe_name)
    auth_fn = getattr(mod, "authenticate", None)
    if auth_fn is None:
        return {"ok": False, "error": f"Pipe {pipe_name} has no authenticate() function"}

    # If this is an MFA completion step
    if "mfa_code" in body.credentials and pipe_name in _pending_mfa:
        return _complete_mfa(pipe_name, mod, body.credentials["mfa_code"])

    try:
        auth_fn(body.credentials)
        return {"ok": True, "message": f"Authenticated {pipe_name}"}
    except ValueError as exc:
        msg = str(exc)
        if "MFA code required" in msg:
            return {"ok": False, "needs_mfa": True, "message": "MFA code required"}
        return {"ok": False, "error": msg}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _complete_mfa(pipe_name: str, mod: object, mfa_code: str) -> dict:
    """Complete an MFA auth flow using stored session state."""
    complete_fn = getattr(mod, "complete_mfa", None)
    if complete_fn is None:
        _pending_mfa.pop(pipe_name, None)
        return {"ok": False, "error": f"Pipe {pipe_name} does not support MFA completion"}

    try:
        state = _pending_mfa.pop(pipe_name)
        complete_fn(state, mfa_code)
        return {"ok": True, "message": f"Authenticated {pipe_name}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@router.get("/{pipe_name}/fields")
def auth_fields(pipe_name: str) -> list[dict]:
    """Get the credential fields needed for a pipe's auth flow."""
    try:
        mod = _load_auth_module(pipe_name)
    except ModuleNotFoundError:
        return []
    return getattr(mod, "AUTH_FIELDS", [])


def _load_auth_module(pipe_name: str) -> object:
    importlib.invalidate_caches()
    for key in list(sys.modules):
        if key.startswith(f"shenas_pipes.{pipe_name}"):
            del sys.modules[key]
    return importlib.import_module(f"shenas_pipes.{pipe_name}.auth")
