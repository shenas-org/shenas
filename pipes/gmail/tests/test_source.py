from shenas_pipes.gmail.source import _epoch_ms_to_iso, _get_header


class TestEpochMsToIso:
    def test_converts(self) -> None:
        assert _epoch_ms_to_iso(1711584000000) == "2024-03-28T00:00:00+00:00"

    def test_zero(self) -> None:
        assert _epoch_ms_to_iso(0) == "1970-01-01T00:00:00+00:00"


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
