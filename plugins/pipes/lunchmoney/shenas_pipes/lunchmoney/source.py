from __future__ import annotations

from datetime import date as date_type
from typing import TYPE_CHECKING, Any

import dlt
import pendulum

from shenas_pipes.lunchmoney.tables import (
    Asset,
    Budget,
    Category,
    PlaidAccount,
    RecurringItem,
    Tag,
    Transaction,
)
from shenas_schemas.core.dlt import dataclass_to_dlt_columns

if TYPE_CHECKING:
    from collections.abc import Iterator

    from lunchable import LunchMoney


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
    from shenas_pipes.core.utils import resolve_start_date

    effective_start = (cursor.last_value or resolve_start_date(start_date))[:10]
    end_date = pendulum.now().to_date_string()
    rows = client.get_transactions(
        start_date=date_type.fromisoformat(effective_start),
        end_date=date_type.fromisoformat(end_date),
    )
    for tx in rows:
        yield tx.model_dump(mode="json")


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
    from shenas_pipes.core.utils import resolve_start_date

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
