"""
Tests for GET /api/v1/puzzles/random endpoint.

These are unit tests that mock get_random_puzzle to avoid a real DB.
"""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_ROW = {
    "id": "00sHx",
    "fen": "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
    "moves": "f3e5 c6e5 d1h5 e8e7 h5e5 e7f6 e5c7",
    "rating": 1500,
    "themes": "fork mateIn1",
}

_VALID_ROW_NO_THEMES = {
    "id": "abcde",
    "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
    "moves": "e2e4",
    "rating": 800,
    "themes": None,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_random_puzzle_returns_200():
    """Mock a valid row — expect 200 with correct top-level fields."""
    with patch(
        "app.api.v1.puzzles.get_random_puzzle",
        new_callable=AsyncMock,
        return_value=_VALID_ROW,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/puzzles/random")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "00sHx"
    assert data["fen"] == _VALID_ROW["fen"]
    assert data["rating"] == 1500


@pytest.mark.asyncio
async def test_random_puzzle_moves_is_list():
    """moves must be a list of strings, not a space-separated string."""
    with patch(
        "app.api.v1.puzzles.get_random_puzzle",
        new_callable=AsyncMock,
        return_value=_VALID_ROW,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/puzzles/random")

    data = response.json()
    assert isinstance(data["moves"], list)
    assert data["moves"] == ["f3e5", "c6e5", "d1h5", "e8e7", "h5e5", "e7f6", "e5c7"]


@pytest.mark.asyncio
async def test_random_puzzle_themes_none_when_empty():
    """themes must be None (not an empty list) when the DB column is NULL."""
    with patch(
        "app.api.v1.puzzles.get_random_puzzle",
        new_callable=AsyncMock,
        return_value=_VALID_ROW_NO_THEMES,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/puzzles/random")

    data = response.json()
    assert data["themes"] is None


@pytest.mark.asyncio
async def test_random_puzzle_themes_list_when_present():
    """themes must be split into a list when the DB column is non-empty."""
    with patch(
        "app.api.v1.puzzles.get_random_puzzle",
        new_callable=AsyncMock,
        return_value=_VALID_ROW,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/puzzles/random")

    data = response.json()
    assert isinstance(data["themes"], list)
    assert data["themes"] == ["fork", "mateIn1"]


@pytest.mark.asyncio
async def test_random_puzzle_503_when_no_puzzles():
    """When no puzzle is found (empty DB), the endpoint must return 503."""
    with patch(
        "app.api.v1.puzzles.get_random_puzzle",
        new_callable=AsyncMock,
        return_value=None,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/puzzles/random")

    assert response.status_code == 503
    assert response.json()["detail"] == "No puzzles available"
