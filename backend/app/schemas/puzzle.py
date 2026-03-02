from typing import Optional

from pydantic import BaseModel


class PuzzleResponse(BaseModel):
    id: str
    fen: str
    moves: list[str]  # split from space-separated UCI string stored in DB
    rating: int
    themes: Optional[list[str]] = None  # split from space-separated string; None if empty/NULL

    model_config = {"from_attributes": True}
