# Frontend Branding — What Was Changed

This file lists every file touched during the Prabodh frontend white-labelling pass on branch `prabodh/whitelabel`, and why. It reflects the actual implemented state, not a plan.

## Global metadata / titles

- `apps/web/app/admin/layout.tsx` — admin panel title/template: `LearnHouse Admin` → `Prabodh Admin`.
- `apps/web/app/orgs/[orgslug]/dash/layout.tsx` — dashboard title: `LearnHouse Dashboard` → `Prabodh Dashboard`.

## Authentication

- `apps/web/app/auth/{forgot,login,reset,signup,verify-email}/page.tsx` — all `<title>` metadata (both the org-less-apex branch and the `${org?.name || 'LearnHouse'}` fallback branch) changed to say Prabodh.
- `apps/web/app/auth/login/login.tsx`, `apps/web/app/auth/signup/signup.tsx` — hardcoded `defaultValue` fallback for the auth illustration's title text.
- `apps/web/app/auth/layout.tsx` — a stale code comment referencing "LearnHouse branding".
- `apps/web/components/Auth/AuthBrandingPanel.tsx`:
  - Hid LearnHouse's own top-bar logo/link on self-hosted OSS/EE deployments (previously only hidden for `plan === 'enterprise'`; see "Watermarks" below for the same pattern elsewhere).
  - `alt="LearnHouse"` → `alt="Prabodh"` on the fallback org-icon image (image asset itself unchanged — no approved Prabodh asset exists yet, see `frontend-open-questions.md`).
  - No-org apex fallback title: `'Welcome back to LearnHouse.'` → `'Welcome back to Prabodh.'`
  - Org-name fallback heading: `{org?.name || 'LearnHouse'}` → `{org?.name || 'Prabodh'}`.
- `apps/web/components/Auth/AuthMobileHeader.tsx` — same `alt` and org-name-fallback fixes as above.
- `apps/web/locales/en.json` (`auth.*` keys) — `terms_text`, `image_title_login`, `image_title_signup` all changed from LearnHouse to Prabodh.

## Legal / copyright footer

- `apps/web/components/Footers/LegalFooters.tsx` — `"© {{year}} LearnHouse, Inc."` → `"© {{year}} Prabodh"` (both the component's hardcoded `defaultValue` and the matching `en.json` `common.copyright` key). Deliberately used just "Prabodh", not "Prabodh, Inc." — no evidence a corporate entity by that name exists, and inventing one would violate the no-unsupported-claims rule.
  - **Not changed**: the fallback Terms of Service / Privacy Policy URLs, which still point at `learnhouse.io`. See `frontend-open-questions.md` — this needs real Prabodh legal content, which this pass cannot invent.

## Navigation / menus (dashboard + org chrome)

- `apps/web/components/Objects/Menus/OrgMenu.tsx` and `apps/web/components/Dashboard/Menus/DashLeftMenu.tsx` and `apps/web/components/Dashboard/Menus/DashMobileMenu.tsx` — removed the "Documentation" (`docs.learnhouse.app`), "Website" (`learnhouse.app`), and "Discord" (`discord.gg/learnhouse`) help-menu links in all three menu surfaces (desktop dropdown, desktop hover-menu, mobile panel). Kept the in-app "Report Issue or Feedback" item, which has no external dependency. Removed now-unused `Book`/`Globe`/`DiscordIcon` icon imports where they became dead.
- `apps/web/components/Security/HeaderProfileBox.tsx`, `apps/web/components/Dashboard/Menus/DashLeftMenu.tsx`, `apps/web/app/home/home.tsx`, `apps/web/components/Dashboard/Menus/DashMobileMenu.tsx` — added `AVAILABLE_LANGUAGES.length > 1` guards around every language-switcher submenu, so the now-single-language list doesn't render a pointless one-item dropdown (per Frontend Track §7.3's explicit requirement). `apps/web/components/Utils/LanguageSwitcher.tsx` (the shared component used elsewhere) got the same guard at its root.
- `apps/web/components/Admin/AdminLeftMenu.tsx`, `apps/web/components/Dashboard/Menus/DashLeftMenu.tsx`, `apps/web/components/Dashboard/Onboarding/WelcomeModal.tsx` — `alt="Learnhouse logo"` / `alt="LearnHouse"` → Prabodh, on the small `/lrn-dash.svg` icon used in the admin/dashboard sidebars and the onboarding modal (image content unchanged — see open questions).
- `apps/web/app/home/home.tsx`, `apps/web/app/(hub)/new/page.tsx` — `alt="LearnHouse"` → `alt="Prabodh"` on the `/lrn.svg` mark.

