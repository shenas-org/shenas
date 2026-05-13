"""Generic IMAP source -- syncs message envelope metadata from any IMAP server.

Subclass this to ship presets for a specific provider (e.g.
``ProtonMailBridgeSource`` overrides ``Config`` defaults so they point at
the local Bridge process).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.access_type import OFFICIAL_API
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source

if TYPE_CHECKING:
    from shenas_sources.core.table import SourceTable


@dataclass
class ImapAuth(SourceAuth):
    username: (
        Annotated[
            str | None,
            Field(db_type="VARCHAR", description="IMAP username (often the full email address)"),
        ]
        | None
    ) = None
    password: (
        Annotated[
            str | None,
            Field(db_type="VARCHAR", description="IMAP password or app-specific token", category="secret"),
        ]
        | None
    ) = None


@dataclass
class ImapConfig(SourceConfig):
    imap_host: Annotated[
        str | None,
        Field(
            db_type="VARCHAR",
            description="IMAP server hostname",
            ui_widget="text",
            example_value="imap.example.com",
        ),
    ] = None
    imap_port: Annotated[
        int | None,
        Field(
            db_type="INTEGER",
            description="IMAP server port (993 for IMAPS, 143 for STARTTLS)",
            ui_widget="text",
            example_value="993",
        ),
    ] = 993
    use_starttls: Annotated[
        bool,
        Field(db_type="BOOLEAN", description="Use STARTTLS instead of implicit TLS"),
    ] = False
    verify_tls: Annotated[
        bool,
        Field(db_type="BOOLEAN", description="Verify the server TLS certificate"),
    ] = True
    mailboxes: Annotated[
        str | None,
        Field(
            db_type="VARCHAR",
            description="Comma-separated mailboxes to sync (empty = all discovered folders)",
            ui_widget="text",
            example_value="INBOX,Sent",
        ),
    ] = "INBOX"
    lookback_period: Annotated[
        int | None,
        Field(
            db_type="INTEGER",
            description="How many days back to fetch on each sync (0 = all)",
            ui_widget="text",
            example_value="90",
        ),
    ] = 90


class ImapSource(Source):
    name = "imap"
    display_name = "IMAP"
    primary_table = "messages"
    entity_types: ClassVar[list[str]] = ["human"]
    default_update_frequency = "R/PT1H"
    description = (
        "Syncs message envelope metadata (headers, flags, size, INTERNALDATE) "
        "from any IMAP server. Subject and addresses are decoded from RFC 2047 "
        "MIME-encoded headers; body content is never fetched.\n\n"
        "Configure host/port/TLS for your provider and supply IMAP credentials "
        "(or an app-specific password)."
    )
    access_types = (OFFICIAL_API,)

    Auth: ClassVar[type] = ImapAuth
    Config: ClassVar[type] = ImapConfig

    auth_instructions = (
        "Enter your IMAP username (usually your full email address) and "
        "password. Many providers require an app-specific password or "
        "OAuth-issued token rather than your account password."
    )

    @property
    def auth_fields(self) -> list[dict[str, str | bool]]:
        return [
            {"name": "username", "prompt": "IMAP username", "hide": False},
            {"name": "password", "prompt": "IMAP password", "hide": True},
        ]

    # -- subclass hooks -------------------------------------------------------

    def connection_params(self) -> dict[str, Any]:
        """Return host/port/TLS settings, merging Config row over class defaults.

        Subclasses (e.g. Proton Mail Bridge) can override this to hardcode
        provider-specific defaults that the user shouldn't need to set.
        """
        config_row = self.Config.read_row() or {}  # ty: ignore[unresolved-attribute]
        host = config_row.get("imap_host") or ""
        if not host:
            msg = "IMAP host is not configured. Set it in the Config tab."
            raise RuntimeError(msg)
        return {
            "host": host,
            "port": int(config_row.get("imap_port") or 993),
            "use_starttls": bool(_default(config_row.get("use_starttls"), default=False)),
            "verify_tls": bool(_default(config_row.get("verify_tls"), default=True)),
        }

    def _tables(self) -> tuple[type[SourceTable], ...]:
        """Resolve the TABLES tuple for this source.

        Defaults to ``shenas_sources.<name>.tables.TABLES`` so subclasses
        only need their own ``tables.py`` to register provider-scoped
        copies of the IMAP tables.
        """
        import importlib

        module = importlib.import_module(f"shenas_sources.{self.name}.tables")
        return tuple(module.TABLES)

    # -- Source contract ------------------------------------------------------

    def build_client(self) -> Any:
        from shenas_sources.imap.client import ImapClient

        auth_row = self.Auth.read_row()  # ty: ignore[unresolved-attribute]
        if not auth_row or not auth_row.get("username") or not auth_row.get("password"):
            msg = "No IMAP credentials. Configure them in the Auth tab."
            raise RuntimeError(msg)
        return ImapClient(
            username=auth_row["username"],
            password=auth_row["password"],
            **self.connection_params(),
        ).connect()

    def cleanup_client(self, client: Any) -> None:
        if client is not None:
            client.close()

    def authenticate(self, credentials: dict[str, str]) -> None:
        from shenas_sources.imap.client import ImapClient

        username = (credentials.get("username") or "").strip()
        password = credentials.get("password") or ""
        if not username or not password:
            msg = "username and password are required"
            raise ValueError(msg)
        ImapClient(
            username=username,
            password=password,
            **self.connection_params(),
        ).connect().close()
        self.Auth.write_row(username=username, password=password)  # ty: ignore[unresolved-attribute]

    def resources(self, client: Any) -> list[Any]:
        config_row = self.Config.read_row() or {}  # ty: ignore[unresolved-attribute]
        raw_mailboxes = (config_row.get("mailboxes") or "").strip()
        mailboxes = [name.strip() for name in raw_mailboxes.split(",") if name.strip()] if raw_mailboxes else None
        days = int(config_row.get("lookback_period") or 0)
        return [table.to_resource(client, mailboxes=mailboxes, lookback_days=days) for table in self._tables()]


def _default(value: Any, *, default: bool) -> bool:
    return default if value is None else bool(value)
