"""Find and download Google Takeout archives from Google Drive."""

import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any


def find_takeout_archives(service: Any) -> list[dict]:
    """Search Google Drive for Takeout archive files (zip/tgz).

    Searches for:
    1. Files named takeout-* (standard naming)
    2. Files inside a folder named "Takeout"
    3. Any zip/tgz file with "takeout" in the name (case-insensitive)
    """
    # Search by multiple strategies and deduplicate by file ID
    archive_mimes = (
        "mimeType='application/zip' or mimeType='application/x-zip' or "
        "mimeType='application/x-compressed-tar' or mimeType='application/gzip' or "
        "mimeType='application/x-gzip' or mimeType='application/x-gtar'"
    )
    queries = [
        f"name contains 'takeout-' and ({archive_mimes})",
        f"name contains 'Takeout' and ({archive_mimes})",
    ]

    # Also search for archives inside a "Takeout" folder
    takeout_folder_id = _find_folder(service, "Takeout")
    if takeout_folder_id:
        queries.append(f"'{takeout_folder_id}' in parents and ({archive_mimes})")

    seen_ids: set[str] = set()
    archives = []

    for query in queries:
        page_token = None
        while True:
            result = (
                service.files()
                .list(
                    q=query,
                    fields="nextPageToken, files(id, name, size, createdTime, mimeType)",
                    pageSize=100,
                    orderBy="createdTime desc",
                    pageToken=page_token,
                )
                .execute()
            )

            for f in result.get("files", []):
                if f["id"] not in seen_ids:
                    seen_ids.add(f["id"])
                    archives.append(
                        {
                            "id": f["id"],
                            "name": f["name"],
                            "size": int(f.get("size", 0)),
                            "created_time": f.get("createdTime", ""),
                            "mime_type": f.get("mimeType", ""),
                        }
                    )

            page_token = result.get("nextPageToken")
            if not page_token:
                break

    # Sort newest first
    archives.sort(key=lambda a: a["created_time"], reverse=True)
    return archives


def _find_folder(service: Any, name: str) -> str | None:
    """Find a folder by name on Google Drive. Returns folder ID or None."""
    result = (
        service.files()
        .list(
            q=f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id)",
            pageSize=1,
        )
        .execute()
    )
    files = result.get("files", [])
    return files[0]["id"] if files else None


def download_archive(service: Any, file_id: str, dest_dir: Path) -> Path:
    """Download an archive from Drive to a local temp file."""
    meta = service.files().get(fileId=file_id, fields="name").execute()
    filename = meta["name"]
    dest = dest_dir / filename

    request = service.files().get_media(fileId=file_id)
    with open(dest, "wb") as f:
        # Download in chunks
        from googleapiclient.http import MediaIoBaseDownload

        downloader = MediaIoBaseDownload(f, request, chunksize=10 * 1024 * 1024)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    return dest


def extract_archive(archive_path: Path) -> Path:
    """Extract a zip or tgz archive to a temp directory. Returns the extraction root."""
    extract_dir = Path(tempfile.mkdtemp(prefix="takeout_"))
    name = archive_path.name.lower()

    if name.endswith(".zip"):
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(extract_dir)
    elif name.endswith(".tgz") or name.endswith(".tar.gz"):
        with tarfile.open(archive_path, "r:gz") as tf:
            tf.extractall(extract_dir)
    else:
        raise ValueError(f"Unsupported archive format: {archive_path.name}")

    return extract_dir


def iter_files(extract_dir: Path, prefix: str, suffix: str = ".json") -> list[Path]:
    """Find all files under a Takeout service folder."""
    # Takeout structure: extract_dir/Takeout/<service>/...
    takeout_root = extract_dir / "Takeout"
    if not takeout_root.exists():
        # Sometimes there's no Takeout wrapper
        takeout_root = extract_dir

    service_dir = takeout_root / prefix
    if not service_dir.exists():
        return []

    return sorted(service_dir.rglob(f"*{suffix}"))
