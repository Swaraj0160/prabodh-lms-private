"""Unified, provider-neutral generation helpers.

All AI text generation in the backend goes through ``generate`` / ``generate_stream`` so the
underlying provider is a config concern, not a code concern. These wrap Pydantic AI's
``Agent`` and translate the app's stored message/attachment formats into Pydantic AI types.
"""

from __future__ import annotations

import base64
import logging
from typing import Any, AsyncGenerator, Optional, Sequence, Type, Union

from pydantic_ai import Agent
from pydantic_ai.messages import (
    BinaryContent,
    DocumentUrl,
    ImageUrl,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
    VideoUrl,
)
from pydantic_ai.settings import ModelSettings

from src.services.ai.llm.provider import build_model

logger = logging.getLogger(__name__)

# Per-request timeouts (seconds). Mirrors the previous hand-rolled asyncio timeouts.
DEFAULT_TIMEOUT = 60.0
STREAM_TIMEOUT = 90.0

# Cost-control backstop: cap output tokens even when a call site doesn't pass
# its own `max_tokens`. Credits/rate-limiting bound request *count*, not a
# single request's own runaway generation length — without this, an
# unbounded response from any provider (Claude included) is billed and timed
# entirely at the provider's own default ceiling. 4096 output tokens comfortably
# covers every current feature's real output (chat replies, editor content,
# generated blocks) while capping worst-case per-request cost. Override via a
# larger explicit `max_tokens` at the call site for a feature that genuinely
# needs more (e.g. long-form course planning).
DEFAULT_MAX_OUTPUT_TOKENS = 4096

# A single user turn: a prompt string plus optional multimodal parts (images/docs/video).
UserPrompt = Union[str, Sequence[Any]]


def to_message_history(stored: Any) -> list[ModelMessage]:
    """Convert stored chat history into Pydantic AI ``ModelMessage`` objects.

    Accepts the Redis JSON format (``[{"role": "user"|"model", "content": str}, ...]``) and
    the legacy object format (``msg.type``/``msg.content``). Unknown entries are skipped.
    """
    messages: list[ModelMessage] = []
    if not stored:
        return messages

    items = getattr(stored, "messages", stored)
    for msg in items:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            role, content = msg["role"], msg["content"]
        elif hasattr(msg, "type") and hasattr(msg, "content"):
            role = "user" if msg.type == "human" else "model"
            content = msg.content
        else:
            continue

        if not content:
            continue
        if role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=content)]))
    return messages


def attachments_to_parts(attachments: Any) -> list:
    """Convert ``AttachmentData``-like objects into Pydantic AI multimodal parts.

    Replaces the Gemini-specific ``inline_data``/``file_data`` dicts. Note: video/YouTube and
    URL-based documents are only honored by providers that support them (e.g. Gemini); other
    providers will ignore or reject them — an inherent provider capability difference.
    """
    parts: list = []
    for att in attachments or []:
        a_type = getattr(att, "type", None)
        url = getattr(att, "url", None)
        b64 = getattr(att, "content_base64", None)
        mime = getattr(att, "mime_type", None)

        if a_type == "youtube" and url:
            parts.append(VideoUrl(url=url))
        elif a_type in ("image", "file") and b64 and mime:
            # content_base64 is user-supplied; a malformed/truncated value would
            # raise binascii.Error and surface as an unhandled 500. Skip the bad
            # attachment instead of crashing the whole request.
            try:
                decoded = base64.b64decode(b64)
            except Exception:
                logger.warning("Skipping attachment with invalid base64 content")
                continue
            parts.append(BinaryContent(data=decoded, media_type=mime))
        elif a_type == "image" and url:
            parts.append(ImageUrl(url=url))
        elif a_type == "file" and url:
            parts.append(DocumentUrl(url=url))
    return parts


