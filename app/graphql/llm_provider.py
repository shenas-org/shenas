"""LLM provider lookup for the GraphQL layer.

Routes to either:
1. **ShenasNetProvider** -- if the user has a remote_token (premium via shenas.net proxy)
2. **AnthropicProvider** -- if ANTHROPIC_API_KEY is set (self-hosted)
3. Error -- if neither is available
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from shenas_plugins.core.analytics import AnthropicProvider, LLMProvider

SHENAS_NET_URL = os.environ.get("SHENAS_NET_URL", "https://shenas.net")


class ShenasNetProvider:
    """LLM provider that proxies through shenas.net instead of calling Anthropic directly."""

    name: str

    def __init__(self, *, token: str, model: str = "claude-sonnet-4-6") -> None:
        self.token = token
        self.model = model
        self.name = f"shenas-net@{model}"
        self.last_input_tokens: int = 0
        self.last_output_tokens: int = 0

    def ask(self, *, system: str, user: str, tools: list[dict[str, Any]], tool_name: str | None = None) -> dict[str, Any]:
        forced_name = tool_name or (tools[0]["name"] if tools else None)
        payload = json.dumps(
            {
                "model": self.model,
                "max_tokens": 4096,
                "system": system,
                "messages": [{"role": "user", "content": user}],
                "tools": tools,
                "tool_choice": {"type": "tool", "name": forced_name} if forced_name else {"type": "auto"},
            }
        ).encode()

        req = urllib.request.Request(
            f"{SHENAS_NET_URL}/api/llm/messages",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode() if exc.fp else ""
            msg = f"shenas.net LLM proxy error: {exc.code} -- {body}"
            raise RuntimeError(msg) from exc

        usage = data.get("usage", {})
        self.last_input_tokens = int(usage.get("input_tokens", 0))
        self.last_output_tokens = int(usage.get("output_tokens", 0))

        for block in data.get("content", []):
            if block.get("type") == "tool_use" and (not forced_name or block.get("name") == forced_name):
                return dict(block.get("input", {}))

        msg = f"LLM did not call {forced_name}; got {data.get('content', [])!r}"
        raise RuntimeError(msg)


def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider for hypothesis-driven analysis.

    Priority:
    1. If the current user has a remote_token -> ShenasNetProvider (premium proxy)
    2. If ANTHROPIC_API_KEY env var is set -> AnthropicProvider (self-hosted)
    3. Otherwise -> error
    """
    model = os.environ.get("SHENAS_LLM_MODEL", "claude-sonnet-4-6")

    # Check for premium (remote_token on the current local user)
    try:
        from app.db import current_user_id, cursor

        uid = current_user_id.get()
        if uid:
            with cursor(database="shenas") as cur:
                row = cur.execute(
                    "SELECT remote_token FROM shenas_system.local_users WHERE id = ?",
                    [uid],
                ).fetchone()
                if row and row[0]:
                    return ShenasNetProvider(token=row[0], model=model)  # type: ignore[return-value]
    except Exception:
        pass

    # Fall back to direct Anthropic API key
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicProvider(model=model)

    msg = "No LLM provider available. Set ANTHROPIC_API_KEY or sign in to shenas.net for premium access."
    raise RuntimeError(msg)
