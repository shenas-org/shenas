"""Gmail source tables.

Each table is a subclass of one of the kind base classes in
``shenas_sources.core.table``. Notable design choices:

- ``Messages`` is an ``EventTable`` keyed on ``internal_date``.
- ``Labels`` is a ``DimensionTable`` (SCD2) so label renames preserve
  history (the previous "replace" loader silently rewrote every
  historical join).
- ``Profile``, ``Filters``, ``Vacation``, ``SendAs`` are ``SnapshotTable``
  (SCD2) so changes to mailbox totals, filter rules, vacation settings,
  and send-as identities mint new versions.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from shenas_plugins.core.field import Field
from shenas_sources.core.table import (
    DimensionTable,
    EventTable,
    SnapshotTable,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


_CATEGORY_LABELS = {
    "CATEGORY_PROMOTIONS": "PROMOTIONS",
    "CATEGORY_SOCIAL": "SOCIAL",
    "CATEGORY_UPDATES": "UPDATES",
    "CATEGORY_FORUMS": "FORUMS",
    "CATEGORY_PERSONAL": "PERSONAL",
}

BATCH_SIZE = 25
PAGE_DELAY = 3


# ---------------------------------------------------------------------------
# Helpers shared between message_pages() and the Messages table
# ---------------------------------------------------------------------------


def _get_header(headers: list[dict[str, str]], name: str) -> str:
    """Extract a header value from Gmail message payload headers."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _parse_message(msg: dict[str, Any]) -> dict[str, Any]:
    headers = msg.get("payload", {}).get("headers", [])
    msg_labels = msg.get("labelIds", []) or []
    label_set = set(msg_labels)
    category: str | None = None
    for cat_label, label_value in _CATEGORY_LABELS.items():
        if cat_label in label_set:
            category = label_value
            break
    return {
        "id": msg["id"],
        "thread_id": msg.get("threadId"),
        "internal_date": int(msg.get("internalDate", 0)),
        "date": _get_header(headers, "Date"),
        "from_address": _get_header(headers, "From"),
        "to_address": _get_header(headers, "To"),
        "cc_address": _get_header(headers, "Cc") or None,
        "bcc_address": _get_header(headers, "Bcc") or None,
        "reply_to": _get_header(headers, "Reply-To") or None,
        "message_id_header": _get_header(headers, "Message-ID") or None,
        "in_reply_to": _get_header(headers, "In-Reply-To") or None,
        "references": _get_header(headers, "References") or None,
        "list_id": _get_header(headers, "List-Id") or None,
        "list_unsubscribe": _get_header(headers, "List-Unsubscribe") or None,
        "subject": _get_header(headers, "Subject"),
        "snippet": msg.get("snippet", ""),
        "labels": ", ".join(msg_labels),
        "category": category,
        "is_read": "UNREAD" not in label_set,
        "is_starred": "STARRED" in label_set,
        "is_important": "IMPORTANT" in label_set,
        "is_inbox": "INBOX" in label_set,
        "is_sent": "SENT" in label_set,
        "is_draft": "DRAFT" in label_set,
        "is_trash": "TRASH" in label_set,
        "is_spam": "SPAM" in label_set,
        "is_chat": "CHAT" in label_set,
        "size_estimate": msg.get("sizeEstimate", 0),
    }


def _api_call_with_retry(fn: Any, max_retries: int = 5) -> Any:
    """Execute a Google API call with exponential backoff on quota errors."""
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            exc_str = repr(exc)
            is_rate_limit = any(
                s in exc_str for s in ("rateLimitExceeded", "Quota exceeded", "HttpError 429", "HttpError 403")
            )
            if is_rate_limit:
                if attempt == max_retries:
                    raise
                wait = 15 * (attempt + 1)
                logger.warning("Rate limited, waiting %ds before retry (%d/%d)...", wait, attempt + 1, max_retries)
                time.sleep(wait)
            else:
                raise
    return None


def _batch_get_messages(service: Any, msg_ids: list[str]) -> list[dict[str, Any]]:
    """Fetch multiple messages in a single batch request."""
    results: list[dict[str, Any]] = []

    def _callback(_request_id: str, response: Any, exception: Any) -> None:
        if exception is None:
            results.append(response)

    batch = service.new_batch_http_request(callback=_callback)
    for msg_id in msg_ids:
        batch.add(service.users().messages().get(userId="me", id=msg_id, format="metadata"))
    _api_call_with_retry(batch.execute)
    return results


