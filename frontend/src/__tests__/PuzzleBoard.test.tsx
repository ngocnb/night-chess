/**
 * Tests for PuzzleBoard component
 *
 * Tests cover:
 * - Renders the chessboard without crashing
 * - Board orientation: FEN side 'w' → player is Black → orientation "black"
 * - Board orientation: FEN side 'b' → player is White → orientation "white"
 * - onStatusChange is NOT called initially (status starts as 'playing')
 * - onDrop: correct move calls onStatusChange('correct')
 * - onDrop: incorrect move calls onStatusChange('failed') and onIncorrect (board locks)
 * - onDrop: illegal move returns false (piece snaps back)
 * - Puzzle complete when last move played — calls onComplete, onStatusChange('complete')
 * - Puzzle complete triggered by opponent's last reply (even-length player sequences)
 * - Board is non-draggable when status is 'complete' or 'failed'
 * - Opponent reply fires after 500ms delay
 * - State resets when puzzle.id changes
 */

import React from 'react'
import { render, screen, act } from '@testing-library/react'
import type { Puzzle } from '@/lib/api'
import type { PuzzleStatus } from '@/components/PuzzleBoard'

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

  it('calls onStatusChange("playing") on initial render via reset effect', () => {
    const onStatusChange = jest.fn()
    render(
      <PuzzleBoard
        puzzle={WHITE_OPPONENT_PUZZLE}
        onComplete={jest.fn()}
        onStatusChange={onStatusChange}
      />,
    )
    // The puzzle.id reset effect fires on mount and calls onStatusChange('playing')
    expect(onStatusChange).toHaveBeenCalledWith('playing')
    expect(onStatusChange).toHaveBeenCalledTimes(1)
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

  it('calls onStatusChange("failed") and onIncorrect on a wrong (but legal) move', () => {
    const onIncorrect = jest.fn()
    const onStatusChange = jest.fn()
    render(
      <PuzzleBoard
        puzzle={WHITE_OPPONENT_PUZZLE}
        onComplete={jest.fn()}
        onIncorrect={onIncorrect}
        onStatusChange={onStatusChange}
      />,
    )

    let result!: boolean
    act(() => {
      // f8e7 is a legal move but NOT the expected d8e7
      result = capturedOnPieceDrop!('f8', 'e7', 'bB')
    })

    expect(result).toBe(false)
    expect(onStatusChange).toHaveBeenCalledWith('failed')
    expect(onIncorrect).toHaveBeenCalledTimes(1)
  })

  it('board becomes non-draggable after incorrect move (status=failed)', () => {
    render(<PuzzleBoard puzzle={WHITE_OPPONENT_PUZZLE} onComplete={jest.fn()} />)

    act(() => {
      capturedOnPieceDrop!('f8', 'e7', 'bB')
    })

    expect(screen.getByTestId('chessboard').dataset.draggable).toBe('false')
  })

  it('onIncorrect is optional — does not throw when not provided', () => {
    render(<PuzzleBoard puzzle={WHITE_OPPONENT_PUZZLE} onComplete={jest.fn()} />)

    expect(() => {
      act(() => {
        capturedOnPieceDrop!('f8', 'e7', 'bB')
      })
    }).not.toThrow()
  })

  it('calls onStatusChange("correct") on the correct player move', () => {
    const onStatusChange = jest.fn()
    render(
      <PuzzleBoard
        puzzle={WHITE_OPPONENT_PUZZLE}
        onComplete={jest.fn()}
        onStatusChange={onStatusChange}
      />,
    )

    // After opponent plays f3g5, player must play d8e7
    let result!: boolean
    act(() => {
      result = capturedOnPieceDrop!('d8', 'e7', 'bQ')
    })

    expect(result).toBe(true)
    expect(onStatusChange).toHaveBeenCalledWith('correct')
  })

  it('calls onComplete and onStatusChange("complete") on a 2-move puzzle (no opponent reply)', () => {
    const onComplete = jest.fn()
    const onStatusChange = jest.fn()
    render(
      <PuzzleBoard
        puzzle={TWO_MOVE_PUZZLE}
        onComplete={onComplete}
        onStatusChange={onStatusChange}
      />,
    )

    // opponent already played e7e5; player must play d2d4
    act(() => {
      capturedOnPieceDrop!('d2', 'd4', 'wP')
    })

    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(onStatusChange).toHaveBeenCalledWith('complete')
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
    const onStatusChange = jest.fn()
    render(
      <PuzzleBoard
        puzzle={WHITE_OPPONENT_PUZZLE}
        onComplete={onComplete}
        onStatusChange={onStatusChange}
      />,
    )

    // Player plays correct move d8e7 (solutionIndex=1)
    act(() => {
      capturedOnPieceDrop!('d8', 'e7', 'bQ')
    })
    // onComplete should NOT be called yet (opponent still needs to reply)
    expect(onComplete).not.toHaveBeenCalled()
    expect(onStatusChange).toHaveBeenCalledWith('correct')

    // After 500ms, opponent plays g5f7 and puzzle completes
    onStatusChange.mockClear()
    act(() => {
      jest.advanceTimersByTime(500)
    })
    expect(onComplete).toHaveBeenCalledTimes(1)
    expect(onStatusChange).toHaveBeenCalledWith('complete')
  })

  it('opponent reply fires after 500ms and status transitions to complete', () => {
    const onStatusChange = jest.fn()
    render(
      <PuzzleBoard
        puzzle={WHITE_OPPONENT_PUZZLE}
        onComplete={jest.fn()}
        onStatusChange={onStatusChange}
      />,
    )

    act(() => {
      capturedOnPieceDrop!('d8', 'e7', 'bQ')
    })
    expect(onStatusChange).toHaveBeenCalledWith('correct')

    onStatusChange.mockClear()
    act(() => {
      jest.advanceTimersByTime(499)
    })
    // Still in 'correct' — opponent hasn't replied yet
    expect(onStatusChange).not.toHaveBeenCalled()

    act(() => {
      jest.advanceTimersByTime(1)
    })
    // After timeout fires, status becomes 'complete'
    expect(onStatusChange).toHaveBeenCalledWith('complete')
  })

  it('resets state when puzzle.id changes', () => {
    const onComplete = jest.fn()
    const onStatusChange = jest.fn()
    const { rerender } = render(
      <PuzzleBoard
        puzzle={TWO_MOVE_PUZZLE}
        onComplete={onComplete}
        onStatusChange={onStatusChange}
      />,
    )

    // Complete the first puzzle
    act(() => {
      capturedOnPieceDrop!('d2', 'd4', 'wP')
    })
    expect(onStatusChange).toHaveBeenCalledWith('complete')
    expect(screen.getByTestId('chessboard').dataset.draggable).toBe('false')

    // Switch to a new puzzle
    const newPuzzle: Puzzle = {
      id: 'new-puzzle',
      fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1',
      moves: ['e7e5', 'f2f4'],
      rating: 900,
      themes: null,
    }
    onStatusChange.mockClear()
    rerender(
      <PuzzleBoard puzzle={newPuzzle} onComplete={onComplete} onStatusChange={onStatusChange} />,
    )

    // Board should be draggable again; reset effect fires onStatusChange('playing')
    expect(screen.getByTestId('chessboard').dataset.draggable).toBe('true')
    expect(onStatusChange).toHaveBeenCalledWith('playing')
  })
})
