import type { MetadataRoute } from 'next'

// No real Prabodh icon set exists yet (see docs/prabodh/frontend-assets.md) — the
// icon below points at the same favicon already used as the browser-tab icon
// elsewhere, not a fabricated app icon. Swap once real 192/512 PNGs are supplied.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Prabodh',
    short_name: 'Prabodh',
    description: 'A learning platform for creating, managing, and delivering courses.',
    start_url: '/',
    display: 'standalone',
    background_color: '#ffffff',
    theme_color: '#0f172a',
    icons: [
      {
        src: '/favicon.ico',
        sizes: '48x48',
        type: 'image/x-icon',
      },
    ],
  }
}
