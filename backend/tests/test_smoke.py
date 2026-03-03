"""Automated smoke tests — replaces the Sprint 2 manual exit gate checks.

Run with:
    cd backend && pytest -m integration

Covers:
    - Register → Login → Submit puzzle → progress row recorded
    - Expired access token → 401; valid refresh cookie → new access token
    - Logout → refresh cookie revoked → next refresh returns 401
    - Auth service error branches (duplicate email, wrong password, invalid/expired refresh token)
    - Progress service upsert and pagination branches
"""
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.config import get_settings


# ---------------------------------------------------------------------------
# Smoke test 1: Register → Login → Submit → progress recorded
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_register_login_submit_progress(integration_client, seeded_puzzle):
    """Full authenticated flow: register, login, submit puzzle, verify progress."""
    # Register
    r = await integration_client.post(
        "/api/v1/auth/register",
        json={"email": "smoke1@example.com", "password": "password123"},
    )
    assert r.status_code == 201

    # Login
    r = await integration_client.post(
        "/api/v1/auth/login",
        json={"email": "smoke1@example.com", "password": "password123"},
    )
    assert r.status_code == 200
    access_token = r.json()["access_token"]

    # Submit puzzle result
    r = await integration_client.post(
        f"/api/v1/puzzles/{seeded_puzzle}/submit",
        json={"result": "solved", "time_spent_ms": 5000},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert r.status_code == 200

    # Verify the progress row was recorded
    r = await integration_client.get(
        "/api/v1/users/me/progress",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["puzzle_id"] == seeded_puzzle
    assert data["items"][0]["result"] == "solved"
    assert data["items"][0]["time_spent_ms"] == 5000


# ---------------------------------------------------------------------------
# Smoke test 2: Expired access token → 401; refresh cookie → new token
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_expired_token_refresh(integration_client):
    """Expired access token returns 401; valid refresh cookie issues a new token."""
    settings = get_settings()

    # Register and login to get a real refresh cookie stored in the client
    await integration_client.post(
        "/api/v1/auth/register",
        json={"email": "smoke2@example.com", "password": "password123"},
    )
    r = await integration_client.post(
        "/api/v1/auth/login",
        json={"email": "smoke2@example.com", "password": "password123"},
    )
    assert r.status_code == 200

    # Forge an already-expired access token using the real signing key
    expired_token = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000099",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            "iat": datetime.now(timezone.utc) - timedelta(minutes=16),
            "type": "access",
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    # Expired token → 401
    r = await integration_client.get(
        "/api/v1/users/me/progress",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert r.status_code == 401

    # Client still holds the valid refresh cookie from login → new access token
    r = await integration_client.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    assert r.json()["access_token"]  # non-empty


# ---------------------------------------------------------------------------
# Smoke test 3: Logout → refresh token revoked → next refresh returns 401
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_logout_revokes_refresh_token(integration_client):
    """After logout the refresh token is revoked; refresh returns 401."""
    # Register and login
    await integration_client.post(
        "/api/v1/auth/register",
        json={"email": "smoke3@example.com", "password": "password123"},
    )
    r = await integration_client.post(
        "/api/v1/auth/login",
        json={"email": "smoke3@example.com", "password": "password123"},
    )
    assert r.status_code == 200

    # Logout — cookie path is /api/v1/auth so httpx sends it here automatically
    r = await integration_client.post("/api/v1/auth/logout")
    assert r.status_code == 204

    # The refresh cookie is now revoked in the DB — any refresh attempt returns 401
    r = await integration_client.post("/api/v1/auth/refresh")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Auth service error branches
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_register_duplicate_email(integration_client):
    """Registering the same email twice returns 409."""
    payload = {"email": "dup@example.com", "password": "password123"}
    await integration_client.post("/api/v1/auth/register", json=payload)
    r = await integration_client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409


@pytest.mark.integration
async def test_login_wrong_password(integration_client):
    """Correct email, wrong password returns 401."""
    await integration_client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpw@example.com", "password": "password123"},
    )
    r = await integration_client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.com", "password": "notthepassword"},
    )
    assert r.status_code == 401


@pytest.mark.integration
async def test_login_unknown_email(integration_client):
    """Login with an email that was never registered returns 401."""
    r = await integration_client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "password123"},
    )
    assert r.status_code == 401


