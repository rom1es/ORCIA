"""DeterministicCassetteLLM — 0 $ reproducible LLM test double for CI (AD-17 Layer 4)."""

from __future__ import annotations

import hashlib
import math
import struct
import time
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any

from orcia_core.ports.embedding import EMBEDDING_FIXED_DIMENSION, EmbeddingPort
from orcia_core.ports.llm_port import (
    LlmCompletionResponse,
    LlmGatewayPort,
    LlmPromptRequest,
    assert_model_orthogonality,
    compute_prompt_sha256,
)
from orcia_core.ports.llm_streaming_port import (
    LlmChatTurnOutcome,
    LlmStreamDelta,
    LlmStreamingPort,
    LlmStreamRequest,
)


@dataclass(frozen=True, slots=True)
class CassetteEntry:
    """Pre-recorded deterministic response for a prompt fingerprint or scenario."""

    content: str
    scenario_tag: str = "STANDARD"
    input_tokens: int = 64
    output_tokens: int = 128


class DeterministicCassetteLLM(LlmGatewayPort):
    """Deterministic LLM adapter replaying recorded cassettes with 0 external calls ($0 cost).

    Supports:
    - Exact `sha256:<64-hex>` prompt fingerprint lookup
    - Substring / scenario trigger matching (`WAITING_FOR_HUMAN_ARBITRATION`, `[ASSUMPTION]`)
    - AD-10 model family orthogonality verification when `executor_model_family` is set
    """

    is_cassette_adapter: bool = True

    def __init__(self, entries: dict[str, CassetteEntry] | None = None) -> None:
        self._entries: dict[str, CassetteEntry] = dict(entries or {})
        self._call_history: list[LlmPromptRequest] = []

    @property
    def call_history(self) -> tuple[LlmPromptRequest, ...]:
        """Return immutable tuple of all recorded requests."""
        return tuple(self._call_history)

    def register(self, key_or_sha256: str, entry: CassetteEntry) -> None:
        """Register a cassette entry under an exact `sha256:...` or keyword trigger."""
        self._entries[key_or_sha256] = entry

    async def complete(self, request: LlmPromptRequest) -> LlmCompletionResponse:
        """Replay a deterministic response for `request` without network calls (`0 $`)."""
        if request.executor_model_family is not None:
            assert_model_orthogonality(request.executor_model_family, request.model_family)

        self._call_history.append(request)
        prompt_hash = compute_prompt_sha256(request)

        entry = self._entries.get(prompt_hash)
        if entry is None:
            for trigger, candidate in self._entries.items():
                if not trigger.startswith("sha256:") and trigger in request.user_prompt:
                    entry = candidate
                    break

        if entry is None:
            if request.execution_mode == "FAST_PATH":
                entry = CassetteEntry(
                    content="[ASSUMPTION] Option par défaut retenue en mode Fast-Path.",
                    scenario_tag="FAST_PATH_ASSUMPTION",
                )
            elif "AMBIGU" in request.user_prompt.upper():
                entry = CassetteEntry(
                    content="WAITING_FOR_HUMAN_ARBITRATION",
                    scenario_tag="WAITING_FOR_HUMAN_ARBITRATION",
                )
            else:
                entry = CassetteEntry(
                    content=f"DETERMINISTIC_ACK:{prompt_hash[:19]}",
                    scenario_tag="DEFAULT_CASSETTE",
                )

        return LlmCompletionResponse(
            content=entry.content,
            model_family=request.model_family,
            model_id=request.model_id,
            prompt_sha256=prompt_hash,
            input_tokens=entry.input_tokens,
            output_tokens=entry.output_tokens,
            estimated_cost_usd=0.0,
            scenario_tag=entry.scenario_tag,
        )


def _cassette_vector_1024(text: str) -> list[float]:
    """Derive a deterministic 1024-dim unit-normalized vector from `text` ($0 cost)."""
    current = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < EMBEDDING_FIXED_DIMENSION:
        current = hashlib.sha256(current).digest()
        for val in struct.unpack("8f", current):
            values.append(val if math.isfinite(val) else 0.0)
            if len(values) == EMBEDDING_FIXED_DIMENSION:
                break
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [round(v / norm, 6) for v in values]


class DeterministicCassetteEmbedding(EmbeddingPort):
    """Deterministic 1024-dim embedding adapter for CI/E2E cassette mode (`0 $` network calls)."""

    @property
    def dimension(self) -> int:
        return EMBEDDING_FIXED_DIMENSION

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [_cassette_vector_1024(text) for text in texts]

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        return await self.embed(texts)

    async def embed_query(self, query: str) -> list[float]:
        return _cassette_vector_1024(query)

    def embed_query_sync(self, query: str) -> list[float]:
        return _cassette_vector_1024(query)


class DeterministicCassetteLlmStreamingAdapter(LlmStreamingPort):
    """Deterministic `LlmStreamingPort` adapter for CI/E2E cassette mode (`0 $` network calls)."""

    is_cassette_adapter: bool = True

    def __init__(self, *, canned_reply: str | None = None) -> None:
        self._canned_reply = canned_reply

    def _build_reply(self, request: LlmStreamRequest) -> tuple[str, str, int, int]:
        user_msg = next(
            (
                str(m.get("content") or "")
                for m in reversed(request.messages)
                if m.get("role") == "user"
            ),
            "",
        )
        digest = hashlib.sha256(user_msg.encode("utf-8")).hexdigest()
        reply = self._canned_reply or f"DETERMINISTIC_ACK:sha256:{digest[:12]}"
        thinking = "Cassette deterministic reasoning."
        in_tok = max(1, sum(len(str(m.get("content") or "")) for m in request.messages) // 4)
        out_tok = max(1, (len(reply) + len(thinking)) // 4)
        return reply, thinking, in_tok, out_tok

    async def complete_chat(self, request: LlmStreamRequest) -> LlmChatTurnOutcome | None:
        t0 = time.perf_counter()
        reply, thinking, in_tok, out_tok = self._build_reply(request)
        return LlmChatTurnOutcome(
            content=reply,
            thinking_text=thinking,
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            input_tokens=in_tok,
            output_tokens=out_tok,
            usage_source="estimated",
        )

    async def stream_chat_sse(self, request: LlmStreamRequest) -> AsyncIterator[LlmStreamDelta]:
        t0 = time.perf_counter()
        reply, thinking, in_tok, out_tok = self._build_reply(request)
        yield LlmStreamDelta(
            event="thinking_delta",
            delta=thinking,
            thinking_text=thinking,
            elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
        )
        acc: list[str] = []
        for chunk in reply.splitlines(keepends=True) or [reply]:
            acc.append(chunk)
            yield LlmStreamDelta(
                event="token_delta",
                delta=chunk,
                accumulated_text="".join(acc),
            )
        yield LlmStreamDelta(
            event="turn_completed",
            accumulated_text=reply,
            thinking_text=thinking,
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            input_tokens=in_tok,
            output_tokens=out_tok,
            usage_source="estimated",
        )


def build_cassette_gateway_plugin(**kwargs: Any) -> LlmGatewayPort:
    """Entry point target for `cassette` deterministic CI LLM gateway."""
    return DeterministicCassetteLLM(**kwargs)
