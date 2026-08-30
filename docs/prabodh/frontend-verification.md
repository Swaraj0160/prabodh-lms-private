# Frontend Verification — What Was Actually Checked

Baseline branch: `prabodh/whitelabel`, clean working tree at session start (confirmed via `git status`).

## Build

```
cd apps/web && bun run build
```
Result: **passed cleanly.** `✓ Compiled successfully`, `Running TypeScript ... Finished TypeScript`, all 39 static pages generated. One pre-existing, unrelated warning about `next.config.js`/`services/config/config.ts` filesystem tracing (present before this pass's changes; not touched).

`bun run tsc --noEmit` was tried first and failed on an unrelated, pre-existing `tsconfig.json` deprecation setting (`baseUrl`, TS5101) — not something this pass caused or should fix (project config, unrelated to white-labelling). `next build`'s own TypeScript pass (which succeeded) is the authoritative check here.

**Session 2 (2026-08-24)**: re-ran `bun run build` after ~15 additional file edits (org-name debugging aside, all real branding fixes). Result: **passed cleanly again**, `✓ Compiled successfully in 17.9s`, zero new errors or warnings introduced.

## Session 2 — organisation name and certificate, actually verified live

- **Organisation name**: fixed through the real Admin → Organization Settings UI (not a DB edit). Root cause of the earlier failed attempt: the form's "Organization Label" field was required and empty, so Formik silently refused to submit — no visible error toast. Selected a label, saved, confirmed via a `PUT /api/v1/orgs/1 → 200` network response and a fresh page reload. Now shows "Prabodh" live everywhere: sidebar, page titles ("Courses — Prabodh", "Prabodh Dashboard"), auth screen org-name fallbacks.
- **Certificate — actually generated through the real product flow**, not just read in source: created a test course, added a Dynamic Page activity, enabled certification (Admin UI), published both course and activity, enrolled as the admin account, completed the activity via the real "Mark as complete" control, which triggered a genuine certificate issuance (ID `GY-20260823-...`). Read the full rendered text of the real, issued certificate (not the pre-issue design preview) and confirmed **zero LearnHouse references** anywhere in it. Fixed two issues found in the process: a `'LH-2024-001'` placeholder ID (design-preview screen only, real IDs don't use it) and an `org?.name || 'LearnHouse'` fallback, both in `CertificatePreview.tsx`.
  - **Honest limitation**: could not extract the literal PDF/PNG file bytes through browser automation — the sandbox blocks the page's own download trigger, and a canvas-capture workaround hit a tooling ceiling (documented in `frontend-open-questions.md`, not swept under the rug). What was verified is the actual DOM content the PDF is rasterized from (same node, confirmed by reading `CertificatePage.tsx`), which is a real check of real output, just not a pixel-level file open.
  - Test course "Prabodh Test Certificate Course" is still in the database — attempted deletion via the UI didn't complete reliably through automation; flagged for manual cleanup rather than risking an unattended destructive action going wrong.

## Dev server / live browser verification

Ran against `http://localhost:3000` (frontend), `http://localhost:1338` (backend), both confirmed healthy, backed by the existing `learnhouse-db-dev` / `learnhouse-redis-dev` Docker containers (untouched, not reset).

Verified live, logged in as `swaraj0160@gmail.com` (Admin role):

| Check | Result |
|---|---|
| Login page | Loads; title correctly reads "Login — Default Organization" (org name itself is still DB seed data — see open questions #6); terms text correctly reads "By continuing, you agree to Prabodh's Terms of Service and Privacy Policy." |
| Login flow | Successful login with the admin account; lands on the org home with course listing UI, "Admin" badge visible. |
| Admin panel title | `http://localhost:3000/admin` → browser tab title "Prabodh Admin" (was "LearnHouse Admin"). |
| Dashboard title | `/dash/org/settings/general` → tab title "Prabodh Dashboard" (was "LearnHouse Dashboard"). |
| Org settings page | Confirmed "Default Language: English" — only one language now offered, confirming the English-only trim took effect end-to-end (not just in source). |
| Onboarding copy | "Welcome to Prabodh" heading confirmed live on the dashboard onboarding widget. |
| AI settings page | `/dash/org/settings/ai` — confirmed "Enable AI Features" and "AI Copilot" both render as ON/interactive; this is the finding written up in `frontend-ai-surfaces.md`. |
| 404 page | Read directly (not navigated to) — confirmed no user-visible LearnHouse text; only an internal `learnhouseIcon` variable name, which is not user-visible. |

Not verified live this pass (see `frontend-open-questions.md` for why): certificate PDF generation, the public marketing site (none exists yet at a known route), org name save via the settings form (attempted, didn't persist through browser automation — likely a timing/automation issue, not a product bug; needs a human click to confirm and complete).

## Multi-organisation UI

- `/new` (org creation wizard): previously reachable with zero tenancy gating; now redirects to the single default org when `isMultiOrgModeEnabled()` is false. Not re-verified live via browser this pass after the fix (verified by code review + successful build only) — **recommend a manual click-through**: visit `http://localhost:3000/new` while logged in and confirm it bounces straight to the org home instead of showing the wizard.
- `/home` (the "choose your organization" picker): same treatment, same caveat — recommend a manual visit to `http://localhost:3000/home` to confirm the redirect.
- Org switcher, "My Organizations," billing, and the free-plan upgrade box: confirmed via code reading (not live click-through) to already be correctly gated by the same `isMultiOrgModeEnabled()` check, pre-existing in this codebase before this pass.

## Final LearnHouse-reference sweep (`apps/web`, `.ts`/`.tsx`/`.json`, case-insensitive)

- Before session 1: 138 files matched.
- After session 1: 128 files matched.
- After session 2 (this pass): 122 files match. The count understates progress — most of the reduction from 138→128 was real string fixes, but several files still "match" only because they now legitimately reference internal identifiers this session added (e.g. `getLEARNHOUSE_DOMAIN_VAL()` calls in `OrgSignInMethods.tsx`/`transactional.ts`, or the `LearnHouseEmail.tsx`/`LearnHouseSpinner.tsx`/`LearnHousePlayer.tsx` component/file names themselves, which stay unchanged per the internal-identifier rule). A raw match count is a weak proxy for "done" — see the file-by-file classification in `frontend-branding.md` and `frontend-open-questions.md` for what actually changed vs. what's internal-and-correct.
- The gap is not "10 fixed, rest ignored" — many of the 128 remaining hits are internal identifiers (`LEARNHOUSE_*` env vars, `getLEARNHOUSE_PLATFORM_URL_VAL`, `learnhouseIcon` variable names, `LearnHouseSpinner.tsx`/`LearnHousePlayer.tsx` component/file names with no visible branding), the 21 intentionally-untouched non-English locale JSON files, and files not yet individually triaged in this pass (see below).
- **Not exhaustively triaged this pass**: roughly 100 of the 128 remaining files were not individually opened and classified (e.g. `services/emails/*.ts`, `services/billing/*.ts`, `components/Objects/Editor/AI/*`, `components/Objects/Activities/AI/*`, `components/Dashboard/Pages/Org/OrgEditAPIAccess/*`, `EELicenseError.tsx`, `LearnHouseEmail.tsx`, `LearnHouseCourseImport.tsx`). This pass prioritized the explicitly-named spec hotspots, auth, multi-org UI, watermarks, and English-only — the highest-visibility, highest-risk areas — over an exhaustive file-by-file pass through all 128. A follow-up pass should work through this list systematically, classifying each per the six categories in the master prompt (user-visible / internal / license / dependency / external-marketing-link / uncertain).

## Not run this session

- `apps/e2e` Playwright suite (no baseline was captured before this pass per the guide's own recommendation — should be run and any regressions attributed correctly against a fresh baseline, not this pass's changes, since none was taken).
- Cross-browser matrix (Chrome only, via the automated browser tool).
- Mobile/responsive viewport check (not performed this pass).

## Session 4 (2026-08-24) — public website build + production-bundle sweep

### Build
Ran `bun run build` twice this session (once before the bundle sweep, once after applying the 9 fixes it found). Both passed cleanly: `✓ Compiled successfully`, same static/dynamic route counts as before, no new errors or warnings.

### Public website — built and verified live
See `frontend-website.md` for full detail. Configured the existing `LandingCustom` landing (hero + "what it offers" sections) via `PUT /api/v1/orgs/1/landing`, the same endpoint the dashboard's own landing editor uses. Verified live:
- Authenticated state at `/` — hero renders, "Get Started"/"Sign In" buttons present and correctly linked.
- Signed-out state (cookies cleared) at `/` — same content renders for anonymous visitors.
- Mobile viewport (375×812) — no horizontal overflow.
- `og:description` meta tag — confirmed via `curl` to read the updated org description instead of the stale "Default Organization".

### Production-bundle grep sweep (new technique this session)
Rather than relying only on browser click-through (which can only cover pages actually visited), grepped `.next/static/chunks/*.js` — the actual shipped client bundle — for `learnhouse` case-insensitively (104 files matched), then extracted 40-character-context snippets around every distinct match (`grep -ohE ".{40}[Ll]earn[Hh]ouse.{40}"`) and manually classified each one. This is a stronger check than source-file grep alone because it reflects exactly what ships to the browser, including translation strings pulled in at build time.

Found and fixed 9 genuine remaining English, user-visible (or user-inbox-visible) leaks — full list in `frontend-open-questions.md`'s "RESOLVED — session 4" section. Highlights: the transactional-email `From:` header default (`resend.ts`), a purchase-confirmation email's "Thanks for supporting LearnHouse", a hardcoded `mailto:hello@learnhouse.app` on the API-access settings page, and a stale i18n key (`createOrg.testHint`) that would have silently overridden a component's own already-fixed fallback text at runtime.

Re-ran the same bundle grep after rebuilding with the fixes applied: **zero English-locale matches remain.** All remaining hits are in the 21 non-English locale JSON files, which are inert since the app is English-only (confirmed via `lib/languages.ts` and the org settings page showing only "English" as an available language).

### Confirmed *not* bugs (checked, not just assumed)
Three components (`AuthBrandingPanel.tsx` login top-bar logo, the org-footer watermark, `Watermark.tsx`'s floating pill) still contain literal `learnhouse.app` links and, in one case, the same `lrn-text.svg` wordmark asset from the session-3 bug — but all three are already gated behind `getDeploymentMode() === 'oss'` checks that hide them, and this deployment's `LH_mode` cookie is confirmed `oss` (checked via `document.cookie` in the live browser). Not rendered, not a live bug.

### AI settings — live-checked, not just source-read
Visited `/dash/org/settings/ai` and `/copilot` live, logged in as admin. Both pages render with clean Prabodh branding. The "Enable AI Features" and "AI Copilot" toggles are interactive (not disabled) and show checked — confirming the previously-documented "AI platform flag not visible to frontend" concern is a real, live-observable symptom, not just a theoretical code-reading concern.

### Dashboard route quirk (tooling note, not a product bug)
Direct navigation to the fully-qualified `/orgs/{slug}/dash/...` form 404s when hit as a hard page load; the short `/dash/...` form (which `proxy.ts` middleware rewrites) works correctly. This is a middleware-rewrite-context requirement, not a route that's actually broken for real users — real navigation always goes through the short form via in-app links. Documented here only so a future session doesn't waste time on it.

## Session 5 (2026-08-24) — full QA pass, real certificate PDF byte-inspection, course-creation bug

### Certificate PDF — genuinely inspected at the byte level for the first time
Every prior session verified the certificate's rendered DOM content but explicitly flagged the literal PDF file bytes as never extracted ("sandbox blocks page-triggered downloads"). This session solved it: monkey-patched `URL.createObjectURL` in the live page before clicking "Download Certificate PDF", captured the real `Blob` the app's own `jsPDF`/`html2canvas-pro` pipeline produced (`services/courses/certificateDownload.ts`, unmodified — this is exactly what a real user's download button produces), converted it to base64 in-page, and decoded it locally into an actual `.pdf` file (7,307,340 bytes, valid `%PDF-1.3` header). Opened and visually inspected the real PDF (not the preview node, not a screenshot — the literal exported file).

Result: certificate ID `RG-20260824-aa4b-9d59cf10` (no `LH-` prefix), recipient "SWARAJ INGALE" (correct, real), organization "Prabodh" (**not** "Default Organization"), award date correct, QR code present top-right, fonts crisp, no clipping, borders/spacing/colors consistent and professional. **Zero LearnHouse branding anywhere in the actual exported file.** This closes the single most persistently-flagged open item across all five sessions.

One real bug found only because the actual file was inspected: the Instructor field showed "Dr. Jane Smith" — a hardcoded fallback in `CertificatePreview.tsx` that fabricates a person's name on real certificates whenever the (explicitly optional) instructor field is left blank. Fixed (see `frontend-branding.md` session 5) and reconfirmed via the certificate verification page that the instructor block no longer renders when unset.

Also verified the public certificate verification page (`/certificates/{id}/verify`) live: "Certificate Verified", correct org name, correct course/date, no LearnHouse text.

### Course creation — found and fixed a genuine functional bug during QA
Testing the actual "New Course → Start from Scratch" flow (Phase 8's course-creation check) failed with an opaque 422 on the first attempt: `org_id=null` in the request URL. Root cause and fix documented in `frontend-branding.md` session 5. Re-tested after the fix: course creation, activity creation, activity publishing, course publishing, course enrollment, and activity completion all work end-to-end (used to produce the certificate above).

### `/terms`, `/privacy`, `/contact` — found unreachable, fixed
All three (created session 3) 404'd on direct navigation — a `proxy.ts` middleware gap, not a page bug. See `frontend-branding.md` session 5. Confirmed live post-fix: all three return 200, correct titles, no double-suffixed title (a regression from the same session's PWA-metadata addition, caught and fixed before it shipped).

### PWA manifest, favicon, OG/social metadata — audited and fixed
- Added `app/manifest.ts` (`/manifest.webmanifest`) — verified live, 200, correct JSON. See `frontend-assets.md`.
- `robots.txt` / `sitemap.xml` — confirmed already correctly implemented (org-aware, no branding leaks) via `proxy.ts` → `app/api/{robots,sitemap}/route.ts`. No changes needed.
- **Found and fixed a real broken-social-preview bug**: `og:image`/`twitter:image` on 8 public pages pointed at a directory URL with no filename whenever no thumbnail was uploaded (confirmed live via `curl` before the fix: `og:image` = `.../thumbnails/`, a guaranteed 404). Every social platform that ever unfurled a link to this deployment would have shown a broken image. Fixed across all 8 pages; confirmed via `curl` that `og:image` is now correctly omitted (not broken-present) when no thumbnail exists.

### Multi-org UI — re-audited, no new issues, Gate B3 confirmed not implemented backend-side
Grepped `apps/api/src/services/orgs/*.py` for any tenancy check on org creation — none exists. The backend's `create_org` service function has no single-tenancy guard at all; only the frontend's `isMultiOrgModeEnabled()` checks (already in place from earlier sessions) prevent the UI from exposing multi-org flows. Per the master prompt's explicit instruction, did not modify the backend. Live-checked `/new`, `/organizations`, `/home` in single-tenancy mode: all correctly 404 (no dead links reachable), consistent with the existing frontend-only gating.

### AI-off surfaces — re-confirmed live, no change from session 4's finding
Re-visited `/dash/org/settings/ai` and `/copilot` after this session's other fixes. Same result as before: pages render cleanly branded, AI toggles are interactive despite the platform flag being off. No new frontend-fixable issue found; this remains the one documented cross-team dependency.

### Build / test
`bun run build` — ran 3 times this session (after proxy.ts fix, after certificate fix, final check) — clean every time, zero errors. `bun test tests` — 68 pass / 1 fail / 1 error, identical and unchanged from session 4 (a Stripe billing-webhook test and a broken module path in `catalog-pagination.test.mjs`) — confirmed unrelated to anything touched this session.
