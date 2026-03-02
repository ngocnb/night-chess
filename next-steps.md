# Next Steps

## Sprint 0 — remaining exit gate

Puzzles are imported. One item left before Sprint 1 can start:

**Benchmark random puzzle selection (ADR-003)**

Run these queries against the full dataset and update `ADR-003` status to Accepted or Superseded:

```sql
-- 1. Baseline: ORDER BY RANDOM() — expected slow (~500ms-2s)
EXPLAIN ANALYZE SELECT id, fen, moves, rating FROM puzzles ORDER BY RANDOM() LIMIT 1;

-- 2. TABLESAMPLE — target: < 50ms
EXPLAIN ANALYZE SELECT id, fen, moves, rating FROM puzzles TABLESAMPLE SYSTEM(0.01) LIMIT 1;

-- 3. TABLESAMPLE with fallback (empty sample guard)
EXPLAIN ANALYZE
  SELECT id, fen, moves, rating FROM puzzles TABLESAMPLE SYSTEM(0.01) LIMIT 1
  UNION ALL
  SELECT id, fen, moves, rating FROM puzzles OFFSET floor(random() * (SELECT COUNT(*) FROM puzzles)) LIMIT 1
  LIMIT 1;

-- 4. Random OFFSET — baseline alternative
EXPLAIN ANALYZE
  SELECT id, fen, moves, rating FROM puzzles
  OFFSET floor(random() * (SELECT COUNT(*) FROM puzzles))
  LIMIT 1;
```

Record results in `.aiwg/architecture/adr/ADR-003-random-puzzle-selection.md` and change status from **Proposed** → **Accepted** (or **Superseded** if TABLESAMPLE is too sparse).

---

## Sprint 1 — Puzzle API + Chessboard + Guest Flow

Goal: a guest can load the site, see a real puzzle, attempt to solve it, and click Next Puzzle.

### 1. `GET /api/v1/puzzles/random` endpoint

- File: `backend/app/api/v1/puzzles.py`
- Use the winning strategy from ADR-003 benchmarks
- Response: `{ id, fen, moves, rating, themes }`
- Benchmark locally: p95 < 300ms on 3.5M rows
- Tests in `backend/tests/test_puzzles_api.py`: valid schema, rating is int, fen non-empty

### 2. PuzzleBoard React component

- Files: `frontend/src/components/PuzzleBoard.tsx`
- Install: `react-chessboard`, `chess.js` (already in `package.json` — run `npm install`)
- Props: `{ fen: string, moves: string[], onComplete: () => void }`
- chess.js validates all moves — zero custom chess logic (non-negotiable, see ADR-002)
- Illegal moves snap back silently
- Correct move → opponent auto-replies after 500ms
- `onComplete` fires exactly once on last solution move
- Handles: castling, en passant, pawn promotion modal (Q/R/B/N)
- Manual test: solve 10+ real puzzles covering castling, en passant, promotion before marking done

### 3. Guest puzzle page

- File: `frontend/src/app/page.tsx` (replace placeholder)
- Fetch from `GET /api/v1/puzzles/random` on load
- Render `PuzzleBoard` with received fen + moves
- "Next Puzzle" button → new fetch
- Error state: "Could not load puzzle — try again"
- No auth required

### 4. Puzzle rating display

- Show Lichess rating next to the board: `Rating: 1487`

### Sprint 1 exit gate

- [ ] `GET /api/v1/puzzles/random` returns a valid puzzle in < 300ms p95
- [ ] Illegal moves are rejected silently (piece snaps back)
- [ ] At least one castling, one en passant, and one promotion puzzle solve end-to-end
- [ ] Guest can load → solve → click Next Puzzle → get a different puzzle
- [ ] No auth token required at any point

---

## Sprint 2 — Auth + Progress Tracking (after Sprint 1)

- `POST /api/v1/auth/register` — bcrypt cost 12, return 201
- `POST /api/v1/auth/login` — JWT access token (15min) + refresh token (HttpOnly cookie, 7 days)
- `POST /api/v1/auth/refresh` + `POST /api/v1/auth/logout`
- `POST /api/v1/puzzles/{id}/submit` — save result for authenticated users
- `GET /api/v1/users/me/progress` — paginated solve history
- Next.js: `/register`, `/login`, `AuthProvider` with in-memory token + transparent refresh
- Test coverage ≥ 80% on auth module

## Sprint 3 — Dashboard + GDPR + Deploy (after Sprint 2)

- Progress dashboard at `/dashboard`
- `DELETE /api/v1/users/me` (GDPR account deletion, CASCADE)
- Privacy policy page at `/privacy`
- 100+ real Lichess puzzles manually tested — launch blocker until done
- Production deploy to self-hosted server via GitHub Actions
