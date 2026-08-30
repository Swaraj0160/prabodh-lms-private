"""Live tests against a real Gemini API key — the same purpose test_llm_ollama.py serves
for Ollama: prove the provider-agnostic layer actually works end-to-end against a real
provider, not just against mocks.

These exist because a real, previously-shipped bug (``result.usage()`` called as a method
when it is actually a property on Pydantic AI's result objects — see
docs/prabodh/part2-gemini-provider.md) passed every existing mocked unit test and was only
caught by a live call. Mocked ``Agent``/result objects don't reproduce a real
property-vs-method mismatch; only a real provider call does.

Opt-in and skipped automatically unless ``LEARNHOUSE_AI_PROVIDER=google`` (or unset, since
that's the default) AND a real key is present via ``LEARNHOUSE_AI_API_KEY`` or
``LEARNHOUSE_GEMINI_API_KEY`` — so CI and any environment without a configured key never
attempts a network call. Never asserts on the literal content of a model response (that's
inherently non-deterministic); asserts only on shape/success, mirroring test_llm_ollama.py.

Run locally with a real key already in apps/api/.env:
    pytest -m gemini_live src/tests/services/test_llm_gemini.py
"""

import os

import pytest

from config.config import get_learnhouse_config
from src.services.ai.llm import client as llm_client
from src.services.ai.llm.tiers import model_for_tier


def _gemini_configured() -> bool:
    try:
        cfg = get_learnhouse_config().ai_config
    except Exception:
        return False
    provider = (getattr(cfg, "provider", None) or "google").strip().lower()
    if provider not in ("google", "google-gla", "gemini"):
        return False
    return bool(getattr(cfg, "api_key", None) or getattr(cfg, "gemini_api_key", None))


pytestmark = [
    pytest.mark.gemini_live,
    pytest.mark.skipif(
        not _gemini_configured(),
        reason="No Gemini API key configured (LEARNHOUSE_AI_API_KEY / LEARNHOUSE_GEMINI_API_KEY)",
    ),
]

FAST_MODEL = model_for_tier("fast")
STANDARD_MODEL = model_for_tier("standard")


@pytest.mark.asyncio
async def test_generate_returns_text():
    """Regression test for the `.usage()` vs `.usage` bug: generate() must return
    real text without raising, which requires the post-call usage-logging line to
    not crash on a real (non-mocked) result object."""
    text = await llm_client.generate(
        model_name=FAST_MODEL,
        user_prompt="Reply with the single word: pong",
        system_prompt="You are a terse assistant.",
        timeout=30.0,
    )
    assert isinstance(text, str) and text.strip()


@pytest.mark.asyncio
async def test_generate_stream_yields_chunks():
    """Regression test for the streaming half of the same bug — and for the
    Gemini-3 'thinking model' token-budget-sharing behavior (see
    docs/prabodh/part2-gemini-provider.md): uses the real production default
    (no explicit max_tokens), not an artificially tiny budget that would starve
    a thinking model's visible output."""
    chunks = []
    async for chunk in llm_client.generate_stream(
        model_name=STANDARD_MODEL,
        user_prompt="Count from 1 to 5 separated by spaces.",
        system_prompt="You are a terse assistant.",
        timeout=30.0,
    ):
        chunks.append(chunk)
    assert chunks
    assert "".join(chunks).strip()


@pytest.mark.asyncio
async def test_generate_with_explicit_small_max_tokens_on_fast_tier():
    """The fast tier (used for chat titles / follow-ups with max_tokens=30/150 in
    base.py) must not exhibit the thinking-model starvation seen on the standard
    tier — confirms those two existing small-budget call sites remain safe."""
    text = await llm_client.generate(
        model_name=FAST_MODEL,
        user_prompt="Reply with the single word: pong",
        max_tokens=10,
        timeout=30.0,
    )
    assert isinstance(text, str) and text.strip()


@pytest.mark.asyncio
async def test_embeddings_return_correct_dimensions():
    from src.services.ai.llm import embed_query

    vec = await embed_query("test query")
    assert len(vec) == 768  # matches the pgvector column; see embeddings.py


@pytest.mark.asyncio
async def test_activity_content_generation_does_not_truncate():
    """Regression test for the AI Course Creator bug: a real, richly-structured
    activity request (headings, paragraphs, callouts, lists, an embedded quiz)
    must come back as complete, parseable JSON — not cut off mid-string by the
    shared 4096-token default. Reproduces the exact real-world failure: before
    the fix (explicit max_tokens=16000 in generate_activity_content_stream),
    this exact request truncated at 12k+ characters, still mid-quiz-question.
    See docs/prabodh/part2-gemini-provider.md and
    test_courseplanning_service.py for the full incident writeup and the
    fast/mocked counterpart of this test.
    """
    import json

    from src.services.ai.courseplanning import build_activity_content_system_prompt
    from src.services.ai.llm import generate_stream

    system_prompt = build_activity_content_system_prompt(
        course_name="Grade 5 Math Fundamentals",
        course_description="A math course for grade 5",
        chapter_name="Large Numbers and Advanced Arithmetic",
        activity_name="Understanding Place Value up to Millions",
        activity_description="Learn to read, write, and compare numbers up to 7 digits",
        language="en",
    )

    full = ""
    async for chunk in generate_stream(
        model_name=STANDARD_MODEL,
        user_prompt="Generate comprehensive educational content for this activity: Understanding Place Value up to Millions",
        system_prompt=system_prompt,
        temperature=0.7,
        timeout=120.0,
        max_tokens=16000,  # the actual fix — mirror the real call site
    ):
        full += chunk

    parsed = json.loads(full)  # raises if truncated/invalid — the original bug
    assert parsed.get("type") == "doc"
    assert parsed.get("content")
