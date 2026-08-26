"""Insert minimal illustrative Trading-domain sample data for one user.

Manual, one-off dev tool — never imported or run by the application itself
(not wired into app/main.py, any router, or any startup hook). Run by hand:

    .venv\\Scripts\\python.exe -m scripts.seed_trading_sample_data --user-id <uuid>

Refuses to run without an explicit ``--user-id`` (there is deliberately no
"seed some default user" fallback). Refuses to run if that user already has
any orders, so it can never silently duplicate data on a second run.

Every statement against ``markets``/``exchanges``/``symbols`` — tables with no
ORM model in this MVP (Market domain excluded, RECOVERY_MANIFEST.md) — is a
plain parameterized ``INSERT ... RETURNING id`` via SQLAlchemy ``text()`` with
bound parameters; no string interpolation of any value anywhere. Orders,
executions, positions, and trades are inserted through the existing Trading
repositories (parameterized by SQLAlchemy Core in the normal way).

The data is illustrative only — enough to exercise the dashboard UI (one
open order, one open position with realized+unrealized PnL, two closed
trades: one winner, one loser). It is not a consistent, balance-checked
trading ledger.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import dispose_engine, get_session_factory, init_engine
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork


async def _insert_market(uow: SqlAlchemyUnitOfWork) -> uuid.UUID:
    stmt = text(
        "INSERT INTO markets (code, name, market_type, base_currency, is_active) "
        "VALUES (:code, :name, :market_type, :base_currency, true) "
        "RETURNING id"
    )
    result = await uow.session.execute(
        stmt,
        {
            "code": "SAMPLE_CRYPTO",
            "name": "Sample Crypto Market",
            "market_type": "crypto",
            "base_currency": "USD",
        },
    )
    return result.scalar_one()


async def _insert_exchange(uow: SqlAlchemyUnitOfWork, market_id: uuid.UUID) -> uuid.UUID:
    stmt = text(
        "INSERT INTO exchanges (market_id, code, name, timezone, is_active) "
        "VALUES (:market_id, :code, :name, :timezone, true) "
        "RETURNING id"
    )
    result = await uow.session.execute(
        stmt,
        {
            "market_id": market_id,
            "code": "SAMPLE_EX",
            "name": "Sample Exchange",
            "timezone": "UTC",
        },
    )
    return result.scalar_one()


async def _insert_symbol(
    uow: SqlAlchemyUnitOfWork,
    *,
    exchange_id: uuid.UUID,
    market_id: uuid.UUID,
    ticker: str,
    name: str,
    base_asset: str,
    quote_asset: str,
) -> uuid.UUID:
    stmt = text(
        "INSERT INTO symbols "
        "(exchange_id, market_id, ticker, name, base_asset, quote_asset, "
        " price_precision, quantity_precision, is_tradable, is_active) "
        "VALUES "
        "(:exchange_id, :market_id, :ticker, :name, :base_asset, :quote_asset, "
        " :price_precision, :quantity_precision, true, true) "
        "RETURNING id"
    )
    result = await uow.session.execute(
        stmt,
        {
            "exchange_id": exchange_id,
            "market_id": market_id,
            "ticker": ticker,
            "name": name,
            "base_asset": base_asset,
            "quote_asset": quote_asset,
            "price_precision": 2,
            "quantity_precision": 8,
        },
    )
    return result.scalar_one()


async def _seed(user_id: uuid.UUID) -> None:
    settings = get_settings()
    init_engine(settings)
    try:
        uow = SqlAlchemyUnitOfWork(get_session_factory())
        try:
            user = await uow.users.get_by_id(user_id)
            if user is None:
                print(f"No user with id {user_id} exists. Aborting.", file=sys.stderr)
                sys.exit(1)

            existing = await uow.orders.get_orders_for_user(user_id)
            if existing.items:
                print(
                    f"User {user_id} already has {len(existing.items)}+ order(s). "
                    "Refusing to seed a second time.",
                    file=sys.stderr,
                )
                sys.exit(1)

            now = datetime.now(UTC)

            market_id = await _insert_market(uow)
            exchange_id = await _insert_exchange(uow, market_id)
            btc_id = await _insert_symbol(
                uow,
                exchange_id=exchange_id,
                market_id=market_id,
                ticker="BTC/USD",
                name="Bitcoin / US Dollar",
                base_asset="BTC",
                quote_asset="USD",
            )
            eth_id = await _insert_symbol(
                uow,
                exchange_id=exchange_id,
                market_id=market_id,
                ticker="ETH/USD",
                name="Ethereum / US Dollar",
                base_asset="ETH",
                quote_asset="USD",
            )

            # Orders: one filled buy, one filled sell (partial exit), one open limit buy.
            buy_order = await uow.orders.create(
                {
                    "user_id": user_id,
                    "symbol_id": btc_id,
                    "side": "buy",
                    "order_type": "market",
                    "time_in_force": "gtc",
                    "quantity": 0.5,
                    "filled_quantity": 0.5,
                    "avg_fill_price": 60000,
                    "status": "filled",
                    "submitted_at": now - timedelta(days=2),
                }
            )
            sell_order = await uow.orders.create(
                {
                    "user_id": user_id,
                    "symbol_id": btc_id,
                    "side": "sell",
                    "order_type": "market",
                    "time_in_force": "gtc",
                    "quantity": 0.2,
                    "filled_quantity": 0.2,
                    "avg_fill_price": 61000,
                    "status": "filled",
                    "submitted_at": now - timedelta(days=1),
                }
            )
            await uow.orders.create(
                {
                    "user_id": user_id,
                    "symbol_id": eth_id,
                    "side": "buy",
                    "order_type": "limit",
                    "time_in_force": "gtc",
                    "quantity": 2,
                    "price": 3000,
                    "filled_quantity": 0,
                    "status": "open",
                    "submitted_at": now - timedelta(hours=1),
                }
            )

            await uow.executions.create(
                {
                    "order_id": buy_order.id,
                    "symbol_id": btc_id,
                    "exec_price": 60000,
                    "exec_quantity": 0.5,
                    "fee": 3,
                    "fee_currency": "USD",
                    "liquidity": "taker",
                    "executed_at": now - timedelta(days=2),
                }
            )
            await uow.executions.create(
                {
                    "order_id": sell_order.id,
                    "symbol_id": btc_id,
                    "exec_price": 61000,
                    "exec_quantity": 0.2,
                    "fee": 1.2,
                    "fee_currency": "USD",
                    "liquidity": "taker",
                    "executed_at": now - timedelta(days=1),
                }
            )

            # Open position: remaining 0.3 BTC from the buy, marked to a current price.
            await uow.positions.create(
                {
                    "user_id": user_id,
                    "symbol_id": btc_id,
                    "side": "long",
                    "quantity": 0.3,
                    "avg_entry_price": 60000,
                    "current_price": 62000,
                    "unrealized_pnl": 600,
                    "realized_pnl": 200,
                    "status": "open",
                    "opened_at": now - timedelta(days=2),
                }
            )

            # Closed trades: one winner (the BTC partial exit), one loser (illustrative ETH swing).
            await uow.trades.create(
                {
                    "user_id": user_id,
                    "symbol_id": btc_id,
                    "side": "long",
                    "entry_price": 60000,
                    "exit_price": 61000,
                    "quantity": 0.2,
                    "gross_pnl": 200,
                    "net_pnl": 198.8,
                    "total_fees": 1.2,
                    "return_pct": 1.6667,
                    "status": "closed",
                    "entry_at": now - timedelta(days=2),
                    "exit_at": now - timedelta(days=1),
                }
            )
            await uow.trades.create(
                {
                    "user_id": user_id,
                    "symbol_id": eth_id,
                    "side": "long",
                    "entry_price": 3200,
                    "exit_price": 3100,
                    "quantity": 1,
                    "gross_pnl": -100,
                    "net_pnl": -101,
                    "total_fees": 1,
                    "return_pct": -3.125,
                    "status": "closed",
                    "entry_at": now - timedelta(days=5),
                    "exit_at": now - timedelta(days=4),
                }
            )

            await uow.commit()
            print(f"Seeded sample trading data for user {user_id}.")
        finally:
            await uow.close()
    finally:
        await dispose_engine()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Insert minimal illustrative Trading-domain sample data for one "
            "existing user. Requires --user-id; refuses to run without it "
            "and refuses to run if that user already has orders."
        )
    )
    parser.add_argument(
        "--user-id",
        required=True,
        type=uuid.UUID,
        help="UUID of an existing user to seed sample data for (required).",
    )
    args = parser.parse_args()
    asyncio.run(_seed(args.user_id))


if __name__ == "__main__":
    main()
