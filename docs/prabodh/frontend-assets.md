# Frontend Assets

## Current state

`apps/web/public/` still contains only LearnHouse-branded image assets — no content was swapped this pass, because no approved Prabodh assets exist yet (see `frontend-open-questions.md` #1). What *was* done: every `alt` attribute referencing these images in code was corrected to say "Prabodh" (or removed where the link/text around it was removed entirely), so accessibility text and hover tooltips are accurate even though the pixels underneath are still LearnHouse's.

## Inventory (unchanged from the original audit)

| File | Used by (confirmed this pass) |
|---|---|
| `learnhouse_logo.png`, `black_logo.png`, `dashLogo.png` | Various dashboard/auth surfaces — not all individually re-confirmed this pass |
| `favicon.ico` | Browser tab icon — not touched, no PWA manifest found either (see below) |
| `lrn.svg` | Watermark, `(withmenu)` org footer, `/home`, `/new` top bar — all confirmed live this pass |
| `lrn-dash.svg` | Admin sidebar, dashboard sidebar, onboarding welcome modal — all confirmed live this pass |
| `lrn-text.svg` | `Watermark.tsx` floating badge |
| `learnhouse_ai_black_logo.png`, `learnhouse_ai_simple*.png`, `lrnai_icon.png` | AI-related surfaces — not individually confirmed this pass |
| `UNI_LOGO.png`, `theclassroom.png` | Were used by the onboarding "LearnHouse University" / "The Classroom" cards, which this pass **removed** (see `frontend-branding.md`) — these two files are now unreferenced in code. Left on disk (not deleted) per the "don't rename/remove assets casually" guidance. |
| `auth-default.png` | Auth illustration background for the org-less apex login/signup — 8MB, not a branding issue but worth flagging as a performance concern for whoever does the real asset swap. |

## Required from design before Wave 1's asset swap can happen

Logo (light + dark variants, SVG preferred), favicon + app icon set, Open Graph image (1200×630), brand color palette (hex values), typography choice. None of these exist in the repo. Once supplied, swap file **contents** at the existing paths — the spec explicitly recommends against renaming on the first pass, and nothing in this pass's code changes depends on the current filenames changing.

## PWA manifest

**Added this pass**: `apps/web/app/manifest.ts` (Next.js metadata-route convention, served at `/manifest.webmanifest`, linked from `app/layout.tsx`). Declares `name`/`short_name: "Prabodh"`, a neutral (not "the" official) `theme_color`/`background_color`, and points its one icon entry at the existing `/favicon.ico` — deliberately not at any of the `learnhouse_*.png` files, since a PWA icon is a genuine user-visible surface (the actual home-screen icon a user would see after installing), not just an alt-text/hygiene concern. Verified live: `GET /manifest.webmanifest` returns 200 with correct JSON.

**Still open**: `/favicon.ico` itself is still LearnHouse's real icon pixels (unavoidable without a real asset), and no dedicated 192×192/512×512 PNG icon set exists for a proper installable PWA — the manifest's single low-res `.ico` reference is a placeholder, not a finished PWA icon set. Needs real design assets before this is actually launch-ready.

## Sitemap / robots.txt

Already implemented and working correctly before this pass, via `apps/web/proxy.ts` (routes `/sitemap.xml` and `/robots.txt` to `apps/web/app/api/sitemap/route.ts` and `apps/web/app/api/robots/route.ts`, org-aware). Verified live this pass (`curl http://localhost:3000/robots.txt` and `/sitemap.xml`) — both work, no LearnHouse references, correctly disallow `/dash/`, `/admin/`, `/auth/`, `/editor/`, `/api/`. (A redundant `app/robots.ts`/`app/sitemap.ts` pair was drafted and then deleted after discovering the existing implementation — noted here so a future pass doesn't duplicate the work.)
