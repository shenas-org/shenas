"""Tests for Google Takeout parsers."""

import email.message
import json
import mailbox
from pathlib import Path

import pytest

from shenas_sources.gtakeout.parsers.chrome import parse_browser_history
from shenas_sources.gtakeout.parsers.fit import (
    _extract_aggregates,
    _safe_float,
    _safe_int,
    parse_activity_sessions,
    parse_daily_metrics,
)
from shenas_sources.gtakeout.parsers.location import parse_location_records, parse_semantic_locations
from shenas_sources.gtakeout.parsers.mail import _decode_header, _has_attachments, _parse_date, parse_mbox
from shenas_sources.gtakeout.parsers.photos import parse_photos_metadata
from shenas_sources.gtakeout.parsers.youtube import parse_search_history, parse_subscriptions, parse_watch_history


@pytest.fixture
def tmp(tmp_path: Path) -> Path:
    return tmp_path


class TestPhotosParser:
    def test_parses_photo_metadata(self, tmp: Path) -> None:
        f = tmp / "IMG_001.jpg.json"
        f.write_text(
            json.dumps(
                {
                    "title": "IMG_001.jpg",
                    "description": "A sunset",
                    "photoTakenTime": {"timestamp": "1711641600", "formatted": "Mar 28, 2024"},
                    "creationTime": {"timestamp": "1711641600", "formatted": "Mar 28, 2024"},
                    "geoData": {"latitude": 59.33, "longitude": 18.07, "altitude": 28.0},
                    "geoDataExif": {"latitude": 59.33, "longitude": 18.07},
                }
            )
        )

        result = list(parse_photos_metadata([f]))
        assert len(result) == 1
        assert result[0]["title"] == "IMG_001.jpg"
        assert result[0]["latitude"] == 59.33
        assert result[0]["photo_taken_timestamp"] == "1711641600"

    def test_skips_album_metadata(self, tmp: Path) -> None:
        f = tmp / "metadata.json"
        f.write_text(json.dumps({"title": "Album", "description": ""}))
        assert list(parse_photos_metadata([f])) == []

    def test_skips_non_photo_json(self, tmp: Path) -> None:
        f = tmp / "random.json"
        f.write_text(json.dumps({"unrelated": True}))
        assert list(parse_photos_metadata([f])) == []


class TestLocationParser:
    def test_parses_records(self, tmp: Path) -> None:
        f = tmp / "Records.json"
        f.write_text(
            json.dumps(
                {
                    "locations": [
                        {
                            "timestamp": "2024-03-28T10:00:00Z",
                            "latitudeE7": 593300000,
                            "longitudeE7": 180700000,
                            "accuracy": 20,
                        }
                    ]
                }
            )
        )

        result = list(parse_location_records([f]))
        assert len(result) == 1
        assert abs(result[0]["latitude"] - 59.33) < 0.001
        assert abs(result[0]["longitude"] - 18.07) < 0.001

    def test_parses_semantic_visits(self, tmp: Path) -> None:
        f = tmp / "2024_MARCH.json"
        f.write_text(
            json.dumps(
                {
                    "timelineObjects": [
                        {
                            "placeVisit": {
                                "location": {"name": "Office", "latitudeE7": 593300000, "longitudeE7": 180700000},
                                "duration": {"startTimestamp": "2024-03-28T08:00:00Z", "endTimestamp": "2024-03-28T17:00:00Z"},
                                "placeConfidence": "HIGH",
                            }
                        }
                    ]
                }
            )
        )

        result = list(parse_semantic_locations([f]))
        assert len(result) == 1
        assert result[0]["type"] == "visit"
        assert result[0]["place_name"] == "Office"


class TestYouTubeParser:
    def test_parses_watch_history(self, tmp: Path) -> None:
        f = tmp / "watch-history.json"
        f.write_text(
            json.dumps(
                [
                    {
                        "title": "Watched a video",
                        "titleUrl": "https://youtube.com/watch?v=abc",
                        "time": "2024-03-28T12:00:00Z",
                        "subtitles": [{"name": "Channel Name", "url": "https://youtube.com/channel/xyz"}],
                        "header": "YouTube",
                    }
                ]
            )
        )

        result = list(parse_watch_history([f]))
        assert len(result) == 1
        assert result[0]["title"] == "Watched a video"
        assert result[0]["channel_name"] == "Channel Name"

    def test_parses_search_history(self, tmp: Path) -> None:
        f = tmp / "search-history.json"
        f.write_text(
            json.dumps(
                [
                    {
                        "title": "Searched for python",
                        "titleUrl": "https://youtube.com/results?q=python",
                        "time": "2024-03-28T10:00:00Z",
                    }
                ]
            )
        )

        result = list(parse_search_history([f]))
        assert len(result) == 1
        assert "python" in result[0]["title"]

    def test_parses_subscriptions(self, tmp: Path) -> None:
        f = tmp / "subscriptions.csv"
        f.write_text("Channel Id,Channel Url,Channel Title\nUC123,https://youtube.com/c/test,Test Channel\n")

        result = list(parse_subscriptions([f]))
        assert len(result) == 1
        assert result[0]["channel_id"] == "UC123"
        assert result[0]["channel_title"] == "Test Channel"


