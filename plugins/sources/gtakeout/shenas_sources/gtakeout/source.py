"""Google Takeout pipe -- finds and parses Takeout archives from Google Drive."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from shenas_plugins.core.base_auth import SourceAuth
from shenas_plugins.core.base_config import SourceConfig
from shenas_plugins.core.field import Field
from shenas_sources.core.source import Source


class GTakeoutSource(Source):
    name = "gtakeout"
    display_name = "Google Takeout"
    primary_table = "photos_metadata"
    description = (
        "Finds and parses Google Takeout archives from Google Drive.\n\n"
        "Uses Google OAuth2 to search Drive for Takeout zip/tgz files, downloads "
        "them to a local cache, extracts, and parses the contents with streaming "
        "JSON parsers (ijson) for large files."
    )

    @dataclass
    class Auth(SourceAuth):
        token: (
            Annotated[
                str | None,
                Field(db_type="VARCHAR", description="Google OAuth2 credentials (JSON)", category="secret"),
            ]
            | None
        ) = None

    @dataclass
    class Config(SourceConfig):
        latest: Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Only process the N most recent archives (0 = all)",
                default="0",
                ui_widget="text",
                example_value="0",
            ),
        ] = 0
        name_filter: Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="Only process archives matching this substring (e.g. '.tgz')",
                default="",
                ui_widget="text",
                example_value=".tgz",
            ),
        ] = ""

    @property
    def auth_fields(self) -> list:  # No user input -- browser OAuth
        return []

    auth_instructions = "Click Authenticate to sign in with your Google account."

    def _google_auth(self) -> Any:
        from shenas_sources.core.google_auth import GoogleAuth

        return GoogleAuth(
            "gtakeout",
            ["https://www.googleapis.com/auth/drive.readonly"],
            "drive",
            "v3",
            auth_cls=self.Auth,
        )

    def build_client(self) -> Any:
        return self._google_auth().build_client()

    def authenticate(self, credentials: dict[str, str]) -> None:
        self._google_auth().authenticate(credentials)

    def sync(self, *, full_refresh: bool = False, **_kwargs: Any) -> None:
        """Custom sync: downloads and processes archives one at a time."""
        from shenas_sources.core.cli import run_sync
        from shenas_sources.core.db import DB_PATH
        from shenas_sources.gtakeout.drive import download_archive, extract_archive, find_takeout_archives
        from shenas_sources.gtakeout.tables import TABLES

        service = self.build_client()

        # Read config for latest/name_filter
        row = self._config_store.get(self.Config)
        latest = (row.get("latest") if row else None) or 0
        name_filter = (row.get("name_filter") if row else None) or ""

        archives = find_takeout_archives(service)
        if not archives:
            msg = (
                "No Takeout archives found on Google Drive. Go to https://takeout.google.com and export to Google Drive first."
            )
            raise RuntimeError(msg)

        if name_filter:
            archives = [a for a in archives if name_filter in a["name"]]
            if not archives:
                msg = f"No archives matching '{name_filter}'."
                raise RuntimeError(msg)

        if latest > 0:
            archives = archives[:latest]

        cache_dir = DB_PATH.parent / "takeout_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        total_size = sum(a["size"] for a in archives)
        total_mb = total_size / (1024 * 1024)
        free_mb = shutil.disk_usage(cache_dir).free / (1024 * 1024)
        needed_mb = total_mb * 2
        if free_mb < needed_mb:
            msg = (
                f"Insufficient disk space. Need ~{needed_mb:.0f} MB but only {free_mb:.0f} MB free in {cache_dir}. "
                f"Use config latest/name_filter to process fewer archives."
            )
            raise RuntimeError(msg)

        tmp_dir = Path(tempfile.mkdtemp(prefix="takeout_", dir=str(cache_dir)))
        try:
            for archive_info in archives:
                archive_path = download_archive(service, archive_info["id"], tmp_dir)
                extract_dir = extract_archive(archive_path, tmp_dir)

                resources = [t.to_resource(extract_dir) for t in TABLES]

                run_sync("gtakeout", "gtakeout", resources, full_refresh, self._auto_transform)

                shutil.rmtree(extract_dir, ignore_errors=True)
                archive_path.unlink(missing_ok=True)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def resources(self, _client: Any) -> list[Any]:
        return []  # sync() is overridden
