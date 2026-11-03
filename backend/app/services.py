"""Business rules that need the database: membership, idempotency, soft delete."""

import hashlib
import json
from decimal import Decimal

from sqlalchemy.orm import Session

from app import repository as repo
from app.domain.money import format_amount, parse_amount
from app.domain.settle_up import Transfer, settle_up
from app.domain.splits import allocate_equal, allocate_exact, compute_balances
from app.errors import (
    ExpenseNotFound,
    IdempotencyKeyReused,
    MemberNotInGroup,
    NotPayer,
)
from app.models import Expense, Group, User
from app.schemas import EqualSplit, ExpenseCreate


def member_names(group: Group) -> list[str]:
    return [m.user.username for m in group.members]


def create_expense(
    session: Session,
    user: User,
    group: Group,
    payload: ExpenseCreate,
    idempotency_key: str | None,
) -> tuple[Expense, bool]:
    """Validate and store an expense. Returns (expense, created).

    created=False means the Idempotency-Key was already used in this group and
    the original expense is returned unchanged.
    """
    ids = {m.user.username: m.user_id for m in group.members}

    amount = parse_amount(payload.amount)
    split_members = (
        payload.split.members
        if isinstance(payload.split, EqualSplit)
        else list(payload.split.shares)
    )
    outsiders = [name for name in [payload.paid_by, *split_members] if name not in ids]
    if outsiders:
        unique = list(dict.fromkeys(outsiders))
        raise MemberNotInGroup(
            f"Not a member of this group: {', '.join(unique)}.", {"members": unique}
        )

    if isinstance(payload.split, EqualSplit):
        shares = allocate_equal(amount, payload.split.members)
    else:
        shares = allocate_exact(amount, payload.split.shares)

    request_hash = _request_hash(payload, amount, shares)
    values = {
        "group_id": group.id,
        "description": payload.description,
        "paid_by_id": ids[payload.paid_by],
        "amount": amount,
        "split_type": payload.split.type,
        "created_by_id": user.id,
        "idempotency_key": idempotency_key,
        "request_hash": request_hash if idempotency_key else None,
    }

    expense_id = repo.insert_expense(session, values)
    if expense_id is None:
        # Lost the race (or a plain retry): the key already exists in this group.
        # Nothing was written by this transaction, so there is nothing to undo.
        existing = repo.get_expense_by_key(session, group.id, idempotency_key or "")
        if existing is None:  # pragma: no cover - cannot happen with the unique constraint
            raise RuntimeError("idempotency conflict without a matching row")
        if existing.request_hash != request_hash:
            raise IdempotencyKeyReused(
                "This Idempotency-Key was already used for a different expense."
            )
        return existing, False

    repo.insert_shares(session, expense_id, [(ids[name], share) for name, share in shares])
    session.commit()
    expense = repo.get_expense(session, group.id, expense_id)
    assert expense is not None
    return expense, True


def delete_expense(session: Session, user: User, group: Group, expense_id: int) -> None:
    expense = repo.get_active_expense(session, group.id, expense_id)
    if expense is None:
        raise ExpenseNotFound("Expense not found.")
    if expense.paid_by_id != user.id:
        raise NotPayer("Only the payer can delete this expense.")
    if not repo.soft_delete_expense(session, expense.id, user.id):
        raise ExpenseNotFound("Expense not found.")
    session.commit()


def group_balances(session: Session, group: Group) -> list[tuple[str, Decimal]]:
    paid_by_id, owed_by_id = repo.paid_and_owed(session, group.id)
    names = {m.user_id: m.user.username for m in group.members}
    paid = {names[uid]: total for uid, total in paid_by_id.items()}
    owed = {names[uid]: total for uid, total in owed_by_id.items()}
    return compute_balances(member_names(group), paid, owed)


def group_settlements(session: Session, group: Group) -> list[Transfer]:
    """Fewest payments that bring every member of the group to 0.00."""
    return settle_up(group_balances(session, group))


def _request_hash(
    payload: ExpenseCreate, amount: Decimal, shares: list[tuple[str, Decimal]]
) -> str:
    """Fingerprint of the *normalised* request ("1000" and "1000.00" hash the same)."""
    canonical = {
        "description": payload.description,
        "paid_by": payload.paid_by,
        "amount": format_amount(amount),
        "split_type": payload.split.type,
        "shares": [[name, format_amount(share)] for name, share in shares],
    }
    encoded = json.dumps(canonical, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode()).hexdigest()
