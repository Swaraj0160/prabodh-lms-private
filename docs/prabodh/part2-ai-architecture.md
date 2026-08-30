# Part 2 — AI Architecture (Gemini → Claude)

This documents what actually exists in the repository after the Part 2 pass, not a plan. See `part2-ai-verification.md` for tests, security review, and live-verification results.

**Provider update**: this document describes the original Part 2 work, which targeted and configured **Claude/Anthropic** as the active provider. The active provider was subsequently switched to **Gemini** for local/demo development (a Gemini free-tier key is available for this phase) — see `part2-gemini-provider.md` for that switch, the current Gemini model tiers, and confirmation that everything described below (the provider abstraction, cost controls, the AI enable/disable guard, usage logging, tests) is unchanged and provider-agnostic. The Claude configuration and model tiers below remain fully correct and selectable at any time via a `config.yaml` change — nothing Claude-specific was removed.

## Headline finding: there was no Gemini SDK to "replace" for text generation

Before touching anything, this pass audited every AI-related file in `apps/api/src`. The result changes the shape of "Part 2" considerably from what a from-scratch Gemini→Claude migration would look like:

**The text-generation architecture was already fully provider-agnostic**, built on [Pydantic AI](https://ai.pydantic.dev/). `src/services/ai/llm/provider.py`'s `build_model()` already had a first-class `provider == "anthropic"` branch (`AnthropicModel` / `AnthropicProvider`), and `pydantic-ai-slim[openai,anthropic,google,mistral]` was already an installed dependency (`pyproject.toml`). Every text-based AI feature — chat, editor assist, magic blocks, quiz/scenario/assignment generation, course planning, RAG — calls the provider-neutral `generate()` / `generate_stream()` in `src/services/ai/llm/client.py`, which never imports a vendor SDK directly. Confirmed by grep: only two files anywhere in `src/` import the Google GenAI SDK directly (see "Google-only features" below); every other AI service file goes through the neutral layer.

**What Part 2 actually required, then, was:**
1. Configure this deployment's provider as Anthropic (not a code change — `config/config.yaml`'s `ai_config.provider`).
2. Choose and set real Claude model IDs for the tier defaults (`src/services/ai/llm/tiers.py` — previously hardcoded Gemini model names as the fallback).
3. **Enforce the platform AI enable/disable flag**, which existed in config but was checked nowhere (see below — this was the one genuine, consequential gap).
4. Fill real gaps in cost control (a token-length backstop) and usage observability (structured per-request logging).
5. Expose the platform flag to the frontend so the AI settings UI stops rendering as live/interactive when the backend would reject everything.
6. Honestly document the features Claude architecturally cannot replace (image generation, audio/TTS generation, and — a capability gap found during this pass — audio transcription/captions).

## The one real gap: `LEARNHOUSE_IS_AI_ENABLED` was parsed but never checked

`config/config.py` parses `LEARNHOUSE_IS_AI_ENABLED` into `AIConfig.is_ai_enabled`. Grepping all of `src/` for that field before this pass found **zero call sites that read it** — every AI router (`ai.py`, `magicblocks.py`, `courseplanning.py`, `quiz.py`, `scenario.py`, `assignment_gen.py`, `rag.py`, `images.py`, `audio.py`, `boards_playground.py`, `playgrounds_generator.py`) was fully live and callable regardless of the flag. This exactly matched what Part 1's frontend track had already suspected and documented in `frontend-ai-surfaces.md` without being able to confirm from the frontend side.

**Fixed**: added `require_ai_enabled` to `src/security/features_utils/dependencies.py` and wired it as a router-level dependency (`APIRouter(dependencies=[Depends(require_ai_enabled)])`) on all 10 AI routers above. It:
- Requires authentication first (checked internally, not just relying on dependency ordering) — an anonymous caller gets 401, never a 403 that would leak whether AI is configured. This subtlety was caught by a pre-existing test (`test_unauth_ai_billing.py`) that asserted every AI route 401s for anonymous callers; the first implementation attempt broke it because FastAPI resolves router-level `dependencies=[]` before a path operation's own parameters, so an anonymous caller hit the platform-flag check before the endpoint's own auth check. Fixed by having `require_ai_enabled` depend on `get_current_user` itself and check `AnonymousUser` first — FastAPI caches the resolved user per request, so this costs nothing extra when the endpoint's own `get_authenticated_user` also resolves it.
- Is independent of the per-organization `ai` feature flag (`check_ai_credits` / `reserve_ai_credit`, unchanged). Both gates must pass: the platform flag is the operator's global switch; the org flag is a per-tenant admin's toggle. An org admin turning their org's AI on has no effect if the platform operator hasn't enabled and configured AI at all.

Verified live (not just unit-tested): with `is_ai_enabled: false` (the current, correct state — see "Current state" below), a real authenticated request to `/api/v1/ai/rag/chat` returns `403 {"detail":"AI features are not enabled on this platform."}`, and clicking "send" on the real Copilot UI at `/copilot` surfaces that exact message to the user with no dead spinner, no stack trace, no console error. An anonymous request to the same endpoint returns `401`.

