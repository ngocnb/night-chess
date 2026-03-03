const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export interface Puzzle {
  id: string
  fen: string
  moves: string[]
  rating: number
  themes: string[] | null
}

export interface ProgressItem {
  puzzle_id: string
  result: string
  time_spent_ms: number | null
  solved_at: string
}

export interface ProgressPage {
  items: ProgressItem[]
  total: number
  page: number
  page_size: number
}

export async function fetchRandomPuzzle(): Promise<Puzzle> {
  const res = await fetch(`${API_URL}/api/v1/puzzles/random`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`Failed to fetch puzzle: ${res.status}`)
  return res.json()
}

export async function submitPuzzle(
  puzzleId: string,
  result: 'solved' | 'failed',
  timeSpentMs: number | null,
  accessToken: string | null
): Promise<{ puzzle_id: string; result: string; solved_at: string }> {
  if (!accessToken) {
    throw new Error('Authentication required')
  }

  const res = await fetch(`${API_URL}/api/v1/puzzles/${puzzleId}/submit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({ result, time_spent_ms: timeSpentMs }),
  })

  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to submit puzzle')
  }

  return res.json()
}

export async function getProgress(
  accessToken: string | null,
  page: number = 1,
  pageSize: number = 20
): Promise<ProgressPage> {
  if (!accessToken) {
    throw new Error('Authentication required')
  }

  const res = await fetch(
    `${API_URL}/api/v1/users/me/progress?page=${page}&page_size=${pageSize}`,
    {
      headers: { Authorization: `Bearer ${accessToken}` },
    }
  )

  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Failed to fetch progress')
  }

  return res.json()
}
