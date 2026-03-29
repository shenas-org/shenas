from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

DIST_EXTENSIONS = {".whl", ".tar.gz", ".zip", ".egg", ".tar.bz2"}


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def package_name_from_filename(filename: str) -> str | None:
    if filename.endswith(".whl"):
        return filename.split("-")[0]
    if filename.endswith((".tar.gz", ".tar.bz2", ".zip", ".egg")):
        stem = re.sub(r"\.(tar\.gz|tar\.bz2|zip|egg)$", "", filename)
        match = re.match(r"^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)-", stem)
        if match:
            return match.group(1)
    return None


@dataclass
class DistFile:
    path: Path
    sha256: str = field(init=False)

    def __post_init__(self) -> None:
        self.sha256 = file_sha256(self.path)


@dataclass
class Package:
    name: str
    normalized: str
    files: list[DistFile]


class PackageRepository:
    def __init__(self, packages_dir: Path) -> None:
        self.packages_dir = packages_dir

    def all_packages(self) -> list[Package]:
        by_name: dict[str, list[DistFile]] = {}
        for path in sorted(self.packages_dir.iterdir()):
            if not path.is_file():
                continue
            if not any(path.name.endswith(ext) for ext in DIST_EXTENSIONS):
                continue
            raw_name = package_name_from_filename(path.name)
            if raw_name is None:
                continue
            key = normalize(raw_name)
            by_name.setdefault(key, []).append(DistFile(path=path))

        return [Package(name=normalized, normalized=normalized, files=files) for normalized, files in sorted(by_name.items())]

    def get_package(self, name: str) -> Package | None:
        target = normalize(name)
        for pkg in self.all_packages():
            if pkg.normalized == target:
                return pkg
        return None
