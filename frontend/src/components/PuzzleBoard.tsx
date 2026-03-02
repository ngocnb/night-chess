'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { Chessboard } from 'react-chessboard'
import { Chess } from 'chess.js'
import type { Square } from 'chess.js'
import type { Puzzle } from '@/lib/api'

interface PuzzleBoardProps {
  puzzle: Puzzle
  onComplete: () => void
  onIncorrect?: () => void
}

type Status = 'playing' | 'correct' | 'incorrect' | 'complete'

/**
 * Converts a move's from/to/promotion fields to UCI notation (e.g. "e2e4", "e7e8q").
 */
function moveToUci(move: { from: Square; to: Square; promotion?: string }): string {
  return `${move.from}${move.to}${move.promotion ?? ''}`
}

/**
 * Parses a UCI string into its from/to/promotion components.
 */
function parseUci(uci: string): { from: string; to: string; promotion?: string } {
  return {
    from: uci.slice(0, 2),
    to: uci.slice(2, 4),
    promotion: uci.length > 4 ? uci.slice(4) : undefined,
  }
}

/**
 * Creates a Chess instance from puzzle FEN and immediately applies the
 * opponent's first move (moves[0]) to reach the puzzle starting position.
 */
function initGame(puzzle: Puzzle): Chess {
  const chess = new Chess(puzzle.fen)
  if (puzzle.moves.length > 0) {
    const { from, to, promotion } = parseUci(puzzle.moves[0])
    chess.move({ from, to, promotion: promotion ?? 'q' })
  }
  return chess
}

/**
 * Determines board orientation from the puzzle FEN.
 *
 * The side-to-move in the raw FEN is the opponent who plays moves[0].
 * - FEN side 'w' → opponent is White → player is Black → orient "black"
 * - FEN side 'b' → opponent is Black → player is White → orient "white"
 */
function getOrientation(puzzle: Puzzle): 'white' | 'black' {
  const sideToMove = puzzle.fen.split(' ')[1]
  return sideToMove === 'w' ? 'black' : 'white'
}

export default function PuzzleBoard({
  puzzle,
  onComplete,
  onIncorrect,
}: PuzzleBoardProps) {
  // Use a ref for the mutable Chess instance so the callback always sees
  // the latest board position without stale closures.
  const gameRef = useRef<Chess>(initGame(puzzle))

  // FEN string drives rendering — updated whenever a move is made.
  const [fen, setFen] = useState<string>(gameRef.current.fen())

  // Index into puzzle.moves for the next expected move.
  // Starts at 1 because moves[0] has already been applied as the opponent's
  // opening move. After the player plays moves[1], the component plays
  // moves[2] (opponent reply), then expects the player to play moves[3], etc.
  const [solutionIndex, setSolutionIndex] = useState(1)

  const [status, setStatus] = useState<Status>('playing')
  const boardOrientation = getOrientation(puzzle)

  // Reset all state whenever the puzzle identity changes.
  useEffect(() => {
    const newGame = initGame(puzzle)
    gameRef.current = newGame
    setFen(newGame.fen())
    setSolutionIndex(1)
    setStatus('playing')
  }, [puzzle.id])

  const onDrop = useCallback(
    (sourceSquare: Square, targetSquare: Square, _piece: string): boolean => {
      if (status === 'complete') return false

      const game = gameRef.current

      // Attempt the player's move — chess.js v1.x throws on illegal input.
      let move: { from: Square; to: Square; promotion?: string }
      try {
        move = game.move({ from: sourceSquare, to: targetSquare, promotion: 'q' })
      } catch {
        return false
      }

      // Compare played UCI to the expected solution move.
      const playedUci = moveToUci({ from: move.from, to: move.to, promotion: move.promotion })
      const expectedUci = puzzle.moves[solutionIndex]

      if (playedUci !== expectedUci) {
        // Wrong move: undo and report.
        game.undo()
        setFen(game.fen())
        setStatus('incorrect')
        onIncorrect?.()
        setTimeout(() => setStatus('playing'), 1000)
        return false
      }

      // Player played the correct move.
      setFen(game.fen())
      const opponentIndex = solutionIndex + 1

      if (opponentIndex >= puzzle.moves.length) {
        // No opponent reply remaining — puzzle is complete.
        setSolutionIndex(opponentIndex)
        setStatus('complete')
        onComplete()
        return true
      }

      // There is an opponent reply to make. Show "Correct!" briefly first.
      setStatus('correct')

      setTimeout(() => {
        const { from, to, promotion } = parseUci(puzzle.moves[opponentIndex])
        game.move({ from, to, promotion: promotion ?? 'q' })
        setFen(game.fen())

        const nextPlayerIndex = opponentIndex + 1
        setSolutionIndex(nextPlayerIndex)

        if (nextPlayerIndex >= puzzle.moves.length) {
          // No more player moves after the opponent reply — puzzle complete.
          setStatus('complete')
          onComplete()
        } else {
          setStatus('playing')
        }
      }, 500)

      return true
    },
    [puzzle, solutionIndex, status, onComplete, onIncorrect],
  )

  return (
    <div>
      <Chessboard
        position={fen}
        onPieceDrop={onDrop}
        boardOrientation={boardOrientation}
        arePiecesDraggable={status !== 'complete'}
      />
      {status === 'correct' && <p style={{ color: 'green' }}>Correct!</p>}
      {status === 'incorrect' && <p style={{ color: 'red' }}>Incorrect — try again</p>}
      {status === 'complete' && <p style={{ color: 'green' }}>Puzzle complete!</p>}
    </div>
  )
}
