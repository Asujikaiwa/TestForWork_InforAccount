"""Idempotency under concurrency.

A check-then-insert ("SELECT by key; if missing, INSERT") lets two concurrent
requests both see "missing" and both insert. These tests prove that does not
happen here.
"""

import threading
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app import repository as repo
from app.db import SessionLocal
from app.main import app
from app.models import Expense
from tests.conftest import DINNER

THREADS = 12


def test_concurrent_requests_with_the_same_key_create_one_expense():
    barrier = threading.Barrier(THREADS)

    def send(_: int):
        with TestClient(app) as client:
            barrier.wait()  # release every request at the same moment
            return client.post(
                "/groups/1/expenses",
                json=DINNER,
                headers={"X-User": "alice", "Idempotency-Key": "race-0001"},
            )

    with ThreadPoolExecutor(THREADS) as pool:
        responses = list(pool.map(send, range(THREADS)))

    statuses = sorted(r.status_code for r in responses)
    assert statuses == [200] * (THREADS - 1) + [201]
    assert len({r.json()["id"] for r in responses}) == 1
    with SessionLocal() as session:
        count = session.scalar(select(func.count()).select_from(Expense))
    assert count == 1


def test_second_insert_waits_for_the_first_transaction_then_yields():
    """Deterministic version of the race, at the SQL level.

    Transaction A inserts the key but has not committed. Transaction B inserts
    the same key: PostgreSQL blocks B until A finishes. After A commits, B's
    INSERT ... ON CONFLICT DO NOTHING returns no row, and B can read A's expense.
    """
    values = {
        "group_id": 1,
        "description": "Race",
        "paid_by_id": 1,
        "amount": "10.00",
        "split_type": "equal",
        "created_by_id": 1,
        "idempotency_key": "race-0002",
        "request_hash": "x",
    }
    b_started = threading.Event()
    b_result: dict = {}

    def transaction_b():
        with SessionLocal() as session_b:
            b_started.set()
            b_result["id"] = repo.insert_expense(session_b, values)  # blocks here
            b_result["existing"] = repo.get_expense_by_key(session_b, 1, "race-0002").id
            session_b.rollback()

    with SessionLocal() as session_a:
        a_id = repo.insert_expense(session_a, values)
        assert a_id is not None

        thread = threading.Thread(target=transaction_b)
        thread.start()
        b_started.wait()
        thread.join(timeout=1)
        assert thread.is_alive(), "B should be blocked while A is uncommitted"

        session_a.commit()

    thread.join(timeout=5)
    assert not thread.is_alive()
    assert b_result == {"id": None, "existing": a_id}
