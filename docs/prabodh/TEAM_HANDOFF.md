# Prabodh — Team Handoff

This is the single entry point for a new developer or reviewer picking up this project. It summarises what's real, what's verified, and what's still open — cross-referencing the detailed docs in this folder rather than repeating them in full.

## 1. Current architecture

- **Frontend**: `apps/web` — Next.js (App Router), Tailwind. Single-tenancy mode (`LEARNHOUSE_TENANCY=single`) rewrites the public root to the one default organisation via `proxy.ts` middleware.
- **Backend**: `apps/api` — FastAPI, Postgres (via SQLModel/pgvector for embeddings), Redis (sessions, rate limiting, AI credit counters, caching).
- **Collaboration service**: `apps/collab` — separate small service for real-time features; not touched by this project's work.
- **AI layer**: `apps/api/src/services/ai/llm` — a provider-agnostic layer built on Pydantic AI (`build_model()` in `provider.py`). Switching between Google Gemini and Anthropic Claude is a config change (`config/config.yaml`'s `ai_config.provider`), not a code change. Image generation and text-to-speech are Google-only code paths (`services/ai/image`, `services/ai/audio`) because neither Gemini-alternative currently has an equivalent API — this is a vendor capability limit, not an oversight.

## 2. Frontend work — what's actually complete

Full detail: `frontend-branding.md`, `frontend-verification.md`, `frontend-open-questions.md`, `frontend-website.md`, `frontend-assets.md`, `frontend-ai-surfaces.md`.

**Complete and live-verified**: branding across auth/dashboard/nav/course pages/404/certificates, English-only UI with the language switcher hidden, the public landing page, PWA manifest/OG/robots/sitemap, certificate generation (verified at the actual exported PDF byte level, not just the on-screen template), Terms/Privacy/Contact placeholder pages (which were found to be completely unreachable due to a middleware routing gap, then fixed).

**Explicitly not complete**:
- No backend single-org enforcement exists (checked directly in `apps/api/src/services/orgs/*.py` — `create_org` has no tenancy check). The frontend hides the UI path; nothing stops a direct API call from creating a second org.
- No baseline screenshots were captured before white-labelling started, and the Playwright e2e suite (`apps/e2e`) has never been run against this codebase.
- Real brand assets (logo, favicon, palette, typography, OG image) do not exist — every placeholder is either LearnHouse's own file (kept because renaming/fabricating pixels was out of scope) or an honest "content pending" statement.

## 3. AI work — what's actually complete

Full detail: `part2-ai-architecture.md` (the original Claude-targeted work), `part2-gemini-provider.md` (the switch to Gemini and everything verified under it).

**Live-tested with a real Gemini API key**, through either the actual browser UI or a direct backend call:
- Chat/Copilot (streaming, non-streaming)
- AI Course Creator: course-plan generation and per-activity content generation
- Full course creation from a generated plan
- Assignment generation, scenario generation (structured output)
- Magic Blocks (editor AI), Playground generation, Board generation
- RAG: course content embedding → retrieval → grounded, cited Copilot answer
- Text-to-speech / audio generation
- Embeddings (768-dim, matching the existing pgvector schema — no migration was needed)

**Not live-tested**: image generation (blocked — see below), the editor's inline AI content-assist panel (as opposed to the standalone Course Creator), and a couple of narrow AI entry points (Command Palette AI, board-canvas AI tools) that are code-reviewed but not clicked through.

**Blocked, not a bug**: image generation returns a real `429 RESOURCE_EXHAUSTED` — the configured Gemini key's free tier has zero quota for the image model specifically, while text/embeddings/TTS all have real free-tier quota on the same key.

## 4. Gemini configuration

Set in `apps/api/.env` (never committed) or `config/config.yaml`:
- `LEARNHOUSE_IS_AI_ENABLED=true` — the platform-wide switch. Previously this was read from config but enforced nowhere; it's now wired into every AI endpoint via a `require_ai_enabled` dependency.
- `LEARNHOUSE_AI_PROVIDER=google`, `LEARNHOUSE_AI_API_KEY=<your key>`
- Model tiers (`LEARNHOUSE_AI_MODEL_FAST/STANDARD/PRO`) default to `gemini-3.1-flash-lite` / `gemini-3.6-flash` / `gemini-3.1-pro-preview` respectively when unset, chosen against live Gemini pricing/availability documentation at the time. If your key's free tier doesn't have quota for the pro-tier model, override `LEARNHOUSE_AI_MODEL_PRO` — this happened during development and was fixed exactly this way (see §5).

**Claude/Anthropic is still fully supported** — set `provider: anthropic` and a Claude API key to switch back; nothing Claude-specific was removed, and a regression test asserts this.

## 5. Known bugs already found and fixed (do not re-discover these)

| Bug | Root cause | Fix |
|---|---|---|
| Course Creator failed with "internal error generating the stream" | Course-planning's "pro" model tier resolves unconditionally on this self-hosted deployment, and that model has zero free-tier quota on the configured key | `LEARNHOUSE_AI_MODEL_PRO` overridden to a model with real quota (local `.env`, not committed) |
| Course Creator's activity-content generation produced "Failed to parse content" | A shared 4096-output-token cost-control default (fine for short chat replies) silently truncated a full activity's richer JSON content mid-string | Explicit `max_tokens=16000` added at the two call sites in `courseplanning.py` that generate long-form content |
| A usage-logging line crashed every successful AI generation | `result.usage` is a property, not a method, in the installed Pydantic AI version — code called `result.usage()` | Fixed to `result.usage`; only ever surfaced by a live call, not a mocked test |
| Platform AI flag had no effect | `LEARNHOUSE_IS_AI_ENABLED` was parsed but never checked | New `require_ai_enabled` dependency on every AI router |
| An "AI disabled" check leaked config state to anonymous users | The new guard checked the platform flag before authentication | Guard now checks auth first |
| Certificates could show a fabricated instructor name | A hardcoded `'Dr. Jane Smith'` fallback in `CertificatePreview.tsx` | Removed; the instructor block is now hidden when genuinely unset |
| `og:image` broken on 8+ public pages | The thumbnail-URL helper returned a directory path with no filename when no image was set | Only emit `og:image`/Twitter image tags when a real file exists |
| Terms/Privacy/Contact pages were completely unreachable (404) | `proxy.ts` middleware had no pass-through rule for these three top-level routes | Added the pass-through |

## 6. Local setup

See the root `README.md`. In short: Docker for Postgres/Redis, `uv run python app.py` for the API, `bun run dev` for the frontend. On Windows, do not rely on the bundled CLI's own orchestration command — it has a documented PATH-detection bug; run the two services directly.

## 7. How another developer can continue

1. Read this file, then the specific `frontend-*.md` / `part2-*.md` doc for the area you're touching — each one states what's verified vs. assumed.
2. Before changing AI behaviour, read `part2-ai-architecture.md`'s note on the provider-agnostic design — don't hardcode a vendor SDK call; go through `services/ai/llm`.
3. Before changing branding, check `frontend-open-questions.md` first — several "obvious" fixes (e.g. renaming asset files) are deliberately deferred, with the reasoning stated.
4. Run the relevant test suite before and after your change (`pytest src/tests` from `apps/api`, `bun test tests` from `apps/web`) and compare against the pass counts in the root README — any new failure is yours to explain.

## 8. Testing status

See root `README.md` §Testing for exact current pass/fail counts. No baseline existed before white-labelling began, so regression claims for that work rely on live re-verification each session, documented in `frontend-verification.md`, not a diff against a captured baseline.

## 9. Important environment variables

See `apps/api/.env.example` and `apps/web/.env.example` for the full, documented list. No file in this repository contains a real secret value.

## 10. Security notes

- No API key, password, or token is committed anywhere in this repository — verified by scanning every changed file for common secret patterns before this handoff was prepared.
- `.env` / `.env.local` are gitignored at both the repository root and inside `apps/api`/`apps/web`; `apps/api/.venv`, `__pycache__`, and uploaded content under `apps/api/content/` are also gitignored.
- The AI enable/disable flag and the AI credit/rate-limit system were both re-verified live under real traffic during this work (see §5).
- No database migration, schema change, or destructive database operation was performed at any point.
