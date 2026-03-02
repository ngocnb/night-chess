'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { Chessboard } from 'react-chessboard'
import { Chess } from 'chess.js'
import type { Square } from 'chess.js'
import type { Puzzle } from '@/lib/api'

export type PuzzleStatus = 'playing' | 'correct' | 'incorrect' | 'complete'

interface PuzzleBoardProps {
  puzzle: Puzzle
  onComplete: () => void
  onIncorrect?: () => void
  onStatusChange?: (status: PuzzleStatus) => void
}

function moveToUci(move: { from: Square; to: Square; promotion?: string }): string {
  return `${move.from}${move.to}${move.promotion ?? ''}`
}

function parseUci(uci: string): { from: string; to: string; promotion?: string } {
  return {
    from: uci.slice(0, 2),
    to: uci.slice(2, 4),
    promotion: uci.length > 4 ? uci.slice(4) : undefined,
  }
}

function initGame(puzzle: Puzzle): Chess {
  const chess = new Chess(puzzle.fen)
  if (puzzle.moves.length > 0) {
    const { from, to, promotion } = parseUci(puzzle.moves[0])
    chess.move({ from, to, promotion: promotion ?? 'q' })
  }
  return chess
}

function getOrientation(puzzle: Puzzle): 'white' | 'black' {
  const sideToMove = puzzle.fen.split(' ')[1]
  return sideToMove === 'w' ? 'black' : 'white'
}

export default function PuzzleBoard({
  puzzle,
  onComplete,
  onIncorrect,
  onStatusChange,
}: PuzzleBoardProps) {
  const gameRef = useRef<Chess>(initGame(puzzle))
  const [fen, setFen] = useState<string>(gameRef.current.fen())
  const [solutionIndex, setSolutionIndex] = useState(1)
  const [status, setStatus] = useState<PuzzleStatus>('playing')
  const boardOrientation = getOrientation(puzzle)

  const updateStatus = useCallback(
    (next: PuzzleStatus) => {
      setStatus(next)
      onStatusChange?.(next)
    },
    [onStatusChange],
  )

  useEffect(() => {
    const newGame = initGame(puzzle)
    gameRef.current = newGame
    setFen(newGame.fen())
    setSolutionIndex(1)
    updateStatus('playing')
  }, [puzzle.id, updateStatus])

  const onDrop = useCallback(
    (sourceSquare: Square, targetSquare: Square, _piece: string): boolean => {
      if (status === 'complete') return false

      const game = gameRef.current

      let move: { from: Square; to: Square; promotion?: string }
      try {
        move = game.move({ from: sourceSquare, to: targetSquare, promotion: 'q' })
      } catch {
        return false
      }

      const playedUci = moveToUci({ from: move.from, to: move.to, promotion: move.promotion })
      const expectedUci = puzzle.moves[solutionIndex]

      if (playedUci !== expectedUci) {
        game.undo()
        setFen(game.fen())
        updateStatus('incorrect')
        onIncorrect?.()
        setTimeout(() => updateStatus('playing'), 1000)
        return false
      }

      setFen(game.fen())
      const opponentIndex = solutionIndex + 1

      if (opponentIndex >= puzzle.moves.length) {
        setSolutionIndex(opponentIndex)
        updateStatus('complete')
        onComplete()
        return true
      }

      updateStatus('correct')

      setTimeout(() => {
        const { from, to, promotion } = parseUci(puzzle.moves[opponentIndex])
        game.move({ from, to, promotion: promotion ?? 'q' })
        setFen(game.fen())

        const nextPlayerIndex = opponentIndex + 1
        setSolutionIndex(nextPlayerIndex)

        if (nextPlayerIndex >= puzzle.moves.length) {
          updateStatus('complete')
          onComplete()
        } else {
          updateStatus('playing')
        }
      }, 500)

      return true
    },
    [puzzle, solutionIndex, status, onComplete, onIncorrect, updateStatus],
  )

  return (
    <div className="board-container">
      <Chessboard
        position={fen}
        onPieceDrop={onDrop}
        boardOrientation={boardOrientation}
        arePiecesDraggable={status !== 'complete'}
        customDarkSquareStyle={{ backgroundColor: '#b58863' }}
        customLightSquareStyle={{ backgroundColor: '#f0d9b5' }}
      />
    </div>
  )
}
