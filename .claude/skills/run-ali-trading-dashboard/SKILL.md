---
name: run-ali-trading-dashboard
description: Build, run, and drive the Ali Trading Dashboard (FastAPI backend + local PostgreSQL + React/Vite frontend). Use when asked to start the app, run the backend or frontend dev servers, take a screenshot of the dashboard, log in as the test user, or verify a change works end-to-end.
---

Three-part local stack: a portable local PostgreSQL 16 instance
(`local-postgres/`), a FastAPI backend (`backend/`, served by uvicorn,
no separate build step), and a React/Vite frontend (`frontend/`, dev
server proxies `/api` to the backend). Drive it via
`.claude/skills/run-ali-trading-dashboard/driver.mjs` — a headless
Chromium (Playwright) script that logs in and screenshots the
dashboard. `chromium-cli` is not installed in this environment, so
this driver uses `playwright` directly instead.

All paths below are relative to the repo root
(`ali-trading-dashboard/`), except the driver's own path.

This is a Windows environment (PowerShell + Git Bash), not a Linux
container — commands below are PowerShell where they touch
Windows-specific things (processes, services) and Bash/curl elsewhere;
both were actually run this session.

## Prerequisites

Already present in this checkout (not re-verified from scratch this
session — see Troubleshooting if any of these are missing):

- Portable PostgreSQL 16 extracted + initialized at `local-postgres/`
  (`local-postgres/pgsql/bin/`, `local-postgres/data/`,
  `local-postgres/pwfile.txt`). Superuser role `ali` / password
  `ali_password` (from `pwfile.txt`), database `ali_trading`.
- `backend/.venv` created with dependencies installed (Python 3.14;
  see `RECOVERY_MANIFEST.md` §7 for the exact `pip install` line).
- `backend/.env` present, pointing at the local Postgres instance
  (`POSTGRES_HOST=localhost`, `POSTGRES_PORT=5432`,
  `POSTGRES_USER=ali`, `POSTGRES_PASSWORD=ali_password`,
  `POSTGRES_DB=ali_trading`) — **`CORS_ORIGINS` must be omitted
  entirely, not left as an empty string** (see Gotchas).
- `frontend/node_modules` installed (`npm install` in `frontend/`).
- Migrations applied (`alembic upgrade head` from `backend/`, single
  head `c58385829d11`).
- Node.js v22+, Python 3.14, npm.

Driver-only dependency (this skill directory, not the app):

```bash
cd ".claude/skills/run-ali-trading-dashboard"
npm install
npx playwright install chromium   # no-op if already cached
```

## Setup

Nothing beyond the above for a normal run. If you need sample data to
look at (dashboard is otherwise empty for a fresh user), see
`backend/scripts/seed_trading_sample_data.py` — requires an explicit
`--user-id`, refuses to run twice for the same user. The seeded test
account used by this driver is `testuser` /
`correct horse battery staple` (already registered + seeded in this
checkout).

## Build

No separate build step to run the app in dev mode. (`frontend`: `npm
run build` exists for a production bundle but isn't needed to drive
the dev server; `backend`: no compile step.)

## Run (agent path)

1. Start PostgreSQL, if not already running:

```powershell
Get-Process -Name "postgres*" -ErrorAction SilentlyContinue   # empty output = not running
```

If empty, start it (this cluster was previously shut down uncleanly
once already — see Gotchas — so check for a stale pidfile first):

```powershell
$base = "local-postgres"
if (-not (Get-Process -Name "postgres*" -ErrorAction SilentlyContinue)) {
  Remove-Item "$base\data\postmaster.pid" -Force -ErrorAction SilentlyContinue
  & "$base\pgsql\bin\pg_ctl.exe" start -D "$base\data" -l "$base\startup.log" -w
}
```

2. Start the backend (background; no `--reload`, so it must be
   restarted after any `backend/app/**` change):

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Poll until ready:

```bash
until curl.exe -sf http://127.0.0.1:8000/health/live >/dev/null; do sleep 1; done
```

3. Start the frontend dev server (background):

```powershell
Set-Location frontend
npm run dev
```

Poll until ready:

```bash
until curl.exe -sf http://localhost:5173/ >/dev/null; do sleep 1; done
```

4. Run the driver:

```bash
cd ".claude/skills/run-ali-trading-dashboard"
node driver.mjs
```

It logs in as `testuser`, waits for the dashboard's summary cards and
tables to render, prints any browser console errors, prints a
flattened text snapshot of the page body, and exits non-zero if any
console error was logged. Screenshots land in
`.claude/skills/run-ali-trading-dashboard/screenshots/`:
`login.png`, `dashboard.png` (full page).

Override target/creds via env vars if needed:
`FRONTEND_URL`, `TEST_USERNAME`, `TEST_PASSWORD`.

## Run (human path)

