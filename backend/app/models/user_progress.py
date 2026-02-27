import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import TIMESTAMP as TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserProgress(Base):
    __tablename__ = "user_progress"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    puzzle_id: Mapped[str] = mapped_column(
        ForeignKey("puzzles.id"), nullable=False
    )
    result: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # "solved" | "failed"
    time_spent_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    solved_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ(timezone=True), server_default=func.now()
    )

    # unique constraint: one result per puzzle per user
    __table_args__ = (UniqueConstraint("user_id", "puzzle_id"),)

    # indexes on (user_id, solved_at DESC) are created in migration

    user: Mapped["User"] = relationship(back_populates="progress")
