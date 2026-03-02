/**
 * Tests for frontend/src/app/page.tsx (Home)
 *
 * Tests cover:
 * - Shows loading state on initial render
 * - Renders puzzle rating and themes after successful fetch
 * - Shows error message when API fails
 * - "Next Puzzle" button triggers a new fetch
 * - Button is disabled while loading and enabled after
 * - PuzzleBoard is rendered when puzzle loaded
 * - PuzzleBoard is not rendered on error
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

  it('shows "Loading puzzle..." on initial render', async () => {
    mockFetch.mockReturnValue(new Promise(() => {})) // never resolves

    render(<Home />)
    expect(screen.getByText('Loading puzzle...')).toBeInTheDocument()
  })

  it('renders puzzle rating and themes after successful fetch', async () => {
    mockFetch.mockResolvedValue(MOCK_PUZZLE)

    render(<Home />)

    await waitFor(() => {
      expect(screen.getByText(/Rating: 1500/)).toBeInTheDocument()
    })
    expect(screen.getByText(/opening, tactical/)).toBeInTheDocument()
    expect(screen.queryByText('Loading puzzle...')).not.toBeInTheDocument()
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
      expect(screen.getByText('Could not load puzzle — try again')).toBeInTheDocument()
    })
  })

  it('does not show PuzzleBoard when there is an error', async () => {
    mockFetch.mockRejectedValue(new Error('fail'))

    render(<Home />)

    await waitFor(() => {
      expect(screen.queryByTestId('puzzle-board')).not.toBeInTheDocument()
    })
  })

  it('"Next Puzzle" button is disabled while loading', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))

    render(<Home />)

    expect(screen.getByRole('button', { name: /Next Puzzle/i })).toBeDisabled()
  })

  it('"Next Puzzle" button is enabled after load completes', async () => {
    mockFetch.mockResolvedValue(MOCK_PUZZLE)

    render(<Home />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Next Puzzle/i })).not.toBeDisabled()
    })
  })

  it('clicking "Next Puzzle" triggers another fetchRandomPuzzle call', async () => {
    const SECOND_PUZZLE: Puzzle = { ...MOCK_PUZZLE, id: 'second', rating: 1600 }
    mockFetch.mockResolvedValueOnce(MOCK_PUZZLE).mockResolvedValueOnce(SECOND_PUZZLE)

    render(<Home />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Next Puzzle/i })).not.toBeDisabled()
    })

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Next Puzzle/i }))
    })

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2)
    })
  })

  it('renders title "Night Chess"', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))

    render(<Home />)

    expect(screen.getByRole('heading', { name: 'Night Chess' })).toBeInTheDocument()
  })

  it('renders rating without themes separator when themes is null', async () => {
    const puzzleNoThemes: Puzzle = { ...MOCK_PUZZLE, themes: null }
    mockFetch.mockResolvedValue(puzzleNoThemes)

    render(<Home />)

    await waitFor(() => {
      expect(screen.getByText('Rating: 1500')).toBeInTheDocument()
    })
  })
})
