"""Chrome source -- extracts browsing history from local SQLite databases."""

from __future__ import annotations

import logging
import platform
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from shenas_plugins.core.base_config import SourceConfig
from shenas_plugins.core.table import Field
from shenas_sources.core.source import Source

logger = logging.getLogger("shenas.sources.chrome")


def _default_profile_dir() -> str:
    """Return the default Chrome profile directory for the current platform."""
    home = Path.home()
    system = platform.system()
    if system == "Linux":
        return str(home / ".config" / "google-chrome" / "Default")
    if system == "Darwin":
        return str(home / "Library" / "Application Support" / "Google" / "Chrome" / "Default")
    if system == "Windows":
        return str(home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default")
    return ""


class ChromeSource(Source):
    name = "chrome"
    display_name = "Chrome"
    primary_table = "visits"
    description = (
        "Extracts browsing history, downloads, and search terms from a local "
        "Google Chrome profile.\n\n"
        "Reads Chrome's SQLite History database directly from disk. Chrome "
        "locks the database while running, so the file is copied to a "
        "temporary location before reading. No API auth needed -- just "
        "configure the profile directory path."
    )

    @dataclass
    class Config(SourceConfig):
        profile_dir: (
            Annotated[
                str,
                Field(
                    db_type="VARCHAR",
                    description="Path to Chrome profile directory (contains History SQLite file)",
                    ui_widget="text",
                    example_value="~/.config/google-chrome/Default",
                ),
            ]
            | None
        ) = None

    def _get_profile_dir(self) -> str:
        """Return the configured profile directory, falling back to platform default."""
        row = self.Config.read_row()
        configured = row.get("profile_dir") if row else None
        if configured:
            return str(Path(configured).expanduser())
        default = _default_profile_dir()
        if default:
            return default
        msg = "Chrome profile directory not configured. Set it in the Config tab."
        raise RuntimeError(msg)

    def build_client(self) -> Any:
        """Copy Chrome's History database to a temp file to avoid lock conflicts."""
        profile_dir = self._get_profile_dir()
        history_db = Path(profile_dir) / "History"
        if not history_db.exists():
            msg = f"Chrome History database not found at {history_db}"
            raise RuntimeError(msg)

        tmp_dir = tempfile.mkdtemp(prefix="shenas_chrome_")
        tmp_path = Path(tmp_dir) / "History"
        shutil.copy2(str(history_db), str(tmp_path))
        logger.info("Copied Chrome History to %s", tmp_path)
        return str(tmp_path)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.chrome.tables import TABLES

        return [t.to_resource(client) for t in TABLES]

    def sync(
        self,
        *,
        full_refresh: bool = False,
        on_progress: Any = None,
        **_kwargs: Any,
    ) -> None:
        """Sync with temp-file cleanup after the base sync completes."""
        client = self.build_client()
        try:
            from shenas_sources.core.as_of import apply_as_of_macros
            from shenas_sources.core.cli import run_sync
            from shenas_sources.core.db import connect

            res = self.resources(client)
            run_sync(self.name, self.name, res, full_refresh, self._auto_transform, on_progress=on_progress)
            try:
                con = connect()
                try:
                    apply_as_of_macros(con, self.name)
                finally:
                    con.close()
            except Exception:
                logger.exception("Failed to refresh AS-OF macros for %s", self.name)
            self._mark_synced()
            self._log_sync_event(full_refresh)
        finally:
            Path(client).unlink(missing_ok=True)
