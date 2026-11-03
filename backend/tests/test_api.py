"""API tests against a real database. The six cases required by the brief come first."""

from decimal import Decimal

import pytest
from sqlalchemy import text

from app.db import engine
from tests.conftest import DINNER, balances, post_expense


def total(values) -> Decimal:
    return sum((Decimal(v) for v in values), Decimal("0"))


# --- Required case 1 -----------------------------------------------------------------------
def test_equal_split_of_100_among_three_and_balances_sum_to_zero(client):
    body = {**DINNER, "amount": "100.00"}
    response = post_expense(client, body)

    assert response.status_code == 201, response.text
    shares = {s["member"]: s["amount"] for s in response.json()["shares"]}
    assert shares == {"alice": "33.34", "bob": "33.33", "carol": "33.33"}

    result = balances(client)
    assert result == {"alice": "66.66", "bob": "-33.33", "carol": "-33.33"}
    assert total(result.values()) == Decimal("0.00")


def test_example_from_brief_1000_dinner(client):
    response = post_expense(client, DINNER, key="7f3c2a10-dinner-0001")
    assert response.status_code == 201
    assert [s["amount"] for s in response.json()["shares"]] == ["333.34", "333.33", "333.33"]
    assert balances(client) == {"alice": "666.66", "bob": "-333.33", "carol": "-333.33"}


# --- Required case 2 -----------------------------------------------------------------------
def test_exact_split_not_summing_to_amount_is_rejected(client):
    body = {
        **DINNER,
        "split": {
            "type": "exact",
            "shares": {"alice": "500.00", "bob": "300.00", "carol": "100.00"},
        },
    }
    response = post_expense(client, body)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "SHARES_MISMATCH"
    assert error["details"] == {"amount": "1000.00", "shares_total": "900.00"}
    assert "900.00" in error["message"]
    assert client.get("/groups/1/expenses", headers={"X-User": "alice"}).json() == []


def test_exact_split_summing_to_amount_is_accepted(client):
    body = {
        **DINNER,
        "split": {
            "type": "exact",
            "shares": {"alice": "500.00", "bob": "300.00", "carol": "200.00"},
        },
    }
    assert post_expense(client, body).status_code == 201
    assert balances(client) == {"alice": "500.00", "bob": "-300.00", "carol": "-200.00"}


# --- Required case 3 -----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("field", "body"),
    [
        ("amount", {**DINNER, "amount": "10.005"}),
        (
            "split.shares.alice",
            {
                **DINNER,
                "amount": "1.00",
                "split": {"type": "exact", "shares": {"alice": "0.995", "bob": "0.005"}},
            },
        ),
    ],
)
def test_amount_with_three_decimal_places_is_rejected(client, field, body):
    response = post_expense(client, body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "AMOUNT_PRECISION"
    assert response.json()["error"]["details"]["field"] == field


@pytest.mark.parametrize("amount", ["0", "0.00", "-10.00", "abc", "1e3"])
def test_zero_negative_or_malformed_amount_is_rejected(client, amount):
    response = post_expense(client, {**DINNER, "amount": amount})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_AMOUNT"


def test_amount_sent_as_json_number_is_rejected(client):
    """Floats must never be accepted for money."""
    response = post_expense(client, {**DINNER, "amount": 1000.5})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# --- Required case 4 -----------------------------------------------------------------------
def test_repeated_idempotency_key_creates_only_one_expense(client):
    first = post_expense(client, DINNER, key="dinner-0001")
    second = post_expense(client, DINNER, key="dinner-0001")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json() == first.json()
    assert len(client.get("/groups/1/expenses", headers={"X-User": "alice"}).json()) == 1
    assert balances(client)["alice"] == "666.66"


def test_same_key_in_another_group_is_independent(client):
    lunch = {**DINNER, "paid_by": "bob", "split": {"type": "equal", "members": ["bob", "dan"]}}
    assert post_expense(client, DINNER, key="k1").status_code == 201
    assert post_expense(client, lunch, user="bob", group=2, key="k1").status_code == 201


def test_same_key_with_different_body_is_a_conflict(client):
    assert post_expense(client, DINNER, key="k1").status_code == 201
    response = post_expense(client, {**DINNER, "amount": "999.00"}, key="k1")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_equivalent_body_with_same_key_is_a_replay(client):
    """ "1000" and "1000.00" are the same amount, so this is a retry, not a conflict."""
    assert post_expense(client, DINNER, key="k1").status_code == 201
    assert post_expense(client, {**DINNER, "amount": "1000"}, key="k1").status_code == 200


# --- Required case 5 -----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/groups/2"),
        ("GET", "/groups/2/expenses"),
        ("GET", "/groups/2/balances"),
        ("POST", "/groups/2/expenses"),
        ("DELETE", "/groups/2/expenses/1"),
    ],
)
def test_alice_can_neither_read_nor_write_group_2(client, method, path):
    lunch = {
        "description": "Lunch",
        "paid_by": "bob",
        "amount": "200.00",
        "split": {"type": "equal", "members": ["bob", "dan"]},
    }
    assert post_expense(client, lunch, user="bob", group=2).status_code == 201

    response = client.request(
        method, path, headers={"X-User": "alice"}, json=lunch if method == "POST" else None
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "GROUP_NOT_FOUND"
    # Nothing changed in group 2.
    assert len(client.get("/groups/2/expenses", headers={"X-User": "bob"}).json()) == 1


def test_alice_does_not_see_group_2_in_her_list(client):
    response = client.get("/groups", headers={"X-User": "alice"})
    assert response.json() == [{"id": 1, "name": "Chiang Mai trip"}]


def test_non_member_and_missing_group_look_the_same(client):
    not_member = client.get("/groups/2", headers={"X-User": "alice"})
    missing = client.get("/groups/999", headers={"X-User": "alice"})
    assert not_member.status_code == missing.status_code == 404
    assert not_member.json() == missing.json()


# --- Required case 6 -----------------------------------------------------------------------
def test_only_the_payer_can_delete_an_expense(client):
    expense_id = post_expense(client, DINNER).json()["id"]

    for other in ["bob", "carol"]:
        response = client.delete(f"/groups/1/expenses/{expense_id}", headers={"X-User": other})
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "NOT_PAYER"
    assert balances(client)["alice"] == "666.66"

    response = client.delete(f"/groups/1/expenses/{expense_id}", headers={"X-User": "alice"})
    assert response.status_code == 204


def test_payer_is_who_paid_not_who_recorded(client):
    """carol records an expense that bob paid: bob may delete it, carol may not."""
    body = {**DINNER, "paid_by": "bob"}
    expense_id = post_expense(client, body, user="carol").json()["id"]
    assert (
        client.delete(f"/groups/1/expenses/{expense_id}", headers={"X-User": "carol"}).status_code
        == 403
    )
    assert (
        client.delete(f"/groups/1/expenses/{expense_id}", headers={"X-User": "bob"}).status_code
        == 204
    )


# --- Other rules ---------------------------------------------------------------------------
def test_delete_is_soft_and_excluded_from_balances(client):
    expense_id = post_expense(client, DINNER).json()["id"]
    client.delete(f"/groups/1/expenses/{expense_id}", headers={"X-User": "alice"})

    assert client.get("/groups/1/expenses", headers={"X-User": "alice"}).json() == []
    assert balances(client) == {"alice": "0.00", "bob": "0.00", "carol": "0.00"}
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT deleted_at IS NOT NULL, deleted_by_id FROM expenses WHERE id = :id"),
            {"id": expense_id},
        ).one()
    assert tuple(row) == (True, 1)  # row kept, flagged, and who deleted it

    again = client.delete(f"/groups/1/expenses/{expense_id}", headers={"X-User": "alice"})
    assert again.status_code == 404
    assert again.json()["error"]["code"] == "EXPENSE_NOT_FOUND"


