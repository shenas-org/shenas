"""Tests for OS autostart service management."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


class TestLinux:
    def test_install_creates_services(self, tmp_path: Path) -> None:
        from app.cli.commands.service import _linux_install

        with patch("app.cli.commands.service._linux_service_dir", return_value=tmp_path):
            _linux_install("/usr/bin/shenas")

        server_svc = tmp_path / "shenas.service"
        scheduler_svc = tmp_path / "shenas-scheduler.service"
        assert server_svc.exists()
        assert scheduler_svc.exists()

        server_content = server_svc.read_text()
        assert "ExecStart=/usr/bin/shenas --no-tls" in server_content
        assert "Restart=on-failure" in server_content

        scheduler_content = scheduler_svc.read_text()
        assert "ExecStart=" in scheduler_content

    def test_uninstall_removes_services(self, tmp_path: Path) -> None:
        from app.cli.commands.service import _linux_uninstall

        (tmp_path / "shenas.service").write_text("[Unit]\n")
        (tmp_path / "shenas-scheduler.service").write_text("[Unit]\n")

        with patch("app.cli.commands.service._linux_service_dir", return_value=tmp_path):
            _linux_uninstall()

        assert not (tmp_path / "shenas.service").exists()
        assert not (tmp_path / "shenas-scheduler.service").exists()

    def test_uninstall_no_files(self, tmp_path: Path) -> None:
        from app.cli.commands.service import _linux_uninstall

        with patch("app.cli.commands.service._linux_service_dir", return_value=tmp_path):
            _linux_uninstall()  # should not raise

    def test_status(self, tmp_path: Path) -> None:
        from app.cli.commands.service import _linux_status

        with patch("app.cli.commands.service._linux_service_dir", return_value=tmp_path):
            assert _linux_status() is False

            (tmp_path / "shenas.service").write_text("[Unit]\n")
            assert _linux_status() is True


class TestMacOS:
    def test_install_creates_plists(self, tmp_path: Path) -> None:
        from app.cli.commands.service import _macos_install

        with (
            patch("app.cli.commands.service._macos_plist_path", side_effect=lambda label: tmp_path / f"{label}.plist"),
            patch("app.cli.commands.service._find_scheduler_binary", return_value="/usr/bin/shenas-scheduler"),
        ):
            _macos_install("/usr/bin/shenas")

        server_plist = tmp_path / "com.shenas.server.plist"
        daemon_plist = tmp_path / "com.shenas.sync-daemon.plist"
        assert server_plist.exists()
        assert daemon_plist.exists()

        server_content = server_plist.read_text()
        assert "/usr/bin/shenas" in server_content
        assert "--no-tls" in server_content
        assert "RunAtLoad" in server_content

        daemon_content = daemon_plist.read_text()
        assert "/usr/bin/shenas-scheduler" in daemon_content

    def test_uninstall_removes_plists(self, tmp_path: Path) -> None:
        from app.cli.commands.service import _macos_uninstall

        (tmp_path / "com.shenas.server.plist").write_text("<plist/>")
        (tmp_path / "com.shenas.sync-daemon.plist").write_text("<plist/>")

        with patch("app.cli.commands.service._macos_plist_path", side_effect=lambda label: tmp_path / f"{label}.plist"):
            _macos_uninstall()

        assert not (tmp_path / "com.shenas.server.plist").exists()
        assert not (tmp_path / "com.shenas.sync-daemon.plist").exists()

    def test_status(self, tmp_path: Path) -> None:
        from app.cli.commands.service import _macos_status

        with patch("app.cli.commands.service._macos_plist_path", return_value=tmp_path / "com.shenas.server.plist"):
            assert _macos_status() is False

            (tmp_path / "com.shenas.server.plist").write_text("<plist/>")
            assert _macos_status() is True


class TestWindows:
    def test_install_creates_vbs(self, tmp_path: Path) -> None:
        from app.cli.commands.service import _windows_install

        with (
            patch("app.cli.commands.service._windows_vbs_path", return_value=tmp_path / "shenas-server.vbs"),
            patch("app.cli.commands.service._find_scheduler_binary", return_value="C:\\shenas\\shenas-scheduler.exe"),
        ):
            _windows_install("C:\\shenas\\shenas.exe")

        vbs = tmp_path / "shenas-server.vbs"
        assert vbs.exists()
        content = vbs.read_text()
        assert "shenas.exe" in content
        assert "--no-tls" in content
        assert "shenas-scheduler.exe" in content

    def test_uninstall_removes_vbs(self, tmp_path: Path) -> None:
        from app.cli.commands.service import _windows_uninstall

        vbs = tmp_path / "shenas-server.vbs"
        vbs.write_text("Set WshShell = ...\n")

        with patch("app.cli.commands.service._windows_vbs_path", return_value=vbs):
            _windows_uninstall()

        assert not vbs.exists()

    def test_uninstall_no_file(self, tmp_path: Path) -> None:
        from app.cli.commands.service import _windows_uninstall

        with patch("app.cli.commands.service._windows_vbs_path", return_value=tmp_path / "missing.vbs"):
            _windows_uninstall()  # should not raise

    def test_status(self, tmp_path: Path) -> None:
        from app.cli.commands.service import _windows_status

        vbs = tmp_path / "shenas-server.vbs"
        with patch("app.cli.commands.service._windows_vbs_path", return_value=vbs):
            assert _windows_status() is False

            vbs.write_text("Set WshShell = ...\n")
            assert _windows_status() is True
