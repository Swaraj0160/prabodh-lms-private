# Part 2 — AI Security, Testing, and Live Verification

Companion to `part2-ai-architecture.md`. This file records what was actually checked and how, not what should be checked eventually.

**Provider update**: everything in this file was verified against the original Claude/Anthropic configuration. The active provider was subsequently switched to Gemini (`part2-gemini-provider.md`) — the security posture, test results, and enable-flag behavior documented here are all provider-agnostic and were re-confirmed (not re-derived from scratch) after the switch; see `part2-gemini-provider.md`'s own security/testing sections for what was specifically re-checked post-switch and what remains identical.

**Live-key update**: a real Gemini API key was subsequently supplied and verified working end-to-end — see `part2-gemini-provider.md`'s "Live Gemini test" section for full results (a real bug was found and fixed there, `result.usage()` vs `.usage`, only catchable with a live call). The key was written only into the local, gitignored `apps/api/.env` (confirmed via `git check-ignore` before writing), never into a tracked file, never printed, never logged — confirmed by grepping the entire repo tree and scratch/log directories for the key value after the fact, with zero matches outside `.env`.

## Security review

Went through the Part 2 brief's security checklist against the actual code, not just in principle:

| Check | Result |
|---|---|
| API keys server-side only | **Pass.** `ai_config.api_key` / `gemini_api_key` are read only in `apps/api` config/service code. Grepped `apps/web` for any AI provider key reference — none. The frontend never sees a Claude key. |
| No secret in frontend bundles | **Pass.** No `LEARNHOUSE_AI_*` or `ANTHROPIC_*` env var is prefixed `NEXT_PUBLIC_*` anywhere, which is what would leak a var into the client bundle in this Next.js app. |
| No secret in logs | **Pass.** The new usage-logging (`client.py::_log_usage`) logs only model name, feature label, token counts, and success/failure — never prompt/response content, never config values. Existing error handling (`AINotConfiguredError` messages) names which env var is missing, never its value. |
| Authenticated-only AI endpoints | **Pass, verified live.** Every AI router already required `Depends(get_authenticated_user)` per-endpoint before this pass. Confirmed live: anonymous `POST /api/v1/ai/rag/chat` → `401`. |
| Single-org isolation preserved | **Pass, unchanged.** `require_ai_enabled` is a platform-wide gate with no org awareness; every existing per-org authorization check (`is_org_member`, `enforce_org_mfa`, org-scoped credit reservation) is untouched and still runs after it. |
| Users cannot access another user's AI data | **Unchanged, not touched this pass.** Existing chat-session/history lookups already scope by `user_id`/`org_id` — out of scope for a "replace the provider" pass to re-derive; no code path here was modified that touches session ownership checks. |
| Prompts don't leak system data | **Not independently re-audited this pass** — no prompt content was changed (see architecture doc: "no prompt rewrites"), so whatever was true before is unchanged. Flagging rather than claiming a fresh audit that didn't happen. |
| User content treated as untrusted | **Unchanged.** `attachments_to_parts` (`client.py`) already base64-decodes defensively (catches `binascii.Error`, skips malformed attachments instead of 500ing) — pre-existing, confirmed still in place. |
| Error messages don't expose secrets | **Pass, verified live.** The 403 a user actually sees is `"AI features are not enabled on this platform."` — no stack trace, no key fragment, no internal path. Confirmed via the real Copilot UI, not just by reading the code. |
| Provider responses handled safely | **Unchanged**, provider-agnostic layer already wraps generation in try/except with logged (not raised-to-client) internals — the SSE error event a client sees is a fixed generic string (`"An internal error occurred..."`), not the provider exception. |
| No new SSRF/arbitrary-URL vulnerability | **Reviewed, no new surface.** The only URL-shaped AI input is `ImageUrl`/`DocumentUrl`/`VideoUrl` in `attachments_to_parts` — unchanged from before this pass, and those are passed to the provider SDK, not fetched by this codebase. |
| AI endpoints have rate limiting | **Pass, pre-existing.** `enforce_ai_rate_limit` (per-user 30/min, per-org 120/min) was already wired into every AI service call site; confirmed via grep, unchanged. |
| **New surface introduced by this pass**: `require_ai_enabled` dependency ordering | **Found and fixed a real bug during implementation** — first version checked the platform flag before authentication, so an anonymous caller got 403 "AI not enabled" instead of 401, leaking platform AI-configuration state to unauthenticated callers and breaking the existing `test_unauth_ai_billing.py` contract. Fixed by having the dependency check auth internally first. See architecture doc for detail. |

