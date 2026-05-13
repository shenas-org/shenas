"""Thin IMAP wrapper used by the generic ``imap`` source and its subclasses.

Uses stdlib ``imaplib`` + ``email`` so the plugin has no external runtime
dependency. Speaks RFC 3501 enough to:

- list mailboxes (with their hierarchy delimiter and LIST flags)
- SELECT a mailbox read-only and return its UIDVALIDITY + EXISTS counts
- UID SEARCH SINCE <date>
- UID FETCH headers + flags + INTERNALDATE in batches
"""

from __future__ import annotations

import email
import imaplib
import re
import ssl
from datetime import UTC, datetime, timedelta
from email.header import decode_header, make_header
from email.utils import getaddresses, parsedate_to_datetime
from typing import TYPE_CHECKING, Any

from shenas_sources.core import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

logger = get_logger(__name__)


_LIST_RE = re.compile(rb'^\((?P<flags>[^)]*)\) "(?P<delim>[^"]*)" (?P<name>.+)$')
_UID_RE = re.compile(rb"UID (\d+)")
_INTERNALDATE_RE = re.compile(rb'INTERNALDATE "([^"]+)"')
_SIZE_RE = re.compile(rb"RFC822\.SIZE (\d+)")
_FLAGS_RE = re.compile(rb"FLAGS \(([^)]*)\)")


