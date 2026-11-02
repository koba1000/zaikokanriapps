from datetime import UTC, date, datetime
from decimal import Decimal

from flask_login import UserMixin
from sqlalchemy import Date, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))
    active: Mapped[bool] = mapped_column(default=True)
    must_change_password: Mapped[bool] = mapped_column(default=True)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # パスワード変更・無効化で加算し、既存セッションを全て失効させる
    session_version: Mapped[int] = mapped_column(Integer, default=0)

    @property
    def is_active(self) -> bool:
        return self.active

    def get_id(self) -> str:
        return f"{self.id}:{self.session_version}"


class Item(db.Model):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    unit: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    reorder_point: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    order_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    supplier: Mapped[str] = mapped_column(String(100), default="")
    last_ordered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def needs_order(self) -> bool:
        return self.quantity <= self.reorder_point


class StockLog(db.Model):
    __tablename__ = "stock_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    before: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    after: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Employee(db.Model):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    address_encrypted: Mapped[bytes] = mapped_column(LargeBinary)


class Sale(db.Model):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True)
    amount: Mapped[int] = mapped_column(Integer)


class AuditLog(db.Model):
    """個人情報・秘密情報は記録しない。ユーザーIDと対象IDのみ。"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str] = mapped_column(String(64), default="")