No pre-existing critical vulnerability outside this pass's scope was found during this review; nothing to escalate beyond the captions/audio-input capability gap already documented in the architecture doc (a functional limitation, not a security issue).

## Automated tests

Ran the full backend suite (`pytest src/tests`, 4,469 tests) before and after this pass's changes to separate what this work affected from what was already broken:

- **Before any Part 2 change**: baseline not separately captured (Part 2 started from Part 1's already-uncommitted working tree) — instead, every failure this pass introduced was diagnosed and fixed individually (see below), and the final full run was used to confirm nothing outside the identified set was affected.
- **Final full run**: `4,456 passed, 13 failed, 29 skipped`.
- **All 13 remaining failures are pre-existing and unrelated to Part 2** — confirmed by checking that none of the 13 failing test files were touched this pass (`git status` shows zero changes to `test_zapier.py`, `test_content_files_router.py`, `test_upload_faststart_wiring.py`), and by reading each failure's actual cause:
  - `test_zapier.py` (4 failures) — the webhook SSRF-protection validator rejects a test URL that resolves to a private/loopback address in this sandboxed network environment; a DNS/environment difference, not an AI or code issue.
  - `test_content_files_router.py` (7 failures) — storage/S3-configuration-dependent, unrelated to any file this pass touched.
  - `test_upload_faststart_wiring.py` (1 failure) — a Windows path-separator (`\` vs `/`) assertion mismatch, an OS-specific pre-existing test bug.

**Failures this pass introduced and fixed** (all were expected consequences of intentional changes, not accidents):
- 3 tests asserting the old Gemini default model IDs (`test_llm_provider.py`, `test_boards_playground_service.py`, `test_playgrounds_generator_service.py`) — updated to assert the new Claude defaults.
- 11 parametrized cases in `test_unauth_ai_billing.py` — caught the auth-ordering bug described above; fixed in the dependency itself, not by weakening the test.
- 10 router-level tests in `test_boards_router.py` / `test_playgrounds_router.py` — needed `app.dependency_overrides[require_ai_enabled] = lambda: True` added to their fixtures, matching the existing pattern already used for `require_playgrounds_feature`/`require_boards_feature`.
- 3 tests in `test_instance_router.py` — needed `ai_config=SimpleNamespace(is_ai_enabled=...)` added to their mocked config objects, since the router now reads that field.

**New tests added**: `TestRequireAiEnabled` in `test_feature_dependencies.py` (4 cases: anonymous caller → 401 before the flag is even checked, disabled → 403, missing/malformed config → fails closed with 403 rather than crashing, enabled + authenticated → passes). `test_get_instance_info_builds_response` extended to assert `is_ai_enabled` appears correctly in the public instance-info response.

Full command used: `.venv/Scripts/python.exe -m pytest src/tests -q` (Windows venv, from `apps/api`).

## Browser / live verification

Ran against the actual local stack (`apps/api` on :1338, `apps/web` on :3000, real Postgres/Redis via Docker), not just source review:

1. **Backend restarted** after the code changes (Python has no hot-reload in this dev setup) — confirmed via a fresh PID and a clean startup log.
2. **`GET /api/v1/instance/info`** — confirmed `is_ai_enabled: false` appears in the real response after flushing the 10-minute Redis cache (`org_cache:instance_info`) that would otherwise have served a stale pre-change response.
3. **Frontend rebuilt** (`bun run build`) — clean, zero errors.
4. **`/dash/org/settings/ai` visited live**, logged in as admin: the new "AI is turned off for this whole platform..." banner renders, and both toggles (`role="switch"`) are confirmed `disabled=true` via a DOM query — previously they rendered fully interactive despite being non-functional.
5. **`/copilot` visited live**, a real message typed and submitted through the actual UI (not a direct API call): the request round-trips to the real backend, the backend correctly 403s, and the UI surfaces `"AI features are not enabled on this platform."` directly to the user with no dead spinner, no uncaught exception, no React error boundary triggered. Confirmed via `get_page_text` reading the actual rendered DOM after the interaction, and via `read_console_messages` showing no new uncaught errors from the interaction itself (only unrelated dev-tooling HMR reconnect noise).
6. **Direct API calls** (with a real session token from `/api/auth/refresh`, the same mechanism used throughout this project's verification work): authenticated `POST /api/v1/ai/rag/chat` → `403` with the clean message; anonymous (`curl`, no auth header) → `401`.

**Not verified live this pass**: the editor AI-assist panel and magic-blocks/course-planning/quiz/scenario/assignment-generation UI surfaces were not individually clicked through, because they route through the identical `require_ai_enabled`-guarded backend path already confirmed working via the Copilot test above (same dependency, same router-wiring pattern, same error contract) — re-clicking each one would re-verify the same code path rather than find anything new. Flagged here rather than silently assumed.

## Live Claude API smoke test

**BLOCKED: valid `ANTHROPIC_API_KEY` (or `LEARNHOUSE_AI_API_KEY` with `LEARNHOUSE_AI_PROVIDER=anthropic`) required for live provider verification.**

Checked `apps/api/.env` (the real local dev env file) directly — it contains only `LEARNHOUSE_AUTH_JWT_SECRET_KEY` and `COLLAB_INTERNAL_KEY`. No AI provider key of any kind exists anywhere in this environment (checked env, `config.yaml`, and confirmed no `.env.example` previously existed for `apps/api` to have documented one). No key was invented, no secret was fabricated, and `is_ai_enabled` was correctly left `false` rather than flipped on without a real, working credential behind it.

What this pass verified instead, without a live key:
- The Anthropic provider path **imports and constructs cleanly** — `from pydantic_ai.models.anthropic import AnthropicModel; from pydantic_ai.providers.anthropic import AnthropicProvider` succeeds in the installed venv with no import error.
- `build_model()`'s `provider_id == "anthropic"` branch is exercised by existing unit tests (`test_llm_provider.py`, parametrized across all supported providers) with a mocked config — confirming the code path constructs an `AnthropicModel` correctly, without making a real network call.
- The full request path down to (but not including) the actual Anthropic API call was exercised live via the Copilot UI test above — everything up to and including credit reservation, rate limiting, and model resolution runs for real; only the final `agent.run_stream()` call to Anthropic's servers is unverified, because `require_ai_enabled` correctly blocks the request before it would reach that call (AI is off).

**Next manual action for whoever has a Claude API key**: set `LEARNHOUSE_AI_API_KEY` (or `ai_config.api_key` in `config.yaml`) to a real `sk-ant-...` key, set `LEARNHOUSE_IS_AI_ENABLED=true` (or `ai_config.is_ai_enabled: true`), restart the API, and either use the Copilot UI directly or run:
```
curl -X POST http://localhost:1338/api/v1/ai/rag/chat?org_id=1 \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"message":"hello","course_uuid":"<a real course uuid>"}'
```
A real response (not a 403) confirms the live Claude path end-to-end. If it fails, the error will name what's wrong (missing embeddings provider for RAG indexing, invalid key, etc.) rather than fail silently — see `part2-ai-architecture.md`'s error-handling notes.

## Rollback procedure

Every change in this pass is either additive (new dependency function, new log lines, new response field, new doc files) or a config-file edit (`config.yaml`, model defaults) — nothing destructive, no migration to reverse.

To roll back to Part 1's pre-Part-2 AI behavior (Gemini-configured, no platform-flag enforcement):
1. `config/config.yaml`: set `provider: "google"` back, clear `model_fast`/`model_standard`/`model_pro` overrides if any were set (or set them to Gemini IDs).
2. To restore the old "flag exists but isn't enforced" behavior specifically: remove the `dependencies=[Depends(require_ai_enabled)])` argument from the 10 router declarations listed in the architecture doc, and delete `require_ai_enabled` from `dependencies.py`. Not recommended — this was a genuine security/coherence gap, not a stylistic change — but it's a small, easily-reverted, self-contained diff if ever needed.
3. `git diff prabodh/whitelabel..prabodh/part2-claude-ai -- apps/api apps/web` shows the complete change set for review before any rollback decision.
