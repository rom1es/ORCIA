"""Deterministic cassette turn decision helpers (`Story 30.3`, test-only usage)."""

from __future__ import annotations

from orcia_core.agents._agents_locales import get_agent_runtime_copy
from orcia_core.kernel.enums import SupportedLocale
from orcia_core.ports.reflexive_runtime_ports import (
    ReflexiveTurnDecision,
    ReflexiveTurnInput,
)
from orcia_core.ports.surgical_explorer_port import SurgicalPrimitiveName


def resolve_locale_key(raw_locale: str) -> SupportedLocale:
    """Resolve `fr` or `en` locale code from arbitrary locale strings."""
    return "en" if str(raw_locale).strip().lower().startswith("en") else "fr"


def is_surgical_inspectable_uri(uri: str) -> bool:
    """Return True only when `uri` targets an authorized local/virtual surgical path."""
    cleaned = uri.strip()
    if cleaned.startswith("virtual://"):
        return True
    if "://" in cleaned:
        return False
    return cleaned.startswith(("packs/", "docs/", "specs/"))


def build_final_synthesis_decision(
    turn_input: ReflexiveTurnInput,
    tokens: int,
) -> ReflexiveTurnDecision:
    """Build deterministic final synthesis decision from collected scratchpad observations."""
    loc = resolve_locale_key(turn_input.locale)
    copy = get_agent_runtime_copy(loc)
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
    refs_block = "\n".join(citations) if citations else copy.synthesis_empty_refs
    writes_block = (copy.synthesis_writes_heading + "\n".join(write_notes)) if write_notes else ""
    markdown = (
        f"{copy.synthesis_heading_tpl.format(objective=turn_input.objective)}"
        f"{copy.synthesis_sources_heading}"
        f"{refs_block}"
        f"{writes_block}\n\n"
        "```markdown\n"
        f"{copy.synthesis_code_note}"
        "```\n"
    )
    return ReflexiveTurnDecision(
        group_title=copy.synthesis_group_title,
        thought_text=copy.synthesis_thought,
        action_kind="final_answer",
        final_markdown=markdown,
        tokens_used=tokens,
    )


def build_deterministic_cassette_decision(
    turn_input: ReflexiveTurnInput,
    tokens: int,
) -> ReflexiveTurnDecision:
    """Build a deterministic multi-turn plan ONLY when backed by a test cassette."""
    loc = resolve_locale_key(turn_input.locale)
    copy = get_agent_runtime_copy(loc)
    if turn_input.force_final:
        return build_final_synthesis_decision(turn_input, tokens)

    has_surgical_obs = any(
        item.get("action_kind")
        in (
            SurgicalPrimitiveName.INSPECT_RESOURCE_LINES.value,
            SurgicalPrimitiveName.CHECK_RESOURCE_STATE.value,
        )
        for item in turn_input.scratchpad
    )
    inspectable_uri = next(
        (uri for uri in turn_input.initial_resources if is_surgical_inspectable_uri(uri)),
        None,
    )
    if not has_surgical_obs and inspectable_uri:
        return ReflexiveTurnDecision(
            group_title=copy.inspect_group_title,
            thought_text=copy.inspect_thought_tpl.format(target_uri=inspectable_uri),
            action_kind="surgical_primitive",
            primitive=SurgicalPrimitiveName.INSPECT_RESOURCE_LINES,
            resource_uri=inspectable_uri,
            start_line=1,
            end_line=35,
            tokens_used=tokens,
        )

    has_delegated = any(
        item.get("action_kind") in ("sub_agent_result", "delegation_blocked", "delegate_sub_agent")
        for item in turn_input.scratchpad
    )
    if (
        turn_input.allow_sub_agent_delegation
        and turn_input.available_delegate_agents
        and not has_delegated
    ):
        delegate_slug = turn_input.available_delegate_agents[0]
        return ReflexiveTurnDecision(
            group_title=copy.delegate_group_title,
            thought_text=copy.delegate_thought_tpl.format(delegate_slug=delegate_slug),
            action_kind="delegate_sub_agent",
            delegate_agent_slug=delegate_slug,
            delegate_sub_objective=copy.delegate_objective_tpl.format(
                objective=turn_input.objective
            ),
            tokens_used=tokens,
        )

    write_spec = turn_input.requested_write_preview
    has_write_resolution = any(
        item.get("action_kind") in ("external_write_approved", "external_write_rejected")
        for item in turn_input.scratchpad
    )
    if write_spec is not None and not has_write_resolution:
        return ReflexiveTurnDecision(
            group_title=copy.write_preview_group_title,
            thought_text=copy.write_preview_thought,
            action_kind="propose_external_write_preview",
            connector_type=str(write_spec.get("connector_type") or "mcp:enterprise-docs"),
            write_action=str(write_spec.get("action") or "publish_document"),
            write_target_uri=str(
                write_spec.get("target_resource_uri") or "catalog://docs/deliverable"
            ),
            write_summary=str(
                write_spec.get("action_summary") or copy.write_preview_default_summary
            ),
            write_payload=dict(write_spec.get("payload") or {"content": turn_input.objective}),
            tokens_used=tokens,
        )

    return build_final_synthesis_decision(turn_input, tokens)


__all__ = [
    "build_deterministic_cassette_decision",
    "build_final_synthesis_decision",
    "is_surgical_inspectable_uri",
    "resolve_locale_key",
]
