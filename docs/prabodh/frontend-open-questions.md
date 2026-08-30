# Frontend Open Questions

Honest list of what's still unresolved. See `frontend-verification.md` for what was verified working, `frontend-branding.md` for the full file-by-file change log.

## RESOLVED — session 5 (2026-08-24, full QA pass)

### Certificate PDF byte-level inspection — DONE, see frontend-verification.md
Previously the single most persistent open item. Solved by capturing the real `Blob` the app's own download pipeline produces (via a `URL.createObjectURL` intercept) and decoding it locally into an actual PDF file. Confirmed clean: no "Default Organization", no LearnHouse branding, correct real data throughout.

### Leftover test course — resolved again
Created a new test course this session (to generate the real certificate above), then deleted it via the same `DELETE /courses/{uuid}` API the dashboard uses. `/dash/courses` confirmed empty afterward.

### `/terms`, `/privacy`, `/contact` unreachable — FIXED
Found and fixed a real `proxy.ts` middleware gap; all three now work. Full detail in `frontend-branding.md` session 5.

### Fabricated certificate instructor name — FIXED
`CertificatePreview.tsx` hardcoded `'Dr. Jane Smith'` as a fallback that rendered on real, issued certificates whenever the (optional) instructor field was left blank. Fixed to hide the block instead of fabricating a name.

### Broken social-preview images — FIXED
8 pages' `og:image`/`twitter:image` pointed at a guaranteed-404 URL whenever no thumbnail was uploaded. Fixed to correctly omit the image field instead.

### Course creation bug (unrelated to branding, found during QA) — FIXED
`org_id=null` race condition in `CreateCourse.tsx` broke "Start from Scratch" course creation. Fixed.

### Backend Gate B3 (single-org enforcement) — confirmed NOT implemented, documented, not touched
Searched `apps/api/src/services/orgs/*.py` for a tenancy check on org creation — none exists; the backend's `create_org` has no single-tenancy guard. This is a **backend-owned gap**, out of scope for this track. The frontend-only UI gating already in place (`isMultiOrgModeEnabled()`, confirmed still working: `/new`, `/organizations`, `/home` all correctly 404 in single-tenancy) is the correct and complete frontend response until the backend gate exists — hiding the UI is not the same as backend enforcement, and this doc says so explicitly so nobody mistakes one for the other.

## RESOLVED — session 3 (2026-08-24, browser-first audit)

### The actual bug the user's screenshot caught: a text-wordmark SVG, invisible to string search
The top navigation used on `/courses`, `/library`, `/podcasts`, `/communities`, `/playgrounds` (and everywhere else `OrgMenu.tsx` renders) fell back to a `LearnHouseLogo` sub-component whenever no custom org logo is set — which is always true here, since no Prabodh logo asset exists. That component rendered `/lrn-text.svg`, an SVG file whose `<path>` elements are literally hand-drawn letterforms spelling out "LearnHouse" as vector graphics — not a text string anywhere in the codebase, which is exactly why every grep-based sweep in sessions 1 and 2 missed it entirely. **This is the single most important lesson from this session**: string search cannot find text baked into vector path data. Fixed by replacing the component with a plain text "Prabodh" wordmark (honest placeholder, not an invented logo — same pattern already used for the email header) that adapts to light/dark nav backgrounds the same way the old image did. Verified live in the browser at `/courses`, `/library`, `/podcasts`, `/communities`, `/playgrounds` — all now show "Prabodh" instead of the LearnHouse image. Checked the two sibling icon SVGs (`lrn.svg`, `lrn-dash.svg`) for the same problem — both are pure abstract geometric icon shapes with no letterform paths, confirmed safe to keep.

### Terms of Service / Privacy Policy — FIXED (previously "still points at learnhouse.io")
`LegalFooters.tsx`'s fallback URLs sent users to `https://www.learnhouse.io/terms` and `/privacy` — a different company's actual legal pages — whenever no platform URL is configured (which is always, for this deployment). Per instruction not to invent legal text but also not to leave a wrong external link: changed the fallback to relative in-app routes (`/terms`, `/privacy`) and created two minimal placeholder pages (`apps/web/app/terms/page.tsx`, `apps/web/app/privacy/page.tsx`) that plainly state real content is pending, rather than inventing legal copy or sending users to LearnHouse's site. Verified live: the login and signup pages' Terms/Privacy links now point to `/terms` and `/privacy`.

### Support/contact fallback — FIXED (same problem, found during this session's sweep)
`ErrorActions.tsx`'s "Contact support" button fell back to `mailto:support@learnhouse.io` — LearnHouse's own support inbox — under the same conditions. Same treatment: falls back to `/contact`, a new minimal placeholder page (`apps/web/app/contact/page.tsx`) stating real contact details are pending.

