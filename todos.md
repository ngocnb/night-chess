# Sprint 2 — Auth + Progress Tracking

## Status legend

- [ ] not started
- [~] in progress
- [x] done

---

## Sprint 1 exit gate — manual checks

- [ ] At least one **castling** puzzle solves end-to-end
- [ ] At least one **en passant** puzzle solves end-to-end
- [ ] At least one **promotion** puzzle solves end-to-end (pick Q/R/B/N from dialog)
- [ ] Guest can load → solve → click "Next puzzle →" → get a different puzzle
- [ ] No auth token required at any point

---

## Backend

### B1 — Dependencies

- [x] **B1.1** Add `python-jose[cryptography]` to `pyproject.toml` (JWT sign/verify)
- [x] **B1.2** Add `passlib[bcrypt]` to `pyproject.toml` (password hashing, bcrypt cost 12)
- [x] **B1.3** Run `pip install -e ".[dev]"` (or `pip install python-jose[cryptography] passlib[bcrypt]`) in the venv

### B2 — Auth schemas (`backend/app/schemas/auth.py`)

- [x] **B2.1** `RegisterRequest` — `email: EmailStr`, `password: str` (min 8 chars)
- [x] **B2.2** `LoginRequest` — `email: EmailStr`, `password: str`
- [x] **B2.3** `TokenResponse` — `access_token: str`, `token_type: str = "bearer"`
- [x] **B2.4** `UserResponse` — `id: UUID`, `email: str`, `created_at: datetime`

### B3 — Auth service (`backend/app/services/auth_service.py`)

- [x] **B3.1** `hash_password(plain: str) -> str` — `passlib` bcrypt, cost 12
- [x] **B3.2** `verify_password(plain: str, hashed: str) -> bool`
- [x] **B3.3** `create_access_token(user_id: UUID) -> str` — HS256, 15-min expiry, `sub` claim
- [x] **B3.4** `create_refresh_token() -> tuple[str, str]` — returns `(raw_token, sha256_hash)`; store hash only
- [x] **B3.5** `decode_access_token(token: str) -> UUID | None` — returns `None` on invalid/expired
- [x] **B3.6** `register_user(db, email, password) -> User` — check duplicate email (→ 409), insert user
- [x] **B3.7** `login_user(db, email, password) -> tuple[User, str, str]` — verify creds, create both tokens, persist `RefreshToken` row, update `last_login`
- [x] **B3.8** `refresh_tokens(db, raw_token: str) -> tuple[str, str]` — look up hash, check not revoked/expired, revoke old row, issue new pair (rotation)
- [x] **B3.9** `logout_user(db, raw_token: str) -> None` — mark `RefreshToken.revoked = True`

### B4 — Auth dependency (`backend/app/api/deps.py`)

- [x] **B4.1** `get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)) -> User` — decode Bearer token; raise `401` on invalid/expired
- [x] **B4.2** `get_optional_user(...)` — same but returns `None` instead of raising (used by submit endpoint for future guest logic)

### B5 — Auth router (`backend/app/api/v1/auth.py`)

- [x] **B5.1** `POST /auth/register` → 201 `UserResponse`; 409 on duplicate email
- [x] **B5.2** `POST /auth/login` → 200 `TokenResponse` (access token in body) + `Set-Cookie: refresh_token=<raw>; HttpOnly; SameSite=Lax; Path=/api/v1/auth/refresh; Max-Age=604800`
- [x] **B5.3** `POST /auth/refresh` → read `refresh_token` cookie → 200 `TokenResponse` + rotated `Set-Cookie`; 401 on missing/invalid/revoked/expired
- [x] **B5.4** `POST /auth/logout` → read `refresh_token` cookie → revoke in DB → 204; clear cookie in response

### B6 — Progress schemas (`backend/app/schemas/progress.py`)

