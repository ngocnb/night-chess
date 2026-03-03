"""Integration test fixtures.

Requires:
    1. Copy backend/.env.test.example → backend/.env.test
    2. Create the test database once:
         psql -U nightchess -c "CREATE DATABASE nightchess_test;"
    3. Run: cd backend && pytest -m integration

Unit tests (no DB) still run normally with: pytest -m "not integration"
"""
import os
from pathlib import Path

# Load .env.test before any app imports so get_settings() picks up JWT keys etc.
_env_test_file = Path(__file__).parent.parent / ".env.test"
if _env_test_file.exists():
    for _line in _env_test_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app
from app.models.base import Base

_TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "")


def _require_test_db():
    if not _TEST_DB_URL:
        pytest.skip(
            "TEST_DATABASE_URL not set — copy backend/.env.test.example to backend/.env.test"
        )


@pytest_asyncio.fixture
async def integration_client():
    """HTTP client backed by a fresh test database.

    Creates all tables before the test, drops them after.
    FastAPI's get_db dependency is overridden to use the test DB.
    """
    _require_test_db()

    engine = create_async_engine(_TEST_DB_URL, echo=False)
    SessionMaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def _override_get_db():
        async with SessionMaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.pop(get_db, None)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(integration_client):
    """Direct DB session for seeding data and asserting DB state.

    Depends on integration_client so tables already exist.
    """
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    SessionMaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionMaker() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_puzzle(db_session):
    """Insert one puzzle row so the submit endpoint FK constraint is satisfied."""
    from app.models.puzzle import Puzzle

    puzzle = Puzzle(
        id="smoke001",
        fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        moves="e7e5 g1f3",
        rating=1500,
        rating_deviation=100,
        popularity=80,
        nb_plays=1000,
    )
    db_session.add(puzzle)
    await db_session.commit()
    return puzzle.id
