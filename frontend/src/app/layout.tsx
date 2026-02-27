import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Night Chess',
  description: 'Chess puzzle practice on the Lichess open database',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
