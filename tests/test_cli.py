from pathlib import Path
from unittest.mock import patch

import duckdb
import pytest
from typer.testing import CliRunner

from cli.commands.db_cmd import _discover_schemas, app as db_app
from cli.commands.pkg import check_signature
from cli.main import app as main_app

runner = CliRunner()


class TestMainCLI:
    def test_help(self) -> None:
        result = runner.invoke(main_app, ["--help"])
        assert result.exit_code == 0
        assert "pipe" in result.output
        assert "component" in result.output
        assert "schema" in result.output
        assert "ui" in result.output
        assert "registry" in result.output
        assert "db" in result.output

    def test_no_args_shows_help(self) -> None:
        result = runner.invoke(main_app, [])
        assert result.exit_code == 0
        assert "Usage" in result.output

    def test_ui_no_cert(self, tmp_path: Path) -> None:
        """shenas ui should exit with error when no TLS cert exists."""
        result = runner.invoke(
            main_app,
            ["ui", "serve", "--cert", str(tmp_path / "nonexistent.pem"), "--key", str(tmp_path / "nonexistent.key")],
            catch_exceptions=False,
        )
        assert result.exit_code == 1
        assert "TLS certificate not found" in result.output


class TestDbStatus:
    def test_discover_schemas(self) -> None:
        con = duckdb.connect(":memory:")
        con.execute("CREATE SCHEMA myschema")
        con.execute("CREATE TABLE myschema.mytable (id INTEGER)")
        schemas = _discover_schemas(con)
        assert "myschema" in schemas
        assert "mytable" in schemas["myschema"]
        con.close()

    def test_discover_schemas_excludes_system(self) -> None:
        con = duckdb.connect(":memory:")
        schemas = _discover_schemas(con)
        assert "information_schema" not in schemas
        assert "main" not in schemas
        con.close()

    def test_discover_schemas_empty(self) -> None:
        con = duckdb.connect(":memory:")
        schemas = _discover_schemas(con)
        assert schemas == {}
        con.close()

    def test_status_no_db(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("cli.commands.db_cmd.DB_PATH", Path("/nonexistent/path/db.duckdb"))
        result = runner.invoke(db_app, ["status"])
        assert result.exit_code == 0

    def test_status_with_data(self, monkeypatch: pytest.MonkeyPatch) -> None:
        con = duckdb.connect(":memory:")
        con.execute("CREATE SCHEMA test_schema")
        con.execute("CREATE TABLE test_schema.items (date DATE, val INTEGER)")
        con.execute("INSERT INTO test_schema.items VALUES ('2026-03-15', 42)")

        monkeypatch.setattr("cli.commands.db_cmd.DB_PATH", Path("fake_exists.duckdb"))
        with patch("cli.commands.db_cmd.connect", return_value=con):
            with patch("cli.commands.db_cmd.DB_PATH", Path("fake_exists.duckdb")):
                with patch.object(Path, "exists", return_value=True):
                    with patch.object(Path, "stat") as mock_stat:
                        mock_stat.return_value.st_size = 1024 * 1024
                        result = runner.invoke(db_app, ["status"])
        assert result.exit_code == 0
        assert "items" in result.output


class TestCheckSignature:
    def test_no_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("cli.commands.pkg.PUBLIC_KEY_PATH", tmp_path / "nonexistent.pub")
        assert check_signature("shenas-pipe-test", "1.0.0") == "no key"

    def test_no_wheel(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        pub = tmp_path / "shenas.pub"
        pub.write_text("fake")
        monkeypatch.setattr("cli.commands.pkg.PUBLIC_KEY_PATH", pub)
        monkeypatch.setattr("cli.commands.pkg.PACKAGES_DIR", tmp_path / "empty")
        assert check_signature("shenas-pipe-test", "1.0.0") == "unsigned"

    def test_no_sig_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        pub = tmp_path / "shenas.pub"
        pub.write_text("fake")
        pkg_dir = tmp_path / "packages"
        pkg_dir.mkdir()
        (pkg_dir / "shenas_pipe_test-1.0.0-py3-none-any.whl").write_bytes(b"whl")
        monkeypatch.setattr("cli.commands.pkg.PUBLIC_KEY_PATH", pub)
        monkeypatch.setattr("cli.commands.pkg.PACKAGES_DIR", pkg_dir)
        assert check_signature("shenas-pipe-test", "1.0.0") == "unsigned"

    def test_valid_signature(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from repository.signing import generate_keypair, load_private_key, write_signature

        priv, pub = generate_keypair(tmp_path / "keys")
        pkg_dir = tmp_path / "packages"
        pkg_dir.mkdir()
        whl = pkg_dir / "shenas_pipe_test-1.0.0-py3-none-any.whl"
        whl.write_bytes(b"real wheel")
        write_signature(load_private_key(priv), whl)

        monkeypatch.setattr("cli.commands.pkg.PUBLIC_KEY_PATH", pub)
        monkeypatch.setattr("cli.commands.pkg.PACKAGES_DIR", pkg_dir)
        assert check_signature("shenas-pipe-test", "1.0.0") == "valid"

    def test_invalid_signature(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from repository.signing import generate_keypair

        _, pub = generate_keypair(tmp_path / "keys")
        pkg_dir = tmp_path / "packages"
        pkg_dir.mkdir()
        whl = pkg_dir / "shenas_pipe_test-1.0.0-py3-none-any.whl"
        whl.write_bytes(b"real wheel")
        (pkg_dir / "shenas_pipe_test-1.0.0-py3-none-any.whl.sig").write_text("badsig==")

        monkeypatch.setattr("cli.commands.pkg.PUBLIC_KEY_PATH", pub)
        monkeypatch.setattr("cli.commands.pkg.PACKAGES_DIR", pkg_dir)
        assert check_signature("shenas-pipe-test", "1.0.0") == "invalid"