def _settings(
    max_tokens: Optional[int], temperature: Optional[float], timeout: float
) -> ModelSettings:
    settings: dict = {
        "timeout": timeout,
        "max_tokens": max_tokens if max_tokens is not None else DEFAULT_MAX_OUTPUT_TOKENS,
    }
    if temperature is not None:
        settings["temperature"] = temperature
    return ModelSettings(**settings)


def _agent(model_name: str, system_prompt: Optional[str], output_type: Any) -> Agent:
    return Agent(
        build_model(model_name),
        output_type=output_type,
        system_prompt=system_prompt or (),
    )


def _log_usage(model_name: str, usage: Any, *, ok: bool, feature: Optional[str] = None) -> None:
    """Log token usage for a completed generation. Never raises — usage logging must
    never take down an otherwise-successful AI response.

    This is request-level technical observability (model, token counts, success),
    deliberately separate from the org-facing credit accounting in
    ``security.features_utils.usage`` (which already tracks per-org spend against
    plan limits in Redis). Logs, not a DB table: cheap, ships to whatever log
    aggregation the deployment already has, and adds no migration/schema risk for
    a metric that's operational rather than billing-authoritative. Never logs
    prompt/response content — only counts.
    """
    try:
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)
        logger.info(
            "ai_usage model=%s feature=%s ok=%s input_tokens=%s output_tokens=%s",
            model_name, feature or "unknown", ok, input_tokens, output_tokens,
        )
    except Exception:
        logger.debug("AI usage logging failed", exc_info=True)


async def generate(
    *,
    model_name: str,
    user_prompt: UserPrompt,
    system_prompt: Optional[str] = None,
    history: Any = None,
    output_type: Type[Any] = str,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    timeout: float = DEFAULT_TIMEOUT,
    feature: Optional[str] = None,
) -> Any:
    """Run a single (non-streaming) generation.

    Returns plain text when ``output_type`` is ``str``, or a validated instance of
    ``output_type`` (a Pydantic model) for structured output. ``feature`` is an
    optional label (e.g. "quiz", "chat") purely for the usage log line.
    """
    agent = _agent(model_name, system_prompt, output_type)
    try:
        result = await agent.run(
            user_prompt,
            message_history=to_message_history(history) or None,
            model_settings=_settings(max_tokens, temperature, timeout),
        )
    except Exception:
        _log_usage(model_name, None, ok=False, feature=feature)
        raise
    try:
        usage = result.usage
    except Exception:
        # Defense-in-depth: a future pydantic-ai API change to `.usage` must
        # never take down an otherwise-successful generation just because the
        # usage-logging line couldn't read it. (This exact bug happened once
        # already — `.usage()` vs `.usage` — caught by a live smoke test, not
        # by unit tests, since mocked result objects don't reproduce a real
        # property-vs-method mismatch.)
        usage = None
    _log_usage(model_name, usage, ok=True, feature=feature)
    return result.output


async def generate_stream(
    *,
    model_name: str,
    user_prompt: UserPrompt,
    system_prompt: Optional[str] = None,
    history: Any = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    timeout: float = STREAM_TIMEOUT,
    feature: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Stream text deltas for a single generation, yielding chunks as they arrive.

    ``feature`` is an optional label (e.g. "chat", "editor") purely for the usage
    log line emitted once the stream completes.
    """
    agent = _agent(model_name, system_prompt, str)
    ok = False
    try:
        async with agent.run_stream(
            user_prompt,
            message_history=to_message_history(history) or None,
            model_settings=_settings(max_tokens, temperature, timeout),
        ) as result:
            async for chunk in result.stream_text(delta=True):
                yield chunk
            ok = True
            try:
                usage = result.usage
            except Exception:
                # Same defense-in-depth as generate(): a broken `.usage` read must
                # never look like a stream failure to the caller when the content
                # was already fully yielded — that would incorrectly trigger the
                # router's refund-on-failure path for a request that actually
                # succeeded.
                usage = None
            _log_usage(model_name, usage, ok=True, feature=feature)
    except Exception:
        if not ok:
            _log_usage(model_name, None, ok=False, feature=feature)
        raise
