import '../styles/globals.css'
import React from 'react'
import Providers from '@components/Providers'
import { Wix_Madefor_Text } from 'next/font/google'
import type { Metadata, Viewport } from 'next'

const wixMadeforText = Wix_Madefor_Text({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-default',
})

// No `title.template` here deliberately: every page in this app already
// builds its own fully-suffixed title (buildPageTitle() appends "— {org
// name}", and the standalone pages like /terms set a complete string) — a
// root template would double-suffix all of them ("Foo — Prabodh — Prabodh").
// `default` only fires for a route with no title metadata at all.
export const metadata: Metadata = {
  applicationName: 'Prabodh',
  title: 'Prabodh',
  description: 'A learning platform for creating, managing, and delivering courses.',
  manifest: '/manifest.webmanifest',
}

export const viewport: Viewport = {
  themeColor: '#0f172a',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html className={wixMadeforText.variable} lang="en" suppressHydrationWarning>
      <head>
        {/* Synchronous script — blocks parsing to guarantee window.__RUNTIME_CONFIG__ exists before any JS runs.
            Next.js <Script strategy="beforeInteractive"> is not truly blocking in all browsers (Safari). */}
        {/* eslint-disable-next-line @next/next/no-sync-scripts */}
        <script src="/runtime-config.js" />
        {/* Prevent white flash on embed routes: set html+body bg before body is painted.
            Reads the optional ?bgcolor param (hex-validated) or defaults to dark. */}
        {/* eslint-disable-next-line @next/next/no-sync-scripts */}
        <script src="/embed-bg.js" />
      </head>
      <body suppressHydrationWarning>
        <Providers>
          <main className="animate-fade-in">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  )
}
