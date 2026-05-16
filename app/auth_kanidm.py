"""OAuth 2.0 device-authorization-grant against Kanidm for the desktop/CLI app."""

from __future__ import annotations

import httpx

from app.config import KANIDM_CLIENT_ID, KANIDM_DEVICE_SCOPE, KANIDM_URL

_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"


def start_device_flow() -> dict:
    """Initiate device-authorization-grant with Kanidm.

    Returns the full response dict from Kanidm, including:
      device_code, user_code, verification_uri, expires_in, interval.
    """
    if not KANIDM_URL:
        raise RuntimeError("KANIDM_URL is not configured")
    resp = httpx.post(
        f"{KANIDM_URL}/oauth2/device_authorization",
        data={"client_id": KANIDM_CLIENT_ID, "scope": KANIDM_DEVICE_SCOPE},
        timeout=10,
        verify=False,
    )
    resp.raise_for_status()
    return resp.json()


def poll_device_token(device_code: str) -> dict | None:
    """Poll the Kanidm token endpoint once for device-auth-grant completion.

    Returns the token response dict on success, or None if still pending.
    Raises ValueError on terminal errors (expired, denied, etc.).
    """
    if not KANIDM_URL:
        raise RuntimeError("KANIDM_URL is not configured")
    resp = httpx.post(
        f"{KANIDM_URL}/oauth2/token",
        data={
            "grant_type": _GRANT_TYPE,
            "device_code": device_code,
            "client_id": KANIDM_CLIENT_ID,
        },
        timeout=10,
        verify=False,
    )
    if resp.status_code in (400, 428):
        err = resp.json().get("error", "unknown_error")
        if err == "authorization_pending":
            return None
        raise ValueError(f"Device token error: {err}")
    resp.raise_for_status()
    return resp.json()


def is_legacy_token(token: str) -> bool:
    """Return True if *token* looks like an old opaque shenas.ai session token (not a JWT)."""
    return token.count(".") < 2
