"""Trading models (DATABASE_DESIGN.md §النطاق 4).

Tables: orders, order_history, executions, positions, position_history, trades.

Structure only — no logic. No trading behaviour is implemented here; these are
table definitions only.

MVP Phase 2 patch — relationships to Symbol/Strategy/RiskLog/TradeJournal
removed (those models are not present in this MVP; the symbol_id/strategy_id
foreign-key columns themselves are kept unchanged). Enum columns switched
from raw PgEnum to pg_enum(), and 6 datetime columns given
DateTime(timezone=True), mirroring the fix already applied to identity.py in
files3.zip. See RECOVERY_MANIFEST.md.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    Liquidity,
    OrderSide,
    OrderStatus,
    OrderType,
    PositionEventType,
    PositionSide,
    PositionStatus,
    TimeInForce,
    TradeStatus,
    pg_enum,
)
from app.models.mixins import (
    BigIntPrimaryKeyMixin,
    CreatedAtMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from app.models.identity import User


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # MVP Phase 5 patch — no ORM-level ForeignKey("symbols.id") here, for the
    # same reason as strategy_id below: the Market domain has no Symbol model
    # in this MVP, so "symbols" is never registered as a Table on
    # Base.metadata. This column is NOT NULL, so unlike strategy_id it
    # blocked every single order insert, not just ones referencing a
    # strategy. Column and the real Postgres-level FK constraint are
    # unchanged. See RECOVERY_MANIFEST.md.
    symbol_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False
    )
    # MVP Phase 5 patch — no ORM-level ForeignKey("strategies.id") here: the
    # Strategy domain has no model in this MVP, so "strategies" is never
    # registered as a Table on Base.metadata, and SQLAlchemy cannot resolve
    # it when sorting tables for a multi-table insert — it fails at
    # mapper-configuration time for *any* Order insert, regardless of this
    # column's value. The column itself (and the real Postgres-level FK
    # constraint from the migration) is unchanged; only the ORM-level FK
    # object is removed. See RECOVERY_MANIFEST.md.
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True
    )
    client_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    side: Mapped[OrderSide] = mapped_column(
        pg_enum(OrderSide, name="order_side"), nullable=False
    )
    order_type: Mapped[OrderType] = mapped_column(
        pg_enum(OrderType, name="order_type"), nullable=False
    )
    time_in_force: Mapped[TimeInForce] = mapped_column(
        pg_enum(TimeInForce, name="time_in_force"),
        nullable=False,
        server_default=TimeInForce.GTC.value,
    )
    quantity: Mapped[float] = mapped_column(Numeric(30, 8), nullable=False)
    price: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)
    stop_price: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)
    filled_quantity: Mapped[float] = mapped_column(
        Numeric(30, 8), nullable=False, server_default="0"
    )
    avg_fill_price: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        pg_enum(OrderStatus, name="order_status"),
        nullable=False,
        server_default=OrderStatus.PENDING.value,
    )
    reject_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # MVP Phase 2 patch: `symbol`, `strategy`, `risk_logs` relationships removed
    # (Symbol/Strategy/RiskLog models not present in this MVP).
    user: Mapped[User] = relationship(back_populates="orders")
    history: Mapped[list[OrderHistory]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    executions: Mapped[list[Execution]] = relationship(back_populates="order")

    __table_args__ = (
        UniqueConstraint("client_order_id", name="uq_orders_client_order_id"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("filled_quantity <= quantity", name="filled_le_quantity"),
        Index("idx_orders_user", "user_id"),
        Index("idx_orders_symbol", "symbol_id"),
        Index("idx_orders_status", "status"),
        Index("idx_orders_user_status", "user_id", "status"),
        Index("idx_orders_created", "created_at"),
    )


class OrderHistory(BigIntPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "order_history"

    order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_quantity: Mapped[float | None] = mapped_column(
        Numeric(30, 8), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_metadata: Mapped[dict[str, object] | None] = mapped_column(
        "metadata", JSONB, nullable=True, server_default="{}"
    )

    order: Mapped[Order] = relationship(back_populates="history")

    __table_args__ = (
        Index("idx_orderhist_order", "order_id"),
        Index("idx_orderhist_created", "created_at"),
    )


class Execution(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "executions"

    order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # MVP Phase 5 patch — no ORM-level ForeignKey("symbols.id"); see the
    # identical note on Order.symbol_id above. RECOVERY_MANIFEST.md.
    symbol_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False
    )
    exec_price: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False)
    exec_quantity: Mapped[float] = mapped_column(Numeric(30, 8), nullable=False)
    fee: Mapped[float] = mapped_column(
        Numeric(24, 8), nullable=False, server_default="0"
    )
    fee_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    liquidity: Mapped[Liquidity] = mapped_column(
        pg_enum(Liquidity, name="liquidity"),
        nullable=False,
        server_default=Liquidity.UNKNOWN.value,
    )
    external_exec_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # MVP Phase 2 patch: `symbol` relationship removed (Symbol model not present).
    order: Mapped[Order] = relationship(back_populates="executions")

    __table_args__ = (
        UniqueConstraint("external_exec_id", name="uq_executions_external_exec_id"),
        CheckConstraint("exec_quantity > 0", name="exec_quantity_positive"),
        CheckConstraint("exec_price > 0", name="exec_price_positive"),
        Index("idx_exec_order", "order_id"),
        Index("idx_exec_symbol", "symbol_id"),
        Index("idx_exec_executed", "executed_at"),
    )


class Position(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "positions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # MVP Phase 5 patch — no ORM-level ForeignKey("symbols.id"); see the
    # identical note on Order.symbol_id above. RECOVERY_MANIFEST.md.
    symbol_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False
    )
    side: Mapped[PositionSide] = mapped_column(
        pg_enum(PositionSide, name="position_side"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(30, 8), nullable=False)
    avg_entry_price: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False)
    current_price: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)
    unrealized_pnl: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)
    realized_pnl: Mapped[float] = mapped_column(
        Numeric(24, 8), nullable=False, server_default="0"
    )
    status: Mapped[PositionStatus] = mapped_column(
        pg_enum(PositionStatus, name="position_status"),
        nullable=False,
        server_default=PositionStatus.OPEN.value,
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # MVP Phase 2 patch: `symbol` relationship removed (Symbol model not present).
    user: Mapped[User] = relationship(back_populates="positions")
    history: Mapped[list[PositionHistory]] = relationship(
        back_populates="position", cascade="all, delete-orphan"
    )
    trades: Mapped[list[Trade]] = relationship(back_populates="position")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        # Partial unique index: only one open position per user+symbol.
        Index(
            "uq_positions_open_user_symbol",
            "user_id",
            "symbol_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
        Index("idx_positions_user", "user_id"),
        Index("idx_positions_symbol", "symbol_id"),
        Index("idx_positions_user_status", "user_id", "status"),
    )


class PositionHistory(BigIntPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "position_history"

    position_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[PositionEventType] = mapped_column(
        pg_enum(PositionEventType, name="position_event_type"), nullable=False
    )
    quantity_delta: Mapped[float | None] = mapped_column(Numeric(30, 8), nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)
    realized_pnl_delta: Mapped[float | None] = mapped_column(
        Numeric(24, 8), nullable=True
    )
    snapshot_quantity: Mapped[float] = mapped_column(Numeric(30, 8), nullable=False)

    position: Mapped[Position] = relationship(back_populates="history")

    __table_args__ = (
        Index("idx_poshist_position", "position_id"),
        Index("idx_poshist_created", "created_at"),
    )


class Trade(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "trades"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # MVP Phase 5 patch — no ORM-level ForeignKey("symbols.id"); see the
    # identical note on Order.symbol_id above. RECOVERY_MANIFEST.md.
    symbol_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False
    )
    position_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="SET NULL"),
        nullable=True,
    )
    # MVP Phase 5 patch — same rationale as Order.strategy_id above: no
    # ORM-level ForeignKey("strategies.id"), since "strategies" is not a
    # registered Table in this MVP. See RECOVERY_MANIFEST.md.
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True
    )
    side: Mapped[PositionSide] = mapped_column(
        pg_enum(PositionSide, name="position_side"), nullable=False
    )
    entry_price: Mapped[float] = mapped_column(Numeric(24, 8), nullable=False)
    exit_price: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(30, 8), nullable=False)
    gross_pnl: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)
    net_pnl: Mapped[float | None] = mapped_column(Numeric(24, 8), nullable=True)
    total_fees: Mapped[float] = mapped_column(
        Numeric(24, 8), nullable=False, server_default="0"
    )
    return_pct: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    status: Mapped[TradeStatus] = mapped_column(
        pg_enum(TradeStatus, name="trade_status"),
        nullable=False,
        server_default=TradeStatus.OPEN.value,
    )
    entry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # MVP Phase 2 patch: `symbol`, `strategy`, `journal` relationships removed
    # (Symbol/Strategy/TradeJournal models not present in this MVP).
    user: Mapped[User] = relationship(back_populates="trades")
    position: Mapped[Position | None] = relationship(back_populates="trades")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        Index("idx_trades_user", "user_id"),
        Index("idx_trades_symbol", "symbol_id"),
        Index("idx_trades_status", "status"),
        Index("idx_trades_entry", "entry_at"),
        Index("idx_trades_strategy", "strategy_id"),
    )
