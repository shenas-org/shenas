from __future__ import annotations

from shenas_pipes.core.transform import load_transform_defaults

TRANSFORM_DEFAULTS = load_transform_defaults("lunchmoney")


class TestLunchmoneyDefaults:
    def test_has_four_transforms(self) -> None:
        assert len(TRANSFORM_DEFAULTS) == 4

    def test_defaults_have_descriptions(self) -> None:
        for t in TRANSFORM_DEFAULTS:
            assert t.get("description"), f"Missing description for {t['target_duckdb_table']}"

    def test_all_target_metrics_schema(self) -> None:
        for t in TRANSFORM_DEFAULTS:
            assert t["target_duckdb_schema"] == "metrics"
