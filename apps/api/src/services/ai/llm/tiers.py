"""Central plan-based model tiering.

Single source of truth replacing the duplicated ``get_org_ai_model()`` functions that lived
in four routers. Model names come from config (``ai_config.model_*``) and fall back to
PROVIDER-SPECIFIC defaults below, so behavior is unchanged until an operator overrides them
via ``LEARNHOUSE_AI_MODEL_FAST`` / ``_STANDARD`` / ``_PRO``.

Part 2 (Prabodh) provider history:
  - The original Part 2 specification targets Claude (Anthropic) as the production provider.
  - Google Gemini is the CURRENT ACTIVE provider for local/demo development, chosen because a
    Gemini free-tier key is available during this phase — see
    docs/prabodh/part2-ai-architecture.md and part2-gemini-provider.md for the full rationale.
  - Both providers' tier defaults are kept here, keyed by provider, so switching
    ``LEARNHOUSE_AI_PROVIDER`` between ``google`` and ``anthropic`` needs no code change and no
    lost work — this is the whole point of the provider-agnostic design in ``llm/provider.py``.
    Do NOT delete the Anthropic row when Gemini is active, and do NOT delete the Gemini row if
    the deployment later moves back to Anthropic for production.
"""

from __future__ import annotations

import logging
from typing import Literal

from sqlmodel.ext.asyncio.session import AsyncSession

from config.config import get_learnhouse_config
from src.security.features_utils.plan_check import get_org_plan
from src.security.features_utils.plans import plan_meets_requirement
from src.services.ai.llm.provider import DEFAULT_PROVIDER, _GOOGLE_ALIASES

logger = logging.getLogger(__name__)

Tier = Literal["fast", "standard", "pro"]
Purpose = Literal["chat", "planning"]

# Per-provider tier defaults. Selected by whichever provider is actually configured
# (``ai_config.provider``) at call time — see `model_for_tier`.
#
# Gemini (Google) — CURRENT ACTIVE provider, chosen for free-tier access during
# local/demo development (see docs/prabodh/part2-gemini-provider.md). Verified via
# ai.google.dev's current model/pricing docs (August 2026): the Gemini 2.0 family is
# shut down; Gemini 2.5 is being sunset (shutdown announced for Oct 2026); the Gemini 3
# family is the current generation. All three IDs below carry a free tier except the
# pro-tier model (Gemini offers no free tier for its strongest reasoning model, by design
# — matches this tier's own "Pro-plan orgs only" gating).
#   fast     -> gemini-3.1-flash-lite   — cheapest current model, free tier; titles,
#               follow-ups, magic blocks, playgrounds/boards generation
#   standard -> gemini-3.6-flash        — current-generation Flash, free tier, cheaper
#               per-token than the older 3.5 Flash it supersedes; chat, RAG, planning/blocks
#   pro      -> gemini-3.1-pro-preview  — Google's strongest reasoning model, no free tier;
#               course planning for Pro+ plan orgs, where the cost is deliberately gated
# NOTE ("-preview" caveat): gemini-3.1-pro-preview and any "-preview"-suffixed model can be
# allowlist-gated or capacity-limited on some keys/projects. If it 404s or 429s persistently
# for your key, override LEARNHOUSE_AI_MODEL_PRO with gemini-3.5-flash (paid, no allowlist
# concerns reported) until your project's access is confirmed.
_GEMINI_TIER_DEFAULTS: dict[str, str] = {
    "fast": "gemini-3.1-flash-lite",
    "standard": "gemini-3.6-flash",
    "pro": "gemini-3.1-pro-preview",
}

# Claude (Anthropic) — the ORIGINAL Part 2 specification's target provider, kept fully
# intact and selectable via LEARNHOUSE_AI_PROVIDER=anthropic. Not currently active (see
# above) but not removed — switching back requires only a config change, not a rewrite.
#   fast     -> claude-haiku-4-5-20251001
#   standard -> claude-sonnet-5
#   pro      -> claude-opus-5
_CLAUDE_TIER_DEFAULTS: dict[str, str] = {
    "fast": "claude-haiku-4-5-20251001",
    "standard": "claude-sonnet-5",
    "pro": "claude-opus-5",
}

# Fallback used only if `ai_config.provider` is neither Google nor Anthropic (e.g. openai,
# ollama, mistral, ...) AND the operator hasn't set model_fast/standard/pro — in that case
# there is no sane vendor-specific default to guess, so this exists purely so the app never
# crashes; every non-Gemini/non-Anthropic provider SHOULD have its model env vars set
# explicitly. Gemini's defaults double as this catch-all since Gemini is broadly available.
_FALLBACK_TIER_DEFAULTS = _GEMINI_TIER_DEFAULTS


def _tier_defaults_for_provider(provider_id: str) -> dict[str, str]:
    if provider_id in _GOOGLE_ALIASES:
        return _GEMINI_TIER_DEFAULTS
    if provider_id == "anthropic":
        return _CLAUDE_TIER_DEFAULTS
    return _FALLBACK_TIER_DEFAULTS


_TIER_CONFIG_ATTR: dict[str, str] = {
    "fast": "model_fast",
    "standard": "model_standard",
    "pro": "model_pro",
}

# Maps a feature purpose to its (standard-plan tier, pro-plan tier). `planning` (course
# planning) uses `standard` for free/standard plans and `pro` for Pro+ plans; `chat` always
# uses `standard`. Interactive widget features (MagicBlocks, boards, playgrounds) intentionally
# bypass this and use the `fast` tier directly for low latency — see their routers.
_PURPOSE_TIERS: dict[str, tuple[Tier, Tier]] = {
    "chat": ("standard", "standard"),
    "planning": ("standard", "pro"),
}


def model_for_tier(tier: Tier) -> str:
    """Return the configured model name for a tier.

    Falls back to the default for that tier under whichever provider is actually
    configured (``ai_config.provider``) — Gemini and Claude each have their own default
    set (see ``_GEMINI_TIER_DEFAULTS`` / ``_CLAUDE_TIER_DEFAULTS`` above), so this never
    sends a Gemini model ID to Anthropic or vice versa just because an operator switched
    providers without also setting explicit model overrides.
    """
    cfg = get_learnhouse_config().ai_config
    explicit = getattr(cfg, _TIER_CONFIG_ATTR[tier], None)
    if explicit:
        return explicit
    provider_id = (getattr(cfg, "provider", None) or "").strip().lower() or DEFAULT_PROVIDER
    return _tier_defaults_for_provider(provider_id)[tier]


async def resolve_model_for_org(
    org_id: int,
    db_session: AsyncSession,
    *,
    purpose: Purpose = "chat",
) -> str:
    """Resolve the model name for an org and feature purpose, honoring pro-plan upgrades."""
    standard_tier, pro_tier = _PURPOSE_TIERS[purpose]
    try:
        current_plan = await get_org_plan(org_id, db_session)
        tier = pro_tier if plan_meets_requirement(current_plan, "pro") else standard_tier
    except Exception:
        logger.warning("Plan check failed for org %s; using standard tier", org_id, exc_info=True)
        tier = standard_tier
    return model_for_tier(tier)
