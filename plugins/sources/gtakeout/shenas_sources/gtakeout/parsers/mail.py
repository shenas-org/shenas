"""Parse Gmail mbox exports from Takeout."""

from __future__ import annotations

import email.utils
import mailbox
from datetime import UTC
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def parse_mbox(files: list[Path]) -> Iterator[dict[str, Any]]:
    """Yield email metadata from mbox files (streamed, no body content stored)."""
    for path in files:
        if path.suffix != ".mbox":
            continue

        mbox = mailbox.mbox(str(path))
        for message in mbox:
            message_id = message.get("Message-ID", "")
            if not message_id:
                continue

            date_str = message.get("Date", "")
            timestamp = _parse_date(date_str)
            if not timestamp:
                continue

            labels = message.get("X-Gmail-Labels", "")
            from_addr = message.get("From", "")
            to_addr = message.get("To", "")
            subject = message.get("Subject", "")

            # Decode encoded headers
            from_addr = _decode_header(from_addr)
            to_addr = _decode_header(to_addr)
            subject = _decode_header(subject)

            yield {
                "message_id": message_id.strip("<>"),
                "timestamp": timestamp,
                "from_addr": from_addr,
                "to_addr": to_addr,
                "subject": subject,
                "labels": labels,
                "thread_id": message.get("X-GM-THRID", ""),
                "content_type": message.get_content_type(),
                "has_attachments": _has_attachments(message),
            }


def _parse_date(date_str: str) -> str | None:
    """Parse an email Date header into ISO format."""
    if not date_str:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(date_str)
        return parsed.astimezone(UTC).isoformat()
    except (ValueError, TypeError):
        return None


def _decode_header(value: str) -> str:
    """Decode RFC 2047 encoded header value."""
    if not value:
        return ""
    try:
        import email.header

        parts = email.header.decode_header(value)
        decoded = []
        for part, charset in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                decoded.append(part)
        return " ".join(decoded)
    except Exception:
        return value


def _has_attachments(message: mailbox.mboxMessage) -> bool:
    """Check if the message has any non-inline attachments."""
    if not message.is_multipart():
        return False
    for part in message.walk():
        disposition = part.get_content_disposition()
        if disposition == "attachment":
            return True
    return False
