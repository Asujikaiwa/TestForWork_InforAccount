"""Database tables. Money columns are NUMERIC(12,2) and map to Python Decimal."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

Money = Numeric(12, 2, asdecimal=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))

    members: Mapped[list["GroupMember"]] = relationship(
        order_by="GroupMember.position", lazy="selectin"
    )


class GroupMember(Base):
    __tablename__ = "group_members"

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    # Stable display order of members within the group.
    position: Mapped[int] = mapped_column(Integer)

    user: Mapped[User] = relationship(lazy="joined")


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        CheckConstraint("split_type IN ('equal', 'exact')", name="ck_expenses_split_type"),
        # The idempotency guarantee lives in the database, not in application code:
        # two concurrent inserts with the same key cannot both succeed.
        # NULL keys never conflict with each other, so requests without a key
        # are simply not deduplicated.
        UniqueConstraint("group_id", "idempotency_key", name="uq_expenses_group_idempotency_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    description: Mapped[str] = mapped_column(String(200))
    paid_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[Decimal] = mapped_column(Money)
    split_type: Mapped[str] = mapped_column(String(10))
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    idempotency_key: Mapped[str | None] = mapped_column(String(255))
    # SHA-256 of the normalised request, to detect a key reused for a different body.
    request_hash: Mapped[str | None] = mapped_column(String(64))
    # Soft delete: the row stays, balances ignore it.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    paid_by: Mapped[User] = relationship(foreign_keys=[paid_by_id], lazy="joined")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id], lazy="joined")
    shares: Mapped[list["ExpenseShare"]] = relationship(
        order_by="ExpenseShare.position", lazy="selectin"
    )


class ExpenseShare(Base):
    __tablename__ = "expense_shares"
    __table_args__ = (CheckConstraint("amount >= 0", name="ck_expense_shares_amount"),)

    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    # Order the split listed the members in; leftover satang follow this order.
    position: Mapped[int] = mapped_column(Integer)
    amount: Mapped[Decimal] = mapped_column(Money)

    user: Mapped[User] = relationship(lazy="joined")


class Payment(Base):
    """A repayment between two members. Like expenses, it cannot be edited."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        CheckConstraint("from_user_id <> to_user_id", name="ck_payments_not_to_self"),
        UniqueConstraint("group_id", "idempotency_key", name="uq_payments_group_idempotency_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[Decimal] = mapped_column(Money)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    idempotency_key: Mapped[str | None] = mapped_column(String(255))
    request_hash: Mapped[str | None] = mapped_column(String(64))

    from_user: Mapped[User] = relationship(foreign_keys=[from_user_id], lazy="joined")
    to_user: Mapped[User] = relationship(foreign_keys=[to_user_id], lazy="joined")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id], lazy="joined")