class TestChromeParser:
    def test_parses_browser_history(self, tmp: Path) -> None:
        f = tmp / "History.json"
        f.write_text(
            json.dumps(
                {
                    "Browser History": [
                        {
                            "url": "https://example.com",
                            "title": "Example",
                            "time_usec": 1711641600000000,
                            "favicon_url": "https://example.com/favicon.ico",
                            "page_transition": "LINK",
                            "client_id": "abc123",
                        }
                    ]
                }
            )
        )

        result = list(parse_browser_history([f]))
        assert len(result) == 1
        assert result[0]["url"] == "https://example.com"
        assert result[0]["title"] == "Example"
        assert "2024-03-28" in result[0]["timestamp"]
        assert result[0]["client_id"] == "abc123"

    def test_skips_entries_without_url(self, tmp: Path) -> None:
        f = tmp / "History.json"
        f.write_text(json.dumps({"Browser History": [{"title": "No URL", "time_usec": 1711641600000000}]}))

        assert list(parse_browser_history([f])) == []

    def test_skips_non_history_files(self, tmp: Path) -> None:
        f = tmp / "Bookmarks.json"
        f.write_text(json.dumps({"bookmarks": []}))
        assert list(parse_browser_history([f])) == []

    def test_skips_invalid_timestamps(self, tmp: Path) -> None:
        f = tmp / "History.json"
        f.write_text(
            json.dumps(
                {
                    "Browser History": [
                        {"url": "https://example.com", "title": "Bad time", "time_usec": -99999999999999999999},
                    ]
                }
            )
        )
        assert list(parse_browser_history([f])) == []

    def test_multiple_entries(self, tmp: Path) -> None:
        f = tmp / "History.json"
        entries = [
            {"url": f"https://example.com/{i}", "title": f"Page {i}", "time_usec": 1711641600000000 + i * 1000000}
            for i in range(5)
        ]
        f.write_text(json.dumps({"Browser History": entries}))

        result = list(parse_browser_history([f]))
        assert len(result) == 5


class TestFitHelpers:
    def test_safe_float_valid(self) -> None:
        assert _safe_float("3.14") == 3.14

    def test_safe_float_empty(self) -> None:
        assert _safe_float("") is None
        assert _safe_float("   ") is None

    def test_safe_float_invalid(self) -> None:
        assert _safe_float("abc") is None

    def test_safe_int_valid(self) -> None:
        assert _safe_int("42") == 42

    def test_safe_int_from_float(self) -> None:
        assert _safe_int("3.7") == 3

    def test_safe_int_empty(self) -> None:
        assert _safe_int("") is None

    def test_safe_int_invalid(self) -> None:
        assert _safe_int("abc") is None

    def test_extract_aggregates(self) -> None:
        aggregates = [
            {"metricName": "com.google.calories.expended", "floatValue": 123.456},
            {"metricName": "com.google.step_count.delta", "intValue": 5000},
            {"metricName": "com.google.distance.delta", "floatValue": 3200.789},
            {"metricName": "com.google.speed.summary", "floatValue": 1.234},
        ]
        result = _extract_aggregates(aggregates)
        assert result["calories_kcal"] == 123.5
        assert result["step_count"] == 5000
        assert result["distance_m"] == 3200.8
        assert result["avg_speed_ms"] == 1.2

    def test_extract_aggregates_empty(self) -> None:
        result = _extract_aggregates([])
        assert result["calories_kcal"] is None
        assert result["step_count"] is None

    def test_extract_aggregates_unknown_metrics(self) -> None:
        result = _extract_aggregates([{"metricName": "com.google.unknown", "floatValue": 99.0}])
        assert result["calories_kcal"] is None


