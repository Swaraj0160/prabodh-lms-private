"""Regression tests for the AI Course Creator's max_tokens truncation bug.

Root cause: `generate_course_plan_stream` and `generate_activity_content_stream`
called `generate_stream()` without an explicit `max_tokens`, so both silently
inherited the shared cost-control default (`client.DEFAULT_MAX_OUTPUT_TOKENS`,
4096 — sized for short chat replies). A full course plan or a full activity's
ProseMirror JSON (headings, paragraphs, callouts, lists, an embedded quiz) is
verbose enough to exceed that ceiling on a real request, so generation was cut
off mid-JSON-string. The frontend's `parseActivityContentFromStream()` /
`extract_plan_from_response()` then fail to parse the truncated JSON, and the
user sees a generic "Failed to parse content" / "An internal error occurred
while generating the stream." with no indication of the real cause.

Reproduced against a real Gemini call before the fix: a real activity request
ran to 12k+ characters and was still mid-quiz-question at the 4096-token
cutoff (`Unterminated string` on `json.loads`). See
docs/prabodh/part2-gemini-provider.md's "Course Creator" section for the full
incident writeup.

These tests cover both layers:
  - A fast, mocked unit test asserting the explicit `max_tokens=16000` is
    actually passed at both call sites (catches an accidental revert without
    needing network access).
  - `test_llm_gemini.py::test_activity_content_generation_does_not_truncate`
    is the live-Gemini counterpart that reproduces the actual failure mode
    against a real key — a mocked test alone cannot catch a real provider
    truncating a real response.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.services.ai import courseplanning as cp
from src.services.ai.schemas.courseplanning import CoursePlanningSessionData


async def _fake_stream(chunks):
    for c in chunks:
        yield c


@pytest.mark.asyncio
async def test_generate_course_plan_stream_passes_explicit_max_tokens(monkeypatch):
    captured = {}

    def _spy_generate_stream(**kwargs):
        captured.update(kwargs)
        return _fake_stream(['{"name": "Test", "chapters": []}'])

    monkeypatch.setattr(cp, "generate_stream", _spy_generate_stream)
    monkeypatch.setattr(cp, "save_course_planning_session", lambda session: None)

    session = CoursePlanningSessionData(session_uuid="s1", org_id=1)

    chunks = []
    async for chunk in cp.generate_course_plan_stream(
        prompt="Create a course",
        session=session,
        model_name="test-model",
    ):
        chunks.append(chunk)

    assert captured.get("max_tokens") == 16000
    # Sanity: the spy actually ran and the generator forwarded its chunks.
    assert chunks == ['{"name": "Test", "chapters": []}']


@pytest.mark.asyncio
async def test_generate_activity_content_stream_passes_explicit_max_tokens(monkeypatch):
    captured = {}

    def _spy_generate_stream(**kwargs):
        captured.update(kwargs)
        return _fake_stream(['{"type": "doc", "content": []}'])

    monkeypatch.setattr(cp, "generate_stream", _spy_generate_stream)
    monkeypatch.setattr(cp, "save_course_planning_session", lambda session: None)

    session = CoursePlanningSessionData(session_uuid="s1", org_id=1)

    async for _ in cp.generate_activity_content_stream(
        session=session,
        activity_uuid="a1",
        activity_name="Test Activity",
        activity_description="Test",
        chapter_name="Chapter 1",
        course_name="Test Course",
        course_description="Test",
        model_name="test-model",
    ):
        pass

    assert captured.get("max_tokens") == 16000
