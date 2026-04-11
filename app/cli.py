from __future__ import annotations

from pathlib import Path

import typer
import uvicorn

app = typer.Typer(name="shenas", help="Start the shenas server.", invoke_without_command=True)

DEFAULT_CERT_DIR = Path(".shenas")


def _python_reload_dirs() -> list[str]:
    """Reload only Python source dirs; skip JS/Rust/build noise."""
    dirs: list[str] = ["app"]
    for sub in ("sources", "datasets", "core", "themes"):
        base = Path("plugins") / sub
        if base.exists():
            dirs.append(str(base))
    return dirs


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    host: str = typer.Option("127.0.0.1", help="Bind host"),
    port: int = typer.Option(7280, help="Bind port"),
    cert_file: Path = typer.Option(DEFAULT_CERT_DIR / "cert.pem", "--cert", help="TLS certificate file"),
    key_file: Path = typer.Option(DEFAULT_CERT_DIR / "key.pem", "--key", help="TLS private key file"),
    no_tls: bool = typer.Option(False, "--no-tls", help="Run plain HTTP (for desktop app sidecar)"),
    frontend: str = typer.Option("default", "--frontend", help="Frontend plugin to render as the app shell"),
    default_theme: str = typer.Option("default", "--default-theme", help="Theme to enable if none is set"),
    api_url: str = typer.Option("https://shenas.net", "--api-url", help="shenas.net API server URL"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on file changes (development)"),
) -> None:
    """Start the shenas server."""
    if ctx.invoked_subcommand is not None:
        return

    import os

    os.environ["SHENAS_FRONTEND"] = frontend
    os.environ["SHENAS_DEFAULT_THEME"] = default_theme
    os.environ["SHENAS_NET_URL"] = api_url
    os.environ.setdefault("SHENAS_PACKAGE_INDEX", api_url.rstrip("/"))

    if reload:
        app_target = "app.main:app"
        if no_tls:
            typer.echo(f"Starting HTTP server on http://{host}:{port} (reload)")
            uvicorn.run(
                app_target,
                host=host,
                port=port,
                reload=True,
                reload_dirs=_python_reload_dirs(),
                reload_includes=["*.py"],
            )
            return

        if not cert_file.exists() or not key_file.exists():
            typer.echo("TLS certificate not found. Generate one with:\n\n  shenas generate-cert\n")
            raise typer.Exit(code=1)

        typer.echo(f"Starting HTTPS server on https://{host}:{port} (reload)")
        uvicorn.run(
            app_target,
            host=host,
            port=port,
            reload=True,
            reload_dirs=["app", "plugins"],
            ssl_certfile=str(cert_file),
            ssl_keyfile=str(key_file),
        )
        return

    from app.main import app as fastapi_app

    fastapi_app.state.frontend_name = frontend
    fastapi_app.state.default_theme = default_theme

    if no_tls:
        typer.echo(f"Starting HTTP server on http://{host}:{port}")
        uvicorn.run(fastapi_app, host=host, port=port)
        return

    if not cert_file.exists() or not key_file.exists():
        typer.echo("TLS certificate not found. Generate one with:\n\n  shenas generate-cert\n")
        raise typer.Exit(code=1)

    typer.echo(f"Starting HTTPS server on https://{host}:{port}")
    uvicorn.run(
        fastapi_app,
        host=host,
        port=port,
        ssl_certfile=str(cert_file),
        ssl_keyfile=str(key_file),
    )


@app.command("generate-cert")
def generate_cert(
    cert_dir: Path = typer.Option(DEFAULT_CERT_DIR, help="Directory to write cert and key"),
    hostname: str = typer.Option("localhost", help="Hostname for the certificate"),
) -> None:
    """Generate a self-signed TLS certificate for HTTPS."""
    import datetime
    import ipaddress

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_path = cert_dir / "cert.pem"
    key_path = cert_dir / "key.pem"

    private_key = ec.generate_private_key(ec.SECP256R1())

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "shenas"),
        ]
    )

    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName(hostname),
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    typer.echo(f"Certificate: {cert_path}")
    typer.echo(f"Private key: {key_path}")
    typer.echo(f"Valid for: {hostname}, localhost, 127.0.0.1 (365 days)")
