import type { Metadata } from 'next'
import { Plus_Jakarta_Sans } from 'next/font/google'
import { Toaster } from 'sonner'
import './globals.css'
import { Providers } from './providers'

const jakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-jakarta',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Ledgi - Personal Finance Dashboard',
  description: 'Track your spending across all your accounts',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={jakarta.variable}>
      <body className={jakarta.className}>
        <Providers>
          <div className="min-h-screen bg-surface-base">
            {children}
          </div>
          <Toaster position="bottom-right" richColors closeButton />
        </Providers>
      </body>
    </html>
  )
}
