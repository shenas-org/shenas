"""Tests for app.server_cli typer entrypoint."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from typer.testing import CliRunner

from app.server_cli import app as cli_app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


class TestGenerateCert:
    def test_generates_cert_and_key(self, tmp_path: Path) -> None:
        result = runner.invoke(
            cli_app,
            ["generate-cert", "--cert-dir", str(tmp_path), "--hostname", "example.test"],
        )
        assert result.exit_code == 0, result.output
        assert (tmp_path / "cert.pem").exists()
        assert (tmp_path / "key.pem").exists()
        assert "Certificate" in result.output
        assert "Private key" in result.output


class TestServerCli:
    def test_no_tls_runs_uvicorn(self, tmp_path: Path) -> None:
        with patch("app.server_cli.uvicorn.run") as run:
            result = runner.invoke(
                cli_app,
                ["--no-tls", "--host", "127.0.0.1", "--port", "9999", "--ui", "default"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0, result.output
        run.assert_called_once()
        kwargs = run.call_args.kwargs
        assert kwargs["host"] == "127.0.0.1"
        assert kwargs["port"] == 9999
        assert "Starting HTTP server" in result.output

    def test_with_tls(self, tmp_path: Path) -> None:
        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        cert.write_text("c")
        key.write_text("k")
        with patch("app.server_cli.uvicorn.run") as run:
            result = runner.invoke(
                cli_app,
                ["--cert", str(cert), "--key", str(key), "--port", "8443"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0, result.output
        run.assert_called_once()
        kwargs = run.call_args.kwargs
        assert kwargs["ssl_certfile"] == str(cert)
        assert kwargs["ssl_keyfile"] == str(key)
        assert "HTTPS server" in result.output

    def test_reload_no_tls(self, tmp_path: Path) -> None:
        with patch("app.server_cli.uvicorn.run") as run:
            result = runner.invoke(
                cli_app,
                ["--reload", "--no-tls", "--port", "1234"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0, result.output
        args, kwargs = run.call_args
        assert args[0] == "app.server:app"
        assert kwargs["reload"] is True

    def test_reload_with_tls(self, tmp_path: Path) -> None:
        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        cert.write_text("c")
        key.write_text("k")
        with patch("app.server_cli.uvicorn.run") as run:
            result = runner.invoke(
                cli_app,
                ["--reload", "--cert", str(cert), "--key", str(key)],
                catch_exceptions=False,
            )
        assert result.exit_code == 0, result.output
        args, kwargs = run.call_args
        assert args[0] == "app.server:app"
        assert kwargs["reload"] is True
        assert kwargs["ssl_certfile"] == str(cert)

    def test_reload_no_cert_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(
            cli_app,
            [
                "--reload",
                "--cert",
                str(tmp_path / "missing.pem"),
                "--key",
                str(tmp_path / "missing.key"),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 1
        assert "TLS certificate not found" in result.output
