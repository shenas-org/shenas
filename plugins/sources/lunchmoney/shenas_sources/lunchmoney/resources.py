from __future__ import annotations

from datetime import date as date_type
from typing import TYPE_CHECKING, Any

import dlt
import pendulum

from shenas_datasets.core.dlt import dataclass_to_dlt_columns
from shenas_sources.lunchmoney.tables import (
    Asset,
    Budget,
    Category,
    Crypto,
    PlaidAccount,
    RecurringItem,
    Tag,
    Transaction,
    TransactionTag,
    User,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from lunchable import LunchMoney


def _fetch_transactions(client: LunchMoney, start: date_type, end: date_type) -> list[Any]:
    """Fetch transactions in [start, end]. Cached at module level for the
    duration of one sync so the transactions and transaction_tags resources
    only call the API once."""
    key = (id(client), start.isoformat(), end.isoformat())
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    rows = list(client.get_transactions(start_date=start, end_date=end))
    _CACHE[key] = rows
    return rows


_CACHE: dict[tuple[int, str, str], list[Any]] = {}


@dlt.resource(
    write_disposition="merge",
    primary_key=list(Transaction.__pk__),
    columns=dataclass_to_dlt_columns(Transaction),
)
def transactions(
    client: LunchMoney,
    start_date: str,
    cursor: dlt.sources.incremental[str] = dlt.sources.incremental("date", initial_value=None),
) -> Iterator[dict[str, Any]]:
    from shenas_sources.core.utils import resolve_start_date

    effective_start = (cursor.last_value or resolve_start_date(start_date))[:10]
    end_date = pendulum.now().to_date_string()
    rows = _fetch_transactions(
        client,
        date_type.fromisoformat(effective_start),
        date_type.fromisoformat(end_date),
    )
    for tx in rows:
        yield tx.model_dump(mode="json")


@dlt.resource(
    name="transaction_tags",
    write_disposition="merge",
    primary_key=list(TransactionTag.__pk__),
    columns=dataclass_to_dlt_columns(TransactionTag),
)
def transaction_tags(
    client: LunchMoney,
    start_date: str,
) -> Iterator[dict[str, Any]]:
    """Yield (transaction_id, tag_id) link rows for every tagged transaction.

    Reuses the transactions cache populated by the `transactions` resource so
    no extra API call is made within a single sync.
    """
    from shenas_sources.core.utils import resolve_start_date

    effective_start = resolve_start_date(start_date)[:10]
    end_date = pendulum.now().to_date_string()
    rows = _fetch_transactions(
        client,
        date_type.fromisoformat(effective_start),
        date_type.fromisoformat(end_date),
    )
    for tx in rows:
        for tag in getattr(tx, "tags", None) or []:
            tag_id = getattr(tag, "id", None)
            if tag_id is None:
                continue
            yield {
                "transaction_id": int(tx.id),
                "tag_id": int(tag_id),
                "tag_name": getattr(tag, "name", None),
            }


@dlt.resource(write_disposition="replace", columns=dataclass_to_dlt_columns(Category))
def categories(client: LunchMoney) -> Iterator[dict[str, Any]]:
    rows = client.get_categories()
    for cat in rows:
        yield cat.model_dump(mode="json")


@dlt.resource(write_disposition="replace", columns=dataclass_to_dlt_columns(Tag))
def tags(client: LunchMoney) -> Iterator[dict[str, Any]]:
    rows = client.get_tags()
    for tag in rows:
        yield tag.model_dump(mode="json")


@dlt.resource(write_disposition="replace", columns=dataclass_to_dlt_columns(Budget))
def budgets(client: LunchMoney, start_date: str) -> Iterator[dict[str, Any]]:
    from shenas_sources.core.utils import resolve_start_date

    start = date_type.fromisoformat(resolve_start_date(start_date)[:10])
    end = pendulum.now().date()
    data = client.get_budgets(start_date=start, end_date=end)
    for budget in data:
        yield budget.model_dump(mode="json")


@dlt.resource(
    write_disposition="merge",
    primary_key=list(RecurringItem.__pk__),
    columns=dataclass_to_dlt_columns(RecurringItem),
)
def recurring_items(client: LunchMoney) -> Iterator[dict[str, Any]]:
    rows = client.get_recurring_items()
    for item in rows:
        yield item.model_dump(mode="json")


@dlt.resource(write_disposition="replace", columns=dataclass_to_dlt_columns(Asset))
def assets(client: LunchMoney) -> Iterator[dict[str, Any]]:
    rows = client.get_assets()
    for asset in rows:
        yield asset.model_dump(mode="json")


@dlt.resource(write_disposition="replace", columns=dataclass_to_dlt_columns(PlaidAccount))
def plaid_accounts(client: LunchMoney) -> Iterator[dict[str, Any]]:
    rows = client.get_plaid_accounts()
    for acct in rows:
        yield acct.model_dump(mode="json")


@dlt.resource(name="user", write_disposition="replace", columns=dataclass_to_dlt_columns(User))
def user(client: LunchMoney) -> Iterator[dict[str, Any]]:
    """Yield the authenticated user / account info (single row)."""
    me = client.get_user()
    yield me.model_dump(mode="json")


@dlt.resource(name="crypto", write_disposition="replace", columns=dataclass_to_dlt_columns(Crypto))
def crypto(client: LunchMoney) -> Iterator[dict[str, Any]]:
    """Yield crypto holdings."""
    try:
        rows = client.get_crypto()
    except Exception:
        return
    for c in rows:
        yield c.model_dump(mode="json")
