# Ali Trading Dashboard

A recovered MVP of a trading dashboard: a FastAPI backend (async SQLAlchemy 2
+ PostgreSQL) and a React/Vite frontend, covering the **Identity** and
**Trading** domains only.

> **Status: recovery MVP, not the original full project.** This codebase was
> reconstructed from 18 zip archives after the original project state was
> lost. The original design covered 55 tables across 11 domains; this MVP
> covers 14 tables across 2 domains (Identity + Trading). It does **not**
> include Market, Watchlist, Trade Journal, Strategy, Indicator, Alert, News,
> Portfolio, AI, or System domains, and there is no Docker, CI/CD, or
> deployment tooling in this repository. For the full phase-by-phase history,
> every archive-vs-archive decision, every bug found and fixed, and the
> complete list of known gaps, see **[`RECOVERY_MANIFEST.md`](RECOVERY_MANIFEST.md)**
> — that document is the authoritative historical/recovery record; this
> README only describes how to run and use what exists today.

## What's actually here

**Backend (`backend/`)** — FastAPI + SQLAlchemy 2 (async) + Alembic +
PostgreSQL:
- **Identity domain**: users, sessions, refresh tokens, RBAC (roles,
  permissions, role-permission, user-role), API keys.
- **Trading domain**: orders, executions, positions, trades, order history —
  read/write via repositories, exposed read-only over HTTP.
- Argon2 password hashing, JWT access tokens, rotating refresh tokens.
- Structured JSON logging, request-id middleware, centralized exception
  handling.

**Frontend (`frontend/`)** — React 19 + Vite + React Router:
- Login screen and an authenticated dashboard (`src/auth/`, `src/pages/`,
  `src/features/`) that calls the backend's `/auth/*` and `/trading/*`
  endpoints (`src/api/`).
- Session-expiry handling: if both the access and refresh tokens become
  invalid while the dashboard is open, the app redirects to `/login` instead
  of showing a stale dashboard.

## API routes

All routes are mounted at the root — there is no `/api/v1` prefix (no
versioned domain endpoints exist yet). Verified directly against
`backend/app/api/{health,auth,trading}.py`:

**Infrastructure** (`backend/app/api/health.py`):
| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Service identity (name + version) |
| GET | `/version` | Version + environment |
| GET | `/health/live` | Liveness — process is running |
| GET | `/health/ready` | Readiness — checks database connectivity |
| GET | `/health` | Overall health (currently same as readiness) |

**Auth** (`backend/app/api/auth.py`, prefix `/auth`):
| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create a user account |
| POST | `/auth/login` | Authenticate, issue a session + access/refresh token pair |
| POST | `/auth/refresh` | Rotate a refresh token, mint a fresh access token |
| POST | `/auth/logout` | Revoke the session and refresh token behind a given token |
| GET | `/auth/me` | Current user, plus their RBAC roles and permissions |

**Trading** (`backend/app/api/trading.py`, prefix `/trading`, all read-only,
all scoped to the authenticated user):
| Method | Path | Purpose |
|---|---|---|
| GET | `/trading/summary` | Dashboard summary |
| GET | `/trading/positions` | Positions (optional `status` filter) |
| GET | `/trading/orders` | Orders (paginated via `limit`/`offset`) |
| GET | `/trading/executions` | Recent executions (`limit`) |
| GET | `/trading/trades` | Closed trades (paginated via `limit`/`offset`) |

Interactive docs once the backend is running: `http://localhost:8000/docs`
(Swagger) or `/redoc`.

## Project structure

```
ali-trading-dashboard/
├── backend/
│   ├── app/
│   │   ├── api/            auth.py, trading.py, health.py, router.py, deps.py
│   │   ├── core/            config, logging, context, exceptions, security/ (hashing, JWT)
│   │   ├── db/               async engine/session
│   │   ├── middleware/        request-id + request-logging
│   │   ├── models/            identity.py, trading.py, base.py, mixins.py, enums.py
│   │   ├── repositories/      identity/, trading/, base.py, unit_of_work.py
│   │   ├── services/          identity/, authentication/, authorization/, trading/ (DTOs)
│   │   └── main.py            application factory
│   ├── alembic/                env.py + versions/ (single migration: initial schema)
│   ├── scripts/                 seed_trading_sample_data.py
│   ├── tests/                   test_trading_api.py, test_trading_db_invariants.py, test_auth_flow_e2e.py, conftest.py
│   ├── .env.example              tracked template — copy to .env, never commit .env
│   └── pyproject.toml
├── frontend/
│   ├── src/                     api/, auth/, features/, pages/, App.tsx, main.tsx
│   ├── e2e/                      auth.spec.ts, dashboard.spec.ts, global-setup.ts (Playwright)
│   ├── playwright.config.ts
│   └── package.json
├── local-postgres/               portable PostgreSQL 16 instance (binaries/data gitignored)
├── backups/                       local database dump backups (gitignored)
└── RECOVERY_MANIFEST.md           detailed historical/recovery record
```

There is no `Dockerfile`, `docker-compose.yml`, or `.github/workflows/` in
this repository — everything below runs directly against a local Python
virtualenv, Node.js, and the portable PostgreSQL instance under
`local-postgres/`.

## Local development setup

### Prerequisites
- Python 3.12+ (developed/validated locally against Python 3.14 — the
  project's own `pyproject.toml` targets `>=3.12`; see `RECOVERY_MANIFEST.md`
  §"Environment used for validation" for the exact compatibility notes).
