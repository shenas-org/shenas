from unittest.mock import MagicMock

from shenas_sources.core.table import DimensionTable, EventTable, SnapshotTable
from shenas_sources.gmail.tables import (
    Filters,
    Labels,
    Messages,
    Profile,
    SendAs,
    Vacation,
    _get_header,
    _parse_message,
)


class TestGetHeader:
    def test_found(self) -> None:
        headers = [{"name": "From", "value": "user@example.com"}, {"name": "Subject", "value": "Hello"}]
        assert _get_header(headers, "From") == "user@example.com"
        assert _get_header(headers, "Subject") == "Hello"

    def test_case_insensitive(self) -> None:
        headers = [{"name": "from", "value": "user@example.com"}]
        assert _get_header(headers, "From") == "user@example.com"

    def test_not_found(self) -> None:
        headers = [{"name": "From", "value": "user@example.com"}]
        assert _get_header(headers, "To") == ""

    def test_empty_headers(self) -> None:
        assert _get_header([], "From") == ""


def _msg(headers: list[dict[str, str]] | None = None, label_ids: list[str] | None = None) -> dict[str, object]:
    return {
        "id": "m1",
        "threadId": "t1",
        "internalDate": "1700000000000",
        "snippet": "hi",
        "sizeEstimate": 1234,
        "labelIds": label_ids or [],
        "payload": {"headers": headers or []},
    }


class TestParseMessage:
    def test_extracts_extended_headers(self) -> None:
        row = _parse_message(
            _msg(
                headers=[
                    {"name": "From", "value": "alice@example.com"},
                    {"name": "To", "value": "bob@example.com"},
                    {"name": "Cc", "value": "carol@example.com"},
                    {"name": "Bcc", "value": "dan@example.com"},
                    {"name": "Reply-To", "value": "replies@example.com"},
                    {"name": "Subject", "value": "Hello"},
                    {"name": "Message-ID", "value": "<smtp-id@example.com>"},
                    {"name": "In-Reply-To", "value": "<prev@example.com>"},
                    {"name": "References", "value": "<ref1@example.com> <ref2@example.com>"},
                    {"name": "List-Id", "value": "<my.list.example.com>"},
                    {"name": "List-Unsubscribe", "value": "<https://unsub.example.com>"},
                ]
            )
        )
        assert row["cc_address"] == "carol@example.com"
        assert row["bcc_address"] == "dan@example.com"
        assert row["reply_to"] == "replies@example.com"
        assert row["message_id_header"] == "<smtp-id@example.com>"
        assert row["in_reply_to"] == "<prev@example.com>"
        assert row["references"] == "<ref1@example.com> <ref2@example.com>"
        assert row["list_id"] == "<my.list.example.com>"
        assert row["list_unsubscribe"] == "<https://unsub.example.com>"

    def test_state_flags_from_labels(self) -> None:
        row = _parse_message(_msg(label_ids=["UNREAD", "STARRED", "INBOX", "IMPORTANT"]))
        assert row["is_read"] is False
        assert row["is_starred"] is True
        assert row["is_important"] is True
        assert row["is_inbox"] is True
        assert row["is_sent"] is False

    def test_read_flag_when_unread_label_absent(self) -> None:
        row = _parse_message(_msg(label_ids=["INBOX"]))
        assert row["is_read"] is True

    def test_category_extracted(self) -> None:
        row = _parse_message(_msg(label_ids=["INBOX", "CATEGORY_PROMOTIONS"]))
        assert row["category"] == "PROMOTIONS"

    def test_no_category(self) -> None:
        row = _parse_message(_msg(label_ids=["INBOX"]))
        assert row["category"] is None


class TestLabelsExtract:
    def test_yields_labels(self) -> None:
        service = MagicMock()
        service.users().labels().list().execute.return_value = {
            "labels": [
                {"id": "Label_1", "name": "Work", "type": "user"},
                {"id": "INBOX", "name": "INBOX", "type": "system"},
            ]
        }
        rows = list(Labels.extract(service))
        assert len(rows) == 2
        assert rows[0]["label_name"] == "Work"
        assert rows[1]["type"] == "system"


