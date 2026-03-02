/**
 * Tests for frontend/src/app/page.tsx (Home)
 *
 * Tests cover:
 * - Shows loading skeleton (no puzzle board) on initial render
 * - Renders puzzle rating value after successful fetch
 * - Renders each theme as a separate tag after successful fetch
 * - Shows error message when API fails
 * - "Next puzzle" button triggers a new fetch
 * - Button is disabled while loading and enabled after
 * - PuzzleBoard is rendered when puzzle loaded
 * - PuzzleBoard is not rendered on error
 * - Status label starts as "{Color} to play"
 * - Renders correctly when puzzle has null themes
 */

import React from 'react'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import type { Puzzle } from '@/lib/api'

// Mock the api module before any imports from page
jest.mock('@/lib/api', () => ({
  fetchRandomPuzzle: jest.fn(),
}))

// Mock PuzzleBoard to avoid chess rendering complexity
jest.mock('@/components/PuzzleBoard', () => ({
  __esModule: true,
  default: ({ puzzle }: { puzzle: Puzzle }) => (
    <div data-testid="puzzle-board" data-puzzle-id={puzzle.id} />
  ),
}))

// Import after mocks are set up
import Home from '@/app/page'
import { fetchRandomPuzzle } from '@/lib/api'

const mockFetch = fetchRandomPuzzle as jest.Mock

// FEN side-to-move 'w' means opponent is White → player is Black
const MOCK_PUZZLE: Puzzle = {
  id: 'test-puzzle',
  fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
  moves: ['e2e4', 'e7e5'],
  rating: 1500,
  themes: ['opening', 'tactical'],
}

describe('Home page', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('does not render puzzle board during initial loading', () => {
    mockFetch.mockReturnValue(new Promise(() => {})) // never resolves

    render(<Home />)
    expect(screen.queryByTestId('puzzle-board')).not.toBeInTheDocument()
  })

  it('renders puzzle rating value after successful fetch', async () => {
    mockFetch.mockResolvedValue(MOCK_PUZZLE)

    render(<Home />)

    await waitFor(() => {
      expect(screen.getByText('1500')).toBeInTheDocument()
    })
  })

  it('renders each theme as a separate tag', async () => {
    mockFetch.mockResolvedValue(MOCK_PUZZLE)

    render(<Home />)

    await waitFor(() => {
      expect(screen.getByText('opening')).toBeInTheDocument()
      expect(screen.getByText('tactical')).toBeInTheDocument()
    })
  })

  it('renders PuzzleBoard when puzzle loaded', async () => {
    mockFetch.mockResolvedValue(MOCK_PUZZLE)

    render(<Home />)

    await waitFor(() => {
      expect(screen.getByTestId('puzzle-board')).toBeInTheDocument()
    })
    expect(screen.getByTestId('puzzle-board').dataset.puzzleId).toBe('test-puzzle')
  })

  it('shows error message when API call fails', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    render(<Home />)

    await waitFor(() => {
      // Error rendered in both the board area and sidebar
      const msgs = screen.getAllByText('Could not load puzzle — try again')
      expect(msgs.length).toBeGreaterThan(0)
    })
  })

  it('does not show PuzzleBoard when there is an error', async () => {
    mockFetch.mockRejectedValue(new Error('fail'))

    render(<Home />)

    await waitFor(() => {
      expect(screen.queryByTestId('puzzle-board')).not.toBeInTheDocument()
    })
  })

  it('"Next puzzle" button shows "Loading…" while loading', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))

    render(<Home />)

    expect(screen.getByRole('button', { name: /loading/i })).toBeDisabled()
  })

  it('"Next puzzle" button is enabled after load completes', async () => {
    mockFetch.mockResolvedValue(MOCK_PUZZLE)

    render(<Home />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /next puzzle/i })).not.toBeDisabled()
    })
  })

  it('clicking "Next puzzle" triggers another fetchRandomPuzzle call', async () => {
    const SECOND_PUZZLE: Puzzle = { ...MOCK_PUZZLE, id: 'second', rating: 1600 }
    mockFetch.mockResolvedValueOnce(MOCK_PUZZLE).mockResolvedValueOnce(SECOND_PUZZLE)

    render(<Home />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /next puzzle/i })).not.toBeDisabled()
    })

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /next puzzle/i }))
    })

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2)
    })
  })

  it('shows "Black to play" when FEN side-to-move is "w" (opponent is White, player is Black)', async () => {
    mockFetch.mockResolvedValue(MOCK_PUZZLE) // FEN has 'w' side-to-move

    render(<Home />)

    await waitFor(() => {
      expect(screen.getByText('Black to play')).toBeInTheDocument()
    })
  })

  it('renders correctly when puzzle has null themes (no theme tags shown)', async () => {
    const puzzleNoThemes: Puzzle = { ...MOCK_PUZZLE, themes: null }
    mockFetch.mockResolvedValue(puzzleNoThemes)

    render(<Home />)

    await waitFor(() => {
      expect(screen.getByText('1500')).toBeInTheDocument()
    })
    // No theme tags rendered
    expect(screen.queryByText('opening')).not.toBeInTheDocument()
  })
})
