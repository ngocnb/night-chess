/**
 * Tests for PuzzleBoard component
 *
 * Tests cover:
 * - Renders the chessboard without crashing
 * - Board orientation: FEN side 'w' → player is Black → orientation "black"
 * - Board orientation: FEN side 'b' → player is White → orientation "white"
 * - No status message shown initially (status = 'playing')
 * - onDrop: correct move shows 'Correct!' feedback
 * - onDrop: incorrect move shows 'Incorrect' feedback and calls onIncorrect
 * - onDrop: 'Incorrect' status clears after 1 second
 * - onDrop: illegal move returns false (piece snaps back)
 * - Puzzle complete when last move played — calls onComplete, shows 'Puzzle complete!'
 * - Puzzle complete triggered by opponent's last reply (even-length player sequences)
 * - Board is non-draggable when status is 'complete'
 * - Opponent reply fires after 500ms delay
 * - State resets when puzzle.id changes
 */

import React from 'react'
import { render, screen, act } from '@testing-library/react'
import type { Puzzle } from '@/lib/api'

// Capture the onPieceDrop prop from each render so tests can simulate drops.
let capturedOnPieceDrop: ((src: string, tgt: string, piece: string) => boolean) | null = null

// Mock react-chessboard to avoid canvas/DnD complexity in tests.
jest.mock('react-chessboard', () => ({
  Chessboard: (props: {
    onPieceDrop: (src: string, tgt: string, piece: string) => boolean
    boardOrientation: string
    arePiecesDraggable: boolean
    position: string
  }) => {
    capturedOnPieceDrop = props.onPieceDrop
    return (
      <div
        data-testid="chessboard"
        data-orientation={props.boardOrientation}
        data-draggable={String(props.arePiecesDraggable)}
        data-position={props.position}
      />
    )
  },
}))

// Puzzle: White is opponent (FEN side 'w') → player is Black.
// moves[0] = f3g5 (opponent auto-play), moves[1] = d8e7 (player), moves[2] = g5f7 (opponent reply)
// After moves[2] plays, nextPlayerIndex=3=moves.length → onComplete fires.
const WHITE_OPPONENT_PUZZLE: Puzzle = {
  id: 'puzzle-w',
  fen: 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4',
  moves: ['f3g5', 'd8e7', 'g5f7'],
  rating: 1487,
  themes: ['fork'],
}

// Puzzle: Black is opponent (FEN side 'b') → player is White.
// FEN: after 1.e4 — Black to move (opponent is Black)
// opponent plays e7e5, then player (White) must play d2d4
const BLACK_OPPONENT_PUZZLE: Puzzle = {
  id: 'puzzle-b',
  fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1',
  moves: ['e7e5', 'd2d4'], // opponent: e7e5, player: d2d4
  rating: 1200,
  themes: null,
}

// A minimal 2-move puzzle: moves[0]=opponent, moves[1]=player → completes immediately.
const TWO_MOVE_PUZZLE: Puzzle = {
  id: 'two-move',
  // After e4 — Black to move is opponent playing e5
  fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1',
  moves: ['e7e5', 'd2d4'], // opponent: e7e5, player: d2d4
  rating: 800,
  themes: null,
}

import PuzzleBoard from '@/components/PuzzleBoard'

