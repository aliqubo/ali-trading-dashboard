"""Read-only Trading API tests: GET /trading/{summary,positions,orders,executions,trades}.

Runs entirely against the isolated ali_trading_test database via the existing
`client`/`db_session` fixtures in conftest.py (dependency-override pattern,
verified in test_auth_flow_e2e.py) — never ali_trading.

There is no write endpoint for Trading data (Order/Execution/Position/Trade
have no POST routes), so fixtures below seed rows directly through the
existing repositories plus the same parameterized-SQL pattern
backend/scripts/seed_trading_sample_data.py uses for markets/exchanges/symbols
(no ORM model for those three tables in this MVP — Market domain excluded,
see RECOVERY_MANIFEST.md).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork

TRADING_ENDPOINTS = [
    "/trading/summary",
    "/trading/positions",
    "/trading/orders",
    "/trading/executions",
    "/trading/trades",
]


# --- Market-domain infrastructure tables (this test file only) ------------


async def _ensure_market_infrastructure(db_session: AsyncSession) -> None:
    """Create markets/exchanges/symbols in ali_trading_test if not already
    present, using the test's own already-correctly-loop-bound db_session.

    These three tables have no ORM model in this MVP (Market domain
    excluded, see RECOVERY_MANIFEST.md), so conftest.py's
    Base.metadata-based create_all()/drop_all() cycle never creates or
    touches them — but the real Postgres-level symbol_id FK on
    orders/positions/executions/trades still requires an actual symbols
    row to exist. This helper is entirely local to this test file; it does
    not modify conftest.py or application code.

    DDL matches the Alembic migration's column definitions
    (backend/alembic/versions/c58385829d11_initial_schema.py), with one
    intentional omission: symbols.category_id's FK to symbol_categories is
    left off — category_id stays nullable and no test here ever populates
    it, so creating that fourth table too would be unused scope.

    Runs via db_session (not a separate engine) deliberately: an earlier
    version of this helper used its own session-scoped create_async_engine,
    which raised "RuntimeError: ... attached to a different loop" —
    asyncpg connections are bound to the event loop active when they're
    created, and conftest.py's db_session is already function-scoped
    specifically to stay bound to each test's own loop. CREATE TABLE IF NOT
    EXISTS makes the tables idempotent; the enum type needs a plain
    existence check instead of a `DO $$ ... $$` block (Postgres has no
    CREATE TYPE IF NOT EXISTS) — a DO block defaults to the `plpgsql`
    procedural language, which isn't available in ali_trading_test, and
    installing it would edge toward "altering PostgreSQL configuration",
    out of scope for this file.
    """
    type_exists = (
        await db_session.execute(
            text("SELECT 1 FROM pg_type WHERE typname = 'market_type'")
        )
    ).scalar_one_or_none()
    if type_exists is None:
        await db_session.execute(
            text(
                "CREATE TYPE market_type AS ENUM "
                "('stocks', 'forex', 'crypto', 'commodities', 'indices', 'futures')"
            )
        )
    await db_session.execute(
        text(
            "CREATE TABLE IF NOT EXISTS markets ("
            " id uuid PRIMARY KEY DEFAULT gen_random_uuid(),"
            " code varchar(20) NOT NULL UNIQUE,"
            " name varchar(100) NOT NULL,"
            " market_type market_type NOT NULL,"
            " base_currency varchar(10),"
            " is_active boolean NOT NULL DEFAULT true,"
            " created_at timestamptz NOT NULL DEFAULT now(),"
            " updated_at timestamptz NOT NULL DEFAULT now()"
            ")"
        )
    )
    await db_session.execute(
        text(
            "CREATE TABLE IF NOT EXISTS exchanges ("
            " id uuid PRIMARY KEY DEFAULT gen_random_uuid(),"
            " market_id uuid NOT NULL REFERENCES markets(id) ON DELETE RESTRICT,"
            " code varchar(30) NOT NULL UNIQUE,"
            " name varchar(120) NOT NULL,"
            " country varchar(2),"
            " timezone varchar(50) NOT NULL DEFAULT 'UTC',"
            " open_time varchar(8),"
            " close_time varchar(8),"
            " is_active boolean NOT NULL DEFAULT true,"
            " created_at timestamptz NOT NULL DEFAULT now(),"
            " updated_at timestamptz NOT NULL DEFAULT now()"
            ")"
        )
    )
    await db_session.execute(
        text(
            "CREATE TABLE IF NOT EXISTS symbols ("
            " id uuid PRIMARY KEY DEFAULT gen_random_uuid(),"
            " exchange_id uuid NOT NULL REFERENCES exchanges(id) ON DELETE RESTRICT,"
            " market_id uuid NOT NULL REFERENCES markets(id) ON DELETE RESTRICT,"
            " category_id uuid,"
            " ticker varchar(30) NOT NULL,"
            " name varchar(150) NOT NULL,"
            " base_asset varchar(20),"
            " quote_asset varchar(20),"
            " price_precision smallint NOT NULL DEFAULT 2 CHECK (price_precision >= 0),"
            " quantity_precision smallint NOT NULL DEFAULT 2,"
            " min_order_size numeric(24, 8),"
            " tick_size numeric(24, 8),"
            " is_tradable boolean NOT NULL DEFAULT true,"
            " is_active boolean NOT NULL DEFAULT true,"
            " created_at timestamptz NOT NULL DEFAULT now(),"
            " updated_at timestamptz NOT NULL DEFAULT now(),"
            " UNIQUE (exchange_id, ticker)"
            ")"
        )
    )
    await db_session.commit()


# --- Seeding helpers (mirror backend/scripts/seed_trading_sample_data.py) --


async def _insert_symbol(db_session: AsyncSession, *, ticker: str) -> dict:
    """Insert one market + exchange + symbol; return {id, ticker, name}.

    Parameterized SQL only, same as the seed script — no ORM model exists
    for these three tables in this MVP.
    """
    suffix = uuid.uuid4().hex[:8]
    market_id = (
        await db_session.execute(
            text(
                "INSERT INTO markets (code, name, market_type, base_currency, is_active) "
                "VALUES (:code, :name, 'crypto', 'USD', true) RETURNING id"
            ),
            {"code": f"TEST_MKT_{suffix}", "name": f"Test Market {suffix}"},
        )
    ).scalar_one()
    exchange_id = (
        await db_session.execute(
            text(
                "INSERT INTO exchanges (market_id, code, name, timezone, is_active) "
                "VALUES (:market_id, :code, :name, 'UTC', true) RETURNING id"
            ),
            {
                "market_id": market_id,
                "code": f"TEST_EX_{suffix}",
                "name": f"Test Exchange {suffix}",
            },
        )
    ).scalar_one()
    name = f"{ticker} Test Symbol"
    symbol_id = (
        await db_session.execute(
            text(
                "INSERT INTO symbols "
                "(exchange_id, market_id, ticker, name, base_asset, quote_asset, "
                " price_precision, quantity_precision, is_tradable, is_active) "
                "VALUES (:exchange_id, :market_id, :ticker, :name, 'BASE', 'QUOTE', "
                " 2, 8, true, true) RETURNING id"
            ),
            {
                "exchange_id": exchange_id,
                "market_id": market_id,
                "ticker": ticker,
                "name": name,
            },
        )
    ).scalar_one()
    return {"id": symbol_id, "ticker": ticker, "name": name}


async def _seed_full_dataset(
    db_session: AsyncSession, *, user_id: uuid.UUID, symbol_id: uuid.UUID
) -> dict:
    """Insert one of each: open position, open order, filled order + its
    execution, closed trade. Returns the created rows' ids and known values
    for exact-value assertions.
    """
    uow = SqlAlchemyUnitOfWork(lambda: db_session)
    now = datetime.now(UTC)

    position = await uow.positions.create(
        {
            "user_id": user_id,
            "symbol_id": symbol_id,
            "side": "long",
            "quantity": 1.5,
            "avg_entry_price": 100,
            "current_price": 110,
            "unrealized_pnl": 15,
            "realized_pnl": 5,
            "status": "open",
            "opened_at": now - timedelta(days=1),
        }
    )
    open_order = await uow.orders.create(
        {
            "user_id": user_id,
            "symbol_id": symbol_id,
            "side": "buy",
            "order_type": "limit",
            "time_in_force": "gtc",
            "quantity": 2,
            "price": 95,
            "filled_quantity": 0,
            "status": "open",
            "submitted_at": now - timedelta(hours=1),
        }
    )
    filled_order = await uow.orders.create(
        {
            "user_id": user_id,
            "symbol_id": symbol_id,
            "side": "buy",
            "order_type": "market",
            "time_in_force": "gtc",
            "quantity": 1,
            "filled_quantity": 1,
            "avg_fill_price": 100,
            "status": "filled",
            "submitted_at": now - timedelta(days=2),
        }
    )
    execution = await uow.executions.create(
        {
            "order_id": filled_order.id,
            "symbol_id": symbol_id,
            "exec_price": 100,
            "exec_quantity": 1,
            "fee": 0.5,
            "fee_currency": "USD",
            "liquidity": "taker",
            "executed_at": now - timedelta(days=2),
        }
    )
    trade = await uow.trades.create(
        {
            "user_id": user_id,
            "symbol_id": symbol_id,
            "side": "long",
            "entry_price": 100,
            "exit_price": 110,
            "quantity": 1,
            "gross_pnl": 10,
            "net_pnl": 9.5,
            "total_fees": 0.5,
            "return_pct": 10.0,
            "status": "closed",
            "entry_at": now - timedelta(days=2),
            "exit_at": now - timedelta(days=1),
        }
    )
    await uow.commit()

    return {
        "position_id": position.id,
        "open_order_id": open_order.id,
        "filled_order_id": filled_order.id,
        "execution_id": execution.id,
        "trade_id": trade.id,
    }


async def _register_and_login(client: AsyncClient, *, username: str) -> tuple[uuid.UUID, dict]:
    """Register + log in a fresh user; return (user_id, auth_headers)."""
    credentials = {
        "email": f"{username}@example.com",
        "username": username,
        "password": "TestPassword123!",
    }
    register_response = await client.post("/auth/register", json=credentials)
    assert register_response.status_code == 201, register_response.text
    user_id = uuid.UUID(register_response.json()["id"])

    login_response = await client.post(
        "/auth/login",
        json={"identifier": username, "password": credentials["password"]},
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]
    return user_id, {"Authorization": f"Bearer {token}"}


def _make_expired_access_token(subject: str) -> str:
    """Craft a JWT that is valid in every way except already expired.

    Signed with the app's real settings (secret/algorithm/issuer/audience),
    exercising the real verification path in
    app/core/security/token/jwt_token_service.py — this only bypasses
    JWTTokenService.create_access_token()'s use of "now" for `exp`, it does
    not touch or mock any application code.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "jti": str(uuid.uuid4()),
        "type": "access",
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@pytest_asyncio.fixture
async def symbol(db_session: AsyncSession) -> dict:
    await _ensure_market_infrastructure(db_session)
    return await _insert_symbol(db_session, ticker="BTC/USD")


