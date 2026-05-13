"""Abstract IMAP table classes shared between the generic ``imap`` plugin
and any subclass plugin (e.g. ``proton_mail_bridge``).

These define every field, ``_Meta`` attribute, and ``extract`` method.
Each plugin's own ``tables.py`` then trivially subclasses them so the
class identities are unique -- the source-name prefix mutation in
:meth:`Source.__init_subclass__` would otherwise re-prefix the same
class twice across plugins.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.relation import PlotHint
from app.table import Field
from shenas_sources.core import get_logger
from shenas_sources.core.table import DimensionTable, EventTable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.imap.client import ImapClient

logger = get_logger(__name__)


@dataclass
class MailboxesBase(DimensionTable):
    """An IMAP mailbox / folder. SCD2 captures rename history."""

    _abstract: ClassVar[bool] = True

    class _Meta(DimensionTable._Meta):
        name = "mailboxes"
        display_name = "Mailboxes"
        description = "IMAP mailboxes (folders) on the account."
        pk = ("name",)

    name: Annotated[str, Field(db_type="VARCHAR", description="Mailbox name", display_name="Mailbox")] = ""
    delimiter: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Hierarchy delimiter", display_name="Delimiter"),
    ] = None
    flags: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="LIST response flags", display_name="Flags"),
    ] = None
    uidvalidity: Annotated[
        int | None,
        Field(db_type="BIGINT", description="UIDVALIDITY value", display_name="UIDVALIDITY"),
    ] = None

    @classmethod
    def extract(cls, client: ImapClient, **_: Any) -> Iterator[dict[str, Any]]:
        for mailbox in client.list_mailboxes():
            uidvalidity: int | None = None
            try:
                status = client.select(mailbox["name"])
                uidvalidity = status.get("uidvalidity")
            except Exception:
                logger.warning("STATUS failed for mailbox %r", mailbox["name"])
            yield {
                "name": mailbox["name"],
                "delimiter": mailbox.get("delimiter") or None,
                "flags": mailbox.get("flags") or None,
                "uidvalidity": uidvalidity,
            }


@dataclass
class MessagesBase(EventTable):
    """A message envelope (headers + flags) from one IMAP mailbox."""

    _abstract: ClassVar[bool] = True

    class _Meta(EventTable._Meta):
        name = "messages"
        display_name = "Messages"
        description = "Message metadata, headers, and flags fetched via IMAP."
        pk = ("mailbox", "uidvalidity", "uid")
        time_at = "internal_date"
        plot = (PlotHint("size_bytes"),)

    mailbox: Annotated[str, Field(db_type="VARCHAR", description="Source mailbox", display_name="Mailbox")] = ""
    uidvalidity: Annotated[
        int,
        Field(db_type="BIGINT", description="UIDVALIDITY at fetch time", display_name="UIDVALIDITY"),
    ] = 0
    uid: Annotated[int, Field(db_type="BIGINT", description="IMAP UID", display_name="UID")] = 0
    internal_date: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="IMAP INTERNALDATE", display_name="Internal Date"),
    ] = None
    date_header: Annotated[
        str | None,
        Field(db_type="TIMESTAMP", description="Date header value", display_name="Date Header"),
    ] = None
    from_address: Annotated[str | None, Field(db_type="VARCHAR", description="From address", display_name="From")] = None
    to_address: Annotated[str | None, Field(db_type="VARCHAR", description="To address(es)", display_name="To")] = None
    cc_address: Annotated[str | None, Field(db_type="VARCHAR", description="Cc address(es)", display_name="Cc")] = None
    bcc_address: Annotated[str | None, Field(db_type="VARCHAR", description="Bcc address(es)", display_name="Bcc")] = None
    reply_to: Annotated[str | None, Field(db_type="VARCHAR", description="Reply-To address", display_name="Reply-To")] = None
    subject: Annotated[str | None, Field(db_type="VARCHAR", description="Subject line", display_name="Subject")] = None
    message_id: Annotated[str | None, Field(db_type="VARCHAR", description="Message-ID header", display_name="Message-ID")] = (
        None
    )
    in_reply_to: Annotated[
        str | None, Field(db_type="VARCHAR", description="In-Reply-To header", display_name="In-Reply-To")
    ] = None
    references: Annotated[str | None, Field(db_type="TEXT", description="References header", display_name="References")] = None
    list_id: Annotated[str | None, Field(db_type="VARCHAR", description="List-Id header", display_name="List ID")] = None
    list_unsubscribe: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="List-Unsubscribe header", display_name="List-Unsubscribe"),
    ] = None
    is_seen: Annotated[bool, Field(db_type="BOOLEAN", description="Read", display_name="Read")] = False
    is_flagged: Annotated[bool, Field(db_type="BOOLEAN", description="Flagged / starred", display_name="Flagged")] = False
    is_answered: Annotated[bool, Field(db_type="BOOLEAN", description="Replied", display_name="Answered")] = False
    is_draft: Annotated[bool, Field(db_type="BOOLEAN", description="Draft", display_name="Draft")] = False
    is_deleted: Annotated[bool, Field(db_type="BOOLEAN", description="Marked for deletion", display_name="Deleted")] = False
    flags: Annotated[str | None, Field(db_type="VARCHAR", description="Comma-separated IMAP flags", display_name="Flags")] = (
        None
    )
    size_bytes: Annotated[
        int | None,
        Field(db_type="BIGINT", description="RFC822 size", display_name="Size", unit="bytes"),
    ] = None

    @classmethod
    def extract(
        cls,
        client: ImapClient,
        *,
        mailboxes: list[str] | None = None,
        lookback_days: int = 90,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        names = mailboxes or [mb["name"] for mb in client.list_mailboxes()]
        for mailbox_name in names:
            try:
                status = client.select(mailbox_name)
            except Exception:
                logger.warning("Skipping mailbox %r: SELECT failed", mailbox_name)
                continue
            uidvalidity = status.get("uidvalidity") or 0
            uids = client.search_uids(since_days=lookback_days)
            logger.info("Mailbox %r: %d uids (lookback %d days)", mailbox_name, len(uids), lookback_days)
            if not uids:
                continue
            for envelope in client.fetch_envelopes(uids):
                envelope["mailbox"] = mailbox_name
                envelope["uidvalidity"] = uidvalidity
                yield envelope
