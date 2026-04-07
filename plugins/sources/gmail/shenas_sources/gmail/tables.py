"""Gmail raw table schemas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_plugins.core.field import Field, TableKind


@dataclass
class Message:
    """Gmail message metadata + derived state flags."""

    __table__: ClassVar[str] = "messages"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "event"

    id: Annotated[str, Field(db_type="VARCHAR", description="Message ID")]
    thread_id: Annotated[str | None, Field(db_type="VARCHAR", description="Thread ID")] = None
    internal_date: Annotated[int, Field(db_type="BIGINT", description="Internal date as epoch milliseconds")] = 0
    date: Annotated[str | None, Field(db_type="VARCHAR", description="Date header value")] = None
    from_address: Annotated[str | None, Field(db_type="VARCHAR", description="From address")] = None
    to_address: Annotated[str | None, Field(db_type="VARCHAR", description="To address")] = None
    cc_address: Annotated[str | None, Field(db_type="VARCHAR", description="Cc address(es)")] = None
    bcc_address: Annotated[str | None, Field(db_type="VARCHAR", description="Bcc address(es)")] = None
    reply_to: Annotated[str | None, Field(db_type="VARCHAR", description="Reply-To address")] = None
    message_id_header: Annotated[str | None, Field(db_type="VARCHAR", description="SMTP Message-ID header")] = None
    in_reply_to: Annotated[str | None, Field(db_type="VARCHAR", description="In-Reply-To header")] = None
    references: Annotated[str | None, Field(db_type="TEXT", description="References header")] = None
    list_id: Annotated[str | None, Field(db_type="VARCHAR", description="List-Id header (mailing list marker)")] = None
    list_unsubscribe: Annotated[str | None, Field(db_type="VARCHAR", description="List-Unsubscribe header")] = None
    subject: Annotated[str | None, Field(db_type="VARCHAR", description="Subject line")] = None
    snippet: Annotated[str | None, Field(db_type="TEXT", description="Message snippet")] = None
    labels: Annotated[str | None, Field(db_type="VARCHAR", description="Comma-separated label IDs")] = None
    category: Annotated[
        str | None,
        Field(db_type="VARCHAR", description="Inbox category: PROMOTIONS / SOCIAL / UPDATES / FORUMS / PERSONAL"),
    ] = None
    is_read: Annotated[bool, Field(db_type="BOOLEAN", description="Message has been read")] = False
    is_starred: Annotated[bool, Field(db_type="BOOLEAN", description="Starred")] = False
    is_important: Annotated[bool, Field(db_type="BOOLEAN", description="Marked important by Gmail")] = False
    is_inbox: Annotated[bool, Field(db_type="BOOLEAN", description="Currently in inbox")] = False
    is_sent: Annotated[bool, Field(db_type="BOOLEAN", description="Sent by the user")] = False
    is_draft: Annotated[bool, Field(db_type="BOOLEAN", description="Is a draft")] = False
    is_trash: Annotated[bool, Field(db_type="BOOLEAN", description="In trash")] = False
    is_spam: Annotated[bool, Field(db_type="BOOLEAN", description="In spam")] = False
    is_chat: Annotated[bool, Field(db_type="BOOLEAN", description="Chat message")] = False
    size_estimate: Annotated[int, Field(db_type="INTEGER", description="Estimated message size in bytes")] = 0


@dataclass
class Label:
    """Gmail label."""

    __table__: ClassVar[str] = "labels"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "dimension"

    id: Annotated[str, Field(db_type="VARCHAR", description="Label ID")]
    name: Annotated[str | None, Field(db_type="VARCHAR", description="Label name")] = None
    type: Annotated[str | None, Field(db_type="VARCHAR", description="Label type (system or user)")] = None


@dataclass
class Profile:
    """Gmail account profile -- mailbox totals."""

    __table__: ClassVar[str] = "profile"
    __pk__: ClassVar[tuple[str, ...]] = ("email_address",)
    __kind__: ClassVar[TableKind] = "snapshot"

    email_address: Annotated[str, Field(db_type="VARCHAR", description="Account email")]
    messages_total: Annotated[int | None, Field(db_type="BIGINT", description="Total messages in mailbox")] = None
    threads_total: Annotated[int | None, Field(db_type="BIGINT", description="Total threads in mailbox")] = None
    history_id: Annotated[str | None, Field(db_type="VARCHAR", description="Current history ID")] = None


@dataclass
class Filter:
    """Gmail server-side filter rule."""

    __table__: ClassVar[str] = "filters"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    id: Annotated[str, Field(db_type="VARCHAR", description="Filter ID")]
    from_criteria: Annotated[str | None, Field(db_type="VARCHAR", description="Match: from")] = None
    to_criteria: Annotated[str | None, Field(db_type="VARCHAR", description="Match: to")] = None
    subject_criteria: Annotated[str | None, Field(db_type="VARCHAR", description="Match: subject")] = None
    query_criteria: Annotated[str | None, Field(db_type="TEXT", description="Match: raw query")] = None
    add_label_ids: Annotated[str | None, Field(db_type="VARCHAR", description="Action: add label IDs (comma sep)")] = None
    remove_label_ids: Annotated[str | None, Field(db_type="VARCHAR", description="Action: remove label IDs (comma sep)")] = (
        None
    )
    forward_to: Annotated[str | None, Field(db_type="VARCHAR", description="Action: forward to address")] = None


@dataclass
class Vacation:
    """Gmail vacation responder configuration."""

    __table__: ClassVar[str] = "vacation"
    __pk__: ClassVar[tuple[str, ...]] = ("singleton",)
    __kind__: ClassVar[TableKind] = "snapshot"

    singleton: Annotated[int, Field(db_type="INTEGER", description="Always 1 -- single-row table")] = 1
    enabled: Annotated[bool, Field(db_type="BOOLEAN", description="Vacation responder enabled")] = False
    response_subject: Annotated[str | None, Field(db_type="VARCHAR", description="Auto-reply subject")] = None
    response_body_plain: Annotated[str | None, Field(db_type="TEXT", description="Auto-reply plain body")] = None
    restrict_to_contacts: Annotated[bool, Field(db_type="BOOLEAN", description="Only contacts get a reply")] = False
    restrict_to_domain: Annotated[bool, Field(db_type="BOOLEAN", description="Only same-domain users get a reply")] = False
    start_time: Annotated[int | None, Field(db_type="BIGINT", description="Start (epoch ms)")] = None
    end_time: Annotated[int | None, Field(db_type="BIGINT", description="End (epoch ms)")] = None


@dataclass
class SendAs:
    """A 'Send mail as' identity configured on the account."""

    __table__: ClassVar[str] = "send_as"
    __pk__: ClassVar[tuple[str, ...]] = ("send_as_email",)
    __kind__: ClassVar[TableKind] = "snapshot"

    send_as_email: Annotated[str, Field(db_type="VARCHAR", description="The email address to send as")]
    display_name: Annotated[str | None, Field(db_type="VARCHAR", description="Display name")] = None
    reply_to_address: Annotated[str | None, Field(db_type="VARCHAR", description="Reply-To address")] = None
    is_default: Annotated[bool, Field(db_type="BOOLEAN", description="Default identity")] = False
    is_primary: Annotated[bool, Field(db_type="BOOLEAN", description="Primary identity")] = False
    treat_as_alias: Annotated[bool, Field(db_type="BOOLEAN", description="Treat as alias")] = False
    verification_status: Annotated[str | None, Field(db_type="VARCHAR", description="Verification status")] = None
