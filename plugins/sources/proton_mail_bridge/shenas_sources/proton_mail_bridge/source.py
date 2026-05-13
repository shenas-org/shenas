"""Proton Mail Bridge source -- IMAP source preset for the local Bridge process.

Reuses :class:`shenas_sources.imap.source.ImapSource` for all IMAP
plumbing. This subclass only provides Proton-specific defaults:

- IMAP host / port / TLS settings hardcoded for the Bridge (127.0.0.1:1143
  with STARTTLS, certificate verification disabled because Bridge issues
  a self-signed cert).
- Auth / Config tables namespaced under this plugin so the Bridge
  credentials don't share a row with a generic IMAP source.
- User-facing copy that mentions the Bridge mailbox password rather than
  the Proton account password.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shenas_sources.imap.source import ImapAuth, ImapConfig, ImapSource


@dataclass
class ProtonMailBridgeAuth(ImapAuth):
    class _Meta(ImapAuth._Meta):
        name = ""  # forces Source.__init_subclass__ to set source_proton_mail_bridge


@dataclass
class ProtonMailBridgeConfig(ImapConfig):
    class _Meta(ImapConfig._Meta):
        name = ""  # forces Source.__init_subclass__ to set source_proton_mail_bridge


class ProtonMailBridgeSource(ImapSource):
    name = "proton_mail_bridge"
    display_name = "Proton Mail Bridge"
    description = (
        "Syncs message envelope metadata from Proton Mail via the locally-"
        "running Proton Mail Bridge.\n\n"
        "The Bridge exposes IMAP on 127.0.0.1:1143 (STARTTLS) with a self-"
        "signed certificate. Use the bridge-generated mailbox password from "
        "the Bridge app, not your Proton account password."
    )

    Auth: ClassVar[type] = ProtonMailBridgeAuth
    Config: ClassVar[type] = ProtonMailBridgeConfig

    auth_instructions = (
        "Open Proton Mail Bridge, select your account, and copy the IMAP "
        "username (your Proton email) and the bridge-generated mailbox "
        "password (Mailbox details > Password). The Bridge must be running "
        "locally for sync to succeed."
    )

    def connection_params(self) -> dict[str, Any]:
        """Hardcode Bridge defaults; let user-set Config rows override."""
        config_row = self.Config.read_row() or {}  # ty: ignore[unresolved-attribute]
        return {
            "host": config_row.get("imap_host") or "127.0.0.1",
            "port": int(config_row.get("imap_port") or 1143),
            "use_starttls": _coerce_bool(config_row.get("use_starttls"), default=True),
            "verify_tls": _coerce_bool(config_row.get("verify_tls"), default=False),
        }


def _coerce_bool(value: Any, *, default: bool) -> bool:
    return default if value is None else bool(value)
