from pathlib import Path

from shenas_sources.core.table import AggregateTable, EventTable
from shenas_sources.obsidian.tables import (
    DailyNotes,
    Habits,
    _date_from_filename,
)

_parse_frontmatter = DailyNotes._parse_frontmatter
_parse_habit_line = Habits._parse_habit_line
_extract_habits = Habits._extract_habits

# A representative diary chunk based on the user's real template.
_REAL_DIARY = """\
---
mood: 7
---

# Plan for the day
- [ ] Brilliant [scheduled:: 2026-04-03]
- [x] Duolingo  [scheduled:: 2026-04-03]  [completion:: 2026-04-03]
- [ ] Consume culture [scheduled:: 2026-04-03]
- [ ] Learn science [scheduled:: 2026-04-03]
- [ ] Learn technology [scheduled:: 2026-04-03]
- [ ] Workout [scheduled:: 2026-04-03]
- [ ] [Shoulder mobility](https://youtu.be/35lIPoZdJNs) [scheduled:: 2026-04-03]
- [ ] Shower [scheduled:: 2026-04-03]
- [ ] Break [scheduled:: 2026-04-03]
---
- 7:30 - 8:30 Morning Routine
    - [x] Toothbrush  [scheduled:: 2026-04-03]  [completion:: 2026-04-03]
    - [ ] Clean face [scheduled:: 2026-04-03]
- 9:00 - 16:00 IKEA Day
"""


class TestParseFrontmatter:
    def test_valid(self) -> None:
        text = "---\nmood: good\nenergy: 8\n---\n\nSome content."
        result = _parse_frontmatter(text)
        assert result == {"mood": "good", "energy": 8}

    def test_no_frontmatter(self) -> None:
        assert _parse_frontmatter("Just some text.") is None

    def test_empty_frontmatter(self) -> None:
        result = _parse_frontmatter("---\n---\nContent.")
        assert result is None

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


class TestDailyNotesExtract:
    def test_reads_frontmatter(self, tmp_path: Path) -> None:
        (tmp_path / "2026-03-15.md").write_text("---\nmood: good\nenergy: 8\n---\nContent.")
        (tmp_path / "2026-03-16.md").write_text("---\nmood: ok\nenergy: 5\n---\nMore content.")

        rows = list(DailyNotes.extract(str(tmp_path)))
        assert len(rows) == 2
        assert rows[0]["date"] == "2026-03-15"
        assert rows[0]["mood"] == "good"
        assert rows[0]["energy"] == 8
        assert rows[1]["date"] == "2026-03-16"

    def test_skips_no_frontmatter(self, tmp_path: Path) -> None:
        (tmp_path / "2026-03-15.md").write_text("No frontmatter here.")
        assert list(DailyNotes.extract(str(tmp_path))) == []

    def test_skips_non_date_files(self, tmp_path: Path) -> None:
        (tmp_path / "random-note.md").write_text("---\nmood: good\n---\n")
        assert list(DailyNotes.extract(str(tmp_path))) == []

    def test_lists_joined(self, tmp_path: Path) -> None:
        (tmp_path / "2026-03-15.md").write_text("---\ntags:\n  - a\n  - b\n---\n")
        rows = list(DailyNotes.extract(str(tmp_path)))
        assert rows[0]["tags"] == "a, b"

    def test_nonexistent_dir(self) -> None:
        assert list(DailyNotes.extract("/nonexistent/path")) == []

    def test_empty_dir(self, tmp_path: Path) -> None:
        assert list(DailyNotes.extract(str(tmp_path))) == []


class TestParseHabitLine:
    def test_unchecked(self) -> None:
        row = _parse_habit_line("- [ ] Brilliant [scheduled:: 2026-04-03]", "2026-04-03")
        assert row is not None
        assert row["habit_name"] == "Brilliant"
        assert row["completed"] is False
        assert row["scheduled"] == "2026-04-03"
        assert row["completion"] is None
        assert row["url"] is None

    def test_checked_with_completion(self) -> None:
        row = _parse_habit_line(
            "- [x] Duolingo  [scheduled:: 2026-04-03]  [completion:: 2026-04-03]",
            "2026-04-03",
        )
        assert row is not None
        assert row["completed"] is True
        assert row["completion"] == "2026-04-03"
        assert row["habit_name"] == "Duolingo"

    def test_strips_markdown_link_keeps_url(self) -> None:
        row = _parse_habit_line(
            "- [ ] [Shoulder mobility](https://youtu.be/abc) [scheduled:: 2026-04-03]",
            "2026-04-03",
        )
        assert row is not None
        assert row["habit_name"] == "Shoulder mobility"
        assert row["url"] == "https://youtu.be/abc"

    def test_skips_indented_lines(self) -> None:
        assert _parse_habit_line("    - [x] Toothbrush [scheduled:: 2026-04-03]", "2026-04-03") is None
        assert _parse_habit_line("\t- [ ] Anything", "2026-04-03") is None

    def test_skips_non_checkbox_bullets(self) -> None:
        assert _parse_habit_line("- 7:30 - 8:30 Morning Routine", "2026-04-03") is None

    def test_skips_non_dash_lines(self) -> None:
        assert _parse_habit_line("```tasks", "2026-04-03") is None
        assert _parse_habit_line("# Heading", "2026-04-03") is None

    def test_capital_x_is_checked(self) -> None:
        row = _parse_habit_line("- [X] Done thing", "2026-04-03")
        assert row is not None
        assert row["completed"] is True


