"""LLM proxy endpoint -- forwards requests to Anthropic with usage metering.

The local shenas app sends LLM requests here instead of calling Anthropic
directly. This endpoint:

1. Authenticates the user via Bearer token (same as other API endpoints)
2. Checks the user's monthly usage against their plan limit
3. Forwards the request to Anthropic with the server-side API key
4. Records token usage for billing
5. Returns the response verbatim

No request/response transformation -- the local app sends the exact
Anthropic API payload and gets the exact response back. The proxy is
transparent except for auth + metering.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from shenas_net_api.auth import get_current_user
from shenas_net_api.db import get_conn

router = APIRouter(prefix="/llm")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE = "https://api.anthropic.com"

# Default monthly token limit per user (input + output combined).
# Override per-user via the llm_usage.monthly_limit column.
DEFAULT_MONTHLY_LIMIT = 1_000_000


async def _require_user(request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def _get_monthly_usage(user_id: str) -> tuple[int, int]:
    """Return (tokens_used_this_month, monthly_limit) for a user."""
    month = datetime.now(UTC).strftime("%Y-%m")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT tokens_used, monthly_limit FROM llm_usage WHERE user_id = %(uid)s AND month = %(m)s",
            {"uid": user_id, "m": month},
        ).fetchone()
    if row:
        return row["tokens_used"], row["monthly_limit"]
    return 0, DEFAULT_MONTHLY_LIMIT


def _record_usage(user_id: str, input_tokens: int, output_tokens: int) -> None:
    """Increment the user's token count for the current month."""
    month = datetime.now(UTC).strftime("%Y-%m")
    total = input_tokens + output_tokens
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO llm_usage (user_id, month, tokens_used, monthly_limit) "
            "VALUES (%(uid)s, %(m)s, %(t)s, %(lim)s) "
            "ON CONFLICT (user_id, month) DO UPDATE "
            "SET tokens_used = llm_usage.tokens_used + %(t)s",
            {"uid": user_id, "m": month, "t": total, "lim": DEFAULT_MONTHLY_LIMIT},
        )


@router.post("/messages", response_model=None)
async def proxy_messages(request: Request) -> StreamingResponse | dict:
    """Proxy a request to Anthropic's /v1/messages endpoint."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="LLM service not configured")

    user = await _require_user(request)
    user_id = user["id"]

    # Check usage limit
    used, limit = _get_monthly_usage(user_id)
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly token limit reached ({used:,}/{limit:,}). Upgrade your plan.",
        )

    body = await request.body()

    # Forward to Anthropic
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{ANTHROPIC_BASE}/v1/messages",
            content=body,
            headers=headers,
        )

    # Record usage from response
    if resp.status_code == 200:
        try:
            data = resp.json()
            usage = data.get("usage", {})
            _record_usage(
                user_id,
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
            )
        except Exception:
            pass

    return StreamingResponse(
        content=iter([resp.content]),
        status_code=resp.status_code,
        headers={"content-type": resp.headers.get("content-type", "application/json")},
    )


@router.get("/usage")
async def get_usage(request: Request) -> dict:
    """Return the current user's LLM usage for this month."""
    user = await _require_user(request)
    used, limit = _get_monthly_usage(user["id"])
    return {
        "tokens_used": used,
        "monthly_limit": limit,
        "remaining": max(0, limit - used),
        "month": datetime.now(UTC).strftime("%Y-%m"),
    }
