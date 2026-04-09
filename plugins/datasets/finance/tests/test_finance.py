import duckdb

from shenas_datasets.finance import (
    ALL_TABLES,
    DailySpending,
    FinanceSchema,
    MonthlyCategory,
    MonthlyOverview,
    Transaction,
)


class TestMetrics:
    def test_all_tables_count(self) -> None:
        assert len(ALL_TABLES) == 4

    def test_canonical_table_names(self) -> None:
        assert set(FinanceSchema.tables) == {"transactions", "daily_spending", "monthly_category", "monthly_overview"}

    def test_each_table_has_pk(self) -> None:
        for cls in ALL_TABLES:
            assert hasattr(cls._Meta, "name")
            assert hasattr(cls._Meta, "pk")
            assert len(cls._Meta.pk) >= 2

    def test_transaction_fields(self) -> None:
        field_names = [f.name for f in Transaction.__dataclass_fields__.values()]
        assert "id" in field_names
        assert "amount" in field_names
        assert "payee" in field_names
        assert "category" in field_names
        assert "is_income" in field_names

    def test_daily_spending_fields(self) -> None:
        field_names = [f.name for f in DailySpending.__dataclass_fields__.values()]
        assert "total_spent" in field_names
        assert "total_income" in field_names
        assert "transaction_count" in field_names

    def test_monthly_overview_fields(self) -> None:
        field_names = [f.name for f in MonthlyOverview.__dataclass_fields__.values()]
        assert "net" in field_names
        assert "savings_rate" in field_names

    def test_monthly_category_pk(self) -> None:
        assert MonthlyCategory._Meta.pk == ("month", "category", "source")


class TestDDL:
    def test_generate_ddl_transactions(self) -> None:
        ddl = Transaction.to_ddl()
        assert "CREATE TABLE IF NOT EXISTS metrics.transactions" in ddl
        assert "id VARCHAR NOT NULL" in ddl
        assert "source VARCHAR NOT NULL" in ddl
        assert "amount DOUBLE" in ddl
        assert "PRIMARY KEY (id, source)" in ddl

    def test_generate_ddl_all_tables(self) -> None:
        for cls in ALL_TABLES:
            ddl = cls.to_ddl()
            assert f"metrics.{cls._Meta.name}" in ddl
            assert "PRIMARY KEY" in ddl

    def test_ensure_schema_creates_tables(self) -> None:
        con = duckdb.connect(":memory:")
        FinanceSchema.ensure(con)
        tables = {
            r[0]
            for r in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'metrics'").fetchall()
        }
        assert tables == set(FinanceSchema.tables)
        con.close()

    def test_ensure_schema_idempotent(self) -> None:
        con = duckdb.connect(":memory:")
        FinanceSchema.ensure(con)
        FinanceSchema.ensure(con)
        tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'metrics'").fetchall()
        assert len(tables) == 4
        con.close()


class TestIntrospect:
    def test_schema_metadata_returns_all_tables(self) -> None:
        meta = FinanceSchema.metadata()
        assert len(meta) == 4

    def test_table_metadata_structure(self) -> None:
        meta = Transaction.table_metadata()
        assert meta["table"] == "transactions"
        assert meta["primary_key"] == ["id", "source"]
        assert len(meta["columns"]) == 12

    def test_column_metadata_has_description(self) -> None:
        meta = Transaction.table_metadata()
        amount = next(c for c in meta["columns"] if c["name"] == "amount")
        assert "description" in amount
        assert amount["db_type"] == "DOUBLE"

    def test_column_metadata_has_interpretation(self) -> None:
        meta = DailySpending.table_metadata()
        total_spent = next(c for c in meta["columns"] if c["name"] == "total_spent")
        assert "interpretation" in total_spent

    def test_savings_rate_has_range(self) -> None:
        meta = MonthlyOverview.table_metadata()
        savings = next(c for c in meta["columns"] if c["name"] == "savings_rate")
        assert savings.get("value_range") == (-100, 100)

    def test_nullable_flag(self) -> None:
        meta = Transaction.table_metadata()
        id_col = next(c for c in meta["columns"] if c["name"] == "id")
        amount_col = next(c for c in meta["columns"] if c["name"] == "amount")
        assert id_col["nullable"] is False
        assert amount_col["nullable"] is True

    def test_all_metric_fields_have_metadata(self) -> None:
        for table_meta in FinanceSchema.metadata():
            for col in table_meta["columns"]:
                assert "db_type" in col, f"{table_meta['table']}.{col['name']} missing db_type"
                assert "description" in col, f"{table_meta['table']}.{col['name']} missing description"


class TestSchema:
    def test_schema_name(self) -> None:
        assert FinanceSchema.name == "finance"

    def test_schema_tables(self) -> None:
        assert set(FinanceSchema.tables) == {"transactions", "daily_spending", "monthly_category", "monthly_overview"}