With all three services up (steps 1–3 above), open
`http://localhost:5173` in a browser and log in with `testuser` /
`correct horse battery staple`.

## Test

No test suite exists in this codebase yet — confirmed zero test files
across all 18 recovery archives (`RECOVERY_MANIFEST.md` §5/§8). There
is nothing to run here.

---

## Gotchas

- **`local` auth rules in `pg_hba.conf` don't apply on Windows.**
  There's no Unix socket, so every connection — even from
  `localhost` — hits the `host ... scram-sha-256` rule and needs the
  password, regardless of the `local ... trust` line.
- **The `postgres`/`template0` databases don't show under `\l` as
  role `ali`** on this cluster — connect to `ali_trading` or
  `template1` directly, not `postgres`, when running ad hoc `psql`
  checks.
- **A killed/crashed Postgres leaves a stale `data/postmaster.pid`**
  that blocks `pg_ctl start` even though nothing is running. Always
  verify via `Get-Process -Name postgres*` (and that nothing listens
  on 5432) before deleting it — `pg_ctl start` then runs automatic
  WAL-based crash recovery on its own.
- **`backend/.env`'s `CORS_ORIGINS` must be omitted, not set to an
  empty string.** `pydantic-settings` JSON-parses a *present* env var
  for a `list[str]` field before the app's own comma-split validator
  runs, and raises on an empty string. Omitting the line entirely
  falls through to the field's `default_factory=list`.
- **`Numeric` and `INET` Postgres columns decode to `decimal.Decimal`
  / `ipaddress.IPv4Address` at the driver level (psycopg/asyncpg)**,
  not `str`/`float`, regardless of the SQLAlchemy model's own
  `Mapped[float]`/`Mapped[str]` annotation. Every response DTO that
  surfaces one of these columns needs a `field_validator(mode=
  "before")` coercion (see `app/services/identity/dtos.py`'s
  `ip_address` fix and `app/services/trading/dtos.py`'s numeric
  fields) or the route 500s the first time it touches a real row —
  this only surfaces once real data flows through, not on import.
- **`app/models/trading.py`'s `symbol_id`/`strategy_id` columns must
  not carry an ORM-level `ForeignKey("symbols.id"/"strategies.id")`.**
  The Market/Strategy domains have no registered SQLAlchemy model in
  this MVP, so `"symbols"`/`"strategies"` are never `Table` objects on
  `Base.metadata`; SQLAlchemy raises `NoReferencedTableError` at
  *flush* time (not import time) trying to sort insert dependencies —
  this blocks **every** `Order`/`Execution`/`Position`/`Trade` insert,
  not just ones touching those columns. Already fixed (ORM-level FK
  object removed; column + the real Postgres-level FK constraint from
  the migration are untouched). If a `Symbol`/`Strategy` model is ever
  added back, the `ForeignKey(...)` can be restored then.
- **The Vite dev server can resolve `127.0.0.1:5173` slower than
  `localhost:5173`** (IPv6 `::1` answers first) right after start —
  the driver and the poll loop above both target `localhost`, not
  `127.0.0.1`.
- **`chromium-cli` is not installed in this environment** — the
  driver uses `playwright` directly instead, installed only inside
  this skill directory (not the app's own `package.json`).

## Troubleshooting

- **`pg_ctl: server is running (PID: ...)` health log shows
  `database system was interrupted; last known up at ...`**: expected
  after an unclean shutdown — automatic crash recovery ran and
  completed; not an error, just confirms the stale-pidfile situation
  above actually happened.
- **`FATAL: password authentication failed for user "postgres"`**:
  there is no `postgres` superuser role on this cluster — use `ali` /
  `ali_password` (from `local-postgres/pwfile.txt`).
- **Login (`POST /auth/login`) returns 500 with
  `pydantic_core.ValidationError ... ip_address ... IPv4Address`**:
  the `ip_address` coercion validator in
  `app/services/identity/dtos.py` is missing or was reverted —
  restore it.
- **Any `Order`/`Trade` insert (including the seed script) raises
  `sqlalchemy.exc.NoReferencedTableError: ... orders.symbol_id ...
  'symbols'`**: the `ForeignKey("symbols.id"/"strategies.id")` fix in
  `app/models/trading.py` is missing or was reverted — restore it
  (see Gotchas above).
- **`/trading/*` endpoints return empty lists/zeros**: expected for a
  user with no seeded data — run
  `backend/scripts/seed_trading_sample_data.py --user-id <uuid>` once
  for that user (get the id via `SELECT id FROM users WHERE username
  = '<name>'`).
- **Driver hangs on `waitForSelector('text=Sign in')`**: the frontend
  dev server isn't actually up yet, or `backend/.env` is missing so
  the backend never started — check both health/readiness polls in
  step 1–3 above actually returned before running the driver.
