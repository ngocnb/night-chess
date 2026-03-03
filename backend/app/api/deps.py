from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token

# OAuth2 scheme for Bearer token
oauth2_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials_exception: Annotated[
        HTTPException,
        Depends(
            lambda: HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        ),
    ],
    token: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Depends(oauth2_scheme),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Get the current authenticated user from a JWT access token.
    Raises 401 on invalid/expired token or missing user.
    """
    if token is None or token.credentials is None:
        raise credentials_exception

    user_id = decode_access_token(token.credentials)
    if user_id is None:
        raise credentials_exception

    # Fetch user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


async def get_optional_user(
    token: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Depends(oauth2_scheme),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[User]:
    """
    Get the current user if authenticated, None otherwise.
    Does not raise on invalid/missing token.
    """
    if token is None or token.credentials is None:
        return None

    user_id = decode_access_token(token.credentials)
    if user_id is None:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
