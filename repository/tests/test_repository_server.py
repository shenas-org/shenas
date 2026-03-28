import hashlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from repository.main import app
from repository.repository import (
    PackageRepository,
    normalize,
    package_name_from_filename,
)
import repository.main as server_module


@pytest.fixture()
def packages_dir(tmp_path: Path) -> Path:
    """Create a temp packages dir with fake wheel and tarball."""
    whl = tmp_path / "my_package-1.0.0-py3-none-any.whl"
    whl.write_bytes(b"fake wheel content")
    tarball = tmp_path / "my_package-1.0.0.tar.gz"
    tarball.write_bytes(b"fake tarball content")
    sig = tmp_path / "my_package-1.0.0-py3-none-any.whl.sig"
    sig.write_text("fakesig")
    return tmp_path


@pytest.fixture()
def client(packages_dir: Path) -> Iterator[TestClient]:
    """TestClient with initialized repository."""
    server_module._repo = PackageRepository(packages_dir)
    yield TestClient(app)
    server_module._repo = None


# --- repository.py unit tests ---


class TestNormalize:
    def test_hyphens(self) -> None:
        assert normalize("My-Package") == "my-package"

    def test_underscores(self) -> None:
        assert normalize("my_package") == "my-package"

    def test_dots(self) -> None:
        assert normalize("my.package") == "my-package"

    def test_mixed(self) -> None:
        assert normalize("My_Cool.Package") == "my-cool-package"

    def test_consecutive(self) -> None:
        assert normalize("my__package") == "my-package"


class TestPackageNameFromFilename:
    def test_wheel(self) -> None:
        assert package_name_from_filename("shenas_pipe_garmin-0.1.0-py3-none-any.whl") == "shenas_pipe_garmin"

    def test_tarball(self) -> None:
        assert package_name_from_filename("my_package-1.0.0.tar.gz") == "my_package"

    def test_zip(self) -> None:
        assert package_name_from_filename("some_pkg-2.3.1.zip") == "some_pkg"

    def test_egg(self) -> None:
        assert package_name_from_filename("pkg-0.1.egg") == "pkg"

    def test_unknown_extension(self) -> None:
        assert package_name_from_filename("readme.txt") is None

    def test_no_version_separator(self) -> None:
        # wheel filenames split on '-'; no separator means the whole stem is the "name"
        assert package_name_from_filename("noversion.whl") == "noversion.whl"


class TestPackageRepository:
    def test_all_packages(self, packages_dir: Path) -> None:
        repo = PackageRepository(packages_dir)
        pkgs = repo.all_packages()
        assert len(pkgs) == 1
        assert pkgs[0].normalized == "my-package"
        assert len(pkgs[0].files) == 2

    def test_get_package_found(self, packages_dir: Path) -> None:
        repo = PackageRepository(packages_dir)
        pkg = repo.get_package("my-package")
        assert pkg is not None
        assert pkg.normalized == "my-package"

    def test_get_package_not_found(self, packages_dir: Path) -> None:
        repo = PackageRepository(packages_dir)
        assert repo.get_package("nonexistent") is None

    def test_get_package_normalizes(self, packages_dir: Path) -> None:
        repo = PackageRepository(packages_dir)
        assert repo.get_package("My_Package") is not None

    def test_empty_dir(self, tmp_path: Path) -> None:
        repo = PackageRepository(tmp_path)
        assert repo.all_packages() == []

    def test_ignores_non_dist_files(self, tmp_path: Path) -> None:
        (tmp_path / "readme.txt").write_text("hello")
        (tmp_path / ".gitkeep").write_text("")
        repo = PackageRepository(tmp_path)
        assert repo.all_packages() == []

    def test_ignores_sig_files(self, tmp_path: Path) -> None:
        (tmp_path / "pkg-1.0.0-py3-none-any.whl").write_bytes(b"whl")
        (tmp_path / "pkg-1.0.0-py3-none-any.whl.sig").write_text("sig")
        repo = PackageRepository(tmp_path)
        pkgs = repo.all_packages()
        assert len(pkgs) == 1
        assert len(pkgs[0].files) == 1

    def test_sha256_computed(self, packages_dir: Path) -> None:
        repo = PackageRepository(packages_dir)
        pkg = repo.get_package("my-package")
        assert pkg is not None
        whl_file = [f for f in pkg.files if f.path.name.endswith(".whl")][0]
        expected = hashlib.sha256(b"fake wheel content").hexdigest()
        assert whl_file.sha256 == expected

    def test_multiple_packages(self, tmp_path: Path) -> None:
        (tmp_path / "alpha-1.0.0-py3-none-any.whl").write_bytes(b"a")
        (tmp_path / "beta-2.0.0-py3-none-any.whl").write_bytes(b"b")
        repo = PackageRepository(tmp_path)
        pkgs = repo.all_packages()
        assert len(pkgs) == 2
        names = [p.normalized for p in pkgs]
        assert names == ["alpha", "beta"]


# --- main.py API tests ---


class TestSimpleIndex:
    def test_index_lists_packages(self, client: TestClient) -> None:
        resp = client.get("/simple/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "my-package" in resp.text
        assert '<a href="/simple/my-package/">' in resp.text

    def test_index_empty(self, tmp_path: Path) -> None:
        server_module._repo = PackageRepository(tmp_path)
        c = TestClient(app)
        resp = c.get("/simple/")
        assert resp.status_code == 200
        assert "<a" not in resp.text
        server_module._repo = None


class TestSimplePackage:
    def test_package_detail(self, client: TestClient) -> None:
        resp = client.get("/simple/my-package/")
        assert resp.status_code == 200
        assert "my_package-1.0.0-py3-none-any.whl" in resp.text
        assert "my_package-1.0.0.tar.gz" in resp.text
        assert "sha256=" in resp.text

    def test_package_normalizes_name(self, client: TestClient) -> None:
        resp = client.get("/simple/My_Package/")
        assert resp.status_code == 200
        assert "my_package-1.0.0" in resp.text

    def test_package_not_found(self, client: TestClient) -> None:
        resp = client.get("/simple/nonexistent/")
        assert resp.status_code == 404


class TestDownloadFile:
    def test_download_wheel(self, client: TestClient) -> None:
        resp = client.get("/packages/my_package-1.0.0-py3-none-any.whl")
        assert resp.status_code == 200
        assert resp.content == b"fake wheel content"

    def test_download_tarball(self, client: TestClient) -> None:
        resp = client.get("/packages/my_package-1.0.0.tar.gz")
        assert resp.status_code == 200
        assert resp.content == b"fake tarball content"

    def test_download_sig(self, client: TestClient) -> None:
        resp = client.get("/packages/my_package-1.0.0-py3-none-any.whl.sig")
        assert resp.status_code == 200
        assert resp.text == "fakesig"

    def test_download_not_found(self, client: TestClient) -> None:
        resp = client.get("/packages/nonexistent.whl")
        assert resp.status_code == 404