## Provider configuration

`config/config.yaml`'s `ai_config` section (comments updated this pass):

```yaml
ai_config:
  is_ai_enabled: false   # stays false until api_key below is a real key
  provider: "anthropic"  # was "google"
  api_key: ""            # Claude API key (sk-ant-...) — or set LEARNHOUSE_AI_API_KEY
  model_fast: ""         # default: claude-haiku-4-5-20251001
  model_standard: ""     # default: claude-sonnet-5
  model_pro: ""          # default: claude-opus-5
  embedding_provider: "" # REQUIRED when provider=anthropic — see "Embeddings" below
  gemini_api_key: ""     # still used by image/audio generation (Google-only, see below)
```

Every field is also settable via env var (`LEARNHOUSE_AI_PROVIDER`, `LEARNHOUSE_AI_API_KEY`, `LEARNHOUSE_AI_MODEL_FAST/STANDARD/PRO`, `LEARNHOUSE_AI_EMBEDDING_PROVIDER`, `LEARNHOUSE_AI_EMBEDDING_MODEL`, `LEARNHOUSE_GEMINI_API_KEY`) — this mechanism already existed in `config/config.py` before this pass; no code change was needed to support it. There is no separate `ANTHROPIC_API_KEY` variable — `LEARNHOUSE_AI_API_KEY` (paired with `LEARNHOUSE_AI_PROVIDER=anthropic`) is the repository-consistent equivalent, and introducing a redundant Anthropic-specific variable name would fragment the existing provider-agnostic config surface for no benefit.

