"""
Tests for authentication endpoints: POST /api/v1/auth/{register,login,refresh,logout}.

These tests mock the auth_service functions to avoid real DB calls.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = AsyncMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def mock_tokens():
    """Mock tokens for login/refresh."""
    return {
        "raw_refresh": "test_raw_refresh_token_12345",
        "access": "test_access_token_67890",
        "new_raw_refresh": "test_new_raw_refresh_token_99999",
    }


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_success(mock_user):
    """Successful registration returns 201 with user data."""
    with patch(
        "app.api.v1.auth.register_user",
        new_callable=AsyncMock,
        return_value=mock_user,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={"email": "test@example.com", "password": "password123"},
            )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(mock_user):
    """Registering with duplicate email returns 409."""
    from fastapi import HTTPException

    with patch(
        "app.api.v1.auth.register_user",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=409, detail="Email already registered"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={"email": "existing@example.com", "password": "password123"},
            )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_invalid_email():
    """Registering with invalid email format returns 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "password123"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password():
    """Registering with password < 8 chars returns 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "short"},
        )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success(mock_user, mock_tokens):
    """Successful login returns 200 with access token and Set-Cookie header."""
    with patch(
        "app.api.v1.auth.login_user",
        new_callable=AsyncMock,
        return_value=(mock_user, mock_tokens["raw_refresh"], mock_tokens["access"]),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "password123"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == mock_tokens["access"]
    assert data["token_type"] == "bearer"

    # Check Set-Cookie header
    set_cookie = response.headers.get("set-cookie")
    assert set_cookie is not None
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/api/v1/auth/refresh" in set_cookie
    assert "Max-Age=604800" in set_cookie


@pytest.mark.asyncio
async def test_login_wrong_password():
    """Login with wrong password returns 401."""
    from fastapi import HTTPException

    with patch(
        "app.api.v1.auth.login_user",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=401, detail="Invalid email or password"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "wrongpassword"},
            )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email():
    """Login with unknown email returns 401."""
    from fastapi import HTTPException

    with patch(
        "app.api.v1.auth.login_user",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=401, detail="Invalid email or password"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "unknown@example.com", "password": "password123"},
            )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_success(mock_tokens):
    """Successful token refresh returns 200 with new access token and rotated cookie."""
    with patch(
        "app.api.v1.auth.refresh_tokens",
        new_callable=AsyncMock,
        return_value=(mock_tokens["access"], mock_tokens["new_raw_refresh"]),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": mock_tokens["raw_refresh"]},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == mock_tokens["access"]

    # Check Set-Cookie header with rotated token
    set_cookie = response.headers.get("set-cookie")
    assert set_cookie is not None
    assert "refresh_token=" in set_cookie


@pytest.mark.asyncio
async def test_refresh_missing_cookie():
    """Refresh without refresh token cookie returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_revoked_token(mock_tokens):
    """Refresh with revoked token returns 401."""
    from fastapi import HTTPException

    with patch(
        "app.api.v1.auth.refresh_tokens",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=401, detail="Refresh token has been revoked"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": mock_tokens["raw_refresh"]},
            )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_expired_token(mock_tokens):
    """Refresh with expired token returns 401."""
    from fastapi import HTTPException

    with patch(
        "app.api.v1.auth.refresh_tokens",
        new_callable=AsyncMock,
        side_effect=HTTPException(status_code=401, detail="Refresh token has expired"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": mock_tokens["raw_refresh"]},
            )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_success(mock_tokens):
    """Successful logout returns 204 and clears cookie."""
    with patch(
        "app.api.v1.auth.logout_user",
        new_callable=AsyncMock,
        return_value=None,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/logout",
                cookies={"refresh_token": mock_tokens["raw_refresh"]},
            )

    assert response.status_code == 204

    # Check cookie is cleared
    set_cookie = response.headers.get("set-cookie")
    assert set_cookie is not None
    assert "refresh_token=" in set_cookie


@pytest.mark.asyncio
async def test_logout_missing_cookie():
    """Logout without refresh token cookie returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 401
