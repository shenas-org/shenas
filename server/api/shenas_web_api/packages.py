"""PEP 503 Simple Repository backed by GCS.

Serves the package index and wheel downloads from a GCS bucket.
Falls back to a local packages/ directory when GCS is not configured
(local development).
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()

GCS_BUCKET = os.environ.get("GCS_PACKAGES_BUCKET", "")
LOCAL_PACKAGES_DIR = Path(os.environ.get("LOCAL_PACKAGES_DIR", "packages"))

DIST_EXTENSIONS = {".whl", ".tar.gz", ".zip"}


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _package_name_from_filename(filename: str) -> str | None:
    if filename.endswith(".whl"):
        return filename.split("-", maxsplit=1)[0]
    for ext in (".tar.gz", ".zip"):
        if filename.endswith(ext):
            stem = filename.removesuffix(ext)
            match = re.match(r"^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)-", stem)
            return match.group(1) if match else None
    return None


def _list_gcs() -> list[dict[str, str]]:
    """List packages from GCS bucket."""
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    result = []
    for blob in bucket.list_blobs():
        name = blob.name
        if any(name.endswith(ext) for ext in DIST_EXTENSIONS):
            result.append({"name": name, "sha256": blob.md5_hash or ""})
    return result


def _list_local() -> list[dict[str, str]]:
    """List packages from local directory."""
    if not LOCAL_PACKAGES_DIR.is_dir():
        return []
    result = []
    for path in sorted(LOCAL_PACKAGES_DIR.iterdir()):
        if path.is_file() and any(path.name.endswith(ext) for ext in DIST_EXTENSIONS):
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            result.append({"name": path.name, "sha256": sha})
    return result


def _list_files() -> list[dict[str, str]]:
    return _list_gcs() if GCS_BUCKET else _list_local()


def _gcs_signed_url(filename: str) -> str:
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(filename)
    return blob.generate_signed_url(expiration=timedelta(minutes=15), method="GET")


@router.get("/simple/", response_class=HTMLResponse)
def simple_index() -> HTMLResponse:
    files = _list_files()
    packages: dict[str, bool] = {}
    for f in files:
        raw = _package_name_from_filename(f["name"])
        if raw:
            packages[_normalize(raw)] = True
    links = "\n".join(f'    <a href="/simple/{name}/">{name}</a>' for name in sorted(packages))
    html = f"<!DOCTYPE html>\n<html>\n  <head><title>Simple Index</title></head>\n  <body>\n{links}\n  </body>\n</html>"
    return HTMLResponse(content=html)


@router.get("/simple/{name}/", response_class=HTMLResponse)
def simple_package(name: str) -> HTMLResponse:
    target = _normalize(name)
    files = _list_files()
    matches = []
    for f in files:
        raw = _package_name_from_filename(f["name"])
        if raw and _normalize(raw) == target:
            matches.append(f)
    if not matches:
        raise HTTPException(status_code=404, detail=f"No package {name!r} found")
    links = "\n".join(f'    <a href="/packages/{f["name"]}#sha256={f["sha256"]}">{f["name"]}</a>' for f in matches)
    html = (
        f"<!DOCTYPE html>\n<html>\n  <head><title>Links for {target}</title></head>\n"
        f"  <body>\n    <h1>Links for {target}</h1>\n{links}\n  </body>\n</html>"
    )
    return HTMLResponse(content=html)


@router.get("/packages/{filename}")
def download_package(filename: str) -> RedirectResponse:
    if GCS_BUCKET:
        try:
            url = _gcs_signed_url(filename)
            return RedirectResponse(url=url, status_code=302)
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc))
    # Local fallback
    path = LOCAL_PACKAGES_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    from fastapi.responses import FileResponse

    return FileResponse(path=path, filename=filename)
