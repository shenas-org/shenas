"""Firefox source -- extracts browsing data from local places.sqlite."""

from __future__ import annotations

import configparser
import logging
import platform
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source

logger = logging.getLogger("shenas.sources.firefox")


def _resolve_profile_path(base: Path, cfg: configparser.ConfigParser, section: str) -> str:
    """Resolve a profile path from a profiles.ini section."""
    path = cfg.get(section, "Path", fallback="")
    if not path:
        return ""
    if cfg.get(section, "IsRelative", fallback="1") == "1":
        return str(base / path)
    return path


def _find_default_profile() -> str:
    """Auto-detect the default Firefox profile directory from profiles.ini."""
    bases = {
        "Linux": Path.home() / ".mozilla" / "firefox",
        "Darwin": Path.home() / "Library" / "Application Support" / "Firefox",
        "Windows": Path.home() / "AppData" / "Roaming" / "Mozilla" / "Firefox",
    }
    base = bases.get(platform.system())
    if not base:
        return ""

    ini = base / "profiles.ini"
    if not ini.exists():
        return ""

    cfg = configparser.ConfigParser()
    cfg.read(str(ini))

    profile_sections = [s for s in cfg.sections() if s.startswith("Profile")]

    # Prefer the section with Default=1
    for section in profile_sections:
        if cfg.get(section, "Default", fallback="") == "1":
            return _resolve_profile_path(base, cfg, section)

    # Fallback: first profile with a path
    for section in profile_sections:
        result = _resolve_profile_path(base, cfg, section)
        if result:
            return result
    return ""


class FirefoxSource(Source):
    name = "firefox"
    display_name = "Firefox"
    primary_table = "visits"
    entity_types: ClassVar[list[str]] = ["device"]
    description = (
        "Extracts browsing history and bookmarks from a local Firefox profile.\n\n"
        "Reads Firefox's SQLite places.sqlite database directly from disk. "
        "The file is copied to a temporary location before reading to avoid "
        "lock conflicts. No API auth needed -- just configure the profile "
        "directory path (auto-detected by default)."
    )

    @dataclass
    class Config(SourceConfig):
        profile_dir: (
            Annotated[
                str,
                Field(
                    db_type="VARCHAR",
                    description="Path to Firefox profile directory (contains places.sqlite)",
                    ui_widget="text",
                    example_value="~/.mozilla/firefox/xxxxxxxx.default-release",
                ),
            ]
            | None
        ) = None

    def _get_profile_dir(self) -> str:
        row = self.Config.read_row()
        configured = row.get("profile_dir") if row else None
        if configured:
            return str(Path(configured).expanduser())
        default = _find_default_profile()
        if default:
            return default
        msg = "Firefox profile directory not found. Set it in the Config tab."
        raise RuntimeError(msg)

    def build_client(self) -> Any:
        """Copy places.sqlite to a temp file to avoid lock conflicts."""
        profile_dir = self._get_profile_dir()
        places_db = Path(profile_dir) / "places.sqlite"
        if not places_db.exists():
            msg = f"Firefox places.sqlite not found at {places_db}"
            raise RuntimeError(msg)

        tmp_dir = tempfile.mkdtemp(prefix="shenas_firefox_")
        tmp_path = Path(tmp_dir) / "places.sqlite"
        shutil.copy2(str(places_db), str(tmp_path))
        logger.info("Copied Firefox places.sqlite to %s", tmp_path)
        return str(tmp_path)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.firefox.tables import TABLES

        return [t.to_resource(client) for t in TABLES]

    def sync(
        self,
        *,
        full_refresh: bool = False,
        on_progress: Any = None,
        **_kwargs: Any,
    ) -> None:
        """Sync with temp-file cleanup after completion."""
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
