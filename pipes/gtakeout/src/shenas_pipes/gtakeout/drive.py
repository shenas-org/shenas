"""Find and download Google Takeout archives from Google Drive."""

import tarfile
import zipfile
from pathlib import Path
from typing import Any


def find_takeout_archives(service: Any) -> list[dict]:
    """Search Google Drive for Takeout archive files (zip/tgz)."""
    archive_mimes = (
        "mimeType='application/zip' or mimeType='application/x-zip' or "
        "mimeType='application/x-compressed-tar' or mimeType='application/gzip' or "
        "mimeType='application/x-gzip' or mimeType='application/x-gtar'"
    )
    queries = [
        f"name contains 'takeout-' and trashed=false and ({archive_mimes})",
        f"name contains 'Takeout' and trashed=false and ({archive_mimes})",
    ]

    takeout_folder_id = _find_folder(service, "Takeout")
    if takeout_folder_id:
        queries.append(f"'{takeout_folder_id}' in parents and trashed=false and ({archive_mimes})")

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

    archives.sort(key=lambda a: a["created_time"], reverse=True)
    return archives


def _find_folder(service: Any, name: str) -> str | None:
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
    """Download an archive from Drive to a local file."""
    meta = service.files().get(fileId=file_id, fields="name").execute()
    filename = meta["name"]
    dest = dest_dir / filename

    request = service.files().get_media(fileId=file_id)
    with open(dest, "wb") as f:
        from googleapiclient.http import MediaIoBaseDownload

        downloader = MediaIoBaseDownload(f, request, chunksize=10 * 1024 * 1024)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"  {filename}: {pct}%", end="\r")
        print(f"  {filename}: done      ")

    return dest


def extract_archive(archive_path: Path, dest_dir: Path) -> Path:
    """Safely extract a zip or tgz archive. Returns the extraction root."""
    extract_dir = dest_dir / f"extracted_{archive_path.stem}"
    extract_dir.mkdir(parents=True, exist_ok=True)
    name = archive_path.name.lower()

    if name.endswith(".zip"):
        with zipfile.ZipFile(archive_path) as zf:
            for member in zf.namelist():
                # Prevent path traversal
                resolved = (extract_dir / member).resolve()
                if not str(resolved).startswith(str(extract_dir.resolve())):
                    continue
                zf.extract(member, extract_dir)
    elif name.endswith(".tgz") or name.endswith(".tar.gz"):
        with tarfile.open(archive_path, "r:gz") as tf:
            for member in tf.getmembers():
                resolved = (extract_dir / member.name).resolve()
                if not str(resolved).startswith(str(extract_dir.resolve())):
                    continue
                tf.extract(member, extract_dir)
    else:
        raise ValueError(f"Unsupported archive format: {archive_path.name}")

    return extract_dir


def iter_files(extract_dir: Path, prefix: str, suffix: str = ".json") -> list[Path]:
    """Find all files under a Takeout service folder."""
    takeout_root = extract_dir / "Takeout"
    if not takeout_root.exists():
        takeout_root = extract_dir

    service_dir = takeout_root / prefix
    if not service_dir.exists():
        return []

    return sorted(service_dir.rglob(f"*{suffix}"))
