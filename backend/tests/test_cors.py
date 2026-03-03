"""
CORS integration tests.

Verifies that:
- Preflight OPTIONS requests return correct headers for allowed origins.
- Actual requests from allowed origins include Access-Control-Allow-Origin.
- Requests from disallowed origins do NOT get the header.
- Unhandled server errors (500) still return CORS headers — this guards against
  the bug where raw Python exceptions bypassed CORSMiddleware and hit
  ServerErrorMiddleware, which returned a bare 500 with no CORS headers.
"""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

ALLOWED_ORIGIN = "http://localhost:3000"
UNKNOWN_ORIGIN = "http://evil.example.com"


# ---------------------------------------------------------------------------
# Preflight (OPTIONS)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cors_preflight_register():
    """OPTIONS preflight for /auth/register returns CORS headers."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/api/v1/auth/register",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
    assert "POST" in response.headers.get("access-control-allow-methods", "")


@pytest.mark.asyncio
async def test_cors_preflight_login():
    """OPTIONS preflight for /auth/login returns CORS headers."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


# ---------------------------------------------------------------------------
# Actual requests — allowed origin
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cors_header_present_on_4xx():
    """Validation error (422) from allowed origin still includes CORS header."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "short"},
            headers={"Origin": ALLOWED_ORIGIN},
        )

    assert response.status_code == 422
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


@pytest.mark.asyncio
async def test_cors_header_present_on_success():
    """Successful register (mocked) from allowed origin includes CORS header."""
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock
    from uuid import uuid4

    mock_user = AsyncMock()
    mock_user.id = uuid4()
    mock_user.email = "cors@example.com"
    mock_user.created_at = datetime.now(timezone.utc)

    with patch("app.api.v1.auth.register_user", new_callable=AsyncMock, return_value=mock_user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={"email": "cors@example.com", "password": "password123"},
                headers={"Origin": ALLOWED_ORIGIN},
            )

    assert response.status_code == 201
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


@pytest.mark.asyncio
async def test_cors_header_present_on_server_error():
    """Unhandled server error (500) from allowed origin still includes CORS header.

    This tests the fix for the production bug: raw Python exceptions previously
    bypassed CORSMiddleware via ServerErrorMiddleware, dropping the CORS header.
    The global exception_handler in main.py routes all unhandled exceptions back
    through ExceptionMiddleware (which is inside CORSMiddleware), so the header
    is always injected.

    The middleware registered via @app.middleware("http") in main.py sits inside
    CORSMiddleware in the ASGI stack. It catches all unhandled exceptions and
    returns a JSONResponse, which then flows back through CORSMiddleware's send
    wrapper so CORS headers are added before the response reaches the client.
    """
    with patch(
        "app.api.v1.auth.register_user",
        new_callable=AsyncMock,
        side_effect=RuntimeError("DB connection lost"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={"email": "test@example.com", "password": "password123"},
                headers={"Origin": ALLOWED_ORIGIN},
            )

    assert response.status_code == 500
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


# ---------------------------------------------------------------------------
# Disallowed origin
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cors_header_absent_for_unknown_origin():
    """Requests from an unknown origin do not receive Access-Control-Allow-Origin."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email"},  # triggers 422 without DB
            headers={"Origin": UNKNOWN_ORIGIN},
        )

    assert response.headers.get("access-control-allow-origin") is None
