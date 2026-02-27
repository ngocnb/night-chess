from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Puzzle(Base):
    __tablename__ = "puzzles"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)  # Lichess ID e.g. "00sHx"
    fen: Mapped[str] = mapped_column(Text, nullable=False)
    moves: Mapped[str] = mapped_column(Text, nullable=False)  # space-separated UCI moves
    rating: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    rating_deviation: Mapped[int] = mapped_column(Integer, nullable=False)
    popularity: Mapped[int] = mapped_column(Integer, nullable=False)
    nb_plays: Mapped[int] = mapped_column(Integer, nullable=False)
    themes: Mapped[str | None] = mapped_column(Text, nullable=True)
    game_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    opening_tags: Mapped[str | None] = mapped_column(Text, nullable=True)