def message_pages(service: Any, query: str = "") -> Iterator[list[dict[str, Any]]]:
    """Yield pages of parsed Gmail messages. Each page is a list of dicts.

    Used by Source.sync() to flush page-by-page for memory reasons. The
    Messages.extract classmethod just flattens the same iterator.
    """
    page_token: str | None = None
    page_num = 0
    while True:
        params: dict[str, Any] = {"userId": "me", "maxResults": 25}
        if query:
            params["q"] = query
        if page_token:
            params["pageToken"] = page_token

        result = _api_call_with_retry(lambda p=params: service.users().messages().list(**p).execute())
        msg_ids = [m["id"] for m in result.get("messages", [])]
        page_num += 1

        if msg_ids:
            raw = _batch_get_messages(service, msg_ids)
            page = [_parse_message(m) for m in raw]
            logger.info("Gmail page %d: %d messages fetched", page_num, len(page))
            yield page

        page_token = result.get("nextPageToken")
        if not page_token:
            break
        time.sleep(PAGE_DELAY)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class Messages(EventTable):
    """A Gmail message (metadata + derived state flags)."""

    table_name: ClassVar[str] = "messages"
    table_display_name: ClassVar[str] = "Gmail Messages"
    table_description: ClassVar[str | None] = "Email metadata, headers, and label-derived state flags."
    table_pk: ClassVar[tuple[str, ...]] = ("id",)
    time_at: ClassVar[str] = "internal_date"
    cursor_column: ClassVar[str] = "internal_date"

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

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Iterator[dict[str, Any]]:
        for page in message_pages(client):
            yield from page


class Labels(DimensionTable):
    """Gmail label. SCD2 captures rename history."""

    table_name: ClassVar[str] = "labels"
    table_display_name: ClassVar[str] = "Gmail Labels"
    table_description: ClassVar[str | None] = "Labels defined on the user's mailbox."
    table_pk: ClassVar[tuple[str, ...]] = ("id",)

    id: Annotated[str, Field(db_type="VARCHAR", description="Label ID")]
    label_name: Annotated[str | None, Field(db_type="VARCHAR", description="Label name")] = None
    type: Annotated[str | None, Field(db_type="VARCHAR", description="Label type (system or user)")] = None

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Iterator[dict[str, Any]]:
        result = client.users().labels().list(userId="me").execute()
        for label in result.get("labels", []):
            yield {
                "id": label.get("id", ""),
                "label_name": label.get("name"),
                "type": label.get("type"),
            }


class Profile(SnapshotTable):
    """Gmail account profile -- mailbox totals."""

    table_name: ClassVar[str] = "profile"
    table_display_name: ClassVar[str] = "Gmail Profile"
    table_description: ClassVar[str | None] = "Per-account mailbox totals snapshot."
    table_pk: ClassVar[tuple[str, ...]] = ("email_address",)

    email_address: Annotated[str, Field(db_type="VARCHAR", description="Account email")]
    messages_total: Annotated[int | None, Field(db_type="BIGINT", description="Total messages in mailbox")] = None
    threads_total: Annotated[int | None, Field(db_type="BIGINT", description="Total threads in mailbox")] = None
    history_id: Annotated[str | None, Field(db_type="VARCHAR", description="Current history ID")] = None

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Iterator[dict[str, Any]]:
        data = client.users().getProfile(userId="me").execute()
        yield {
            "email_address": data.get("emailAddress", ""),
            "messages_total": data.get("messagesTotal"),
            "threads_total": data.get("threadsTotal"),
            "history_id": data.get("historyId"),
        }


class Filters(SnapshotTable):
    """Gmail server-side filter rule."""

    table_name: ClassVar[str] = "filters"
    table_display_name: ClassVar[str] = "Gmail Filters"
    table_description: ClassVar[str | None] = "Server-side filter rules."
    table_pk: ClassVar[tuple[str, ...]] = ("id",)

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

    @staticmethod
    def _action_labels(action: dict[str, Any], key: str) -> str | None:
        ids = action.get(key) or []
        return ", ".join(ids) if ids else None

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Iterator[dict[str, Any]]:
        try:
            result = client.users().settings().filters().list(userId="me").execute()
        except Exception:
            return
        for f in result.get("filter") or []:
            criteria = f.get("criteria") or {}
            action = f.get("action") or {}
            yield {
                "id": f.get("id", ""),
                "from_criteria": criteria.get("from"),
                "to_criteria": criteria.get("to"),
                "subject_criteria": criteria.get("subject"),
                "query_criteria": criteria.get("query"),
                "add_label_ids": cls._action_labels(action, "addLabelIds"),
                "remove_label_ids": cls._action_labels(action, "removeLabelIds"),
                "forward_to": action.get("forward"),
            }


