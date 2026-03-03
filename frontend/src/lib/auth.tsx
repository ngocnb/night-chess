'use client'

import { createContext, useContext, useEffect, useState, useRef, ReactNode } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export interface User {
  id: string
  email: string
  created_at: string
}

interface AuthContextType {
  user: User | null
  accessToken: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const accessTokenRef = useRef<string | null>(null)
  const [isInitialized, setIsInitialized] = useState(false)

  // Try to refresh token on mount (silent auth restore)
  useEffect(() => {
    const initAuth = async () => {
      try {
        await refresh()
      } catch {
        // No valid refresh token, user remains null
      } finally {
        setIsInitialized(true)
      }
    }
    initAuth()
  }, [])

  const login = async (email: string, password: string) => {
    const res = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
      credentials: 'include',
    })

    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail || 'Login failed')
    }

    const data = await res.json()
    accessTokenRef.current = data.access_token

    // Fetch user info
    const userRes = await fetch(`${API_URL}/api/v1/users/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` },
    })
    if (userRes.ok) {
      const userData = await userRes.json()
      setUser(userData)
    }
  }

  const logout = async () => {
    try {
      await fetch(`${API_URL}/api/v1/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      })
    } catch {
      // Ignore errors during logout
    }
    accessTokenRef.current = null
    setUser(null)
  }

  const refresh = async () => {
    const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    })

    if (!res.ok) {
      throw new Error('Refresh failed')
    }

    const data = await res.json()
    accessTokenRef.current = data.access_token

    // Fetch user info
    const userRes = await fetch(`${API_URL}/api/v1/users/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` },
    })
    if (userRes.ok) {
      const userData = await userRes.json()
      setUser(userData)
    }
  }

  const contextValue: AuthContextType = {
    user,
    accessToken: accessTokenRef.current,
    login,
    logout,
    refresh,
  }

  // Don't render children until we've checked for existing session
  if (!isInitialized) {
    return null
  }

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
