from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_user
from app.db.session import get_db
from app.models.puzzle import Puzzle
from app.models.user import User
from app.schemas.puzzle import PuzzleResponse
from app.schemas.progress import SubmitRequest, SubmitResponse
from app.services.progress_service import submit_result
from app.services.puzzle_service import get_random_puzzle

router = APIRouter()


@router.get("/random", response_model=PuzzleResponse)
async def random_puzzle(
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """Return a single random chess puzzle.

    If user is authenticated, uses their rating to filter puzzles (±200 window).
    Guests receive a purely random puzzle.
    """
    user_rating = user.rating if user else None
    row = await get_random_puzzle(db, user_rating=user_rating)
    if row is None:
        raise HTTPException(status_code=503, detail="No puzzles available")
    return {
        "id": row["id"],
        "fen": row["fen"],
        "moves": row["moves"].split(),
        "rating": row["rating"],
        "themes": row["themes"].split() if row["themes"] else None,
    }


@router.post("/{puzzle_id}/submit", response_model=SubmitResponse)
async def submit_puzzle(
    puzzle_id: str,
    request: SubmitRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a puzzle result for the authenticated user.
    Records the result (solved/failed) and optional time spent.
    """
    # Verify puzzle exists
    from sqlalchemy import select

    result = await db.execute(select(Puzzle).where(Puzzle.id == puzzle_id))
    puzzle = result.scalar_one_or_none()

    if not puzzle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Puzzle '{puzzle_id}' not found",
        )

    # Submit result
    progress, new_rating = await submit_result(
        db, user.id, puzzle_id, request.result, request.time_spent_ms
    )

    return SubmitResponse(
        puzzle_id=puzzle_id,
        result=progress.result,
        solved_at=progress.solved_at,
        new_rating=new_rating,
    )