class ImapClient:
    """Generic IMAP client.

    ``verify_tls`` controls whether the server certificate is verified.
    Set to ``False`` for local bridge processes (Proton Mail Bridge,
    Hydroxide) which use a self-signed cert on 127.0.0.1.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        use_starttls: bool = True,
        verify_tls: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_starttls = use_starttls
        self.verify_tls = verify_tls
        self._imap: imaplib.IMAP4 | None = None

    # -- connection lifecycle -------------------------------------------------

    def _ssl_context(self) -> ssl.SSLContext:
        ctx = ssl.create_default_context()
        if not self.verify_tls:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def connect(self) -> ImapClient:
        ctx = self._ssl_context()
        if self.use_starttls:
            imap: imaplib.IMAP4 = imaplib.IMAP4(self.host, self.port)
            imap.starttls(ctx)
        else:
            imap = imaplib.IMAP4_SSL(self.host, self.port, ssl_context=ctx)
        imap.login(self.username, self.password)
        self._imap = imap
        return self

    def close(self) -> None:
        if self._imap is None:
            return
        try:
            self._imap.logout()
        except Exception:
            logger.debug("IMAP logout failed", exc_info=True)
        finally:
            self._imap = None

    @property
    def imap(self) -> imaplib.IMAP4:
        if self._imap is None:
            msg = "IMAP not connected -- call connect() first"
            raise RuntimeError(msg)
        return self._imap

    # -- mailbox / folder discovery ------------------------------------------

    def list_mailboxes(self) -> list[dict[str, str]]:
        typ, raw = self.imap.list()
        if typ != "OK" or not raw:
            return []
        result: list[dict[str, str]] = []
        for line in raw:
            if not line:
                continue
            # imaplib returns bytes for normal LIST entries; literal-string responses
            # arrive as a 2-tuple (header, literal). Flatten both to bytes.
            if isinstance(line, tuple):
                line_bytes = b"".join(part for part in line if isinstance(part, bytes))
            elif isinstance(line, bytes):
                line_bytes = line
            else:
                continue
            match = _LIST_RE.match(line_bytes)
            if not match:
                continue
            name = match.group("name").decode("utf-8", "replace").strip()
            if name.startswith('"') and name.endswith('"'):
                name = name[1:-1]
            result.append(
                {
                    "name": name,
                    "delimiter": match.group("delim").decode("utf-8", "replace"),
                    "flags": match.group("flags").decode("utf-8", "replace"),
                }
            )
        return result

    def select(self, mailbox: str) -> dict[str, Any]:
        """SELECT a mailbox read-only and return UIDVALIDITY + message count."""
        quoted = _quote_mailbox(mailbox)
        typ, _ = self.imap.select(mailbox=quoted, readonly=True)
        if typ != "OK":
            msg = f"IMAP SELECT failed for {mailbox!r}"
            raise RuntimeError(msg)
        typ, raw = self.imap.status(quoted, "(UIDVALIDITY MESSAGES)")
        uidvalidity = 0
        messages = 0
        if typ == "OK" and raw:
            text = raw[0].decode("utf-8", "replace") if isinstance(raw[0], bytes) else str(raw[0])
            uvm = re.search(r"UIDVALIDITY (\d+)", text)
            mm = re.search(r"MESSAGES (\d+)", text)
            if uvm:
                uidvalidity = int(uvm.group(1))
            if mm:
                messages = int(mm.group(1))
        return {"uidvalidity": uidvalidity, "messages": messages}

    # -- search + fetch -------------------------------------------------------

    def search_uids(self, *, since_days: int = 0) -> list[int]:
        if since_days > 0:
            since = (datetime.now(UTC) - timedelta(days=since_days)).strftime("%d-%b-%Y")
            typ, raw = self.imap.uid("SEARCH", "SINCE", since)
        else:
            typ, raw = self.imap.uid("SEARCH", "ALL")
        if typ != "OK" or not raw:
            return []
        ids: list[int] = []
        for line in raw:
            if not line:
                continue
            ids.extend(int(x) for x in line.split() if x.isdigit())
        return ids

    def fetch_envelopes(self, uids: Iterable[int], *, batch_size: int = 100) -> Iterator[dict[str, Any]]:
        uid_list = list(uids)
        for start in range(0, len(uid_list), batch_size):
            chunk = uid_list[start : start + batch_size]
            if not chunk:
                continue
            uid_set = ",".join(str(uid) for uid in chunk)
            typ, raw = self.imap.uid(
                "FETCH",
                uid_set,
                "(UID INTERNALDATE FLAGS RFC822.SIZE BODY.PEEK[HEADER])",
            )
            if typ != "OK" or not raw:
                continue
            yield from _parse_fetch_response(raw)


# -- helpers -----------------------------------------------------------------


def _quote_mailbox(name: str) -> str:
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _parse_fetch_response(raw: list[Any]) -> Iterator[dict[str, Any]]:
    """Walk the imaplib FETCH response and yield one envelope per message.

    imaplib returns a flat list where each message appears as a 2-tuple:
    ``(b"<n> (UID ... INTERNALDATE ... FLAGS (...) RFC822.SIZE N {bytes}",
       b"<rfc822 header bytes>")`` followed by a trailing ``b")"``.
    """
    for item in raw:
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        head = item[0] if isinstance(item[0], bytes) else b""
        body = item[1] if isinstance(item[1], bytes) else b""
        uid_match = _UID_RE.search(head)
        if not uid_match:
            continue
        internaldate_match = _INTERNALDATE_RE.search(head)
        size_match = _SIZE_RE.search(head)
        flags_match = _FLAGS_RE.search(head)
        try:
            msg = email.message_from_bytes(body)
        except Exception:
            logger.debug("Failed to parse RFC822 headers for UID %s", uid_match.group(1), exc_info=True)
            msg = None
        yield envelope_dict(
            uid=int(uid_match.group(1)),
            internaldate=internaldate_match.group(1).decode("ascii", "replace") if internaldate_match else "",
            flags_text=flags_match.group(1).decode("ascii", "replace") if flags_match else "",
            size=int(size_match.group(1)) if size_match else 0,
            msg=msg,
        )


def envelope_dict(*, uid: int, internaldate: str, flags_text: str, size: int, msg: Any) -> dict[str, Any]:
    """Convert IMAP fetch fragments into a plain envelope row dict."""

    def _header(key: str) -> str | None:
        if not msg:
            return None
        value = msg.get(key)
        if not value:
            return None
        try:
            return str(make_header(decode_header(str(value))))
        except Exception:
            return str(value)

    def _addresses(key: str) -> str | None:
        if not msg:
            return None
        raw_values = msg.get_all(key) or []
        if not raw_values:
            return None
        addresses = getaddresses(raw_values)
        flat = ", ".join(addr for _, addr in addresses if addr)
        return flat or None

    flag_set = {flag.strip().upper() for flag in flags_text.split() if flag.strip()}
    internal_dt = _parse_imap_date(internaldate)
    date_dt = _parse_rfc2822_date(_header("Date"))
    return {
        "uid": uid,
        "internal_date": internal_dt.isoformat() if internal_dt else None,
        "date_header": date_dt.isoformat() if date_dt else _header("Date"),
        "size_bytes": size,
        "from_address": _addresses("From"),
        "to_address": _addresses("To"),
        "cc_address": _addresses("Cc"),
        "bcc_address": _addresses("Bcc"),
        "reply_to": _addresses("Reply-To"),
        "subject": _header("Subject"),
        "message_id": _header("Message-ID"),
        "in_reply_to": _header("In-Reply-To"),
        "references": _header("References"),
        "list_id": _header("List-Id"),
        "list_unsubscribe": _header("List-Unsubscribe"),
        "is_seen": "\\SEEN" in flag_set,
        "is_flagged": "\\FLAGGED" in flag_set,
        "is_answered": "\\ANSWERED" in flag_set,
        "is_draft": "\\DRAFT" in flag_set,
        "is_deleted": "\\DELETED" in flag_set,
        "flags": ",".join(sorted(flag_set)) if flag_set else None,
    }


def _parse_imap_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d-%b-%Y %H:%M:%S %z")
    except ValueError:
        return None


def _parse_rfc2822_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
