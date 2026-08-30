# Frontend AI Surface Findings (Part 1 — AI out of scope)

**Part 2 update (2026-08-24)**: every gap this document originally flagged is now resolved — see `part2-ai-architecture.md` and `part2-ai-verification.md` for the backend enable-flag enforcement, and this file's own note below for the frontend side (`OrgEditAI.tsx` now shows accurate platform-AI state). The active AI provider was subsequently switched from Claude to Gemini for local/demo development (`part2-gemini-provider.md`) — this switch is entirely backend-side (a `config.yaml` change) and required **zero frontend changes**, since none of the frontend AI surfaces are provider-aware; they only care about the platform `is_ai_enabled` flag and the org-level `ai` toggle, both unchanged by which vendor sits behind the API.

**Re-confirmed live, session 5 (2026-08-24)**: re-visited `/dash/org/settings/ai` and `/copilot` after this session's other fixes and rebuilds. Identical result to the original finding below — no regression, no new frontend-fixable issue, AI was not enabled or implemented (per instruction, `LEARNHOUSE_IS_AI_ENABLED` remains false and no Claude/AI integration work was done).

Per the Part 1 Engineering Guide, `LEARNHOUSE_IS_AI_ENABLED=false` for this entire project, and AI integration is Part 2 work. This document records what was found inspecting the frontend's AI-related surfaces with a live, admin-authenticated instance — it is the Part 2 team's starting inventory, per the Frontend Track's instruction.

## RESOLVED — Part 2 (2026-08-24)

Both halves of the gap described below are fixed:
- **Backend**: `LEARNHOUSE_IS_AI_ENABLED` is now actually enforced (`require_ai_enabled`, wired into all 10 AI routers) — previously parsed into config but checked nowhere.
- **Frontend**: the backend's public `/instance/info` endpoint now returns `is_ai_enabled`; `proxy.ts` middleware sets it as an `LH_ai_enabled` cookie; `services/config/config.ts` exposes `isPlatformAiEnabled()`; `OrgEditAI.tsx` now reads it and shows a clear "AI is turned off for this whole platform..." banner with both toggles correctly `disabled` when the platform flag is off — previously they rendered fully interactive with no indication anything was wrong.

Verified live end-to-end, not just in code: with the platform flag off, the `/copilot` UI's toggles are confirmed disabled via a DOM query, and a real message typed and submitted through the actual Copilot UI round-trips to the real backend, gets a clean `403`, and displays `"AI features are not enabled on this platform."` directly to the user — no dead spinner, no stack trace, no console error. Full detail in `part2-ai-architecture.md` and `part2-ai-verification.md`.

**Fully re-verified with AI genuinely ON and a real Gemini key** (`part2-gemini-provider.md`): toggles confirmed interactive (`disabled=false`) once `is_ai_enabled: true`; a real question typed into `/copilot` ("What is 2+2?") got a real, correct Gemini-generated answer, an auto-generated chat title, and follow-up suggestions — the full frontend↔backend AI-flag round trip now confirmed working in both states, not just the off state.

## Headline finding (HISTORICAL — see RESOLVED above): the frontend has no visibility into `LEARNHOUSE_IS_AI_ENABLED` at all

Searched the entire `apps/web` tree for any reference to the platform-wide AI flag (`IS_AI_ENABLED`, `NEXT_PUBLIC_LEARNHOUSE_IS_AI_ENABLED`, or similar) — there is none. The two files that looked promising on an initial grep (`OrgEditAI.tsx`, `Editor.tsx`) turned out to only reference a **per-organization** `ai_enabled` / `copilot_enabled` config field, which is a completely separate, independent toggle stored on the org row and editable by any org admin — nothing to do with the platform-wide environment variable.

Verified live at `http://localhost:3000/dash/org/settings/ai` (logged in as the admin account): the "Enable AI Features" and "AI Copilot" switches both render as **checked/on**, fully interactive, with copy like "Let learners ask questions about course content" and "AI-powered content editor assistance ... Always on". Nothing in this screen indicates that AI is actually disabled platform-wide.

This means, as far as the frontend can tell, AI is available. Whatever actually happens when a learner or admin tries to use one of these features depends entirely on whether the **backend** independently blocks the underlying AI endpoints when `LEARNHOUSE_IS_AI_ENABLED=false`. This pass did not attempt to trigger an actual AI action (e.g. asking the Copilot a question) to observe the failure mode, because that requires content already in place and risks depending on backend behavior this track doesn't own.

**This is a cross-team dependency, recorded in `frontend-open-questions.md`.** It is not something this pass fixed, because:
- Hiding the org's AI settings page outright would be presuming an architectural decision (should Part 1 disable the *org-level* AI config entirely, or only the platform's own AI provider calls?) that isn't spelled out in the specification.
- The correct frontend fix depends on knowing exactly how the backend enforces the flag (which endpoints 403, what the response looks like) — the same category of dependency the Backend Track's own guide describes for the single-org lockdown (Gate B3-style), just for AI instead of orgs.

## Surfaces inventoried (not all individually tested — see caveats)

| Surface | File | Status |
|---|---|---|
| AI Copilot chat bubble | `components/Copilot/CopilotBubble.tsx`, referenced from `OrgMenu.tsx` | Present in the org chrome; renders based on `usePlan()`/org config, not the platform flag. Not clicked/tested this pass. |
| Org AI settings panel | `components/Dashboard/Pages/Org/OrgEditAI/OrgEditAI.tsx` | Confirmed live and fully interactive (see above) — the clearest coherence risk found. |
| Content editor AI assist | `components/Objects/Editor/Editor.tsx` (`canUseAI`) | References the org-level flag, not the platform flag. Not tested in the editor itself this pass (would require creating test course content). |
| Podcast AI generation vs. podcast playback | `components/Contexts/PodcastContext.tsx`, `PodcastPlayerContext.tsx`, `Dashboard/Pages/Podcast/*` | Not separated/tested this pass — podcasts are explicitly in-scope as a feature (non-AI parts), but this pass did not verify AI-generation sub-features are cleanly distinguished from playback/management UI. |
| Command palette AI entry | `components/Dashboard/CommandPalette/CommandPalette.tsx` | Not inspected this pass. |
| "Magic block" / board AI tools | `components/Dashboard/Boards/BoardCanvas.tsx`, `BoardToolbar.tsx` | Not inspected this pass. |

## What was NOT done, and why

A full click-through of every AI entry point (asking the Copilot a real question, triggering AI content generation in the editor, etc.) was not performed. Reasons:
1. It requires backend AI endpoints to be live and to fail in an observable way, which is backend-owned behavior this pass cannot change or guarantee.
2. Per the Part 1 scope rules: "Don't spend significant time fixing AI backend functionality." A deep click-through whose only useful output would be "yes, it's broken because the backend doesn't gate it" duplicates what the headline finding above already establishes from the code.

## Recommendation for whoever picks this up next

Before Part 1 ships, someone (frontend or backend, whoever owns the decision) needs to answer: should the org-level AI settings page be hidden/disabled entirely when the platform flag is off, or does the backend genuinely block every AI action regardless of what the org config says (making the frontend toggle harmless but confusing)? Once that's answered, the actual frontend fix here is small — either gate `OrgEditAI.tsx` behind a flag the backend needs to expose, or leave it as informational-only with a clarifying note.