### Course import labels — FIXED (previously left as "possibly a technical format name")
Actually opened the "Import Course" dialog in the browser as instructed. It shows two options: "SCORM Package" (a real external standard — correctly left alone) and, previously, "LearnHouse Courses" / "Import courses exported from LearnHouse" — plainly a display label, not a technical identifier a user needs to see. Confirmed in code that the internal type discriminator (`'learnhouse'` as a TypeScript union member, used for switch-case branching) is separate from the four display strings; changed only the display strings ("Prabodh Courses", "Import courses exported from Prabodh", etc.) and left the internal `'learnhouse'` type value untouched. Verified live: the dialog now reads "Prabodh Courses" / "Import courses exported from Prabodh".

### Full page-by-page browser audit performed
Logged in and out live (cleared cookies to test the real signed-out state, not just source code) and checked, via both visual inspection and a scripted "does this page's rendered text/alt-attributes contain 'learnhouse'" check: `/`, `/login`, `/signup`, `/courses`, `/library`, `/podcasts`, `/communities`, `/playgrounds`, `/dash`, `/dash/courses`, `/dash/users/settings/users`, `/dash/org/settings/general`, the real issued certificate page, a nonexistent route (404), and mobile viewport (375×812) versions of `/dash` and `/courses`. **All clean** — zero "learnhouse" in rendered text or image alt attributes on any of them, confirmed after the wordmark fix above.

## RESOLVED — session 4 (2026-08-24, public website + deeper source sweep)

### Public Prabodh website — now built
Previously listed as "still not built" below. Re-scoped per the spec (§11): the public surface is the existing signed-out app, config-driven landing builder, not an invented marketing site. Configured the pre-existing `LandingCustom` landing (hero + "what it offers" sections, factual non-invented copy) via the real `PUT /orgs/{id}/landing` API — the same mechanism the dashboard's own landing editor uses. Also fixed a stale `og:description` ("Default Organization"). Full detail in `frontend-website.md`. Verified live, authenticated + signed-out, desktop + mobile.

### A second wave of grep-based (not just browser-based) source sweeping found real remaining leaks
Session 3's methodology was "browser-first, because grep missed the SVG wordmark." Session 4 additionally grepped the **rebuilt production bundle** (`.next/static/chunks/*.js`) for "learnhouse" and manually classified every distinct match — catching several genuine, still-user-visible English strings that no page visited during the browser sweep happened to render (they're on pages/states not in the tested list: API-access page, purchase-confirmation email, course-page SEO fallback, an unused-in-current-UI-but-still-shipped translation key). Fixed:
- `locales/en.json`: `"university": "LearnHouse University"` (dashboard onboarding checklist), `"learnhouse_university": "LearnHouse University"` (orphaned/unreferenced key, fixed for hygiene), `"website": "LearnHouse Website"` (orphaned help-menu key — the actual link was already removed from the UI in session 3, this was just dead translation text), and a stale `createOrg.testHint` sentence ("...to try LearnHouse instead.") that would have **overridden** the component's own already-fixed `defaultValue` fallback at runtime, since i18next prefers a resolved key over `defaultValue`.
- `components/Dashboard/Pages/Org/OrgEditAPIAccess/OrgEditAPIAccess.tsx`: the "something not working?" link on the API/developer settings page hardcoded `mailto:hello@learnhouse.app` — same category of bug as the `ErrorActions.tsx` fix from session 3. Now routes to `/contact`.
- `lib/errors/catalog.ts`: the "stale build" toast message read "A new version of LearnHouse was released...".
- `services/billing/emails.ts`: the purchase-confirmation email said "Thanks for supporting LearnHouse."
- `services/emails/resend.ts`: `DEFAULT_FROM` — the fallback **From:** header for every outgoing transactional email (when `RESEND_FROM_EMAIL` isn't set) was `'LearnHouse <hello@emails.learnhouse.app>'`. Every email a user received would have shown "From: LearnHouse" in their inbox. Changed to a placeholder `Prabodh <no-reply@prabodh.example>` (`.example` is the RFC 2606 reserved placeholder TLD — deliberately not a real, invented-as-if-functional address).
- `services/emails/transactional.ts`: same pattern — fallback contact-form recipient was `hello@learnhouse.app`.
- `app/(hub)/new/_components/PricingCards.tsx` and `app/(hub)/billing/_components/PricingGrid.tsx`: the Enterprise plan's "Talk to us" button linked to `https://learnhouse.app/contact?subject=business`. Changed to `/contact`. (Low reachability in this single-org deployment — see item 3 below — fixed anyway since it's live code.)
- `app/orgs/[orgslug]/(withmenu)/course/[courseuuid]/page.tsx`: SEO metadata fallback when a course fails to load read `Course — LearnHouse` / `View this course on LearnHouse`.
- `components/Dashboard/Pages/Org/OrgEditAI/OrgEditAI.tsx`: an `alt="LearnHouse AI"` on the AI settings page header icon.

