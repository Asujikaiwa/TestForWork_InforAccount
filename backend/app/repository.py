"""Data access. SQL lives here; business rules live in app/services.py."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Expense, ExpenseShare, Group, GroupMember, Payment, User


def get_user(session: Session, username: str) -> User | None:
    return session.scalar(select(User).where(User.username == username))


def list_groups_for_user(session: Session, user_id: int) -> list[Group]:
    stmt = (
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user_id)
        .order_by(Group.id)
    )
    return list(session.scalars(stmt))


def get_group_for_member(session: Session, group_id: int, user_id: int) -> Group | None:
    """The group, only if `user_id` is a member. Non-members get None, like a missing group."""
    stmt = (
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(Group.id == group_id, GroupMember.user_id == user_id)
    )
    return session.scalar(stmt)


def insert_expense(session: Session, values: dict) -> int | None:
    """INSERT ... ON CONFLICT (group_id, idempotency_key) DO NOTHING RETURNING id.

    Returns the new id, or None if an expense with the same key already exists
    in the group. When another transaction is inserting the same key at the
    same moment, PostgreSQL makes this statement wait for it to commit or roll
    back, so exactly one of them wins; there is no check-then-insert race.
    """
    stmt = (
        insert(Expense)
        .values(**values)
        .on_conflict_do_nothing(constraint="uq_expenses_group_idempotency_key")
        .returning(Expense.id)
    )
    return session.execute(stmt).scalar_one_or_none()


def insert_shares(session: Session, expense_id: int, shares: list[tuple[int, Decimal]]) -> None:
    session.add_all(
        ExpenseShare(expense_id=expense_id, user_id=user_id, position=position, amount=amount)
        for position, (user_id, amount) in enumerate(shares)
    )


def get_expense_by_key(session: Session, group_id: int, key: str) -> Expense | None:
    return session.scalar(
        select(Expense).where(Expense.group_id == group_id, Expense.idempotency_key == key)
    )


def get_expense(session: Session, group_id: int, expense_id: int) -> Expense | None:
    return session.scalar(
        select(Expense).where(Expense.group_id == group_id, Expense.id == expense_id)
    )


def get_active_expense(session: Session, group_id: int, expense_id: int) -> Expense | None:
    return session.scalar(
        select(Expense).where(
            Expense.group_id == group_id,
            Expense.id == expense_id,
            Expense.deleted_at.is_(None),
        )
    )


def list_active_expenses(session: Session, group_id: int) -> list[Expense]:
    stmt = (
        select(Expense)
        .where(Expense.group_id == group_id, Expense.deleted_at.is_(None))
        .order_by(Expense.created_at.desc(), Expense.id.desc())
    )
    return list(session.scalars(stmt))


def soft_delete_expense(session: Session, expense_id: int, user_id: int) -> bool:
    """Flag as deleted. False if it was already deleted (e.g. a concurrent delete)."""
    result = session.execute(
        update(Expense)
        .where(Expense.id == expense_id, Expense.deleted_at.is_(None))
        .values(deleted_at=datetime.now(UTC), deleted_by_id=user_id)
    )
    return result.rowcount == 1


def paid_and_owed(session: Session, group_id: int) -> tuple[dict[int, Decimal], dict[int, Decimal]]:
    """Per-user totals over active expenses, summed by PostgreSQL in NUMERIC (exact)."""
    active = (Expense.group_id == group_id, Expense.deleted_at.is_(None))
    paid_rows = session.execute(
        select(Expense.paid_by_id, func.sum(Expense.amount))
        .where(*active)
        .group_by(Expense.paid_by_id)
    )
    owed_rows = session.execute(
        select(ExpenseShare.user_id, func.sum(ExpenseShare.amount))
        .join(Expense, Expense.id == ExpenseShare.expense_id)
        .where(*active)
        .group_by(ExpenseShare.user_id)
    )
    paid = {user_id: amount for user_id, amount in paid_rows}
    owed = {user_id: amount for user_id, amount in owed_rows}
    return paid, owed


def insert_payment(session: Session, values: dict) -> int | None:
    """Same idempotent insert as expenses: None if the key was already used in the group."""
    stmt = (
        insert(Payment)
        .values(**values)
        .on_conflict_do_nothing(constraint="uq_payments_group_idempotency_key")
        .returning(Payment.id)
    )
    return session.execute(stmt).scalar_one_or_none()


def get_payment(session: Session, group_id: int, payment_id: int) -> Payment | None:
    return session.scalar(
        select(Payment).where(Payment.group_id == group_id, Payment.id == payment_id)
    )


def get_payment_by_key(session: Session, group_id: int, key: str) -> Payment | None:
    return session.scalar(
        select(Payment).where(Payment.group_id == group_id, Payment.idempotency_key == key)
    )


def list_payments(session: Session, group_id: int) -> list[Payment]:
    stmt = (
        select(Payment)
        .where(Payment.group_id == group_id)
        .order_by(Payment.created_at.desc(), Payment.id.desc())
    )
    return list(session.scalars(stmt))


def sent_and_received(
    session: Session, group_id: int
) -> tuple[dict[int, Decimal], dict[int, Decimal]]:
    """Per-user repayment totals, summed in NUMERIC."""
    sent_rows = session.execute(
        select(Payment.from_user_id, func.sum(Payment.amount))
        .where(Payment.group_id == group_id)
        .group_by(Payment.from_user_id)
    )
    received_rows = session.execute(
        select(Payment.to_user_id, func.sum(Payment.amount))
        .where(Payment.group_id == group_id)
        .group_by(Payment.to_user_id)
    )
    sent = {user_id: amount for user_id, amount in sent_rows}
    received = {user_id: amount for user_id, amount in received_rows}
    return sent, received
