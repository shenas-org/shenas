"""LLM inference backends: local (llama.cpp) and cloud (shenas.net proxy)."""

from __future__ import annotations

import abc
import logging
import os
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from app.llm.models import Model

log = logging.getLogger(f"shenas.{__name__}")

SHENAS_NET_URL = os.environ.get("SHENAS_NET_URL", "https://shenas.net")


def _get_remote_token() -> str | None:
    """Look up the current user's shenas.net token.

    Lazy-imports app.db to avoid circular imports at module load time.
    An SHENAS_REMOTE_TOKEN env var wins if set (used by tests).
    """
    if env := os.environ.get("SHENAS_REMOTE_TOKEN"):
        return env
    try:
        from app.db import current_user_id, cursor

        uid = current_user_id.get()
        if not uid:
            return None
        with cursor(database="shenas") as cur:
            row = cur.execute(
                "SELECT remote_token FROM shenas_system.local_users WHERE id = ?",
                [uid],
            ).fetchone()
        return row[0] if row and row[0] else None
    except Exception:
        return None


class Backend(abc.ABC):
    """One LLM provider invocation. Stateful (singletons OK)."""

    name: str  # short identifier persisted as llm_cache.model

    @classmethod
    def from_config(cls, config: dict) -> Backend:
        backend = config.get("backend") or "local"
        if backend == "local":
            from .models import ModelStore

            return LlamaCppBackend.get(ModelStore.resolve(config.get("model_path")))
        if backend == "proxy":
            token = _get_remote_token()
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
    """Routes through the shenas.net LLM proxy at /api/llm/messages.

    Same endpoint used by ShenasNetProvider in app/graphql/llm_provider.py
    for hypothesis analysis, but without tool-use (classification is a
    plain text completion).
    """

    def __init__(self, *, token: str, model: str) -> None:
        self._token = token
        self._model = model
        self.name = f"shenas-net@{model}"

    def categorize(self, text: str, *, prompt: str) -> str | None:
        import json
        import urllib.request

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
            from llama_cpp import Llama  # ty: ignore[unresolved-import]
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
            resp: dict = self._llm.create_chat_completion(  # ty: ignore[invalid-assignment]
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
            )
            content = resp["choices"][0]["message"]["content"]
            return content.strip() if isinstance(content, str) else None
        except Exception:
            log.warning("Local LLM categorization failed for %r", text[:50])
            return None
