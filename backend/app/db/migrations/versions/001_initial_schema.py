"""Initial schema — users, puzzles, user_progress, refresh_tokens

Revision ID: 001
Revises:
Create Date: 2026-02-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_login", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    # --- puzzles ---
    op.create_table(
        "puzzles",
        sa.Column("id", sa.String(10), nullable=False),
        sa.Column("fen", sa.Text(), nullable=False),
        sa.Column("moves", sa.Text(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("rating_deviation", sa.Integer(), nullable=False),
        sa.Column("popularity", sa.Integer(), nullable=False),
        sa.Column("nb_plays", sa.Integer(), nullable=False),
        sa.Column("themes", sa.Text(), nullable=True),
        sa.Column("game_url", sa.Text(), nullable=True),
        sa.Column("opening_tags", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_puzzles_rating", "puzzles", ["rating"])

    # --- user_progress ---
    op.create_table(
        "user_progress",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("puzzle_id", sa.String(10), nullable=False),
        sa.Column("result", sa.String(10), nullable=False),
        sa.Column("time_spent_ms", sa.Integer(), nullable=True),
        sa.Column(
            "solved_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["puzzle_id"], ["puzzles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "puzzle_id"),
        sa.CheckConstraint("result IN ('solved', 'failed')", name="ck_user_progress_result"),
    )
    op.create_index("idx_user_progress_user_id", "user_progress", ["user_id"])
    op.create_index(
        "idx_user_progress_solved_at",
        "user_progress",
        ["user_id", sa.text("solved_at DESC")],
    )

    # --- refresh_tokens ---
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("idx_refresh_tokens_hash", "refresh_tokens", ["token_hash"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index("idx_refresh_tokens_hash", table_name="refresh_tokens")
    op.drop_index("idx_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index("idx_user_progress_solved_at", table_name="user_progress")
    op.drop_index("idx_user_progress_user_id", table_name="user_progress")
    op.drop_table("user_progress")

    op.drop_index("idx_puzzles_rating", table_name="puzzles")
    op.drop_table("puzzles")

    op.drop_table("users")
