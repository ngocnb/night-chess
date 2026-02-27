# UC-004: Render Interactive Chessboard

## Summary

The chessboard component is the core UI element of Night Chess. It accepts a FEN string, renders a legal chess position, accepts user move input via drag-and-drop or click-to-move, validates move legality using `chess.js`, and checks each move against the puzzle solution sequence. It handles all standard and special chess moves correctly and communicates results (correct / incorrect / puzzle complete) to the parent page.

## Actor

Any user (guest or registered)

## Preconditions

- A puzzle object has been received from the API: `{puzzle_id, fen, moves, rating}`
- `react-chessboard` and `chess.js` are installed and loaded
- The `moves` field contains a valid UCI move sequence (e.g., `"e2e4 e7e5 g1f3"`)
- The browser supports modern JavaScript (ES2020+)

## Main Flow

1. Parent component passes `fen` and `moves` as props to the `<Chessboard>` component
2. Component initialises a `chess.js` instance with the given FEN: `new Chess(fen)`
3. `react-chessboard` renders the board from the current `chess.js` position; board orientation is set to match the side to move (White moves up, Black moves up from bottom)
4. The solution move list is parsed from UCI format into an ordered array: `["e2e4", "e7e5", "g1f3", ...]`; the expected index starts at 0
5. User selects a piece (click or drag); legal destination squares are highlighted
6. User completes a move (drops piece or clicks destination square)
7. `chess.js` validates the move: if illegal, the piece snaps back silently (no error shown)
8. If the move is legal, compare it to `solutionMoves[currentIndex]` in UCI notation
9. **Incorrect move**: board reverts the move visually, fires `onMoveIncorrect` callback, displays a brief shake animation and "Incorrect" indicator; user may retry
10. **Correct move**: move is applied to the `chess.js` instance and rendered; `currentIndex` advances
11. If more solution moves remain, the board automatically plays the opponent's next move after a 500ms delay (using `chess.js` + re-render); `currentIndex` advances again; return to step 5
12. When `currentIndex` reaches the end of the solution array, fire `onPuzzleComplete` callback; display "Puzzle Solved" overlay with the puzzle rating
13. Special move handling at step 7/8:
    - **Castling**: recognised automatically by `chess.js` via king move to castling square (e.g., `e1g1`)
    - **En passant**: recognised automatically by `chess.js` when a pawn captures to the en passant square
    - **Promotion**: when a pawn reaches the back rank, display a promotion piece picker (Q/R/B/N); selected piece is appended to the UCI string (e.g., `e7e8q`); validated against solution
    - **Check/Checkmate**: `chess.js` detects check and checkmate automatically; board visually highlights the king in check; checkmate ends the puzzle as solved or failed depending on context

## Alternative Flows

**AF-1: Show Solution**
- User triggers "Show Solution" action on the parent page
- The component animates through the remaining solution moves at 800ms intervals using `chess.js` + re-render
- Board enters a read-only state; no further user input is accepted

**AF-2: Promotion piece selection cancelled**
- If the user dismisses the promotion picker without selecting, the pawn move is cancelled and the pawn returns to its original square

**AF-3: FEN for invalid position passed**
- If `new Chess(fen)` throws (invalid FEN), the component renders an error state: "Invalid puzzle position"
- The error is reported via an `onError` callback for parent-level handling

**AF-4: Board orientation override**
- A `boardOrientation` prop can force "white" or "black" view regardless of side-to-move (for future puzzle review features)

## Success Criteria

- [ ] Any legal FEN string renders a visually correct board position with pieces on the right squares
- [ ] All 12 piece types (6 per side) render correctly at all board coordinates
- [ ] Illegal moves (moving opponent's piece, moving into check, etc.) are silently rejected; no error messages displayed
- [ ] Correct first move in a solution sequence is accepted and triggers opponent auto-reply within 500ms
- [ ] Incorrect first move is rejected with visual feedback; board remains in puzzle start position
- [ ] Castling (both sides, both colours) is correctly recognised and accepted when it is the solution move
- [ ] En passant captures are correctly recognised as legal or illegal per the FEN state
- [ ] Pawn promotion to all four piece types is supported; the correct UCI suffix is matched against the solution
- [ ] Check is visually indicated on the board; checkmate is detected and reported correctly
- [ ] Multi-move solutions complete the full sequence (user move → opponent reply → user move → ...) without state drift
- [ ] `onPuzzleComplete` fires exactly once when the last solution move is played

## Dependencies

- `chess.js` (npm) — move legality validation, FEN parsing, game state management, special move detection
- `react-chessboard` (npm) — board rendering, drag-and-drop, square highlighting, orientation
- Parent component props: `fen: string`, `moves: string`, `onMoveCorrect`, `onMoveIncorrect`, `onPuzzleComplete`, `onError`
- UC-001 (Solve Random Puzzle) — primary consumer of this component
- FastAPI puzzle data (UC-003) — provides the FEN and moves this component consumes

## Priority

Must Have
