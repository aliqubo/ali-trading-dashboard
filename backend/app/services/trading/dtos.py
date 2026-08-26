"""Trading domain DTOs.

Data-only response contracts for the read-only dashboard slice (positions,
orders, executions, trades, summary). Structural validation only — no PnL,
matching, or risk logic lives here.

Every ``Numeric`` column decodes to ``decimal.Decimal`` at the driver level
(psycopg/asyncpg), not ``float``, regardless of the ORM's ``Mapped[float]``
annotation — the same class of mismatch fixed for ``ip_address`` in the
Identity DTOs (see RECOVERY_MANIFEST.md). Every numeric field here carries a
``field_validator(mode="before")`` that coerces ``Decimal`` to ``float``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


def _decimal_to_float(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    return value


class SymbolInfo(BaseModel):
    """Minimal display-only symbol reference (ticker/name), not a domain DTO.

    Resolved via a plain read-only lookup against the ``symbols`` table
    (app/api/trading.py) — there is no Symbol model/repository in this MVP
    (Market domain excluded per RECOVERY_MANIFEST.md), so this is not a
    Market-domain object, just enough to render a human-readable label.
    """

    id: uuid.UUID
    ticker: str
    name: str


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: SymbolInfo | None
    side: str
    order_type: str
    time_in_force: str
    quantity: float
    price: float | None
    stop_price: float | None
    filled_quantity: float
    avg_fill_price: float | None
    status: str
    reject_reason: str | None
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_validator(
        "quantity", "price", "stop_price", "filled_quantity", "avg_fill_price", mode="before"
    )
    @classmethod
    def _coerce_numeric(cls, value: object) -> object:
        return _decimal_to_float(value)


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    symbol: SymbolInfo | None
    exec_price: float
    exec_quantity: float
    fee: float
    fee_currency: str | None
    liquidity: str
    executed_at: datetime

    @field_validator("exec_price", "exec_quantity", "fee", mode="before")
    @classmethod
    def _coerce_numeric(cls, value: object) -> object:
        return _decimal_to_float(value)


class PositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: SymbolInfo | None
    side: str
    quantity: float
    avg_entry_price: float
    current_price: float | None
    unrealized_pnl: float | None
    realized_pnl: float
    status: str
    opened_at: datetime
    closed_at: datetime | None

    @field_validator(
        "quantity",
        "avg_entry_price",
        "current_price",
        "unrealized_pnl",
        "realized_pnl",
        mode="before",
    )
    @classmethod
    def _coerce_numeric(cls, value: object) -> object:
        return _decimal_to_float(value)


class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: SymbolInfo | None
    side: str
    entry_price: float
    exit_price: float | None
    quantity: float
    gross_pnl: float | None
    net_pnl: float | None
    total_fees: float
    return_pct: float | None
    status: str
    entry_at: datetime
    exit_at: datetime | None

    @field_validator(
        "entry_price",
        "exit_price",
        "quantity",
        "gross_pnl",
        "net_pnl",
        "total_fees",
        "return_pct",
        mode="before",
    )
    @classmethod
    def _coerce_numeric(cls, value: object) -> object:
        return _decimal_to_float(value)


class DashboardSummaryResponse(BaseModel):
    """Simple counts and sums over already-stored columns — no PnL math."""

    open_positions_count: int
    open_orders_count: int
    unrealized_pnl_total: float
    closed_trades_count: int
    realized_pnl_total: float
