"""GGUF model file management."""

from __future__ import annotations

import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class Model:
    """A local GGUF model file (or a reference to one)."""

    filename: str
    url: str | None = None

    @property
    def path(self) -> Path:
        return ModelStore.dir() / self.filename

    @property
    def exists(self) -> bool:
        return self.path.exists()

    @property
    def size_bytes(self) -> int:
        return self.path.stat().st_size if self.exists else 0


@dataclass(frozen=True)
class _AbsoluteModel(Model):
    """A model referenced by an absolute path outside the store."""

    abs_path: Path = Path()

    @property
    def path(self) -> Path:
        return self.abs_path


DEFAULT_MODEL = Model(
    filename="gemma-3-4b-it-q4_k_m.gguf",
    url="https://huggingface.co/unsloth/gemma-3-4b-it-GGUF/resolve/main/gemma-3-4b-it-Q4_K_M.gguf",
)


class ModelStore:
    """File-system store for local GGUF model files."""

    @staticmethod
    def dir() -> Path:
        """Return the models directory. ~/.shenas/models in bundles, ./data/models in dev."""
        if getattr(sys, "_MEIPASS", None):
            return Path.home() / ".shenas" / "models"
        return Path("data") / "models"

    @classmethod
    def list_models(cls) -> list[Model]:
        d = cls.dir()
        if not d.is_dir():
            return []
        return [Model(filename=p.name) for p in sorted(d.glob("*.gguf"))]

    @classmethod
    def resolve(cls, name_or_path: str | None) -> Model:
        """Convert a config string into a Model. None returns DEFAULT_MODEL."""
        if not name_or_path:
            return DEFAULT_MODEL
        p = Path(name_or_path)
        if p.is_absolute():
            return _AbsoluteModel(filename=p.name, abs_path=p)
        return Model(filename=name_or_path)

    @classmethod
    def download(cls, model: Model, *, on_progress: Callable[[int, int], None] | None = None) -> Model:
        """Stream model.url to model.path. Atomic via .partial rename."""
        if not model.url:
            msg = f"no URL configured for model {model.filename}"
            raise RuntimeError(msg)
        cls.dir().mkdir(parents=True, exist_ok=True)
        tmp = model.path.with_suffix(model.path.suffix + ".partial")

        req = urllib.request.Request(model.url, headers={"User-Agent": "shenas"})
        with urllib.request.urlopen(req, timeout=600) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            read = 0
            with open(tmp, "wb") as f:
                while chunk := resp.read(1024 * 1024):
                    f.write(chunk)
                    read += len(chunk)
                    if on_progress:
                        on_progress(read, total)

        tmp.rename(model.path)
        return model

    @classmethod
    def remove(cls, name: str) -> None:
        Model(filename=name).path.unlink()
