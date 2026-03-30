"""OS-level autostart service management for the shenas server."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import typer
from rich.console import Console

console = Console()
app = typer.Typer(help="Manage OS autostart for the shenas server.")

SERVICE_NAME = "shenas"


def _find_shenas_binary() -> str:
    """Locate the shenas binary."""
    path = shutil.which("shenas")
    if path:
        return path
    bin_dir = Path(sys.executable).parent
    candidate = bin_dir / "shenas"
    if candidate.exists():
        return str(candidate)
    return "shenas"


def _find_scheduler_binary() -> str:
    """Locate the shenas-scheduler binary."""
    path = shutil.which("shenas-scheduler")
    if path:
        return path
    bin_dir = Path(sys.executable).parent
    candidate = bin_dir / "shenas-scheduler"
    if candidate.exists():
        return str(candidate)
    return "shenas-scheduler"


def _platform() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


# --- Windows ---


def _windows_startup_dir() -> Path:
    import os

    appdata = os.environ.get("APPDATA", "")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _windows_vbs_path() -> Path:
    return _windows_startup_dir() / "shenas-server.vbs"


def _windows_install(binary: str) -> None:
    scheduler = _find_scheduler_binary()
    vbs = _windows_vbs_path()
    # VBScript wrapper to launch both server and sync daemon without a visible console window
    script = (
        f'Set WshShell = CreateObject("WScript.Shell")\n'
        f'WshShell.Run """{binary}"" --no-tls", 0, False\n'
        f'WshShell.Run """{scheduler}""", 0, False\n'
    )
    vbs.parent.mkdir(parents=True, exist_ok=True)
    vbs.write_text(script)
    console.print(f"[green]Created startup script: {vbs}[/green]")


def _windows_uninstall() -> None:
    vbs = _windows_vbs_path()
    if vbs.exists():
        vbs.unlink()
        console.print(f"[green]Removed startup script: {vbs}[/green]")
    else:
        console.print("[dim]No startup script found[/dim]")


def _windows_status() -> bool:
    return _windows_vbs_path().exists()


# --- macOS ---


def _macos_plist_path(label: str = "com.shenas.server") -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"


def _macos_write_plist(binary: str, label: str, args: list[str], log_name: str) -> Path:
    plist = _macos_plist_path(label)
    log_dir = Path.home() / ".shenas"
    args_xml = "\n        ".join(f"<string>{a}</string>" for a in [binary, *args])
    content = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        {args_xml}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_dir / log_name}</string>
    <key>StandardErrorPath</key>
    <string>{log_dir / log_name}</string>
</dict>
</plist>
"""
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_text(content)
    return plist


def _macos_install(binary: str) -> None:
    scheduler = _find_scheduler_binary()
    p1 = _macos_write_plist(binary, "com.shenas.server", ["--no-tls"], "server.log")
    console.print(f"[green]Created LaunchAgent: {p1}[/green]")
    p2 = _macos_write_plist(scheduler, "com.shenas.sync-daemon", [], "sync-daemon.log")
    console.print(f"[green]Created LaunchAgent: {p2}[/green]")
    console.print("Load them with:")
    console.print(f"  launchctl load {p1}")
    console.print(f"  launchctl load {p2}")


def _macos_uninstall() -> None:
    for label in ("com.shenas.server", "com.shenas.sync-daemon"):
        plist = _macos_plist_path(label)
        if plist.exists():
            plist.unlink()
            console.print(f"[green]Removed LaunchAgent: {plist}[/green]")
        else:
            console.print(f"[dim]No LaunchAgent found: {plist}[/dim]")


def _macos_status() -> bool:
    return _macos_plist_path("com.shenas.server").exists()


# --- Linux ---


def _linux_service_dir() -> Path:
    return Path.home() / ".config" / "systemd" / "user"


def _linux_write_service(exec_start: str, name: str, description: str) -> Path:
    service = _linux_service_dir() / f"{name}.service"
    content = f"""\
[Unit]
Description={description}
After=network.target

[Service]
Type=simple
ExecStart={exec_start}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""
    service.parent.mkdir(parents=True, exist_ok=True)
    service.write_text(content)
    return service


def _linux_install(binary: str) -> None:
    scheduler = _find_scheduler_binary()
    s1 = _linux_write_service(f"{binary} --no-tls", "shenas", "Shenas Server")
    console.print(f"[green]Created systemd user service: {s1}[/green]")
    s2 = _linux_write_service(scheduler, "shenas-scheduler", "Shenas Sync Scheduler")
    console.print(f"[green]Created systemd user service: {s2}[/green]")
    console.print("Enable them with:")
    console.print("  systemctl --user enable --now shenas shenas-scheduler")


def _linux_uninstall() -> None:
    for name in ("shenas", "shenas-scheduler"):
        service = _linux_service_dir() / f"{name}.service"
        if service.exists():
            service.unlink()
            console.print(f"[green]Removed systemd user service: {service}[/green]")
        else:
            console.print(f"[dim]No systemd user service found: {service}[/dim]")
    console.print("Disable them first with: systemctl --user disable shenas shenas-scheduler")


def _linux_status() -> bool:
    return (_linux_service_dir() / "shenas.service").exists()


# --- Commands ---


@app.command("install")
def install_cmd() -> None:
    """Register shenas server to start on login."""
    binary = _find_shenas_binary()
    platform = _platform()
    if platform == "windows":
        _windows_install(binary)
    elif platform == "macos":
        _macos_install(binary)
    else:
        _linux_install(binary)


@app.command("uninstall")
def uninstall_cmd() -> None:
    """Remove shenas server from login startup."""
    platform = _platform()
    if platform == "windows":
        _windows_uninstall()
    elif platform == "macos":
        _macos_uninstall()
    else:
        _linux_uninstall()


@app.command("status")
def status_cmd() -> None:
    """Check if shenas server is registered for login startup."""
    platform = _platform()
    if platform == "windows":
        installed = _windows_status()
    elif platform == "macos":
        installed = _macos_status()
    else:
        installed = _linux_status()

    if installed:
        console.print("[green]Autostart is enabled[/green]")
    else:
        console.print("[dim]Autostart is not configured[/dim]")