- [x] **B6.1** `SubmitRequest` — `result: Literal["solved", "failed"]`, `time_spent_ms: int | None`
- [x] **B6.2** `SubmitResponse` — `puzzle_id: str`, `result: str`, `solved_at: datetime`
- [x] **B6.3** `ProgressItem` — `puzzle_id: str`, `result: str`, `time_spent_ms: int | None`, `solved_at: datetime`
- [x] **B6.4** `ProgressPage` — `items: list[ProgressItem]`, `total: int`, `page: int`, `page_size: int`

### B7 — Progress service (`backend/app/services/progress_service.py`)

- [x] **B7.1** `submit_result(db, user_id, puzzle_id, result, time_spent_ms) -> UserProgress` — upsert (conflict on unique constraint → update result + time)
- [x] **B7.2** `get_progress(db, user_id, page, page_size) -> tuple[list[UserProgress], int]` — ORDER BY `solved_at DESC`, paginated

### B8 — Puzzles + Users routers

- [x] **B8.1** Add `POST /puzzles/{id}/submit` to `backend/app/api/v1/puzzles.py` — requires `get_current_user`; calls `submit_result`; 404 if puzzle not found
- [x] **B8.2** Create `backend/app/api/v1/users.py` — `GET /users/me/progress` requires auth; returns `ProgressPage`
- [x] **B8.3** Register `auth` and `users` routers in `backend/app/api/v1/__init__.py`

### B9 — `.env.example` + config

- [x] **B9.1** Confirm `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` are in `backend/.env.example` (already in `config.py`, verify example matches)

### B10 — Backend tests (`backend/tests/test_auth.py`, `test_progress.py`)

- [x] **B10.1** `test_register_success` — 201, returns email + id
- [x] **B10.2** `test_register_duplicate_email` — 409
- [x] **B10.3** `test_register_invalid_email` — 422
- [x] **B10.4** `test_register_short_password` — 422
- [x] **B10.5** `test_login_success` — 200, access token in body, `Set-Cookie` header present
- [x] **B10.6** `test_login_wrong_password` — 401
- [x] **B10.7** `test_login_unknown_email` — 401
- [x] **B10.8** `test_refresh_success` — valid cookie → new access token + rotated cookie
- [x] **B10.9** `test_refresh_missing_cookie` — 401
- [x] **B10.10** `test_refresh_revoked_token` — 401
- [x] **B10.11** `test_refresh_expired_token` — 401
- [x] **B10.12** `test_logout_success` — 204, token revoked in DB
- [x] **B10.13** `test_logout_missing_cookie` — 401
- [ ] **B10.14** `test_submit_authenticated` — 200, progress row created (skipped — requires DB integration)
- [x] **B10.15** `test_submit_unauthenticated` — 401
- [ ] **B10.16** `test_submit_unknown_puzzle` — 404 (skipped — requires DB integration)
- [ ] **B10.17** `test_submit_upsert` — submitting same puzzle twice updates result, no duplicate row (integration test)
- [ ] **B10.18** `test_get_progress_paginated` — correct ordering and pagination meta (integration test)
- [x] **B10.19** `test_get_progress_unauthenticated` — 401
- [ ] **B10.20** Run `pytest --cov=app/services/auth_service --cov=app/api/v1/auth` — confirm ≥ 80%

---

## Frontend

### F1 — AuthProvider (`frontend/src/lib/auth.tsx`)

- [x] **F1.1** `AuthContext` — `{ user: { email: string } | null, accessToken: string | null, login, logout, refresh }`
- [x] **F1.2** `AuthProvider` — wraps app; stores access token in `useRef` (not state, avoids re-renders); exposes via context
- [x] **F1.3** `login(email, password)` — calls `POST /api/v1/auth/login`, stores access token in ref, sets `user` state
- [x] **F1.4** `logout()` — calls `POST /api/v1/auth/logout`, clears token ref + user state
- [x] **F1.5** `refresh()` — calls `POST /api/v1/auth/refresh`, updates token ref silently
- [x] **F1.6** Silent refresh on mount — call `refresh()` once on `AuthProvider` mount to restore session from cookie (avoids logout on page reload)

