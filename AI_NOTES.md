# AI notes

## Tools used

- **Claude (Anthropic), in the Claude app**, with access to a cloud workspace (shell, Python,
  Node, a local PostgreSQL 16, headless Chromium) and to this project folder on my computer.

Claude generated almost all of the code, tests and documentation in this repository, and made
the commits after running the checks below. I chose the scope and the order of work (frontend
first against an agreed API contract, then backend), answered its questions about decisions
such as 404 vs 403 and whether to attempt the optional extensions, set up and ran the project
on my own Windows machine, and asked for explanations of each part.

| Part | What the AI did |
|---|---|
| API contract | Drafted `docs/API_CONTRACT.md` before any code so both sides had one shape |
| Backend | Models, migrations, domain functions, services, routes, error envelope |
| Tests | pytest suite (including the concurrency tests) and Vitest unit tests |
| Frontend | Money/split logic, API client, form, preview, balances, list |
| Verification | Browser end-to-end run against a throwaway mock and then the real backend |
| Docs | READMEs, this file, Thai study notes for me (not committed) |

## Effective prompts

My prompts were in Thai; translated:

1. *"Build it in this folder. Do the Next.js part first, and write down an explanation of
   everything."*
   Asking for the frontend first forced the API contract to be written down before any backend
   code existed, and the explanation requirement produced per-decision notes I could study.
2. *"Do it part by part, in detail."* (with the brief attached)
   This made the assistant propose a plan with one reviewable step per part and ask about
   ambiguous points (403 vs 404, optional scope) before writing code.

## Incorrect or unsafe AI output, how it was caught, and the fix

1. **Thai digits accepted as money (correctness bug).** The first amount regex used `\d`. In
   Python `\d` also matches non-ASCII digits, and `Decimal("๑๐๐")` is `100`, so `"๑๐๐"` would
   have been stored as 100.00 THB. No ordinary test would catch it.
   *Caught by:* reviewing the regex and proving it in a shell
   (`re.match(r'^\d+$', '๑๐๐')` matched).
   *Fix:* `[0-9]` with `fullmatch`, plus test cases for `"๑๐๐"`, `"+5"` and `" . "`.

2. **Idempotency race (the risk the brief warns about).** The usual implementation,
   "look up the key, insert if missing", lets two concurrent requests both insert.
   *Caught by:* mutation testing. After writing the concurrency tests, the implementation was
   temporarily replaced with check-then-insert; both tests failed, so they really detect
   the race. The real code was then restored and the tests passed.
   *Fix:* unique constraint plus `INSERT ... ON CONFLICT DO NOTHING`.

3. **Outdated library APIs.** SQLAlchemy 2.1 broke `Result.tuples()` used for the balance
   query (7 tests failed with a `TypeError`), and Starlette 1.x deprecated `httpx` for the test
   client in favour of `httpx2` (deprecation warning). Next.js 16 also differs from what the
   assistant knew (`AGENTS.md` warns about this).
   *Caught by:* the test run, the warning output and the generated `AGENTS.md`.
   *Fix:* unpack rows directly, switch to `httpx2`, and read the docs bundled in
   `node_modules/next/dist/docs` before writing config.

4. **Form that could never show its errors.** The first draft disabled the submit button
   whenever the form was invalid, so the "Enter a description" message could never appear.
   *Caught by:* reviewing the component before running it.
   *Fix:* disable only where the brief requires it (exact split not equal to the total) and
   while submitting.

5. **Unnecessary memoisation.** A `useMemo` around a cheap calculation was flagged by the React
   Compiler lint rule `react-hooks/preserve-manual-memoization`.
   *Caught by:* `npm run lint`. *Fix:* removed it.

6. **Fragile test setup.** The test fixture used `alembic downgrade base`; after an interrupted
   run, leftover rows made the downgrade fail on a foreign key and every test errored.
   *Caught by:* the next test run. *Fix:* drop and recreate the schema, then upgrade.

7. **A false alarm.** One browser check reported the network-error message as missing; the
   check read the page before it updated. The app was correct and the check was fixed, a
   reminder that a failing test is not always a bug in the code.

## Review process before each commit

- `ruff check` and `ruff format --check` (backend), ESLint and `tsc --noEmit` (frontend).
- Full test suites: pytest against real PostgreSQL 16 (96 tests) and Vitest (39 tests).
- Every commit was checked out on its own and linted and tested, so no commit in the history
  is broken.
- `alembic check` to confirm the models match the migrations.
- A browser end-to-end run of the brief's scenarios against the real backend
  (100.00 / 3 preview, 10.005 rejected, exact split disabled until balanced, 0.1 + 0.2 = 0.30,
  non-member access, payer-only delete, plain-language errors, retry reusing the same
  Idempotency-Key).
- Checked that no `.env`, virtual environment, `node_modules` or personal notes are tracked.
- On my own machine I installed Python and PostgreSQL 16, created the databases, ran the
  migrations and ran the backend suite (96 passed).

What I did not do before each commit: read every line myself. Most review was done through
the automated checks above and the assistant's own re-reading. I am going through the code
with the assistant's explanations, starting with money handling and split allocation, so that
I can explain and change any part of it.
