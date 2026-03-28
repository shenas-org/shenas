from pathlib import Path

import typer
import uvicorn

app = typer.Typer(name="shenas", help="Start the shenas server.", invoke_without_command=True)

DEFAULT_CERT_DIR = Path(".shenas")


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        serve(
            host="127.0.0.1",
            port=7280,
            cert_file=DEFAULT_CERT_DIR / "cert.pem",
            key_file=DEFAULT_CERT_DIR / "key.pem",
            no_tls=False,
        )


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host"),
    port: int = typer.Option(7280, help="Bind port"),
    cert_file: Path = typer.Option(DEFAULT_CERT_DIR / "cert.pem", "--cert", help="TLS certificate file"),
    key_file: Path = typer.Option(DEFAULT_CERT_DIR / "key.pem", "--key", help="TLS private key file"),
    no_tls: bool = typer.Option(False, "--no-tls", help="Run plain HTTP (for desktop app sidecar)"),
) -> None:
    """Start the UI web server."""
    from app.server import app as fastapi_app

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

    now = datetime.datetime.now(datetime.timezone.utc)
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
