# Night Chess — Archived Backlog Items

Completed sprint items moved here to keep the active backlog clean.

---

## Sprint 0 — Foundation (completed 2026-03-01)

| Item | Notes |
|------|-------|
| Project intake + inception docs | `/aiwg/intake/`, vision document, use-case briefs |
| Architecture decisions (ADR-001 to ADR-004) | JWT auth, react-chessboard, TABLESAMPLE, self-hosted deploy |
| FastAPI backend scaffold | `backend/app/` — main.py, config, session, models, migrations |
| Alembic migration — initial schema | `001_initial_schema.py` — puzzles, users, user_progress, refresh_tokens |
| Lichess puzzle import script | `backend/scripts/import_puzzles.py` — zstd decompress, batch upsert, ~3.5M rows |
| Import script test suite | 44 tests — schema validation, batch logic, CLI flags, error paths |
| Next.js 14 scaffold | App Router, TypeScript, `@/` alias, Tailwind removed (plain CSS) |
| Docker Compose stack | db + backend + frontend services; `env_file: ./backend/.env` pattern |
| GitHub Actions CI | Separate workflows for backend (pytest) and frontend (jest) |
| `backend/.env.example` | All 8 Settings fields documented; matches `app/config.py` exactly |
| ADR-003 Accepted | TABLESAMPLE SYSTEM(0.01): 0.167ms vs ORDER BY RANDOM() 2630ms on 3.5M rows |

---

## Sprint 1 — Puzzle API + Chessboard + Guest Flow (completed 2026-03-02)

| Item | Notes |
|------|-------|
| `GET /api/v1/puzzles/random` endpoint | TABLESAMPLE with OFFSET fallback; returns `{id, fen, moves, rating, themes}` |
| Backend puzzle tests | 5 tests — 200/404/503 responses, schema validation, themes null handling |
| Frontend API client | `src/lib/api.ts` — `fetchRandomPuzzle()`, `Puzzle` interface |
| Frontend API tests | 5 tests — success, null themes, error, network failure, env URL |
| PuzzleBoard component | click-to-move, drag-drop, legal move hints, promotion dialog, ResizeObserver boardWidth |
| PuzzleBoard tests | 14 tests — orientation, draggability, correct/incorrect/complete flows, 500ms delay, reset |
| Guest puzzle page | Two-column layout (board + sidebar), loading skeleton, error state |
| Page tests | 11 tests — loading, rating, themes, error, next puzzle button, status label |
| Lichess-inspired dark theme | CSS variables, Lichess brown board colors, status dot, theme tags |
| Sidebar — rating + theme display | Gold rating value, capsule theme tags, color-coded status dot |
| "White/Black to play" status | Derived from puzzle FEN side-to-move; shown in sidebar |
| `jest.setup.ts` — ResizeObserver stub | Added global no-op so PuzzleBoard renders in jsdom |

---

*Last updated: 2026-03-02*
