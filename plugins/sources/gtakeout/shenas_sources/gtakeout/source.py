"""Google Takeout source -- finds and parses Takeout archives from Google Drive."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class GTakeoutSource(Source):
    name = "gtakeout"
    display_name = "Google Takeout"
    primary_table = "photos_metadata"
    description = (
        "Finds and parses Google Takeout archives.\n\n"
        "By default, uses Google OAuth2 to search Drive for Takeout zip/tgz files. "
        "Alternatively, set local_folder in config to point at a directory containing "
        "Takeout archives or an already-extracted Takeout folder, skipping Drive entirely."
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
        local_folder: Annotated[
            str,
            Field(
                db_type="VARCHAR",
                description="Path to a local Takeout folder. If set, archives are read from here instead of Google Drive.",
                default="",
                ui_widget="text",
                example_value="/home/user/Downloads/Takeout",
            ),
        ] = ""
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

    auth_instructions = "Click Authenticate to sign in with your Google account. Not needed when using a local folder."

    @property
    def is_authenticated(self) -> bool | None:
        """Auth is not required when a local folder is configured."""
        if self._has_local_folder():
            return True
        return super().is_authenticated

    def _google_auth(self) -> Any:
        from shenas_sources.core.google_auth import GoogleAuth

        return GoogleAuth(
            "gtakeout",
            ["https://www.googleapis.com/auth/drive.readonly"],
            "drive",
            "v3",
            auth_cls=self.Auth,
        )

    def _has_local_folder(self) -> bool:
        """Check if a local folder is configured."""
        row = self.Config.read_row()
        return bool(row and row.get("local_folder"))

    def build_client(self) -> Any:
        if self._has_local_folder():
            return None
        return self._google_auth().build_client()

    @property
    def supports_oauth_redirect(self) -> bool:
        return True

    def start_oauth(self, redirect_uri: str, credentials: dict[str, str] | None = None) -> str:  # noqa: ARG002
        return self._google_auth().start_oauth(redirect_uri)

    def complete_oauth(self, *, code: str, state: str | None = None) -> None:
        self._google_auth().complete_oauth(code, state)

    def sync(self, *, full_refresh: bool = False, **_kwargs: Any) -> None:
        """Custom sync: downloads and processes archives one at a time."""
        from shenas_sources.gtakeout.tables import TABLES

        dataset = self.dataset_name

        # Read config
        row = self.Config.read_row()
        latest = (row.get("latest") if row else None) or 0
        name_filter = (row.get("name_filter") if row else None) or ""
        local_folder = (row.get("local_folder") if row else None) or ""

        # Build resource name -> display name map from table classes.
        rdn: dict[str, str] = {}
        for table in TABLES:
            rdn[table._Meta.name] = getattr(table._Meta, "display_name", table._Meta.name)

        if local_folder:
            self._sync_local(local_folder, dataset, full_refresh, latest, name_filter, rdn)
        else:
            self._sync_drive(dataset, full_refresh, latest, name_filter, rdn)

        self._post_sync(full_refresh)

    def _sync_local(
        self,
        local_folder: str,
        dataset: str,
        full_refresh: bool,
        latest: int,
        name_filter: str,
        resource_display_names: dict[str, str],
    ) -> None:
        """Sync from a local folder containing Takeout archives or extracted data."""
        from shenas_sources.core.cli import run_sync
        from shenas_sources.gtakeout.drive import extract_archive
        from shenas_sources.gtakeout.tables import TABLES

        folder = Path(local_folder)
        if not folder.exists():
            msg = f"Local folder does not exist: {local_folder}"
            raise RuntimeError(msg)

        # Check if this is an already-extracted Takeout folder (contains a "Takeout" subfolder)
        takeout_subdir = folder / "Takeout"
        if takeout_subdir.exists():
            # Directly use the folder as extraction root
            resources = [t.to_resource(folder) for t in TABLES]
            run_sync(
                self.name,
                dataset,
                resources,
                full_refresh,
                self._auto_transform,
                display_name=self.display_name,
                resource_display_names=resource_display_names,
            )
            return

        # Otherwise look for archive files in the folder
        archives = sorted(
            [p for p in folder.iterdir() if p.suffix in (".zip", ".tgz") or p.name.endswith(".tar.gz")],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not archives:
            msg = (
                f"No Takeout archives or 'Takeout' subfolder found in {local_folder}. "
                f"Place .zip or .tgz archives there, or point to an extracted Takeout directory."
            )
            raise RuntimeError(msg)

        if name_filter:
            archives = [a for a in archives if name_filter in a.name]
            if not archives:
                msg = f"No archives matching '{name_filter}' in {local_folder}."
                raise RuntimeError(msg)

        if latest > 0:
            archives = archives[:latest]

        tmp_dir = Path(tempfile.mkdtemp(prefix="takeout_local_"))
        try:
            for archive_path in archives:
                extract_dir = extract_archive(archive_path, tmp_dir)
                resources = [t.to_resource(extract_dir) for t in TABLES]

                run_sync(
                    self.name,
                    dataset,
                    resources,
                    full_refresh,
                    self._auto_transform,
                    display_name=self.display_name,
                    resource_display_names=resource_display_names,
                )

                shutil.rmtree(extract_dir, ignore_errors=True)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _sync_drive(
        self,
        dataset: str,
        full_refresh: bool,
        latest: int,
        name_filter: str,
        resource_display_names: dict[str, str],
    ) -> None:
        """Sync from Google Drive (original behavior)."""
        from shenas_sources.core.cli import run_sync
        from shenas_sources.core.db import DB_PATH
        from shenas_sources.gtakeout.drive import download_archive, extract_archive, find_takeout_archives
        from shenas_sources.gtakeout.tables import TABLES

        service = self.build_client()

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

                run_sync(
                    self.name,
                    dataset,
                    resources,
                    full_refresh,
                    self._auto_transform,
                    display_name=self.display_name,
                    resource_display_names=resource_display_names,
                )

                shutil.rmtree(extract_dir, ignore_errors=True)
                archive_path.unlink(missing_ok=True)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def resources(self, _client: Any) -> list[Any]:  # ty: ignore[invalid-method-override]
        return []  # sync() is overridden