**Provider stays fully configurable, not hardcoded to Anthropic in code.** `provider.py`'s own code-level default (`DEFAULT_PROVIDER = "google"`, used only when config is entirely absent) was deliberately left unchanged — that's a safety fallback for the wider LearnHouse codebase, not specific to this deployment. Only the checked-in `config.yaml` (Prabodh's actual applied config) was changed to declare Anthropic as the intended provider.

## Model selection and tiering

Three tiers (`src/services/ai/llm/tiers.py`), unchanged tiering *logic* — only the default model IDs changed:

| Tier | Model | Used for | Rationale |
|---|---|---|---|
| fast | `claude-haiku-4-5-20251001` | Chat titles, follow-up suggestions, magic blocks, playground/board generation | Low-latency interactive tools where the user is watching a live stream; cheapest tier |
| standard | `claude-sonnet-5` | Chat, RAG, course planning/blocks (free & standard plans) | Balanced default — substantive answers, reasonable cost, the tier most requests hit |
| pro | `claude-opus-5` | Course planning/blocks for Pro+ plan orgs | Strongest reasoning, reserved for the feature (multi-step course structuring) and plan tier where the extra cost is worth it |

These are the **repository code defaults**, used only when an operator hasn't overridden `model_fast`/`model_standard`/`model_pro`. The tiering *policy* (which purpose maps to which tier, plan-based upgrades) is unchanged from Part 1's existing design — this pass did not invent new tiering logic, since the existing chat→standard / planning→standard-or-pro-by-plan mapping was already sound and unrelated to which vendor's models fill each tier.

An operator running a non-Anthropic provider (Gemini, OpenAI, Ollama, ...) must set the three model env vars to that provider's own model IDs — the Claude defaults above are only correct when `provider: anthropic`. This is now documented directly in `tiers.py` and `config.yaml`.

## Embeddings (RAG / Course Copilot)

Anthropic has no embeddings API — this was already correctly handled in `src/services/ai/llm/embeddings.py` before this pass (a genuinely well-designed pre-existing fallback: providers without embeddings fall back to Google embeddings when `gemini_api_key` is set, otherwise raise a clear `AINotConfiguredError`). No code change was needed here.

**Operational requirement, not a code gap**: with `provider: anthropic`, an operator MUST also set `embedding_provider` (to `openai` or `ollama`, with that provider's own credentials) or keep `gemini_api_key` configured purely for embeddings. Without one of these, RAG/Course Copilot's indexing step fails with a clear error rather than silently using the wrong provider. This is now called out explicitly in `config.yaml`'s comments.

## Google-only features — Claude cannot replace these (architectural, not a code gap)

Two features go **straight to the Google GenAI SDK**, bypassing the provider-neutral layer entirely, because Claude has no equivalent API:

- **Image generation** (`src/services/ai/image/generator.py`) — Google's "nano banana" (`gemini-2.5-flash-image`) family. Claude has no image generation capability at all.
- **Audio / podcast TTS generation** (`src/services/ai/audio/generator.py`) — Google Gemini TTS. Claude has no text-to-speech capability at all.

These were **left exactly as they are** — still Google-powered, requiring `gemini_api_key` to function — rather than removed or broken. Ripping out working functionality to "finish" a Claude migration that is architecturally impossible would violate "preserve existing business behavior" and would leave the product with a genuine feature regression for no benefit. Their docstrings already correctly documented this as Google-only before this pass; no change was needed there beyond the tier-default cleanup above.

**A third, less obvious capability gap found during this pass**: `src/services/ai/captions.py` (audio → WebVTT transcription) technically routes through the provider-neutral `generate()` layer, so it *looks* provider-agnostic — but it sends raw audio bytes as a multimodal attachment, and Claude's public API accepts text, images, and PDF documents as input, not native audio. With `provider: anthropic`, this feature will fail per-chunk with a clear provider error rather than transcribe. This was not previously documented anywhere (the original docstring said "Gemini by default" as if it were just a config default, not a hard capability requirement). Documented now in the module docstring. **Untested against a live Claude call** — no API key exists in this environment (see `part2-ai-verification.md`); this is inferred from Claude's publicly documented input modalities, not from an observed failure, and is flagged as such.

**Escalation per the Part 2 brief's own rules (§23)**: whether to (a) accept this three-feature gap as a permanent product boundary, (b) wire a second, Google-only credential path specifically for these three features (already supported — set `gemini_api_key` alongside `provider: anthropic`), or (c) find alternative providers for image/audio/transcription is a product decision beyond what this pass can resolve from repository evidence alone, and is flagged for the deployment operator rather than decided unilaterally.

## Cost controls

Found already extensively built, not built from scratch this pass:

- **Per-organization AI credits** (`src/security/features_utils/usage.py`): atomic Redis-based reservation (`reserve_ai_credit`) with refund-on-failure (`refund_ai_credit`), plan-based limits, purchased-credit top-ups, unlimited-but-tracked for non-SaaS (OSS) deployments — this deployment's mode. Wired into every AI router already (confirmed by grep, unchanged).
- **Rate limiting** (`src/services/security/rate_limiting.py`): `enforce_ai_rate_limit` — per-user (30/min) AND per-org (120/min) sliding-window limits, already wired into every AI service call site.
- **Durable generation history** (`src/db/ai/generations.py`): per-artifact records (image/quiz/assignment/scenario) for user-facing history, already existed.

**Added this pass** (a genuine, previously-missing gap): a **default output-token cap**. `client.py`'s `generate()`/`generate_stream()` accepted an optional `max_tokens` parameter, but the actual feature call sites (chat, editor, magic blocks, course planning) never passed one — meaning a single response's length was bounded only by the provider's own default ceiling, not by the application. Fixed centrally in `_settings()`: any call that doesn't specify `max_tokens` now defaults to 4096 output tokens (`DEFAULT_MAX_OUTPUT_TOKENS`), a single-point change covering every text-generation feature at once. Two pre-existing call sites (chat-title generation, follow-up suggestions) already passed their own smaller explicit values and are unaffected.

## Usage / cost observability

**Added this pass**: structured per-request logging in `client.py` — `_log_usage()` logs `model`, `feature` label, `input_tokens`, `output_tokens`, and success/failure for every `generate()`/`generate_stream()` call, sourced from Pydantic AI's real `RunUsage` object (`result.usage()`), not fabricated. Never logs prompt or response content.

**Deliberately NOT a new database table.** The existing Redis-based AI-credits system already provides the business-facing, per-org usage accounting (queryable via `GET /orgs/{id}/ai-credits`). A token-level Postgres table would be a second, overlapping accounting system and a real migration-risk decision (schema, retention, whether it becomes billing-authoritative) that section 26 of the brief explicitly says to avoid unless genuinely required. Structured logs satisfy "capture where technically available" at the *technical/operational* observability layer without that risk — an operator can ship these log lines to whatever aggregation they already run. This tradeoff is a documented choice, not an oversight; a durable token-cost table remains a reasonable next step if an operator wants billing-grade per-request reporting, and is called out as such rather than silently left undone.

**Not currently threaded through**: org_id/user_id context at the `client.py` layer — adding it would require changing every call site's signature across ~8 files. The existing per-org credit system already gives org-level attribution separately; the new log line gives model/token/feature-level detail. Combining both into one place is future work, not done here.

## What was NOT changed

- No database migrations (none were genuinely required — see above).
- No new third-party dependencies (`pydantic-ai-slim[anthropic]` was already installed).
- No rewrite of prompts — none were Gemini-specific in a way that would break on Claude (the shared `client.py` layer already normalized message/attachment formats away from Gemini's `inline_data`/`file_data` shape in an earlier pass).
- No change to streaming behavior, SSE event shapes, cancellation handling, or credit-refund-on-failure logic — all were already correct and provider-agnostic.
- Image/audio/TTS generation code — unchanged, still Google-only (see above).
- The `DEFAULT_PROVIDER = "google"` fallback in `provider.py` — unchanged (a repo-wide safety default, not Prabodh-specific config).

See `part2-ai-verification.md` for the security review, test results, and live-verification log, and `frontend-ai-surfaces.md` (Part 1, re-confirmed this pass) for the frontend AI-surface inventory.
