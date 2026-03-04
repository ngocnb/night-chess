from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_progress import UserProgress
from app.models.user import User


def calculate_elo_delta(user_rating: int, puzzle_rating: int, is_success: bool) -> int:
    """
    Calculate Elo rating delta for a puzzle result.

    Formula:
    - K = 32 (standard chess K-factor)
    - expected = 1 / (1 + 10^((puzzle_rating - user_rating) / 400))
    - Success: delta = +round(K * (1 - expected))
    - Fail: delta = -round(K * expected)

    Rating is clamped to [400, 3000] after application.
    """
    K = 32
    expected = 1 / (1 + 10 ** ((puzzle_rating - user_rating) / 400))

    if is_success:
        delta = round(K * (1 - expected))
    else:
        delta = -round(K * expected)

    return delta


async def submit_result(
    db: AsyncSession,
    user_id: UUID,
    puzzle_id: str,
    result: str,
    time_spent_ms: int | None,
) -> tuple[UserProgress, int]:
    """
    Submit a puzzle result for a user.
    Upserts: if a record already exists for (user_id, puzzle_id), updates it.
    Applies Elo rating delta based on result.
    Returns (UserProgress record, new_user_rating).
    """
    # Get user and puzzle info for rating calculation
    user_stmt = select(User).where(User.id == user_id)
    user = await db.scalar(user_stmt)
    if not user:
        raise ValueError(f"User {user_id} not found")

    # Get puzzle rating
    from app.models.puzzle import Puzzle
    puzzle_stmt = select(Puzzle).where(Puzzle.id == puzzle_id)
    puzzle = await db.scalar(puzzle_stmt)
    if not puzzle:
        raise ValueError(f"Puzzle {puzzle_id} not found")

    # Check for existing record
    stmt = select(UserProgress).where(
        UserProgress.user_id == user_id,
        UserProgress.puzzle_id == puzzle_id,
    )
    result_obj = await db.scalar(stmt)

    if result_obj:
        # Update existing
        result_obj.result = result
        result_obj.time_spent_ms = time_spent_ms
        result_obj.solved_at = datetime.now(timezone.utc)
    else:
        # Insert new
        result_obj = UserProgress(
            user_id=user_id,
            puzzle_id=puzzle_id,
            result=result,
            time_spent_ms=time_spent_ms,
        )
        db.add(result_obj)

    # Calculate and apply Elo delta
    is_success = result == "solved"
    elo_delta = calculate_elo_delta(user.rating, puzzle.rating, is_success)
    new_rating = user.rating + elo_delta
    # Clamp rating to [400, 3000]
    new_rating = max(400, min(3000, new_rating))
    user.rating = new_rating

    await db.commit()
    await db.refresh(result_obj)

    return result_obj, new_rating


async def get_progress(
    db: AsyncSession,
    user_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[UserProgress], int]:
    """
    Get a user's puzzle progress, paginated.
    Returns (list of UserProgress ordered by solved_at DESC, total count).
    """
    # Get total count
    count_stmt = select(func.count()).select_from(UserProgress).where(
        UserProgress.user_id == user_id
    )
    total = await db.scalar(count_stmt) or 0

    # Get paginated results
    offset = (page - 1) * page_size
    stmt = (
        select(UserProgress)
        .where(UserProgress.user_id == user_id)
        .order_by(UserProgress.solved_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(stmt)
    items = result.scalars().all()

    return list(items), total
