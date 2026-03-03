/**
 * Tests for frontend/src/components/Header.tsx
 *
 * Guards against the regression where auth links were placed in the sidebar
 * instead of the site header. Tests verify:
 * - Unauthenticated: "Sign In" and "Register" links appear inside <header>
 * - Authenticated: user email and "Log out" button appear inside <header>
 * - Log out button calls the logout callback
 */

import React from 'react'
import { render, screen, fireEvent, within } from '@testing-library/react'
import Header from '@/components/Header'

jest.mock('@/lib/auth', () => ({
  useAuth: jest.fn(),
}))

jest.mock('next/link', () => ({
  __esModule: true,
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}))

import { useAuth } from '@/lib/auth'
const mockUseAuth = useAuth as jest.Mock

describe('Header', () => {
  describe('unauthenticated', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({ user: null, logout: jest.fn() })
    })

    it('renders inside a <header> element', () => {
      render(<Header />)
      expect(screen.getByRole('banner')).toBeInTheDocument()
    })

    it('shows Sign In link inside the header', () => {
      render(<Header />)
      const header = screen.getByRole('banner')
      expect(within(header).getByRole('link', { name: /sign in/i })).toBeInTheDocument()
    })

    it('shows Register link inside the header', () => {
      render(<Header />)
      const header = screen.getByRole('banner')
      expect(within(header).getByRole('link', { name: /register/i })).toBeInTheDocument()
    })

    it('Sign In link points to /login', () => {
      render(<Header />)
      expect(screen.getByRole('link', { name: /sign in/i })).toHaveAttribute('href', '/login')
    })

    it('Register link points to /register', () => {
      render(<Header />)
      expect(screen.getByRole('link', { name: /register/i })).toHaveAttribute('href', '/register')
    })

    it('does not show Log out button', () => {
      render(<Header />)
      expect(screen.queryByRole('button', { name: /log out/i })).not.toBeInTheDocument()
    })
  })

  describe('authenticated', () => {
    const mockLogout = jest.fn()

    beforeEach(() => {
      mockLogout.mockReset()
      mockUseAuth.mockReturnValue({
        user: { id: '1', email: 'chess@example.com', created_at: '' },
        logout: mockLogout,
      })
    })

    it('shows user email inside the header', () => {
      render(<Header />)
      const header = screen.getByRole('banner')
      expect(within(header).getByText('chess@example.com')).toBeInTheDocument()
    })

    it('shows Log out button inside the header', () => {
      render(<Header />)
      const header = screen.getByRole('banner')
      expect(within(header).getByRole('button', { name: /log out/i })).toBeInTheDocument()
    })

    it('calls logout when Log out button is clicked', () => {
      render(<Header />)
      fireEvent.click(screen.getByRole('button', { name: /log out/i }))
      expect(mockLogout).toHaveBeenCalledTimes(1)
    })

    it('does not show Sign In or Register links', () => {
      render(<Header />)
      expect(screen.queryByRole('link', { name: /sign in/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: /register/i })).not.toBeInTheDocument()
    })
  })
})
