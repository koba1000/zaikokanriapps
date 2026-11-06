"""Add order lifecycle tracking."""

import sqlalchemy as sa
from alembic import op

revision = "0002_purchase_orders"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("item_name", sa.String(length=100), nullable=False),
        sa.Column("supplier", sa.String(length=100), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("ordered_at", sa.DateTime(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('ordered', 'received', 'cancelled')",
            name="ck_purchase_order_status",
        ),
    )
    op.create_index(
        "uq_purchase_orders_open_item",
        "purchase_orders",
        ["item_id"],
        unique=True,
        sqlite_where=sa.text("status = 'ordered'"),
        postgresql_where=sa.text("status = 'ordered'"),
    )


def downgrade() -> None:
    op.drop_index("uq_purchase_orders_open_item", table_name="purchase_orders")
    op.drop_table("purchase_orders")
