'use client'

import Link from 'next/link'
import { useAuth } from '@/lib/auth'

export default function Header() {
  const { user, logout } = useAuth()

  return (
    <header className="site-header">
      <div className="site-header-content">
        <h1>Night Chess</h1>
        <nav className="site-nav">
          {user ? (
            <div className="auth-buttons">
              <span className="user-email">{user.email}</span>
              <button onClick={logout} className="btn-logout">Log out</button>
            </div>
          ) : (
            <div className="auth-buttons">
              <Link href="/login" className="btn-login">Sign In</Link>
              <Link href="/register" className="btn-register">Register</Link>
            </div>
          )}
        </nav>
      </div>
    </header>
  )
}
