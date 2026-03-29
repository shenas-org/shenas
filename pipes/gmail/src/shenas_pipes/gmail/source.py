"""Gmail dlt resources -- messages, labels, threads."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import dlt


def _get_header(headers: list[dict[str, str]], name: str) -> str:
    """Extract a header value from Gmail message payload headers."""
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


@dlt.resource(write_disposition="merge", primary_key="id")
def messages(
    service: Any,
    query: str = "",
    cursor: dlt.sources.incremental[int] = dlt.sources.incremental("internal_date", initial_value=None),
) -> Iterator[dict[str, Any]]:
    """Yield Gmail messages with metadata."""
    page_token: str | None = None
    while True:
        params: dict[str, Any] = {"userId": "me", "maxResults": 100}
        if query:
            params["q"] = query
        if page_token:
            params["pageToken"] = page_token

        result = service.users().messages().list(**params).execute()
        msg_list = result.get("messages", [])

        for msg_ref in msg_list:
            msg = service.users().messages().get(userId="me", id=msg_ref["id"], format="metadata").execute()

            internal_date = int(msg.get("internalDate", 0))

            # Skip messages older than the cursor
            if cursor.last_value and internal_date <= cursor.last_value:
                return

            headers = msg.get("payload", {}).get("headers", [])
            labels = msg.get("labelIds", [])

            yield {
                "id": msg["id"],
                "thread_id": msg.get("threadId"),
                "internal_date": internal_date,
                "date": _get_header(headers, "Date"),
                "from_address": _get_header(headers, "From"),
                "to_address": _get_header(headers, "To"),
                "subject": _get_header(headers, "Subject"),
                "snippet": msg.get("snippet", ""),
                "labels": ", ".join(labels),
                "size_estimate": msg.get("sizeEstimate", 0),
            }

        page_token = result.get("nextPageToken")
        if not page_token:
            break


@dlt.resource(write_disposition="replace")
def labels(service: Any) -> Iterator[dict[str, Any]]:
    """Yield all Gmail labels."""
    result = service.users().labels().list(userId="me").execute()
    for label in result.get("labels", []):
        yield label
