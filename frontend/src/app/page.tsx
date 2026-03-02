'use client'

import { useState, useEffect } from 'react'
import PuzzleBoard from '@/components/PuzzleBoard'
import { fetchRandomPuzzle, type Puzzle } from '@/lib/api'

export default function Home() {
  const [puzzle, setPuzzle] = useState<Puzzle | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadPuzzle = async () => {
    setLoading(true)
    setError(null)
    try {
      const p = await fetchRandomPuzzle()
      setPuzzle(p)
    } catch {
      setError('Could not load puzzle — try again')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPuzzle()
  }, [])

  return (
    <main>
      <h1>Night Chess</h1>
      {puzzle && (
        <p>
          Rating: {puzzle.rating}
          {puzzle.themes ? ` · ${puzzle.themes.join(', ')}` : ''}
        </p>
      )}
      {loading && <p>Loading puzzle...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {puzzle && !loading && (
        <PuzzleBoard
          puzzle={puzzle}
          onComplete={() => {}}
        />
      )}
      <button onClick={loadPuzzle} disabled={loading}>
        Next Puzzle
      </button>
    </main>
  )
}