def test_expenses_cannot_be_edited(client):
    expense_id = post_expense(client, DINNER).json()["id"]
    for method in ["PUT", "PATCH"]:
        response = client.request(
            method, f"/groups/1/expenses/{expense_id}", headers={"X-User": "alice"}, json=DINNER
        )
        assert response.status_code == 405


@pytest.mark.parametrize(
    ("body", "outsiders"),
    [
        ({**DINNER, "paid_by": "dan"}, ["dan"]),
        ({**DINNER, "split": {"type": "equal", "members": ["alice", "dan"]}}, ["dan"]),
        (
            {**DINNER, "split": {"type": "exact", "shares": {"alice": "500.00", "dan": "500.00"}}},
            ["dan"],
        ),
        ({**DINNER, "paid_by": "zoe"}, ["zoe"]),
    ],
)
def test_payer_and_split_members_must_belong_to_group(client, body, outsiders):
    response = post_expense(client, body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MEMBER_NOT_IN_GROUP"
    assert response.json()["error"]["details"]["members"] == outsiders


def test_balances_stay_zero_sum_over_many_expenses(client):
    amounts = ["100.00", "0.01", "0.02", "333.33", "1000.01", "7.77"]
    payers = ["alice", "bob", "carol"]
    for i, amount in enumerate(amounts):
        post_expense(client, {**DINNER, "paid_by": payers[i % 3], "amount": amount})
    post_expense(
        client,
        {**DINNER, "amount": "10.00", "split": {"type": "equal", "members": ["carol", "bob"]}},
    )
    assert total(balances(client).values()) == Decimal("0.00")


def test_expenses_are_listed_newest_first(client):
    for name in ["first", "second", "third"]:
        post_expense(client, {**DINNER, "description": name})
    listed = client.get("/groups/1/expenses", headers={"X-User": "bob"}).json()
    assert [e["description"] for e in listed] == ["third", "second", "first"]


def test_group_detail_lists_members_in_order(client):
    response = client.get("/groups/1", headers={"X-User": "bob"})
    assert response.json() == {
        "id": 1,
        "name": "Chiang Mai trip",
        "members": ["alice", "bob", "carol"],
    }


@pytest.mark.parametrize(
    ("headers", "code"),
    [({}, "MISSING_USER"), ({"X-User": "mallory"}, "UNKNOWN_USER")],
)
def test_requests_need_a_known_user(client, headers, code):
    response = client.get("/groups", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == code


def test_validation_errors_use_the_error_envelope(client):
    response = post_expense(client, {"description": "x"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert {f["field"] for f in error["details"]["fields"]} >= {"paid_by", "amount", "split"}


def test_unknown_route_uses_the_error_envelope(client):
    response = client.get("/nope", headers={"X-User": "alice"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


# --- Optional: settle-up ---------------------------------------------------------------------
def test_settle_up_suggests_payments_for_the_brief_example(client):
    post_expense(client, DINNER)
    response = client.get("/groups/1/settle-up", headers={"X-User": "bob"})
    assert response.status_code == 200
    assert response.json() == {
        "group_id": 1,
        "payments": [
            {"from": "bob", "to": "alice", "amount": "333.33"},
            {"from": "carol", "to": "alice", "amount": "333.33"},
        ],
    }


def test_settle_up_is_empty_when_everyone_is_even(client):
    assert client.get("/groups/1/settle-up", headers={"X-User": "alice"}).json()["payments"] == []


def test_settle_up_requires_membership(client):
    response = client.get("/groups/2/settle-up", headers={"X-User": "alice"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "GROUP_NOT_FOUND"
