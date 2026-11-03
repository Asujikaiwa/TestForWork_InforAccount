"""Money parsing.

Amounts arrive as strings ("1000.00") and become Decimal with exactly two
places. float is never involved: a JSON number is rejected at the schema layer,
and Decimal is built from the string itself.
"""

import re
from decimal import Decimal

from app.errors import AmountPrecision, InvalidAmount

CENT = Decimal("0.01")
# Largest value of NUMERIC(12,2).
MAX_AMOUNT = Decimal("9999999999.99")

# [0-9], not \d: in Python \d also matches non-ASCII digits such as Thai "๑๐๐".
_AMOUNT_RE = re.compile(r"(?P<whole>[0-9]+)(?:\.(?P<fraction>[0-9]+))?")


def parse_amount(value: str, field: str = "amount") -> Decimal:
    """Parse a positive amount with at most 2 decimal places.

    "10.005" -> AmountPrecision, "0" / "-1" / "abc" / "1e3" -> InvalidAmount.
    """
    match = _AMOUNT_RE.fullmatch(value.strip())
    if match is None:
        raise InvalidAmount(
            f'{field} must be a positive number such as "1000.00".', {"field": field}
        )
    fraction = match.group("fraction") or ""
    if len(fraction) > 2:
        raise AmountPrecision(
            f"{field} has more than 2 decimal places.", {"field": field, "value": value}
        )
    amount = Decimal(value.strip()).quantize(CENT)
    if amount <= 0:
        raise InvalidAmount(f"{field} must be greater than 0.", {"field": field})
    if amount > MAX_AMOUNT:
        raise InvalidAmount(f"{field} is too large (max {MAX_AMOUNT}).", {"field": field})
    return amount


def to_cents(amount: Decimal) -> int:
    """Decimal("333.34") -> 33334. Exact, because amounts have 2 places."""
    return int(amount.quantize(CENT) * 100)


def from_cents(cents: int) -> Decimal:
    """33334 -> Decimal("333.34")."""
    return (Decimal(cents) / 100).quantize(CENT)


def format_amount(amount: Decimal) -> str:
    """Always two places in responses: Decimal("1000") -> "1000.00"."""
    return f"{amount.quantize(CENT):f}"
