from shenas_sources.gmail.resources import _get_header


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
