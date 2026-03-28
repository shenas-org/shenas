"""HTTP client for the shenas REST API."""

import os
from collections.abc import Iterator

import httpx

DEFAULT_SERVER_URL = "https://localhost:7280"


class ShenasServerError(Exception):
    """Raised when the server returns a non-2xx response or is unreachable."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Server error {status_code}: {detail}")


def _connect_error(base_url: str) -> ShenasServerError:
    return ShenasServerError(0, f"Cannot reach shenas server at {base_url}. Start it with: shenas serve")


class ShenasClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or os.environ.get("SHENAS_SERVER_URL", DEFAULT_SERVER_URL)
        self._client = httpx.Client(base_url=self.base_url, verify=False, timeout=30.0)
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

            HTTPXClientInstrumentor.instrument_client(self._client)
        except ImportError:
            pass

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, path: str, **kwargs):  # noqa: ANN202
        try:
            resp = self._client.request(method, path, **kwargs)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            raise _connect_error(self.base_url)
        if resp.status_code >= 400:
            try:
                body = resp.json()
                detail = body.get("detail") or body.get("error", resp.text)
            except Exception:
                detail = resp.text
            raise ShenasServerError(resp.status_code, detail)
        return resp.json()

    def _stream_sse(self, method: str, path: str, **kwargs) -> Iterator[dict]:
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
                        data = json.loads(line[5:].strip())
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

    # --- Pipes ---

    def pipes_list(self) -> list[dict]:
        return self._request("GET", "/api/pipes")

    def pipe_auth_fields(self, name: str) -> list[dict]:
        return self._request("GET", f"/api/auth/{name}/fields")

    def pipe_auth(self, name: str, credentials: dict[str, str]) -> dict:
        return self._request("POST", f"/api/auth/{name}", json={"credentials": credentials})

    # --- Config ---

    def config_list(self, kind: str | None = None, name: str | None = None) -> list[dict]:
        params = {}
        if kind:
            params["kind"] = kind
        if name:
            params["name"] = name
        return self._request("GET", "/api/config", params=params)

    def config_get(self, kind: str, name: str, key: str) -> dict:
        return self._request("GET", f"/api/config/{kind}/{name}/{key}")

    def config_set(self, kind: str, name: str, key: str, value: str) -> dict:
        return self._request("PUT", f"/api/config/{kind}/{name}", json={"key": key, "value": value})

    def config_delete(self, kind: str, name: str, key: str | None = None) -> dict:
        if key:
            return self._request("DELETE", f"/api/config/{kind}/{name}/{key}")
        return self._request("DELETE", f"/api/config/{kind}/{name}")

    # --- DB ---

    def db_status(self) -> dict:
        return self._request("GET", "/api/db/status")

    def db_keygen(self) -> dict:
        return self._request("POST", "/api/db/keygen")

    # --- Packages ---

    def packages_list(self, kind: str) -> list[dict]:
        return self._request("GET", f"/api/packages/{kind}")

    def packages_add(self, kind: str, names: list[str], index_url: str | None = None, skip_verify: bool = False) -> dict:
        body: dict = {"names": names, "skip_verify": skip_verify}
        if index_url:
            body["index_url"] = index_url
        return self._request("POST", f"/api/packages/{kind}", json=body)

    def packages_remove(self, kind: str, name: str) -> dict:
        return self._request("DELETE", f"/api/packages/{kind}/{name}")

    # --- Sync ---

    def sync_all(self) -> Iterator[dict]:
        return self._stream_sse("POST", "/api/sync")

    def sync_pipe(
        self, name: str, start_date: str | None = None, full_refresh: bool = False, **extra: str | int | bool
    ) -> Iterator[dict]:
        body: dict = {}
        if start_date:
            body["start_date"] = start_date
        if full_refresh:
            body["full_refresh"] = True
        if extra:
            body["extra"] = extra
        return self._stream_sse("POST", f"/api/sync/{name}", json=body)
