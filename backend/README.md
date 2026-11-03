# SplitBill backend

FastAPI + SQLAlchemy 2 + PostgreSQL 16 + Alembic. API described in
`../docs/API_CONTRACT.md`. See the root `README.md` for the full setup.

```bash
docker compose up -d db                 # from the repo root (or use your own PostgreSQL 16)
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head                    # schema + seed users/groups
uvicorn app.main:app --reload           # http://localhost:8000/docs
pytest                                  # needs the splitbill_test database
ruff check . && ruff format --check .
```

## Layout

| Layer          | File                     | Responsibility                                   |
|----------------|--------------------------|--------------------------------------------------|
| Routing        | `app/routers/groups.py`  | HTTP in/out, status codes, response shapes        |
| Dependencies   | `app/deps.py`            | `X-User`, group membership, `Idempotency-Key`     |
| Business rules | `app/domain/*.py`        | Money parsing, split allocation, balances (pure)  |
|                | `app/services.py`        | Rules that need data: membership, idempotency     |
| Data access    | `app/repository.py`      | All SQL                                           |
| Errors         | `app/errors.py`          | One JSON error envelope for every failure         |
