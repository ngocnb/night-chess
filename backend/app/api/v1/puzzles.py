from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.puzzle import PuzzleResponse
from app.services.puzzle_service import get_random_puzzle

router = APIRouter()


@router.get("/random", response_model=PuzzleResponse)
async def random_puzzle(db: AsyncSession = Depends(get_db)):
    """Return a single random chess puzzle."""
    row = await get_random_puzzle(db)
    if row is None:
        raise HTTPException(status_code=503, detail="No puzzles available")
    return {
        "id": row["id"],
        "fen": row["fen"],
        "moves": row["moves"].split(),
        "rating": row["rating"],
        "themes": row["themes"].split() if row["themes"] else None,
    }
