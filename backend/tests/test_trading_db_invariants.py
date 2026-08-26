"""Database-level invariant tests for the Trading domain (Phase 8 Item 2).

Exercises real Postgres constraints — the `client_order_id` unique
constraint, the open-position partial unique index, and every documented
CheckConstraint on Order/Execution/Position/Trade in
app/models/trading.py — through the actual production write path
(BaseRepository.create()/update() via SqlAlchemyUnitOfWork), not raw SQL, so
these tests fail if a future model or repository change weakens what the
database itself enforces.

Runs entirely against the isolated ali_trading_test database via conftest.py's
existing `db_session`/`test_user_id` fixtures (Base.metadata
create_all()/drop_all() cycle) — never ali_trading. No ORM-level FK exists on
symbol_id here (see app/models/trading.py's Phase 5 patch notes), so a random
UUID is used for it throughout; only user_id (and, for Execution, order_id)
have a real enforced FK in this schema.

The 6 CheckConstraint tests deliberately do not assert a specific top-level
application exception type (see BaseRepository.create()'s blanket
`except IntegrityError: raise DuplicateEntityError()`) — only that the
raised exception's __cause__ is a genuine sqlalchemy.exc.IntegrityError,
proving the database itself rejected the row. The actual top-level exception
type observed is printed for the record.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationAppError
from app.repositories.exceptions import DuplicateEntityError
from app.repositories.unit_of_work import SqlAlchemyUnitOfWork


def _uow(db_session: AsyncSession) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(lambda: db_session)


# --- A. Order.client_order_id uniqueness -----------------------------------


async def test_client_order_id_uniqueness_rejects_duplicate(
    db_session: AsyncSession, test_user_id
) -> None:
    symbol_id = uuid.uuid4()
    uow = _uow(db_session)
    await uow.orders.create(
        {
            "user_id": test_user_id,
            "symbol_id": symbol_id,
            "client_order_id": "dup-client-order-1",
            "side": "buy",
            "order_type": "limit",
            "time_in_force": "gtc",
            "quantity": 1,
            "price": 100,
            "status": "open",
        }
    )
    await uow.commit()

    uow2 = _uow(db_session)
    with pytest.raises(DuplicateEntityError) as exc_info:
        await uow2.orders.create(
            {
                "user_id": test_user_id,
                "symbol_id": symbol_id,
                "client_order_id": "dup-client-order-1",
                "side": "sell",
                "order_type": "limit",
                "time_in_force": "gtc",
                "quantity": 2,
                "price": 200,
                "status": "open",
            }
        )
    assert isinstance(exc_info.value.__cause__, IntegrityError)


# --- A2. Execution.external_exec_id uniqueness ------------------------------


async def test_execution_external_exec_id_uniqueness_rejects_duplicate(
    db_session: AsyncSession, test_user_id
) -> None:
    symbol_id = uuid.uuid4()
    uow = _uow(db_session)
    order = await _create_valid_filled_order(uow, user_id=test_user_id, symbol_id=symbol_id)

    await uow.executions.create(
        {
            "order_id": order.id,
            "symbol_id": symbol_id,
            "exec_price": 100,
            "exec_quantity": 1,
            "liquidity": "taker",
            "external_exec_id": "dup-external-exec-1",
        }
    )
    await uow.commit()

    uow2 = _uow(db_session)
    with pytest.raises(DuplicateEntityError) as exc_info:
        await uow2.executions.create(
            {
                "order_id": order.id,
                "symbol_id": symbol_id,
                "exec_price": 200,
                "exec_quantity": 2,
                "liquidity": "taker",
                "external_exec_id": "dup-external-exec-1",
            }
        )
    assert isinstance(exc_info.value.__cause__, IntegrityError)


# --- B. Open-position partial unique index ----------------------------------


async def test_open_position_unique_index_rejects_duplicate_open(
    db_session: AsyncSession, test_user_id
) -> None:
    symbol_id = uuid.uuid4()
    uow = _uow(db_session)
    await uow.positions.create(
        {
            "user_id": test_user_id,
            "symbol_id": symbol_id,
            "side": "long",
            "quantity": 1,
            "avg_entry_price": 100,
            "status": "open",
        }
    )
    await uow.commit()

    uow2 = _uow(db_session)
    with pytest.raises(DuplicateEntityError) as exc_info:
        await uow2.positions.create(
            {
                "user_id": test_user_id,
                "symbol_id": symbol_id,
                "side": "long",
                "quantity": 2,
                "avg_entry_price": 200,
                "status": "open",
            }
        )
    assert isinstance(exc_info.value.__cause__, IntegrityError)


async def test_open_position_unique_index_allows_reopen_after_close(
    db_session: AsyncSession, test_user_id
) -> None:
    symbol_id = uuid.uuid4()
    uow = _uow(db_session)
    first = await uow.positions.create(
        {
            "user_id": test_user_id,
            "symbol_id": symbol_id,
            "side": "long",
            "quantity": 1,
            "avg_entry_price": 100,
            "status": "open",
        }
    )
    await uow.commit()

    await uow.positions.update(
        first.id, {"status": "closed", "closed_at": datetime.now(UTC)}
    )
    await uow.commit()

    second = await uow.positions.create(
        {
            "user_id": test_user_id,
            "symbol_id": symbol_id,
            "side": "long",
            "quantity": 3,
            "avg_entry_price": 150,
            "status": "open",
        }
    )
    await uow.commit()

    assert second.id != first.id
    assert second.status == "open"


# --- C. CheckConstraints -----------------------------------------------------


async def test_order_quantity_positive_check_constraint(
    db_session: AsyncSession, test_user_id
) -> None:
    uow = _uow(db_session)
    with pytest.raises(ValidationAppError) as exc_info:
        await uow.orders.create(
            {
                "user_id": test_user_id,
                "symbol_id": uuid.uuid4(),
                "side": "buy",
                "order_type": "limit",
                "time_in_force": "gtc",
                "quantity": 0,
                "price": 100,
                "status": "open",
            }
        )
    assert not isinstance(exc_info.value, DuplicateEntityError)
    assert isinstance(exc_info.value.__cause__, IntegrityError), (
        f"expected an IntegrityError-caused rejection, got "
        f"{type(exc_info.value)!r} caused by {type(exc_info.value.__cause__)!r}"
    )
    print(
        "[invariant] Order.quantity>0 violation raised: "
        f"{type(exc_info.value).__name__}"
    )


async def test_order_filled_quantity_le_quantity_check_constraint(
    db_session: AsyncSession, test_user_id
) -> None:
    uow = _uow(db_session)
    with pytest.raises(ValidationAppError) as exc_info:
        await uow.orders.create(
            {
                "user_id": test_user_id,
                "symbol_id": uuid.uuid4(),
                "side": "buy",
                "order_type": "limit",
                "time_in_force": "gtc",
                "quantity": 1,
                "filled_quantity": 5,
                "price": 100,
                "status": "open",
            }
        )
    assert not isinstance(exc_info.value, DuplicateEntityError)
    assert isinstance(exc_info.value.__cause__, IntegrityError), (
        f"expected an IntegrityError-caused rejection, got "
        f"{type(exc_info.value)!r} caused by {type(exc_info.value.__cause__)!r}"
    )
    print(
        "[invariant] Order.filled_quantity<=quantity violation raised: "
        f"{type(exc_info.value).__name__}"
    )


async def _create_valid_filled_order(uow: SqlAlchemyUnitOfWork, *, user_id, symbol_id):
    order = await uow.orders.create(
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
        }
    )
    await uow.commit()
    return order


async def test_execution_exec_quantity_positive_check_constraint(
    db_session: AsyncSession, test_user_id
) -> None:
    symbol_id = uuid.uuid4()
    uow = _uow(db_session)
    order = await _create_valid_filled_order(uow, user_id=test_user_id, symbol_id=symbol_id)

    with pytest.raises(ValidationAppError) as exc_info:
        await uow.executions.create(
            {
                "order_id": order.id,
                "symbol_id": symbol_id,
                "exec_price": 100,
                "exec_quantity": 0,
                "liquidity": "taker",
            }
        )
    assert not isinstance(exc_info.value, DuplicateEntityError)
    assert isinstance(exc_info.value.__cause__, IntegrityError), (
        f"expected an IntegrityError-caused rejection, got "
        f"{type(exc_info.value)!r} caused by {type(exc_info.value.__cause__)!r}"
    )
    print(
        "[invariant] Execution.exec_quantity>0 violation raised: "
        f"{type(exc_info.value).__name__}"
    )


async def test_execution_exec_price_positive_check_constraint(
    db_session: AsyncSession, test_user_id
) -> None:
    symbol_id = uuid.uuid4()
    uow = _uow(db_session)
    order = await _create_valid_filled_order(uow, user_id=test_user_id, symbol_id=symbol_id)

    with pytest.raises(ValidationAppError) as exc_info:
        await uow.executions.create(
            {
                "order_id": order.id,
                "symbol_id": symbol_id,
                "exec_price": 0,
                "exec_quantity": 1,
                "liquidity": "taker",
            }
        )
    assert not isinstance(exc_info.value, DuplicateEntityError)
    assert isinstance(exc_info.value.__cause__, IntegrityError), (
        f"expected an IntegrityError-caused rejection, got "
        f"{type(exc_info.value)!r} caused by {type(exc_info.value.__cause__)!r}"
    )
    print(
        "[invariant] Execution.exec_price>0 violation raised: "
        f"{type(exc_info.value).__name__}"
    )


async def test_position_quantity_non_negative_check_constraint(
    db_session: AsyncSession, test_user_id
) -> None:
    uow = _uow(db_session)
    with pytest.raises(ValidationAppError) as exc_info:
        await uow.positions.create(
            {
                "user_id": test_user_id,
                "symbol_id": uuid.uuid4(),
                "side": "long",
                "quantity": -1,
                "avg_entry_price": 100,
                "status": "open",
            }
        )
    assert not isinstance(exc_info.value, DuplicateEntityError)
    assert isinstance(exc_info.value.__cause__, IntegrityError), (
        f"expected an IntegrityError-caused rejection, got "
        f"{type(exc_info.value)!r} caused by {type(exc_info.value.__cause__)!r}"
    )
    print(
        "[invariant] Position.quantity>=0 violation raised: "
        f"{type(exc_info.value).__name__}"
    )


async def test_trade_quantity_positive_check_constraint(
    db_session: AsyncSession, test_user_id
) -> None:
    uow = _uow(db_session)
    with pytest.raises(ValidationAppError) as exc_info:
        await uow.trades.create(
            {
                "user_id": test_user_id,
                "symbol_id": uuid.uuid4(),
                "side": "long",
                "entry_price": 100,
                "quantity": 0,
                "status": "open",
                "entry_at": datetime.now(UTC),
            }
        )
    assert not isinstance(exc_info.value, DuplicateEntityError)
    assert isinstance(exc_info.value.__cause__, IntegrityError), (
        f"expected an IntegrityError-caused rejection, got "
        f"{type(exc_info.value)!r} caused by {type(exc_info.value.__cause__)!r}"
    )
    print(
        "[invariant] Trade.quantity>0 violation raised: "
        f"{type(exc_info.value).__name__}"
    )
