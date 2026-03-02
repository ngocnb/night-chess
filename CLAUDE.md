# Night Chess — Claude Instructions

This file contains project conventions and lessons learned for AI agents working on Night Chess.

## Project Overview

Chess puzzle training web app backed by the Lichess open puzzle database (3.5M puzzles).
- **Backend**: Python 3.12 + FastAPI + SQLAlchemy 2.x async + PostgreSQL 16
- **Frontend**: Next.js 14 (App Router, TypeScript), no component library, plain CSS
- **Chess**: `react-chessboard` v4 (rendering) + `chess.js` v1.3 (validation) — zero custom chess logic
- **Auth**: JWT access tokens (15min, in-memory) + refresh tokens (7-day, HttpOnly cookie) — Sprint 2

## Key Files

| Path | Purpose |
|------|---------|
| `backend/app/config.py` | Pydantic-settings; all env vars defined here — `.env.example` must match |
| `backend/app/api/v1/puzzles.py` | `GET /api/v1/puzzles/random` — the core puzzle endpoint |
| `backend/app/services/puzzle_service.py` | TABLESAMPLE SYSTEM(0.01) random selection |
| `backend/scripts/import_puzzles.py` | One-time Lichess CSV import (3.5M rows) |
| `frontend/src/components/PuzzleBoard.tsx` | Full puzzle UX — click-to-move, drag-drop, promotion, legal hints |
| `frontend/src/app/page.tsx` | Guest page — sidebar layout, status, next puzzle |
| `frontend/src/lib/api.ts` | `fetchRandomPuzzle()` — single API call |
| `.aiwg/architecture/adr/` | Architecture decisions — read before changing core tech choices |

## Architecture Decisions (never reverse without updating the ADR)

- **ADR-001**: JWT auth — access token in memory, refresh token in HttpOnly cookie
- **ADR-002**: `react-chessboard` + `chess.js` — zero custom chess logic, period
- **ADR-003**: TABLESAMPLE SYSTEM(0.01) for random puzzles — benchmarked 0.167ms on 3.5M rows
- **ADR-004**: Self-hosted deploy — single server, Docker Compose, GitHub Actions

## Lessons Learned

### Python / Backend

**Mock where the name is used, not where it's defined.**
```python
# puzzles.py does: from app.services.puzzle_service import get_random_puzzle
# Mock target = app.api.v1.puzzles.get_random_puzzle  ← correct
# NOT: app.services.puzzle_service.get_random_puzzle  ← wrong
```

**`.env.example` must mirror `app/config.py` exactly.**
Field names are `UPPER_CASE` of the Settings attribute. If you add/rename a field in `config.py`, update `backend/.env.example` immediately. Previous mismatch: `SECRET_KEY` vs `JWT_SECRET_KEY`.

**Docker Compose `env_file` pattern.**
All services use `env_file: ./backend/.env`. The backend service overrides `DATABASE_URL` to swap `@localhost` → `@db` for Docker networking. Frontend uses hardcoded `NEXT_PUBLIC_API_URL=http://localhost:8000` (not sensitive).

**TABLESAMPLE percentage.**
`SYSTEM(0.01)` samples ~350 rows from 3.5M. Empty sample is possible on a nearly-empty table; always add an OFFSET fallback in `puzzle_service.py`. ADR-003 is Accepted.

### JavaScript / Frontend

**`jest.config.js` not `jest.config.ts`.**
`next/jest` uses CommonJS. A `.ts` config requires `ts-node`, which is not installed. Always use `jest.config.js` with `require('next/jest')`.

**Wrap `jest.runAllTimers()` in `act()` in `afterEach`.**
Pending timers (e.g., 500ms opponent reply, 1000ms incorrect clear) fire outside React's update cycle if not wrapped:
```ts
afterEach(() => {
  act(() => { jest.runAllTimers() })
  jest.useRealTimers()
})
```

**Mock `ResizeObserver` in `jest.setup.ts`.**
jsdom doesn't implement `ResizeObserver`. Add a no-op stub globally:
```ts
global.ResizeObserver = class ResizeObserver {
  observe() {} unobserve() {} disconnect() {}
}
```

**Test against `onStatusChange` callbacks, not DOM text.**
`PuzzleBoard` reports status via `onStatusChange` prop — it renders no status text itself. Tests must capture the callback and assert on what it was called with.

**The puzzle `useEffect` fires on mount.**
The `[puzzle.id]` reset effect calls `onStatusChange('playing')` on initial render, not just on puzzle changes. Tests that check `onStatusChange` wasn't called on mount will fail.

**Page renders status in the sidebar, not inside PuzzleBoard.**
`page.tsx` manages `puzzleStatus` state. PuzzleBoard is purely a chess UI — the sidebar shows "White to play", "Best move!", etc. When testing `page.tsx`, mock `PuzzleBoard` and check sidebar text.

**Error message appears twice in `page.tsx`.**
`error` state renders one `<p>` in the board column and one in the sidebar. Use `getAllByText()` not `getByText()` in tests.

**`react-chessboard` v4 `boardWidth` prop is required for visibility.**
Without it the board defaults to its internal size, which may be 0px in a flex/grid container. Use `ResizeObserver` on the container `div` and pass the measured width.

### General

**Update tests when component API changes.**
When `PuzzleBoard` was refactored to use `onStatusChange` (removing inline status text), 7 tests broke silently at the CI level. Always search for DOM text assertions that reference removed UI before marking a refactor done.

**`NEXT_PUBLIC_*` env vars are baked in at build time.**
Changing them in `.env` does not affect a running dev server without a restart. They cannot be overridden at runtime.

## Running Tests

```bash
# Backend (from backend/)
pytest -x

# Frontend (from frontend/)
yarn test
yarn test --no-coverage   # faster, skips threshold checks
```

## Environments

```
DATABASE_URL=postgresql+asyncpg://nightchess:nightchess_dev@localhost:5432/nightchess
# @localhost for local dev; Docker backend overrides to @db automatically
```