All confirmed fixed via a post-fix rebuild + re-grep of the bundle (the English strings no longer appear anywhere in `.next/static/chunks/`; remaining bundle hits are exclusively other-language locale JSON, which is inert since the app ships English-only per `lib/languages.ts`).

### Things checked and confirmed correctly *not* leaking (by design, not oversight)
Three components (`AuthBrandingPanel.tsx`'s login top-bar logo, the org-page footer watermark in `app/orgs/[orgslug]/(withmenu)/layout.tsx`, and `components/Objects/Watermark.tsx`'s floating "Made with LearnHouse" pill) all still contain literal `https://learnhouse.app` links and, in `Watermark.tsx`'s case, the same `lrn-text.svg` wordmark asset that caused the session-3 bug. All three are already gated behind `getDeploymentMode() === 'oss'` (or `'ee'`) checks that correctly return `null`/hide before rendering — and this deployment's `LH_mode` cookie is confirmed `oss`. These are dead-in-this-deployment code paths for LearnHouse's own hypothetical non-white-label SaaS mode, not bugs. Left as-is; flagging here so a future pass doesn't waste time re-discovering them.

### AI settings page — reachable and fully interactive despite AI being platform-disabled
Visited `/dash/org/settings/ai` and `/copilot` live. Both render cleanly (no leftover branding) and the "Enable AI Features" / "AI Copilot" toggles are clickable, not disabled, and show as checked. This confirms — rather than newly discovers — the item below: the frontend has no way to know `LEARNHOUSE_IS_AI_ENABLED=false` at the platform level, so these controls silently no-op instead of being visibly disabled. No frontend-only fix is correct here (see below); documenting the live-verified symptom rather than leaving it as a theoretical concern.

## STILL OPEN

### 1. No approved Prabodh visual assets exist yet
Unchanged: no real logo, favicon set, OG image, palette, or typeface has been supplied. The nav wordmark is now honest placeholder text (not the LearnHouse SVG), and all `alt` text says "Prabodh" — but a proper graphic mark still needs a real designed asset. **Not fabricated** per instruction.

### 2. ~~AI platform flag not visible to the frontend~~ — RESOLVED, Part 2
Backend now enforces the flag and exposes it via `/instance/info`; frontend reads it and shows accurate state. Full detail in `frontend-ai-surfaces.md` and `docs/prabodh/part2-ai-architecture.md`. The active AI provider (Claude, then switched to Gemini for local/demo — see `part2-gemini-provider.md`) required no further frontend change, since the frontend is provider-agnostic by design (it only reacts to `is_ai_enabled`, never to which vendor is behind it).

### 3. `apps/web/ee/` folder — ownership unclear
Unchanged. Not touched — no spec guidance found on it after re-reading the three PDFs.

### 4. ~~Public Prabodh website~~ — RESOLVED session 4, see above and `frontend-website.md`

### 5. ~~Certificate PDF byte-level file inspection~~ — RESOLVED session 5, see above and `frontend-verification.md`

### 6. ~~Leftover test course~~ — RESOLVED session 4
Deleted via a direct `DELETE /api/v1/courses/{uuid}` call (the same endpoint the dashboard's own delete button uses). Verified `/dash/courses` now shows "No courses yet".

### 7. Full apps/web LearnHouse-string sweep — substantially more exhaustive after session 4, still not mathematically 100%
Session 4 added a second sweep pass this session 3 didn't do: grepping the **rebuilt production bundle** (not just source files, and not just browser-rendered pages) and manually classifying every distinct match. That caught 9 real remaining leaks across files a page-by-page browser click-through wouldn't necessarily land on (see the RESOLVED section above) — confirming the earlier concern in this item was well-founded. All 9 are now fixed and reconfirmed absent from a fresh rebuild's bundle. What's still unverified: every course-editor sub-tab and every modal in the app wasn't individually opened in a browser (impractical to enumerate exhaustively); the bundle-grep approach mitigates most of that risk since it catches any string that ships to the client regardless of which click-path reaches it, but a string assembled at runtime via string concatenation (not a literal in source) would still be invisible to grep the same way the SVG wordmark was invisible to it.

### 8. `(hub)/new` and `(hub)/billing` pricing pages still reference an Enterprise/multi-tenant sales flow
`PricingCards.tsx` / `PricingGrid.tsx` render an "Enterprise" plan card with "Talk to us" (now pointed at `/contact` instead of LearnHouse's sales email, but the surrounding Enterprise-tier marketing content — "Built for scale", plan comparison — is still LearnHouse SaaS-product content). These routes are under `app/(hub)/`, which per `proxy.ts` only rewrites unconditionally for `multi` tenancy; this deployment runs `single` tenancy, so they're not reachable through normal navigation, only by direct URL. Not fixed further this pass — same reasoning as item 3, ownership of `(hub)/*` (multi-tenant SaaS shell vs. this single-org deployment) wasn't specified in the PDFs.
