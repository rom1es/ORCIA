"""Pure helper functions for `NonDeterministicReflexiveRuntime` (`Story 16.2`).

Keeps `reflexive_runtime.py` concise (`< 300` lines) with low cyclomatic complexity.
Zero external SDK or connector imports.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from orcia_core.agents.errors import ReflexiveSessionExpiredError
from orcia_core.agents.reflexive_schemas import (
    MAX_DELEGATION_DEPTH_CAP,
    AgentTraceEvent,
    ProcessOrchestrationType,
    ReflexiveRuntimeConfig,
    ReflexiveScratchpadEntry,
    ReflexiveSessionSnapshot,
    ReflexiveTurnInput,
    TraceEventKind,
    compute_default_session_expiry_utc,
)
from orcia_core.ports.surgical_explorer_port import (
    SurgicalObservation,
    SurgicalPrimitiveName,
)


def build_initial_reflexive_snapshot(
    *,
    execution_id: str,
    actor_slug: str,
    objective: str,
    config: ReflexiveRuntimeConfig,
) -> ReflexiveSessionSnapshot:
    """Instantiate the initial `ReflexiveSessionSnapshot` for a reflexive run."""
    now_iso = datetime.now(UTC).isoformat()
    return ReflexiveSessionSnapshot(
        execution_id=execution_id,
        workspace_id=config.workspace_id,
        actor_slug=actor_slug,
        actor_user_id=config.actor_user_id,
        objective=objective,
        orchestration_type=ProcessOrchestrationType.NON_DETERMINISTIC,
        effort_level=config.effort_level,
        effort_mode=config.effort_mode,
        status="RUNNING",
        allow_sub_agent_delegation=(
            config.allow_sub_agent_delegation
            and config.delegation_depth < config.max_delegation_depth
        ),
        delegation_depth=config.delegation_depth,
        available_delegate_agents=list(config.available_delegate_agents),
        has_read_source=config.has_read_source,
        locale=config.locale,
        initial_resources=list(config.initial_resources),
        requested_write_preview=config.requested_write_preview,
        max_turns=config.max_turns,
        max_budget_tokens=config.max_budget_tokens,
        created_at_utc=now_iso,
        updated_at_utc=now_iso,
        expires_at_utc=compute_default_session_expiry_utc(),
    )


def build_child_delegation_config(snapshot: ReflexiveSessionSnapshot) -> ReflexiveRuntimeConfig:
    """Build bounded child sub-agent config (`allow_sub_agent_delegation=False`, shared budget)."""
    remaining_budget = max(256, snapshot.max_budget_tokens - snapshot.tokens_used)
    return ReflexiveRuntimeConfig(
        effort_level=snapshot.effort_level,
        effort_mode=snapshot.effort_mode,
        max_turns=min(4, snapshot.max_turns),
        max_budget_tokens=remaining_budget,
        allow_sub_agent_delegation=False,
        delegation_depth=snapshot.delegation_depth + 1,
        max_delegation_depth=MAX_DELEGATION_DEPTH_CAP,
        workspace_id=snapshot.workspace_id,
        actor_user_id=snapshot.actor_user_id,
        has_read_source=snapshot.has_read_source,
        locale=snapshot.locale,
    )


def assert_snapshot_not_expired(snapshot: ReflexiveSessionSnapshot) -> None:
    """Raise `ReflexiveSessionExpiredError` if `snapshot.expires_at_utc` is in the past."""
    raw_exp = snapshot.expires_at_utc.strip()
    if raw_exp.endswith("Z"):
        raw_exp = raw_exp[:-1] + "+00:00"
    exp_dt = datetime.fromisoformat(raw_exp)
    if exp_dt.tzinfo is None:
        exp_dt = exp_dt.replace(tzinfo=UTC)
    if datetime.now(UTC) > exp_dt:
        raise ReflexiveSessionExpiredError(
            detail_override=(
                f"ERR_REFLEXIVE_SESSION_EXPIRED: Execution '{snapshot.execution_id}' "
                f"expired at {snapshot.expires_at_utc}."
            )
        )


def build_trace_event_from_observation(
    *,
    execution_id: str,
    sequence_index: int,
    turn_index: int,
    obs: SurgicalObservation,
) -> AgentTraceEvent:
    """Convert a governed `SurgicalObservation` into a `CHECK_EXECUTED` or `FILE_ANALYZED` event."""
    if obs.kind == SurgicalPrimitiveName.INSPECT_RESOURCE_LINES:
        return AgentTraceEvent(
            execution_id=execution_id,
            sequence_index=sequence_index,
            turn_index=turn_index,
            kind=TraceEventKind.FILE_ANALYZED,
            resource_uri=obs.resource_uri,
            display_filename=obs.display_filename,
            file_badge_code=obs.file_badge_code,
            formatted_badge=obs.formatted_badge,
            start_line=obs.start_line,
            end_line=obs.end_line,
            redacted=obs.redacted,
            metadata={
                "total_lines": obs.total_lines,
                "redacted_reason": obs.redacted_reason,
                "permission_request_hint": obs.permission_request_hint,
            },
        )
    return AgentTraceEvent(
        execution_id=execution_id,
        sequence_index=sequence_index,
        turn_index=turn_index,
        kind=TraceEventKind.CHECK_EXECUTED,
        resource_uri=obs.resource_uri,
        display_filename=obs.display_filename,
        file_badge_code=obs.file_badge_code,
        formatted_badge=obs.formatted_badge,
        check_label=obs.check_label or obs.summary or obs.kind.value,
        redacted=obs.redacted,
        metadata={
            "primitive": obs.kind.value,
            "exists": obs.exists,
            "outline_count": len(obs.outline),
            "snippets_count": len(obs.snippets),
        },
    )


def build_scratchpad_entry_from_observation(
    *,
    turn_index: int,
    obs: SurgicalObservation,
) -> ReflexiveScratchpadEntry:
    """Summarize a `SurgicalObservation` for the compact multi-turn `scratchpad`."""
    anchor = ""
    if obs.start_line is not None and obs.end_line is not None:
        anchor = f"#L{obs.start_line}-{obs.end_line}"
    if obs.redacted:
        excerpt = "[Extrait protégé — permission READ_SOURCE requise]"
    elif obs.lines:
        preview_lines = [f"L{ln.line_number}: {ln.content}" for ln in obs.lines[:12]]
        excerpt = "\n".join(preview_lines)
    elif obs.snippets:
        excerpt = "\n".join(
            f"{sn.display_filename} {sn.line_anchor}: {sn.excerpt}" for sn in obs.snippets[:5]
        )
    elif obs.outline:
        excerpt = "\n".join(f"L{nd.line_number} [{nd.kind}] {nd.title}" for nd in obs.outline[:10])
    else:
        excerpt = obs.summary
    return ReflexiveScratchpadEntry(
        turn_index=turn_index,
        action_kind=obs.kind.value,
        resource_uri=obs.resource_uri,
        line_anchor=anchor,
        formatted_badge=obs.formatted_badge,
        summary=obs.summary or obs.formatted_badge,
        excerpt=excerpt,
        redacted=obs.redacted,
        metadata={"sha256": obs.sha256} if obs.sha256 else {},
    )


def serialize_scratchpad_for_llm(
    entries: list[ReflexiveScratchpadEntry],
) -> list[dict[str, Any]]:
    """Serialize `scratchpad` entries into compact dictionaries for `ReflexiveTurnInput`."""
    return [entry.model_dump(mode="json") for entry in entries]


def build_turn_input(snapshot: ReflexiveSessionSnapshot, turn_index: int) -> ReflexiveTurnInput:
    """Build `ReflexiveTurnInput` for the current turn from `snapshot`."""
    return ReflexiveTurnInput(
        execution_id=snapshot.execution_id,
        actor_slug=snapshot.actor_slug,
        objective=snapshot.objective,
        turn_index=turn_index,
        max_turns=snapshot.max_turns,
        force_final=snapshot.force_final,
        allow_sub_agent_delegation=snapshot.allow_sub_agent_delegation,
        available_delegate_agents=list(snapshot.available_delegate_agents),
        scratchpad=serialize_scratchpad_for_llm(snapshot.scratchpad),
        initial_resources=list(snapshot.initial_resources),
        requested_write_preview=snapshot.requested_write_preview,
        locale=snapshot.locale,
    )