class TestFitDailyMetrics:
    def test_parses_daily_csv(self, tmp: Path) -> None:
        f = tmp / "2024-10-09.csv"
        header = "Start time,End time,Calories (kcal),Distance (m),Step count,Move Minutes count"
        row = "08:00:00.000+02:00,08:15:00.000+02:00,33.3,80.6,142,3"
        f.write_text(f"{header}\n{row}\n")

        result = list(parse_daily_metrics([f]))
        assert len(result) == 1
        assert result[0]["date"] == "2024-10-09"
        assert result[0]["start_time"] == "2024-10-09T08:00:00.000+02:00"
        assert result[0]["calories_kcal"] == 33.3
        assert result[0]["step_count"] == 142
        assert result[0]["move_minutes"] == 3

    def test_skips_empty_rows(self, tmp: Path) -> None:
        f = tmp / "2024-01-01.csv"
        header = "Start time,End time,Calories (kcal),Distance (m),Step count"
        row = "00:00:00.000+01:00,00:15:00.000+01:00,,,"
        f.write_text(f"{header}\n{row}\n")

        assert list(parse_daily_metrics([f])) == []

    def test_skips_files_without_date_name(self, tmp: Path) -> None:
        f = tmp / "summary.csv"
        f.write_text("Start time,Calories (kcal)\n08:00,100\n")
        assert list(parse_daily_metrics([f])) == []

    def test_skips_non_csv(self, tmp: Path) -> None:
        f = tmp / "2024-01-01.json"
        f.write_text("{}")
        assert list(parse_daily_metrics([f])) == []

    def test_multiple_intervals(self, tmp: Path) -> None:
        f = tmp / "2024-03-15.csv"
        header = "Start time,End time,Calories (kcal),Step count"
        rows = [
            "08:00:00.000+01:00,08:15:00.000+01:00,30.0,100",
            "08:15:00.000+01:00,08:30:00.000+01:00,25.0,80",
            "08:30:00.000+01:00,08:45:00.000+01:00,,,",
        ]
        f.write_text(f"{header}\n" + "\n".join(rows) + "\n")

        result = list(parse_daily_metrics([f]))
        assert len(result) == 2


class TestFitActivitySessions:
    def test_parses_running_session(self, tmp: Path) -> None:
        f = tmp / "2024-03-28T08_00_00Z_RUNNING.json"
        f.write_text(
            json.dumps(
                {
                    "fitnessActivity": "running",
                    "startTime": "2024-03-28T08:00:00Z",
                    "endTime": "2024-03-28T08:35:00Z",
                    "duration": "2100s",
                    "aggregate": [
                        {"metricName": "com.google.calories.expended", "floatValue": 350.0},
                        {"metricName": "com.google.step_count.delta", "intValue": 4200},
                        {"metricName": "com.google.distance.delta", "floatValue": 5000.0},
                    ],
                }
            )
        )

        result = list(parse_activity_sessions([f]))
        assert len(result) == 1
        assert result[0]["activity"] == "running"
        assert result[0]["duration_s"] == 2100
        assert result[0]["calories_kcal"] == 350.0
        assert result[0]["step_count"] == 4200
        assert result[0]["distance_m"] == 5000.0

    def test_skips_session_without_start_time(self, tmp: Path) -> None:
        f = tmp / "bad_session.json"
        f.write_text(json.dumps({"fitnessActivity": "walking", "duration": "600s"}))
        assert list(parse_activity_sessions([f])) == []

    def test_handles_missing_duration(self, tmp: Path) -> None:
        f = tmp / "no_duration.json"
        f.write_text(
            json.dumps({"fitnessActivity": "walking", "startTime": "2024-01-01T10:00:00Z", "endTime": "2024-01-01T10:30:00Z"})
        )

        result = list(parse_activity_sessions([f]))
        assert len(result) == 1
        assert result[0]["duration_s"] is None

    def test_skips_non_json(self, tmp: Path) -> None:
        f = tmp / "activity.tcx"
        f.write_text("<xml/>")
        assert list(parse_activity_sessions([f])) == []

    def test_handles_no_aggregates(self, tmp: Path) -> None:
        f = tmp / "simple.json"
        f.write_text(json.dumps({"fitnessActivity": "yoga", "startTime": "2024-01-01T06:00:00Z", "duration": "3600s"}))

        result = list(parse_activity_sessions([f]))
        assert len(result) == 1
        assert result[0]["calories_kcal"] is None
        assert result[0]["step_count"] is None


