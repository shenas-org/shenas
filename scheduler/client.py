"""Minimal HTTP client for the scheduler -- talks to the shenas server REST API."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from collections.abc import Iterator


class ShenasServerError(Exception):
    """Raised when the server returns a non-2xx response or is unreachable."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Server error {status_code}: {detail}")


class SchedulerClient:
    """HTTP client with only the endpoints the scheduler needs."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self._client = httpx.Client(base_url=base_url, verify=False, timeout=30.0)

    def get_sync_schedule(self) -> list[dict[str, Any]]:
        try:
            resp = self._client.post(
                "/api/graphql",
                json={"query": "{ syncSchedule { name syncFrequency syncedAt isDue } }"},
            )
        except (httpx.ConnectError, httpx.ConnectTimeout):
            raise ShenasServerError(0, f"Cannot reach server at {self.base_url}")
        if resp.status_code >= 400:
            raise ShenasServerError(resp.status_code, resp.text)
        body = resp.json()
        if body.get("errors"):
            detail = "; ".join(e.get("message", str(e)) for e in body["errors"])
            raise ShenasServerError(resp.status_code, detail)
        return body["data"]["syncSchedule"]

    def sync_source(self, name: str) -> Iterator[dict[str, Any]]:
        try:
            with self._client.stream(
                "POST",
                f"/api/sync/{name}",
                json={},
                timeout=httpx.Timeout(connect=30.0, read=3600.0, write=30.0, pool=30.0),
            ) as resp:
                if resp.status_code >= 400:
                    resp.read()
                    raise ShenasServerError(resp.status_code, resp.text)
                event_type = "message"
                for line in resp.iter_lines():
                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        data: dict[str, Any] = json.loads(line[5:].strip())
                        data["_event"] = event_type
                        yield data
                        event_type = "message"
        except (httpx.ConnectError, httpx.ConnectTimeout):
            raise ShenasServerError(0, f"Cannot reach server at {self.base_url}")
