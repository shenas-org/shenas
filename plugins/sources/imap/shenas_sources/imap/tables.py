"""Concrete IMAP table classes for the generic ``imap`` source plugin.

The schemas + extract logic live in :mod:`shenas_sources.imap.tables_base`.
This module just creates concrete subclasses so :class:`Source` can prefix
their ``_Meta.name`` with the source slug (``imap__messages`` etc.).
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
