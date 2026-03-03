from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.progress import ProgressPage, ProgressItem
from app.services.progress_service import get_progress
from app.services.auth_service import user_to_response
from app.schemas.auth import UserResponse

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: User = Depends(get_current_user)):
    """Get the current authenticated user's information."""
    return user_to_response(user)


@router.get("/me/progress", response_model=ProgressPage)
async def get_user_progress(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
):
    """Get the current user's puzzle progress history."""
    items, total = await get_progress(db, user.id, page, page_size)

    return ProgressPage(
        items=[
            ProgressItem(
                puzzle_id=item.puzzle_id,
                result=item.result,
                time_spent_ms=item.time_spent_ms,
                solved_at=item.solved_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
