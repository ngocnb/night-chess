from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_progress import UserProgress


async def submit_result(
    db: AsyncSession,
    user_id: UUID,
    puzzle_id: str,
    result: str,
    time_spent_ms: int | None,
) -> UserProgress:
    """
    Submit a puzzle result for a user.
    Upserts: if a record already exists for (user_id, puzzle_id), updates it.
    Returns the UserProgress record.
    """
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

    await db.commit()
    await db.refresh(result_obj)

    return result_obj


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
