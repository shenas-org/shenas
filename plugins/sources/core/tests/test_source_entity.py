# ruff: noqa: SIM117, RUF012
"""Tests for Source entity-related methods and _iso8601_recurring_to_minutes."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from shenas_sources.core.source import Source, _iso8601_recurring_to_minutes

# ---------------------------------------------------------------------------
# _iso8601_recurring_to_minutes (standalone function, no DB needed)
# ---------------------------------------------------------------------------


class TestIso8601RecurringToMinutes:
    def test_daily(self) -> None:
        assert _iso8601_recurring_to_minutes("R/P1D") == 1440

    def test_hourly(self) -> None:
        assert _iso8601_recurring_to_minutes("R/PT1H") == 60

    def test_two_weeks(self) -> None:
        assert _iso8601_recurring_to_minutes("R/P2W") == 20160

    def test_fifteen_minutes(self) -> None:
        assert _iso8601_recurring_to_minutes("R/PT15M") == 15

    def test_one_week(self) -> None:
        assert _iso8601_recurring_to_minutes("R/P1W") == 10080

    def test_combined_days_and_hours(self) -> None:
        # 1 day + 6 hours = 1440 + 360 = 1800
        assert _iso8601_recurring_to_minutes("R/P1DT6H") == 1800

    def test_seconds_truncated(self) -> None:
        # 90 seconds -> 1 minute (integer division)
        assert _iso8601_recurring_to_minutes("R/PT90S") == 1

    def test_seconds_less_than_minute(self) -> None:
        # 30 seconds -> 0 minutes -> None (zero means no meaningful interval)
        assert _iso8601_recurring_to_minutes("R/PT30S") is None

    def test_empty_string(self) -> None:
        assert _iso8601_recurring_to_minutes("") is None

    def test_invalid_pattern(self) -> None:
        assert _iso8601_recurring_to_minutes("every day") is None

    def test_missing_r_prefix(self) -> None:
        assert _iso8601_recurring_to_minutes("P1D") is None

    def test_bare_r_p(self) -> None:
        # "R/P" with no duration components -> None
        assert _iso8601_recurring_to_minutes("R/P") is None


# ---------------------------------------------------------------------------
# Fixtures and helpers for entity-related tests
# ---------------------------------------------------------------------------


class FakeSource(Source):
    """Minimal concrete Source subclass for testing."""

    name = "fakesrc"
    display_name = "Fake Source"
    entity_types: list[str] = ["human"]

    def resources(self, client):
        return []


class FakeSourceNoHuman(Source):
    """Source that does NOT declare human in entity_types."""

    name = "fakesrc_no_human"
    display_name = "Fake No Human"
    entity_types: list[str] = []

    def resources(self, client):
        return []


@dataclass
class FakeRow:
    city: str | None = "Berlin"
    language: str | None = "de"
    empty_field: str | None = None


@dataclass
class FakeEntity:
    uuid: str = "entity-uuid-1"
    type: str = "human"
    name: str = "Me"
    status: str = "enabled"

    def insert(self):
        pass

    def save(self):
        pass


# ---------------------------------------------------------------------------
# _source_entity_uuids
# ---------------------------------------------------------------------------


class TestSourceEntityUuids:
    def test_includes_me_entity_for_human_type(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"
        source.entity_types = ["human"]

        with patch.object(Source, "resolve_entity_uuids", return_value=["me-uuid-123"]):
            with patch("shenas_sources.core.source.Source._source_entity_uuids", Source._source_entity_uuids):
                # Patch Statement.distinct_values to return empty (no statement-linked entities)
                with patch("app.entities.statements.Statement") as mock_stmt:
                    mock_stmt.distinct_values.return_value = []
                    result = source._source_entity_uuids()

        assert "me-uuid-123" in result

    def test_includes_statement_linked_entities(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"
        source.entity_types = ["human"]

        fake_entity = FakeEntity(uuid="stmt-entity-1", status="enabled")

        with patch.object(Source, "resolve_entity_uuids", return_value=["me-uuid-123"]):
            with patch("app.entities.statements.Statement") as mock_stmt:
                mock_stmt.distinct_values.return_value = ["stmt-entity-1"]
                with patch("app.entity.Entity") as mock_entity_cls:
                    mock_entity_cls.find_by_uuid.return_value = fake_entity
                    result = source._source_entity_uuids()

        assert "me-uuid-123" in result
        assert "stmt-entity-1" in result

    def test_deduplicates_uuids(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"
        source.entity_types = ["human"]

        # Same UUID from both "me" and statements
        fake_entity = FakeEntity(uuid="me-uuid-123", status="enabled")

        with patch.object(Source, "resolve_entity_uuids", return_value=["me-uuid-123"]):
            with patch("app.entities.statements.Statement") as mock_stmt:
                mock_stmt.distinct_values.return_value = ["me-uuid-123"]
                with patch("app.entity.Entity") as mock_entity_cls:
                    mock_entity_cls.find_by_uuid.return_value = fake_entity
                    result = source._source_entity_uuids()

        assert result == ["me-uuid-123"]

    def test_no_human_type_skips_me(self) -> None:
        source = FakeSourceNoHuman.__new__(FakeSourceNoHuman)
        source.name = "fakesrc_no_human"
        source.entity_types = []

        with patch("app.entities.statements.Statement") as mock_stmt:
            mock_stmt.distinct_values.return_value = []
            result = source._source_entity_uuids()

        assert result == []

    def test_excludes_disabled_statement_entities(self) -> None:
        source = FakeSourceNoHuman.__new__(FakeSourceNoHuman)
        source.name = "fakesrc_no_human"
        source.entity_types = []

        disabled_entity = FakeEntity(uuid="disabled-1", status="disabled")

        with patch("app.entities.statements.Statement") as mock_stmt:
            mock_stmt.distinct_values.return_value = ["disabled-1"]
            with patch("app.entity.Entity") as mock_entity_cls:
                mock_entity_cls.find_by_uuid.return_value = disabled_entity
                result = source._source_entity_uuids()

        assert "disabled-1" not in result


# ---------------------------------------------------------------------------
# _upsert_entity_ref
# ---------------------------------------------------------------------------


class TestUpsertEntityRef:
    def test_creates_new_entity_when_not_found(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"

        row = FakeRow(city="Berlin")

        with patch("app.entity.Entity") as mock_entity_cls:
            with patch("app.entity.compute_entity_id", return_value="city-berlin-uuid"):
                mock_entity_cls.find_by_uuid.return_value = None
                mock_instance = MagicMock()
                mock_entity_cls.return_value = mock_instance
                with patch("app.entities.statements.Statement") as mock_stmt:
                    mock_stmt.find.return_value = None
                    mock_stmt.from_row.return_value = MagicMock()

                    source._upsert_entity_ref(row, "city", "city")

                mock_entity_cls.assert_called_once_with(
                    uuid="city-berlin-uuid",
                    type="city",
                    name="Berlin",
                    status="enabled",
                )
                mock_instance.insert.assert_called_once()

    def test_enables_disabled_entity(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"

        row = FakeRow(city="Berlin")
        existing = MagicMock()
        existing.status = "disabled"

        with patch("app.entity.Entity") as mock_entity_cls:
            with patch("app.entity.compute_entity_id", return_value="city-berlin-uuid"):
                mock_entity_cls.find_by_uuid.return_value = existing
                with patch("app.entities.statements.Statement") as mock_stmt:
                    mock_stmt.find.return_value = None
                    mock_stmt.from_row.return_value = MagicMock()

                    source._upsert_entity_ref(row, "city", "city")

        assert existing.status == "enabled"
        existing.save.assert_called_once()

    def test_skips_empty_value(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"

        row = FakeRow(city="")

        with patch("app.entity.Entity") as mock_entity_cls:
            source._upsert_entity_ref(row, "city", "city")
            mock_entity_cls.find_by_uuid.assert_not_called()

    def test_skips_none_value(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"

        row = FakeRow(city=None)

        with patch("app.entity.Entity") as mock_entity_cls:
            source._upsert_entity_ref(row, "city", "city")
            mock_entity_cls.find_by_uuid.assert_not_called()

    def test_creates_linking_statement(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"

        row = FakeRow(city="Berlin")

        with patch("app.entity.Entity") as mock_entity_cls:
            with patch("app.entity.compute_entity_id", return_value="city-berlin-uuid"):
                mock_entity_cls.find_by_uuid.return_value = None
                mock_entity_cls.return_value = MagicMock()
                with patch("app.entities.statements.Statement") as mock_stmt:
                    mock_stmt.find.return_value = None
                    mock_from_row = MagicMock()
                    mock_stmt.from_row.return_value = mock_from_row

                    source._upsert_entity_ref(row, "city", "city")

                    mock_stmt.find.assert_called_once_with("city-berlin-uuid", "referenced_by:city", "fakesrc")
                    mock_stmt.from_row.assert_called_once_with(
                        ("city-berlin-uuid", "referenced_by:city", "fakesrc", "fakesrc", "normal", None, "fakesrc")
                    )
                    mock_from_row.insert.assert_called_once()


# ---------------------------------------------------------------------------
# _upsert_property_statement
# ---------------------------------------------------------------------------


class TestUpsertPropertyStatement:
    def test_creates_new_statement(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"

        row = FakeRow(language="de")
        mock_stmt_cls = MagicMock()
        mock_stmt_cls.find.return_value = None
        mock_from_row = MagicMock()
        mock_stmt_cls.from_row.return_value = mock_from_row

        source._upsert_property_statement(row, "language", "P277", "entity-1", mock_stmt_cls)

        mock_stmt_cls.find.assert_called_once_with("entity-1", "P277", "de")
        mock_stmt_cls.from_row.assert_called_once_with(("entity-1", "P277", "de", "de", "normal", None, "fakesrc"))
        mock_from_row.insert.assert_called_once()

    def test_updates_existing_statement(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"

        row = FakeRow(language="de")
        existing = MagicMock()
        mock_stmt_cls = MagicMock()
        mock_stmt_cls.find.return_value = existing

        source._upsert_property_statement(row, "language", "P277", "entity-1", mock_stmt_cls)

        assert existing.value_label == "de"
        assert existing.source == "fakesrc"
        existing.save.assert_called_once()

    def test_skips_none_value(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"

        row = FakeRow(empty_field=None)
        mock_stmt_cls = MagicMock()

        source._upsert_property_statement(row, "empty_field", "P999", "entity-1", mock_stmt_cls)

        mock_stmt_cls.find.assert_not_called()

    def test_skips_empty_string_value(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"

        row = FakeRow(language="")
        mock_stmt_cls = MagicMock()

        source._upsert_property_statement(row, "language", "P277", "entity-1", mock_stmt_cls)

        mock_stmt_cls.find.assert_not_called()


# ---------------------------------------------------------------------------
# cleanup_client
# ---------------------------------------------------------------------------


class TestCleanupClient:
    def test_default_does_nothing(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"
        # Should not raise
        result = source.cleanup_client(MagicMock())
        assert result is None


# ---------------------------------------------------------------------------
# _lookback_start_date
# ---------------------------------------------------------------------------


class TestLookbackStartDate:
    def test_returns_default_when_no_config(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"

        mock_config = MagicMock()
        mock_config.read_row.return_value = None
        source.Config = mock_config

        result = source._lookback_start_date(90)
        assert result == "90 days ago"

    def test_returns_config_value(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"

        mock_config = MagicMock()
        mock_config.read_row.return_value = {"lookback_period": 30}
        source.Config = mock_config

        result = source._lookback_start_date(90)
        assert result == "30 days ago"

    def test_falls_back_on_zero_config(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"

        mock_config = MagicMock()
        mock_config.read_row.return_value = {"lookback_period": 0}
        source.Config = mock_config

        result = source._lookback_start_date(90)
        assert result == "90 days ago"

    def test_falls_back_on_exception(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"

        mock_config = MagicMock()
        mock_config.read_row.side_effect = RuntimeError("DB error")
        source.Config = mock_config

        result = source._lookback_start_date(60)
        assert result == "60 days ago"

    def test_coerces_string_config_value(self) -> None:
        source = FakeSource.__new__(FakeSource)
        source.name = "fakesrc"

        mock_config = MagicMock()
        mock_config.read_row.return_value = {"lookback_period": "14"}
        source.Config = mock_config

        result = source._lookback_start_date(90)
        assert result == "14 days ago"
