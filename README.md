# SplitBill

Shared-expense app: record costs shared by a group and see each member's net balance,
accurate to the satang.

- `backend/`: Python 3.12+, FastAPI, SQLAlchemy 2, PostgreSQL 16, Alembic, pytest, Ruff
- `frontend/`: Next.js 16, TypeScript, Tailwind CSS, Vitest, ESLint
- `docs/API_CONTRACT.md`: request/response shapes and error codes shared by both sides

## Setup from a fresh clone

### 1. Database (PostgreSQL 16)

With Docker:

```bash
docker compose up -d db      # creates databases splitbill and splitbill_test
```

Without Docker, install PostgreSQL 16 and run as the `postgres` superuser:

```sql
CREATE USER splitbill PASSWORD 'splitbill' CREATEDB;
CREATE DATABASE splitbill OWNER splitbill;
CREATE DATABASE splitbill_test OWNER splitbill;
```

### 2. Backend (http://localhost:8000, docs at /docs)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env               # Windows: copy .env.example .env
alembic upgrade head               # schema + seed users and groups
uvicorn app.main:app --reload
```

### 3. Frontend (http://localhost:3000)

```bash
cd frontend
npm install
npm run dev
```

The frontend proxies `/api/*` to the backend (`BACKEND_URL`, default `http://localhost:8000`).

## Tests and linting

```bash
cd backend  && pytest                            # 96 tests, needs the splitbill_test database
cd backend  && ruff check . && ruff format --check .
cd frontend && npm run check                     # ESLint + TypeScript + 39 Vitest tests
```

The backend suite runs against a real PostgreSQL database (`TEST_DATABASE_URL`, default
`.../splitbill_test`). It drops and recreates the schema through the real Alembic migrations,
and refuses to run against a database whose name does not end in `_test`.

Required cases and where they are tested (`backend/tests/test_api.py`):

| Case | Test |
|---|---|
| 100.00 split equally among three: 33.34 / 33.33 / 33.33, balances sum to 0.00 | `test_equal_split_of_100_among_three_and_balances_sum_to_zero` |
| Exact split not summing to the amount is rejected | `test_exact_split_not_summing_to_amount_is_rejected` |
| Amount with 3 decimal places is rejected | `test_amount_with_three_decimal_places_is_rejected` |
| Repeated Idempotency-Key creates one expense | `test_repeated_idempotency_key_creates_only_one_expense`, `tests/test_idempotency_concurrency.py` |
| alice can neither read nor write group 2 | `test_alice_can_neither_read_nor_write_group_2` (all five group endpoints) |
| Only the payer can delete | `test_only_the_payer_can_delete_an_expense`, `test_payer_is_who_paid_not_who_recorded` |

## Key design decisions

**404, not 403, for non-members.** A user who is not a member of a group gets
`404 GROUP_NOT_FOUND`, byte-for-byte the same response as for a group id that does not exist.
A 403 would confirm that the group exists and let anyone enumerate group ids. The membership
check is a single query (group joined with membership), applied as a FastAPI dependency to
every `/groups/{group_id}` route so it cannot be forgotten. Inside a group, a member who tries
to delete someone else's expense gets `403 NOT_PAYER`: they can already see the expense, so
there is nothing to hide and a precise error is more useful.

**Money is never a float.** Amounts travel as strings (`"1000.00"`). The request schema types
money fields as `str`, and Pydantic does not coerce JSON numbers to strings, so `1000.5`
(a JSON number) is rejected before a float exists. Strings are parsed into `Decimal`
(ASCII digits only, at most 2 decimal places, greater than 0, at most 9,999,999,999.99) and
stored in `NUMERIC(12,2)`. Sums are done by PostgreSQL in `NUMERIC`, which is exact.

**Allocating leftover satang.** Equal splits are computed in integer satang:
`base, remainder = divmod(total, n)`, and the first `remainder` members in the order listed
get one extra satang. No rounding mode is involved, shares always sum to the amount, and no
member differs from another by more than 0.01. Shares are stored per expense rather than
recomputed, so past expenses never change. Exact splits must sum to the amount exactly or the
request fails with `SHARES_MISMATCH` (details include both totals).

**Zero-sum balances.** A balance is what a member paid minus their shares over non-deleted
expenses. Every stored expense satisfies sum(shares) = amount, so the group total is always
exactly 0.00. A test checks this over a mix of awkward amounts.

**Idempotency that holds under concurrency.** `UNIQUE (group_id, idempotency_key)` lives in
the database, and the expense is created with
`INSERT ... ON CONFLICT (group_id, idempotency_key) DO NOTHING RETURNING id`.
If no id comes back, the key was already used: the original expense is returned with
`200 OK` (a new one returns `201 Created`). If a second transaction inserts the same key while
the first is still open, PostgreSQL makes it wait for the first to commit or roll back, so
there is no check-then-insert race. A SHA-256 of the normalised request is stored with the key;
reusing a key with a different body returns `409 IDEMPOTENCY_KEY_REUSED` instead of silently
returning the wrong expense. Requests without the header are not deduplicated (NULL keys never
conflict). Two tests cover concurrency: 12 identical requests released at once by a barrier,
and a deterministic two-transaction test that proves the second insert blocks and then yields.
Both fail when the implementation is swapped for check-then-insert.

**Immutability and soft delete.** There is no PUT/PATCH route (`405`). `DELETE` is allowed only
for the payer (not the person who recorded it), and sets `deleted_at`/`deleted_by_id`; the row
stays and is excluded from lists and balances.

**Layering.** `routers/` (HTTP only) → `services.py` (rules needing data: membership,
idempotency, delete) → `domain/` (pure functions: money parsing, splits, balances; tested
without a database) → `repository.py` (all SQL). `errors.py` gives every failure the same
envelope: `{"error": {"code", "message", "details"}}`, including validation errors, unknown
routes and unexpected 500s (no stack traces or SQL leak to clients).

**Frontend money and preview.** The frontend keeps every amount as integer satang. Input is
parsed from the string digit by digit (never `parseFloat`), splits use the same algorithm as
the backend, and display formats the whole part with `Intl.NumberFormat("th-TH")` and appends
the two decimals as text, so no fractional number is ever created: `0.1 + 0.2` is
`10 + 20 = 30` satang and displays `0.30`. Equal splits are sent in group member order, so the
member who receives a leftover satang in the preview is the same one the backend chooses.
After saving, the list shows the shares returned by the backend, not the preview.

**Frontend errors and retries.** API errors are translated to plain language from the error
`code`, never from server wording ("The shares do not add up to the total",
"Not a member of this group"). The form keeps one Idempotency-Key per intended expense: a
resubmission of the same form (double click, retry after a network error) reuses the key,
while editing the form issues a new one. Data hooks abort stale requests so a slow response
for one group can never overwrite another.

## Assumptions

- Users are identified only by `X-User` (authentication is out of scope). Missing or unknown
  users get `401`.
- There is no endpoint to list users, so the frontend's user picker offers the four seeded users.
- "Members in the order listed" means the order of `split.members` in the request; the frontend
  always sends group member order.
- In an exact split, a member with a blank or zero share is not part of the split. Every given
  share must be greater than 0.
- An equal split of an amount smaller than the number of members (0.02 among three) gives some
  members 0.00. This is mathematically correct and allowed.
- The payer does not have to be part of the split.
- An idempotent replay returns the original expense even if it has since been deleted.

## Known limitations and next steps

- Idempotency keys never expire; production systems usually keep them for about 24 hours.
- No pagination on the expense list.
- The frontend does not refetch when another user changes the group (could add polling or
  refetch on focus, e.g. with React Query).
- No real authentication; `X-User` is trusted.
- No CORS configuration: the browser talks to the backend through the Next.js proxy.
  `BACKEND_URL` is read when Next.js starts or builds.
- The Docker Compose file starts PostgreSQL only and has not been tested on this machine;
  the API runs locally.
- Optional extensions (settle-up, repayments, containerised API) are not implemented.
  Settle-up would be a pure function over the existing balances in `domain/splits.py` plus one
  route.

## Time spent

About 6 hours over four days: roughly 2.5 hours building and testing the code with an AI
assistant, and the rest setting up the local environment (Python, PostgreSQL), running the
suite and reviewing the code and design decisions. See `AI_NOTES.md`.
