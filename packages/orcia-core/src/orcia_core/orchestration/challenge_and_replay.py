"""Inter-Step Upstream Challenge (`What-If` Impact Preview) & Targeted Step Replay (`Story 3.5`)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from orcia_core.blackboard.models import StepMemlogEntry
from orcia_core.ontology.models import HumanProfileArchetype
from orcia_core.orchestration._challenge_replay_executors import (
    execute_replay_async,
    execute_replay_sync,
)
from orcia_core.orchestration._challenge_replay_models import (
    ChallengeStatus,
    StepReplayResult,
    UpstreamChallengeEntity,
    UpstreamChallengeImpactPreview,
    compute_upstream_challenge_preview,
)
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.events import HumanArbitrationRequested
from orcia_kernel.ids import new_uuid7_str

if TYPE_CHECKING:
    from orcia_core.orchestration.engine import DurableOrchestrationEngine


class UpstreamChallengeAndReplayService:
    """Domain service for Upstream Challenges (`What-If`) and Targeted Step Replay (`Story 3.5`)."""

    def __init__(self, *, engine: DurableOrchestrationEngine) -> None:
        self.engine = engine
        self._challenges_by_id: dict[str, UpstreamChallengeEntity] = {}
        self._challenges_by_run: dict[str, list[str]] = {}

    def list_challenges(self, run_id: str) -> tuple[UpstreamChallengeEntity, ...]:
        """Return all upstream challenges recorded for `run_id`."""
        return tuple(self._challenges_by_id[cid] for cid in self._challenges_by_run.get(run_id, []))

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
        return compute_upstream_challenge_preview(
            self.engine,
            run_id=run_id,
            challenger_step_key=challenger_step_key,
            target_upstream_step_key=target_upstream_step_key,
            challenged_section_key=challenged_section_key,
            challenge_reason=challenge_reason,
            target_profile_archetype=target_profile_archetype,
            instance=instance,
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
            status, revised_version = "RESOLVED_REVISED", "v1.1"

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

    def _finish_replay(
        self,
        *,
        run: Any,
        step_key: str,
        sub_workflow_step_key: str | None,
        reused: tuple[str, ...],
        superseded: list[str],
        new_active: list[str],
    ) -> StepReplayResult:
        for cid in self._challenges_by_run.get(run.id, []):
            chal = self._challenges_by_id[cid]
            if chal.target_upstream_step_key == step_key:
                self._challenges_by_id[cid] = replace(chal, status="REPLAYED")
        return StepReplayResult(
            run_id=run.id,
            replayed_from_step_key=step_key,
            sub_workflow_step_key=sub_workflow_step_key,
            reused_upstream_snapshot_ids=reused,
            superseded_snapshot_ids=tuple(dict.fromkeys(superseded)),
            new_active_snapshot_ids=tuple(new_active),
            upstream_steps_reexecuted_count=0,
            upstream_tokens_consumed=0,
            run_lock_sha256=run.run_lock.manifest_sha256,
        )

    async def replay_from_step_async(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        step_key: str,
        sub_workflow_step_key: str | None = None,
        revised_section_payload: dict[str, Any] | None = None,
        instance: str | None = None,
    ) -> StepReplayResult:
        """Async replay from Step $N$ reusing $1..N-1$ snapshots without blocking event loop."""
        return await execute_replay_async(
            self,
            user,
            run_id=run_id,
            step_key=step_key,
            sub_workflow_step_key=sub_workflow_step_key,
            revised_section_payload=revised_section_payload,
            instance=instance,
        )

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
        """Sync replay from Step $N$ reusing $1..N-1$ snapshots."""
        return execute_replay_sync(
            self,
            user,
            run_id=run_id,
            step_key=step_key,
            sub_workflow_step_key=sub_workflow_step_key,
            revised_section_payload=revised_section_payload,
            instance=instance,
        )


__all__ = [
    "ChallengeStatus",
    "StepReplayResult",
    "UpstreamChallengeAndReplayService",
    "UpstreamChallengeEntity",
    "UpstreamChallengeImpactPreview",
]
