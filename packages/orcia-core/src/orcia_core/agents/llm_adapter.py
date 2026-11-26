"""Agnostic `ReflexiveLlmPort` adapter bridging live workspace LLMs & test cassettes (`Story 30.3`).

Uses the workspace's configured `LlmEndpointConfig` via `LlmStreamingPort` in live production
(or an injected `LlmGatewayPort` test double in unit/cassette tests) with zero hardcoded
fallback to `DeterministicCassetteLLM` or `docs/product/capabilities.yaml`.
Preserves `\\n` and Markdown indentation verbatim across streamed chunks.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from orcia_core.agents._agents_locales import get_agent_runtime_copy
from orcia_core.agents._cassette_reflexive_decisions import (
    build_deterministic_cassette_decision,
    resolve_locale_key,
)
from orcia_core.agents.errors import ProcessModelNotConfiguredError
from orcia_core.ports.llm_port import LlmGatewayPort, LlmPromptRequest
from orcia_core.ports.llm_streaming_port import (
    LlmEndpointConfig,
    LlmStreamingPort,
    LlmStreamRequest,
)
from orcia_core.ports.reflexive_runtime_ports import (
    ReflexiveLlmChunk,
    ReflexiveLlmPort,
    ReflexiveTurnDecision,
    ReflexiveTurnInput,
)

LlmEndpointResolver = Callable[[str | None], Awaitable[LlmEndpointConfig | None]]
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL | re.IGNORECASE)


def _slice_preserving_newlines(text: str, chunk_chars: int = 80) -> list[str]:
    if not text:
        return []
    step = max(16, chunk_chars)
    return [text[idx : idx + step] for idx in range(0, len(text), step)]


def _try_parse_json_decision(raw: str, tokens: int) -> ReflexiveTurnDecision | None:
    candidate = raw.strip()
    fence_match = _JSON_FENCE_RE.match(candidate)
    if fence_match:
        candidate = fence_match.group(1).strip()
    if not candidate.startswith("{"):
        return None
    try:
        parsed: dict[str, Any] = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    parsed.setdefault("tokens_used", tokens)
    return ReflexiveTurnDecision.model_validate(parsed)


class GatewayReflexiveLlmAdapter(ReflexiveLlmPort):
    """Bridges live workspace `LlmStreamingPort` or test `LlmGatewayPort` to `ReflexiveLlmPort`."""

    def __init__(
        self,
        llm_gateway: LlmGatewayPort | None = None,
        *,
        streaming_port: LlmStreamingPort | None = None,
        endpoint_resolver: LlmEndpointResolver | None = None,
        model_family: str = "agnostic-default",
        model_id: str = "orcia-reflexive-default",
    ) -> None:
        self._gateway = llm_gateway
        self._streaming_port = streaming_port
        self._endpoint_resolver = endpoint_resolver
        self._model_family = model_family
        self._model_id = model_id

    def _is_cassette_mode(self) -> bool:
        return bool(
            self._gateway is not None and getattr(self._gateway, "is_cassette_adapter", False)
        )

    async def decide_next_turn(self, turn_input: ReflexiveTurnInput) -> ReflexiveTurnDecision:
        """Query live workspace LLM (or explicit test cassette) for next `ReflexiveTurnDecision`."""
        loc = resolve_locale_key(turn_input.locale)
        copy = get_agent_runtime_copy(loc)
        system_prompt = (
            "You are an ORCIA reflexive agent orchestrating read-only surgical exploration "
            "and governed outputs. Respond clearly in the user's language ("
            f"{loc})."
        )
        user_payload: dict[str, Any] = {
            "actor_slug": turn_input.actor_slug,
            "objective": turn_input.objective,
            "turn_index": turn_input.turn_index,
            "force_final": turn_input.force_final,
            "initial_resources": list(turn_input.initial_resources),
            "scratchpad": list(turn_input.scratchpad),
        }
        user_prompt = json.dumps(user_payload, ensure_ascii=False, sort_keys=True)

        if (
            not self._is_cassette_mode()
            and self._streaming_port is not None
            and self._endpoint_resolver is not None
        ):
            endpoint = await self._endpoint_resolver(turn_input.workspace_id)
            if endpoint is None:
                raise ProcessModelNotConfiguredError()
            outcome = await self._streaming_port.complete_chat(
                LlmStreamRequest(
                    endpoint=endpoint,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    stream=False,
                    include_thoughts=True,
                )
            )
            if outcome is None:
                raise ProcessModelNotConfiguredError()
            tokens = max(1, outcome.input_tokens + outcome.output_tokens)
            parsed = _try_parse_json_decision(outcome.content, tokens)
            if parsed is not None:
                if not parsed.thought_text and outcome.thinking_text.strip():
                    return parsed.model_copy(update={"thought_text": outcome.thinking_text.strip()})
                return parsed
            content = outcome.content.strip()
            if not content:
                raise ProcessModelNotConfiguredError()
            return ReflexiveTurnDecision(
                group_title=copy.synthesis_group_title,
                thought_text=outcome.thinking_text.strip(),
                action_kind="final_answer",
                final_markdown=content,
                tokens_used=tokens,
            )

        if self._gateway is None:
            raise ProcessModelNotConfiguredError()

        completion = await self._gateway.complete(
            LlmPromptRequest(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_family=self._model_family,
                model_id=self._model_id,
            )
        )
        tokens = max(1, completion.input_tokens + completion.output_tokens)
        raw = completion.content.strip()
        parsed = _try_parse_json_decision(raw, tokens)
        if parsed is not None:
            return parsed

        if self._is_cassette_mode():
            return build_deterministic_cassette_decision(turn_input, tokens)

        if not raw:
            raise ProcessModelNotConfiguredError()
        return ReflexiveTurnDecision(
            group_title=copy.synthesis_group_title,
            thought_text="",
            action_kind="final_answer",
            final_markdown=raw,
            tokens_used=tokens,
        )

    async def stream_turn_deltas(
        self,
        turn_input: ReflexiveTurnInput,
        decision: ReflexiveTurnDecision,
    ) -> AsyncIterator[ReflexiveLlmChunk]:
        """Yield character-faithful `thinking_delta` and `answer_delta` chunks (`\\n` preserved)."""
        del turn_input
        for piece in _slice_preserving_newlines(decision.thought_text, chunk_chars=64):
            yield ReflexiveLlmChunk(thinking_delta=piece)
        if decision.action_kind == "final_answer" and decision.final_markdown:
            for piece in _slice_preserving_newlines(decision.final_markdown, chunk_chars=72):
                yield ReflexiveLlmChunk(answer_delta=piece)


__all__ = ["GatewayReflexiveLlmAdapter", "LlmEndpointResolver"]