describe('PuzzleBoard', () => {
  beforeEach(() => {
    capturedOnPieceDrop = null
    jest.useFakeTimers()
  })

  afterEach(() => {
    act(() => {
      jest.runAllTimers()
    })
    jest.useRealTimers()
  })

  it('renders without crashing', () => {
    render(<PuzzleBoard puzzle={WHITE_OPPONENT_PUZZLE} onComplete={jest.fn()} />)
    expect(screen.getByTestId('chessboard')).toBeInTheDocument()
  })

  it('sets boardOrientation to "black" when FEN side-to-move is "w"', () => {
    render(<PuzzleBoard puzzle={WHITE_OPPONENT_PUZZLE} onComplete={jest.fn()} />)
    expect(screen.getByTestId('chessboard').dataset.orientation).toBe('black')
  })

  it('sets boardOrientation to "white" when FEN side-to-move is "b"', () => {
    render(<PuzzleBoard puzzle={BLACK_OPPONENT_PUZZLE} onComplete={jest.fn()} />)
    expect(screen.getByTestId('chessboard').dataset.orientation).toBe('white')
  })

  it('does not show any status message initially', () => {
    render(<PuzzleBoard puzzle={WHITE_OPPONENT_PUZZLE} onComplete={jest.fn()} />)
    expect(screen.queryByText('Correct!')).not.toBeInTheDocument()
    expect(screen.queryByText(/Incorrect/)).not.toBeInTheDocument()
    expect(screen.queryByText('Puzzle complete!')).not.toBeInTheDocument()
  })

  it('board is draggable initially', () => {
    render(<PuzzleBoard puzzle={WHITE_OPPONENT_PUZZLE} onComplete={jest.fn()} />)
    expect(screen.getByTestId('chessboard').dataset.draggable).toBe('true')
  })

  it('returns false for a chess-illegal move (piece snaps back)', () => {
    render(<PuzzleBoard puzzle={WHITE_OPPONENT_PUZZLE} onComplete={jest.fn()} />)
    expect(capturedOnPieceDrop).not.toBeNull()

    let result!: boolean
    act(() => {
      // a8→a1 is not a legal move in this position
      result = capturedOnPieceDrop!('a8', 'a1', 'bR')
    })

    expect(result).toBe(false)
  })

  it('shows "Incorrect — try again" and calls onIncorrect on a wrong (but legal) move', () => {
    const onIncorrect = jest.fn()
    render(
      <PuzzleBoard
        puzzle={WHITE_OPPONENT_PUZZLE}
        onComplete={jest.fn()}
        onIncorrect={onIncorrect}
      />,
    )

    let result!: boolean
    act(() => {
      // f8e7 is a legal move but NOT the expected d8e7
      result = capturedOnPieceDrop!('f8', 'e7', 'bB')
    })

    expect(result).toBe(false)
    expect(screen.getByText('Incorrect — try again')).toBeInTheDocument()
    expect(onIncorrect).toHaveBeenCalledTimes(1)
  })

  it('clears "Incorrect" status after 1 second', () => {
    render(<PuzzleBoard puzzle={WHITE_OPPONENT_PUZZLE} onComplete={jest.fn()} />)

    act(() => {
      capturedOnPieceDrop!('f8', 'e7', 'bB')
    })
    expect(screen.getByText('Incorrect — try again')).toBeInTheDocument()

    act(() => {
      jest.advanceTimersByTime(1000)
    })
    expect(screen.queryByText('Incorrect — try again')).not.toBeInTheDocument()
  })

  it('onIncorrect is optional — does not throw when not provided', () => {
    render(<PuzzleBoard puzzle={WHITE_OPPONENT_PUZZLE} onComplete={jest.fn()} />)

    expect(() => {
      act(() => {
        capturedOnPieceDrop!('f8', 'e7', 'bB')
      })
    }).not.toThrow()
  })

  it('shows "Correct!" on the correct player move', () => {
    render(<PuzzleBoard puzzle={WHITE_OPPONENT_PUZZLE} onComplete={jest.fn()} />)

    // After opponent plays f3g5, player must play d8e7
    let result!: boolean
    act(() => {
      result = capturedOnPieceDrop!('d8', 'e7', 'bQ')
    })

    expect(result).toBe(true)
    expect(screen.getByText('Correct!')).toBeInTheDocument()
  })

  it('calls onComplete and shows "Puzzle complete!" on a 2-move puzzle (no opponent reply)', () => {
    const onComplete = jest.fn()
    render(<PuzzleBoard puzzle={TWO_MOVE_PUZZLE} onComplete={onComplete} />)

    // opponent already played e7e5; player must play d2d4
    act(() => {
      capturedOnPieceDrop!('d2', 'd4', 'wP')
    })

    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(screen.getByText('Puzzle complete!')).toBeInTheDocument()
  })

  it('board becomes non-draggable after puzzle completion (no-reply puzzle)', () => {
    render(<PuzzleBoard puzzle={TWO_MOVE_PUZZLE} onComplete={jest.fn()} />)

    act(() => {
      capturedOnPieceDrop!('d2', 'd4', 'wP')
    })

    expect(screen.getByTestId('chessboard').dataset.draggable).toBe('false')
  })

  it('calls onComplete after opponent reply when last move was opponent-replied', () => {
    const onComplete = jest.fn()
    render(<PuzzleBoard puzzle={WHITE_OPPONENT_PUZZLE} onComplete={onComplete} />)

    // Player plays correct move d8e7 (solutionIndex=1)
    act(() => {
      capturedOnPieceDrop!('d8', 'e7', 'bQ')
    })
    // onComplete should NOT be called yet (opponent still needs to reply)
    expect(onComplete).not.toHaveBeenCalled()

    // After 500ms, opponent plays g5f7 and puzzle completes
    act(() => {
      jest.advanceTimersByTime(500)
    })
    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(screen.getByText('Puzzle complete!')).toBeInTheDocument()
  })

  it('opponent reply fires after 500ms and status transitions to complete (or playing)', () => {
    render(<PuzzleBoard puzzle={WHITE_OPPONENT_PUZZLE} onComplete={jest.fn()} />)

    act(() => {
      capturedOnPieceDrop!('d8', 'e7', 'bQ')
    })
    expect(screen.getByText('Correct!')).toBeInTheDocument()

    act(() => {
      jest.advanceTimersByTime(499)
    })
    // Still showing Correct before timeout fires
    expect(screen.getByText('Correct!')).toBeInTheDocument()

    act(() => {
      jest.advanceTimersByTime(1)
    })
    // After timeout, "Correct!" is gone (status is now 'complete')
    expect(screen.queryByText('Correct!')).not.toBeInTheDocument()
  })

  it('resets state when puzzle.id changes', () => {
    const onComplete = jest.fn()
    const { rerender } = render(
      <PuzzleBoard puzzle={TWO_MOVE_PUZZLE} onComplete={onComplete} />,
    )

    // Complete the first puzzle
    act(() => {
      capturedOnPieceDrop!('d2', 'd4', 'wP')
    })
    expect(screen.getByText('Puzzle complete!')).toBeInTheDocument()

    // Switch to a new puzzle
    const newPuzzle: Puzzle = {
      id: 'new-puzzle',
      fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1',
      moves: ['e7e5', 'f2f4'],
      rating: 900,
      themes: null,
    }
    rerender(<PuzzleBoard puzzle={newPuzzle} onComplete={onComplete} />)

    // Status should reset to playing
    expect(screen.queryByText('Puzzle complete!')).not.toBeInTheDocument()
    expect(screen.queryByText('Correct!')).not.toBeInTheDocument()
    expect(screen.getByTestId('chessboard').dataset.draggable).toBe('true')
  })
})