class TestProfileExtract:
    def test_yields_profile(self) -> None:
        service = MagicMock()
        service.users().getProfile().execute.return_value = {
            "emailAddress": "me@example.com",
            "messagesTotal": 12345,
            "threadsTotal": 6789,
            "historyId": "98765",
        }
        rows = list(Profile.extract(service))
        assert len(rows) == 1
        assert rows[0]["email_address"] == "me@example.com"
        assert rows[0]["messages_total"] == 12345


class TestFiltersExtract:
    def test_yields_filters(self) -> None:
        service = MagicMock()
        service.users().settings().filters().list().execute.return_value = {
            "filter": [
                {
                    "id": "f1",
                    "criteria": {"from": "noreply@example.com", "subject": "promo"},
                    "action": {"addLabelIds": ["Label_1", "Label_2"], "removeLabelIds": ["INBOX"]},
                },
                {
                    "id": "f2",
                    "criteria": {"query": "older_than:1y"},
                    "action": {"forward": "archive@example.com"},
                },
            ]
        }
        rows = list(Filters.extract(service))
        assert len(rows) == 2
        assert rows[0]["from_criteria"] == "noreply@example.com"
        assert rows[0]["add_label_ids"] == "Label_1, Label_2"
        assert rows[0]["remove_label_ids"] == "INBOX"
        assert rows[1]["query_criteria"] == "older_than:1y"
        assert rows[1]["forward_to"] == "archive@example.com"

    def test_handles_failure(self) -> None:
        service = MagicMock()
        service.users().settings().filters().list().execute.side_effect = RuntimeError("scope")
        assert list(Filters.extract(service)) == []


class TestVacationExtract:
    def test_yields_vacation(self) -> None:
        service = MagicMock()
        service.users().settings().getVacation().execute.return_value = {
            "enableAutoReply": True,
            "responseSubject": "Out",
            "responseBodyPlainText": "Back next week",
            "restrictToContacts": False,
            "restrictToDomain": True,
            "startTime": "1700000000000",
            "endTime": "1700604800000",
        }
        rows = list(Vacation.extract(service))
        assert len(rows) == 1
        row = rows[0]
        assert row["enabled"] is True
        assert row["response_subject"] == "Out"
        assert row["restrict_to_domain"] is True
        assert row["start_time"] == 1700000000000
        assert row["end_time"] == 1700604800000


class TestSendAsExtract:
    def test_yields_identities(self) -> None:
        service = MagicMock()
        service.users().settings().sendAs().list().execute.return_value = {
            "sendAs": [
                {
                    "sendAsEmail": "me@example.com",
                    "displayName": "Me",
                    "isDefault": True,
                    "isPrimary": True,
                    "verificationStatus": "accepted",
                },
                {"sendAsEmail": "alt@example.com", "displayName": "Alt", "treatAsAlias": True},
            ]
        }
        rows = list(SendAs.extract(service))
        assert len(rows) == 2
        primary = next(r for r in rows if r["send_as_email"] == "me@example.com")
        assert primary["is_default"] is True
        assert primary["is_primary"] is True
        assert primary["display_name_"] == "Me"
        alt = next(r for r in rows if r["send_as_email"] == "alt@example.com")
        assert alt["treat_as_alias"] is True


class TestKindsAndDispositions:
    def test_messages_is_event(self) -> None:
        assert issubclass(Messages, EventTable)
        assert Messages._Meta.time_at == "internal_date"
        assert Messages.cursor_column == "internal_date"
        assert Messages.write_disposition() == "merge"

    def test_labels_is_dimension_scd2(self) -> None:
        assert issubclass(Labels, DimensionTable)
        assert Labels.write_disposition() == {"disposition": "merge", "strategy": "scd2"}

    def test_profile_is_snapshot_scd2(self) -> None:
        assert issubclass(Profile, SnapshotTable)
        assert Profile.write_disposition() == {"disposition": "merge", "strategy": "scd2"}
