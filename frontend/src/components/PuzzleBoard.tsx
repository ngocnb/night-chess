'use client'

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
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

// ── Helpers ──────────────────────────────────────────────────────────────────

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
  return puzzle.fen.split(' ')[1] === 'w' ? 'black' : 'white'
}

function isPawnPromotion(game: Chess, from: Square, to: Square): boolean {
  const piece = game.get(from)
  if (!piece || piece.type !== 'p') return false
  return (piece.color === 'w' && to[1] === '8') || (piece.color === 'b' && to[1] === '1')
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function PuzzleBoard({
  puzzle,
  onComplete,
  onIncorrect,
  onStatusChange,
}: PuzzleBoardProps) {
  // Measure container so the board always fills its column
  const containerRef = useRef<HTMLDivElement>(null)
  const [boardWidth, setBoardWidth] = useState(480)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width
      if (w) setBoardWidth(w)
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const gameRef = useRef<Chess>(initGame(puzzle))
  const [fen, setFen] = useState<string>(gameRef.current.fen())
  const [solutionIndex, setSolutionIndex] = useState(1)
  const [status, setStatus] = useState<PuzzleStatus>('playing')

  // Click-to-move state
  const [selectedSquare, setSelectedSquare] = useState<Square | null>(null)
  const [legalTargets, setLegalTargets] = useState<Set<Square>>(new Set())

  // Promotion state
  const [showPromotion, setShowPromotion] = useState(false)
  const [promotionToSquare, setPromotionToSquare] = useState<Square | null>(null)
  const [pendingFrom, setPendingFrom] = useState<Square | null>(null)

  const boardOrientation = getOrientation(puzzle)
  const playerColor = boardOrientation === 'white' ? 'w' : 'b'

  const updateStatus = useCallback(
    (next: PuzzleStatus) => {
      setStatus(next)
      onStatusChange?.(next)
    },
    [onStatusChange],
  )

  const clearSelection = useCallback(() => {
    setSelectedSquare(null)
    setLegalTargets(new Set())
  }, [])

  // Reset when puzzle changes
  useEffect(() => {
    const newGame = initGame(puzzle)
    gameRef.current = newGame
    setFen(newGame.fen())
    setSolutionIndex(1)
    updateStatus('playing')
    clearSelection()
    setShowPromotion(false)
    setPromotionToSquare(null)
    setPendingFrom(null)
  }, [puzzle.id, updateStatus, clearSelection])

  // ── Core move execution (shared by drag-drop and click-to-move) ───────────

  const executeMove = useCallback(
    (from: Square, to: Square, promotion?: string) => {
      const game = gameRef.current

      let move: { from: Square; to: Square; promotion?: string }
      try {
        move = game.move({ from, to, promotion: promotion ?? 'q' })
      } catch {
        clearSelection()
        return false
      }

      const playedUci = moveToUci({ from: move.from, to: move.to, promotion: move.promotion })
      const expectedUci = puzzle.moves[solutionIndex]

      if (playedUci !== expectedUci) {
        game.undo()
        setFen(game.fen())
        updateStatus('incorrect')
        onIncorrect?.()
        clearSelection()
        setTimeout(() => updateStatus('playing'), 1000)
        return false
      }

      // Correct move
      setFen(game.fen())
      clearSelection()
      const opponentIndex = solutionIndex + 1

      if (opponentIndex >= puzzle.moves.length) {
        setSolutionIndex(opponentIndex)
        updateStatus('complete')
        onComplete()
        return true
      }

      updateStatus('correct')

      setTimeout(() => {
        const opp = parseUci(puzzle.moves[opponentIndex])
        game.move({ from: opp.from, to: opp.to, promotion: opp.promotion ?? 'q' })
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
    [puzzle, solutionIndex, onComplete, onIncorrect, updateStatus, clearSelection],
  )

  // ── Drag-and-drop ─────────────────────────────────────────────────────────

  const onDrop = useCallback(
    (sourceSquare: Square, targetSquare: Square, _piece: string): boolean => {
      if (status === 'complete') return false
      clearSelection()

      if (isPawnPromotion(gameRef.current, sourceSquare, targetSquare)) {
        setPendingFrom(sourceSquare)
        setPromotionToSquare(targetSquare)
        setShowPromotion(true)
        return false // board stays, promotion dialog opens
      }

      return executeMove(sourceSquare, targetSquare)
    },
    [status, executeMove, clearSelection],
  )

  // ── Click-to-move ──────────────────────────────────────────────────────────

  const onSquareClick = useCallback(
    (square: Square) => {
      if (status === 'complete') return
      if (showPromotion) return

      const game = gameRef.current
      const piece = game.get(square)

      // If a square is already selected, attempt to move there
      if (selectedSquare) {
        // Clicking another own piece — reselect instead
        if (piece && piece.color === playerColor) {
          const moves = game.moves({ square, verbose: true })
          setSelectedSquare(square)
          setLegalTargets(new Set(moves.map((m) => m.to as Square)))
          return
        }

        // Attempt promotion via click
        if (isPawnPromotion(game, selectedSquare, square)) {
          clearSelection()
          setPendingFrom(selectedSquare)
          setPromotionToSquare(square)
          setShowPromotion(true)
          return
        }

        // Attempt the move
        executeMove(selectedSquare, square)
        return
      }

      // No square selected — select if it's the player's piece
      if (piece && piece.color === playerColor) {
        const moves = game.moves({ square, verbose: true })
        setSelectedSquare(square)
        setLegalTargets(new Set(moves.map((m) => m.to as Square)))
      }
    },
    [status, selectedSquare, playerColor, executeMove, clearSelection, showPromotion],
  )

  // ── Promotion pick ────────────────────────────────────────────────────────

  const onPromotionPieceSelect = useCallback(
    (piece?: string): boolean => {
      setShowPromotion(false)
      setPromotionToSquare(null)
      if (!piece || !pendingFrom || !promotionToSquare) {
        setPendingFrom(null)
        return false
      }
      // piece comes in as e.g. "wQ" — extract the lowercase letter
      const promotion = piece[1]?.toLowerCase() ?? 'q'
      setPendingFrom(null)
      return executeMove(pendingFrom, promotionToSquare, promotion)
    },
    [pendingFrom, promotionToSquare, executeMove],
  )

  // ── Square highlight styles ───────────────────────────────────────────────

  const customSquareStyles = useMemo(() => {
    const styles: Record<string, React.CSSProperties> = {}
    if (selectedSquare) {
      styles[selectedSquare] = { backgroundColor: 'rgba(255, 255, 100, 0.35)' }
    }
    legalTargets.forEach((sq) => {
      const occupied = !!gameRef.current.get(sq)
      styles[sq] = occupied
        ? {
            background:
              'radial-gradient(circle, transparent 58%, rgba(0,0,0,0.25) 58%)',
            borderRadius: '50%',
          }
        : {
            background:
              'radial-gradient(circle, rgba(0,0,0,0.2) 28%, transparent 28%)',
          }
    })
    return styles
  }, [selectedSquare, legalTargets])

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div ref={containerRef} className="board-container">
      <Chessboard
        id="puzzle-board"
        boardWidth={boardWidth}
        position={fen}
        boardOrientation={boardOrientation}
        onPieceDrop={onDrop}
        onSquareClick={onSquareClick}
        arePiecesDraggable={status !== 'complete'}
        customSquareStyles={customSquareStyles}
        customDarkSquareStyle={{ backgroundColor: '#b58863' }}
        customLightSquareStyle={{ backgroundColor: '#f0d9b5' }}
        promotionToSquare={promotionToSquare}
        showPromotionDialog={showPromotion}
        onPromotionPieceSelect={onPromotionPieceSelect}
      />
    </div>
  )
}