class TestMailHelpers:
    def test_parse_date_valid(self) -> None:
        result = _parse_date("Thu, 28 Mar 2024 12:00:00 +0000")
        assert result is not None
        assert "2024-03-28" in result

    def test_parse_date_empty(self) -> None:
        assert _parse_date("") is None

    def test_parse_date_invalid(self) -> None:
        assert _parse_date("not a date") is None

    def test_decode_header_plain(self) -> None:
        assert _decode_header("Hello World") == "Hello World"

    def test_decode_header_empty(self) -> None:
        assert _decode_header("") == ""

    def test_decode_header_encoded(self) -> None:
        result = _decode_header("=?utf-8?B?SGVsbG8=?=")
        assert result == "Hello"

    def test_has_attachments_simple(self) -> None:
        msg = mailbox.mboxMessage()
        msg["Subject"] = "Test"
        msg.set_payload("Hello")
        assert _has_attachments(msg) is False

    def test_has_attachments_with_attachment(self) -> None:
        msg = mailbox.mboxMessage()
        msg["Subject"] = "Test"
        msg["MIME-Version"] = "1.0"
        msg["Content-Type"] = "multipart/mixed; boundary=boundary123"
        msg.set_payload(None)  # ty: ignore[invalid-argument-type]
        text_part = email.message.Message()
        text_part["Content-Type"] = "text/plain"
        text_part.set_payload("Hello")
        attachment = email.message.Message()
        attachment["Content-Type"] = "application/octet-stream"
        attachment["Content-Disposition"] = 'attachment; filename="test.txt"'
        attachment.set_payload("data")
        msg.attach(text_part)
        msg.attach(attachment)
        assert _has_attachments(msg) is True


class TestMboxParser:
    def _write_mbox(self, path: Path, messages: list[dict[str, str]]) -> None:
        """Write a minimal mbox file with the given messages."""
        mbox = mailbox.mbox(str(path))
        for msg_data in messages:
            msg = mailbox.mboxMessage()
            for header, value in msg_data.items():
                if header == "body":
                    msg.set_payload(value)
                else:
                    msg[header] = value
            if "body" not in msg_data:
                msg.set_payload("Test body")
            mbox.add(msg)
        mbox.flush()
        mbox.close()

    def test_parses_basic_message(self, tmp: Path) -> None:
        f = tmp / "mail.mbox"
        self._write_mbox(
            f,
            [
                {
                    "Message-ID": "<test@example.com>",
                    "Date": "Thu, 28 Mar 2024 12:00:00 +0000",
                    "From": "sender@example.com",
                    "To": "recipient@example.com",
                    "Subject": "Test Subject",
                    "X-Gmail-Labels": "Inbox,Unread",
                    "X-GM-THRID": "12345",
                }
            ],
        )

        result = list(parse_mbox([f]))
        assert len(result) == 1
        assert result[0]["message_id"] == "test@example.com"
        assert result[0]["from_addr"] == "sender@example.com"
        assert result[0]["to_addr"] == "recipient@example.com"
        assert result[0]["subject"] == "Test Subject"
        assert result[0]["labels"] == "Inbox,Unread"
        assert result[0]["thread_id"] == "12345"

    def test_skips_messages_without_id(self, tmp: Path) -> None:
        f = tmp / "mail.mbox"
        self._write_mbox(f, [{"Date": "Thu, 28 Mar 2024 12:00:00 +0000", "From": "test@example.com"}])

        assert list(parse_mbox([f])) == []

    def test_skips_messages_without_date(self, tmp: Path) -> None:
        f = tmp / "mail.mbox"
        self._write_mbox(f, [{"Message-ID": "<test@example.com>", "From": "test@example.com"}])

        assert list(parse_mbox([f])) == []

    def test_skips_non_mbox_files(self, tmp: Path) -> None:
        f = tmp / "mail.txt"
        f.write_text("not an mbox")
        assert list(parse_mbox([f])) == []

    def test_multiple_messages(self, tmp: Path) -> None:
        f = tmp / "mail.mbox"
        messages = [
            {
                "Message-ID": f"<msg{i}@example.com>",
                "Date": f"Thu, {28 - i} Mar 2024 12:00:00 +0000",
                "From": "sender@example.com",
                "Subject": f"Message {i}",
            }
            for i in range(3)
        ]
        self._write_mbox(f, messages)

        result = list(parse_mbox([f]))
        assert len(result) == 3

    def test_strips_angle_brackets_from_message_id(self, tmp: Path) -> None:
        f = tmp / "mail.mbox"
        self._write_mbox(
            f,
            [{"Message-ID": "<brackets@example.com>", "Date": "Thu, 28 Mar 2024 12:00:00 +0000", "From": "a@b.com"}],
        )

        result = list(parse_mbox([f]))
        assert result[0]["message_id"] == "brackets@example.com"
