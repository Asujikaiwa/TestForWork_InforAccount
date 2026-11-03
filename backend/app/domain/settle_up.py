"""Settlement suggestions: the fewest payments that bring every balance to 0.00.

Why this is not just "largest debtor pays largest creditor":
that greedy rule always finishes, but it can use more payments than needed.

The fewest payments for n members with non-zero balances is n - k, where k is
the largest number of groups the members can be split into such that each
group's balances sum to zero (each group then settles internally with
size - 1 payments, and no group can do better). So we:

1. find that best split into zero-sum groups (exact search over subsets,
   fine for the small groups this app has), then
2. settle each group with the greedy rule, which uses exactly size - 1
   payments inside a group that cannot be split further.

All arithmetic is in integer satang.
"""

from collections.abc import Sequence
from decimal import Decimal

from app.domain.money import from_cents, to_cents

# Above this many members with a non-zero balance, the exact search
# (3^n steps) gets slow; fall back to the greedy rule for everyone.
MAX_EXACT_MEMBERS = 12

Transfer = tuple[str, str, Decimal]  # (from, to, amount)


def settle_up(balances: Sequence[tuple[str, Decimal]]) -> list[Transfer]:
    """Payments that bring every balance to zero, as (payer, payee, amount).

    `balances` are net balances (positive = is owed money) and must sum to zero.
    """
    people = [(member, to_cents(balance)) for member, balance in balances if balance != 0]
    if sum(cents for _, cents in people) != 0:
        raise ValueError("balances must sum to zero")
    if not people:
        return []

    groups = _best_zero_sum_groups(people) if len(people) <= MAX_EXACT_MEMBERS else [people]
    transfers: list[Transfer] = []
    for group in groups:
        transfers.extend(
            (payer, payee, from_cents(cents)) for payer, payee, cents in _greedy(group)
        )
    return transfers


def _best_zero_sum_groups(people: list[tuple[str, int]]) -> list[list[tuple[str, int]]]:
    """Split people into the largest possible number of zero-sum groups.

    Subsets are bitmasks: bit i set = people[i] is in the subset.
    best[mask] = most zero-sum groups that exactly cover `mask`
    (only defined for masks whose balances sum to zero).
    """
    n = len(people)
    full = (1 << n) - 1

    sums = [0] * (full + 1)
    for mask in range(1, full + 1):
        lowest = mask & -mask
        sums[mask] = sums[mask ^ lowest] + people[lowest.bit_length() - 1][1]

    best = {0: 0}
    choice: dict[int, int] = {}
    for mask in range(1, full + 1):
        if sums[mask] != 0:
            continue
        # The group containing the lowest member of `mask`, plus anything else in `mask`.
        lowest = mask & -mask
        rest = mask ^ lowest
        sub = rest
        while True:
            group = sub | lowest
            if sums[group] == 0:
                # mask ^ group also sums to zero and is smaller, so best[] has it.
                count = 1 + best[mask ^ group]
                if count > best.get(mask, -1):
                    best[mask] = count
                    choice[mask] = group
            if sub == 0:
                break
            sub = (sub - 1) & rest

    groups = []
    mask = full
    while mask:
        group = choice[mask]
        groups.append([people[i] for i in range(n) if group >> i & 1])
        mask ^= group
    return groups


def _greedy(group: list[tuple[str, int]]) -> list[tuple[str, str, int]]:
    """Largest debtor pays largest creditor until everyone is at zero.

    Each payment brings at least one person to zero, so a group of m people
    needs at most m - 1 payments. Ties keep the original member order.
    """
    debtors = [[member, -cents] for member, cents in group if cents < 0]
    creditors = [[member, cents] for member, cents in group if cents > 0]
    transfers = []
    while debtors and creditors:
        debtors.sort(key=lambda d: -d[1])
        creditors.sort(key=lambda c: -c[1])
        debtor, creditor = debtors[0], creditors[0]
        amount = min(debtor[1], creditor[1])
        transfers.append((debtor[0], creditor[0], amount))
        debtor[1] -= amount
        creditor[1] -= amount
        debtors = [d for d in debtors if d[1] > 0]
        creditors = [c for c in creditors if c[1] > 0]
    return transfers
