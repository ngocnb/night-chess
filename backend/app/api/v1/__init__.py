from fastapi import APIRouter

from app.api.v1 import puzzles

router = APIRouter()
router.include_router(puzzles.router, prefix="/puzzles", tags=["puzzles"])
