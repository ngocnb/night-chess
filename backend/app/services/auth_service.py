import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt as _bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.auth import UserResponse

# settings
settings = get_settings()


def _prehash(plain: str) -> bytes:
    """SHA-256 prehash to produce a fixed 32-byte input for bcrypt.

    This avoids bcrypt's 72-byte limit while ensuring every bit of the
    password is factored into the hash. bcrypt 4.x+ enforces the limit
    strictly, and passlib 1.7.x is incompatible with bcrypt 4.x+.
    """
    return hashlib.sha256(plain.encode("utf-8")).digest()


def hash_password(plain: str) -> str:
    """Hash a password using bcrypt (cost factor 12) with SHA-256 prehashing."""
    salt = _bcrypt.gensalt(rounds=12)
    return _bcrypt.hashpw(_prehash(plain), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return _bcrypt.checkpw(_prehash(plain), hashed.encode("utf-8"))


def create_access_token(user_id: UUID) -> str:
    """Create a JWT access token with 15-minute expiry."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token() -> tuple[str, str]:
    """
    Create a refresh token and return (raw_token, token_hash).
    The raw token is sent to the client as a cookie.
    The hash is stored in the database.
    """
    raw_token = secrets.token_urlsafe(32)  # 256-bit random token
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash


def decode_access_token(token: str) -> UUID | None:
    """
    Decode and validate a JWT access token.
    Returns the user_id UUID if valid, None if invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return UUID(user_id)
    except JWTError:
        return None


async def register_user(db: AsyncSession, email: str, password: str) -> User:
    """
    Register a new user.
    Raises HTTPException 409 if email already exists.
    Returns the created User.
    """
    from fastapi import HTTPException

    # Check for duplicate email
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create new user
    password_hash = hash_password(password)
    user = User(email=email, password_hash=password_hash)

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def login_user(db: AsyncSession, email: str, password: str) -> tuple[User, str, str]:
    """
    Authenticate a user and create tokens.
    Returns (user, raw_refresh_token, access_token).
    Raises HTTPException 401 on invalid credentials.
    """
    from fastapi import HTTPException

    # Find user by email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Update last_login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    # Create tokens
    access_token = create_access_token(user.id)
    raw_refresh_token, token_hash = create_refresh_token()

    # Store refresh token in DB
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expire,
    )

    db.add(refresh_token)
    await db.commit()

    return user, raw_refresh_token, access_token


async def refresh_tokens(db: AsyncSession, raw_token: str) -> tuple[str, str]:
    """
    Rotate refresh tokens.
    Returns (new_access_token, new_raw_refresh_token).
    Raises HTTPException 401 if token is missing, invalid, expired, or revoked.
    """
    from fastapi import HTTPException

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    # Find the refresh token
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    refresh_token = result.scalar_one_or_none()

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if refresh_token.revoked:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    if refresh_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token has expired")

    # Get user
    result = await db.execute(select(User).where(User.id == refresh_token.user_id))
    user = result.scalar_one()

    # Revoke old token
    refresh_token.revoked = True

    # Create new tokens
    access_token = create_access_token(user.id)
    new_raw_token, new_token_hash = create_refresh_token()

    # Store new refresh token
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    new_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=new_token_hash,
        expires_at=expire,
    )

    db.add(new_refresh_token)
    await db.commit()

    return access_token, new_raw_token


async def logout_user(db: AsyncSession, raw_token: str) -> None:
    """
    Logout a user by revoking their refresh token.
    """
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    # Find and revoke the refresh token
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    refresh_token = result.scalar_one_or_none()

    if refresh_token:
        refresh_token.revoked = True
        await db.commit()


def user_to_response(user: User) -> UserResponse:
    """Convert a User model to a UserResponse schema."""
    return UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
    )
