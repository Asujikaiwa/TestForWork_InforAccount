"""Unit tests for the pure business rules (no database needed)."""

from decimal import Decimal

import pytest

from app.domain.money import format_amount, parse_amount
from app.domain.splits import allocate_equal, allocate_exact, compute_balances, total
from app.errors import AmountPrecision, EmptySplit, InvalidAmount, InvalidRequest, SharesMismatch

D = Decimal


class TestParseAmount:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [("1000.00", "1000.00"), ("1000", "1000.00"), ("0.01", "0.01"), ("12.5", "12.50")],
    )
    def test_valid(self, value, expected):
        assert parse_amount(value) == D(expected)

    def test_three_decimal_places_rejected(self):
        with pytest.raises(AmountPrecision):
            parse_amount("10.005")

    @pytest.mark.parametrize(
        "value", ["0", "0.00", "-5", "abc", "1e3", "", "1,000", "NaN", "๑๐๐", "+5", " . "]
    )
    def test_invalid(self, value):
        with pytest.raises(InvalidAmount):
            parse_amount(value)

    def test_too_large(self):
        with pytest.raises(InvalidAmount):
            parse_amount("10000000000.00")

    def test_format_always_two_places(self):
        assert format_amount(D("1000")) == "1000.00"
        assert format_amount(D("-333.33")) == "-333.33"


class TestEqualSplit:
    def test_100_among_three(self):
        shares = allocate_equal(D("100.00"), ["alice", "bob", "carol"])
        assert shares == [("alice", D("33.34")), ("bob", D("33.33")), ("carol", D("33.33"))]

    def test_leftover_follows_listed_order(self):
        shares = allocate_equal(D("0.05"), ["carol", "alice", "bob"])
        assert shares == [("carol", D("0.02")), ("alice", D("0.02")), ("bob", D("0.01"))]

    @pytest.mark.parametrize("amount", ["0.01", "0.99", "1.00", "100.00", "1000.01", "9999999.99"])
    @pytest.mark.parametrize("n", [1, 2, 3, 4, 7])
    def test_always_sums_to_amount(self, amount, n):
        shares = allocate_equal(D(amount), [f"m{i}" for i in range(n)])
        assert total(s for _, s in shares) == D(amount)

    def test_empty(self):
        with pytest.raises(EmptySplit):
            allocate_equal(D("10.00"), [])

    def test_duplicate_member(self):
        with pytest.raises(InvalidRequest):
            allocate_equal(D("10.00"), ["alice", "alice"])


class TestExactSplit:
    def test_valid(self):
        shares = allocate_exact(D("1000.00"), {"alice": "500.00", "bob": "300", "carol": "200.00"})
        assert shares == [("alice", D("500.00")), ("bob", D("300.00")), ("carol", D("200.00"))]

    def test_not_summing_to_amount_rejected(self):
        with pytest.raises(SharesMismatch) as exc:
            allocate_exact(D("1000.00"), {"alice": "500.00", "bob": "300.00"})
        assert exc.value.details == {"amount": "1000.00", "shares_total": "800.00"}

    def test_share_precision_checked(self):
        with pytest.raises(AmountPrecision):
            allocate_exact(D("1.00"), {"alice": "0.995", "bob": "0.005"})


def test_balances_example_from_brief():
    shares = allocate_equal(D("1000.00"), ["alice", "bob", "carol"])
    balances = compute_balances(
        ["alice", "bob", "carol"], paid={"alice": D("1000.00")}, owed=dict(shares)
    )
    assert balances == [("alice", D("666.66")), ("bob", D("-333.33")), ("carol", D("-333.33"))]
    assert total(b for _, b in balances) == D("0.00")
