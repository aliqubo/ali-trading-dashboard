# RECOVERY_MANIFEST.md

## Scope and disclaimer

This directory is the output of an **8–12 hour recovery MVP sprint**, reconstructing a runnable local backend from 18 zip archives (`files.zip`–`files17.zip`) after the original Phase 1 project state was lost. It restores the **Identity** and **Trading** domains only, plus the minimum Phase 1 runtime scaffolding needed to boot.

**This is explicitly not a full or exact restoration of the original project.** The original design covered 55 database tables across 11 domains (Identity, Market, Watchlist, Trading, Trade Journal, Strategy, Indicator, Alert, News, Portfolio, AI, System). This MVP covers 14 of those tables (8 Identity + 6 Trading). See "Known missing / excluded scope" below for the complete gap list.

None of `files.zip`–`files17.zip` were ever modified, renamed, moved, or deleted during this sprint. Two pre-existing extracted folders, `files1/` and `files17/`, were present before this sprint began and were only read from, never written to.

**Environment used for validation:** Python 3.14.6 (no 3.12 interpreter was available on the machine; the project's own `pyproject.toml`/`mypy`/`ruff` config targets 3.12). No local PostgreSQL instance was available, so all database-dependent behavior is unvalidated — see "Validation status."

---

## 1. Files copied verbatim from archives

| Destination (relative to `backend/`) | Source archive |
|---|---|
| `../README.md` | files.zip |
| `pyproject.toml` (base; later patched, see §3) | files.zip |
| `.env.example` | files.zip |
| `app/main.py` (later patched, see §3) | files1.zip |
| `app/core/config.py` | files15.zip (cumulative superset of files1.zip's fail-fast version) |
| `app/core/exception_handlers.py` | files1.zip |
| `app/models/base.py` | files2.zip |
| `app/models/mixins.py` | files2.zip |
| `app/models/enums.py` | files3.zip (fixed version, supersedes files2.zip) |
| `app/models/identity.py` (later patched, see §3) | files3.zip (fixed version, supersedes files2.zip) |
| `app/models/trading.py` (later patched, see §3) | files2.zip (**only copy that ever existed** — the enum/timezone fix applied to identity.py in files3.zip was never applied to trading.py in any archive; this sprint applied the equivalent fix) |
| `alembic/env.py` | files4.zip |
| `alembic/versions/c58385829d11_initial_schema.py` | files4.zip |
| `app/repositories/base.py` | files5.zip |
| `app/repositories/specification.py` | files5.zip |
| `app/repositories/query.py` | files5.zip |
| `app/repositories/types.py` | files5.zip |
| `app/repositories/exceptions.py` | files5.zip |
| `app/repositories/interfaces.py` | files10.zip (byte-identical to files11.zip; files10 picked arbitrarily) |
| `app/repositories/unit_of_work.py` (later patched, see §3) | files10.zip (byte-identical to files11.zip) |
| `app/repositories/identity/user_repository.py` | files6.zip |
| `app/repositories/identity/session_repository.py` | files6.zip |
| `app/repositories/identity/refresh_token_repository.py` | files6.zip |
| `app/repositories/identity/api_key_repository.py` | files6.zip |
| `app/repositories/identity/__init__.py` (later patched, see §3) | files6.zip |
| `app/repositories/trading/order_repository.py` | files8.zip |
| `app/repositories/trading/execution_repository.py` | files8.zip |
| `app/repositories/trading/position_repository.py` | files8.zip |
| `app/repositories/trading/trade_repository.py` | files8.zip |
| `app/repositories/trading/trade_journal_repository.py` | files8.zip (**restored but orphaned/unimported** — see §6) |
| `app/repositories/trading/order_history_repository.py` | files9.zip |
| `app/repositories/trading/__init__.py` (later patched, see §3) | files8.zip |
| `app/services/interfaces.py` | files12.zip |
| `app/services/base.py` | files12.zip |
| `app/services/identity/interfaces.py` | files12.zip (stored under a mislabeled nested path `mnt/user-data/outputs/...` inside the archive — a packaging artifact, not a real duplicate; content retargeted to its correct path) |
| `app/services/identity/dtos.py` | files12.zip |
| `app/services/identity/validation.py` | files12.zip |
| `app/services/identity/mapping.py` | files12.zip |
| `app/core/security/interfaces.py` | files13.zip |
| `app/core/security/password_hasher.py` | files13.zip |
| `app/core/security/policy.py` | files13.zip |
| `app/core/security/exceptions.py` | files13.zip |
| `app/core/security/token/interfaces.py` | files15.zip |
| `app/core/security/token/jwt_token_service.py` | files15.zip |
| `app/core/security/token/claims.py` | files15.zip |
| `app/core/security/token/exceptions.py` | files15.zip |
| `app/services/authentication/authentication_service.py` | files14.zip |
| `app/services/authentication/results.py` | files14.zip |
| `app/services/authentication/interfaces.py` | files16.zip (supersedes files14.zip — verified superset by diff) |
| `app/services/authentication/exceptions.py` | files16.zip (supersedes files14.zip — verified superset by diff) |
| `app/services/authentication/session_service.py` | files16.zip |
| `app/services/authentication/refresh_token_service.py` | files16.zip |
| `app/services/authentication/token_records.py` | files16.zip |
| `app/services/authorization/interfaces.py` | files17.zip |
| `app/services/authorization/authorization_service.py` | files17.zip |
| `app/services/authorization/exceptions.py` | files17.zip |

---

## 2. Conflicts resolved (archive vs. archive)

| Path | Chosen version | Why |
|---|---|---|
| `app/main.py`, `app/core/config.py` | files1.zip / files15.zip | files.zip's originals were pre-audit-fix; superseded by verified-superset diffs |
| `app/models/enums.py`, `app/models/identity.py` | files3.zip | Pure-additive fix vs files2.zip, confirmed by diff (enum casing, timezone, `uq_users_phone`) |
| `app/repositories/interfaces.py`, `app/repositories/unit_of_work.py` | files10.zip (= files11.zip) | Byte-identical duplicate archives (md5-verified); no real conflict |
| `app/services/authentication/interfaces.py`, `exceptions.py` | files16.zip | Verified to reproduce files14.zip's content verbatim, plus additions — a true superset, not a rewrite |
| `app/services/identity/interfaces.py` | files12.zip, nested path | Not a duplicate — a single mislabeled path in one archive; retargeted, not merged |

---

## 3. Files patched/trimmed (archived originals, edited for this sprint)

| File | What changed | Phase |
|---|---|---|
| `app/models/identity.py` | Removed 15 `relationship()` attributes on `User` pointing at models absent from this MVP (Watchlist, Strategy, Alert, AlertHistory, Notification, Portfolio, RiskProfile, RiskLog, TradeJournal, TradeNote, TradeScreenshot, AIAnalysis, PromptHistory, AuditLog, ApplicationSetting). Trimmed `TYPE_CHECKING` imports accordingly. | 2 |
| `app/models/trading.py` | Removed 8 `relationship()` attributes pointing at Symbol/Strategy/RiskLog/TradeJournal (FK *columns* like `symbol_id` were kept intact — only the ORM relationship wiring was removed). Converted all 10 `PgEnum(...)` calls to `pg_enum(...)`. Added `DateTime(timezone=True)` to 6 columns that lacked it: `submitted_at`, `closed_at`, `executed_at`, `opened_at`, `entry_at`, `exit_at` (2 more than originally estimated from a partial grep — found on a full file read). | 2 |
| `app/repositories/identity/__init__.py` | Added exports for the 4 reconstructed RBAC repositories (§4). Content now matches the archived export list exactly. | 2 |
| `app/repositories/trading/__init__.py` | Dropped exports for `PositionHistoryRepository`/`TradeNoteRepository`/`TradeScreenshotRepository` (files absent from every archive). Added `OrderHistoryRepository` (file existed but was never exported). Later dropped `TradeJournalRepository` (§6). | 2, 4 |
| `app/repositories/unit_of_work.py` | Trimmed from the archived 55-property/9-import-block version to 14 properties across 2 domains (8 identity incl. RBAC, 6 trading). Later trimmed to 13 properties (removed `trade_journal`, §6). Session/transaction machinery (`begin/commit/rollback/flush/refresh/close`, context manager, `_get` cache) left untouched throughout. | 2, 4 |
| `app/main.py` | Removed Redis/cache wiring (`init_redis`/`close_redis`, `app.cache.redis_client` import) — out of this sprint's scope. Changed router import from `app.api.v1.router` to `app.api.router` (no versioned domain endpoints exist in this MVP). | 2 |
| `backend/pyproject.toml` | Added `email-validator>=2.2,<3.0`, `argon2-cffi>=23.1,<24.0`, `PyJWT>=2.9,<3.0` (each documented as an added dependency in its phase report, but never re-archived). Later widened `asyncpg` from `>=0.30,<0.31` to `>=0.31,<0.32` — 0.30.x has no Python 3.14 Windows wheel, 0.31.0 does; a compatibility fix, not a behavioral change. | 2, 4 |
| `app/api/auth.py` | Added `response_model=None` to the `/auth/logout` route decorator. This fixes a bug in this sprint's own Phase 3 code (a FastAPI behavior where a bare `-> None` return annotation doesn't automatically suppress the response model, which then conflicts with a 204 status) — **not** an archive-inherited issue. | 4 |

---

## 4. Files reconstructed for the MVP (no archive source exists)

All header-commented `Reconstructed MVP scaffolding — original source unavailable.` in the file itself.

**Core runtime scaffolding** (Phase 2 — inferred from `PROJECT_AUDIT_REPORT.md`'s behavioral description and from what already-restored files expect to import):
`app/models/__init__.py` (trimmed 2-domain aggregator), `app/core/exceptions.py` (`AppError`/`NotFoundError`/`UnauthorizedError`/`ForbiddenError`/`ConflictError`/`ValidationAppError` — names proven by usage in already-restored files, not guessed), `app/core/context.py`, `app/core/logging.py`, `app/db/__init__.py`, `app/db/session.py`, `app/middleware/__init__.py`, `app/middleware/request_id.py`, `app/middleware/logging.py`, `app/api/__init__.py`, `app/api/deps.py` (Phase 2 subset), `app/api/router.py`, `app/api/health.py`.

**Package `__init__.py` completion** (Phase 2 addendum): `app/__init__.py`, `app/core/__init__.py`, `app/core/security/__init__.py`, `app/services/__init__.py`, `app/services/identity/__init__.py`, `app/services/authentication/__init__.py`, `app/services/authorization/__init__.py`, `app/repositories/__init__.py` — all minimal namespace-completing stubs. **Exception:** `app/core/security/token/__init__.py` required real re-exports (`ITokenService`, `JWTTokenService`, `TokenClaims`, `TokenType`, 5 token exceptions), because the already-restored `refresh_token_service.py` does a package-level `from app.core.security.token import ITokenService, TokenType`.

**Reconstructed RBAC repositories** (Phase 2, explicitly approved after a scope discussion): `app/repositories/identity/role_repository.py`, `permission_repository.py`, `user_role_repository.py`, `role_permission_repository.py`. These are absent from every archive; the models they wrap (`Role`, `Permission`, `UserRole`, `RolePermission`) do exist in `identity.py`. Built by following the exact `BaseRepository` pattern demonstrated 9 times elsewhere, and the exact method names (`get_by_name`, `get_by_code`, `get_for_user`, `get_for_role`, `get_for_permission`) documented in `PHASE_2_3_2_REPORT.md`'s method table. Without these, `AuthorizationService` (fully archived, files17.zip) would import cleanly but raise `AttributeError` on every call.

**Auth routes** (Phase 3): `app/api/auth.py` — wires the already-restored `AuthenticationService`, `SessionService`, `RefreshTokenService`, `JWTTokenService`, `AuthorizationService` into 5 HTTP routes (`/auth/register`, `/login`, `/refresh`, `/logout`, `/me`). **`/auth/register` specifically is new business logic, not scaffolding** — no `IUserService` implementation (hash password + create user) exists in any of the 18 archives, only its unimplemented Phase 3.0 interface. Approved explicitly as a minimal, clearly-flagged addition so the login flow is testable. It sets `status=ACTIVE` on the new user directly (bypassing the column's own `pending` default), since no email-verification flow exists anywhere to move a user from `pending` to `active` — without this, a freshly registered user could never log in.

**Alembic bootstrap** (Phase 4): `alembic.ini` — standard Alembic-generated boilerplate (`script_location` + standard logging sections), no project-specific values. `env.py` (archived, files4.zip) overrides `sqlalchemy.url` from `Settings.alembic_database_url` at runtime regardless of what's in this file.

---

## 5. Known missing / excluded scope

**Entirely absent from every one of the 18 archives:**
- 9 of 11 domain model files: `app/models/{market,watchlist,trade_journal,strategy,alert,news,portfolio,ai,system}.py`.
- An entire phase's worth of repositories — "Phase 2.3.5" (Portfolio/Risk/AI/Alerts/News/Settings/Audit, ~20 files across 7 domains) — no archive and no report exist for it; its only trace is a retrospective count in `PHASE_2_3_5C_REPORT.md`.
- The 4 frozen governing specifications: `ARCHITECTURE.md`, `DATABASE_DESIGN.md`, `BACKEND_SPECIFICATION.md`, `SYSTEM_DESIGN.md` — referenced constantly, never archived.
- The entire historical test suite (all phases combined report ~340 tests; zero test files exist in any archive).
- `Dockerfile`, `docker-compose.dev.yml`, `deploy/nginx/*`, `.github/workflows/*`, `requirements-dev.txt`, `Makefile`.

**Deliberately excluded from this MVP's active scope** (per your instructions):
- Portfolio, Risk, AI, Alerts, News, Settings, Audit domains — not recreated.
- Market, Watchlist, Strategy, Indicator domains — their repositories exist in archives (files7.zip, files9.zip) but their backing models (`market.py`, `watchlist.py`, `strategy.py`, `indicator` classes) don't; excluded from this MVP rather than inventing the models.
- Docker, CI/CD, deployment, production infrastructure — none created.
- Redis/cache — wiring dropped from `main.py`; `redis` remains an unused dependency in `pyproject.toml` (pre-existing, not removed without being asked to).

**Orphaned within the restored code itself:**
- `app/repositories/trading/trade_journal_repository.py` — its file is restored (files8.zip) and syntactically valid, but it imports `TradeJournal`/`TradeNote` from `app.models`, and `app/models/trade_journal.py` is one of the 9 missing model files above. A read-only dependency audit (Phase 4) confirmed zero other consumers depend on it and found no archive evidence it was meant to be excluded — the opposite: `PHASE_2_3_4_REPORT.md` presents it as fully built and tested. It was removed from `trading/__init__.py` and `unit_of_work.py`'s wiring only; the file itself is untouched on disk, ready to be re-wired if `trade_journal.py` is ever reconstructed.

---

## 6. Bugs found and fixed during Phase 4 validation

| Issue | Root cause | Fix | Category |
|---|---|---|---|
| `pip install .` fails to build | `pyproject.toml`'s `readme = "../README.md"` points outside `backend/`; modern setuptools refuses to package a file outside the build root | **Worked around, not fixed** — dependencies installed directly by name instead of via a project wheel build; the project is still not installable as a real package | Archive-inherited |
| `asyncpg` install fails (needs MSVC C++ Build Tools) | Pinned range `>=0.30,<0.31` excludes 0.31.0, the only version with a Python 3.14 Windows wheel | Verified via PyPI, then widened the pin to `>=0.31,<0.32` and installed 0.31.0 | Environment (3.14 vs targeted 3.12) |
| `ImportError: cannot import name 'TradeJournal'` | `trade_journal_repository.py` depends on the missing `trade_journal.py` model | Audited (§5), then removed from `trading/__init__.py` + `unit_of_work.py` | Archive-inherited |
| `AssertionError: Status code 204 must not have a response body` | `/auth/logout`'s `-> None` annotation doesn't suppress FastAPI's response-model construction | Added `response_model=None` explicitly | **Introduced in this sprint's Phase 3 code** |
| `pydantic_core.ValidationError: 1 validation error for SessionResponse / ip_address — Input should be a valid string [type=string_type, input_value=IPv4Address(...)]` on every `/auth/login` call | `app/models/identity.py`'s `sessions.ip_address` column is `postgresql.INET`, which the psycopg driver decodes to `ipaddress.IPv4Address`/`IPv6Address` at runtime regardless of the ORM's `Mapped[str \| None]` annotation; `SessionResponse.ip_address` (`app/services/identity/dtos.py`) is typed `str` and pydantic v2 does not auto-coerce an `IPv4Address`/`IPv6Address` to `str` | Added a `field_validator("ip_address", mode="before")` on `SessionResponse` that coerces `IPv4Address`/`IPv6Address` to `str` | Archive-inherited; only surfaced once `/auth/login` was first exercised end-to-end against a live local PostgreSQL instance (2026-08-24, post-Phase-4 validation session) |
| `sqlalchemy.exc.NoReferencedTableError: Foreign key associated with column 'orders.symbol_id' could not find table 'symbols'` on any `Order`/`Execution`/`Position`/`Trade` insert | `app/models/trading.py`'s `symbol_id`/`strategy_id` columns carried ORM-level `ForeignKey("symbols.id"/"strategies.id")`; neither `symbols` nor `strategies` has a registered SQLAlchemy model in this MVP (Market/Strategy domains excluded), so SQLAlchemy cannot resolve them when sorting insert dependencies at flush time — this blocked every insert into all four Trading tables, not just rows populating those columns | Removed the ORM-level `ForeignKey` object on all 6 affected columns (`Order.symbol_id`, `Order.strategy_id`, `Execution.symbol_id`, `Position.symbol_id`, `Trade.symbol_id`, `Trade.strategy_id`); the columns themselves and the real Postgres-level FK constraints (from the migration) are unchanged | Archive-inherited; only surfaced once the first `Order`/`Trade` insert was attempted (the trading-dashboard sample-data seed script, 2026-08-24) — same class of gap as the `ip_address` bug, just never exercised until real writes were attempted |
| Numeric (`Decimal`) fields in the new Trading DTOs would have hit the same failure mode as `ip_address` | `postgresql.Numeric` columns decode to `decimal.Decimal` at the driver level (psycopg/asyncpg), not `float`, regardless of the ORM's `Mapped[float]` annotation | `app/services/trading/dtos.py`'s response DTOs (`OrderResponse`, `PositionResponse`, `ExecutionResponse`, `TradeResponse`) carry a `field_validator(mode="before")` on every numeric field, coercing `Decimal` to `float` — added proactively, verified via a live query against the running Postgres instance, before the trading endpoints ever served real data | Archive-inherited class of gap (same root cause as `ip_address`); caught before it could 500 in production, unlike the `ip_address` case |

---

## 7. Environment and exact commands to run locally

```powershell
# From: C:\Users\User\Desktop\ali trading center\ali-trading-dashboard\backend

# 1. Virtual environment (already created this sprint)
python -m venv .venv

# 2. Install dependencies — NOT `pip install .` (fails, see §6). Install directly:
.\.venv\Scripts\python.exe -m pip install `
  "fastapi>=0.115,<0.116" "uvicorn[standard]>=0.34,<0.35" `
  "pydantic>=2.9,<3.0" "pydantic-settings>=2.5,<3.0" "email-validator>=2.2,<3.0" `
  "sqlalchemy[asyncio]>=2.0,<2.1" "asyncpg==0.31.0" "psycopg[binary]>=3.2,<3.3" `
  "alembic>=1.14,<1.15" "redis>=5.2,<6.0" "python-dotenv>=1.0,<2.0" `
  "argon2-cffi>=23.1,<24.0" "PyJWT>=2.9,<3.0"

# 3. Configure environment
Copy-Item .env.example .env
# Edit .env with real PostgreSQL connection details — the documented
# defaults (postgres_user=ali, postgres_password=ali_password,
# postgres_db=ali_trading, host=postgres, port=5432) assume a container
# hostname that won't resolve locally; point postgres_host at your actual
# local instance (e.g. localhost).

# 4. Run migrations (needs a live PostgreSQL 16 — NOT validated this sprint)
.\.venv\Scripts\python.exe -m alembic upgrade head

# 5. Start the app
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 6. Verify
curl.exe http://127.0.0.1:8000/health/live
curl.exe http://127.0.0.1:8000/health/ready   # needs step 4 done against a real DB
curl.exe -X POST http://127.0.0.1:8000/auth/register -H "Content-Type: application/json" `
  -d '{\"email\":\"a@example.com\",\"username\":\"alice\",\"password\":\"correct horse battery\"}'
curl.exe -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" `
  -d '{\"identifier\":\"alice\",\"password\":\"correct horse battery\"}'
```

Discovery-only, no DB needed:
```powershell
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m alembic history
```

---

## 8. Validation status (Phase 4, this sprint)

| Item | Status |
|---|---|
| All restored/patched/reconstructed modules import cleanly | ✅ Verified (`python -c "import app.main"`) |
| App boots, structured JSON logging works | ✅ Verified (live process, log inspected) |
| `GET /health/live` | ✅ Verified — `200 {"status":"ok"}` |
| `GET /health/ready`, `GET /health` (DB unreachable) | ✅ Verified — graceful `503`, not a crash |
| `GET /health/ready`, `GET /health` (DB reachable, 200 path) | ❌ Not validated — no local PostgreSQL available |
| Alembic migration discovery (`heads`/`history`) | ✅ Verified — single head `c58385829d11`, no down-revision |
| `alembic upgrade head` actually applying schema | ❌ Not validated |
| `/auth/register` → `/auth/login` → `/auth/refresh` → `/auth/me` end-to-end | ❌ Not validated (routes load and register correctly; behavior against a live DB is unverified) |
| `pip install .` as a real installable package | ❌ Fails; worked around only |
| Historical test suite | N/A — does not exist in any archive, never in scope |

---

## 9. Phase 7 — Trading Vertical Slice Hardening

**Purpose:** harden the Trading vertical slice (the read-only `/trading/*` endpoints and the dashboard frontend built on top of them, both added after the Phase 4 validation above) with test coverage and review, following on from the bug fixes recorded in §6. This is a hardening/verification pass on existing functionality — it does not restore or add any domain beyond what §5 already documents as in scope, and does not change the known-missing/excluded scope recorded there.

### 7.2 — ORM/DTO hardening

Inspected the Trading ORM models, DTOs, and repositories against the fixes recorded in §6, and added `backend/tests/test_trading_api.py` to verify, rather than merely assume, the following:
- `symbol_id`/`strategy_id` ORM-FK behavior — verified both columns accept inserts without the `NoReferencedTableError` recorded in §6 (the earlier fix had only been proven for `symbol_id`; `strategy_id` was independently exercised for the first time here).
- `Decimal`/`Numeric` serialization — verified the `field_validator` coercion recorded in §6 actually produces JSON numbers, not strings, across all four Trading response DTOs.
- All four Trading model inserts (`Order`, `Execution`, `Position`, `Trade`) — verified directly with a dedicated regression test, rather than only as a side effect of other tests succeeding.
- Symbol resolution — verified both the successful-resolution path and the `symbol: null` fallback path (the latter is reachable in the isolated test database, which has no real FK constraint on `symbol_id`; it is not reachable in `ali_trading`, where the real constraint from the migration still applies).
- DTO response shapes — verified the exact JSON key set returned by each of the five endpoints.

### 7.3 / 7.4 — Trading API contract hardening

Locked down the HTTP/JSON contract for all five Trading endpoints (`/trading/summary`, `/trading/positions`, `/trading/orders`, `/trading/executions`, `/trading/trades`) against what the frontend actually depends on:
- Top-level JSON types (bare arrays for the four list endpoints, a bare object for summary — not a wrapper object).
- Nullable fields serialize as actual JSON `null` when unset, distinguished from fields with a database `server_default` (which serialize as `0.0`, not `null`).
- Timestamp fields are valid ISO 8601, parseable by `datetime.fromisoformat`.
- Pagination and filter parameters: `limit`/`offset` on `/trading/orders` and `/trading/trades`, `limit` on `/trading/executions`, `status` on `/trading/positions` — all verified against the implementation as it exists, not invented.
- `422` boundary behavior for out-of-range `limit`/`offset` and invalid `status` values.

Final result: **36/36 Trading API tests passing.**

### 7.5 — Dashboard frontend review

Reviewed all five data flows (summary, positions, orders, executions, trades) in the dashboard frontend against the contract verified in 7.3/7.4:
- API integration (endpoint paths, methods, auth headers, 401 handling) and data mapping (field names/types, nullable handling) verified correct.
- UI states — loading, populated, empty-array, and API-error states — verified handled without crashing.
- Frontend production build (`npm run build`) verified clean.
- No production frontend code was changed during this review; no defect was found that warranted a fix.

### 7.6 — Isolated full E2E

Ran the complete Playwright E2E suite twice against an isolated stack (frontend `:5174` → backend `:8001` → `ali_trading_test`), reusing the isolated-backend configuration first set up for this purpose. Result: **9/9 passing, both runs.**

Only the user-registration test in `frontend/e2e/auth.spec.ts` is routed through the isolated `:5174` → `:8001` → `ali_trading_test` path — it is the one test that permanently writes a new user, and isolating it was the explicit purpose of that configuration. The remaining eight tests (the unauthenticated-redirect and wrong-credentials tests, plus all six `dashboard.spec.ts` tests) run against the normal `:5173` → `:8000` → `ali_trading` path, because they depend on the seeded `testuser` account that only exists there.

`ali_trading`'s `users` and `tables` counts were confirmed unchanged by this run. `sessions`/`refresh_tokens` row counts did increase, as an expected, ordinary side effect of the `dashboard.spec.ts` tests logging in as `testuser` on the normal path — not a schema or user-count change.

### 7.7 — Closure regression

After a schema-only reset of `ali_trading_test` (`DROP SCHEMA public CASCADE; CREATE SCHEMA public;`, database and role untouched) to return it to the state the pytest fixtures expect:
- Backend full suite: **43/43 passed** (`tests/test_auth_flow_e2e.py` 7/7, `tests/test_trading_api.py` 36/36).
- Frontend build: clean.
- `ali_trading`: confirmed unchanged throughout — **56 tables, 3 users.**

### Known gaps (Phase 7)

- `ali_trading_test` requires a schema reset when switching between the Alembic-based isolated E2E setup (7.6) and the `Base.metadata`-based pytest fixtures (7.2–7.4, 7.7) — the two are not compatible with each other in the same schema state, and nothing currently automates the reset between them.
- Database-level invariant coverage is incomplete: no test exercises `client_order_id` uniqueness, the partial unique index on open positions, or any `CheckConstraint`.
- Multi-symbol batching in `_resolve_symbols()` is untested — every test in this phase uses exactly one symbol.
- A session-expiry dashboard-redirect gap exists outside the trading-dashboard scope: if the access and refresh tokens both become invalid while the dashboard is open, the user sees an error message rather than being redirected to `/login`. This lives in `frontend/src/api/client.ts`/`frontend/src/auth/AuthContext.tsx`, not in the trading-dashboard files reviewed in 7.5.
- A `pytest-asyncio` deprecation warning (the custom `event_loop` fixture in `backend/tests/conftest.py`) remains deferred — cosmetic, does not affect test results.

---

## 10. Phase 8 — Item 4: Session-Expiry Dashboard Redirect

**Purpose:** close the session-expiry gap recorded above in §7.7 "Known gaps (Phase 7)" — previously, if both the access and refresh tokens became invalid while the dashboard was open, the user saw an API error banner instead of being redirected to `/login`.

### Implementation

- `frontend/src/api/client.ts` now exports `onSessionExpired(listener)`, backed by a module-level listener registry (`sessionExpiredListeners`). When an `auth: true` request receives a `401` and the subsequent background token refresh also fails, `apiRequest()` clears the module's tokens (`setTokens(null)`) and invokes every registered listener before rethrowing the original error to the caller.
- `frontend/src/auth/AuthContext.tsx` subscribes to `onSessionExpired` on mount (inside a `useEffect`) and calls `setUser(null)` when notified.
- No changes were made to `ProtectedRoute` — clearing `user` already drives it into its existing unauthenticated branch, which redirects to `/login`.
- `frontend/e2e/auth.spec.ts` gained a new `test.describe('session expiry while the dashboard is open', ...)` block: it registers a fresh user, logs in, then uses Playwright route interception to force every `**/api/trading/**` call and the `**/api/auth/refresh` call to return `401`, then asserts the app redirects to `/login` instead of leaving a stale dashboard visible.

### Files modified for Item 4

- `frontend/src/api/client.ts`
- `frontend/src/auth/AuthContext.tsx`
- `frontend/e2e/auth.spec.ts`

No backend, database, `conftest.py`, or trading-dashboard application files were changed for Item 4.

### Status — verified

The targeted Playwright session-expiry regression test has been run and passed: **1 passed, 0 failed, 0 skipped, 4.5s.**

- Test: `"redirects to /login once a background refresh fails, instead of leaving a stale dashboard visible"`
- Ran against the isolated E2E path: `:5174` → `:8001` → `ali_trading_e2e`.
- It forced `**/api/trading/**` and `**/api/auth/refresh` to return `401` and confirmed the app redirected to `/login`.
- `ali_trading` and `ali_trading_test` were not touched.
- No Alembic, schema reset, or source changes were performed during the test run.

### Item 5: pytest-asyncio `event_loop` Deprecation Warning

**Purpose:** close the remaining gap recorded in §7.7 "Known gaps (Phase 7)" — the custom session-scoped `event_loop` fixture in `backend/tests/conftest.py` triggered a pytest-asyncio deprecation warning on every backend test run.

### Implementation

- The custom `@pytest.fixture(scope="session") def event_loop()` fixture was removed from `backend/tests/conftest.py`, along with its now-unused `import asyncio` and the now-unused `Generator` import (trimmed from `from typing import AsyncGenerator, Generator` to `from typing import AsyncGenerator`).
- The applied change matched the previously investigated and approved minimal diff exactly — no other lines were touched.
- `pyproject.toml` was **not modified**; `asyncio_mode = "auto"` and the absence of an explicit `asyncio_default_fixture_loop_scope` setting were left as-is.

### Files modified for Item 5

- `backend/tests/conftest.py`

No other file was changed for Item 5.

### Status — VERIFIED / COMPLETE

The full backend test suite was run after the change: **53 passed, 0 failed, 0 errors, 0 skipped.**

- The "event_loop fixture ... has been redefined" deprecation warning is gone from the run's output.
- No event-loop errors occurred: no `RuntimeError: Event loop is closed`, no "Future attached to a different loop", no `MultipleEventLoopsRequestedError`.
- The separate `asyncio_default_fixture_loop_scope` warning (unrelated to this fixture, sourced from `pyproject.toml`) also did not appear in the actual run.
- Remaining warnings are pre-existing Python 3.14 / FastAPI / pytest-asyncio deprecation warnings (`asyncio.iscoroutinefunction`, `asyncio.get_event_loop_policy`), unrelated to this fix.
- `ali_trading` remained unchanged: **3 users before and after.**
- `ali_trading_e2e` remained unchanged: **4 users before and after.**
- Only `ali_trading_test` was touched, as designed (its schema is created/dropped per test via `Base.metadata`, not Alembic).
- No Alembic commands were run; no manual database reset/drop/create was performed.
- PostgreSQL was started only because it was stopped at the time and was required to run the tests.

### DB-Invariant Coverage Completion

**Purpose:** close the remaining gap in the existing DB-invariant coverage work (`backend/tests/test_trading_db_invariants.py`, originally added under this session's internal "Phase 8 Item 2" label — see its module docstring). A read-only inspection found 8 of the 9 real DB-level invariants declared in `backend/app/models/trading.py` already covered by tests, with `Execution.uq_executions_external_exec_id` the only one untested.

### Implementation

- Added `backend/tests/test_trading_db_invariants.py::test_execution_external_exec_id_uniqueness_rejects_duplicate` — creates a valid filled order, commits one execution with a given `external_exec_id`, then asserts a second execution with the same value raises `DuplicateEntityError` whose `__cause__` is a genuine `sqlalchemy.exc.IntegrityError`, following the same pattern as the existing `client_order_id` uniqueness test.
- This closes the previously identified missing invariant: `Execution.uq_executions_external_exec_id`.

All 9 DB-level invariants declared in `backend/app/models/trading.py` are now covered by tests:

1. Order `client_order_id` uniqueness
2. Execution `external_exec_id` uniqueness
3. Position open user+symbol partial unique index (`uq_positions_open_user_symbol`)
4. Order `quantity_positive`
5. Order `filled_le_quantity`
6. Execution `exec_quantity_positive`
7. Execution `exec_price_positive`
8. Position `quantity_non_negative`
9. Trade `quantity_positive`

### Files modified for this addition

- `backend/tests/test_trading_db_invariants.py`

No application code, models, `conftest.py`, frontend code, or `pyproject.toml` was modified for this coverage addition.

### Status — VERIFIED / COMPLETE

- `backend/tests/test_trading_db_invariants.py` now passes **10/10**.
- Full backend suite: **54 passed, 0 failed, 0 errors, 0 skipped.**
- No application defect was found from the new invariant test.
- `ali_trading` remained unchanged: **3 users before and after.**
- Only `ali_trading_test` was used by the pytest fixtures.
- No Alembic was run.

### Full Frontend Playwright Regression (post-Phase-8 verification)

**Purpose:** confirm no regressions across the entire frontend Playwright E2E suite following the completion of Phase 8 Items 4 and 5 and the DB-invariant coverage addition above — a full unfiltered run (`npx playwright test`, no `-g`/grep filter), not just the targeted session-expiry test recorded under Item 4.

**Result: 10 passed, 0 failed, 0 skipped, 28.9s.**

- All authentication tests passed (`frontend/e2e/auth.spec.ts`): unauthenticated root redirect, wrong-credentials rejection, the isolated registration → login → dashboard → logout flow, and the Phase 8 session-expiry regression test.
- The Phase 8 session-expiry regression test passed **1/1**: `"redirects to /login once a background refresh fails, instead of leaving a stale dashboard visible"`.
- All 6 dashboard E2E tests passed (`frontend/e2e/dashboard.spec.ts`): summary cards, positions table, orders table, executions table, trades table, and refresh-without-navigating-away.

**Tested architecture:**

- Normal path: frontend `:5173` → backend `:8000` → `ali_trading`.
- Isolated E2E path: frontend `:5174` → backend `:8001` → `ali_trading_e2e`.
- `ali_trading_test` was not part of either path and was not touched.

**Database verification:**

- `ali_trading`: 56 tables unchanged, 3 users unchanged, Alembic revision unchanged (`c58385829d11`). `sessions` and `refresh_tokens` rows increased 55 → 61 (+6) — an expected side effect of the 6 `dashboard.spec.ts` tests each logging in as the seeded `testuser` account via `beforeEach`, not a schema or user-count change.
- `ali_trading_e2e`: 56 tables unchanged, Alembic revision unchanged (`c58385829d11`). `users`, `sessions`, and `refresh_tokens` rows increased 4 → 6 (+2 each) — an expected side effect of the two tests in `auth.spec.ts` that each register one fresh, permanent user (the isolated registration-flow test and the session-expiry test), not an unexpected mutation.
- `ali_trading_test`: untouched — confirmed not used by this run.
- No Alembic migration, schema reset, database creation/drop, or manual database modification of any kind was performed during this verification.

**Process hygiene:** all five services/processes started for this run (PostgreSQL, backend `:8000`, backend `:8001`, frontend `:5173`, frontend `:5174`) were stopped afterward. Ports 8000, 8001, 5173, 5174, and 5432 were confirmed free once the run completed.

**Files modified for this verification:** none — this was a verification-only run against the existing Phase 8 implementation; no application, test, or configuration files were changed.

### Phase 8 — Closure

- Items 4 (session-expiry dashboard redirect) and 5 (pytest-asyncio `event_loop` deprecation warning) are verified/complete, per the sections above.
- DB-level invariant coverage — the third gap named in §7.7 "Known gaps (Phase 7)" — is now also complete, per the addition documented above.
- Full backend verification currently stands at **54/54** (`tests/test_auth_flow_e2e.py` + `tests/test_trading_api.py` + `tests/test_trading_db_invariants.py`, combined, 0 failed/errors/skipped).
- The full frontend Playwright E2E suite (unfiltered) currently stands at **10/10 passed, 0 failed, 0 skipped**, including the session-expiry regression test at **1/1**, all authentication tests, and all 6 dashboard E2E tests — see "Full Frontend Playwright Regression (post-Phase-8 verification)" above.
- The isolated E2E path continues to use its own dedicated database, `ali_trading_e2e`, kept separate from both `ali_trading` and `ali_trading_test`.
- `ali_trading` remained protected/unchanged throughout all of Phase 8's work (schema, table count, and user count); the same holds for `ali_trading_e2e`'s schema, table count, and Alembic revision, with only the expected user/session/refresh-token row increases documented above.
- **Not** covered by this closure: the §7.7 gap describing the `ali_trading_test` schema-reset incompatibility between the Alembic-based isolated E2E setup and the `Base.metadata`-based pytest fixtures, and the §7.7 gap noting `_resolve_symbols()` multi-symbol batching is untested — neither was addressed during Phase 8, and both remain open.
- This closure does **not** claim that any historical/pre-recovery test suite (the ~340 tests referenced in the lost phase reports, §5/§8) has been restored — only the tests that exist in this recovered codebase were run.
