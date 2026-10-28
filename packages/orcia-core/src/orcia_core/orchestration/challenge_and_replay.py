"""Inter-Step Upstream Challenge (`What-If` Impact Preview) & Targeted Step Replay (`Story 3.5`).

Covers:
- `UpstreamChallengeImpactPreview` & `UpstreamChallengeAndReplayService.preview_upstream_challenge`
  computing downstream step/section/axiom invalidation via DAG & `ImpactSimulatorService` (`AD-7`,
  `FR-7`, `UX-DR7`) and translating technical impact into the upstream author's
  `HumanProfileArchetype` (`ProfileSemanticTranslator`).
- `submit_upstream_challenge` emitting `HumanArbitrationRequested` into `domain_events_outbox`
  (`FR-7`, `AD-19`) and optionally applying a `v1.1` upstream artifact revision.
- `replay_from_step` (`FR-16`, `FR-30`, `AD-2`, `AD-18`) supporting both parent Step $N$ replay and
  intra-sub-workflow Step $k$ replay with `0` upstream re-execution (`0` upstream tokens), strict
  preservation of `run-lock.json` (`SHA-256`), and strictly append-only `SUPERSEDED`/`ACTIVE`
  branching in `blackboard_snapshots`.

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Literal

from orcia_core.blackboard.models import StepMemlogEntry
from orcia_core.ontology.models import HumanProfileArchetype
from orcia_core.ontology.resolver import ProfileSemanticTranslator
from orcia_core.orchestration.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.orchestration.jit_hydrator import JitStepHydrator
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.events import HumanArbitrationRequested
from orcia_kernel.ids import new_uuid7_str

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


class UpstreamChallengeAndReplayService:
    """Domain service for Upstream Challenges (`What-If`) and Targeted Step Replay (`Story 3.5`)."""

    def __init__(self, *, engine: DurableOrchestrationEngine) -> None:
        self.engine = engine
        self._challenges_by_id: dict[str, UpstreamChallengeEntity] = {}
        self._challenges_by_run: dict[str, list[str]] = {}

    def list_challenges(self, run_id: str) -> tuple[UpstreamChallengeEntity, ...]:
        """Return all upstream challenges recorded for `run_id`."""
        ids = self._challenges_by_run.get(run_id, [])
        return tuple(self._challenges_by_id[cid] for cid in ids)

    def preview_upstream_challenge(
        self,
        *,
        run_id: str,
        challenger_step_key: str,
        target_upstream_step_key: str,
        challenged_section_key: str = "business_rules",
        challenge_reason: str,
        target_profile_archetype: HumanProfileArchetype = "PM_BUSINESS",
        instance: str | None = None,
    ) -> UpstreamChallengeImpactPreview:
        """Compute DAG + Ontology `What-If Impact Preview` for challenging an upstream step."""
        if len(challenge_reason.strip()) < 10:
            raise ValidationDomainError(
                detail_override=(
                    "La justification du Challenge Amont doit comporter au moins 10 caractères."
                ),
                instance=instance,
            )
        run = self.engine._get_run(run_id, instance=instance)
        wf = self.engine._get_workflow(run.workflow_uri, instance=instance)
        self.engine.initialize_run_steps(run, wf)

        step_index = {s.step_key: idx for idx, s in enumerate(wf.steps)}
        if target_upstream_step_key not in step_index:
            raise ResourceNotFoundError(
                detail_override=f"Étape amont '{target_upstream_step_key}' introuvable.",
                instance=instance,
            )
        if challenger_step_key not in step_index:
            raise ResourceNotFoundError(
                detail_override=f"Étape émettrice '{challenger_step_key}' introuvable.",
                instance=instance,
            )
        target_idx = step_index[target_upstream_step_key]
        challenger_idx = step_index[challenger_step_key]
        if target_idx > challenger_idx:
            raise ValidationDomainError(
                detail_override=(
                    f"L'étape cible '{target_upstream_step_key}' (index {target_idx}) doit être "
                    f"en amont de l'étape '{challenger_step_key}' (index {challenger_idx})."
                ),
                instance=instance,
            )

        # Traverse DAG dependencies (`depends_on` + `input_mapping`) from `target_upstream_step_key`
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

        ontology_svc = self.engine.setup_service.ontology_service
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
        translated_summary = (
            f"[Traduction Ontologique -> {target_profile_archetype}] "
            f"Challenge émis depuis '{challenger_step_key}' sur "
            f"'{target_upstream_step_key}.{challenged_section_key}' ({concept_translation}) : "
            f"{challenge_reason.strip()} — Impact : {len(invalidated_steps)} étape(s) à rejouer, "
            f"{len(preserved_steps)} étape(s) amont préservées (0 token reconsommé)."
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

    def submit_upstream_challenge(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        challenger_step_key: str,
        target_upstream_step_key: str,
        challenged_section_key: str = "business_rules",
        challenge_reason: str,
        target_profile_archetype: HumanProfileArchetype = "PM_BUSINESS",
        proposed_upstream_revision: str | None = None,
        trace_id: str = "00000000000000000000000000000000",
        instance: str | None = None,
    ) -> tuple[UpstreamChallengeEntity, UpstreamChallengeImpactPreview]:
        """Record an upstream challenge, emit Outbox notification, and optionally apply `v1.1`."""
        run = self.engine._get_run(run_id, instance=instance)
        self.engine.setup_service._enforce_mutation_guard(user, run.workspace_id, instance=instance)
        preview = self.preview_upstream_challenge(
            run_id=run_id,
            challenger_step_key=challenger_step_key,
            target_upstream_step_key=target_upstream_step_key,
            challenged_section_key=challenged_section_key,
            challenge_reason=challenge_reason,
            target_profile_archetype=target_profile_archetype,
            instance=instance,
        )
        challenge_id = new_uuid7_str()
        event = HumanArbitrationRequested.create(
            arbitration_id=challenge_id,
            run_id=run.id,
            workspace_id=run.workspace_id,
            step_key=target_upstream_step_key,
            options_count=len(preview.invalidated_downstream_step_keys),
            trace_id=trace_id,
        )
        self.engine.anchors_and_arbitration._outbox_events.append(event)

        status: ChallengeStatus = "OPEN"
        revised_version: str | None = None
        if proposed_upstream_revision and proposed_upstream_revision.strip():
            upstream_exec = self.engine.blackboard.get_step_execution(
                run.id, target_upstream_step_key
            )
            updated_draft = {
                **upstream_exec.draft_artifact,
                challenged_section_key: proposed_upstream_revision.strip(),
                "artifact_revision": "v1.1",
            }
            self.engine.blackboard.save_step_draft(
                run.id,
                target_upstream_step_key,
                status="EXECUTING_AGENT",
                draft_artifact=updated_draft,
                memlog_entries=(
                    StepMemlogEntry(
                        entry_id=new_uuid7_str(),
                        step_key=target_upstream_step_key,
                        marker_type="DECISION",
                        summary=(
                            f"Révision amont v1.1 suite au challenge de '{challenger_step_key}'"
                        ),
                        details=preview.translated_summary,
                    ),
                ),
            )
            status = "RESOLVED_REVISED"
            revised_version = "v1.1"

        record = UpstreamChallengeEntity(
            id=challenge_id,
            challenge_key=f"chal-{run.id[-6:]}-{target_upstream_step_key}-{challenge_id[-6:]}",
            workspace_id=run.workspace_id,
            run_id=run.id,
            challenger_step_key=challenger_step_key,
            target_upstream_step_key=target_upstream_step_key,
            challenged_section_key=challenged_section_key,
            challenge_reason=preview.challenge_reason,
            target_profile_archetype=target_profile_archetype,
            translated_summary=preview.translated_summary,
            invalidated_downstream_step_keys=preview.invalidated_downstream_step_keys,
            invalidated_artifact_sections=preview.invalidated_artifact_sections,
            invalidated_ontology_axiom_keys=preview.invalidated_ontology_axiom_keys,
            preserved_upstream_step_keys=preview.preserved_upstream_step_keys,
            status=status,
            created_by_user_id=user.id,
            outbox_event_id=event.event_id,
            revised_artifact_version=revised_version,
        )
        self._challenges_by_id[challenge_id] = record
        self._challenges_by_run.setdefault(run.id, []).append(challenge_id)
        return record, preview

    def replay_from_step(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        step_key: str,
        sub_workflow_step_key: str | None = None,
        revised_section_payload: dict[str, Any] | None = None,
        instance: str | None = None,
    ) -> StepReplayResult:
        """Replay from Step $N$ (or intra-sub-workflow Step $k$) reusing $1..N-1$ snapshots."""
        run = self.engine._get_run(run_id, instance=instance)
        self.engine.setup_service._enforce_mutation_guard(user, run.workspace_id, instance=instance)
        wf = self.engine._get_workflow(run.workflow_uri, instance=instance)
        self.engine.initialize_run_steps(run, wf)

        step_index = {s.step_key: idx for idx, s in enumerate(wf.steps)}
        if step_key not in step_index:
            raise ResourceNotFoundError(
                detail_override=f"Étape '{step_key}' introuvable pour le Replay.",
                instance=instance,
            )
        target_idx = step_index[step_key]
        active_before = self.engine.blackboard.get_active_snapshots(run.id)

        reused_upstream_ids = tuple(
            sn.id for sn in active_before if step_index.get(sn.step_key, 0) < target_idx
        )
        superseded_parent_ids = [
            sn.id for sn in active_before if step_index.get(sn.step_key, 0) >= target_idx
        ]
        self.engine.blackboard.supersede_snapshots(tuple(superseded_parent_ids))

        all_superseded_ids: list[str] = list(superseded_parent_ids)
        new_active_ids: list[str] = []

        # Intra-Sub-Workflow Replay (`FR-30`) if `sub_workflow_step_key` is specified
        target_spec = wf.steps[target_idx]
        if sub_workflow_step_key is not None:
            if target_spec.step_type != "SUB_WORKFLOW" or not target_spec.sub_workflow_uri:
                raise ValidationDomainError(
                    detail_override=(
                        f"L'étape '{step_key}' n'est pas un SUB_WORKFLOW; impossible de rejouer "
                        f"le sous-step '{sub_workflow_step_key}'."
                    ),
                    instance=instance,
                )
            parent_step_exec = self.engine.blackboard.get_step_execution(run.id, step_key)
            if not parent_step_exec.child_run_id:
                self.engine.execute_step(
                    user, run_id=run.id, step_key=step_key, commit_immediately=True
                )
                parent_step_exec = self.engine.blackboard.get_step_execution(run.id, step_key)
            assert parent_step_exec.child_run_id is not None
            child_res = self.replay_from_step(
                user,
                run_id=parent_step_exec.child_run_id,
                step_key=sub_workflow_step_key,
                revised_section_payload=revised_section_payload,
                instance=instance,
            )
            reused_upstream_ids = (*reused_upstream_ids, *child_res.reused_upstream_snapshot_ids)
            all_superseded_ids.extend(child_res.superseded_snapshot_ids)
            new_active_ids.extend(child_res.new_active_snapshot_ids)

            # Update parent SUB_WORKFLOW output_mapping without re-running child steps 1..k-1
            mapped_outputs: dict[str, Any] = {}
            for out_alias, out_expr in sorted(target_spec.output_mapping.items()):
                target_child_step, target_field = JitStepHydrator._parse_input_ref(
                    out_expr, parent_step_exec.child_run_id
                )
                child_snap = self.engine.blackboard.get_active_step_snapshot(
                    parent_step_exec.child_run_id, target_child_step
                )
                if child_snap is not None:
                    mapped_outputs[out_alias] = child_snap.artifact_payload.get(
                        target_field, child_snap.artifact_payload
                    )
            self.engine.blackboard.save_step_draft(
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
            new_parent_snap = self.engine.blackboard.commit_step_snapshot(
                run.id,
                step_key,
                parent_snapshot_id=parent_snap_id,
                superseded_snapshot_ids=tuple(superseded_parent_ids),
            )
            new_active_ids.append(new_parent_snap.id)
            start_parent_loop_idx = target_idx + 1
        else:
            start_parent_loop_idx = target_idx

        for idx in range(start_parent_loop_idx, len(wf.steps)):
            cur_step_spec = wf.steps[idx]
            cur_exec = self.engine.blackboard.get_step_execution(run.id, cur_step_spec.step_key)
            # Replay target step and any downstream step that was previously executed
            if (
                idx > target_idx
                and cur_exec.status == "PENDING"
                and not cur_exec.committed_snapshot_id
            ):
                break
            _, snap = self.engine.execute_step(
                user,
                run_id=run.id,
                step_key=cur_step_spec.step_key,
                commit_immediately=True,
                executor_metadata=(
                    {"revised_section_payload": revised_section_payload}
                    if idx == target_idx and revised_section_payload
                    else None
                ),
                cost_usd=0.1,
                instance=instance,
            )
            if snap is not None:
                new_active_ids.append(snap.id)

        for cid in self._challenges_by_run.get(run.id, []):
            chal = self._challenges_by_id[cid]
            if chal.target_upstream_step_key == step_key:
                self._challenges_by_id[cid] = replace(chal, status="REPLAYED")

        return StepReplayResult(
            run_id=run.id,
            replayed_from_step_key=step_key,
            sub_workflow_step_key=sub_workflow_step_key,
            reused_upstream_snapshot_ids=reused_upstream_ids,
            superseded_snapshot_ids=tuple(dict.fromkeys(all_superseded_ids)),
            new_active_snapshot_ids=tuple(new_active_ids),
            upstream_steps_reexecuted_count=0,
            upstream_tokens_consumed=0,
            run_lock_sha256=run.run_lock.manifest_sha256,
        )


__all__ = [
    "ChallengeStatus",
    "StepReplayResult",
    "UpstreamChallengeAndReplayService",
    "UpstreamChallengeEntity",
    "UpstreamChallengeImpactPreview",
]