@pytest.mark.integration
async def test_refresh_invalid_token(integration_client):
    """A refresh cookie whose hash is not in the DB returns 401."""
    r = await integration_client.post(
        "/api/v1/auth/refresh",
        headers={"Cookie": "refresh_token=completely_bogus_token_not_in_db"},
    )
    assert r.status_code == 401


@pytest.mark.integration
async def test_refresh_expired_token(integration_client, db_session):
    """A refresh token whose expires_at is in the past returns 401."""
    from sqlalchemy import update
    from app.models.refresh_token import RefreshToken

    # Register and login — capture the raw token from the Set-Cookie header
    await integration_client.post(
        "/api/v1/auth/register",
        json={"email": "expiry@example.com", "password": "password123"},
    )
    r = await integration_client.post(
        "/api/v1/auth/login",
        json={"email": "expiry@example.com", "password": "password123"},
    )
    assert r.status_code == 200
    raw_token = r.cookies.get("refresh_token")

    # Back-date the token in the DB
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    past = datetime(2020, 1, 1, tzinfo=timezone.utc)
    await db_session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .values(expires_at=past)
    )
    await db_session.commit()

    # Refresh should now return 401 (expired)
    r = await integration_client.post("/api/v1/auth/refresh")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Progress service branches: upsert and pagination
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_submit_upsert(integration_client, seeded_puzzle):
    """Submitting the same puzzle twice updates the row instead of inserting a duplicate."""
    await integration_client.post(
        "/api/v1/auth/register",
        json={"email": "upsert@example.com", "password": "password123"},
    )
    r = await integration_client.post(
        "/api/v1/auth/login",
        json={"email": "upsert@example.com", "password": "password123"},
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # First attempt — failed
    await integration_client.post(
        f"/api/v1/puzzles/{seeded_puzzle}/submit",
        json={"result": "failed"},
        headers=headers,
    )

    # Second attempt — solved (should update, not insert)
    r = await integration_client.post(
        f"/api/v1/puzzles/{seeded_puzzle}/submit",
        json={"result": "solved", "time_spent_ms": 3000},
        headers=headers,
    )
    assert r.status_code == 200

    # Still only 1 row, with the updated result
    r = await integration_client.get("/api/v1/users/me/progress", headers=headers)
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["result"] == "solved"


@pytest.mark.integration
async def test_get_progress_pagination(integration_client, db_session, seeded_puzzle):
    """page_size=1 with 2 submitted puzzles: page 1 and page 2 each return 1 item."""
    from app.models.puzzle import Puzzle

    # Seed a second puzzle
    puzzle2 = Puzzle(
        id="smoke002",
        fen="rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1",
        moves="d7d5 c2c4",
        rating=1600,
        rating_deviation=80,
        popularity=90,
        nb_plays=2000,
    )
    db_session.add(puzzle2)
    await db_session.commit()

    await integration_client.post(
        "/api/v1/auth/register",
        json={"email": "page@example.com", "password": "password123"},
    )
    r = await integration_client.post(
        "/api/v1/auth/login",
        json={"email": "page@example.com", "password": "password123"},
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    for pid in [seeded_puzzle, "smoke002"]:
        await integration_client.post(
            f"/api/v1/puzzles/{pid}/submit",
            json={"result": "solved"},
            headers=headers,
        )

    # Page 1
    r = await integration_client.get(
        "/api/v1/users/me/progress?page=1&page_size=1", headers=headers
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert len(data["items"]) == 1
    assert data["page"] == 1

    # Page 2 — exercises the non-zero offset path in get_progress
    r = await integration_client.get(
        "/api/v1/users/me/progress?page=2&page_size=1", headers=headers
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert len(data["items"]) == 1
    assert data["page"] == 2
