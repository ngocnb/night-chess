import random

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_random_puzzle(db: AsyncSession):
    """
    Return a random puzzle row as a mapping, or None if the table is empty.

    Strategy (per ADR-003 — Accepted, benchmarked 2026-03-02):
    1. Primary: TABLESAMPLE SYSTEM(0.01) — 0.167ms on 3.5M rows (vs 2630ms for ORDER BY RANDOM()).
       Samples ~350 rows at the page level, returns one. O(1) relative to table size.
    2. Fallback: random OFFSET — only triggers if TABLESAMPLE returns nothing (rare on large tables).
       Benchmarked at 357ms; acceptable as an emergency fallback only.
    """
    result = await db.execute(
        text("SELECT id, fen, moves, rating, themes FROM puzzles TABLESAMPLE SYSTEM(0.01) LIMIT 1")
    )
    row = result.mappings().first()

    if row is None:
        count_result = await db.execute(text("SELECT COUNT(*) FROM puzzles"))
        count = count_result.scalar_one()
        if count == 0:
            return None
        offset = random.randint(0, count - 1)
        result = await db.execute(
            text(
                "SELECT id, fen, moves, rating, themes FROM puzzles LIMIT 1 OFFSET :offset"
            ),
            {"offset": offset},
        )
        row = result.mappings().first()

    return row
