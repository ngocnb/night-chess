# ADR-002: react-chessboard + chess.js for Puzzle Rendering and Validation

**Status**: Accepted
**Date**: 2026-02-27
**Deciders**: Developer (solo)

---

## Context

Night Chess needs an interactive chessboard that:

1. Renders a chess position from a FEN string
2. Accepts user input via drag-and-drop and/or click-to-move
3. Validates that every attempted move is legal (including castling, en passant, pawn promotion)
4. Checks each move against the puzzle's solution sequence (a list of UCI moves from Lichess)
5. Detects puzzle completion (all solution moves played correctly) and failure (wrong move)
6. Integrates cleanly with a React/Next.js frontend

Chess correctness is the single most critical quality dimension for this product (see R-001 in the risk register). A chess player will immediately notice and reject an application that allows illegal moves or mishandles special positions. This means the chess logic library must be battle-tested and comprehensive -- not a recent or experimental project.

## Decision

Use **react-chessboard** for board rendering and **chess.js** for all game logic and move validation.

**react-chessboard**:
- React component providing an SVG chessboard with drag-and-drop piece interaction
- Accepts a `position` prop (FEN string) and fires callbacks on piece drop
- Handles board orientation (white/black perspective), animation, and piece styling
- npm: `react-chessboard` (~100K weekly downloads)

**chess.js**:
- JavaScript chess library implementing the complete rules of chess
- FEN parsing, move generation, move validation, check/checkmate/stalemate detection
- Handles all special moves: castling (kingside + queenside), en passant, pawn promotion (all four piece types), fifty-move rule, threefold repetition
- npm: `chess.js` (~1M+ weekly downloads, actively maintained)

**Integration pattern**:

```typescript
import { Chess } from 'chess.js';
import { Chessboard } from 'react-chessboard';

function PuzzleBoard({ fen, solutionMoves }: PuzzleBoardProps) {
  const [game] = useState(new Chess(fen));
  const [moveIndex, setMoveIndex] = useState(0);

  function onPieceDrop(sourceSquare: string, targetSquare: string) {
    // chess.js validates the move is legal
    const move = game.move({
      from: sourceSquare,
      to: targetSquare,
      promotion: 'q',  // default; show promotion dialog for pawn moves
    });

    if (move === null) return false;  // Illegal move -- rejected

    // Check against puzzle solution
    const expectedMove = solutionMoves[moveIndex];
    if (move.lan === expectedMove) {
      // Correct move -- advance to next in sequence
      setMoveIndex(prev => prev + 1);
      // Play opponent's response (next move in solution)
      // ...
    } else {
      // Wrong move -- puzzle failed
      game.undo();
    }

    return true;
  }

  return (
    <Chessboard
      position={game.fen()}
      onPieceDrop={onPieceDrop}
      boardWidth={560}
    />
  );
}
```

**Critical rule**: All move validation flows through chess.js. Zero custom chess logic anywhere in the codebase. This is a non-negotiable architectural constraint documented in the risk register (R-001).

## Alternatives Considered

### Alternative 1: chessground (Lichess's Board Library)

**What it is**: The chessboard rendering library used by Lichess itself. Open source, highly optimized, supports all chess features. Originally built for Mithril.js, with community wrappers for other frameworks.

**Pros**:
- Used in production by Lichess serving millions of users -- proven at extreme scale
- Extremely performant rendering (canvas-based)
- Highly customizable (Lichess themes, sounds, animations)
- Includes its own move validation logic

**Cons**:
- Not built for React -- community React wrappers exist but are less mature and less maintained than react-chessboard
- Mithril.js rendering model creates friction with React's virtual DOM -- integration requires careful lifecycle management
- Steeper learning curve; documentation is Lichess-centric, not general-purpose
- The React wrapper (`react-chessground` or `chessground`) has significantly fewer npm downloads (~5K/week vs react-chessboard's ~100K/week) and less community support

**Why rejected**: The React integration friction is not justified for a solo developer on a 4-6 week timeline. react-chessboard provides a native React experience with lower integration risk. If chessground's performance or customization becomes necessary post-MVP, migration is feasible because the chess logic layer (chess.js) is decoupled from the rendering layer.

### Alternative 2: cm-chessboard

**What it is**: A lightweight, dependency-free SVG chessboard component. Framework-agnostic.

**Pros**:
- Very small bundle size
- Clean API, no framework dependency
- Good for simple static board display

**Cons**:
- Smaller community (~2K weekly npm downloads)
- Less mature drag-and-drop interaction
- No built-in React bindings -- requires manual DOM integration
- Fewer features for interactive puzzle solving (promotion dialogs, move animation)

**Why rejected**: Lower community adoption means fewer answered questions and less battle-testing. The lack of React bindings adds integration work that react-chessboard eliminates.

### Alternative 3: Custom SVG Chessboard

**What it is**: Build the chessboard rendering from scratch using SVG elements in React.

**Pros**:
- Full control over rendering, styling, and interaction
- No third-party dependency for the board component
- Minimal bundle size (only what is needed)

**Cons**:
- Significant development effort: piece rendering, drag-and-drop, touch support, animation, promotion dialogs, board orientation, responsive sizing
- Every browser compatibility issue must be solved manually
- Time-to-feature is measured in weeks, not hours
- Completely unjustifiable for a solo developer on a 4-6 week timeline

**Why rejected**: Building a chessboard renderer is a project unto itself. This is the definition of scope creep for a puzzle platform. The value is in the puzzle experience, not in custom board rendering.

## Consequences

### Positive

- **Chess correctness confidence**: chess.js is the most widely used JavaScript chess library. Its move validation has been exercised against millions of games. The probability of encountering a move validation bug is very low.
- **Fast integration**: react-chessboard + chess.js is an established pairing with documented integration patterns and community examples. Time from zero to working interactive board is measured in hours.
- **Clean separation**: Board rendering (react-chessboard) is decoupled from game logic (chess.js). Either can be replaced independently if needed post-MVP.
- **Special move handling**: chess.js handles all special moves (castling, en passant, promotion, insufficient material, fifty-move rule) without any custom code.
- **Active maintenance**: Both libraries are actively maintained with regular releases.

### Negative

- **Bundle size**: react-chessboard adds ~150 KB (gzipped) to the frontend bundle. Acceptable for a puzzle app where the chessboard is the primary UI element, but worth monitoring.
- **Limited board customization**: react-chessboard's styling options are less extensive than chessground's. Custom piece sets, board themes, and animations are more constrained. Acceptable for MVP; revisit if design requirements expand.
- **Promotion dialog**: react-chessboard's built-in promotion dialog may not match the desired UX. May need a custom React component for the promotion piece picker. This is a bounded scope addition.

## Critical Requirement (Non-Negotiable)

**NEVER implement custom chess logic.** All move legality checks, turn tracking, check/checkmate/stalemate detection, en passant validation, castling rights parsing from FEN, and pawn promotion handling MUST route through chess.js.

If a chess correctness bug is discovered:
1. First check if the FEN or move data from Lichess is malformed (data pipeline issue)
2. Then check if the chess.js integration is wiring the data incorrectly (integration issue)
3. Only if neither explains the bug, file an issue on chess.js -- do not write a workaround

This constraint exists because R-001 (Chess Move Validation Correctness) is rated CRITICAL in the risk register. Hand-rolled chess logic is the fastest path to product failure.

---

## Version History

| Version | Date       | Change                     |
|---------|------------|----------------------------|
| 1.0     | 2026-02-27 | Initial decision -- accepted |
