"""Tests for Lunch Money source tables (Table ABC pattern)."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from shenas_sources.core.table import DimensionTable, EventTable, M2MTable, SnapshotTable
from shenas_sources.lunchmoney import tables as t


@pytest.fixture(autouse=True)
def _clear_tx_cache() -> None:
    """The transactions cache is module-level state shared between tests."""
    t._TX_CACHE.clear()


def _make_tx(tag_objs: list[SimpleNamespace] | None = None, **overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 1,
        "date": "2026-04-01",
        "payee": "Test Payee",
        "amount": 12.34,
        "currency": "USD",
        "tags": tag_objs or [],
    }
    base.update(overrides)

    def _model_dump(mode: str = "json") -> dict[str, object]:
        return {k: v for k, v in base.items() if k != "tags"}

    return SimpleNamespace(model_dump=_model_dump, **base)


class TestTransactionsExtract:
    def test_yields_rows(self) -> None:
        client = MagicMock()
        client.get_transactions.return_value = [_make_tx(id=1), _make_tx(id=2)]
        rows = list(t.Transactions.extract(client, start_date="2026-01-01"))
        assert [r["id"] for r in rows] == [1, 2]
        # Single API call for the page
        assert client.get_transactions.call_count == 1

    def test_uses_cursor_last_value_when_set(self) -> None:
        client = MagicMock()
        client.get_transactions.return_value = [_make_tx(id=1)]
        cursor = SimpleNamespace(last_value="2026-03-15")
        list(t.Transactions.extract(client, start_date="2026-01-01", cursor=cursor))
        # cursor.last_value should be the start of the fetched window
        call_kwargs = client.get_transactions.call_args.kwargs
        assert call_kwargs["start_date"].isoformat() == "2026-03-15"


class TestTransactionTagsExtract:
    def test_yields_link_rows(self) -> None:
        client = MagicMock()
        tag_a = SimpleNamespace(id=10, name="travel")
        tag_b = SimpleNamespace(id=20, name="reimbursable")
        client.get_transactions.return_value = [
            _make_tx(id=1, tag_objs=[tag_a, tag_b]),
            _make_tx(id=2, tag_objs=[]),
            _make_tx(id=3, tag_objs=[tag_a]),
        ]
        rows = list(t.TransactionTags.extract(client, start_date="2026-01-01"))
        assert sorted((r["transaction_id"], r["tag_id"]) for r in rows) == [
            (1, 10),
            (1, 20),
            (3, 10),
        ]

    def test_skips_tags_without_id(self) -> None:
        client = MagicMock()
        broken = SimpleNamespace(id=None, name="bogus")
        client.get_transactions.return_value = [_make_tx(id=1, tag_objs=[broken])]
        assert list(t.TransactionTags.extract(client, start_date="2026-01-01")) == []


class TestSharedTransactionCache:
    def test_two_tables_share_one_api_call(self) -> None:
        client = MagicMock()
        client.get_transactions.return_value = [
            _make_tx(id=1, tag_objs=[SimpleNamespace(id=10, name="x")]),
        ]
        # First call populates the cache.
        list(t.Transactions.extract(client, start_date="2026-01-01"))
        # Second call (different table, same client + window) should hit the cache.
        list(t.TransactionTags.extract(client, start_date="2026-01-01"))
        assert client.get_transactions.call_count == 1


class TestUserExtract:
    def test_yields_user(self) -> None:
        client = MagicMock()
        client.get_user.return_value = SimpleNamespace(
            model_dump=lambda mode="json": {
                "user_id": 999,
                "user_name": "Alice",
                "user_email": "alice@example.com",
                "account_id": 42,
                "budget_name": "Personal",
                "api_key_label": "shenas",
            }
        )
        rows = list(t.User.extract(client))
        assert len(rows) == 1
        assert rows[0]["user_id"] == 999
        assert rows[0]["budget_name"] == "Personal"


class TestCryptoExtract:
    def test_yields_crypto_with_balance_dropped(self) -> None:
        client = MagicMock()
        client.get_crypto.return_value = [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "id": 1,
                    "name": "Bitcoin",
                    "currency": "BTC",
                    # balance fields will be popped by extract():
                    "balance": 0.5,
                    "balance_as_of": "2026-04-01T00:00:00Z",
                    "source": "manual",
                    "status": "active",
                }
            )
        ]
        rows = list(t.Crypto.extract(client))
        assert len(rows) == 1
        assert rows[0]["currency"] == "BTC"
        assert rows[0]["crypto_name"] == "Bitcoin"
        # Balance fields are deliberately dropped (counter follow-up).
        assert "balance" not in rows[0]
        assert "balance_as_of" not in rows[0]

    def test_handles_endpoint_failure(self) -> None:
        client = MagicMock()
        client.get_crypto.side_effect = RuntimeError("not on this plan")
        assert list(t.Crypto.extract(client)) == []


class TestCategoriesExtract:
    def test_yields_categories_with_renamed_field(self) -> None:
        client = MagicMock()
        client.get_categories.return_value = [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "id": 1,
                    "name": "Coffee",
                    "is_income": False,
                    "exclude_from_budget": False,
                    "exclude_from_totals": False,
                    "archived": False,
                }
            )
        ]
        rows = list(t.Categories.extract(client))
        assert len(rows) == 1
        assert rows[0]["category_name"] == "Coffee"
        assert "name" not in rows[0]


class TestKindsAndDispositions:
    def test_transactions_is_event_merge(self) -> None:
        assert issubclass(t.Transactions, EventTable)
        assert t.Transactions.write_disposition() == "merge"

    def test_categories_is_dimension_scd2(self) -> None:
        assert issubclass(t.Categories, DimensionTable)
        assert t.Categories.write_disposition() == {"disposition": "merge", "strategy": "scd2"}

    def test_user_is_snapshot_scd2(self) -> None:
        assert issubclass(t.User, SnapshotTable)
        assert t.User.write_disposition() == {"disposition": "merge", "strategy": "scd2"}

    def test_transaction_tags_is_m2m_relation_scd2(self) -> None:
        assert issubclass(t.TransactionTags, M2MTable)
        assert t.TransactionTags.write_disposition() == {"disposition": "merge", "strategy": "scd2"}

    def test_transaction_tags_no_observed_at(self) -> None:
        # M2MTable uses SCD2 (_dlt_valid_from/_dlt_valid_to), not observed_at.
        cols = t.TransactionTags.to_dlt_columns()
        assert "observed_at" not in cols

    def test_transaction_tags_has_no_value_columns(self) -> None:
        # The pure m2m link has only the two FKs -- no denormalized tag_name.
        cols = t.TransactionTags.to_dlt_columns()
        assert set(cols.keys()) == {"transaction_id", "tag_id"}

    def test_transactions_event_with_native_time_does_not_inject_observed_at(self) -> None:
        cols = t.Transactions.to_dlt_columns()
        assert "observed_at" not in cols