# --- Authenticated happy path ------------------------------------------


async def test_summary_happy_path(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    await _seed_full_dataset(db_session, user_id=user_id, symbol_id=symbol["id"])

    response = await client.get("/trading/summary", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "open_positions_count": 1,
        "open_orders_count": 1,
        "unrealized_pnl_total": 15.0,
        "closed_trades_count": 1,
        "realized_pnl_total": 9.5,
    }


async def test_positions_happy_path(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    seeded = await _seed_full_dataset(db_session, user_id=user_id, symbol_id=symbol["id"])

    response = await client.get("/trading/positions", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    position = body[0]
    assert position["id"] == str(seeded["position_id"])
    assert position["side"] == "long"
    assert position["status"] == "open"
    assert position["quantity"] == 1.5
    assert position["avg_entry_price"] == 100.0
    assert position["unrealized_pnl"] == 15.0
    assert position["realized_pnl"] == 5.0


async def test_orders_happy_path(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    seeded = await _seed_full_dataset(db_session, user_id=user_id, symbol_id=symbol["id"])

    response = await client.get("/trading/orders", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    ids = {order["id"] for order in body}
    assert ids == {str(seeded["open_order_id"]), str(seeded["filled_order_id"])}
    statuses = {order["id"]: order["status"] for order in body}
    assert statuses[str(seeded["open_order_id"])] == "open"
    assert statuses[str(seeded["filled_order_id"])] == "filled"


async def test_executions_happy_path(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    seeded = await _seed_full_dataset(db_session, user_id=user_id, symbol_id=symbol["id"])

    response = await client.get("/trading/executions", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    execution = body[0]
    assert execution["id"] == str(seeded["execution_id"])
    assert execution["order_id"] == str(seeded["filled_order_id"])
    assert execution["exec_price"] == 100.0
    assert execution["exec_quantity"] == 1.0
    assert execution["fee"] == 0.5


async def test_trades_happy_path(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    seeded = await _seed_full_dataset(db_session, user_id=user_id, symbol_id=symbol["id"])

    response = await client.get("/trading/trades", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    trade = body[0]
    assert trade["id"] == str(seeded["trade_id"])
    assert trade["status"] == "closed"
    assert trade["net_pnl"] == 9.5
    assert trade["return_pct"] == 10.0


# --- Unauthenticated / invalid / expired token --------------------------


@pytest.mark.parametrize("path", TRADING_ENDPOINTS)
async def test_unauthenticated_request_returns_401(client: AsyncClient, path: str) -> None:
    response = await client.get(path)
    assert response.status_code == 401


async def test_garbage_token_returns_401(client: AsyncClient) -> None:
    response = await client.get(
        "/trading/summary", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


async def test_expired_token_returns_401(client: AsyncClient, test_user_id) -> None:
    user_id = test_user_id
    expired = _make_expired_access_token(str(user_id))
    response = await client.get(
        "/trading/summary", headers={"Authorization": f"Bearer {expired}"}
    )
    assert response.status_code == 401


# --- User isolation -------------------------------------------------------


async def test_user_isolation_across_all_endpoints(
    client: AsyncClient, db_session: AsyncSession, symbol: dict
) -> None:
    user_a_id, user_a_headers = await _register_and_login(client, username="trader_a")
    user_b_id, user_b_headers = await _register_and_login(client, username="trader_b")

    seeded_a = await _seed_full_dataset(db_session, user_id=user_a_id, symbol_id=symbol["id"])
    seeded_b = await _seed_full_dataset(db_session, user_id=user_b_id, symbol_id=symbol["id"])
    assert seeded_a != seeded_b  # sanity: genuinely distinct rows per user

    for path in TRADING_ENDPOINTS:
        response_a = await client.get(path, headers=user_a_headers)
        response_b = await client.get(path, headers=user_b_headers)
        assert response_a.status_code == 200
        assert response_b.status_code == 200

        body_a, body_b = response_a.json(), response_b.json()
        if path == "/trading/summary":
            # Same shape of data seeded for both -> same counts/sums, but
            # each computed independently from that user's own rows only
            # (verified precisely via the id-level checks on the other
            # four endpoints below).
            assert body_a == body_b
            continue

        ids_a = {row["id"] for row in body_a}
        ids_b = {row["id"] for row in body_b}
        assert ids_a, f"{path}: user A unexpectedly has no rows"
        assert ids_b, f"{path}: user B unexpectedly has no rows"
        assert ids_a.isdisjoint(ids_b), f"{path}: user A and user B share row ids"


# --- Empty trading-data behavior -------------------------------------------


async def test_empty_state_for_user_with_no_trading_data(client: AsyncClient) -> None:
    _user_id, headers = await _register_and_login(client, username="trader_empty")

    summary = await client.get("/trading/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json() == {
        "open_positions_count": 0,
        "open_orders_count": 0,
        "unrealized_pnl_total": 0.0,
        "closed_trades_count": 0,
        "realized_pnl_total": 0.0,
    }

    for path in ("/trading/positions", "/trading/orders", "/trading/executions", "/trading/trades"):
        response = await client.get(path, headers=headers)
        assert response.status_code == 200
        assert response.json() == []


# --- Response structure / types matching frontend/src/api/trading.ts ------


async def test_order_response_shape_matches_frontend_contract(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    await _seed_full_dataset(db_session, user_id=user_id, symbol_id=symbol["id"])

    response = await client.get("/trading/orders", headers=auth_headers)
    order = response.json()[0]

    # Exact key set expected by frontend/src/api/trading.ts's OrderRow.
    assert set(order.keys()) == {
        "id",
        "symbol",
        "side",
        "order_type",
        "time_in_force",
        "quantity",
        "price",
        "stop_price",
        "filled_quantity",
        "avg_fill_price",
        "status",
        "reject_reason",
        "submitted_at",
        "created_at",
        "updated_at",
    }
    assert set(order["symbol"].keys()) == {"id", "ticker", "name"}


async def test_summary_response_shape_matches_frontend_contract(
    client: AsyncClient, auth_headers: dict
) -> None:
    response = await client.get("/trading/summary", headers=auth_headers)
    assert set(response.json().keys()) == {
        "open_positions_count",
        "open_orders_count",
        "unrealized_pnl_total",
        "closed_trades_count",
        "realized_pnl_total",
    }


# --- Decimal/numeric serialization -----------------------------------------


async def test_numeric_fields_serialize_as_json_numbers_not_strings(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    """Guards the exact bug class documented in RECOVERY_MANIFEST.md: Numeric
    columns decode to decimal.Decimal at the driver level, which the DTOs'
    field_validator(mode="before") must coerce to float before serialization.
    """
    user_id = test_user_id
    await _seed_full_dataset(db_session, user_id=user_id, symbol_id=symbol["id"])

    position = (await client.get("/trading/positions", headers=auth_headers)).json()[0]
    for field in ("quantity", "avg_entry_price", "current_price", "unrealized_pnl", "realized_pnl"):
        assert isinstance(position[field], float), f"{field} was {type(position[field])!r}"

    trade = (await client.get("/trading/trades", headers=auth_headers)).json()[0]
    for field in ("entry_price", "exit_price", "quantity", "gross_pnl", "net_pnl", "total_fees", "return_pct"):
        assert isinstance(trade[field], float), f"{field} was {type(trade[field])!r}"

    orders = (await client.get("/trading/orders", headers=auth_headers)).json()
    filled_order = next(o for o in orders if o["status"] == "filled")
    for field in ("quantity", "filled_quantity", "avg_fill_price"):
        assert isinstance(filled_order[field], float), f"{field} was {type(filled_order[field])!r}"

    execution = (await client.get("/trading/executions", headers=auth_headers)).json()[0]
    for field in ("exec_price", "exec_quantity", "fee"):
        assert isinstance(execution[field], float), f"{field} was {type(execution[field])!r}"


# --- Symbol resolution -------------------------------------------------


async def test_symbol_resolution_returns_correct_ticker_and_name(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    await _seed_full_dataset(db_session, user_id=user_id, symbol_id=symbol["id"])

    for path in ("/trading/positions", "/trading/orders", "/trading/executions", "/trading/trades"):
        response = await client.get(path, headers=auth_headers)
        rows = response.json()
        assert rows, f"{path}: expected at least one row"
        for row in rows:
            assert row["symbol"] is not None, f"{path}: symbol was not resolved"
            assert row["symbol"]["id"] == str(symbol["id"])
            assert row["symbol"]["ticker"] == symbol["ticker"]
            assert row["symbol"]["name"] == symbol["name"]


async def test_symbol_resolution_returns_null_when_symbol_row_is_missing(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    """_resolve_symbols()/the response builders must degrade to `symbol:
    null`, not crash, when a symbol_id has no matching row in `symbols`.

    Unreachable in the real ali_trading (a live Postgres FK constraint from
    the Alembic migration guarantees symbol_id always resolves there) but IS
    reachable in ali_trading_test's Base.metadata-create_all()-built schema,
    which has no such constraint (see the ORM-FK-removal notes in
    app/models/trading.py) — this exercises the defensive fallback that
    would otherwise be untestable. Depends on `symbol` only so the `symbols`
    table itself exists; deliberately does not use symbol["id"].
    """
    user_id = test_user_id
    dangling_symbol_id = uuid.uuid4()  # no row in `symbols` for this id
    uow = SqlAlchemyUnitOfWork(lambda: db_session)
    await uow.positions.create(
        {
            "user_id": user_id,
            "symbol_id": dangling_symbol_id,
            "side": "long",
            "quantity": 1,
            "avg_entry_price": 100,
            "status": "open",
        }
    )
    await uow.commit()

    response = await client.get("/trading/positions", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["symbol"] is None


async def test_symbol_resolution_maps_multiple_symbols_independently(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id
) -> None:
    """_resolve_symbols() batches a *set* of symbol_ids into one lookup dict.

    Every other symbol-resolution test in this file uses exactly one
    symbol_id (via the `symbol` fixture), so a bug that collapsed every row
    onto the first (or last) resolved symbol in the batch would go
    undetected. This seeds two distinct symbols and one order per symbol for
    the same user, then asserts each order's returned symbol matches its own
    symbol_id — and that the two resolved symbols are not the same one.
    """
    await _ensure_market_infrastructure(db_session)
    symbol_a = await _insert_symbol(db_session, ticker="AAA/USD")
    symbol_b = await _insert_symbol(db_session, ticker="BBB/USD")
    assert symbol_a["id"] != symbol_b["id"]  # sanity: genuinely distinct rows

    user_id = test_user_id
    uow = SqlAlchemyUnitOfWork(lambda: db_session)
    order_a = await uow.orders.create(
        {
            "user_id": user_id,
            "symbol_id": symbol_a["id"],
            "side": "buy",
            "order_type": "limit",
            "time_in_force": "gtc",
            "quantity": 1,
            "price": 100,
            "status": "open",
        }
    )
    order_b = await uow.orders.create(
        {
            "user_id": user_id,
            "symbol_id": symbol_b["id"],
            "side": "sell",
            "order_type": "limit",
            "time_in_force": "gtc",
            "quantity": 2,
            "price": 200,
            "status": "open",
        }
    )
    await uow.commit()

    response = await client.get("/trading/orders", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2

    by_id = {row["id"]: row for row in body}
    resolved_a = by_id[str(order_a.id)]["symbol"]
    resolved_b = by_id[str(order_b.id)]["symbol"]

    assert resolved_a is not None
    assert resolved_b is not None
    assert resolved_a["id"] == str(symbol_a["id"])
    assert resolved_a["ticker"] == symbol_a["ticker"]
    assert resolved_b["id"] == str(symbol_b["id"])
    assert resolved_b["ticker"] == symbol_b["ticker"]

    # Explicit guard against every row collapsing onto the same symbol
    # (e.g. always the first or last id resolved in the batch).
    assert resolved_a["id"] != resolved_b["id"]


# --- ORM FK hardening: strategy_id, and an explicit insert regression -----


async def test_strategy_id_accepts_a_value_without_orm_fk_error(
    db_session: AsyncSession, test_user_id, symbol: dict
) -> None:
    """Phase 6 removed the ORM-level ForeignKey("strategies.id") object from
    Order.strategy_id/Trade.strategy_id (no Strategy model in this MVP) —
    the same fix already proven for symbol_id by every other test in this
    file. strategy_id itself was never independently exercised with a
    non-null value anywhere; this closes that gap directly rather than
    relying on "it's the same code path as symbol_id" as an inference.

    The real ali_trading migration does define
    fk_orders_strategy_id_strategies/fk_trades_strategy_id_strategies —
    confirmed by inspection — but since strategy_id is nullable and every
    other test leaves it NULL, that constraint is never exercised either;
    ali_trading_test's create_all()-built schema has no such constraint at
    all, so any UUID is accepted here.
    """
    user_id = test_user_id
    fake_strategy_id = uuid.uuid4()
    uow = SqlAlchemyUnitOfWork(lambda: db_session)
    order = await uow.orders.create(
        {
            "user_id": user_id,
            "symbol_id": symbol["id"],
            "strategy_id": fake_strategy_id,
            "side": "buy",
            "order_type": "market",
            "time_in_force": "gtc",
            "quantity": 1,
            "filled_quantity": 1,
            "avg_fill_price": 100,
            "status": "filled",
        }
    )
    trade = await uow.trades.create(
        {
            "user_id": user_id,
            "symbol_id": symbol["id"],
            "strategy_id": fake_strategy_id,
            "side": "long",
            "entry_price": 100,
            "quantity": 1,
            "status": "open",
            "entry_at": datetime.now(UTC),
        }
    )
    await uow.commit()
    assert order.strategy_id == fake_strategy_id
    assert trade.strategy_id == fake_strategy_id


async def test_all_four_trading_models_insert_without_orm_fk_error(
    db_session: AsyncSession, test_user_id, symbol: dict
) -> None:
    """Explicit, self-documenting regression test for the Phase 6 bug
    (sqlalchemy.exc.NoReferencedTableError at flush time, from the since-
    removed ORM-level ForeignKey("symbols.id"/"strategies.id") objects).
    Every other test in this file only exercises this as a side effect of
    _seed_full_dataset succeeding; this isolates the concern under its own
    name so a future regression here fails clearly and specifically.
    """
    seeded = await _seed_full_dataset(db_session, user_id=test_user_id, symbol_id=symbol["id"])
    assert all(seeded.values())  # every one of the 4 rows' ids is present


# --- DTO / response-shape hardening: Position, Execution, Trade -----------


async def test_position_response_shape_matches_frontend_contract(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    await _seed_full_dataset(db_session, user_id=user_id, symbol_id=symbol["id"])
    response = await client.get("/trading/positions", headers=auth_headers)
    position = response.json()[0]
    assert set(position.keys()) == {
        "id",
        "symbol",
        "side",
        "quantity",
        "avg_entry_price",
        "current_price",
        "unrealized_pnl",
        "realized_pnl",
        "status",
        "opened_at",
        "closed_at",
    }
    assert set(position["symbol"].keys()) == {"id", "ticker", "name"}


async def test_execution_response_shape_matches_frontend_contract(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    await _seed_full_dataset(db_session, user_id=user_id, symbol_id=symbol["id"])
    response = await client.get("/trading/executions", headers=auth_headers)
    execution = response.json()[0]
    assert set(execution.keys()) == {
        "id",
        "order_id",
        "symbol",
        "exec_price",
        "exec_quantity",
        "fee",
        "fee_currency",
        "liquidity",
        "executed_at",
    }
    assert set(execution["symbol"].keys()) == {"id", "ticker", "name"}


async def test_trade_response_shape_matches_frontend_contract(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    await _seed_full_dataset(db_session, user_id=user_id, symbol_id=symbol["id"])
    response = await client.get("/trading/trades", headers=auth_headers)
    trade = response.json()[0]
    assert set(trade.keys()) == {
        "id",
        "symbol",
        "side",
        "entry_price",
        "exit_price",
        "quantity",
        "gross_pnl",
        "net_pnl",
        "total_fees",
        "return_pct",
        "status",
        "entry_at",
        "exit_at",
    }
    assert set(trade["symbol"].keys()) == {"id", "ticker", "name"}


# --- Phase 7.4: top-level JSON structure (array vs. object) ---------------


async def test_list_endpoints_return_bare_json_arrays(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    """frontend/src/api/trading.ts types every list endpoint's response
    directly as e.g. PositionRow[] — never {items: [...]} or similar. A
    bare `len()` check alone doesn't distinguish a list from a same-sized
    dict; this asserts the actual JSON type explicitly.
    """
    user_id = test_user_id
    await _seed_full_dataset(db_session, user_id=user_id, symbol_id=symbol["id"])

    for path in ("/trading/positions", "/trading/orders", "/trading/executions", "/trading/trades"):
        body = (await client.get(path, headers=auth_headers)).json()
        assert isinstance(body, list), f"{path}: expected a JSON array, got {type(body).__name__}"
        assert all(isinstance(row, dict) for row in body), f"{path}: row was not a JSON object"


async def test_summary_returns_bare_json_object(client: AsyncClient, auth_headers: dict) -> None:
    body = (await client.get("/trading/summary", headers=auth_headers)).json()
    assert isinstance(body, dict), f"expected a JSON object, got {type(body).__name__}"


# --- Phase 7.4: nullable fields round-trip as actual JSON null ------------


async def test_order_nullable_fields_serialize_as_null_when_unset(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    """A brand-new (pending/open) order never sets stop_price, avg_fill_price,
    or submitted_at — the DTO must emit JSON null for these, not omit the
    key, not "None" as a string, and not error.
    """
    user_id = test_user_id
    uow = SqlAlchemyUnitOfWork(lambda: db_session)
    await uow.orders.create(
        {
            "user_id": user_id,
            "symbol_id": symbol["id"],
            "side": "buy",
            "order_type": "limit",
            "time_in_force": "gtc",
            "quantity": 1,
            "price": 100,  # required for a limit order to be meaningful; left non-null on purpose
            "status": "pending",
        }
    )
    await uow.commit()

    response = await client.get("/trading/orders", headers=auth_headers)
    order = response.json()[0]
    assert order["stop_price"] is None
    assert order["avg_fill_price"] is None
    assert order["submitted_at"] is None
    # filled_quantity has a DB server_default of 0, not left NULL — confirms
    # the distinction between "column has a default" and "column is nullable".
    assert order["filled_quantity"] == 0.0


async def test_position_nullable_fields_serialize_as_null_when_unset(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    uow = SqlAlchemyUnitOfWork(lambda: db_session)
    await uow.positions.create(
        {
            "user_id": user_id,
            "symbol_id": symbol["id"],
            "side": "long",
            "quantity": 1,
            "avg_entry_price": 100,
            "status": "open",
        }
    )
    await uow.commit()

    response = await client.get("/trading/positions", headers=auth_headers)
    position = response.json()[0]
    assert position["current_price"] is None
    assert position["unrealized_pnl"] is None
    assert position["closed_at"] is None
    # realized_pnl has a DB server_default of 0, not left NULL.
    assert position["realized_pnl"] == 0.0


async def test_trade_nullable_exit_fields_serialize_as_null_when_unset(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    """/trading/trades only ever returns status=closed rows (get_closed_trades),
    so this doesn't claim to be realistic business data — it verifies the
    DTO/serialization contract holds even when the DB permits exit_price/
    exit_at/gross_pnl/net_pnl to be null on a row that happens to be closed.
    """
    user_id = test_user_id
    uow = SqlAlchemyUnitOfWork(lambda: db_session)
    await uow.trades.create(
        {
            "user_id": user_id,
            "symbol_id": symbol["id"],
            "side": "long",
            "entry_price": 100,
            "quantity": 1,
            "status": "closed",
            "entry_at": datetime.now(UTC),
        }
    )
    await uow.commit()

    response = await client.get("/trading/trades", headers=auth_headers)
    trade = response.json()[0]
    assert trade["exit_price"] is None
    assert trade["exit_at"] is None
    assert trade["gross_pnl"] is None
    assert trade["net_pnl"] is None
    assert trade["return_pct"] is None
    # total_fees has a DB server_default of 0, not left NULL.
    assert trade["total_fees"] == 0.0


async def test_execution_fee_currency_serializes_as_null_when_unset(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    uow = SqlAlchemyUnitOfWork(lambda: db_session)
    order = await uow.orders.create(
        {
            "user_id": user_id,
            "symbol_id": symbol["id"],
            "side": "buy",
            "order_type": "market",
            "time_in_force": "gtc",
            "quantity": 1,
            "filled_quantity": 1,
            "avg_fill_price": 100,
            "status": "filled",
        }
    )
    await uow.executions.create(
        {
            "order_id": order.id,
            "symbol_id": symbol["id"],
            "exec_price": 100,
            "exec_quantity": 1,
            "liquidity": "taker",
            # fee_currency intentionally omitted
        }
    )
    await uow.commit()

    response = await client.get("/trading/executions", headers=auth_headers)
    execution = response.json()[0]
    assert execution["fee_currency"] is None
    # fee has a DB server_default of 0, not left NULL.
    assert execution["fee"] == 0.0


# --- Phase 7.4: timestamp format contract ----------------------------------


async def test_timestamp_fields_are_valid_iso8601(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    """formatDateTime() in frontend/src/features/dashboard/format.ts does
    `new Date(value).toLocaleString()` — a malformed string wouldn't throw,
    it'd silently render "Invalid Date". This locks the actual serialized
    format down explicitly rather than relying on that being forgiving.
    """
    user_id = test_user_id
    await _seed_full_dataset(db_session, user_id=user_id, symbol_id=symbol["id"])

    orders = (await client.get("/trading/orders", headers=auth_headers)).json()
    for order in orders:
        datetime.fromisoformat(order["created_at"])
        datetime.fromisoformat(order["updated_at"])
        if order["submitted_at"] is not None:
            datetime.fromisoformat(order["submitted_at"])

    execution = (await client.get("/trading/executions", headers=auth_headers)).json()[0]
    datetime.fromisoformat(execution["executed_at"])

    position = (await client.get("/trading/positions", headers=auth_headers)).json()[0]
    datetime.fromisoformat(position["opened_at"])

    trade = (await client.get("/trading/trades", headers=auth_headers)).json()[0]
    datetime.fromisoformat(trade["entry_at"])
    datetime.fromisoformat(trade["exit_at"])


# --- Phase 7.4: pagination / filter query parameters -----------------------


async def test_orders_pagination_limit_and_offset(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    uow = SqlAlchemyUnitOfWork(lambda: db_session)
    for i in range(3):
        await uow.orders.create(
            {
                "user_id": user_id,
                "symbol_id": symbol["id"],
                "side": "buy",
                "order_type": "limit",
                "time_in_force": "gtc",
                "quantity": 1,
                "price": 100 + i,
                "status": "open",
            }
        )
    await uow.commit()

    page1 = (await client.get("/trading/orders?limit=2&offset=0", headers=auth_headers)).json()
    page2 = (await client.get("/trading/orders?limit=2&offset=2", headers=auth_headers)).json()
    assert len(page1) == 2
    assert len(page2) == 1  # 3 total, 2 on page 1

    ids_page1 = {o["id"] for o in page1}
    ids_page2 = {o["id"] for o in page2}
    assert ids_page1.isdisjoint(ids_page2), "pages overlapped"
    assert len(ids_page1 | ids_page2) == 3, "pages did not cover every seeded order exactly once"


async def test_orders_limit_out_of_range_returns_422(client: AsyncClient, auth_headers: dict) -> None:
    too_low = await client.get("/trading/orders?limit=0", headers=auth_headers)
    too_high = await client.get("/trading/orders?limit=101", headers=auth_headers)
    negative_offset = await client.get("/trading/orders?offset=-1", headers=auth_headers)
    assert too_low.status_code == 422
    assert too_high.status_code == 422
    assert negative_offset.status_code == 422


async def test_trades_pagination_limit_and_offset(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    uow = SqlAlchemyUnitOfWork(lambda: db_session)
    for i in range(3):
        await uow.trades.create(
            {
                "user_id": user_id,
                "symbol_id": symbol["id"],
                "side": "long",
                "entry_price": 100,
                "exit_price": 100 + i,
                "quantity": 1,
                "status": "closed",
                "entry_at": datetime.now(UTC) - timedelta(days=i + 1),
                "exit_at": datetime.now(UTC),
            }
        )
    await uow.commit()

    page1 = (await client.get("/trading/trades?limit=2&offset=0", headers=auth_headers)).json()
    page2 = (await client.get("/trading/trades?limit=2&offset=2", headers=auth_headers)).json()
    assert len(page1) == 2
    assert len(page2) == 1
    ids_page1 = {t["id"] for t in page1}
    ids_page2 = {t["id"] for t in page2}
    assert ids_page1.isdisjoint(ids_page2)
    assert len(ids_page1 | ids_page2) == 3


async def test_executions_limit_parameter_is_respected(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    uow = SqlAlchemyUnitOfWork(lambda: db_session)
    order = await uow.orders.create(
        {
            "user_id": user_id,
            "symbol_id": symbol["id"],
            "side": "buy",
            "order_type": "market",
            "time_in_force": "gtc",
            "quantity": 3,
            "filled_quantity": 3,
            "avg_fill_price": 100,
            "status": "filled",
        }
    )
    for i in range(3):
        await uow.executions.create(
            {
                "order_id": order.id,
                "symbol_id": symbol["id"],
                "exec_price": 100 + i,
                "exec_quantity": 1,
                "liquidity": "taker",
            }
        )
    await uow.commit()

    limited = (await client.get("/trading/executions?limit=2", headers=auth_headers)).json()
    assert len(limited) == 2

    unlimited = (await client.get("/trading/executions", headers=auth_headers)).json()
    assert len(unlimited) == 3  # default limit (20) comfortably covers 3 rows


async def test_positions_status_filter(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict, test_user_id, symbol: dict
) -> None:
    user_id = test_user_id
    uow = SqlAlchemyUnitOfWork(lambda: db_session)
    await uow.positions.create(
        {
            "user_id": user_id,
            "symbol_id": symbol["id"],
            "side": "long",
            "quantity": 1,
            "avg_entry_price": 100,
            "status": "open",
        }
    )
    await uow.positions.create(
        {
            "user_id": user_id,
            "symbol_id": symbol["id"],
            "side": "short",
            "quantity": 0,
            "avg_entry_price": 100,
            "status": "closed",
            "closed_at": datetime.now(UTC),
        }
    )
    await uow.commit()

    default_response = await client.get("/trading/positions", headers=auth_headers)
    open_response = await client.get("/trading/positions?status=open", headers=auth_headers)
    all_response = await client.get("/trading/positions?status=all", headers=auth_headers)
    assert len(default_response.json()) == 1  # default is "open"
    assert len(open_response.json()) == 1
    assert len(all_response.json()) == 2

    invalid_status = await client.get("/trading/positions?status=bogus", headers=auth_headers)
    assert invalid_status.status_code == 422
