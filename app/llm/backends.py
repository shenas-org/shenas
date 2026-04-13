"""LLM inference backends: local (llama.cpp) and cloud (shenas.net proxy).

All cloud LLM calls go through the shenas.net proxy. The user must be
signed in (remote_token stored) for cloud features to work.
"""

from __future__ import annotations

import abc
import json
import logging
import urllib.error
import urllib.request
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

from app.config import SHENAS_NET_URL

if TYPE_CHECKING:
    from app.llm.models import Model

log = logging.getLogger(f"shenas.{__name__}")

# -- LLM provider protocol (tool-use interface) ----------------------------


class LLMProvider(Protocol):
    """Minimal interface for tool-use LLM calls (hypothesis analysis, suggestions)."""

    name: str
    last_input_tokens: int
    last_output_tokens: int

    def ask(self, *, system: str, user: str, tools: list[dict[str, Any]], tool_name: str | None = None) -> dict[str, Any]:
        """Send prompt + tools to the LLM and return the parsed tool-use payload."""
        ...


class FakeProvider:
    """In-process provider for tests. Returns a pre-canned payload."""

    name: ClassVar[str] = "fake@v0"

    def __init__(self, payload: dict[str, Any], *, input_tokens: int = 100, output_tokens: int = 50) -> None:
        self._payload = payload
        self._in = input_tokens
        self._out = output_tokens
        self.calls: list[tuple[str, str]] = []
        self.last_input_tokens = 0
        self.last_output_tokens = 0

    def ask(self, *, system: str, user: str, tools: list[dict[str, Any]], tool_name: str | None = None) -> dict[str, Any]:  # noqa: ARG002
        self.calls.append((system, user))
        self.last_input_tokens = self._in
        self.last_output_tokens = self._out
        return self._payload


class ShenasNetProvider:
    """LLM provider that proxies tool-use calls through shenas.net."""

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
                "max_tokens": 16384,
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


# -- Categorization backend (text classification) --------------------------


class Backend(abc.ABC):
    """LLM backend for simple text classification (no tool-use)."""

    name: str

    @classmethod
    def from_config(cls, config: dict) -> Backend:  # type: ignore[type-arg]
        backend = config.get("backend") or "local"
        if backend == "local":
            from .models import ModelStore

            return LlamaCppBackend.get(ModelStore.resolve(config.get("model_path")))
        if backend == "proxy":
            from app.local_users import LocalUser

            token = LocalUser.get_remote_token()
            if not token:
                msg = "Cloud backend requires a shenas.net account. Sign in via Settings or set backend=local."
                raise RuntimeError(msg)
            return ShenasProxyBackend(token=token, model=config.get("proxy_model") or "claude-sonnet-4-6")
        msg = f"unknown llm backend: {backend!r}"
        raise RuntimeError(msg)

    @abc.abstractmethod
    def categorize(self, text: str, *, prompt: str) -> str | None:
        raise NotImplementedError


class ShenasProxyBackend(Backend):
    """Routes classification calls through the shenas.net LLM proxy."""

    def __init__(self, *, token: str, model: str) -> None:
        self._token = token
        self._model = model
        self.name = f"shenas-net@{model}"

    def categorize(self, text: str, *, prompt: str) -> str | None:
        payload = json.dumps(
            {
                "model": self._model,
                "max_tokens": 50,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode()
        req = urllib.request.Request(
            f"{SHENAS_NET_URL}/api/llm/messages",
            data=payload,
            headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            for block in data.get("content", []):
                if block.get("type") == "text":
                    return block.get("text", "").strip()
            return None
        except Exception:
            log.warning("shenas.net proxy categorization failed for %r", text[:50])
            return None


class LlamaCppBackend(Backend):
    """In-process llama.cpp inference. One model loaded per process."""

    _loaded: ClassVar[LlamaCppBackend | None] = None

    @classmethod
    def get(cls, model: Model) -> LlamaCppBackend:
        if cls._loaded is None or cls._loaded._model.path != model.path:
            cls._loaded = cls(model)
        return cls._loaded

    def __init__(self, model: Model) -> None:
        try:
            from llama_cpp import Llama
        except ImportError as e:
            msg = "Local LLM requires llama-cpp-python. Install with: uv pip install 'shenas-app[local]'"
            raise RuntimeError(msg) from e
        if not model.exists:
            msg = f"Model not found: {model.path}. Run: shenasctl model download"
            raise RuntimeError(msg)
        self._model = model
        self._llm = Llama(model_path=str(model.path), n_ctx=512, n_gpu_layers=-1, verbose=False)
        self.name = model.filename

    def categorize(self, text: str, *, prompt: str) -> str | None:
        try:
            resp: dict = self._llm.create_chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
            )
            content = resp["choices"][0]["message"]["content"]
            return content.strip() if isinstance(content, str) else None
        except Exception:
            log.warning("Local LLM categorization failed for %r", text[:50])
            return None
