from __future__ import annotations

from collections.abc import Iterator
from datetime import date as date_type
from typing import Any

import dlt
import pendulum
from lunchable import LunchMoney

from shenas_pipes.lunchmoney.auth import build_client
from shenas_pipes.lunchmoney.utils import resolve_start_date


@dlt.source(name="lunchmoney")
def lunchmoney(
    api_key: str = dlt.secrets.value,
    start_date: str = dlt.config.value,
    token_store: str | None = None,
) -> Any:
    client = build_client(api_key, token_store)
    resolved = resolve_start_date(start_date)
    return (
        transactions(client, resolved),
        categories(client),
        tags(client),
        budgets(client, resolved),
        recurring_items(client),
        assets(client),
        plaid_accounts(client),
    )


@dlt.resource(write_disposition="merge", primary_key="id")
def transactions(
    client: LunchMoney,
    start_date: str,
    cursor: dlt.sources.incremental[str] = dlt.sources.incremental("date", initial_value=None),
) -> Iterator[dict[str, Any]]:
    effective_start = (cursor.last_value or start_date)[:10]
    end_date = pendulum.now().to_date_string()
    rows = client.get_transactions(
        start_date=date_type.fromisoformat(effective_start),
        end_date=date_type.fromisoformat(end_date),
    )
    for tx in rows:
        yield tx.model_dump(mode="json")


@dlt.resource(write_disposition="replace")
def categories(client: LunchMoney) -> Iterator[dict[str, Any]]:
    rows = client.get_categories()
    for cat in rows:
        yield cat.model_dump(mode="json")


@dlt.resource(write_disposition="replace")
def tags(client: LunchMoney) -> Iterator[dict[str, Any]]:
    rows = client.get_tags()
    for tag in rows:
        yield tag.model_dump(mode="json")


@dlt.resource(write_disposition="replace")
def budgets(client: LunchMoney, start_date: str) -> Iterator[dict[str, Any]]:
    start = date_type.fromisoformat(start_date[:10])
    end = pendulum.now().date()
    data = client.get_budgets(start_date=start, end_date=end)
    for budget in data:
        yield budget.model_dump(mode="json")


@dlt.resource(write_disposition="merge", primary_key="id")
def recurring_items(client: LunchMoney) -> Iterator[dict[str, Any]]:
    rows = client.get_recurring_items()
    for item in rows:
        yield item.model_dump(mode="json")


@dlt.resource(write_disposition="replace")
def assets(client: LunchMoney) -> Iterator[dict[str, Any]]:
    rows = client.get_assets()
    for asset in rows:
        yield asset.model_dump(mode="json")


@dlt.resource(write_disposition="replace")
def plaid_accounts(client: LunchMoney) -> Iterator[dict[str, Any]]:
    rows = client.get_plaid_accounts()
    for acct in rows:
        yield acct.model_dump(mode="json")
