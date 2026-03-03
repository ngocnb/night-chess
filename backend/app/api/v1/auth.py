from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    logout_user,
    login_user,
    refresh_tokens,
    register_user,
    user_to_response,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user with email and password."""
    user = await register_user(db, email=request.email, password=request.password)
    return user_to_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Login with email and password.
    Returns access token in response body and refresh token as HttpOnly cookie.
    """
    user, raw_refresh_token, access_token = await login_user(db, request.email, request.password)

    response = Response(
        content=TokenResponse(access_token=access_token).model_dump_json(),
        media_type="application/json",
    )
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        samesite="lax",
        path="/api/v1/auth/refresh",
        max_age=604800,  # 7 days
    )
    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Refresh access token using refresh token cookie.
    Returns new access token and rotated refresh token cookie.
    """
    raw_token = request.cookies.get("refresh_token")

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    access_token, new_raw_token = await refresh_tokens(db, raw_token)

    response = Response(
        content=TokenResponse(access_token=access_token).model_dump_json(),
        media_type="application/json",
    )
    response.set_cookie(
        key="refresh_token",
        value=new_raw_token,
        httponly=True,
        samesite="lax",
        path="/api/v1/auth/refresh",
        max_age=604800,  # 7 days
    )
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    """Logout user and revoke refresh token."""
    raw_token = request.cookies.get("refresh_token")

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    await logout_user(db, raw_token)

    response = Response(status_code=204)
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth/refresh",
    )
    return response
