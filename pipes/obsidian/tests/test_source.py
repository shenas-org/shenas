from pathlib import Path

from shenas_pipes.obsidian.source import _date_from_filename, _parse_frontmatter, daily_notes


class TestParseFrontmatter:
    def test_valid(self) -> None:
        text = "---\nmood: good\nenergy: 8\n---\n\nSome content."
        result = _parse_frontmatter(text)
        assert result == {"mood": "good", "energy": 8}

    def test_no_frontmatter(self) -> None:
        assert _parse_frontmatter("Just some text.") is None

    def test_empty_frontmatter(self) -> None:
        result = _parse_frontmatter("---\n---\nContent.")
        assert result is None  # yaml.safe_load returns None for empty

    def test_nested_values(self) -> None:
        text = "---\nmood: great\ntags:\n  - fitness\n  - journal\n---\n"
        result = _parse_frontmatter(text)
        assert result is not None
        assert result["tags"] == ["fitness", "journal"]

    def test_invalid_yaml(self) -> None:
        text = "---\n: bad: yaml: here\n---\n"
        assert _parse_frontmatter(text) is None


class TestDateFromFilename:
    def test_standard(self) -> None:
        assert _date_from_filename(Path("2026-03-15.md")) == "2026-03-15"

    def test_with_suffix(self) -> None:
        assert _date_from_filename(Path("2026-03-15 Monday.md")) == "2026-03-15"

    def test_no_date(self) -> None:
        assert _date_from_filename(Path("random-note.md")) is None


class TestDailyNotes:
    def test_reads_frontmatter(self, tmp_path: Path) -> None:
        (tmp_path / "2026-03-15.md").write_text("---\nmood: good\nenergy: 8\n---\nContent.")
        (tmp_path / "2026-03-16.md").write_text("---\nmood: ok\nenergy: 5\n---\nMore content.")

        rows = list(daily_notes(str(tmp_path)))
        assert len(rows) == 2
        assert rows[0]["date"] == "2026-03-15"
        assert rows[0]["mood"] == "good"
        assert rows[0]["energy"] == 8
        assert rows[1]["date"] == "2026-03-16"

    def test_skips_no_frontmatter(self, tmp_path: Path) -> None:
        (tmp_path / "2026-03-15.md").write_text("No frontmatter here.")
        rows = list(daily_notes(str(tmp_path)))
        assert len(rows) == 0

    def test_skips_non_date_files(self, tmp_path: Path) -> None:
        (tmp_path / "random-note.md").write_text("---\nmood: good\n---\n")
        rows = list(daily_notes(str(tmp_path)))
        assert len(rows) == 0

    def test_lists_joined(self, tmp_path: Path) -> None:
        (tmp_path / "2026-03-15.md").write_text("---\ntags:\n  - a\n  - b\n---\n")
        rows = list(daily_notes(str(tmp_path)))
        assert rows[0]["tags"] == "a, b"

    def test_nonexistent_dir(self) -> None:
        rows = list(daily_notes("/nonexistent/path"))
        assert len(rows) == 0

    def test_empty_dir(self, tmp_path: Path) -> None:
        rows = list(daily_notes(str(tmp_path)))
        assert len(rows) == 0