class TestExtractHabitsFromRealDiary:
    def test_extracts_only_top_level_under_plan_for_the_day(self) -> None:
        rows = list(_extract_habits(_REAL_DIARY, "2026-04-03", "Plan for the day"))
        names = [r["habit_name"] for r in rows]
        assert names == [
            "Brilliant",
            "Duolingo",
            "Consume culture",
            "Learn science",
            "Learn technology",
            "Workout",
            "Shoulder mobility",
            "Shower",
            "Break",
        ]
        assert "Toothbrush" not in names
        assert "Clean face" not in names

    def test_completion_state(self) -> None:
        rows = list(_extract_habits(_REAL_DIARY, "2026-04-03", "Plan for the day"))
        by_name = {r["habit_name"]: r for r in rows}
        assert by_name["Duolingo"]["completed"] is True
        assert by_name["Duolingo"]["completion"] == "2026-04-03"
        assert by_name["Brilliant"]["completed"] is False
        assert by_name["Brilliant"]["completion"] is None

    def test_url_extracted_from_link(self) -> None:
        rows = list(_extract_habits(_REAL_DIARY, "2026-04-03", "Plan for the day"))
        by_name = {r["habit_name"]: r for r in rows}
        assert by_name["Shoulder mobility"]["url"] == "https://youtu.be/35lIPoZdJNs"

    def test_section_ends_at_horizontal_rule(self) -> None:
        rows = list(_extract_habits(_REAL_DIARY, "2026-04-03", "Plan for the day"))
        assert len(rows) == 9

    def test_section_ends_at_next_heading(self) -> None:
        text = "# Plan for the day\n- [ ] One\n# Other heading\n- [ ] Two\n"
        rows = list(_extract_habits(text, "2026-04-03", "Plan for the day"))
        assert [r["habit_name"] for r in rows] == ["One"]

    def test_no_matching_heading_yields_nothing(self) -> None:
        text = "# Some other section\n- [ ] Nope\n"
        assert list(_extract_habits(text, "2026-04-03", "Plan for the day")) == []

    def test_heading_match_is_case_insensitive(self) -> None:
        text = "# PLAN FOR THE DAY\n- [ ] Yes\n"
        rows = list(_extract_habits(text, "2026-04-03", "Plan for the day"))
        assert len(rows) == 1

    def test_h2_heading_also_works(self) -> None:
        text = "## Plan for the day\n- [ ] Yes\n"
        rows = list(_extract_habits(text, "2026-04-03", "Plan for the day"))
        assert len(rows) == 1

    def test_configurable_heading(self) -> None:
        text = "# Daily Habits\n- [ ] Hydrate\n- [x] Vitamins\n"
        rows = list(_extract_habits(text, "2026-04-03", "Daily Habits"))
        assert {r["habit_name"] for r in rows} == {"Hydrate", "Vitamins"}


class TestHabitsExtract:
    def test_yields_one_row_per_checkbox_per_day(self, tmp_path: Path) -> None:
        (tmp_path / "2026-04-03.md").write_text(_REAL_DIARY)
        (tmp_path / "2026-04-04.md").write_text(_REAL_DIARY.replace("2026-04-03", "2026-04-04"))

        rows = list(Habits.extract(str(tmp_path)))
        assert len(rows) == 18
        dates = {r["date"] for r in rows}
        assert dates == {"2026-04-03", "2026-04-04"}

    def test_skips_files_without_date(self, tmp_path: Path) -> None:
        (tmp_path / "random.md").write_text(_REAL_DIARY)
        assert list(Habits.extract(str(tmp_path))) == []

    def test_nonexistent_dir(self) -> None:
        assert list(Habits.extract("/nonexistent/path")) == []

    def test_custom_heading(self, tmp_path: Path) -> None:
        (tmp_path / "2026-04-03.md").write_text("# Daily Habits\n- [x] Read\n- [ ] Sleep early\n")
        rows = list(Habits.extract(str(tmp_path), heading="Daily Habits"))
        assert {r["habit_name"] for r in rows} == {"Read", "Sleep early"}


class TestKindsAndDispositions:
    def test_daily_notes_is_aggregate(self) -> None:
        assert issubclass(DailyNotes, AggregateTable)
        assert DailyNotes._Meta.time_at == "date"

    def test_habits_is_event(self) -> None:
        assert issubclass(Habits, EventTable)
        assert Habits._Meta.time_at == "date"
