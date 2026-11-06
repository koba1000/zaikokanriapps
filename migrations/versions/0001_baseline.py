"""Baseline schema for databases originally initialized with db.create_all."""

import sqlalchemy as sa
from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("session_version", sa.Integer(), nullable=False),
    )
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("reorder_point", sa.Numeric(10, 2), nullable=False),
        sa.Column("order_quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("supplier", sa.String(length=100), nullable=False),
        sa.Column("last_ordered_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("address_encrypted", sa.LargeBinary(), nullable=False),
    )
    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False, unique=True),
        sa.Column("amount", sa.Integer(), nullable=False),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target", sa.String(length=64), nullable=False),
    )
    op.create_table(
        "stock_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("before", sa.Numeric(10, 2), nullable=False),
        sa.Column("after", sa.Numeric(10, 2), nullable=False),
        sa.Column("at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("stock_logs")
    op.drop_table("audit_logs")
    op.drop_table("sales")
    op.drop_table("employees")
    op.drop_table("items")
    op.drop_table("users")
