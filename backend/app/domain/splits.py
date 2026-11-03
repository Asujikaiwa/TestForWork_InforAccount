"""Split allocation and balance calculation (pure functions)."""

from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal

from app.domain.money import format_amount, from_cents, parse_amount, to_cents
from app.errors import EmptySplit, InvalidRequest, SharesMismatch

ZERO = Decimal("0.00")


def allocate_equal(amount: Decimal, members: Sequence[str]) -> list[tuple[str, Decimal]]:
    """Split equally; leftover satang go one at a time in the order listed.

    100.00 among [alice, bob, carol] -> 33.34, 33.33, 33.33.
    Works in integer satang so no rounding mode is involved at all.
    """
    if not members:
        raise EmptySplit("Choose at least one member to split with.")
    if len(set(members)) != len(members):
        raise InvalidRequest("A member is listed more than once in the split.")
    total = to_cents(amount)
    base, remainder = divmod(total, len(members))
    return [
        (member, from_cents(base + (1 if index < remainder else 0)))
        for index, member in enumerate(members)
    ]


def allocate_exact(amount: Decimal, shares: Mapping[str, str]) -> list[tuple[str, Decimal]]:
    """Validate an exact split: every share is a valid amount and they sum to the total."""
    if not shares:
        raise EmptySplit("Give at least one share.")
    parsed = [
        (member, parse_amount(value, field=f"split.shares.{member}"))
        for member, value in shares.items()
    ]
    shares_total = sum((share for _, share in parsed), ZERO)
    if shares_total != amount:
        raise SharesMismatch(
            f"The shares add up to {format_amount(shares_total)} "
            f"but the amount is {format_amount(amount)}.",
            {"amount": format_amount(amount), "shares_total": format_amount(shares_total)},
        )
    return parsed


def compute_balances(
    members: Sequence[str],
    paid: Mapping[str, Decimal],
    owed: Mapping[str, Decimal],
    sent: Mapping[str, Decimal] | None = None,
    received: Mapping[str, Decimal] | None = None,
) -> list[tuple[str, Decimal]]:
    """Net balance per member.

    balance = paid for expenses - own shares + repayments sent - repayments received

    Positive = the group owes them. Every expense's shares sum to its amount,
    and every repayment is sent by one member and received by another, so the
    balances always sum to exactly 0.00.
    """
    sent = sent or {}
    received = received or {}
    return [
        (
            m,
            paid.get(m, ZERO) - owed.get(m, ZERO) + sent.get(m, ZERO) - received.get(m, ZERO),
        )
        for m in members
    ]


def total(values: Iterable[Decimal]) -> Decimal:
    return sum(values, ZERO)
