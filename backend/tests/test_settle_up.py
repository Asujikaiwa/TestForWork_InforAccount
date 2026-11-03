"""Unit tests for settlement suggestions (pure function, no database)."""

import random
from decimal import Decimal

import pytest

from app.domain.settle_up import _greedy, settle_up

D = Decimal


def apply(balances, transfers):
    """Balances after the suggested payments are made."""
    result = dict(balances)
    for payer, payee, amount in transfers:
        assert amount > 0
        result[payer] += amount  # paying back raises the payer's balance
        result[payee] -= amount
    return result


def fewest_payments_brute_force(cents):
    """n - (max number of zero-sum groups), by trying every partition."""
    people = [c for c in cents if c != 0]

    def max_groups(remaining):
        if not remaining:
            return 0
        first, rest = remaining[0], remaining[1:]
        best = 0
        for mask in range(1 << len(rest)):
            group = [first] + [rest[i] for i in range(len(rest)) if mask >> i & 1]
            if sum(group) == 0:
                others = [rest[i] for i in range(len(rest)) if not mask >> i & 1]
                best = max(best, 1 + max_groups(others))
        return best

    return len(people) - max_groups(people)


def test_example_from_brief():
    balances = [("alice", D("666.66")), ("bob", D("-333.33")), ("carol", D("-333.33"))]
    assert settle_up(balances) == [
        ("bob", "alice", D("333.33")),
        ("carol", "alice", D("333.33")),
    ]


def test_nothing_to_settle():
    assert settle_up([("alice", D("0.00")), ("bob", D("0.00"))]) == []
    assert settle_up([]) == []


def test_finds_fewer_payments_than_the_plain_greedy_rule():
    """a(-5) b(-4) c(-4) d(+5) e(+8).

    Greedy alone: a pays e 5, b pays e 3, b pays d 1, c pays d 4 = 4 payments.
    Optimal: {a, d} and {b, c, e} each sum to zero: a->d, b->e, c->e = 3 payments.
    """
    cents = [-500, -400, -400, 500, 800]
    names = ["a", "b", "c", "d", "e"]
    assert len(_greedy(list(zip(names, cents, strict=True)))) == 4  # the naive answer

    balances = [(n, Decimal(c) / 100) for n, c in zip(names, cents, strict=True)]
    transfers = settle_up(balances)

    assert len(transfers) == 3
    assert sorted(transfers) == [
        ("a", "d", D("5.00")),
        ("b", "e", D("4.00")),
        ("c", "e", D("4.00")),
    ]
    assert all(v == 0 for v in apply(balances, transfers).values())


@pytest.mark.parametrize("seed", range(200))
def test_matches_brute_force_minimum_on_random_groups(seed):
    rng = random.Random(seed)
    n = rng.randint(2, 7)
    # Small values make zero-sum subgroups likely, which is where greedy goes wrong.
    cents = [rng.choice([-300, -200, -100, -1, 1, 100, 200, 300]) for _ in range(n - 1)]
    cents.append(-sum(cents))
    balances = [(f"m{i}", Decimal(c) / 100) for i, c in enumerate(cents)]

    transfers = settle_up(balances)

    assert all(v == 0 for v in apply(balances, transfers).values())
    assert len(transfers) == fewest_payments_brute_force(cents)
    for payer, payee, _ in transfers:
        assert dict(balances)[payer] < 0 < dict(balances)[payee]


def test_large_group_falls_back_but_still_settles():
    rng = random.Random(1)
    cents = [rng.randint(-50_000, 50_000) for _ in range(19)]
    cents.append(-sum(cents))
    balances = [(f"m{i}", Decimal(c) / 100) for i, c in enumerate(cents)]
    transfers = settle_up(balances)
    assert all(v == 0 for v in apply(balances, transfers).values())
    assert len(transfers) <= len([c for c in cents if c != 0]) - 1


def test_rejects_balances_that_do_not_sum_to_zero():
    with pytest.raises(ValueError):
        settle_up([("a", D("1.00")), ("b", D("-0.99"))])
