import type { Metadata } from 'next'
import './globals.css'
import { AuthProvider } from '@/lib/auth'
import Header from '@/components/Header'

export const metadata: Metadata = {
  title: 'Night Chess',
  description: 'Chess puzzle practice on the Lichess open database',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <Header />
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}
