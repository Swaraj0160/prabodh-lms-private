import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Privacy Policy — Prabodh',
}

// Placeholder page. Real Privacy Policy content has not been supplied yet —
// this deliberately states that rather than inventing legal text, and exists
// so the app never links out to a different company's legal pages in the
// meantime. See docs/prabodh/frontend-open-questions.md.
export default function PrivacyPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-16">
      <div className="max-w-lg text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-3">Privacy Policy</h1>
        <p className="text-gray-600 leading-relaxed">
          Prabodh&apos;s Privacy Policy is being finalized and will be published here.
        </p>
        <Link href="/" className="inline-block mt-6 text-sm font-semibold text-black/60 hover:text-black transition-colors">
          ← Back to Prabodh
        </Link>
      </div>
    </div>
  )
}
