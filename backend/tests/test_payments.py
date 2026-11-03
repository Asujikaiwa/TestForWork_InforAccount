"""Repayments: recording, rules, idempotency and their effect on balances and settle-up."""

from decimal import Decimal

import pytest

from tests.conftest import DINNER, balances, post_expense


def post_payment(client, body, user="bob", group=1, key=None):
    headers = {"X-User": user}
    if key is not None:
        headers["Idempotency-Key"] = key
    return client.post(f"/groups/{group}/payments", json=body, headers=headers)


BOB_PAYS_ALICE = {"from": "bob", "to": "alice", "amount": "333.33"}


def test_repayment_updates_balances_and_settle_up(client):
    post_expense(client, DINNER)

    response = post_payment(client, BOB_PAYS_ALICE)

    assert response.status_code == 201, response.text
    body = response.json()
    assert {k: body[k] for k in ("from", "to", "amount", "created_by")} == {
        "from": "bob",
        "to": "alice",
        "amount": "333.33",
        "created_by": "bob",
    }
    assert balances(client) == {"alice": "333.33", "bob": "0.00", "carol": "-333.33"}
    settle = client.get("/groups/1/settle-up", headers={"X-User": "alice"}).json()
    assert settle["payments"] == [{"from": "carol", "to": "alice", "amount": "333.33"}]


def test_following_every_suggestion_settles_the_group(client):
    post_expense(client, DINNER)
    post_expense(client, {**DINNER, "paid_by": "bob", "amount": "100.00"})
    suggestions = client.get("/groups/1/settle-up", headers={"X-User": "alice"}).json()["payments"]

    for suggestion in suggestions:
        assert post_payment(client, suggestion, user=suggestion["from"]).status_code == 201

    assert set(balances(client).values()) == {"0.00"}
    assert client.get("/groups/1/settle-up", headers={"X-User": "alice"}).json()["payments"] == []


def test_balances_stay_zero_sum_with_repayments(client):
    post_expense(client, DINNER)
    post_payment(client, {"from": "carol", "to": "alice", "amount": "100.01"}, user="carol")
    post_payment(client, {"from": "bob", "to": "carol", "amount": "0.01"}, user="carol")
    total = sum((Decimal(v) for v in balances(client).values()), Decimal("0"))
    assert total == Decimal("0.00")


def test_repayments_are_listed_newest_first(client):
    post_payment(client, {**BOB_PAYS_ALICE, "amount": "1.00"})
    post_payment(client, {**BOB_PAYS_ALICE, "amount": "2.00"})
    listed = client.get("/groups/1/payments", headers={"X-User": "carol"}).json()
    assert [p["amount"] for p in listed] == ["2.00", "1.00"]


def test_only_the_payer_or_receiver_can_record_a_repayment(client):
    assert post_payment(client, BOB_PAYS_ALICE, user="alice").status_code == 201  # receiver

    response = post_payment(client, BOB_PAYS_ALICE, user="carol")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_PAYMENT_PARTY"


def test_cannot_pay_yourself(client):
    response = post_payment(client, {"from": "bob", "to": "bob", "amount": "1.00"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PAYMENT_TO_SELF"


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({**BOB_PAYS_ALICE, "amount": "1.005"}, "AMOUNT_PRECISION"),
        ({**BOB_PAYS_ALICE, "amount": "0"}, "INVALID_AMOUNT"),
        ({**BOB_PAYS_ALICE, "amount": 5}, "VALIDATION_ERROR"),
        ({**BOB_PAYS_ALICE, "to": "dan"}, "MEMBER_NOT_IN_GROUP"),
        ({"from": "bob", "amount": "1.00"}, "VALIDATION_ERROR"),
    ],
)
def test_invalid_repayments_are_rejected(client, body, code):
    response = post_payment(client, body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    assert client.get("/groups/1/payments", headers={"X-User": "bob"}).json() == []


def test_non_members_cannot_read_or_record_repayments(client):
    lunch = {"from": "dan", "to": "bob", "amount": "10.00"}
    assert post_payment(client, lunch, user="dan", group=2).status_code == 201

    read = client.get("/groups/2/payments", headers={"X-User": "alice"})
    write = post_payment(client, lunch, user="alice", group=2)

    assert read.status_code == write.status_code == 404
    assert read.json()["error"]["code"] == "GROUP_NOT_FOUND"
    assert len(client.get("/groups/2/payments", headers={"X-User": "bob"}).json()) == 1


def test_repeated_idempotency_key_records_one_repayment(client):
    first = post_payment(client, BOB_PAYS_ALICE, key="pay-0001")
    second = post_payment(client, BOB_PAYS_ALICE, key="pay-0001")
    conflict = post_payment(client, {**BOB_PAYS_ALICE, "amount": "1.00"}, key="pay-0001")

    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json() == first.json()
    assert conflict.status_code == 409
    assert len(client.get("/groups/1/payments", headers={"X-User": "bob"}).json()) == 1
