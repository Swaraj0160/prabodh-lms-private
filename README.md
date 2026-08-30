# Prabodh

Prabodh is a white-labelled, single-organisation learning management platform, built on top of the open-source [LearnHouse](https://github.com/learnhouse/learnhouse) project (AGPL-3.0). It is not a from-scratch product — the underlying platform, architecture, and a large share of the codebase are LearnHouse's own work, licensed under AGPL-3.0. See `LICENSE` for the exact terms and `docs/prabodh/` for what has actually been changed on top of it.

This repository is a private handoff snapshot of the current Prabodh implementation for the project team.

## What has been implemented

### Frontend white-labelling (`apps/web`)
- LearnHouse branding replaced with Prabodh across every user-visible screen, page title, navigation element, and error/empty state that was checked (auth screens, dashboard, course pages, 404, certificates). A branding leak baked into an SVG's vector path data (not plain text) was found and fixed — a reminder that a text-only grep sweep is not sufficient on its own.
- The multi-organisation UI (org creation, org switcher, org-picker signup path) is hidden/redirected on the frontend for single-tenancy mode. **Note:** the corresponding backend enforcement (rejecting a second org at the API level) was checked and does not exist yet — this is a frontend-only gate today, not a backend security boundary.
- UI restricted to English only; the other 21 shipped locale files are left in place but unreachable, per the project's own instruction not to delete them.
- A public marketing/landing page was built using the platform's existing config-driven landing-page system, with factual, non-invented copy (no unapproved claims about the product).
- PWA manifest, `robots.txt`/sitemap, and Open Graph metadata are in place. A real bug where `og:image` pointed at a broken URL on several pages was found and fixed.
- Certificate generation and the public certificate-verification page were rebranded; a real certificate was generated through the actual product flow and the exported PDF file itself (not just the on-screen preview) was inspected byte-for-byte to confirm it was clean.
- Placeholder Terms of Service, Privacy Policy, and Contact pages exist and state plainly that real content is pending — no legal or contact information has been invented.

### AI integration (`apps/api`, Gemini)
- The backend's AI layer is provider-agnostic (built on Pydantic AI) — this abstraction pre-dates this project's AI work. **Google Gemini is the currently configured provider** for local/demo use; Anthropic/Claude support is fully retained and can be switched back to with a config-only change.
- Features implemented and exercised: chat/Copilot, AI Course Creator (course-plan generation and per-activity content generation), assignment generation, scenario generation, Magic Blocks (editor AI), Playground generation, Board generation, RAG (course-content embedding, retrieval, and grounded Q&A via Copilot), text-to-speech/audio generation.
- Image generation is implemented but is currently blocked by the configured API key having zero free-tier quota for that specific model — this is an account/billing limitation, not a code defect.
- A platform-wide AI enable/disable flag now actually has effect (previously it was read from config but never enforced anywhere).
- Cost controls (per-organisation credit reservation with refund-on-failure), rate limiting, and usage logging were already present in the codebase and were verified to still function correctly under real Gemini traffic.

## What has NOT been done

- **No production deployment.** This has only ever been run locally. No hosting account, domain, or CI/CD pipeline has been set up.
- **No backend single-org enforcement.** The API will currently accept a request to create a second organisation; only the frontend UI hides the path to do so.
- **No official brand assets.** Logo, favicon, colour palette, typography, and Open Graph image are all still placeholders or LearnHouse's own files — real design assets have not been supplied.
- **No approved marketing copy or legal text.** The public website's copy is deliberately generic and factual; Terms/Privacy pages are placeholders.
- **No baseline UI screenshots or Playwright end-to-end run** were captured before white-labelling started, and the e2e suite (`apps/e2e`) has not been run against this codebase.

See `docs/prabodh/TEAM_HANDOFF.md` and the other files in `docs/prabodh/` for the full, itemised status of every area, including what was actually live-tested versus what was only code-reviewed.

## Local development setup

Prerequisites: Node 18+, Python (pinned per `apps/api/pyproject.toml`), [`uv`](https://github.com/astral-sh/uv), [`bun`](https://bun.sh), and Docker (for Postgres + Redis).

```bash
# 1. Start Postgres + Redis (and, if used, the Cloudflare tunnel) via your existing
#    Docker setup for this project.

# 2. Backend
cd apps/api
cp .env.example .env      # fill in real values — see below
uv run python app.py      # http://localhost:1338

# 3. Frontend (separate terminal)
cd apps/web
cp .env.example .env.local
bun install
bun run dev                # http://localhost:3000
```

On Windows, the bundled `learnhouse` CLI's own dev-orchestration command has a known PATH-detection issue and does not reliably start both services — running `apps/api` and `apps/web` directly, as above, is the confirmed-working path in this environment.

### Environment variables

Full, documented templates are provided at `apps/api/.env.example` and `apps/web/.env.example` — copy them and fill in real values locally. **Never commit a real `.env`/`.env.local` file.** At minimum you will need:

- A JWT signing secret for auth (`LEARNHOUSE_AUTH_JWT_SECRET_KEY`)
- A Postgres connection string and a Redis connection string
- To enable AI features: `LEARNHOUSE_IS_AI_ENABLED=true`, `LEARNHOUSE_AI_PROVIDER=google`, and a real Gemini API key in `LEARNHOUSE_AI_API_KEY` — AI stays off by default until these are set

No API key, password, or other secret value is stored anywhere in this repository.

## Testing

- Backend (`pytest`, run from `apps/api`): last verified at 4,466 passing / 13 failing / 29 skipped. The 13 failures are pre-existing and environment-dependent (an SSRF check rejecting a test URL in this network, storage-configuration-dependent tests, and one Windows path-separator assertion) — not caused by any Prabodh-specific change.
- Frontend (`bun test`, run from `apps/web`): last verified at 68 passing / 1 failing / 1 error, both pre-existing and unrelated to this project's changes.
- A dedicated live-Gemini test suite exists (`apps/api/src/tests/services/test_llm_gemini.py`) — it is skipped automatically unless a real Gemini key is configured, so it never requires network access in CI.
- Frontend production build (`bun run build`) passes cleanly.

## Repository / branch notes

This repository was packaged from the working tree of the project's implementation branch. See `docs/prabodh/TEAM_HANDOFF.md` for exactly what state it reflects and how to pick up the remaining work.
