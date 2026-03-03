from fastapi import APIRouter

from app.api.v1 import auth, puzzles, users

router = APIRouter()
router.include_router(auth.router, tags=["auth"])
router.include_router(puzzles.router, prefix="/puzzles", tags=["puzzles"])
router.include_router(users.router, prefix="/users", tags=["users"])
