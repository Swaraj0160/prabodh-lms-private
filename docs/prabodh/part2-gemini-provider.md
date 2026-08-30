# Part 2 — Gemini as the Current Active Provider

Companion to `part2-ai-architecture.md` (which documents the original Claude/Anthropic Part 2 work) and `part2-ai-verification.md`. This file documents the subsequent decision to run Gemini as the active provider for local/demo development, and exactly what changed and what didn't.

## Why Gemini, and why this doesn't contradict the Part 2 spec

**The original Part 2 specification targets Claude (Anthropic) as the production provider.** That work is complete and untouched — see `part2-ai-architecture.md`. Gemini was subsequently chosen as the **current active provider for local/demo development**, specifically because a Gemini free-tier API key is available for this phase and a paid Anthropic key is not yet provisioned. This is a deployment/environment decision, not a retraction of the Claude work, and not a claim that Gemini satisfies the original Claude-specific requirement — it doesn't; it's a separate, explicit choice for right now.

This was possible with a **config-only change** — no rewrite — precisely because the Part 2 Claude work built (and correctly kept) a provider-agnostic architecture: `src/services/ai/llm/provider.py`'s `build_model()` already had a `provider == "google"` branch (in fact `"google"` was already the code-level `DEFAULT_PROVIDER`, kept for backward compatibility with the wider LearnHouse codebase's original Gemini-only history). Switching required:
1. `config/config.yaml`: `provider: "anthropic"` → `provider: "google"`.
2. `src/services/ai/llm/tiers.py`: the tier-default lookup, previously a single hardcoded Claude-only dict, restructured into **per-provider** default dicts (`_GEMINI_TIER_DEFAULTS`, `_CLAUDE_TIER_DEFAULTS`) selected by whichever provider is actually configured. **Both are kept.** Nothing Claude-specific was deleted — see "Claude support" below.

No other code changed. `require_ai_enabled`, cost controls, rate limiting, usage logging, the frontend AI-flag exposure — all provider-agnostic already, all untouched.

## Current Gemini model tiers

Verified via live web research against `ai.google.dev`'s current models/pricing documentation (August 2026) — not guessed, not carried over from stale training knowledge. Findings, with sources:

- **Gemini 2.0 family: confirmed shut down.** Do not use.
- **Gemini 2.5 family**: sources disagreed on exact sunset status — one indicated an October 2026 shutdown is announced, another showed it still listed as available. Given the ambiguity and the imminent date either way, **not selected** for text-generation tiers (see the one deliberate exception, image/audio, below).
- **Gemini 3 family: current generation, confirmed via the official pricing page.**

| Tier | Model | Free tier | Rationale |
|---|---|---|---|
| fast | `gemini-3.1-flash-lite` | Yes | Cheapest current model ($0.25/$1.50 per 1M tokens in/out); titles, follow-ups, magic blocks, playground/board generation — low-latency interactive tools |
| standard | `gemini-3.6-flash` | Yes | Current-generation Flash; cheaper per-token than the 3.5 Flash it supersedes ($0.75/$3.75 vs $1.50/$9.00); chat, RAG, planning/blocks on free/standard plans |
| pro | `gemini-3.1-pro-preview` | **No** | Google's strongest reasoning model; no free tier is offered for it (by Google's own design) — this happens to align with the tier's existing "Pro-plan orgs only" gating, so no paid usage is possible on a free-tier key regardless |

