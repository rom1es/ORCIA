"""Mandatory Human-Led Anchors (`UX-DR3`) & Systematic Human Arbitration (`UX-DR6`, `Story 3.4`).

Implements `AD-3`, `AD-18`, `AD-19`, `FR-4`, `FR-5`, `FR-29` with zero framework imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from orcia_core.blackboard.models import (
    BlackboardSnapshotEntity,
    StepExecutionEntity,
    StepMemlogEntry,
)
from orcia_core.orchestration._human_anchors_arbitration_ops import (
    execute_request_human_arbitration,
    prepare_arbitration_resolution,
)
from orcia_core.orchestration._human_anchors_models import (
    MIN_HUMAN_ANCHOR_CHARS,
    ArbitrationOptionItem,
    AuthorIdentityType,
    HumanAnchorSignatureEntity,
    HumanArbitrationRequestEntity,
    HumanArbitrationStatus,
    validate_human_anchor_submission,
)
from orcia_core.orchestration.errors import HumanAnchorRequiredError
from orcia_core.orchestration.models import TieBreakPolicy, WorkflowRunEntity, WorkflowStepSpec
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.events import DomainEvent
from orcia_kernel.ids import new_uuid7_str

if TYPE_CHECKING:
    from orcia_core.orchestration.engine import DurableOrchestrationEngine


class HumanAnchorAndArbitrationService:
    """Domain service managing mandatory human anchors and systematic arbitration (`Story 3.4`)."""

    def __init__(self, *, engine: DurableOrchestrationEngine) -> None:
        self.engine = engine
        self._anchors_by_step_section: dict[tuple[str, str, str], HumanAnchorSignatureEntity] = {}
        self._arbitrations_by_id: dict[str, HumanArbitrationRequestEntity] = {}
        self._outbox_events: list[DomainEvent] = []

    @property
    def outbox_events(self) -> tuple[DomainEvent, ...]:
        """Return immutable domain events emitted to `domain_events_outbox` (`AD-19`)."""
        return tuple(self._outbox_events)

    def get_step_anchors(
        self, run_id: str, step_key: str
    ) -> tuple[HumanAnchorSignatureEntity, ...]:
        """Return all signed human anchors for `(run_id, step_key)`."""
        return tuple(
            sig
            for (r_id, s_key, _), sig in self._anchors_by_step_section.items()
            if r_id == run_id and s_key == step_key
        )

    def list_arbitrations(self, run_id: str) -> tuple[HumanArbitrationRequestEntity, ...]:
        """Return all `HumanArbitrationRequestEntity` records for `run_id`."""
        return tuple(a for a in self._arbitrations_by_id.values() if a.run_id == run_id)

    def sign_human_anchor(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        step_key: str,
        section_key: str = "primary-anchor",
        content_text: str,
        signature_text: str,
        author_type: AuthorIdentityType = "HUMAN",
        instance: str | None = None,
    ) -> HumanAnchorSignatureEntity:
        """Sign a `human_authored_required: true` section (`>= 30` chars, rejects agent callers)."""
        run = self.engine._get_run(run_id, instance=instance)
        self.engine.setup_service._enforce_mutation_guard(user, run.workspace_id, instance=instance)
        wf = self.engine._get_workflow(run.workflow_uri, instance=instance)
        self.engine.initialize_run_steps(run, wf)
        step_exec = self.engine.blackboard.get_step_execution(run.id, step_key)

        cleaned_content, content_sha, sig_hash, char_len = validate_human_anchor_submission(
            content_text,
            signature_text,
            author_type=author_type,
            instance=instance,
        )
        sig_id = new_uuid7_str()
        entity = HumanAnchorSignatureEntity(
            id=sig_id,
            signature_key=f"anchor-{run.id[-6:]}-{step_key}-{section_key}",
            workspace_id=run.workspace_id,
            run_id=run.id,
            step_execution_id=step_exec.id,
            step_key=step_key,
            section_key=section_key,
            content_text=cleaned_content,
            content_sha256=content_sha,
            char_length=char_len,
            authored_by_user_id=user.id,
            author_display_name=user.display_name,
            signature_hash=sig_hash,
        )
        self._anchors_by_step_section[(run.id, step_key, section_key)] = entity

        anchor_memlog = StepMemlogEntry(
            entry_id=new_uuid7_str(),
            step_key=step_key,
            marker_type="HUMAN_ANCHOR_SIGNED",
            summary=f"Ancre humaine signée sur '{section_key}' ({char_len} caractères)",
            details=f"SHA-256={content_sha[:16]} par {user.display_name} ({user.id})",
        )
        draft_payload = {
            **step_exec.draft_artifact,
            "human_anchors": {
                **step_exec.draft_artifact.get("human_anchors", {}),
                section_key: {
                    "content_text": cleaned_content,
                    "content_sha256": content_sha,
                    "char_length": char_len,
                    "authored_by_user_id": user.id,
                },
            },
        }
        next_status = (
            "PENDING" if step_exec.status == "WAITING_FOR_HUMAN_ANCHOR" else step_exec.status
        )
        self.engine.blackboard.save_step_draft(
            run.id,
            step_key,
            status=next_status,
            draft_artifact=draft_payload,
            memlog_entries=(anchor_memlog,),
        )
        return entity

    def enforce_step_anchor_if_required(
        self,
        run: WorkflowRunEntity,
        step_spec: WorkflowStepSpec,
        *,
        require_human_anchor: bool = False,
        author_type: AuthorIdentityType = "HUMAN",
        instance: str | None = None,
    ) -> None:
        """Verify human anchor before agent step execution when `human_authored_required: true`."""
        if not step_spec.human_authored_required:
            return
        if author_type != "HUMAN":
            raise HumanAnchorRequiredError(
                detail_override=(
                    f"L'étape '{step_spec.step_key}' requiert une ancre humaine obligatoire "
                    f"(human_authored_required: true) et rejette toute écriture par un agent."
                ),
                instance=instance,
            )
        step_exec = self.engine.blackboard.get_step_execution(run.id, step_spec.step_key)
        if not require_human_anchor and step_exec.status != "WAITING_FOR_HUMAN_ANCHOR":
            return
        if not self.get_step_anchors(run.id, step_spec.step_key):
            self.engine.blackboard.save_step_draft(
                run.id,
                step_spec.step_key,
                status="WAITING_FOR_HUMAN_ANCHOR",
                draft_artifact=step_exec.draft_artifact,
            )
            raise HumanAnchorRequiredError(
                detail_override=(
                    f"Impossible de lancer l'agent sur l'étape '{step_spec.step_key}' : "
                    f"aucune signature dans human_anchor_signatures (>= 30 caractères)."
                ),
                instance=instance,
            )

    def request_human_arbitration(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        step_key: str,
        question_title: str,
        context_summary: str,
        options_matrix: tuple[ArbitrationOptionItem, ...],
        tie_break_policy: TieBreakPolicy | None = None,
        trace_id: str = "00000000000000000000000000000000",
        instance: str | None = None,
    ) -> tuple[HumanArbitrationRequestEntity, StepExecutionEntity]:
        """Execute `request_human_arbitration(options_matrix)` according to `tie_break_policy`."""
        return execute_request_human_arbitration(
            self,
            user,
            run_id=run_id,
            step_key=step_key,
            question_title=question_title,
            context_summary=context_summary,
            options_matrix=options_matrix,
            tie_break_policy=tie_break_policy,
            trace_id=trace_id,
            instance=instance,
        )

    async def resolve_human_arbitration_async(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        step_key: str,
        arbitration_id: str,
        selected_option_key: str,
        human_justification: str | None = None,
        instance: str | None = None,
    ) -> tuple[HumanArbitrationRequestEntity, StepExecutionEntity, BlackboardSnapshotEntity | None]:
        """Resolve human arbitration and resume the step asynchronously without blocking loop."""
        resolved_req, decision_summary = prepare_arbitration_resolution(
            self,
            user,
            run_id=run_id,
            step_key=step_key,
            arbitration_id=arbitration_id,
            selected_option_key=selected_option_key,
            human_justification=human_justification,
            instance=instance,
        )
        resumed_step, snapshot = await self.engine.resume_human_task_async(
            user,
            run_id=run_id,
            step_key=step_key,
            decision=decision_summary,
            instance=instance,
        )
        return resolved_req, resumed_step, snapshot

    def resolve_human_arbitration(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        step_key: str,
        arbitration_id: str,
        selected_option_key: str,
        human_justification: str | None = None,
        instance: str | None = None,
    ) -> tuple[HumanArbitrationRequestEntity, StepExecutionEntity, BlackboardSnapshotEntity | None]:
        """Resolve a `PENDING` human arbitration, record decision in Blackboard, and resume step."""
        resolved_req, decision_summary = prepare_arbitration_resolution(
            self,
            user,
            run_id=run_id,
            step_key=step_key,
            arbitration_id=arbitration_id,
            selected_option_key=selected_option_key,
            human_justification=human_justification,
            instance=instance,
        )
        resumed_step, snapshot = self.engine.resume_human_task(
            user,
            run_id=run_id,
            step_key=step_key,
            decision=decision_summary,
            instance=instance,
        )
        return resolved_req, resumed_step, snapshot

    def _resolve_by_ontology_axiom(
        self,
        run: WorkflowRunEntity,
        options_matrix: tuple[ArbitrationOptionItem, ...],
    ) -> tuple[ArbitrationOptionItem, str] | None:
        axioms = self.engine.setup_service.ontology_service.axioms
        for opt in options_matrix:
            if not opt.ontology_concept_key:
                continue
            for ax in axioms:
                if ax.concept_key == opt.ontology_concept_key and ax.immutable:
                    return opt, ax.axiom_key
        return None


__all__ = [
    "ArbitrationOptionItem",
    "AuthorIdentityType",
    "HumanAnchorAndArbitrationService",
    "HumanAnchorSignatureEntity",
    "HumanArbitrationRequestEntity",
    "HumanArbitrationStatus",
    "MIN_HUMAN_ANCHOR_CHARS",
    "validate_human_anchor_submission",
]