class Vacation(SnapshotTable):
    """Gmail vacation responder configuration (single row)."""

    table_name: ClassVar[str] = "vacation"
    table_display_name: ClassVar[str] = "Vacation Responder"
    table_description: ClassVar[str | None] = "Vacation responder configuration."
    table_pk: ClassVar[tuple[str, ...]] = ("singleton",)

    singleton: Annotated[int, Field(db_type="INTEGER", description="Always 1 -- single-row table")] = 1
    enabled: Annotated[bool, Field(db_type="BOOLEAN", description="Vacation responder enabled")] = False
    response_subject: Annotated[str | None, Field(db_type="VARCHAR", description="Auto-reply subject")] = None
    response_body_plain: Annotated[str | None, Field(db_type="TEXT", description="Auto-reply plain body")] = None
    restrict_to_contacts: Annotated[bool, Field(db_type="BOOLEAN", description="Only contacts get a reply")] = False
    restrict_to_domain: Annotated[bool, Field(db_type="BOOLEAN", description="Only same-domain users get a reply")] = False
    start_time: Annotated[int | None, Field(db_type="BIGINT", description="Start (epoch ms)")] = None
    end_time: Annotated[int | None, Field(db_type="BIGINT", description="End (epoch ms)")] = None

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Iterator[dict[str, Any]]:
        try:
            data = client.users().settings().getVacation(userId="me").execute()
        except Exception:
            return
        yield {
            "singleton": 1,
            "enabled": bool(data.get("enableAutoReply", False)),
            "response_subject": data.get("responseSubject"),
            "response_body_plain": data.get("responseBodyPlainText"),
            "restrict_to_contacts": bool(data.get("restrictToContacts", False)),
            "restrict_to_domain": bool(data.get("restrictToDomain", False)),
            "start_time": int(data["startTime"]) if data.get("startTime") else None,
            "end_time": int(data["endTime"]) if data.get("endTime") else None,
        }


class SendAs(SnapshotTable):
    """A 'Send mail as' identity configured on the account."""

    table_name: ClassVar[str] = "send_as"
    table_display_name: ClassVar[str] = "Send-As Identities"
    table_description: ClassVar[str | None] = "Send-mail-as identities configured on the account."
    table_pk: ClassVar[tuple[str, ...]] = ("send_as_email",)

    send_as_email: Annotated[str, Field(db_type="VARCHAR", description="The email address to send as")]
    display_name_: Annotated[str | None, Field(db_type="VARCHAR", description="Display name")] = None
    reply_to_address: Annotated[str | None, Field(db_type="VARCHAR", description="Reply-To address")] = None
    is_default: Annotated[bool, Field(db_type="BOOLEAN", description="Default identity")] = False
    is_primary: Annotated[bool, Field(db_type="BOOLEAN", description="Primary identity")] = False
    treat_as_alias: Annotated[bool, Field(db_type="BOOLEAN", description="Treat as alias")] = False
    verification_status: Annotated[str | None, Field(db_type="VARCHAR", description="Verification status")] = None

    @classmethod
    def extract(cls, client: Any, **_: Any) -> Iterator[dict[str, Any]]:
        try:
            result = client.users().settings().sendAs().list(userId="me").execute()
        except Exception:
            return
        for s in result.get("sendAs") or []:
            email = s.get("sendAsEmail")
            if not email:
                continue
            yield {
                "send_as_email": email,
                "display_name_": s.get("displayName"),
                "reply_to_address": s.get("replyToAddress"),
                "is_default": bool(s.get("isDefault", False)),
                "is_primary": bool(s.get("isPrimary", False)),
                "treat_as_alias": bool(s.get("treatAsAlias", False)),
                "verification_status": s.get("verificationStatus"),
            }


TABLES: tuple[type, ...] = (Messages, Labels, Profile, Filters, Vacation, SendAs)
