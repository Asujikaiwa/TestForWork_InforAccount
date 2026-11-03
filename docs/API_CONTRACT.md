# SplitBill API contract

This is the contract between `frontend/` and `backend/`. The frontend was built
against it first; the backend implements it.

## Conventions

- Every request carries `X-User: <username>` (alice, bob, carol, dan).
- Money is always a **string** with exactly 2 decimal places in responses
  (`"1000.00"`, `"-333.33"`). Requests may send 1 or 2 decimal places.
- Lists are ordered: group members in membership order, expense shares in the
  order the split listed them, expenses newest first.

## Endpoints

### `GET /groups`
Groups of the requesting user.
```json
[{ "id": 1, "name": "Chiang Mai trip" }]
```

### `GET /groups/{group_id}`
```json
{ "id": 1, "name": "Chiang Mai trip", "members": ["alice", "bob", "carol"] }
```

### `POST /groups/{group_id}/expenses`
Headers: `X-User`, `Idempotency-Key` (the frontend always sends one).
```json
{
  "description": "Dinner at the night market",
  "paid_by": "alice",
  "amount": "1000.00",
  "split": { "type": "equal", "members": ["alice", "bob", "carol"] }
}
```
or `"split": { "type": "exact", "shares": { "alice": "500.00", "bob": "500.00" } }`.

`201 Created` for a new expense, `200 OK` when the `Idempotency-Key` was already
used in this group (the original expense is returned unchanged).

### Expense object
```json
{
  "id": 7,
  "group_id": 1,
  "description": "Dinner at the night market",
  "paid_by": "alice",
  "amount": "1000.00",
  "split_type": "equal",
  "shares": [
    { "member": "alice", "amount": "333.34" },
    { "member": "bob", "amount": "333.33" },
    { "member": "carol", "amount": "333.33" }
  ],
  "created_by": "alice",
  "created_at": "2026-10-30T12:00:00Z"
}
```

### `GET /groups/{group_id}/expenses`
Array of expense objects, newest first, soft-deleted expenses excluded.

### `DELETE /groups/{group_id}/expenses/{expense_id}`
`204 No Content`. Only the payer may delete.

### `GET /groups/{group_id}/balances`
Positive = the group owes this member money. Always sums to `"0.00"`.
```json
{
  "group_id": 1,
  "balances": [
    { "member": "alice", "balance": "666.66" },
    { "member": "bob", "balance": "-333.33" },
    { "member": "carol", "balance": "-333.33" }
  ]
}
```
Balance = paid for expenses − own shares + repayments sent − repayments received.

## Optional extensions

### `GET /groups/{group_id}/settle-up`
The fewest payments that bring every balance to `"0.00"`.
```json
{
  "group_id": 1,
  "payments": [
    { "from": "bob", "to": "alice", "amount": "333.33" },
    { "from": "carol", "to": "alice", "amount": "333.33" }
  ]
}
```

### `POST /groups/{group_id}/payments`
Records a repayment. Headers: `X-User` (must be `from` or `to`), optional `Idempotency-Key`
(same behaviour as expenses: `201` new, `200` replay, `409` different body).
```json
{ "from": "bob", "to": "alice", "amount": "333.33" }
```
Response (also the shape of each item in `GET /groups/{group_id}/payments`, newest first):
```json
{
  "id": 1, "group_id": 1, "from": "bob", "to": "alice", "amount": "333.33",
  "created_by": "bob", "created_at": "2026-11-03T10:00:00Z"
}
```

## Errors

Every error uses the same body:
```json
{ "error": { "code": "SHARES_MISMATCH", "message": "Human readable text", "details": {} } }
```

| Status | `code`                  | When                                                        | `details`                          |
|--------|-------------------------|-------------------------------------------------------------|------------------------------------|
| 401    | `MISSING_USER`          | No `X-User` header                                          |                                    |
| 401    | `UNKNOWN_USER`          | `X-User` is not a known user                                |                                    |
| 404    | `GROUP_NOT_FOUND`       | Group does not exist **or** the user is not a member        |                                    |
| 404    | `EXPENSE_NOT_FOUND`     | Expense does not exist in this group or is already deleted |                                    |
| 403    | `NOT_PAYER`             | A member other than the payer tries to delete              |                                    |
| 422    | `VALIDATION_ERROR`      | Malformed body (missing field, wrong type)                 | `{ "fields": [{ "field", "message" }] }` |
| 422    | `INVALID_AMOUNT`        | Amount or share is not a positive number                   | `{ "field" }`                      |
| 422    | `AMOUNT_PRECISION`      | More than 2 decimal places                                 | `{ "field" }`                      |
| 422    | `SHARES_MISMATCH`       | Exact shares do not sum to the amount                      | `{ "amount", "shares_total" }`     |
| 422    | `MEMBER_NOT_IN_GROUP`   | Payer or a split member is not in the group                | `{ "members": ["dan"] }`           |
| 422    | `EMPTY_SPLIT`           | No members / shares given                                  |                                    |
| 409    | `IDEMPOTENCY_KEY_REUSED`| Same key reused with a different request body              |                                    |
| 403    | `NOT_PAYMENT_PARTY`     | Repayment recorded by someone who is neither `from` nor `to` |                                  |
| 422    | `PAYMENT_TO_SELF`       | Repayment with `from` equal to `to`                        |                                    |