## Onboarding

- `apps/web/components/Dashboard/Onboarding/OnboardingBar.tsx` — removed the "LearnHouse University" (`university.learnhouse.io`) and "The Classroom" (`classroom.learnhouse.io`) external resource cards from the "Learn & grow" onboarding step. The step's completion button (`Done` → `completeStep('teach_the_world')`) was left untouched, so the onboarding flow's logic and completion tracking still work.
- `apps/web/locales/en.json` — `onboarding.steps.teach_the_world.description` rewritten (the old copy promised "resources to get the most out of LearnHouse" that no longer exist on this screen); `onboarding.welcome.title`: `"Welcome to LearnHouse"` → `"Welcome to Prabodh"`; `common.feedback_description` rebranded.

## Watermarks (see also `frontend-open-questions.md`)

LearnHouse's own "Made with LearnHouse" promotional watermark/link exists in two places, both gated on deployment mode (`ee`/`oss`/other) and org plan. Both only excluded `'ee'` mode from showing it — not `'oss'`, which is what this deployment actually reports (`LH_mode=oss`, confirmed live via cookie). That meant the ad was genuinely showing on every page of this self-hosted instance. Fixed to also exclude `'oss'`, matching a pattern already used elsewhere in this exact codebase (`services/config/config.ts`'s upgrade-URL helper already treats `oss`/`ee` the same way):
- `apps/web/components/Objects/Watermark.tsx` — the floating "Made with [logo]" badge.
- `apps/web/app/orgs/[orgslug]/(withmenu)/layout.tsx` — a second, smaller `lrn.svg`-icon-linking-to-`learnhouse.app` instance in the org footer.
- `apps/web/components/Dashboard/Pages/Org/OrgEditOther/OrgEditOther.tsx` — the org settings toggle that controls/describes this watermark. Fixing the two render sites above without touching this settings panel would have left the toggle showing "Watermark is always shown on the free plan" (a message that would now be simply false) with a still-enabled, clickable switch. Added the same OSS exclusion here, with a new copy string for the OSS case (disabled toggle + "Hidden on this self-hosted deployment").
- `apps/web/locales/en.json` — `dashboard.organization.settings.watermark_label` / `watermark_desc` rebranded from "LearnHouse" wording to "Prabodh" wording (these still show for actual SaaS-free-tier orgs, which is a real scenario the toggle still serves).

## Course import (flagged, not changed)

