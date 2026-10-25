"""DeterministicCassetteLLM — 0 $ reproducible LLM test double for CI (AD-17 Layer 4)."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_core.ports.llm_port import (
    LlmCompletionResponse,
    LlmGatewayPort,
    LlmPromptRequest,
    assert_model_orthogonality,
    compute_prompt_sha256,
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