### F2 — Authenticated fetch helper (`frontend/src/lib/api.ts`)

- [x] **F2.1** `submitPuzzle(puzzleId, result, timeSpentMs, accessToken)` — calls `POST /api/v1/puzzles/{id}/submit`
- [x] **F2.2** `getProgress(accessToken, page, pageSize)` — calls `GET /api/v1/users/me/progress`

### F3 — Register page (`frontend/src/app/register/page.tsx`)

- [x] **F3.1** Email + password fields, submit button, link to `/login`
- [x] **F3.2** Client-side validation: non-empty email, password ≥ 8 chars (show inline error before fetch)
- [x] **F3.3** On success (201) → redirect to `/login` with `?registered=1` query param
- [x] **F3.4** On 409 → show "Email already registered" inline error
- [x] **F3.5** On network/5xx → show generic error message
- [x] **F3.6** Disable submit button while request in flight

### F4 — Login page (`frontend/src/app/login/page.tsx`)

- [x] **F4.1** Email + password fields, submit button, link to `/register`
- [x] **F4.2** Show `?registered=1` success banner ("Account created — please log in")
- [x] **F4.3** On success → call `AuthContext.login()` → redirect to `/`
- [x] **F4.4** On 401 → show "Invalid email or password"
- [x] **F4.5** Disable submit button while request in flight

### F5 — Sidebar auth section (`frontend/src/app/page.tsx`)

- [x] **F5.1** When `user === null` — show "Sign in" and "Register" links
- [x] **F5.2** When `user !== null` — show `user.email` and a "Log out" button
- [x] **F5.3** "Log out" button calls `AuthContext.logout()`
- [x] **F5.4** After logout, sidebar reverts to sign-in links (no page reload needed)

### F6 — Wire AuthProvider into layout

- [x] **F6.1** Wrap `<AuthProvider>` around `{children}` in `frontend/src/app/layout.tsx`

### F7 — Frontend tests

- [x] **F7.1** Existing tests updated to mock AuthProvider
- [x] **F7.2** All 31 existing tests pass

---

## Sprint 2 — addendum (from 2026-03-03 feedback)

These two items are small enough to close in Sprint 2 before the exit gate.

### F8 — Puzzle result UX (1 wrong move = Fail)

- [x] **F8.1** In `PuzzleBoard.tsx`: on first incorrect move, immediately set status to `'failed'` and lock the board (no retry). Remove "Incorrect — try again" flow.
- [x] **F8.2** Update `getStatusLabel` in `page.tsx`: map `'failed'` → "Incorrect — failed". Remove `'incorrect'` label.
- [x] **F8.3** Update `PuzzleStatus` type: replace `'incorrect'` with `'failed'` (or add `'failed'` alongside `'incorrect'` as distinct locked state).
- [x] **F8.4** Update all tests that reference the old `'incorrect'` status or "try again" text.
- [x] **F8.5** Call `submitPuzzle` to submit the puzzle result when it's failed or success.

### F9 — Next Puzzle button lock

- [x] **F9.1** In `page.tsx`: disable "Next puzzle →" button until `puzzleStatus === 'complete' || puzzleStatus === 'failed'`. Currently it's only disabled while `loading`.

---

## Sprint 2 exit gate

- [ ] Register → Login → Solve puzzle → progress row recorded (manual smoke test)
- [ ] Access token expires → transparent refresh via cookie, no user action required (manual smoke test)
- [ ] Logout clears token; next authenticated request returns 401 (manual smoke test)
- [ ] Auth module backend test coverage ≥ 80% (`pytest --cov` output)
- [x] All existing tests still pass (`pytest -x` + `yarn test`) — 75 backend + 43 frontend tests
- [x] Puzzle fails immediately on first wrong move (manual smoke test)
- [x] Next Puzzle button is locked while puzzle is in progress (manual smoke test)

