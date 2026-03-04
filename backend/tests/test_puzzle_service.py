"""Unit tests for puzzle_service — mocks the DB so TABLESAMPLE works on any size table."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.puzzle_service import get_random_puzzle


def _cursor(first_value):
    """Return a mock CursorResult whose .mappings().first() returns first_value."""
    m = MagicMock()
    m.mappings.return_value.first.return_value = first_value
    return m


def _scalar(value):
    """Return a mock CursorResult whose .scalar_one() returns value."""
    m = MagicMock()
    m.scalar_one.return_value = value
    return m


async def test_tablesample_returns_row():
    """TABLESAMPLE returns a row — no fallback needed."""
    row = {"id": "abc01", "fen": "rnbq...", "moves": "e2e4", "rating": 1500, "themes": "fork"}
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_cursor(row))

    result = await get_random_puzzle(db)

    assert result == row
    assert db.execute.call_count == 1  # only the TABLESAMPLE query


async def test_tablesample_empty_fallback_returns_row():
    """TABLESAMPLE returns nothing — falls back to COUNT + OFFSET."""
    row = {"id": "xyz02", "fen": "rnbq...", "moves": "d2d4", "rating": 1200, "themes": "pin"}
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[_cursor(None), _scalar(10), _cursor(row)]
    )

    result = await get_random_puzzle(db)

    assert result == row
    assert db.execute.call_count == 3  # TABLESAMPLE + COUNT + OFFSET query


async def test_empty_table_returns_none():
    """TABLESAMPLE returns nothing and COUNT is 0 — return None."""
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[_cursor(None), _scalar(0)])

    result = await get_random_puzzle(db)

    assert result is None
    assert db.execute.call_count == 2  # TABLESAMPLE + COUNT (no OFFSET query)


async def test_rating_window_filter_applied():
    """When user_rating is provided, rating-filtered TABLESAMPLE is used first."""
    row = {"id": "rated01", "fen": "rnbq...", "moves": "e2e4", "rating": 1550, "themes": "fork"}
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_cursor(row))

    result = await get_random_puzzle(db, user_rating=1500)

    assert result == row
    # Verify the call used rating filter params
    call_args = db.execute.call_args
    sql = str(call_args[0][0]) if call_args[0] else str(call_args[1].text)
    assert "BETWEEN" in sql.upper()


async def test_rating_window_falls_back_to_unconstrained():
    """When rating-filtered sample returns nothing, falls back to unconstrained TABLESAMPLE."""
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[_cursor(None), _cursor({"id": "any01", "fen": "...", "moves": "e4", "rating": 1200, "themes": None})]
    )

    result = await get_random_puzzle(db, user_rating=1500)

    assert result is not None
    assert result["id"] == "any01"
    assert db.execute.call_count == 2  # filtered + unconstrained


async def test_guest_gets_pure_random():
    """When user_rating is None (guest), no rating filter is applied."""
    row = {"id": "guest01", "fen": "rnbq...", "moves": "e2e4", "rating": 2000, "themes": None}
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_cursor(row))

    result = await get_random_puzzle(db, user_rating=None)

    assert result == row
    # Verify no rating filter params were used
    call_args = db.execute.call_args
    sql = str(call_args[0][0]) if call_args[0] else str(call_args[1].text)
    assert "BETWEEN" not in sql.upper()
