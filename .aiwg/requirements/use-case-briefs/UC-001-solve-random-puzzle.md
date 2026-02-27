# UC-001: Solve Random Puzzle (Guest)

## Summary

A guest user visits Night Chess and immediately receives a random chess puzzle to solve — no account, no login, no friction. The system renders the puzzle position, accepts the user's moves, validates them against the correct solution, and returns a clear correct/incorrect result.

## Actor

Guest (unauthenticated user)

## Preconditions

- At least one puzzle exists in the PostgreSQL database (import pipeline has run)
- The Next.js frontend is reachable
- The FastAPI backend `/puzzles/random` endpoint is responding

## Main Flow

1. Guest navigates to the Night Chess homepage (or `/puzzle`)
2. Frontend calls `GET /puzzles/random` on the FastAPI backend (no auth token required)
3. Backend selects a random puzzle from the database and returns: `puzzle_id`, `fen`, `moves`, `rating`, `themes`
4. Frontend renders the chessboard from the FEN string using `react-chessboard`
5. Guest views the position; the side-to-move is visually indicated (White/Black to move label)
6. Guest drags or clicks a piece to make a move
7. `chess.js` validates move legality on the client; illegal moves are silently rejected (piece snaps back)
8. If the move is legal, it is compared against the first expected move in the solution sequence
9. If incorrect: board highlights the move as wrong, shows "Incorrect — try again" feedback, allows retry
10. If correct and the solution has more moves: board auto-plays the opponent's response move, prompts for the next move in the sequence
11. When the guest completes the full solution sequence: display "Puzzle Solved" with the puzzle rating
12. Guest may click "Next Puzzle" to fetch a new random puzzle (returns to step 2)

## Alternative Flows

**AF-1: Incorrect move with no retry limit**
- At step 9, the guest may retry indefinitely; there is no penalty for incorrect attempts in v1

**AF-2: Guest gives up**
- Guest clicks "Show Solution"; the correct move sequence is revealed and animated on the board
- Puzzle is marked as viewed but not solved (progress not recorded for guests)

**AF-3: Backend unavailable**
- At step 2, if the API call fails, the frontend displays a clear error message: "Could not load puzzle — please try again"
- A retry button re-triggers the fetch

## Success Criteria

- [ ] Puzzle loads within 300ms (p95) from page arrival to board render
- [ ] FEN string is rendered correctly as a legal chess position on the board
- [ ] All piece movements obey chess rules; illegal moves are rejected without error messages
- [ ] Correct first move advances the puzzle; incorrect first move shows failure feedback
- [ ] Full multi-move solution sequences complete correctly (opponent auto-replies after each correct move)
- [ ] "Next Puzzle" fetches a different puzzle from the previous one
- [ ] No authentication is required at any point in this flow

## Dependencies

- `GET /puzzles/random` FastAPI endpoint (UC-003 import pipeline must have run)
- `react-chessboard` — board rendering from FEN
- `chess.js` — move legality validation and move application
- PostgreSQL puzzle table with indexed random-access query
- UC-004 (Render Interactive Chessboard) — the board component is a shared dependency

## Priority

Must Have