`apps/web/locales/en.json` contains `courses.import.import_learnhouse` / `import_learnhouse_description` ("Import LearnHouse Course" / "Import a course exported from LearnHouse") and a duplicate set under a different namespace (`learnhouse_courses` / `learnhouse_format` / `learnhouse_info`). This describes a real file-interop feature (importing a `.zip` package this app's own export produces), not a LearnHouse-vs-Prabodh identity question. Left unchanged — see `frontend-open-questions.md` for why.

## Multi-organisation UI — see `frontend-verification.md` for the full writeup

- `apps/web/app/(hub)/new/page.tsx` — the entire org-creation wizard (use-type → usage → plan → create → Stripe checkout) had **no tenancy gating at all** and was reachable directly by URL regardless of single-org mode. Added a redirect to the single default org when `!isMultiOrgModeEnabled()`.
- `apps/web/app/home/home.tsx` — this route is LearnHouse's authenticated "choose your organization" picker (confirmed live: title "Your Organizations", subtitle "Choose an organization to continue"), also completely unguarded. Added the same tenancy-based redirect into the single default org, and made its existing "org-less user → `/new`" redirect only fire in multi-org mode (avoids a redirect loop with the fix above).
- Confirmed **already correctly gated** by existing `isMultiOrgModeEnabled()` checks in this codebase (no changes needed): the "Organizations" switcher submenu, "My Organizations"/apex-home link, "Billing" link, and the free-plan SaaS upgrade box, all in `HeaderProfileBox.tsx` / `DashLeftMenu.tsx`.

## English-only

- `apps/web/lib/languages.ts` — `AVAILABLE_LANGUAGES` trimmed from 22 entries to just English, per Frontend Track §7.3. The 21 locale JSON files under `apps/web/locales/` were **not** deleted (left in place, unreachable, per the spec's explicit instruction).
- Language-switcher hide-when-single-language behavior — see "Navigation / menus" above.

## Session 2 additions (2026-08-24) — organisation name, certificate, and a second full sweep

See `frontend-open-questions.md`'s "RESOLVED this session" section for the organisation-name fix and the real certificate-generation walkthrough (both non-trivial and written up there rather than duplicated here).

A second, broader sweep for `alt="LearnHouse"` / hardcoded "LearnHouse" / hardcoded `learnhouse.io` across all of `apps/web` (not just the explicitly-named hotspots) turned up real, previously-missed instances:

- **`apps/web/app/admin/login/page.tsx`** — the superadmin login screen's actual `<h1>` read "LearnHouse Admin" (the earlier pass only fixed this route's `<title>` metadata, not the visible heading). Now "Prabodh Admin".
- **`apps/web/components/Emails/LearnHouseEmail.tsx`** — the shared transactional-email template (used by `services/emails/resend.ts` for real emails) was loading a **live remote LearnHouse logo image from `https://www.learnhouse.io/...`** into every email, with `alt="LearnHouse"`, plus a footer reading "LearnHouse — the open-source learning platform." Replaced the remote image with a plain text "Prabodh" wordmark (no fake logo invented, no external dependency on a competitor's domain) and reworded the footer.
- **`apps/web/services/emails/transactional.ts`** — the actual welcome email sent to every new signup had subject "Welcome to LearnHouse 👋", heading "Welcome to LearnHouse!", and a "Get started" button linking to `https://www.learnhouse.io/home`. Fixed the subject/heading text and changed the link to use the app's own configured domain (`getLEARNHOUSE_HTTP_PROTOCOL_VAL()` + `getLEARNHOUSE_DOMAIN_VAL()`, both already-existing config helpers) instead of a hardcoded LearnHouse URL.
- **`apps/web/components/Dashboard/Pages/Users/Security/OrgSignInMethods.tsx`** — the "central session sharing" security setting's label and hint both hardcoded "learnhouse.io" as the platform domain in user-visible copy. Since this describes real behavior tied to whatever domain the instance is actually configured for, hardcoding the wrong domain was factually incorrect for any self-hosted deployment, not just a branding nit. Now interpolates the same `getLEARNHOUSE_DOMAIN_VAL()` helper.
- **A fifth instance of the "hide LearnHouse branding unless enterprise plan" bug** (missing the `oss` deployment-mode exclusion already applied to `Watermark.tsx`, `AuthBrandingPanel.tsx`, `(withmenu)/layout.tsx`, and `OrgEditOther.tsx` in the previous session): `apps/web/components/Dashboard/Pages/Org/OrgEditBranding/AuthBrandingTab.tsx` (the auth-branding settings live preview). Fixed identically.
- **Ten more `alt="LearnHouse"` / `alt="Learnhouse"` instances**, all on the `/lrn.svg` or `/lrn-dash.svg` marks, found and fixed: `EmbedActivityClient.tsx` (×2, including the "activity not supported" fallback icon), `PlaygroundEditor.tsx`, `DashMobileMenu.tsx` (×2), `OrgMenu.tsx`, `BoardTopBar.tsx`, `Editor.tsx`, plus two that the previous session's edits to the *surrounding* logic in `(withmenu)/layout.tsx` and `AuthBrandingPanel.tsx` had missed on the `alt` attribute itself.
- **`apps/web/app/home/home.tsx`** — two more instances of a "Powered by LearnHouse" footer badge (separate from the ones fixed in the previous session), now "Powered by Prabodh".
- **`apps/web/locales/en.json`** — the orphaned `embed.powered_by` key ("Powered by LearnHouse") fixed for consistency even though it's not currently wired to any rendered component (confirmed via grep — dead but harmless to leave wrong).

All of the above were re-verified with a follow-up sweep for `alt="LearnHouse"` (zero remaining) and a broader pattern search for "Made with/Powered by/University/Classroom/, Inc/.io" strings (remaining hits are either the 21 untouched non-English locale files, orphaned unused keys, or genuine internal/technical comments and domain-detection logic).

## Session 3 (2026-08-24) — the actual browser-visible bug, plus Terms/Privacy/Contact and course-import labels

A user-reported screenshot showed "learnhouse" still visible top-left on `/courses` despite two prior sessions of string-level fixes and clean grep sweeps. Root cause, found only by opening the real page in a browser and reading the DOM (not by grepping source):

- **`apps/web/components/Objects/Menus/OrgMenu.tsx`** — the `LearnHouseLogo` sub-component (used as the top-nav logo fallback whenever no custom org logo is set — i.e. always, for this deployment) rendered `/lrn-text.svg`, an SVG whose `<path>` data is hand-drawn letterforms spelling "LearnHouse" as vector graphics. No amount of text search finds this — it isn't a string anywhere in the repo. Replaced with a plain "Prabodh" text wordmark, adapting to the light/dark nav background the same way the image did (`logoFilter` prop repurposed as a boolean check). Verified live across every top-level route that uses this nav: `/courses`, `/library`, `/podcasts`, `/communities`, `/playgrounds`. The two sibling icon files (`lrn.svg`, `lrn-dash.svg`) were checked and confirmed to be pure abstract geometric marks with no letterform paths — safe to keep using as-is.

- **`apps/web/components/Footers/LegalFooters.tsx`** — Terms/Privacy fallback URLs changed from `https://www.learnhouse.io/{terms,privacy}` to relative `/terms` and `/privacy`. New placeholder pages `apps/web/app/terms/page.tsx` and `apps/web/app/privacy/page.tsx` state plainly that real content is pending (no legal text invented).
- **`apps/web/components/Objects/StyledElements/Error/ErrorActions.tsx`** — the error-page "Contact support" fallback changed from `mailto:support@learnhouse.io` to `/contact`, a new placeholder page (`apps/web/app/contact/page.tsx`) with the same honest-pending-content approach.
- **`apps/web/locales/en.json`** — `courses.import.{learnhouse_courses,learnhouse_description,learnhouse_format,learnhouse_info,import_learnhouse,import_learnhouse_description}` all rebranded to Prabodh, after actually opening the "Import Course" dialog in the browser and confirming these are display labels, not a technical format name a user needs to see (unlike "SCORM Package," left alone). The internal `'learnhouse'` TypeScript union-type value used for switch-case branching in `ImportTypeSelector.tsx` was left untouched — only the four display strings changed.

## Session 4 (2026-08-24) — production-bundle sweep + public website

Built the public website (see `frontend-website.md`) and found, by grepping the *rebuilt production bundle* rather than source or rendered pages, 9 more genuine English leaks no browser click-through had landed on: `locales/en.json` (`university`, `learnhouse_university`, `website`, `createOrg.testHint`), `OrgEditAPIAccess.tsx`'s hardcoded `mailto:hello@learnhouse.app`, `lib/errors/catalog.ts`'s stale-build toast, `services/billing/emails.ts`'s purchase email, `services/emails/resend.ts`'s default `From:` header, `services/emails/transactional.ts`'s fallback recipient, the `(hub)` pricing pages' "Talk to us" link, and the course-page SEO fallback title. Full list in `frontend-open-questions.md`'s "RESOLVED — session 4" section. Re-verified via a second bundle grep after rebuild: zero English matches remain.

## Session 5 (2026-08-24) — QA pass surfaced three real bugs beyond branding

Actually exercising the product (not just grepping/reading code) per the Frontend Track's QA requirement surfaced bugs that string-search could never catch, since none of them contain the word "learnhouse":

- **`apps/web/proxy.ts`** — `/terms`, `/privacy`, and `/contact` (created session 3) were **completely unreachable**: no route in the middleware's explicit top-level-path allowlist covered them, so they fell into the tenant-scoped catch-all, which rewrote them to `/orgs/{slug}/terms` — a route that doesn't exist — and 404'd every time. Every prior session's "verified" check had only confirmed the `href` attribute on login/signup pointed at `/terms`/`/privacy`, never actually followed the link. Added an explicit pass-through (matching the existing pattern for `/board/`, `/health`, etc.) so these three routes bypass the org rewrite. Confirmed live: all three now return 200 with correct content.
- **`apps/web/app/layout.tsx`** — added root-level `metadata` (manifest link, `applicationName`, icons/theme-color) for the new PWA manifest (see `frontend-assets.md`). First attempt used a `title.template`, which double-suffixed every page that already builds its own complete title (`buildPageTitle()` appends "— {org name}", and this org's name is itself "Prabodh" — so `/terms` briefly showed "Terms of Service — Prabodh — Prabodh"). Fixed by dropping the template and using a plain `default` title instead — confirmed no more doubling on `/`, `/terms`, `/privacy`, `/contact`.
- **`apps/web/components/Objects/Modals/Course/Create/CreateCourse.tsx`** — course creation from "Start from Scratch" failed with an opaque 422 ("Input should be a valid integer") when submitted quickly. Root cause: `orgId` is fetched asynchronously in a `useEffect` after the modal mounts, but the submit button and handler had no guard against submitting before that fetch resolved, sending the literal string `"null"` as `org_id` to the backend. Fixed by disabling the submit button until `orgId` loads and adding a matching guard in the submit handler. Confirmed live: course creation now works end-to-end once `orgId` has loaded (button is disabled until then).
- **`apps/web/components/Dashboard/Pages/Course/EditCourseCertification/CertificatePreview.tsx`** — the same component renders both the design-time certificate preview *and* a real issued certificate. It hardcoded `certificateInstructor || 'Dr. Jane Smith'` — meaning any real, issued certificate where the org admin left the (explicitly labeled "Optional") instructor field blank would show a fabricated person's name as fact. Confirmed by generating and byte-level-inspecting a real issued certificate PDF (see `frontend-verification.md`) before the fix — "Dr. Jane Smith" was genuinely embedded in the exported PDF. Fixed by hiding the whole instructor block when unset, rather than fabricating a name — matches the project's "do not invent business claims" rule, applied to a person's name instead of a company claim.
- **8 pages' Open Graph/Twitter image metadata** (`app/orgs/[orgslug]/(withmenu)/{page,courses,library,communities,boards,podcasts,store}.tsx`, `community/[communityuuid]/page.tsx`, `library/folder/[folderid]/page.tsx`) — when no thumbnail was uploaded, `getOrgThumbnailMediaDirectory()` still returned a URL (just pointing at a directory with no filename, e.g. `.../thumbnails/`), so the "no image" guards elsewhere in the same files never fired — every social-media crawler fetching one of these pages' `og:image` got a guaranteed-404 image URL instead of no image field at all. Fixed by only building the thumbnail URL when a real `thumbnail_image` file is actually set. Confirmed via `curl` that `og:image` is now correctly absent from the root page's meta tags when no thumbnail exists.
