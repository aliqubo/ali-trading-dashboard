"""Trading dashboard routes: read-only summary, positions, orders, executions, trades.

New MVP glue code (this vertical slice) — uses only the existing Identity and
Trading models/repositories plus a plain, parameterized, read-only lookup
against the ``symbols`` table for display labels. It does not add a Symbol
model, repository, or service, and does not touch Market/AI/Alerts/Portfolio/
Risk domains (RECOVERY_MANIFEST.md scope).

Every route is scoped to ``current_user.id`` — no cross-user data is ever
returned.
"""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Query
from sqlalchemy import bindparam, text

from app.api.deps import CurrentUserDep, UnitOfWorkDep
from app.models.trading import Execution, Order, Position, Trade
from app.repositories.types import Pagination
from app.services.trading.dtos import (
    DashboardSummaryResponse,
    ExecutionResponse,
    OrderResponse,
    PositionResponse,
    SymbolInfo,
    TradeResponse,
)

router = APIRouter(prefix="/trading", tags=["trading"])

_DEFAULT_LIST_LIMIT = 20
_MAX_LIST_LIMIT = 100


async def _resolve_symbols(
    uow: UnitOfWorkDep, symbol_ids: set[uuid.UUID]
) -> dict[uuid.UUID, SymbolInfo]:
    """Look up ticker/name for a batch of symbol ids.

    Plain parameterized SELECT against the ``symbols`` table — display-only,
    not a Market-domain repository (see module docstring).
    """
    if not symbol_ids:
        return {}
    stmt = text("SELECT id, ticker, name FROM symbols WHERE id IN :ids").bindparams(
        bindparam("ids", expanding=True)
    )
    result = await uow.session.execute(stmt, {"ids": list(symbol_ids)})
    return {
        row.id: SymbolInfo(id=row.id, ticker=row.ticker, name=row.name) for row in result
    }


def _order_response(order: Order, symbols: dict[uuid.UUID, SymbolInfo]) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        symbol=symbols.get(order.symbol_id),
        side=order.side,
        order_type=order.order_type,
        time_in_force=order.time_in_force,
        quantity=order.quantity,
        price=order.price,
        stop_price=order.stop_price,
        filled_quantity=order.filled_quantity,
        avg_fill_price=order.avg_fill_price,
        status=order.status,
        reject_reason=order.reject_reason,
        submitted_at=order.submitted_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def _execution_response(
    execution: Execution, symbols: dict[uuid.UUID, SymbolInfo]
) -> ExecutionResponse:
    return ExecutionResponse(
        id=execution.id,
        order_id=execution.order_id,
        symbol=symbols.get(execution.symbol_id),
        exec_price=execution.exec_price,
        exec_quantity=execution.exec_quantity,
        fee=execution.fee,
        fee_currency=execution.fee_currency,
        liquidity=execution.liquidity,
        executed_at=execution.executed_at,
    )


def _position_response(
    position: Position, symbols: dict[uuid.UUID, SymbolInfo]
) -> PositionResponse:
    return PositionResponse(
        id=position.id,
        symbol=symbols.get(position.symbol_id),
        side=position.side,
        quantity=position.quantity,
        avg_entry_price=position.avg_entry_price,
        current_price=position.current_price,
        unrealized_pnl=position.unrealized_pnl,
        realized_pnl=position.realized_pnl,
        status=position.status,
        opened_at=position.opened_at,
        closed_at=position.closed_at,
    )


def _trade_response(trade: Trade, symbols: dict[uuid.UUID, SymbolInfo]) -> TradeResponse:
    return TradeResponse(
        id=trade.id,
        symbol=symbols.get(trade.symbol_id),
        side=trade.side,
        entry_price=trade.entry_price,
        exit_price=trade.exit_price,
        quantity=trade.quantity,
        gross_pnl=trade.gross_pnl,
        net_pnl=trade.net_pnl,
        total_fees=trade.total_fees,
        return_pct=trade.return_pct,
        status=trade.status,
        entry_at=trade.entry_at,
        exit_at=trade.exit_at,
    )


@router.get("/summary")
async def get_summary(
    current_user: CurrentUserDep, uow: UnitOfWorkDep
) -> DashboardSummaryResponse:
    """Counts and sums over already-stored columns — no PnL computation."""
    open_positions = await uow.positions.get_open_positions(current_user.id)
    open_orders = await uow.orders.get_open_orders(current_user.id)
    all_trades = await uow.trades.get_for_user(current_user.id)
    closed_trades = [t for t in all_trades if t.status == "closed"]

    return DashboardSummaryResponse(
        open_positions_count=len(open_positions),
        open_orders_count=len(open_orders),
        unrealized_pnl_total=float(sum((p.unrealized_pnl or 0) for p in open_positions)),
        closed_trades_count=len(closed_trades),
        realized_pnl_total=float(sum((t.net_pnl or 0) for t in closed_trades)),
    )


@router.get("/positions")
async def list_positions(
    current_user: CurrentUserDep,
    uow: UnitOfWorkDep,
    status: Literal["open", "all"] = "open",
) -> list[PositionResponse]:
    positions = (
        await uow.positions.get_open_positions(current_user.id)
        if status == "open"
        else (await uow.positions.get_for_user(current_user.id))[:_MAX_LIST_LIMIT]
    )
    symbols = await _resolve_symbols(uow, {p.symbol_id for p in positions})
    return [_position_response(p, symbols) for p in positions]


@router.get("/orders")
async def list_orders(
    current_user: CurrentUserDep,
    uow: UnitOfWorkDep,
    limit: int = Query(default=_DEFAULT_LIST_LIMIT, ge=1, le=_MAX_LIST_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> list[OrderResponse]:
    page = await uow.orders.get_orders_for_user(
        current_user.id, Pagination(limit=limit, offset=offset)
    )
    symbols = await _resolve_symbols(uow, {o.symbol_id for o in page.items})
    return [_order_response(o, symbols) for o in page.items]


@router.get("/executions")
async def list_executions(
    current_user: CurrentUserDep,
    uow: UnitOfWorkDep,
    limit: int = Query(default=_DEFAULT_LIST_LIMIT, ge=1, le=_MAX_LIST_LIMIT),
) -> list[ExecutionResponse]:
    executions = await uow.executions.get_recent_for_user(current_user.id, limit=limit)
    symbols = await _resolve_symbols(uow, {e.symbol_id for e in executions})
    return [_execution_response(e, symbols) for e in executions]


@router.get("/trades")
async def list_trades(
    current_user: CurrentUserDep,
    uow: UnitOfWorkDep,
    limit: int = Query(default=_DEFAULT_LIST_LIMIT, ge=1, le=_MAX_LIST_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> list[TradeResponse]:
    page = await uow.trades.get_closed_trades(
        current_user.id, Pagination(limit=limit, offset=offset)
    )
    symbols = await _resolve_symbols(uow, {t.symbol_id for t in page.items})
    return [_trade_response(t, symbols) for t in page.items]
