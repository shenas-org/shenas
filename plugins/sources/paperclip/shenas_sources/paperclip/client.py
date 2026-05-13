"""Read-only Paperclip REST API client.

Only GET methods are exposed. POST/PATCH/PUT/DELETE are intentionally
omitted — this client is a read-only observer of the Paperclip control
plane.
"""

from __future__ import annotations

from typing import Any

import httpx


class PaperclipClient:
    """HTTP client for the Paperclip REST API (read-only)."""

    def __init__(self, api_url: str, api_key: str) -> None:
        self._http = httpx.Client(
            base_url=api_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    def close(self) -> None:
        self._http.close()

    def _get(self, path: str, **params: Any) -> Any:
        resp = self._http.get(path, params=params or None)
        resp.raise_for_status()
        return resp.json()

    def get_me(self) -> dict[str, Any]:
        """Validate credentials and return the agent identity."""
        return self._get("/api/agents/me")

    def get_company(self, company_id: str) -> dict[str, Any]:
        return self._get(f"/api/companies/{company_id}")

    def get_agents(self, company_id: str) -> list[dict[str, Any]]:
        data = self._get(f"/api/companies/{company_id}/agents")
        if isinstance(data, list):
            return data
        return data.get("agents") or data.get("data") or []

    def get_projects(self, company_id: str) -> list[dict[str, Any]]:
        data = self._get(f"/api/companies/{company_id}/projects")
        if isinstance(data, list):
            return data
        return data.get("projects") or data.get("data") or []
