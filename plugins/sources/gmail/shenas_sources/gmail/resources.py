"""Gmail dlt resources -- messages, labels, profile, filters, vacation, send_as."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import dlt

from shenas_datasets.core.dlt import dataclass_to_dlt_columns
from shenas_sources.gmail.tables import Filter, Label, Message, Profile, SendAs, Vacation

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


BATCH_SIZE = 25
PAGE_DELAY = 3


def message_pages(service: Any, query: str = "") -> Iterator[list[dict[str, Any]]]:
    """Yield pages of parsed Gmail messages. Each page is a list of dicts."""
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


@dlt.resource(write_disposition="merge", primary_key=list(Message.__pk__), columns=dataclass_to_dlt_columns(Message))
def messages(
    service: Any,
    query: str = "",
    _cursor: dlt.sources.incremental[int] = dlt.sources.incremental("internal_date", initial_value=None),
) -> Iterator[list[dict[str, Any]]]:
    """Yield Gmail messages in batches for single-resource usage."""
    yield from message_pages(service, query)


@dlt.resource(write_disposition="replace", columns=dataclass_to_dlt_columns(Label))
def labels(service: Any) -> Iterator[dict[str, Any]]:
    """Yield all Gmail labels."""
    result = service.users().labels().list(userId="me").execute()
    yield from result.get("labels", [])


@dlt.resource(name="profile", write_disposition="replace", columns=dataclass_to_dlt_columns(Profile))
def profile(service: Any) -> Iterator[dict[str, Any]]:
    """Yield the Gmail account profile (single row)."""
    data = service.users().getProfile(userId="me").execute()
    yield {
        "email_address": data.get("emailAddress", ""),
        "messages_total": data.get("messagesTotal"),
        "threads_total": data.get("threadsTotal"),
        "history_id": data.get("historyId"),
    }


def _action_labels(action: dict[str, Any], key: str) -> str | None:
    ids = action.get(key) or []
    return ", ".join(ids) if ids else None


@dlt.resource(name="filters", write_disposition="replace", columns=dataclass_to_dlt_columns(Filter))
def filters(service: Any) -> Iterator[dict[str, Any]]:
    """Yield server-side Gmail filter rules."""
    try:
        result = service.users().settings().filters().list(userId="me").execute()
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
            "add_label_ids": _action_labels(action, "addLabelIds"),
            "remove_label_ids": _action_labels(action, "removeLabelIds"),
            "forward_to": action.get("forward"),
        }


@dlt.resource(name="vacation", write_disposition="replace", columns=dataclass_to_dlt_columns(Vacation))
def vacation(service: Any) -> Iterator[dict[str, Any]]:
    """Yield the vacation responder configuration (single row)."""
    try:
        data = service.users().settings().getVacation(userId="me").execute()
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


@dlt.resource(name="send_as", write_disposition="replace", columns=dataclass_to_dlt_columns(SendAs))
def send_as(service: Any) -> Iterator[dict[str, Any]]:
    """Yield 'send mail as' identities."""
    try:
        result = service.users().settings().sendAs().list(userId="me").execute()
    except Exception:
        return
    for s in result.get("sendAs") or []:
        email = s.get("sendAsEmail")
        if not email:
            continue
        yield {
            "send_as_email": email,
            "display_name": s.get("displayName"),
            "reply_to_address": s.get("replyToAddress"),
            "is_default": bool(s.get("isDefault", False)),
            "is_primary": bool(s.get("isPrimary", False)),
            "treat_as_alias": bool(s.get("treatAsAlias", False)),
            "verification_status": s.get("verificationStatus"),
        }
