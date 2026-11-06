from sqlalchemy import create_engine, inspect


def test_fresh_database_migrates_to_current_schema(tmp_path, monkeypatch):
    database_path = tmp_path / "migration-test.sqlite"
    monkeypatch.setenv("MIGRATION_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")

    from alembic import command
    from alembic.config import Config

    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.check(config)

    inspector = inspect(create_engine(f"sqlite:///{database_path.as_posix()}"))
    assert {
        "alembic_version",
        "users",
        "items",
        "stock_logs",
        "employees",
        "sales",
        "audit_logs",
        "purchase_orders",
    }.issubset(inspector.get_table_names())
    order_columns = {column["name"] for column in inspector.get_columns("purchase_orders")}
    assert {
        "status",
        "ordered_at",
        "received_at",
        "cancelled_at",
        "item_name",
        "supplier",
        "unit",
    }.issubset(order_columns)