- Node.js 22+, npm.
- The portable PostgreSQL 16 instance under `local-postgres/` (already
  extracted and initialized in this checkout — superuser role `ali`,
  password in `local-postgres/pwfile.txt`).

### 1. Start PostgreSQL
```powershell
cd local-postgres
.\pgsql\bin\pg_ctl.exe start -D data -l startup.log -w
```

### 2. Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install `
  "fastapi>=0.115,<0.116" "uvicorn[standard]>=0.34,<0.35" `
  "pydantic>=2.9,<3.0" "pydantic-settings>=2.5,<3.0" "email-validator>=2.2,<3.0" `
  "sqlalchemy[asyncio]>=2.0,<2.1" "asyncpg==0.31.0" "psycopg[binary]>=3.2,<3.3" `
  "alembic>=1.14,<1.15" "redis>=5.2,<6.0" "python-dotenv>=1.0,<2.0" `
  "argon2-cffi>=23.1,<24.0" "PyJWT>=2.9,<3.0"

Copy-Item .env.example .env
# Edit .env: set POSTGRES_HOST=localhost, POSTGRES_USER=ali,
# POSTGRES_PASSWORD=<from local-postgres/pwfile.txt>, POSTGRES_DB=ali_trading.
# Leave CORS_ORIGINS out of the file entirely (not an empty string) —
# pydantic-settings fails to parse an empty string for that field.

.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
`pip install .` (installing as a package) does not work — this project's
`pyproject.toml` points its `readme` outside the build root; install
dependencies by name as above instead. Dev-only tools (`pytest`, `ruff`,
`mypy`, etc.) are declared under `[project.optional-dependencies].dev` in
`backend/pyproject.toml`.

### 3. Frontend
```powershell
cd frontend
npm install
npm run dev
```
The Vite dev server proxies `/api` to the backend and serves the dashboard at
`http://localhost:5173`.

### Verify
```bash
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready   # needs the database reachable
```

## Testing

**Backend (pytest)** — from `backend/`:
```powershell
.\.venv\Scripts\python.exe -m pytest
```
Requires PostgreSQL running (see above). Tests run against a dedicated
`ali_trading_test` database (see "Databases" below), not the development
database. Current full-suite result: **54 passed, 0 failed, 0 errors, 0
skipped** (`test_auth_flow_e2e.py`, `test_trading_api.py`,
`test_trading_db_invariants.py` combined).

**Frontend (Playwright E2E)** — from `frontend/`:
```powershell
npm run test:e2e
```
Most tests run against the normal dev stack (`:5173` → backend `:8000` →
`ali_trading`, using the seeded `testuser` account); the tests that
permanently create a new user run against an isolated stack (`:5174` →
backend `:8001` → `ali_trading_e2e`) instead, so they never write to the
shared `ali_trading` database. See `frontend/e2e/global-setup.ts` and
`backend/.env.e2e` for the isolated-stack wiring.

This project does **not** restore the ~340-test historical suite referenced
in earlier (lost) phase reports — only the tests that actually exist in this
recovered codebase (54 backend + 10 frontend E2E, as of the last verified
run) exist and run. See `RECOVERY_MANIFEST.md` for the full test-coverage
history.

## Migrations

Alembic is configured and has one applied migration:
`backend/alembic/versions/c58385829d11_initial_schema.py` (single head,
no down-revision — this is the initial schema for the 14 tables this MVP
covers). Run `alembic upgrade head` from `backend/` after pointing `.env` at
a reachable PostgreSQL instance. `backend/alembic/env.py` overrides
`sqlalchemy.url` from application settings at runtime, regardless of what's
in `alembic.ini`.

## Databases

This project uses **three separate PostgreSQL databases**, on the same local
instance, kept strictly isolated from each other:

| Database | Used by | Notes |
|---|---|---|
| `ali_trading` | The normal dev backend (`:8000`) and frontend (`:5173`) | The real/protected application database. Contains the seeded `testuser` account. Schema managed by Alembic. Treat as precious — do not reset or drop it casually. |
| `ali_trading_test` | The backend pytest suite (`backend/tests/conftest.py` swaps the URL from `ali_trading` to this database) | Schema is created/dropped per test session via SQLAlchemy `Base.metadata`, **not** Alembic — this is a different schema-management path from the other two databases, and switching between it and Alembic-managed state can require a manual schema reset. |
| `ali_trading_e2e` | The isolated Playwright E2E path (backend `:8001`, frontend `:5174`, configured via `backend/.env.e2e`) | Schema managed by Alembic, like `ali_trading`. Exists specifically so the E2E tests that register real, permanent users never touch `ali_trading`. |

## Secrets

`backend/.env` and `backend/.env.e2e` contain real local secrets (database
credentials) and are **never** committed — both are excluded via
`.gitignore`, and only `backend/.env.example` (a template with no real
values) is tracked. Do not add real values to `.env.example`, and
double-check `git status`/`git diff` before committing if you ever touch
these files.

## Further reading

For the complete recovery history — every file's archive source, every
conflict resolved between archives, every patch applied, every bug found and
fixed, the full list of known gaps and their closure status, and detailed
phase-by-phase verification results — see
**[`RECOVERY_MANIFEST.md`](RECOVERY_MANIFEST.md)**.
