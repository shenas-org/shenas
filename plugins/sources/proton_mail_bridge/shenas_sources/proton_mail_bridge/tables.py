"""Proton Mail Bridge tables -- thin concrete subclasses of the shared IMAP base.

Each plugin needs its own concrete table classes so :class:`Source`
auto-prefixes ``_Meta.name`` with this plugin's slug
(``proton_mail_bridge__messages`` etc.) instead of re-prefixing the
``imap`` plugin's already-prefixed classes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from shenas_sources.imap.tables_base import MailboxesBase, MessagesBase

if TYPE_CHECKING:
    from shenas_sources.core.table import SourceTable


class Mailboxes(MailboxesBase):
    pass


class Messages(MessagesBase):
    pass


TABLES: tuple[type[SourceTable], ...] = (Mailboxes, Messages)
