# Next Steps

## ~~Sprint 0 — completed~~ ✓

All items done. ADR-003 Accepted (TABLESAMPLE 0.167ms). Import script ships 44 tests.

## ~~Sprint 1 — completed~~ ✓

All items implemented and tested. 31 frontend tests pass.

### Sprint 1 exit gate — manual checks still required

- [ ] At least one **castling** puzzle solves end-to-end
- [ ] At least one **en passant** puzzle solves end-to-end
- [ ] At least one **promotion** puzzle solves end-to-end (pick Q/R/B/N from dialog)
- [ ] Guest can load → solve → click "Next puzzle →" → get a different puzzle
- [ ] No auth token required at any point

---

## Sprint 2 — Auth + Progress Tracking

### 1. Auth endpoints

- `POST /api/v1/auth/register` — bcrypt cost 12, return 201, duplicate email → 409
- `POST /api/v1/auth/login` — JWT access token (15min) + HttpOnly refresh token (7 days)
- `POST /api/v1/auth/refresh` — rotate refresh token, issue new access token
- `POST /api/v1/auth/logout` — revoke refresh token in DB
- Test coverage ≥ 80% on auth module

### 2. Puzzle submit + progress

- `POST /api/v1/puzzles/{id}/submit` — save result (correct/incorrect) for authenticated users
- `GET /api/v1/users/me/progress` — paginated solve history (most recent first)

### 3. Frontend auth

- `/register` page — email + password form, error display
- `/login` page — email + password form, redirect on success
- `AuthProvider` — in-memory access token + transparent refresh via `fetch` interceptor
- Sidebar: show logged-in user email + "Log out" link when authenticated

### Sprint 2 exit gate

- [ ] Register → Login → Solve puzzle → progress recorded
- [ ] Access token expires → transparent refresh via cookie (no user action)
- [ ] Logout clears token; next request returns 401
- [ ] Auth module test coverage ≥ 80%

---

## Sprint 3 — Dashboard + GDPR + Deploy

- Progress dashboard at `/dashboard` (solve count, accuracy, recent history)
- `DELETE /api/v1/users/me` — GDPR account deletion, CASCADE all user data
- Privacy policy page at `/privacy`
- 100+ real Lichess puzzles manually tested across themes — launch blocker
- Production deploy to self-hosted server via GitHub Actions (ADR-004)
