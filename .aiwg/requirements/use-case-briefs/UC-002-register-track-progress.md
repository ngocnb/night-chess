# UC-002: Register and Track Progress

## Summary

A chess enthusiast creates an account with email and password, logs in with a JWT-based session, solves puzzles, and reviews their solve history and basic statistics on a progress dashboard. Progress persists across sessions and devices.

## Actor

Registered User (authenticated)

## Preconditions

- Registration form is accessible at `/register`
- FastAPI `/auth/register` and `/auth/login` endpoints are operational
- PostgreSQL `users` and `user_progress` tables exist
- Email address is not already registered

## Main Flow

**Registration**
1. User navigates to `/register`
2. User enters email address and password (minimum 8 characters)
3. Frontend validates email format and password length before submitting
4. Frontend sends `POST /auth/register` with `{email, password}`
5. Backend validates uniqueness of email; hashes password with bcrypt (cost factor >= 12)
6. Backend creates user record; returns `201 Created` with `{user_id, email}`
7. Frontend redirects user to `/login` with a success notice

**Login**
8. User enters email and password on `/login`
9. Frontend sends `POST /auth/login` with `{email, password}`
10. Backend verifies password hash; issues JWT access token (15-minute expiry) and refresh token (7-day expiry)
11. Frontend stores access token in memory and refresh token in an HttpOnly cookie
12. User is redirected to the puzzle page; subsequent API calls include the Bearer token

**Progress Recording**
13. After each puzzle attempt, the frontend sends `POST /users/progress` with `{puzzle_id, result, time_spent_ms}`
14. Backend records the solve entry in `user_progress`; associates it with the authenticated user

**Dashboard**
15. User navigates to `/dashboard`
16. Frontend calls `GET /users/progress` (paginated, most recent first)
17. Dashboard displays: total puzzles attempted, total solved, solve rate (%), and a list of recent puzzle results

## Alternative Flows

**AF-1: Duplicate email registration**
- At step 5, backend returns `409 Conflict`
- Frontend displays: "An account with this email already exists. Log in instead?"

**AF-2: Incorrect password on login**
- At step 10, backend returns `401 Unauthorized`
- Frontend displays: "Invalid email or password" (generic message, no enumeration of which field is wrong)
- After 5 consecutive failures on the same email within 15 minutes, the backend returns `429 Too Many Requests`

**AF-3: Expired access token**
- On any authenticated API call, backend returns `401`
- Frontend silently exchanges the refresh token via `POST /auth/refresh`
- If the refresh token is also expired, the user is redirected to `/login`

**AF-4: Guest converts to registered user**
- Guest completes puzzles without an account; history is not retained
- After registering, only puzzles solved after registration are tracked (no retroactive guest history in v1)

## Success Criteria

- [ ] User registers with a valid email and password; duplicate email returns an actionable error
- [ ] Passwords are hashed with bcrypt (cost >= 12); plaintext passwords never stored or logged
- [ ] Login succeeds with correct credentials and returns a scoped JWT access token
- [ ] Access token expires within 15 minutes; refresh token enables silent re-authentication
- [ ] Each puzzle solve (result + time) is recorded and associated with the correct user
- [ ] Dashboard displays accurate solve count and solve rate
- [ ] Users cannot access another user's progress data (user-scoped authorization enforced)
- [ ] Auth endpoints enforce rate limiting (max 5 login attempts / 15 min per email)

## Dependencies

- FastAPI endpoints: `/auth/register`, `/auth/login`, `/auth/refresh`, `/users/progress`
- PostgreSQL tables: `users`, `user_progress`
- `bcrypt` library (Python) for password hashing
- `python-jose` or `PyJWT` for JWT issuance and validation
- Pydantic models for request/response validation
- UC-001 (Solve Random Puzzle) — progress is recorded when puzzles are solved

## Priority

Must Have
