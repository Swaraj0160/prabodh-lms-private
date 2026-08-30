# Public Prabodh Website

**Built and live this pass**, using the existing landing-page architecture rather than a new route.

## Where it actually lives

Earlier passes correctly identified that `app/home/home.tsx` is the authenticated multi-organisation *picker*, not a public marketing page, and redirected it away for single-org mode. The real public (signed-out) landing route was found instead at:

- `app/orgs/[orgslug]/(withmenu)/page.tsx` — the actual route rendered at `/` for this single-org, self-hosted deployment (`proxy.ts` rewrites `/` to the tenant-scoped org root when `LEARNHOUSE_TENANCY=single`). Generates SEO/OG metadata server-side via `generateMetadata()`.
- `app/orgs/[orgslug]/(withmenu)/home-client.tsx` — reads `org.config.config.customization.landing.enabled` and renders `LandingCustom` (config-driven sections) when enabled, or `LandingClassic` (plain course grid) otherwise.
- `components/Landings/LandingCustom.tsx` — renders an ordered array of typed sections (`hero`, `text-and-image`, `logos`, `people`, `featured-courses`) from `org.config.config.customization.landing.sections`.

This is the pre-existing config-driven landing builder already shipped in the codebase (same one an org admin could configure through `OrgEditLanding.tsx` in the dashboard) — not a hand-built new page.

## What was configured

Enabled the landing (`enabled: true`) with two `hero`-type sections, set via the real backend API (`PUT /api/v1/orgs/1/landing`, the same endpoint `OrgEditLanding.tsx`'s save button calls):

1. A top hero: "Prabodh" heading, "A learning platform for creating, managing, and delivering courses." subheading, "Get Started" (→ `/signup`) and "Sign In" (→ `/login`) buttons.
2. A second section: "Everything you need to teach" / "Create courses, publish lessons and activities, track learner progress, and issue completion certificates."

No `text-and-image`, `logos`, or `people` sections were used — those types require an `image` object or people/logo data, and no real asset or claim exists to put there (would have required inventing content, which the spec forbids).

Also fixed via the same org-update endpoint: `og:description` was still "Default Organization" — updated to match the org description above.

## Verified live

- Authenticated and signed-out states, desktop and mobile (375×812) — no horizontal overflow, hero renders correctly, `og:description` meta tag confirmed correct via curl.
- Copy is deliberately generic/factual (what the product does, not who it's for or unverified claims) — consistent with the spec's "do not invent unsupported claims" instruction.

## Still open

No real logo, illustration, or photography exists to use in a `text-and-image` or `logos` section — see `frontend-open-questions.md` item 1. Adding those sections once real assets exist is a config-only change (no code), since `LandingCustom.tsx` already supports them.
