"""Lunch Money source tables.

Each table is a subclass of one of the kind base classes in
``shenas_sources.core.table``. The class declares its schema fields, its
metadata, and the extraction logic in one place. The kind base class
determines the dlt write_disposition automatically.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import TYPE_CHECKING, Annotated, Any, ClassVar

import pendulum

from app.relation import PlotHint
from app.table import Field
from shenas_sources.core.table import (
    DimensionTable,
    EventTable,
    M2MTable,
    SnapshotTable,
    SourceTable,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from lunchable import LunchMoney


# ---------------------------------------------------------------------------
# Shared transactions cache
# ---------------------------------------------------------------------------
# Both Transactions and TransactionTags pull from the same client.get_transactions
# call. We cache the list at module level for the duration of one sync so the
# tag link table doesn't trigger a second API call.

_TX_CACHE: dict[tuple[int, str, str], list[Any]] = {}


def _fetch_transactions(client: LunchMoney, start: date_type, end: date_type) -> list[Any]:
    key = (id(client), start.isoformat(), end.isoformat())
    cached = _TX_CACHE.get(key)
    if cached is not None:
        return cached
    rows = list(client.get_transactions(start_date=start, end_date=end))
    _TX_CACHE[key] = rows
    return rows


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class Transactions(EventTable):
    """A single Lunch Money transaction (one per outflow/inflow event)."""

    class _Meta:
        name = "transactions"
        display_name = "Transactions"
        description = "Per-transaction events synced from Lunch Money."
        pk = ("id",)
        time_at = "date"
        plot = (PlotHint("amount", group_by="category_name", chart_type="bar"),)

    cursor_column: ClassVar[str] = "date"

    id: Annotated[int, Field(db_type="INTEGER", description="Transaction ID", display_name="Transaction ID")]
    date: Annotated[str, Field(db_type="DATE", description="Transaction date", display_name="Date")]
    payee: Annotated[str | None, Field(db_type="VARCHAR", description="Payee name (user-edited)", display_name="Payee")] = None
    original_name: Annotated[
        str | None, Field(db_type="VARCHAR", description="Original payee from source", display_name="Original Name")
    ] = None
    amount: Annotated[float, Field(db_type="DOUBLE", description="Transaction amount", display_name="Amount")] = 0.0
    currency: Annotated[str | None, Field(db_type="VARCHAR", description="Currency code", display_name="Currency")] = None
    to_base: Annotated[
        float | None, Field(db_type="DOUBLE", description="Amount in primary currency", display_name="Base Amount")
    ] = None
    category_id: Annotated[int | None, Field(db_type="INTEGER", description="Category ID", display_name="Category ID")] = None
    category_name: Annotated[str | None, Field(db_type="VARCHAR", description="Category name", display_name="Category")] = None
    asset_id: Annotated[
        int | None, Field(db_type="INTEGER", description="Linked manual asset ID", display_name="Asset ID")
    ] = None
    plaid_account_id: Annotated[
        int | None, Field(db_type="INTEGER", description="Linked Plaid account ID", display_name="Plaid Account ID")
    ] = None
    recurring_id: Annotated[
        int | None, Field(db_type="INTEGER", description="Linked recurring item ID", display_name="Recurring ID")
    ] = None
    type: Annotated[str | None, Field(db_type="VARCHAR", description="Transaction type", display_name="Type")] = None
    parent_id: Annotated[
        int | None, Field(db_type="INTEGER", description="Parent transaction ID (for splits)", display_name="Parent ID")
    ] = None
    has_children: Annotated[bool, Field(db_type="BOOLEAN", description="Has split children", display_name="Has Children")] = (
        False
    )
    group_id: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Transaction group ID (e.g. transfers)", display_name="Group ID"),
    ] = None
    is_group: Annotated[
        bool, Field(db_type="BOOLEAN", description="Is itself a group transaction", display_name="Is Group")
    ] = False
    external_id: Annotated[
        str | None, Field(db_type="VARCHAR", description="External / Plaid ID", display_name="External ID")
    ] = None
    is_income: Annotated[
        bool | None, Field(db_type="BOOLEAN", description="Whether this is income", display_name="Is Income")
    ] = None
    is_pending: Annotated[bool, Field(db_type="BOOLEAN", description="Pending transaction", display_name="Is Pending")] = False
    status: Annotated[str | None, Field(db_type="VARCHAR", description="Transaction status", display_name="Status")] = None
    notes: Annotated[str | None, Field(db_type="TEXT", description="Notes", display_name="Notes")] = None
    created_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Creation timestamp", display_name="Created At")
    ] = None
    updated_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Last updated timestamp", display_name="Updated At")
    ] = None

    @classmethod
    def extract(
        cls,
        client: LunchMoney,
        *,
        start_date: str = "90 days ago",
        cursor: Any = None,
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        from shenas_sources.core.utils import resolve_start_date

        last_value = getattr(cursor, "last_value", None) if cursor is not None else None
        effective_start = (last_value or resolve_start_date(start_date))[:10]
        end_date = pendulum.now().to_date_string()
        rows = _fetch_transactions(
            client,
            date_type.fromisoformat(effective_start),
            date_type.fromisoformat(end_date),
        )
        for tx in rows:
            yield tx.model_dump(mode="json")


class TransactionTags(M2MTable):
    """Many-to-many bridge between ``transactions`` and ``tags``.

    Composite PK is (transaction_id, tag_id) and no value columns -- the link
    is the entire row. Loaded as SCD2 so when the user removes a tag from a
    transaction, the loader closes the row's ``_dlt_valid_to`` instead of
    leaving it alive forever (as the previous EventTable + merge-on-PK
    classification did). Tag *name* is NOT denormalized here; join to the
    ``tags`` dimension AS OF the desired timestamp to get historical names.
    """

    class _Meta:
        name = "transaction_tags"
        display_name = "Transaction Tags"
        description = "(transaction_id, tag_id) link rows from tagged transactions."
        pk = ("transaction_id", "tag_id")

    transaction_id: Annotated[int, Field(db_type="INTEGER", description="Transaction ID", display_name="Transaction ID")]
    tag_id: Annotated[int, Field(db_type="INTEGER", description="Tag ID", display_name="Tag ID")]

    @classmethod
    def extract(
        cls,
        client: LunchMoney,
        *,
        start_date: str = "90 days ago",
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
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
                }


# ---------------------------------------------------------------------------
# Dimensions (loaded as SCD2)
# ---------------------------------------------------------------------------


class Categories(DimensionTable):
    """A spending/income category. Joined by transactions on ``category_id``."""

    class _Meta:
        name = "categories"
        display_name = "Categories"
        description = "Spending and income categories the user has defined."
        pk = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Category ID", display_name="Category ID")]
    category_name: Annotated[str, Field(db_type="VARCHAR", description="Category name", display_name="Category Name")]
    is_income: Annotated[
        bool, Field(db_type="BOOLEAN", description="Whether this is an income category", display_name="Is Income")
    ] = False
    exclude_from_budget: Annotated[
        bool, Field(db_type="BOOLEAN", description="Excluded from budget", display_name="Exclude Budget")
    ] = False
    exclude_from_totals: Annotated[
        bool, Field(db_type="BOOLEAN", description="Excluded from totals", display_name="Exclude Totals")
    ] = False
    archived: Annotated[bool, Field(db_type="BOOLEAN", description="Whether archived", display_name="Archived")] = False

    @classmethod
    def extract(cls, client: LunchMoney, **_: Any) -> Iterator[dict[str, Any]]:
        for cat in client.get_categories():
            row = cat.model_dump(mode="json")
            # The lunchable model uses `name`; rename to `category_name` so it
            # doesn't collide with the Table class attribute.
            if "name" in row:
                row["category_name"] = row.pop("name")
            yield row


class Tags(DimensionTable):
    """A user-defined tag. Joined by transaction_tags on ``tag_id``."""

    class _Meta:
        name = "tags"
        display_name = "Tags"
        description = "User-defined transaction tags."
        pk = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Tag ID", display_name="Tag ID")]
    tag_name: Annotated[str, Field(db_type="VARCHAR", description="Tag name", display_name="Tag Name")]
    archived: Annotated[bool, Field(db_type="BOOLEAN", description="Whether archived", display_name="Archived")] = False

    @classmethod
    def extract(cls, client: LunchMoney, **_: Any) -> Iterator[dict[str, Any]]:
        for tag in client.get_tags():
            row = tag.model_dump(mode="json")
            if "name" in row:
                row["tag_name"] = row.pop("name")
            yield row


class Assets(DimensionTable):
    """A manually-tracked asset. Joined by transactions on ``asset_id``.

    NOTE: ``balance`` and ``balance_as_of`` are intentionally not in this
    schema -- balance changes daily and would mint a new SCD2 version every
    sync. A separate counter table for asset balances will land in a follow-up.
    """

    class _Meta:
        name = "assets"
        display_name = "Assets"
        description = "Manually-tracked assets (cash accounts, brokerage, etc.)."
        pk = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Asset ID", display_name="Asset ID")]
    asset_name: Annotated[str, Field(db_type="VARCHAR", description="Asset name", display_name="Asset Name")]
    type_name: Annotated[str, Field(db_type="VARCHAR", description="Asset type", display_name="Asset Type")]
    currency: Annotated[str, Field(db_type="VARCHAR", description="Currency code", display_name="Currency")] = ""
    institution_name: Annotated[
        str | None, Field(db_type="VARCHAR", description="Institution name", display_name="Institution")
    ] = None
    created_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Creation timestamp", display_name="Created At")
    ] = None

    @classmethod
    def extract(cls, client: LunchMoney, **_: Any) -> Iterator[dict[str, Any]]:
        for asset in client.get_assets():
            row = asset.model_dump(mode="json")
            if "name" in row:
                row["asset_name"] = row.pop("name")
            # Drop balance fields -- see class docstring.
            row.pop("balance", None)
            row.pop("balance_as_of", None)
            yield row


class PlaidAccounts(DimensionTable):
    """A connected Plaid account. Joined by transactions on ``plaid_account_id``.

    NOTE: ``balance`` is intentionally not in this schema -- it changes daily.
    """

    class _Meta:
        name = "plaid_accounts"
        display_name = "Plaid Accounts"
        description = "Connected bank/credit card accounts via Plaid."
        pk = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Plaid account ID", display_name="Account ID")]
    account_name: Annotated[str, Field(db_type="VARCHAR", description="Account name", display_name="Account Name")]
    type: Annotated[str, Field(db_type="VARCHAR", description="Account type", display_name="Account Type")] = ""
    subtype: Annotated[str, Field(db_type="VARCHAR", description="Account subtype", display_name="Subtype")] = ""
    institution_name: Annotated[str, Field(db_type="VARCHAR", description="Institution name", display_name="Institution")] = ""
    status: Annotated[str, Field(db_type="VARCHAR", description="Account status", display_name="Status")] = ""
    currency: Annotated[str, Field(db_type="VARCHAR", description="Currency code", display_name="Currency")] = ""
    date_linked: Annotated[str, Field(db_type="DATE", description="Date linked", display_name="Date Linked")] = ""

    @classmethod
    def extract(cls, client: LunchMoney, **_: Any) -> Iterator[dict[str, Any]]:
        for acct in client.get_plaid_accounts():
            row = acct.model_dump(mode="json")
            if "name" in row:
                row["account_name"] = row.pop("name")
            row.pop("balance", None)
            yield row


# ---------------------------------------------------------------------------
# Snapshots (loaded as SCD2)
# ---------------------------------------------------------------------------


class Budgets(SnapshotTable):
    """Per-category budget configuration."""

    class _Meta:
        name = "budgets"
        display_name = "Budgets"
        description = "Per-category budget configuration."
        pk = ("category_name",)

    category_name: Annotated[str, Field(db_type="VARCHAR", description="Budget category name", display_name="Category")]
    category_id: Annotated[int | None, Field(db_type="INTEGER", description="Category ID", display_name="Category ID")] = None
    is_income: Annotated[
        bool, Field(db_type="BOOLEAN", description="Whether this is an income category", display_name="Is Income")
    ] = False
    exclude_from_budget: Annotated[
        bool, Field(db_type="BOOLEAN", description="Excluded from budget", display_name="Exclude Budget")
    ] = False
    exclude_from_totals: Annotated[
        bool, Field(db_type="BOOLEAN", description="Excluded from totals", display_name="Exclude Totals")
    ] = False

    @classmethod
    def extract(
        cls,
        client: LunchMoney,
        *,
        start_date: str = "90 days ago",
        **_: Any,
    ) -> Iterator[dict[str, Any]]:
        from shenas_sources.core.utils import resolve_start_date

        start = date_type.fromisoformat(resolve_start_date(start_date)[:10])
        end = pendulum.now().date()
        for budget in client.get_budgets(start_date=start, end_date=end):
            yield budget.model_dump(mode="json")


class RecurringItems(DimensionTable):
    """Recurring transaction templates. Joined by ``transactions.recurring_id``.

    A dimension, not a snapshot, because when the user changes a recurring
    amount (Netflix raises its price), historical transactions joined AS OF
    their own date will still resolve the original amount via SCD2.
    """

    class _Meta:
        name = "recurring_items"
        display_name = "Recurring Items"
        description = "Recurring transaction templates (subscriptions, bills, etc.)."
        pk = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Recurring item ID", display_name="Recurring ID")]
    payee: Annotated[str, Field(db_type="VARCHAR", description="Payee name", display_name="Payee")]
    amount: Annotated[float, Field(db_type="DOUBLE", description="Recurring amount", display_name="Amount")] = 0.0
    currency: Annotated[str, Field(db_type="VARCHAR", description="Currency code", display_name="Currency")] = ""
    cadence: Annotated[str | None, Field(db_type="VARCHAR", description="Recurrence cadence", display_name="Cadence")] = None
    billing_date: Annotated[str, Field(db_type="DATE", description="Next billing date", display_name="Billing Date")] = ""
    source: Annotated[str, Field(db_type="VARCHAR", description="Source", display_name="Source")] = ""
    created_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Creation timestamp", display_name="Created At")
    ] = None

    @classmethod
    def extract(cls, client: LunchMoney, **_: Any) -> Iterator[dict[str, Any]]:
        for item in client.get_recurring_items():
            yield item.model_dump(mode="json")


class User(SnapshotTable):
    """The authenticated Lunch Money user / account info."""

    class _Meta:
        name = "user"
        display_name = "User"
        description = "Authenticated user / account info."
        pk = ("user_id",)

    user_id: Annotated[int, Field(db_type="INTEGER", description="User ID", display_name="User ID")]
    user_name: Annotated[str | None, Field(db_type="VARCHAR", description="User name", display_name="User Name")] = None
    user_email: Annotated[str | None, Field(db_type="VARCHAR", description="User email", display_name="Email")] = None
    account_id: Annotated[int | None, Field(db_type="INTEGER", description="Account ID", display_name="Account ID")] = None
    budget_name: Annotated[str | None, Field(db_type="VARCHAR", description="Budget name", display_name="Budget Name")] = None
    api_key_label: Annotated[
        str | None, Field(db_type="VARCHAR", description="API key label", display_name="API Key Label")
    ] = None

    @classmethod
    def extract(cls, client: LunchMoney, **_: Any) -> Iterator[dict[str, Any]]:
        yield client.get_user().model_dump(mode="json")


class Crypto(SnapshotTable):
    """Crypto holdings.

    NOTE: ``balance`` and ``balance_as_of`` are intentionally not in this
    schema -- balance changes minute-to-minute and would mint a new SCD2
    version every sync. A separate counter table for crypto balances will
    land in a follow-up.
    """

    class _Meta:
        name = "crypto"
        display_name = "Crypto"
        description = "Crypto holdings (manual + connected exchange accounts)."
        pk = ("id",)

    id: Annotated[int, Field(db_type="INTEGER", description="Crypto holding ID", display_name="Crypto ID")]
    crypto_name: Annotated[str | None, Field(db_type="VARCHAR", description="Asset name", display_name="Crypto Name")] = None
    currency: Annotated[
        str | None, Field(db_type="VARCHAR", description="Crypto symbol/currency", display_name="Currency")
    ] = None
    institution_name: Annotated[
        str | None, Field(db_type="VARCHAR", description="Institution name", display_name="Institution")
    ] = None
    source: Annotated[str | None, Field(db_type="VARCHAR", description="Source: manual or synced", display_name="Source")] = (
        None
    )
    status: Annotated[str | None, Field(db_type="VARCHAR", description="Status", display_name="Status")] = None
    zabo_account_id: Annotated[
        str | None, Field(db_type="VARCHAR", description="Zabo account ID", display_name="Zabo Account ID")
    ] = None
    created_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Creation timestamp", display_name="Created At")
    ] = None

    @classmethod
    def extract(cls, client: LunchMoney, **_: Any) -> Iterator[dict[str, Any]]:
        try:
            holdings = client.get_crypto()
        except Exception:
            return
        for c in holdings:
            row = c.model_dump(mode="json")
            if "name" in row:
                row["crypto_name"] = row.pop("name")
            row.pop("balance", None)
            row.pop("balance_as_of", None)
            yield row


# Tables this source exposes, in sync order.
TABLES: tuple[type[SourceTable], ...] = (
    Transactions,
    TransactionTags,
    Categories,
    Tags,
    Budgets,
    RecurringItems,
    Assets,
    PlaidAccounts,
    User,
    Crypto,
)