---

## Sprint 3 — Rating System + UX Polish

*Goal: logged-in users have a meaningful rating that improves puzzle selection and visible move feedback.*

### B11 — Rating system (backend)

- [ ] **B11.1** Add `rating: int` column to `users` table (default 1500) — Alembic migration
- [ ] **B11.2** Add `UserResponse` field `rating: int` and `GET /users/me` endpoint returning it
- [ ] **B11.3** In `progress_service.py`: after inserting/updating progress row, apply Elo delta to `users.rating`:
  - Formula: K=32; `expected = 1/(1+10^((puzzle_rating − user_rating)/400))`
  - Success: `Δ = +round(K × (1 − expected))`
  - Fail: `Δ = −round(K × expected)`
  - Clamp rating to `[400, 3000]` to prevent runaway values
- [ ] **B11.4** Return updated `user_rating` in `SubmitResponse` so frontend can display the change
- [ ] **B11.5** Tests: `test_rating_increases_on_success`, `test_rating_decreases_on_fail`, `test_rating_clamped`

### B12 — Rating-based puzzle selection (backend)

- [ ] **B12.1** Add optional `user_rating: int | None` param to `get_random_puzzle` service
- [ ] **B12.2** When `user_rating` is provided: filter `WHERE rating BETWEEN (user_rating−200) AND (user_rating+200)` after TABLESAMPLE; if result is empty, fall back to unconstrained TABLESAMPLE
- [ ] **B12.3** Wire `GET /puzzles/random` to read `user_rating` from current user (via `get_optional_user`); guests get pure random
- [ ] **B12.4** Tests: `test_random_puzzle_uses_rating_window`, `test_random_puzzle_falls_back_on_empty_sample`

### F10 — King check highlight (frontend)

- [ ] **F10.1** In `PuzzleBoard.tsx`: after every move, detect `game.inCheck()`. If true, find the king's square and add it to `customSquareStyles` with `{ background: 'radial-gradient(circle, #ff0000 0%, transparent 70%)' }`.
- [ ] **F10.2** Clear the check highlight when the king is no longer in check.

### F11 — Move result markers (frontend)

- [ ] **F11.1** Track the last move's `to` square and whether it was correct or incorrect.
- [ ] **F11.2** On correct move: overlay a green ✓ badge on the destination square using `customSquareStyles` (background image or pseudo-element via CSS class).
- [ ] **F11.3** On incorrect move (first wrong = fail): overlay a red ✗ badge on the destination square before locking the board.
- [ ] **F11.4** Clear markers when a new puzzle loads.

### F12 — Rating display (frontend)

- [ ] **F12.1** Show logged-in user's rating in the sidebar (fetched from `GET /users/me`).
- [ ] **F12.2** After puzzle submit, animate the rating change (+Δ / −Δ) in the sidebar.

### Sprint 3 exit gate

- [ ] Logged-in user rating changes after each puzzle solve/fail
- [ ] Next puzzle is within ±200 of user's rating (verify via puzzle rating tag in sidebar)
- [ ] King in check shows red highlight
- [ ] Correct move shows ✓, wrong move shows ✗
- [ ] All existing tests still pass

---

## Sprint 4 — Dashboard + GDPR + Deploy

*(was Sprint 3 — pushed back to accommodate rating system)*

- [ ] Progress dashboard page at `/dashboard` (solve count, accuracy, rating graph, recent history)
- [ ] `DELETE /api/v1/users/me` — GDPR account deletion, CASCADE all user data
- [ ] Privacy policy page at `/privacy`
- [ ] 100+ real Lichess puzzles manually tested across themes — launch blocker
- [ ] Production deploy to self-hosted server via GitHub Actions (ADR-004)
