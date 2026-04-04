"""Gmail dlt resources -- messages, labels, threads."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import dlt

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


def _get_header(headers: list[dict[str, str]], name: str) -> str:
    """Extract a header value from Gmail message payload headers."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _parse_message(msg: dict[str, Any]) -> dict[str, Any]:
    headers = msg.get("payload", {}).get("headers", [])
    msg_labels = msg.get("labelIds", [])
    return {
        "id": msg["id"],
        "thread_id": msg.get("threadId"),
        "internal_date": int(msg.get("internalDate", 0)),
        "date": _get_header(headers, "Date"),
        "from_address": _get_header(headers, "From"),
        "to_address": _get_header(headers, "To"),
        "subject": _get_header(headers, "Subject"),
        "snippet": msg.get("snippet", ""),
        "labels": ", ".join(msg_labels),
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


@dlt.resource(write_disposition="merge", primary_key="id")
def messages(
    service: Any,
    query: str = "",
    _cursor: dlt.sources.incremental[int] = dlt.sources.incremental("internal_date", initial_value=None),
) -> Iterator[list[dict[str, Any]]]:
    """Yield Gmail messages in batches for single-resource usage."""
    yield from message_pages(service, query)


@dlt.resource(write_disposition="replace")
def labels(service: Any) -> Iterator[dict[str, Any]]:
    """Yield all Gmail labels."""
    result = service.users().labels().list(userId="me").execute()
    yield from result.get("labels", [])
