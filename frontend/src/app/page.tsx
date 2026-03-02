'use client'

import { useState, useEffect, useCallback } from 'react'
import PuzzleBoard, { type PuzzleStatus } from '@/components/PuzzleBoard'
import { fetchRandomPuzzle, type Puzzle } from '@/lib/api'

function getPlayerColor(puzzle: Puzzle): 'White' | 'Black' {
  // FEN side-to-move is the opponent (they play moves[0]).
  // The player is the opposite color.
  return puzzle.fen.split(' ')[1] === 'w' ? 'Black' : 'White'
}

function getStatusLabel(status: PuzzleStatus, puzzle: Puzzle | null): string {
  if (status === 'playing') return puzzle ? `${getPlayerColor(puzzle)} to play` : '…'
  if (status === 'correct') return 'Best move!'
  if (status === 'incorrect') return 'Incorrect — try again'
  return 'Puzzle solved!'
}

export default function Home() {
  const [puzzle, setPuzzle] = useState<Puzzle | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [puzzleStatus, setPuzzleStatus] = useState<PuzzleStatus>('playing')

  const loadPuzzle = useCallback(async () => {
    setLoading(true)
    setError(null)
    setPuzzleStatus('playing')
    try {
      setPuzzle(await fetchRandomPuzzle())
    } catch {
      setError('Could not load puzzle — try again')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadPuzzle() }, [loadPuzzle])

  return (
    <div className="page-wrapper">
      {/* Board */}
      <div>
        {loading && <div className="board-container skeleton" />}
        {error && !loading && (
          <div className="board-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <p className="error-msg">{error}</p>
          </div>
        )}
        {puzzle && !loading && (
          <PuzzleBoard
            puzzle={puzzle}
            onComplete={() => {}}
            onStatusChange={setPuzzleStatus}
          />
        )}
      </div>

      {/* Sidebar */}
      <aside className="sidebar">
        <span className="sidebar-title">Puzzle training</span>

        {puzzle && (
          <div className="rating-row">
            <span className="rating-label">Rating</span>
            <span className="rating-value">{puzzle.rating}</span>
          </div>
        )}

        {puzzle?.themes && puzzle.themes.length > 0 && (
          <div className="themes">
            {puzzle.themes.map((t) => (
              <span key={t} className="theme-tag">{t}</span>
            ))}
          </div>
        )}

        <hr className="divider" />

        <div className="status-bar">
          <span className={`status-dot ${puzzleStatus}`} />
          <span className={`status-text ${puzzleStatus}`}>
            {getStatusLabel(puzzleStatus, puzzle)}
          </span>
        </div>

        <hr className="divider" />

        <button className="btn-next" onClick={loadPuzzle} disabled={loading}>
          {loading ? 'Loading…' : 'Next puzzle →'}
        </button>

        {error && <p className="error-msg">{error}</p>}
      </aside>
    </div>
  )
}
