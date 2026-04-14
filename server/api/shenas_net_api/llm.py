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

import logging
import os
import time
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from shenas_net_api.auth import get_current_user
from shenas_net_api.db import get_conn

log = logging.getLogger("shenas-net-api.llm")

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


def _parse_request_meta(body: bytes) -> dict:
    """Extract logging metadata from an LLM proxy request body."""
    import json

    try:
        req_data = json.loads(body)
        tools = [t.get("name", "?") for t in req_data.get("tools", [])]
        tool_choice = req_data.get("tool_choice", {})
        return {
            "model": req_data.get("model", "unknown"),
            "max_tokens": req_data.get("max_tokens", "?"),
            "tools": tools,
            "forced_tool": tool_choice.get("name", "") if isinstance(tool_choice, dict) else "",
            "msg_chars": sum(len(str(m.get("content", ""))) for m in req_data.get("messages", [])),
            "sys_chars": len(str(req_data.get("system", ""))),
        }
    except Exception:
        return {"model": "?", "max_tokens": "?", "tools": [], "forced_tool": "", "msg_chars": 0, "sys_chars": 0}


@router.post("/messages", response_model=None)
async def proxy_messages(request: Request) -> StreamingResponse | dict:
    """Proxy a request to Anthropic's /v1/messages endpoint."""

    if not ANTHROPIC_API_KEY:
        log.warning("LLM proxy called but ANTHROPIC_API_KEY not configured")
        raise HTTPException(status_code=503, detail="LLM service not configured")

    user = await _require_user(request)
    user_id = user["id"]
    email = user.get("email", "unknown")

    # Check usage limit
    used, limit = _get_monthly_usage(user_id)
    if used >= limit:
        log.warning("Rate limit hit for %s: %d/%d tokens used", email, used, limit)
        raise HTTPException(
            status_code=429,
            detail=f"Monthly token limit reached ({used:,}/{limit:,}). Upgrade your plan.",
        )

    body = await request.body()
    meta = _parse_request_meta(body)

    log.info(
        "LLM request: user=%s model=%s max_tokens=%s tools=[%s] forced=%s system=%d chars messages=%d chars (usage %d/%d)",
        email,
        meta["model"],
        meta["max_tokens"],
        ", ".join(meta["tools"]),
        meta["forced_tool"] or "-",
        meta["sys_chars"],
        meta["msg_chars"],
        used,
        limit,
    )

    # Forward to Anthropic
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{ANTHROPIC_BASE}/v1/messages",
                content=body,
                headers=headers,
            )
    except httpx.TimeoutException:
        elapsed = (time.monotonic() - start) * 1000
        log.exception("LLM request timed out after %.0fms for %s", elapsed, email)
        raise HTTPException(status_code=504, detail="LLM request timed out")
    except httpx.ConnectError:
        log.exception("LLM connection failed for %s", email)
        raise HTTPException(status_code=502, detail="Failed to connect to LLM provider")

    elapsed = (time.monotonic() - start) * 1000

    # Record usage from response
    if resp.status_code == 200:
        try:
            data = resp.json()
            usage = data.get("usage", {})
            input_t = usage.get("input_tokens", 0)
            output_t = usage.get("output_tokens", 0)
            cache_read = usage.get("cache_read_input_tokens", 0)
            cache_create = usage.get("cache_creation_input_tokens", 0)
            stop = data.get("stop_reason", "?")
            tool_calls = [b.get("name", "?") for b in data.get("content", []) if b.get("type") == "tool_use"]
            _record_usage(user_id, input_t, output_t)
            log.info(
                "LLM response: %d input + %d output tokens (cache read=%d create=%d) stop=%s tools_called=[%s] %.0fms user=%s",
                input_t,
                output_t,
                cache_read,
                cache_create,
                stop,
                ", ".join(tool_calls),
                elapsed,
                email,
            )
        except Exception:
            log.warning("LLM response 200 but failed to parse usage (%.0fms)", elapsed)
    else:
        # Log error responses
        error_body = ""
        try:
            error_data = resp.json()
            error_body = error_data.get("error", {}).get("message", resp.text[:200])
        except Exception:
            error_body = resp.text[:200]
        log.error(
            "LLM error: status=%d %.0fms user=%s error=%s",
            resp.status_code,
            elapsed,
            email,
            error_body,
        )

    return StreamingResponse(
        content=iter([resp.content]),
        status_code=resp.status_code,
        headers={"content-type": resp.headers.get("content-type", "application/json")},
    )


@router.get("/usage/all")
async def get_all_usage(request: Request) -> list[dict]:
    """Return LLM usage for all users (admin only)."""
    from shenas_net_api.auth import require_admin

    await require_admin(request)
    month = datetime.now(UTC).strftime("%Y-%m")
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT u.email, u.name, l.month, l.tokens_used, l.monthly_limit"
            " FROM llm_usage l JOIN users u ON l.user_id = u.id"
            " ORDER BY l.month DESC, l.tokens_used DESC",
        ).fetchall()
    # Also include users with no usage this month
    with get_conn() as conn:
        all_users = conn.execute("SELECT id, email, name FROM users").fetchall()
    user_months: set[tuple[str, str]] = {(r["email"], r["month"]) for r in rows}
    result = [dict(r) for r in rows]
    result.extend(
        {
            "email": u["email"],
            "name": u["name"],
            "month": month,
            "tokens_used": 0,
            "monthly_limit": DEFAULT_MONTHLY_LIMIT,
        }
        for u in all_users
        if (u["email"], month) not in user_months
    )
    return result


@router.get("/usage")
async def get_usage(request: Request) -> dict:
    """Return the current user's LLM usage for this month."""
    user = await _require_user(request)
    used, limit = _get_monthly_usage(user["id"])
    log.info("Usage query: %s %d/%d tokens", user.get("email"), used, limit)
    return {
        "tokens_used": used,
        "monthly_limit": limit,
        "remaining": max(0, limit - used),
        "month": datetime.now(UTC).strftime("%Y-%m"),
    }
