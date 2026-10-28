"""Mandatory Human-Led Anchors (`UX-DR3`) & Systematic Human Arbitration (`UX-DR6`, `Story 3.4`).

Implements `AD-3`, `AD-18`, `AD-19`, `FR-4`, `FR-5`, `FR-29` with zero framework imports.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Literal

from orcia_core.blackboard.models import (
    BlackboardSnapshotEntity,
    StepExecutionEntity,
    StepMemlogEntry,
)
from orcia_core.orchestration.errors import (
    HumanAnchorRequiredError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.orchestration.models import TieBreakPolicy, WorkflowRunEntity, WorkflowStepSpec
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.events import DomainEvent, HumanArbitrationRequested
from orcia_kernel.ids import new_uuid7_str

if TYPE_CHECKING:
    from orcia_core.orchestration.engine import DurableOrchestrationEngine

HumanArbitrationStatus = Literal[
    "PENDING",
    "RESOLVED_BY_HUMAN",
    "RESOLVED_BY_AXIOM",
    "DEFERRED_WITH_ASSUMPTION",
]
AuthorIdentityType = Literal["HUMAN", "AGENT"]

MIN_HUMAN_ANCHOR_CHARS = 30


@dataclass(frozen=True, slots=True)
class HumanAnchorSignatureEntity:
    """Cryptographic proof of human authorship for a `human_authored_required: true` section."""

    id: str
    signature_key: str
    workspace_id: str
    run_id: str
    step_execution_id: str
    step_key: str
    section_key: str
    content_text: str
    content_sha256: str
    char_length: int
    authored_by_user_id: str
    author_display_name: str
    signature_hash: str


@dataclass(frozen=True, slots=True)
class ArbitrationOptionItem:
    """Single option inside an `Arbitration Tie-Break Matrix` (`UX-DR6`, `FR-5`)."""

    option_key: str
    title: str
    pros: tuple[str, ...]
    cons: tuple[str, ...]
    si_impact: str
    finops_impact: str
    recommended: bool = False
    ontology_concept_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize option item for JSONB storage and OpenAPI transport."""
        return {
            "option_key": self.option_key,
            "title": self.title,
            "pros": list(self.pros),
            "cons": list(self.cons),
            "si_impact": self.si_impact,
            "finops_impact": self.finops_impact,
            "recommended": self.recommended,
            "ontology_concept_key": self.ontology_concept_key,
        }


@dataclass(frozen=True, slots=True)
class HumanArbitrationRequestEntity:
    """Durable record in `human_arbitration_requests` (`AD-3`, `AD-18`, `UX-DR6`)."""

    id: str
    arbitration_key: str
    workspace_id: str
    run_id: str
    step_execution_id: str
    step_key: str
    tie_break_policy: TieBreakPolicy
    status: HumanArbitrationStatus
    question_title: str
    context_summary: str
    options_matrix: tuple[ArbitrationOptionItem, ...]
    selected_option_key: str | None = None
    human_justification: str | None = None
    resolved_by_user_id: str | None = None
    resolved_by_axiom_key: str | None = None
    outbox_event_id: str | None = None


