from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SubmitRequest(BaseModel):
    result: Literal["solved", "failed"]
    time_spent_ms: int | None = None


class SubmitResponse(BaseModel):
    puzzle_id: str
    result: str
    solved_at: datetime


class ProgressItem(BaseModel):
    puzzle_id: str
    result: str
    time_spent_ms: int | None
    solved_at: datetime


class ProgressPage(BaseModel):
    items: list[ProgressItem]
    total: int
    page: int
    page_size: int
