"""Test setup: a real PostgreSQL database, migrated with Alembic.

A real database (not SQLite) is required: idempotency relies on PostgreSQL's
INSERT ... ON CONFLICT and its locking behaviour, and money on NUMERIC.
"""

import os
from pathlib import Path

import pytest

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://splitbill:splitbill@localhost:5432/splitbill_test",
)
# The suite wipes this database. Refuse anything that does not look like a test DB.
if not TEST_DATABASE_URL.rsplit("/", 1)[-1].endswith("_test"):
    raise RuntimeError(f"TEST_DATABASE_URL must point at a *_test database: {TEST_DATABASE_URL}")

# Must be set before app.db creates its engine.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    """Run the real migrations (schema + seed) once per test session."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.attributes["database_url"] = TEST_DATABASE_URL
    # Start from an empty schema so leftovers from an interrupted run never matter.
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(config, "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_expenses():
    """Each test starts with the seed data and no expenses or repayments."""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE expense_shares, expenses, payments RESTART IDENTITY"))


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


DINNER = {
    "description": "Dinner at the night market",
    "paid_by": "alice",
    "amount": "1000.00",
    "split": {"type": "equal", "members": ["alice", "bob", "carol"]},
}


def post_expense(client: TestClient, body: dict, user: str = "alice", group: int = 1, key=None):
    headers = {"X-User": user}
    if key is not None:
        headers["Idempotency-Key"] = key
    return client.post(f"/groups/{group}/expenses", json=body, headers=headers)


def balances(client: TestClient, user: str = "alice", group: int = 1) -> dict[str, str]:
    response = client.get(f"/groups/{group}/balances", headers={"X-User": user})
    assert response.status_code == 200, response.text
    return {b["member"]: b["balance"] for b in response.json()["balances"]}
