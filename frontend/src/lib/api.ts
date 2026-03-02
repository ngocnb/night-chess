const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export interface Puzzle {
  id: string
  fen: string
  moves: string[]
  rating: number
  themes: string[] | null
}

export async function fetchRandomPuzzle(): Promise<Puzzle> {
  const res = await fetch(`${API_URL}/api/v1/puzzles/random`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`Failed to fetch puzzle: ${res.status}`)
  return res.json()
}
