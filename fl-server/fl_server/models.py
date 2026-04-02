"""Model weight storage and versioning.

Stores serialized model weights on the filesystem, one directory per task,
with monotonically increasing round numbers.

    weights/
      sleep-forecast/
        round-000.npz
        round-001.npz
        latest -> round-001.npz
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS_DIR = Path(".shenas-fl/weights")


class ModelStore:
    """Filesystem-backed storage for global model weights."""

    def __init__(self, weights_dir: Path = DEFAULT_WEIGHTS_DIR) -> None:
        self._dir = weights_dir

    def _task_dir(self, task_name: str) -> Path:
        d = self._dir / task_name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save(
        self,
        task_name: str,
        round_num: int,
        weights: list[np.ndarray],
        *,
        num_clients: int = 0,
        metrics: dict | None = None,
    ) -> Path:
        """Save weights for a completed round. Returns the saved path."""
        task_dir = self._task_dir(task_name)
        path = task_dir / f"round-{round_num:03d}.npz"
        np.savez(path, *weights)
        # Update symlink to latest
        latest = task_dir / "latest.npz"
        if latest.is_symlink() or latest.exists():
            latest.unlink()
        latest.symlink_to(path.name)

        # Write version metadata
        meta_path = task_dir / f"round-{round_num:03d}.json"
        meta = {
            "round": round_num,
            "task": task_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "num_clients": num_clients,
            "num_arrays": len(weights),
            "shapes": [list(w.shape) for w in weights],
            "total_params": sum(w.size for w in weights),
            "metrics": metrics or {},
        }
        meta_path.write_text(json.dumps(meta, indent=2))

        logger.info("Saved weights for %s round %d (%d arrays, %d clients)", task_name, round_num, len(weights), num_clients)
        return path

    def load_latest(self, task_name: str) -> list[np.ndarray] | None:
        """Load the latest weights for a task. Returns None if no weights exist."""
        latest = self._task_dir(task_name) / "latest.npz"
        if not latest.exists():
            return None
        data = np.load(latest)
        return [data[k] for k in sorted(data.files)]

    def load_round(self, task_name: str, round_num: int) -> list[np.ndarray] | None:
        """Load weights for a specific round."""
        path = self._task_dir(task_name) / f"round-{round_num:03d}.npz"
        if not path.exists():
            return None
        data = np.load(path)
        return [data[k] for k in sorted(data.files)]

    def latest_round(self, task_name: str) -> int | None:
        """Return the latest round number, or None if no rounds completed."""
        task_dir = self._task_dir(task_name)
        rounds = sorted(task_dir.glob("round-*.npz"))
        if not rounds:
            return None
        # round-003.npz -> 3
        return int(rounds[-1].stem.split("-")[1])

    def get_round_meta(self, task_name: str, round_num: int) -> dict | None:
        """Load metadata for a specific round."""
        meta_path = self._task_dir(task_name) / f"round-{round_num:03d}.json"
        if not meta_path.exists():
            return None
        return json.loads(meta_path.read_text())

    def history(self, task_name: str) -> list[dict]:
        """Return version history for a task (all rounds with metadata)."""
        task_dir = self._task_dir(task_name)
        history = []
        for meta_path in sorted(task_dir.glob("round-*.json")):
            try:
                history.append(json.loads(meta_path.read_text()))
            except Exception:
                continue
        return history
