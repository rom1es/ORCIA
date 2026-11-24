"""Data Models & Impact Preview Calculation for Upstream Challenge & Replay (`Story 3.5`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from orcia_core.ontology.models import HumanProfileArchetype
from orcia_core.ontology.resolver import ProfileSemanticTranslator
from orcia_core.orchestration._orchestration_runtime_locales import (
    CHALLENGE_REPLAY_LOCALES,
    get_runtime_copy,
)
from orcia_core.orchestration.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.orchestration.jit_hydrator import JitStepHydrator
from orcia_core.permissions.models import UserIdentity

if TYPE_CHECKING:
    from orcia_core.orchestration.engine import DurableOrchestrationEngine

ChallengeStatus = Literal["OPEN", "RESOLVED_REVISED", "REPLAYED"]


@dataclass(frozen=True, slots=True)
class UpstreamChallengeImpactPreview:
    """What-If impact simulation report for an inter-step upstream challenge (`UX-DR7`, `AD-7`)."""

    run_id: str
    challenger_step_key: str
    target_upstream_step_key: str
    challenged_section_key: str
    challenge_reason: str
    target_profile_archetype: HumanProfileArchetype
    translated_summary: str
    invalidated_downstream_step_keys: tuple[str, ...]
    invalidated_artifact_sections: tuple[str, ...]
    invalidated_ontology_axiom_keys: tuple[str, ...]
    preserved_upstream_step_keys: tuple[str, ...]
    upstream_tokens_saved: int = 0


@dataclass(frozen=True, slots=True)
class UpstreamChallengeEntity:
    """Persisted upstream challenge record in `upstream_challenges` (`FR-7`, `AD-7`)."""

    id: str
    challenge_key: str
    workspace_id: str
    run_id: str
    challenger_step_key: str
    target_upstream_step_key: str
    challenged_section_key: str
    challenge_reason: str
    target_profile_archetype: HumanProfileArchetype
    translated_summary: str
    invalidated_downstream_step_keys: tuple[str, ...]
    invalidated_artifact_sections: tuple[str, ...]
    invalidated_ontology_axiom_keys: tuple[str, ...]
    preserved_upstream_step_keys: tuple[str, ...]
    status: ChallengeStatus
    created_by_user_id: str
    outbox_event_id: str
    revised_artifact_version: str | None = None


@dataclass(frozen=True, slots=True)
class StepReplayResult:
    """Result of a targeted Replay from Step $N$ or sub-workflow Step $k$ (`FR-16`, `FR-30`)."""

    run_id: str
    replayed_from_step_key: str
    sub_workflow_step_key: str | None
    reused_upstream_snapshot_ids: tuple[str, ...]
    superseded_snapshot_ids: tuple[str, ...]
    new_active_snapshot_ids: tuple[str, ...]
    upstream_steps_reexecuted_count: int
    upstream_tokens_consumed: int
    run_lock_sha256: str


def compute_upstream_challenge_preview(
    engine: DurableOrchestrationEngine,
    *,
    run_id: str,
    challenger_step_key: str,
    target_upstream_step_key: str,
    challenged_section_key: str,
    challenge_reason: str,
    target_profile_archetype: HumanProfileArchetype,
    instance: str | None,
) -> UpstreamChallengeImpactPreview:
    """Compute DAG + Ontology `What-If Impact Preview` for challenging an upstream step."""
    if len(challenge_reason.strip()) < 10:
        raise ValidationDomainError(
            detail_code="ERR_CHALLENGE_REASON_TOO_SHORT",
            instance=instance,
        )
    run = engine._get_run(run_id, instance=instance)
    wf = engine._get_workflow(run.workflow_uri, instance=instance)
    engine.initialize_run_steps(run, wf)

    step_index = {s.step_key: idx for idx, s in enumerate(wf.steps)}
    if target_upstream_step_key not in step_index:
        raise ResourceNotFoundError(
            detail_code="ERR_CHALLENGE_UPSTREAM_NOT_FOUND",
            detail_params={"step_key": target_upstream_step_key},
            instance=instance,
        )
    if challenger_step_key not in step_index:
        raise ResourceNotFoundError(
            detail_code="ERR_CHALLENGE_CHALLENGER_NOT_FOUND",
            detail_params={"step_key": challenger_step_key},
            instance=instance,
        )
    target_idx = step_index[target_upstream_step_key]
    challenger_idx = step_index[challenger_step_key]
    if target_idx > challenger_idx:
        raise ValidationDomainError(
            detail_code="ERR_CHALLENGE_NOT_UPSTREAM",
            detail_params={
                "target": target_upstream_step_key,
                "target_idx": target_idx,
                "challenger": challenger_step_key,
                "challenger_idx": challenger_idx,
            },
            instance=instance,
        )

    invalidated_steps: list[str] = []
    preserved_steps: list[str] = []
    for idx, s in enumerate(wf.steps):
        refs_upstream = any(
            inv in s.depends_on or any(inv in expr for expr in s.input_mapping.values())
            for inv in invalidated_steps
        )
        if idx < target_idx:
            preserved_steps.append(s.step_key)
        elif idx == target_idx or refs_upstream or idx >= target_idx:
            invalidated_steps.append(s.step_key)

    invalidated_sections: list[str] = [f"{target_upstream_step_key}:{challenged_section_key}"]
    for s_key in invalidated_steps[1:]:
        invalidated_sections.append(f"{s_key}:dependent_on_{challenged_section_key}")

    ontology_svc = engine.setup_service.ontology_service
    invalidated_axioms = tuple(
        ax.axiom_key
        for ax in ontology_svc.axioms
        if ax.immutable
        or challenged_section_key.lower() in ax.rule_expression.lower()
        or ax.concept_key
    )[:3]
    concepts = ontology_svc.concepts
    primary_concept = concepts[0] if concepts else None
    concept_translation = (
        ProfileSemanticTranslator.translate_concept(primary_concept, target_profile_archetype)
        if primary_concept is not None
        else challenged_section_key
    )
    translated_summary = get_runtime_copy(CHALLENGE_REPLAY_LOCALES)["preview_summary"].format(
        arch=target_profile_archetype,
        challenger=challenger_step_key,
        target=target_upstream_step_key,
        section=challenged_section_key,
        translation=concept_translation,
        reason=challenge_reason.strip(),
        inv_count=len(invalidated_steps),
        pres_count=len(preserved_steps),
    )
    return UpstreamChallengeImpactPreview(
        run_id=run.id,
        challenger_step_key=challenger_step_key,
        target_upstream_step_key=target_upstream_step_key,
        challenged_section_key=challenged_section_key,
        challenge_reason=challenge_reason.strip(),
        target_profile_archetype=target_profile_archetype,
        translated_summary=translated_summary,
        invalidated_downstream_step_keys=tuple(invalidated_steps),
        invalidated_artifact_sections=tuple(invalidated_sections),
        invalidated_ontology_axiom_keys=invalidated_axioms,
        preserved_upstream_step_keys=tuple(preserved_steps),
        upstream_tokens_saved=len(preserved_steps) * 1250,
    )


def prepare_replay_scope(
    engine: DurableOrchestrationEngine,
    user: UserIdentity,
    *,
    run_id: str,
    step_key: str,
    instance: str | None,
) -> tuple[Any, Any, int, tuple[str, ...], list[str]]:
    """Compute reused and superseded snapshot sets prior to replaying from `step_key`."""
    run = engine._get_run(run_id, instance=instance)
    engine.setup_service._enforce_mutation_guard(user, run.workspace_id, instance=instance)
    wf = engine._get_workflow(run.workflow_uri, instance=instance)
    engine.initialize_run_steps(run, wf)
    step_index = {s.step_key: idx for idx, s in enumerate(wf.steps)}
    if step_key not in step_index:
        raise ResourceNotFoundError(
            detail_code="ERR_REPLAY_STEP_NOT_FOUND",
            detail_params={"step_key": step_key},
            instance=instance,
        )
    target_idx = step_index[step_key]
    active_before = engine.blackboard.get_active_snapshots(run.id)
    reused = tuple(sn.id for sn in active_before if step_index.get(sn.step_key, 0) < target_idx)
    superseded = [sn.id for sn in active_before if step_index.get(sn.step_key, 0) >= target_idx]
    engine.blackboard.supersede_snapshots(tuple(superseded))
    return run, wf, target_idx, reused, superseded


def commit_sub_workflow_replay_parent(
    engine: DurableOrchestrationEngine,
    *,
    run: Any,
    step_key: str,
    target_spec: Any,
    sub_workflow_step_key: str,
    parent_step_exec: Any,
    reused_upstream_ids: tuple[str, ...],
    superseded_parent_ids: list[str],
) -> str:
    """Propagate replayed sub-workflow outputs back into the parent step snapshot."""
    mapped_outputs: dict[str, Any] = {}
    assert parent_step_exec.child_run_id is not None
    for out_alias, out_expr in sorted(target_spec.output_mapping.items()):
        child_step, field = JitStepHydrator._parse_input_ref(
            out_expr, parent_step_exec.child_run_id
        )
        child_snap = engine.blackboard.get_active_step_snapshot(
            parent_step_exec.child_run_id, child_step
        )
        if child_snap is not None:
            mapped_outputs[out_alias] = child_snap.artifact_payload.get(
                field, child_snap.artifact_payload
            )
    engine.blackboard.save_step_draft(
        run.id,
        step_key,
        status="EXECUTING_AGENT",
        draft_artifact={
            **parent_step_exec.draft_artifact,
            **mapped_outputs,
            "replayed_sub_workflow_step": sub_workflow_step_key,
        },
        added_cost_usd=0.0,
    )
    parent_snap_id = reused_upstream_ids[-1] if reused_upstream_ids else None
    return engine.blackboard.commit_step_snapshot(
        run.id,
        step_key,
        parent_snapshot_id=parent_snap_id,
        superseded_snapshot_ids=tuple(superseded_parent_ids),
    ).id
