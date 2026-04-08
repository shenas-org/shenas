"""Lunch Money raw table schemas.

Most resources yield model_dump() dicts with many fields.
These dataclasses define only the key fields -- dlt will handle
extra fields automatically via its schema inference.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_plugins.core.field import Field, TableKind


@dataclass
class Transaction:
    """Lunch Money transaction."""

    __table__: ClassVar[str] = "transactions"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "event"

    id: Annotated[int, Field(db_type="INTEGER", description="Transaction ID")]
    date: Annotated[str, Field(db_type="DATE", description="Transaction date")]
    payee: Annotated[str | None, Field(db_type="VARCHAR", description="Payee name (user-edited)")] = None
    original_name: Annotated[str | None, Field(db_type="VARCHAR", description="Original payee from source")] = None
    amount: Annotated[float, Field(db_type="DOUBLE", description="Transaction amount")] = 0.0
    currency: Annotated[str | None, Field(db_type="VARCHAR", description="Currency code")] = None
    to_base: Annotated[float | None, Field(db_type="DOUBLE", description="Amount in primary currency")] = None
    category_id: Annotated[int | None, Field(db_type="INTEGER", description="Category ID")] = None
    category_name: Annotated[str | None, Field(db_type="VARCHAR", description="Category name")] = None
    asset_id: Annotated[int | None, Field(db_type="INTEGER", description="Linked manual asset ID")] = None
    plaid_account_id: Annotated[int | None, Field(db_type="INTEGER", description="Linked Plaid account ID")] = None
    recurring_id: Annotated[int | None, Field(db_type="INTEGER", description="Linked recurring item ID")] = None
    type: Annotated[str | None, Field(db_type="VARCHAR", description="Transaction type")] = None
    parent_id: Annotated[int | None, Field(db_type="INTEGER", description="Parent transaction ID (for splits)")] = None
    has_children: Annotated[bool, Field(db_type="BOOLEAN", description="Has split children")] = False
    group_id: Annotated[int | None, Field(db_type="INTEGER", description="Transaction group ID (e.g. transfers)")] = None
    is_group: Annotated[bool, Field(db_type="BOOLEAN", description="Is itself a group transaction")] = False
    external_id: Annotated[str | None, Field(db_type="VARCHAR", description="External / Plaid ID")] = None
    is_income: Annotated[bool | None, Field(db_type="BOOLEAN", description="Whether this is income")] = None
    is_pending: Annotated[bool, Field(db_type="BOOLEAN", description="Pending transaction")] = False
    status: Annotated[str | None, Field(db_type="VARCHAR", description="Transaction status")] = None
    notes: Annotated[str | None, Field(db_type="TEXT", description="Notes")] = None
    created_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="Creation timestamp")] = None
    updated_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="Last updated timestamp")] = None


@dataclass
class TransactionTag:
    """Link table joining a transaction to a tag."""

    __table__: ClassVar[str] = "transaction_tags"
    __pk__: ClassVar[tuple[str, ...]] = ("transaction_id", "tag_id")
    __kind__: ClassVar[TableKind] = "event"

    transaction_id: Annotated[int, Field(db_type="INTEGER", description="Transaction ID")]
    tag_id: Annotated[int, Field(db_type="INTEGER", description="Tag ID")]
    tag_name: Annotated[str | None, Field(db_type="VARCHAR", description="Tag name (denormalized)")] = None


@dataclass
class User:
    """Lunch Money authenticated user / account info."""

    __table__: ClassVar[str] = "user"
    __pk__: ClassVar[tuple[str, ...]] = ("user_id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    user_id: Annotated[int, Field(db_type="INTEGER", description="User ID")]
    user_name: Annotated[str | None, Field(db_type="VARCHAR", description="User name")] = None
    user_email: Annotated[str | None, Field(db_type="VARCHAR", description="User email")] = None
    account_id: Annotated[int | None, Field(db_type="INTEGER", description="Account ID")] = None
    budget_name: Annotated[str | None, Field(db_type="VARCHAR", description="Budget name")] = None
    api_key_label: Annotated[str | None, Field(db_type="VARCHAR", description="API key label")] = None


@dataclass
class Crypto:
    """Lunch Money crypto holding."""

    __table__: ClassVar[str] = "crypto"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    id: Annotated[int, Field(db_type="INTEGER", description="Crypto holding ID")]
    name: Annotated[str | None, Field(db_type="VARCHAR", description="Asset name")] = None
    display_name: Annotated[str | None, Field(db_type="VARCHAR", description="Display name")] = None
    currency: Annotated[str | None, Field(db_type="VARCHAR", description="Crypto symbol/currency")] = None
    balance: Annotated[float | None, Field(db_type="DOUBLE", description="Current balance")] = None
    balance_as_of: Annotated[str | None, Field(db_type="TIMESTAMP", description="Balance asof timestamp")] = None
    institution_name: Annotated[str | None, Field(db_type="VARCHAR", description="Institution name")] = None
    source: Annotated[str | None, Field(db_type="VARCHAR", description="Source: manual or synced")] = None
    status: Annotated[str | None, Field(db_type="VARCHAR", description="Status")] = None
    zabo_account_id: Annotated[str | None, Field(db_type="VARCHAR", description="Zabo account ID")] = None
    created_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="Creation timestamp")] = None


@dataclass
class Category:
    """Lunch Money category."""

    __table__: ClassVar[str] = "categories"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    id: Annotated[int, Field(db_type="INTEGER", description="Category ID")]
    name: Annotated[str, Field(db_type="VARCHAR", description="Category name")]
    is_income: Annotated[bool, Field(db_type="BOOLEAN", description="Whether this is an income category")] = False
    exclude_from_budget: Annotated[bool, Field(db_type="BOOLEAN", description="Excluded from budget")] = False
    exclude_from_totals: Annotated[bool, Field(db_type="BOOLEAN", description="Excluded from totals")] = False
    archived: Annotated[bool, Field(db_type="BOOLEAN", description="Whether archived")] = False


@dataclass
class Tag:
    """Lunch Money tag."""

    __table__: ClassVar[str] = "tags"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    id: Annotated[int, Field(db_type="INTEGER", description="Tag ID")]
    name: Annotated[str, Field(db_type="VARCHAR", description="Tag name")]
    description: Annotated[str | None, Field(db_type="VARCHAR", description="Tag description")] = None
    archived: Annotated[bool, Field(db_type="BOOLEAN", description="Whether archived")] = False


@dataclass
class Budget:
    """Lunch Money budget entry."""

    __table__: ClassVar[str] = "budgets"
    __pk__: ClassVar[tuple[str, ...]] = ("category_name",)
    __kind__: ClassVar[TableKind] = "snapshot"

    category_name: Annotated[str, Field(db_type="VARCHAR", description="Budget category name")]
    category_id: Annotated[int | None, Field(db_type="INTEGER", description="Category ID")] = None
    is_income: Annotated[bool, Field(db_type="BOOLEAN", description="Whether this is an income category")] = False
    exclude_from_budget: Annotated[bool, Field(db_type="BOOLEAN", description="Excluded from budget")] = False
    exclude_from_totals: Annotated[bool, Field(db_type="BOOLEAN", description="Excluded from totals")] = False


@dataclass
class RecurringItem:
    """Lunch Money recurring item."""

    __table__: ClassVar[str] = "recurring_items"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    id: Annotated[int, Field(db_type="INTEGER", description="Recurring item ID")]
    payee: Annotated[str, Field(db_type="VARCHAR", description="Payee name")]
    amount: Annotated[float, Field(db_type="DOUBLE", description="Recurring amount")] = 0.0
    currency: Annotated[str, Field(db_type="VARCHAR", description="Currency code")] = ""
    cadence: Annotated[str | None, Field(db_type="VARCHAR", description="Recurrence cadence")] = None
    billing_date: Annotated[str, Field(db_type="DATE", description="Next billing date")] = ""
    source: Annotated[str, Field(db_type="VARCHAR", description="Source")] = ""
    created_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="Creation timestamp")] = None


@dataclass
class Asset:
    """Lunch Money asset."""

    __table__: ClassVar[str] = "assets"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    id: Annotated[int, Field(db_type="INTEGER", description="Asset ID")]
    name: Annotated[str, Field(db_type="VARCHAR", description="Asset name")]
    type_name: Annotated[str, Field(db_type="VARCHAR", description="Asset type")]
    balance: Annotated[float, Field(db_type="DOUBLE", description="Current balance")] = 0.0
    currency: Annotated[str, Field(db_type="VARCHAR", description="Currency code")] = ""
    institution_name: Annotated[str | None, Field(db_type="VARCHAR", description="Institution name")] = None
    created_at: Annotated[str | None, Field(db_type="TIMESTAMP", description="Creation timestamp")] = None


@dataclass
class PlaidAccount:
    """Lunch Money Plaid account."""

    __table__: ClassVar[str] = "plaid_accounts"
    __pk__: ClassVar[tuple[str, ...]] = ("id",)
    __kind__: ClassVar[TableKind] = "snapshot"

    id: Annotated[int, Field(db_type="INTEGER", description="Plaid account ID")]
    name: Annotated[str, Field(db_type="VARCHAR", description="Account name")]
    type: Annotated[str, Field(db_type="VARCHAR", description="Account type")]
    subtype: Annotated[str, Field(db_type="VARCHAR", description="Account subtype")]
    institution_name: Annotated[str, Field(db_type="VARCHAR", description="Institution name")]
    status: Annotated[str, Field(db_type="VARCHAR", description="Account status")]
    balance: Annotated[float | None, Field(db_type="DOUBLE", description="Current balance")] = None
    currency: Annotated[str, Field(db_type="VARCHAR", description="Currency code")] = ""
    date_linked: Annotated[str, Field(db_type="DATE", description="Date linked")] = ""
