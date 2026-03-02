import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Night Chess',
  description: 'Chess puzzle practice on the Lichess open database',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <h1>Night Chess</h1>
        </header>
        {children}
      </body>
    </html>
  )
}
