# Project overview

This project is built for chess puzzles only. The puzzles database is retrieved from lichess: https://database.lichess.org/lichess_db_puzzle.csv.zst. Below is the list of the features:

- First version is web application. Backend is Python FastAPI, Frontend is Nextjs.
- Second version will support Android and iOS, built from Flutter.
- Guest can solve random puzzle.
- Authentication features for saving user progress.

# Feedback + Change request

## 2026-03-03

- I want to save user puzzle result:
  - 1 wrong move = Fail
  - All correct moves = Success
  - → **Planned**: F8 (Sprint 2 addendum) — PuzzleBoard locks on first wrong move, status becomes `'failed'`
- I want to calculate user's rating based on the result of submitted puzzle.
  - Fail: reduce rating
  - Success: increase rating
  - **Formula (Elo, K=32, initial rating 1500)**:
    - `expected = 1 / (1 + 10^((puzzle_rating − user_rating) / 400))`
    - Success: `Δ = +round(32 × (1 − expected))` — bigger reward for beating harder puzzles
    - Fail: `Δ = −round(32 × expected)` — smaller penalty for failing hard puzzles
    - Rating clamped to [400, 3000]
  - → **Planned**: B11 (Sprint 3)
- Query the next puzzles based on user's rating.
  - **Logic**: after TABLESAMPLE, filter `WHERE puzzle.rating BETWEEN (user_rating − 200) AND (user_rating + 200)`. If empty, fall back to unconstrained TABLESAMPLE. Guests always get pure random (unchanged).
  - → **Planned**: B12 (Sprint 3)
- User can click on the Next Puzzle button only after solving it.
  - → **Planned**: F9 (Sprint 2 addendum) — button disabled until `status === 'complete'` or `'failed'`
- Highlight the King when it's checked. See `images/2026-03-03_14-20.png`.
  - → **Planned**: F10 (Sprint 3) — `customSquareStyles` red radial gradient on king square when `game.inCheck()` is true
- When making correct move, add a check mark on it. Wrong move will have a red mark with x. See `images/2026-03-03_14-20.png`.
  - → **Planned**: F11 (Sprint 3) — green ✓ / red ✗ overlay on destination square via `customSquareStyles`
- In previous sprint (sprint 1), there was an error like this.
```
(trapped) error reading bcrypt version
Traceback (most recent call last):
  File "/home/baongoc/workspaces/night-chess/backend/.venv/lib/python3.12/site-packages/passlib/handlers/bcrypt.py", line 620, in _load_backend_mixin
    version = _bcrypt.__about__.__version__
              ^^^^^^^^^^^^^^^^^
AttributeError: module 'bcrypt' has no attribute '__about__'
2026-03-03 14:04:15,081 INFO sqlalchemy.engine.Engine ROLLBACK
2026-03-03 14:04:15 [error    ] unhandled_exception            error='password cannot be longer than 72 bytes, truncate manually if necessary (e.g. my_password[:72])' path=http://localhost:8000/api/v1/auth/register
INFO:     127.0.0.1:43344 - "POST /api/v1/auth/register HTTP/1.1" 500 Internal Server Error
```
when I tested on browser, it returned CORS error and it made me confused. I tried to to fix it but it was the wrong problem. when I looked at the log in backend terminal, it showed the real problem. Propose a way to identify this problem so that Claude Code can check it. Maybe logging the error into a file then read it.