def validate_human_anchor_submission(
    content_text: str,
    signature_text: str,
    *,
    author_type: AuthorIdentityType = "HUMAN",
    instance: str | None = None,
) -> tuple[str, str, str, int]:
    """Validate human authorship (`author_type == 'HUMAN'`) and `>= 30` meaningful characters."""
    if author_type != "HUMAN":
        raise HumanAnchorRequiredError(
            detail_override=(
                "Toute écriture ou signature par une identité d'agent (author_type='AGENT') sur "
                "un champ human_authored_required: true est strictement interdite (AD-3, FR-4)."
            ),
            instance=instance,
        )
    cleaned_content = content_text.strip()
    cleaned_sig = signature_text.strip()
    char_len = len(cleaned_content)
    if (
        char_len < MIN_HUMAN_ANCHOR_CHARS
        or len(set(cleaned_content.lower())) < 5
        or len(cleaned_sig) < 3
        or any(ord(c) < 32 and c not in ("\n", "\r", "\t") for c in cleaned_content + cleaned_sig)
    ):
        raise HumanAnchorRequiredError(
            detail_override=(
                f"Une ancre humaine obligatoire exige au moins {MIN_HUMAN_ANCHOR_CHARS} "
                f"caractères significatifs rédigés et signés par un humain (reçu: {char_len})."
            ),
            instance=instance,
        )
    content_sha = hashlib.sha256(cleaned_content.encode("utf-8")).hexdigest()
    sig_hash = hashlib.sha256(f"{cleaned_sig}:{content_sha}".encode()).hexdigest()
    return cleaned_content, content_sha, sig_hash, char_len


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
        anchors = self.get_step_anchors(run.id, step_spec.step_key)
        if not anchors:
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
        run = self.engine._get_run(run_id, instance=instance)
        self.engine.setup_service._enforce_mutation_guard(user, run.workspace_id, instance=instance)
        wf = self.engine._get_workflow(run.workflow_uri, instance=instance)
        self.engine.initialize_run_steps(run, wf)
        step_exec = self.engine.blackboard.get_step_execution(run.id, step_key)

        if len(options_matrix) < 2:
            raise ValidationDomainError(
                detail_override="L'arbitrage humain exige au moins 2 options dans options_matrix.",
                instance=instance,
            )

        effective_policy: TieBreakPolicy = tie_break_policy or wf.tie_break_policy
        if (
            run.criticality == "HIGH_CRITICAL"
            and effective_policy == "DEFER_AND_CONTINUE_WITH_ASSUMPTION"
        ):
            effective_policy = "PAUSE_AND_ESCALATE"

        arb_id = new_uuid7_str()
        arb_key = f"arb-{run.id[-6:]}-{step_key}-{arb_id[-6:]}"

        if effective_policy == "ONTOLOGY_AXIOM_FIRST":
            matched = self._resolve_by_ontology_axiom(run, options_matrix)
            if matched is not None:
                opt, axiom_key = matched
                req = HumanArbitrationRequestEntity(
                    id=arb_id,
                    arbitration_key=arb_key,
                    workspace_id=run.workspace_id,
                    run_id=run.id,
                    step_execution_id=step_exec.id,
                    step_key=step_key,
                    tie_break_policy=effective_policy,
                    status="RESOLVED_BY_AXIOM",
                    question_title=question_title.strip(),
                    context_summary=context_summary.strip(),
                    options_matrix=options_matrix,
                    selected_option_key=opt.option_key,
                    resolved_by_axiom_key=axiom_key,
                )
                self._arbitrations_by_id[arb_id] = req
                updated_step = self.engine.blackboard.save_step_draft(
                    run.id,
                    step_key,
                    status="EXECUTING_AGENT",
                    draft_artifact={
                        **step_exec.draft_artifact,
                        "arbitration_resolution": {
                            "arbitration_id": arb_id,
                            "status": "RESOLVED_BY_AXIOM",
                            "selected_option_key": opt.option_key,
                            "resolved_by_axiom_key": axiom_key,
                        },
                    },
                    memlog_entries=(
                        StepMemlogEntry(
                            entry_id=new_uuid7_str(),
                            step_key=step_key,
                            marker_type="REASONING",
                            summary=(
                                f"Départage par axiome ontologique '{axiom_key}' "
                                f"-> {opt.option_key}"
                            ),
                            details=f"Option '{opt.title}' retenue formellement par l'Ontologie.",
                        ),
                    ),
                )
                return req, updated_step

        if effective_policy == "DEFER_AND_CONTINUE_WITH_ASSUMPTION":
            chosen = next((o for o in options_matrix if o.recommended), options_matrix[0])
            req = HumanArbitrationRequestEntity(
                id=arb_id,
                arbitration_key=arb_key,
                workspace_id=run.workspace_id,
                run_id=run.id,
                step_execution_id=step_exec.id,
                step_key=step_key,
                tie_break_policy=effective_policy,
                status="DEFERRED_WITH_ASSUMPTION",
                question_title=question_title.strip(),
                context_summary=context_summary.strip(),
                options_matrix=options_matrix,
                selected_option_key=chosen.option_key,
            )
            self._arbitrations_by_id[arb_id] = req
            assumption_entry = StepMemlogEntry(
                entry_id=new_uuid7_str(),
                step_key=step_key,
                marker_type="ASSUMPTION",
                summary=(
                    f"[ASSUMPTION] Option par défaut '{chosen.option_key}' ({chosen.title}) "
                    f"retenue sur '{question_title.strip()}'"
                ),
                details=(
                    f"Politique DEFER_AND_CONTINUE_WITH_ASSUMPTION appliquée. "
                    f"Impact SI: {chosen.si_impact} | FinOps: {chosen.finops_impact}"
                ),
            )
            updated_step = self.engine.blackboard.save_step_draft(
                run.id,
                step_key,
                status="EXECUTING_AGENT",
                draft_artifact={
                    **step_exec.draft_artifact,
                    "arbitration_resolution": {
                        "arbitration_id": arb_id,
                        "status": "DEFERRED_WITH_ASSUMPTION",
                        "selected_option_key": chosen.option_key,
                    },
                },
                memlog_entries=(assumption_entry,),
            )
            return req, updated_step

        event = HumanArbitrationRequested.create(
            arbitration_id=arb_id,
            run_id=run.id,
            workspace_id=run.workspace_id,
            step_key=step_key,
            options_count=len(options_matrix),
            trace_id=trace_id,
        )
        self._outbox_events.append(event)
        req = HumanArbitrationRequestEntity(
            id=arb_id,
            arbitration_key=arb_key,
            workspace_id=run.workspace_id,
            run_id=run.id,
            step_execution_id=step_exec.id,
            step_key=step_key,
            tie_break_policy=effective_policy,
            status="PENDING",
            question_title=question_title.strip(),
            context_summary=context_summary.strip(),
            options_matrix=options_matrix,
            outbox_event_id=event.event_id,
        )
        self._arbitrations_by_id[arb_id] = req
        updated_step = self.engine.blackboard.save_step_draft(
            run.id,
            step_key,
            status="WAITING_FOR_HUMAN_ARBITRATION",
            draft_artifact={
                **step_exec.draft_artifact,
                "pending_arbitration_id": arb_id,
                "options_matrix": [o.to_dict() for o in options_matrix],
            },
            memlog_entries=(
                StepMemlogEntry(
                    entry_id=new_uuid7_str(),
                    step_key=step_key,
                    marker_type="HUMAN_ARBITRATION_REQUESTED",
                    summary=f"Escalade vers Arbitrage Humain : {question_title.strip()}",
                    details=f"{len(options_matrix)} options comparées (outbox={event.event_id}).",
                ),
            ),
        )
        self.engine.setup_service.set_run_status(run.id, "WAITING_FOR_HUMAN_ARBITRATION")
        return req, updated_step

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
        run = self.engine._get_run(run_id, instance=instance)
        self.engine.setup_service._enforce_mutation_guard(user, run.workspace_id, instance=instance)
        req = self._arbitrations_by_id.get(arbitration_id)
        if req is None or req.run_id != run.id or req.step_key != step_key:
            raise ResourceNotFoundError(
                detail_override=f"Demande d'arbitrage '{arbitration_id}' introuvable.",
                instance=instance,
            )
        chosen = next(
            (o for o in req.options_matrix if o.option_key == selected_option_key),
            None,
        )
        if chosen is None:
            raise ValidationDomainError(
                detail_override=f"Option '{selected_option_key}' absente de options_matrix.",
                instance=instance,
            )

        just_clean = human_justification.strip() if human_justification else None
        resolved_req = replace(
            req,
            status="RESOLVED_BY_HUMAN",
            selected_option_key=chosen.option_key,
            human_justification=just_clean,
            resolved_by_user_id=user.id,
        )
        self._arbitrations_by_id[arbitration_id] = resolved_req

        step_exec = self.engine.blackboard.get_step_execution(run.id, step_key)
        self.engine.blackboard.save_step_draft(
            run.id,
            step_key,
            status="EXECUTING_AGENT",
            draft_artifact={
                **step_exec.draft_artifact,
                "arbitration_resolution": {
                    "arbitration_id": arbitration_id,
                    "status": "RESOLVED_BY_HUMAN",
                    "selected_option_key": chosen.option_key,
                    "selected_option_title": chosen.title,
                    "human_justification": just_clean,
                    "resolved_by_user_id": user.id,
                },
            },
            memlog_entries=(
                StepMemlogEntry(
                    entry_id=new_uuid7_str(),
                    step_key=step_key,
                    marker_type="HUMAN_ARBITRATION_RESOLVED",
                    summary=f"Arbitrage humain tranché : {chosen.option_key} ({chosen.title})",
                    details=just_clean or "Option validée sans note additionnelle.",
                ),
            ),
        )
        decision_summary = f"{chosen.option_key}: {just_clean}" if just_clean else chosen.option_key
        resumed_step, snapshot = self.engine.resume_human_task(
            user,
            run_id=run.id,
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
