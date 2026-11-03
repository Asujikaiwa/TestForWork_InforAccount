"""Request and response shapes (see docs/API_CONTRACT.md).

Money fields are typed `str` on purpose: Pydantic does not coerce JSON numbers
to str, so `"amount": 1000.5` is rejected before a float can sneak in.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
MoneyStr = Annotated[str, StringConstraints(max_length=32)]


class EqualSplit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["equal"]
    members: list[Username]


class ExactSplit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["exact"]
    shares: dict[Username, MoneyStr]


class ExpenseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    paid_by: Username
    amount: MoneyStr
    split: Annotated[EqualSplit | ExactSplit, Field(discriminator="type")]


class GroupOut(BaseModel):
    id: int
    name: str


class GroupDetailOut(GroupOut):
    members: list[str]


class ShareOut(BaseModel):
    member: str
    amount: str


class ExpenseOut(BaseModel):
    id: int
    group_id: int
    description: str
    paid_by: str
    amount: str
    split_type: Literal["equal", "exact"]
    shares: list[ShareOut]
    created_by: str
    created_at: datetime


class BalanceOut(BaseModel):
    member: str
    balance: str


class BalancesOut(BaseModel):
    group_id: int
    balances: list[BalanceOut]


class SettlementOut(BaseModel):
    """One suggested payment: `from` pays `to` the amount."""

    model_config = ConfigDict(populate_by_name=True)
    from_: str = Field(alias="from")
    to: str
    amount: str


class SettleUpOut(BaseModel):
    group_id: int
    payments: list[SettlementOut]
