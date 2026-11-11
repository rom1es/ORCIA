"""Agnostic `ReflexiveLlmPort` adapter bridging `LlmGatewayPort` (`Story 16.2`).

Supports both structured JSON `ReflexiveTurnDecision` responses from live/cassette LLMs and
zero-cost deterministic multi-turn plans when backed by `DeterministicCassetteLLM`.
Preserves `\n` and Markdown indentation verbatim across streamed chunks (zero word-splitting).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from orcia_core.ports.llm_port import LlmGatewayPort, LlmPromptRequest
from orcia_core.ports.reflexive_runtime_ports import (
    ReflexiveLlmChunk,
    ReflexiveLlmPort,
    ReflexiveTurnDecision,
    ReflexiveTurnInput,
)
from orcia_core.ports.surgical_explorer_port import SurgicalPrimitiveName

_DEFAULT_FALLBACK_RESOURCE = "docs/product/capabilities.yaml"


def _slice_preserving_newlines(text: str, chunk_chars: int = 80) -> list[str]:
    """Slice `text` into contiguous character spans preserving every `\n` and space verbatim."""
    if not text:
        return []
    step = max(16, chunk_chars)
    return [text[idx : idx + step] for idx in range(0, len(text), step)]


class GatewayReflexiveLlmAdapter(ReflexiveLlmPort):
    """Bridges `LlmGatewayPort` (`LiteLLMAdapter` / `CassetteLLM`) to `ReflexiveLlmPort`."""

    def __init__(
        self,
        llm_gateway: LlmGatewayPort,
        *,
        model_family: str = "agnostic-default",
        model_id: str = "orcia-reflexive-default",
    ) -> None:
        self._gateway = llm_gateway
        self._model_family = model_family
        self._model_id = model_id

    async def decide_next_turn(self, turn_input: ReflexiveTurnInput) -> ReflexiveTurnDecision:
        """Query `LlmGatewayPort` and resolve a structured `ReflexiveTurnDecision`."""
        system_prompt = (
            "You are an ORCIA reflexive agent orchestrating read-only surgical exploration "
            "and governed outputs. Respond in the user's language ("
            f"{turn_input.locale})."
        )
        user_prompt = json.dumps(
            {
                "actor_slug": turn_input.actor_slug,
                "objective": turn_input.objective,
                "turn_index": turn_input.turn_index,
                "force_final": turn_input.force_final,
                "scratchpad_len": len(turn_input.scratchpad),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
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
        if raw.startswith("{"):
            parsed: dict[str, Any] = json.loads(raw)
            parsed.setdefault("tokens_used", tokens)
            return ReflexiveTurnDecision.model_validate(parsed)

        return self._build_deterministic_cassette_decision(turn_input, tokens)

    async def stream_turn_deltas(
        self,
        turn_input: ReflexiveTurnInput,
        decision: ReflexiveTurnDecision,
    ) -> AsyncIterator[ReflexiveLlmChunk]:
        """Yield character-faithful `thinking_delta` and `answer_delta` chunks (`\n` preserved)."""
        del turn_input
        for piece in _slice_preserving_newlines(decision.thought_text, chunk_chars=64):
            yield ReflexiveLlmChunk(thinking_delta=piece)
        if decision.action_kind == "final_answer" and decision.final_markdown:
            for piece in _slice_preserving_newlines(decision.final_markdown, chunk_chars=72):
                yield ReflexiveLlmChunk(answer_delta=piece)

    def _build_deterministic_cassette_decision(
        self,
        turn_input: ReflexiveTurnInput,
        tokens: int,
    ) -> ReflexiveTurnDecision:
        if turn_input.force_final:
            return self._build_final_synthesis_decision(turn_input, tokens)

        # Step 1: Surgical inspection of initial resource (or default workspace registry)
        has_surgical_obs = any(
            item.get("action_kind")
            in (
                SurgicalPrimitiveName.INSPECT_RESOURCE_LINES.value,
                SurgicalPrimitiveName.CHECK_RESOURCE_STATE.value,
            )
            for item in turn_input.scratchpad
        )
        if not has_surgical_obs:
            target_uri = (
                turn_input.initial_resources[0]
                if turn_input.initial_resources
                else _DEFAULT_FALLBACK_RESOURCE
            )
            return ReflexiveTurnDecision(
                group_title="Inspection chirurgicale des sources de l'Espace",
                thought_text=(
                    f"Analysons un extrait ciblé de `{target_uri}` (`#L1-35`)\n"
                    "afin d'ancrer la réponse sur les lignes exactes."
                ),
                action_kind="surgical_primitive",
                primitive=SurgicalPrimitiveName.INSPECT_RESOURCE_LINES,
                resource_uri=target_uri,
                start_line=1,
                end_line=35,
                tokens_used=tokens,
            )

        # Step 1b: Governed @Agent sub-delegation when enabled & available (depth-capped by runtime)
        has_delegated = any(
            item.get("action_kind")
            in ("sub_agent_result", "delegation_blocked", "delegate_sub_agent")
            for item in turn_input.scratchpad
        )
        if (
            turn_input.allow_sub_agent_delegation
            and turn_input.available_delegate_agents
            and not has_delegated
        ):
            delegate_slug = turn_input.available_delegate_agents[0]
            return ReflexiveTurnDecision(
                group_title="Vérification croisée par un agent spécialisé",
                thought_text=(
                    f"Sollicitons @{delegate_slug} pour croiser les constats documentaires\n"
                    "avec les exigences métier de l'Espace."
                ),
                action_kind="delegate_sub_agent",
                delegate_agent_slug=delegate_slug,
                delegate_sub_objective=(
                    f"Vérifier la cohérence métier pour : {turn_input.objective}"
                ),
                tokens_used=tokens,
            )

        # Step 2: Optional governed external write preview if requested and not yet resolved
        write_spec = turn_input.requested_write_preview
        has_write_resolution = any(
            item.get("action_kind") in ("external_write_approved", "external_write_rejected")
            for item in turn_input.scratchpad
        )
        if write_spec is not None and not has_write_resolution:
            return ReflexiveTurnDecision(
                group_title="Préparation de l'aperçu d'écriture gouvernée",
                thought_text=(
                    "Préparons la carte d'aperçu avant toute écriture externe\n"
                    "pour soumettre la modification à validation humaine."
                ),
                action_kind="propose_external_write_preview",
                connector_type=str(write_spec.get("connector_type") or "mcp:enterprise-docs"),
                write_action=str(write_spec.get("action") or "publish_document"),
                write_target_uri=str(
                    write_spec.get("target_resource_uri") or "catalog://docs/deliverable"
                ),
                write_summary=str(
                    write_spec.get("action_summary") or "Valider la publication du livrable"
                ),
                write_payload=dict(write_spec.get("payload") or {"content": turn_input.objective}),
                tokens_used=tokens,
            )

        return self._build_final_synthesis_decision(turn_input, tokens)

    def _build_final_synthesis_decision(
        self,
        turn_input: ReflexiveTurnInput,
        tokens: int,
    ) -> ReflexiveTurnDecision:
        citations: list[str] = []
        write_notes: list[str] = []
        for idx, item in enumerate(turn_input.scratchpad, start=1):
            uri = str(item.get("resource_uri") or "")
            anchor = str(item.get("line_anchor") or "")
            kind = str(item.get("action_kind") or "")
            if kind in ("external_write_approved", "external_write_rejected"):
                write_notes.append(f"- {item.get('summary', '')}")
            elif uri:
                citations.append(f"- `[S{idx}]` `{uri}` {anchor}".rstrip())
        refs_block = "\n".join(citations) if citations else "- Aucune source additionnelle."
        writes_block = (
            ("\n\n### Gouvernance d'écriture\n" + "\n".join(write_notes)) if write_notes else ""
        )
        markdown = (
            f"## Synthèse — {turn_input.objective}\n\n"
            "### Sources inspectées\n"
            f"{refs_block}"
            f"{writes_block}\n\n"
            "```markdown\n"
            "  Livrable structuré vérifié par lecture chirurgicale.\n"
            "```\n"
        )
        return ReflexiveTurnDecision(
            group_title="Consolidation du livrable final",
            thought_text="Synthèse finale prête à partir des observations collectées.",
            action_kind="final_answer",
            final_markdown=markdown,
            tokens_used=tokens,
        )
