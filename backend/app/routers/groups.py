"""HTTP routes. Thin: parse the request, call a service, shape the response."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app import repository as repo
from app import services
from app.deps import CurrentUser, MemberGroup, SessionDep, idempotency_key
from app.domain.money import format_amount
from app.models import Expense
from app.schemas import (
    BalanceOut,
    BalancesOut,
    ExpenseCreate,
    ExpenseOut,
    GroupDetailOut,
    GroupOut,
    SettlementOut,
    SettleUpOut,
    ShareOut,
)

router = APIRouter(prefix="/groups", tags=["groups"])


def expense_out(expense: Expense) -> ExpenseOut:
    return ExpenseOut(
        id=expense.id,
        group_id=expense.group_id,
        description=expense.description,
        paid_by=expense.paid_by.username,
        amount=format_amount(expense.amount),
        split_type=expense.split_type,  # type: ignore[arg-type]
        shares=[
            ShareOut(member=s.user.username, amount=format_amount(s.amount)) for s in expense.shares
        ],
        created_by=expense.created_by.username,
        created_at=expense.created_at,
    )


@router.get("", response_model=list[GroupOut])
def list_groups(session: SessionDep, user: CurrentUser) -> list[GroupOut]:
    return [GroupOut(id=g.id, name=g.name) for g in repo.list_groups_for_user(session, user.id)]


@router.get("/{group_id}", response_model=GroupDetailOut)
def get_group(group: MemberGroup) -> GroupDetailOut:
    return GroupDetailOut(id=group.id, name=group.name, members=services.member_names(group))


@router.post(
    "/{group_id}/expenses",
    response_model=ExpenseOut,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"description": "Idempotent replay: the original expense"}},
)
def create_expense(
    payload: ExpenseCreate,
    response: Response,
    session: SessionDep,
    user: CurrentUser,
    group: MemberGroup,
    key: Annotated[str | None, Depends(idempotency_key)],
) -> ExpenseOut:
    expense, created = services.create_expense(session, user, group, payload, key)
    if not created:
        response.status_code = status.HTTP_200_OK
    return expense_out(expense)


@router.get("/{group_id}/expenses", response_model=list[ExpenseOut])
def list_expenses(session: SessionDep, group: MemberGroup) -> list[ExpenseOut]:
    return [expense_out(e) for e in repo.list_active_expenses(session, group.id)]


@router.delete("/{group_id}/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int, session: SessionDep, user: CurrentUser, group: MemberGroup
) -> Response:
    services.delete_expense(session, user, group, expense_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{group_id}/balances", response_model=BalancesOut)
def get_balances(session: SessionDep, group: MemberGroup) -> BalancesOut:
    return BalancesOut(
        group_id=group.id,
        balances=[
            BalanceOut(member=m, balance=format_amount(b))
            for m, b in services.group_balances(session, group)
        ],
    )


@router.get("/{group_id}/settle-up", response_model=SettleUpOut)
def get_settle_up(session: SessionDep, group: MemberGroup) -> SettleUpOut:
    return SettleUpOut(
        group_id=group.id,
        payments=[
            SettlementOut(from_=payer, to=payee, amount=format_amount(amount))
            for payer, payee, amount in services.group_settlements(session, group)
        ],
    )
