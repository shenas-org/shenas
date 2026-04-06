"""HTTP client for the shenas GraphQL + REST API."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from collections.abc import Iterator

DEFAULT_SERVER_URL = "https://localhost:7280"


class ShenasServerError(Exception):
    """Raised when the server returns a non-2xx response or is unreachable."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Server error {status_code}: {detail}")


def _connect_error(base_url: str) -> ShenasServerError:
    return ShenasServerError(0, f"Cannot reach shenas server at {base_url}. Start it with: shenas serve")


class ShenasClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.environ.get("SHENAS_SERVER_URL", DEFAULT_SERVER_URL)
        self._client = httpx.Client(base_url=self.base_url, verify=False, timeout=30.0)
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

            HTTPXClientInstrumentor.instrument_client(self._client)
        except ImportError:
            pass

    def close(self) -> None:
        self._client.close()

    def _graphql(self, query: str, variables: dict[str, Any] | None = None) -> Any:
        """Execute a GraphQL query/mutation and return the data dict."""
        try:
            resp = self._client.post("/api/graphql", json={"query": query, "variables": variables or {}})
        except (httpx.ConnectError, httpx.ConnectTimeout):
            raise _connect_error(self.base_url)
        body = resp.json()
        if body.get("errors"):
            detail = "; ".join(e.get("message", str(e)) for e in body["errors"])
            raise ShenasServerError(resp.status_code, detail)
        return body.get("data")

    def _stream_sse(self, method: str, path: str, **kwargs: Any) -> Iterator[dict[str, Any]]:
        """Stream Server-Sent Events, yielding parsed data dicts."""
        import json

        try:
            with self._client.stream(
                method, path, timeout=httpx.Timeout(connect=30.0, read=3600.0, write=30.0, pool=30.0), **kwargs
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
            raise _connect_error(self.base_url)

    def is_server_running(self) -> bool:
        try:
            self._client.get("/api/health")
            return True
        except (httpx.ConnectError, httpx.ConnectTimeout):
            return False

    # --- Auth ---

    def source_auth_fields(self, name: str) -> dict[str, Any]:
        data = self._graphql(
            "query($pipe: String!) { authFields(pipe: $pipe) { fields { name prompt hide } instructions stored } }",
            {"pipe": name},
        )
        return data["authFields"]

    def source_auth(self, name: str, credentials: dict[str, str]) -> dict[str, Any]:
        data = self._graphql(
            "mutation($pipe: String!, $creds: JSON!) {"
            " authenticate(pipe: $pipe, credentials: $creds)"
            " { ok message error needsMfa oauthUrl } }",
            {"pipe": name, "creds": credentials},
        )
        return data["authenticate"]

    # --- Config ---

    def config_list(self, kind: str, name: str | None = None) -> list[dict[str, Any]]:
        data = self._graphql(
            "query($kind: String!) { plugins(kind: $kind) { name hasConfig configEntries { key label value description } } }",
            {"kind": kind},
        )
        result = []
        for p in data["plugins"]:
            if not p["hasConfig"]:
                continue
            if name and p["name"] != name:
                continue
            result.append({"kind": kind, "name": p["name"], "entries": p["configEntries"]})
        return result

    def config_get(self, kind: str, name: str, key: str) -> dict[str, str]:
        data = self._graphql(
            "query($kind: String!, $name: String!, $key: String!) { configValue(kind: $kind, name: $name, key: $key) }",
            {"kind": kind, "name": name, "key": key},
        )
        return {"key": key, "value": data["configValue"]}

    def config_set(self, kind: str, name: str, key: str, value: str) -> dict[str, Any]:
        data = self._graphql(
            "mutation($kind: String!, $name: String!, $key: String!, $value: String!)"
            " { setConfig(kind: $kind, name: $name, key: $key, value: $value) { ok } }",
            {"kind": kind, "name": name, "key": key, "value": value},
        )
        return data["setConfig"]

    def config_delete(self, kind: str, name: str, key: str | None = None) -> dict[str, Any]:
        if key:
            data = self._graphql(
                "mutation($kind: String!, $name: String!, $key: String!)"
                " { deleteConfigKey(kind: $kind, name: $name, key: $key) { ok } }",
                {"kind": kind, "name": name, "key": key},
            )
            return data["deleteConfigKey"]
        data = self._graphql(
            "mutation($kind: String!, $name: String!) { deleteConfig(kind: $kind, name: $name) { ok } }",
            {"kind": kind, "name": name},
        )
        return data["deleteConfig"]

    # --- DB ---

    def db_status(self) -> dict[str, Any]:
        data = self._graphql(
            "{ dbStatus { keySource dbPath sizeMb schemas { name tables { name rows cols earliest latest } } } }"
        )
        return data["dbStatus"]

    def db_keygen(self) -> dict[str, Any]:
        data = self._graphql("mutation { generateDbKey { ok } }")
        return data["generateDbKey"]

    # --- Plugins ---

    def plugins_list(self, kind: str) -> list[dict[str, str]]:
        data = self._graphql(
            "query($kind: String!) { plugins(kind: $kind) { name displayName"
            " package version signature description commands enabled hasAuth"
            " syncFrequency addedAt updatedAt statusChangedAt syncedAt } }",
            {"kind": kind},
        )
        return data["plugins"]

    def plugins_add(
        self, kind: str, names: list[str], index_url: str | None = None, skip_verify: bool = False
    ) -> dict[str, Any]:
        data = self._graphql(
            "mutation($kind: String!, $names: [String!]!, $indexUrl: String,"
            " $skipVerify: Boolean) { installPlugins(kind: $kind, names: $names,"
            " indexUrl: $indexUrl, skipVerify: $skipVerify)"
            " { results { name ok message } } }",
            {"kind": kind, "names": names, "indexUrl": index_url, "skipVerify": skip_verify},
        )
        return data["installPlugins"]

    def plugins_remove(self, kind: str, name: str) -> dict[str, Any]:
        data = self._graphql(
            "mutation($kind: String!, $name: String!) { removePlugin(kind: $kind, name: $name) { ok message } }",
            {"kind": kind, "name": name},
        )
        return data["removePlugin"]

    def plugins_info(self, kind: str, name: str) -> dict[str, Any]:
        data = self._graphql(
            "query($kind: String!, $name: String!) { pluginInfo(kind: $kind, name: $name) }",
            {"kind": kind, "name": name},
        )
        return data["pluginInfo"]

    def plugins_enable(self, kind: str, name: str) -> dict[str, Any]:
        data = self._graphql(
            "mutation($kind: String!, $name: String!) { enablePlugin(kind: $kind, name: $name) { ok message } }",
            {"kind": kind, "name": name},
        )
        return data["enablePlugin"]

    def plugins_disable(self, kind: str, name: str) -> dict[str, Any]:
        data = self._graphql(
            "mutation($kind: String!, $name: String!) { disablePlugin(kind: $kind, name: $name) { ok message } }",
            {"kind": kind, "name": name},
        )
        return data["disablePlugin"]

    # --- Sync (SSE -- stays REST) ---

    def sync_all(self) -> Iterator[dict[str, Any]]:
        return self._stream_sse("POST", "/api/sync")

    def sync_source(
        self, name: str, start_date: str | None = None, full_refresh: bool = False, **extra: str | int | bool
    ) -> Iterator[dict[str, Any]]:
        body: dict[str, object] = {}
        if start_date:
            body["start_date"] = start_date
        if full_refresh:
            body["full_refresh"] = True
        if extra:
            body["extra"] = extra
        return self._stream_sse("POST", f"/api/sync/{name}", json=body)

    # --- Schedule ---

    def get_sync_schedule(self) -> list[dict[str, Any]]:
        data = self._graphql("{ syncSchedule { name syncFrequency syncedAt isDue } }")
        return data["syncSchedule"]
