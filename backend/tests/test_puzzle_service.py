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
