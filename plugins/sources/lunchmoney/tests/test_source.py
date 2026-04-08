"""Tests for Lunch Money source resources."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from shenas_sources.lunchmoney.resources import (
    crypto,
    transaction_tags,
    transactions,
    user,
)


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


class TestTransactionsAndTagsShareCache:
    def test_transactions_resource_yields_rows(self) -> None:
        client = MagicMock()
        client.get_transactions.return_value = [_make_tx(id=1), _make_tx(id=2)]
        rows = list(transactions(client, start_date="2026-01-01"))
        assert [r["id"] for r in rows] == [1, 2]
        assert client.get_transactions.call_count == 1

    def test_transaction_tags_yields_link_rows(self) -> None:
        client = MagicMock()
        tag_a = SimpleNamespace(id=10, name="travel")
        tag_b = SimpleNamespace(id=20, name="reimbursable")
        client.get_transactions.return_value = [
            _make_tx(id=1, tag_objs=[tag_a, tag_b]),
            _make_tx(id=2, tag_objs=[]),
            _make_tx(id=3, tag_objs=[tag_a]),
        ]
        rows = list(transaction_tags(client, start_date="2026-01-01"))
        assert sorted((r["transaction_id"], r["tag_id"]) for r in rows) == [
            (1, 10),
            (1, 20),
            (3, 10),
        ]
        assert rows[0]["tag_name"] == "travel"

    def test_skips_tags_without_id(self) -> None:
        client = MagicMock()
        broken = SimpleNamespace(id=None, name="bogus")
        client.get_transactions.return_value = [_make_tx(id=1, tag_objs=[broken])]
        assert list(transaction_tags(client, start_date="2026-01-01")) == []


class TestUserResource:
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
        rows = list(user(client))
        assert len(rows) == 1
        assert rows[0]["user_id"] == 999
        assert rows[0]["budget_name"] == "Personal"


class TestCryptoResource:
    def test_yields_crypto(self) -> None:
        client = MagicMock()
        client.get_crypto.return_value = [
            SimpleNamespace(
                model_dump=lambda mode="json": {
                    "id": 1,
                    "name": "Bitcoin",
                    "currency": "BTC",
                    "balance": 0.5,
                    "balance_as_of": "2026-04-01T00:00:00Z",
                    "source": "manual",
                    "status": "active",
                }
            )
        ]
        rows = list(crypto(client))
        assert len(rows) == 1
        assert rows[0]["currency"] == "BTC"
        assert rows[0]["balance"] == 0.5

    def test_handles_failure(self) -> None:
        client = MagicMock()
        client.get_crypto.side_effect = RuntimeError("not on this plan")
        assert list(crypto(client)) == []