**"-preview" caveat, documented in `tiers.py` and `config.yaml`**: `gemini-3.1-pro-preview` and other preview-suffixed models can be allowlist-gated or capacity-limited on some keys/projects (confirmed via Google's own developer forum — multiple threads requesting allowlist access to 3.1-series models on Vertex AI specifically). If it 404s/429s persistently for your key, override `LEARNHOUSE_AI_MODEL_PRO` with `gemini-3.5-flash` (paid, no allowlist reports found) until access is confirmed. This is a genuine, sourced risk, not hypothetical — flagged rather than silently assumed away.

**Image and audio/TTS generation defaults were deliberately left unchanged** (`gemini-2.5-flash-image`, `gemini-2.5-flash-preview-tts`) rather than "upgraded" to the newer Gemini 3 image models (`gemini-3.1-flash-image` / `gemini-3-pro-image`, "Nano Banana 2/Pro"). Research confirmed these newer image models require allowlist access on Vertex AI and multiple developers report persistent 404s despite nominal GA status — upgrading the default risked silently breaking a currently-working feature for an unverified, access-gated replacement. This is documented in `image/generator.py`'s existing comments and `config.yaml`; override `LEARNHOUSE_AI_IMAGE_MODEL` once your project's access to the newer models is confirmed.

## Feature-by-feature Gemini support

| Feature | Gemini support | Model/tier | Notes |
|---|---|---|---|
| Chat/Copilot | Yes — text | standard | Via provider-agnostic layer, unchanged code |
| Editor AI assist | Yes — text | standard | Same |
| Magic blocks | Yes — text | fast | Same |
| RAG / course copilot | Yes — text + embeddings | standard (chat) | Embeddings now work out-of-the-box with the same `api_key` (provider=google) — no separate `embedding_provider` override needed, unlike the Anthropic path which required one |
| Quiz generation | Yes — structured text | resolved per org/plan | Unchanged |
| Scenario generation | Yes — structured text | resolved per org/plan | Unchanged |
| Assignment generation | Yes — structured text | resolved per org/plan | Unchanged |
| Course planning | Yes — text | standard/pro by plan | Unchanged |
| Playground generation | Yes — text | fast | Unchanged |
| Boards playground generation | Yes — text | fast | Unchanged |
| Image generation | Yes — native Gemini capability | `gemini-2.5-flash-image` (unchanged) | Already Google-only before this pass; now doubly natural since Gemini is the main provider too |
| Audio / TTS generation | Yes — native Gemini capability | `gemini-2.5-flash-preview-tts` (unchanged) | Same |
| Captions / transcription | Yes — Gemini supports native audio input | provider-agnostic `generate()`, standard tier | **This is the one feature whose expected behavior flips between providers** — Claude cannot accept audio input at all, so this would fail under `provider: anthropic`; it's expected to work under the current `provider: google`. Updated the module's docstring accordingly. **Not live-tested either way** (no key) — documented as expected-per-capability, not observed. |

No feature claims support it doesn't have. Where a claim is "expected, not observed," that's stated explicitly (see "Live Gemini test" below).

## Embeddings under Gemini

Gemini has a native embeddings API and it's already correctly wired (`src/services/ai/llm/embeddings.py`, unchanged code — this file was already provider-aware before the Gemini switch). With `provider: google` and `api_key` set, `embed_query()`/`embed_documents()` use `gemini-embedding-001` by default (768-dim, matching the existing pgvector column — no migration needed) and the **same single API key** already covers this, with no `embedding_provider` override required. This is simpler than the Anthropic path (which required a second, separate embeddings-capable credential since Anthropic has none).

## Cost controls — unchanged, still fully in effect

Nothing about the existing cost-control work was touched or weakened:
- Per-org atomic credit reservation (`reserve_ai_credit`) with refund-on-failure — provider-agnostic, unchanged.
- Per-user (30/min) + per-org (120/min) rate limiting (`enforce_ai_rate_limit`) — unchanged.
- The 4096-token default output cap added in the Claude pass (`client.py`'s `DEFAULT_MAX_OUTPUT_TOKENS`) — unchanged, applies identically regardless of provider.
- Structured per-request usage logging (`client.py`'s `_log_usage`) — unchanged; logs model name, feature, input/output tokens for every request, Gemini included.

**Free-tier cost note**: Gemini's free tier means $0 actual spend during this phase, but the credit-reservation and usage-logging systems still count every request and log real token counts (sourced from Pydantic AI's `RunUsage`, same as under Claude) — so the operational data needed to estimate paid-tier cost if this deployment later needs to scale beyond free-tier limits is already being captured, per the original brief's instruction to "still track token usage" even when the current cost is zero.

## AI enable/disable flag — unchanged behavior, re-verified

`require_ai_enabled` (added in the Claude pass) is provider-agnostic — it checks `ai_config.is_ai_enabled` only, with zero reference to which provider is configured. Re-verified live after the Gemini switch:
- `is_ai_enabled` remains `false` (no real key exists yet — see "Live Gemini test" below; never auto-enabled without one).
- `GET /api/v1/instance/info` correctly returns `is_ai_enabled: false` after a cache flush, confirming the frontend will still show the "AI is turned off" banner and disabled toggles from the Claude-era work, unchanged and unaffected by the provider switch underneath.

## Security — unchanged, re-confirmed

All of `part2-ai-verification.md`'s security review holds unmodified: `require_ai_enabled`'s auth-ordering fix, server-side-only key handling, clean error messages, rate limiting. Nothing here is provider-specific. Re-confirmed:
- No `LEARNHOUSE_AI_*` / `GEMINI_*` env var is `NEXT_PUBLIC_*`-prefixed anywhere in `apps/web` — grepped again after this pass, unchanged (none was, still none is).
- `apps/api/.env` (the real local dev file) inspected directly (names only, not printed) — still contains no AI key of any kind.
- No key value appears in any file changed this pass — verified by reviewing every diff before writing it; `config.yaml`'s `api_key`/`gemini_api_key` fields remain empty strings.

## Claude (Anthropic) support — fully retained, verified

**Nothing Claude-specific was deleted.** Concretely:
- `provider.py`'s `provider_id == "anthropic"` branch (`AnthropicModel`/`AnthropicProvider`) — untouched.
- `pydantic-ai-slim[...,anthropic,...]` dependency — untouched, still installed, still importable (re-verified: `from pydantic_ai.models.anthropic import AnthropicModel` succeeds in the venv).
- `tiers.py`'s `_CLAUDE_TIER_DEFAULTS` dict (`claude-haiku-4-5-20251001` / `claude-sonnet-5` / `claude-opus-5`) — kept in full, selected automatically whenever `provider: anthropic` is set.
- New test coverage added specifically to prove this: `test_model_for_tier_defaults_claude_still_available` in `test_llm_provider.py` asserts all three Claude tier defaults resolve correctly with `provider=anthropic`, run and passing.

**To switch back to Claude for production** (or at any point): change two `config.yaml` lines — `provider: "google"` → `"anthropic"`, and `api_key` to a real Claude key — restart the API. No code change, no redeploy of a different build, no lost work. This is exactly the property the original Part 2 architecture was designed to have, and it now has it in both directions (Gemini↔Claude), not just Claude-only.

## Live Gemini test — PASSED (real key provided and verified)

A real Gemini API key was supplied through the local, gitignored `apps/api/.env` file (`LEARNHOUSE_AI_PROVIDER=google`, `LEARNHOUSE_AI_API_KEY=...`, `LEARNHOUSE_IS_AI_ENABLED=true`) — never pasted into source, never committed, never printed or logged at any point in this process. `git check-ignore apps/api/.env` was confirmed before writing anything.

**A real bug was found and fixed during this verification** — the first live call failed with `TypeError: 'RunUsage' object is not callable`. Root cause: the usage-logging code added in the Claude-era pass (`client.py`) called `result.usage()` as a method; in the installed Pydantic AI version, `usage` is a property, not a method. This is exactly the kind of bug unit tests cannot catch (mocked result objects don't reproduce a real property-vs-method mismatch) — only a live call surfaced it. Fixed in both `generate()` and `generate_stream()`, plus added defense-in-depth (a `try/except` around reading `.usage` so a future API change to this property can never again take down an otherwise-successful generation, and — for the streaming path specifically — can never look like a request *failure* to the caller after content was already fully delivered, which would have wrongly tripped the refund-on-failure path).

Results after the fix, every test using the smallest reasonable input:

| Test | Model | Result |
|---|---|---|
| Non-streaming text generation | `gemini-3.1-flash-lite` (fast) | **PASS** — exact expected response returned |
| Streaming text generation | `gemini-3.6-flash` (standard) | **PASS** (after correcting an unrealistic test — see below) |
| Structured-output generation (quiz schema) | `gemini-3.6-flash` (standard) | **PASS** — valid schema, correct question count |
| Embeddings (query + document) | `gemini-embedding-001` | **PASS** — 768 dimensions, matching the pgvector column exactly |
| Audio/TTS generation | `gemini-2.5-flash-preview-tts` | **PASS** — 229 KB of real WAV audio for a natural sentence |
| Image generation | `gemini-2.5-flash-image` | **BLOCKED — real account limitation, not a bug**: `429 RESOURCE_EXHAUSTED`, `limit: 0` for this model's free-tier input-token quota. This specific key's free tier grants zero image-generation quota; text generation, embeddings, and TTS all have real free-tier quota and worked. Not fixable from this codebase — an account/billing-tier fact, not a defect. |
| Copilot, end-to-end via the real browser UI | `gemini-3.1-flash-lite` (title + follow-ups) + `gemini-3.6-flash` (answer) | **PASS** — asked "What is 2+2?" through the actual `/copilot` page in General mode; got the correct answer "4", an auto-generated chat title ("Addition of two and two"), and three relevant follow-up suggestions. No dead spinner, no leaked error, clean UI. |

**A genuine Gemini 3 "thinking model" characteristic was discovered, not a bug**: the standard-tier model shares its `max_output_tokens` budget between internal reasoning and the visible answer. A first streaming test used an artificially tiny `max_tokens=10` and got an empty response (reasoning consumed the entire budget) — this reproduced a behavior the codebase's own `audio/generator.py` had already documented for script generation, just not yet observed for the interactive chat path. Retesting with the real production default (4096 tokens, `DEFAULT_MAX_OUTPUT_TOKENS`) worked correctly. The two existing small-budget call sites in `base.py` (`max_tokens=30`/`150`, for chat-title and follow-up generation) were checked and confirmed to use the **fast** tier (`gemini-3.1-flash-lite`), which did not exhibit this starvation even at `max_tokens=10` in direct testing — so no code change was needed there, but this is flagged as a real characteristic worth knowing if `max_tokens` is ever tightened further on the standard/pro tiers.

**Credit accounting confirmed correct with real traffic**: `GET /orgs/1/ai-credits` showed `used_credits: 2` after one earlier (pre-fix, errored-but-content-produced) Copilot message and one successful one — confirming the refund-on-failure logic correctly did NOT refund the first message (real content was generated before the downstream bug hit), matching its own documented design intent exactly.

## Documentation cross-references

## Documentation cross-references

- `part2-ai-architecture.md` — original Claude/Anthropic Part 2 architecture (unchanged, still accurate for the Anthropic path).
- `part2-ai-verification.md` — original Claude-era security review and test log (unchanged; Gemini-specific verification is in this file instead of duplicating it there).
- `frontend-ai-surfaces.md` — Part 1 frontend AI-surface inventory; the Gemini switch requires no frontend changes beyond what the Claude pass already did (`is_ai_enabled` exposure, `OrgEditAI.tsx` banner), since both are provider-agnostic from the frontend's perspective.
