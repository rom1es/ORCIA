"""Unit tests for Story 16.3 (`ProcessExecutionDispatcher`, Dual-Mode `WorkflowDefinitionV2`).

Validates:
1. `WorkflowDefinitionV2` defaults to `DETERMINISTIC_DBOS`; `fork_workflow_as_draft` preserves
   `orchestration_type`, `reflexive_objective`, and `allowed_delegate_agents`.
2. `ProcessExecutionDispatcher` in `NON_DETERMINISTIC` mode invokes reflexive runtime with
   `allow_sub_agent_delegation=True` and `available_delegate_agents`, runs `GatePipelineExecutor`
   (including 3x self-heal remediation + blocking gate failure), and stores the deliverable via
   `ClaimCheckStorageService`.
3. `ProcessExecutionDispatcher` in `DETERMINISTIC_DBOS` mode delegates via
   `BoundedWorkflowLauncherPort`.
4. Principle 7 Encapsulation: `agent_executor` sub-steps inside a bounded workflow run an internal
   reflexive loop (`allow_sub_agent_delegation=False`) and persist ONLY `ClaimCheckPointer` +
   `reflexive_execution_id` in `SubStepExecutionRecord` (zero internal scratchpad bloat).
5. Declarative packs (`packs/orcia-docs` vs `packs/sdlc`) load with expected `orchestration_type`,
   `reflexive_objective`, and `allowed_delegate_agents`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from orcia_connectors.bounded_workflow_v2 import BoundedWorkflowLauncherAdapter
from orcia_connectors.surgical import SurgicalContextExplorer
from orcia_core.agents import (
    NonDeterministicReflexiveRuntime,
    ProcessExecutionDispatcher,
    ReflexiveEventStreamBroker,
    SqlReflexiveSessionStore,
)
from orcia_core.agents.reflexive_schemas import (
    ProcessOrchestrationType,
    ReflexiveTurnDecision,
)
from orcia_core.packs.loader import DeclarativePackLoader
from orcia_core.ports import (
    BoundedWorkflowLauncherPort,
    ReflexiveLlmChunk,
    ReflexiveLlmPort,
    ReflexiveTurnInput,
    SurgicalPrimitiveName,
)
from orcia_core.storage.claim_check import ClaimCheckStorageService
from orcia_core.workflows.schemas_v2 import (
    DeterministicControlSpec,
    DeterministicSubStepSpec,
    EffortLevel,
    StepControlsPipeline,
    WorkflowContract,
    WorkflowDefinitionV2,
    WorkflowLifecycleStatus,
    fork_workflow_as_draft,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


class RecordingReflexiveLlmDouble(ReflexiveLlmPort):
    """Deterministic `ReflexiveLlmPort` recording every `ReflexiveTurnInput`."""

    def __init__(self, decisions_by_actor: dict[str, list[ReflexiveTurnDecision]]) -> None:
        self._queues = {k: list(v) for k, v in decisions_by_actor.items()}
        self.calls: list[ReflexiveTurnInput] = []

    async def decide_next_turn(self, turn_input: ReflexiveTurnInput) -> ReflexiveTurnDecision:
        self.calls.append(turn_input)
        queue = self._queues.get(turn_input.actor_slug, [])
        if queue:
            return queue.pop(0)
        return ReflexiveTurnDecision(
            thought_text="Consolidation directe du livrable.",
            action_kind="final_answer",
            final_markdown=(
                "# Synthese\n\n"
                "## Objectif\nResultat consolide avec soin.\n\n"
                "## Etapes cles\nVerification completee.\n"
            ),
            tokens_used=180,
        )

    async def stream_turn_deltas(
        self,
        turn_input: ReflexiveTurnInput,
        decision: ReflexiveTurnDecision,
    ) -> AsyncIterator[ReflexiveLlmChunk]:
        del turn_input
        if decision.thought_text:
            yield ReflexiveLlmChunk(thinking_delta=decision.thought_text)
        if decision.action_kind == "final_answer" and decision.final_markdown:
            yield ReflexiveLlmChunk(answer_delta=decision.final_markdown)


def _build_dispatcher(
    decisions_by_actor: dict[str, list[ReflexiveTurnDecision]],
    *,
    self_heal_override: Any | None = None,
) -> tuple[
    ProcessExecutionDispatcher,
    RecordingReflexiveLlmDouble,
    SqlReflexiveSessionStore,
    ClaimCheckStorageService,
]:
    llm = RecordingReflexiveLlmDouble(decisions_by_actor)
    session_store = SqlReflexiveSessionStore(session_maker=None)
    claim_check = ClaimCheckStorageService()
    runtime = NonDeterministicReflexiveRuntime(
        llm_port=llm,
        surgical_explorer=SurgicalContextExplorer(),
        session_store=session_store,
        event_stream=ReflexiveEventStreamBroker(redis_url=None),
        claim_check_storage=claim_check,
    )
    launcher: BoundedWorkflowLauncherPort = BoundedWorkflowLauncherAdapter()
    dispatcher = ProcessExecutionDispatcher(
        reflexive_runtime=runtime,
        bounded_launcher=launcher,
        claim_check_storage=claim_check,
        self_heal_callback=self_heal_override,
    )
    return dispatcher, llm, session_store, claim_check


def test_workflow_v2_defaults_and_fork_preserves_dual_mode_fields() -> None:
    """Verify `WorkflowDefinitionV2` defaults and `fork_workflow_as_draft` preservation."""
    default_wf = WorkflowDefinitionV2(
        id="wf-default",
        slug="wf-default",
        title="Processus par defaut",
        pack_id="pack-demo",
    )
    assert default_wf.orchestration_type == ProcessOrchestrationType.DETERMINISTIC_DBOS
    assert default_wf.reflexive_objective is None
    assert default_wf.allowed_delegate_agents == []

    goal_wf = WorkflowDefinitionV2(
        id="wf-goal",
        slug="wf-goal",
        title="Processus adaptatif publie",
        version="2.0.0",
        status=WorkflowLifecycleStatus.PUBLISHED,
        pack_id="pack-docs",
        orchestration_type=ProcessOrchestrationType.NON_DETERMINISTIC,
        reflexive_objective="Produire un guide utilisateur bilingue complet.",
        allowed_delegate_agents=["redacteur-documentation-orcia"],
    )
    forked = fork_workflow_as_draft(goal_wf)
    assert forked.status == WorkflowLifecycleStatus.DRAFT
    assert forked.version == "2.1.0-draft"
    assert forked.orchestration_type == ProcessOrchestrationType.NON_DETERMINISTIC
    assert forked.reflexive_objective == "Produire un guide utilisateur bilingue complet."
    assert forked.allowed_delegate_agents == ["redacteur-documentation-orcia"]


async def test_dispatcher_goal_driven_delegation_self_heal_and_claim_check() -> None:
    """Verify `NON_DETERMINISTIC` delegation, gate self-healing, and Claim-Check storage."""
    dispatcher, llm, session_store, claim_check = _build_dispatcher(
        {
            "lead-doc-agent": [
                ReflexiveTurnDecision(
                    thought_text="Deleguer la redaction initiale au specialiste documentaire.",
                    action_kind="delegate_sub_agent",
                    delegate_agent_slug="redacteur-documentation-orcia",
                    delegate_sub_objective="Preparer le squelette FR/EN.",
                    tokens_used=200,
                ),
                ReflexiveTurnDecision(
                    thought_text="Produire un premier brouillon avec un marqueur TODO a corriger.",
                    action_kind="final_answer",
                    final_markdown="# Guide Aide\n\nTODO: completer les sections obligatoires.",
                    tokens_used=220,
                ),
            ],
            "redacteur-documentation-orcia": [
                ReflexiveTurnDecision(
                    thought_text="Redaction du squelette bilingue sans sous-delegation.",
                    action_kind="final_answer",
                    final_markdown="Squelette FR/EN pret pour consolidation.",
                    tokens_used=150,
                ),
            ],
        }
    )

    workflow = WorkflowDefinitionV2(
        id="wf-goal-doc",
        slug="wf-goal-doc",
        title="Generation Aide Contextuelle",
        version="2.0.0",
        status=WorkflowLifecycleStatus.PUBLISHED,
        pack_id="orcia-pack-docs",
        orchestration_type=ProcessOrchestrationType.NON_DETERMINISTIC,
        reflexive_objective="Rediger une fiche d'aide bilingue FR/EN structuree.",
        allowed_delegate_agents=["redacteur-documentation-orcia"],
        effort=EffortLevel.HIGH,
        global_system_prompt_or_ref="pack://orcia-docs/agents/lead-doc-agent.md",
        contract=WorkflowContract(
            required_markdown_sections=["# ", "## Objectif", "## Etapes cles"]
        ),
        controls=StepControlsPipeline(
            deterministic=[
                DeterministicControlSpec(
                    id="det-doc-sections",
                    name="Contrat structure aide",
                    short_label="Structure Markdown",
                    runner_plugin_id="markdown_contract_runner",
                    verifies_description="Verifie les titres et l'absence de TODO.",
                    on_ko_behavior="Auto-correction 3x",
                    max_self_heal_retries=3,
                    config={
                        "required_headings": ["# ", "## Objectif", "## Etapes cles"],
                        "min_chars": 40,
                        "forbidden_substrings": ["TODO"],
                    },
                )
            ]
        ),
    )

    result = await dispatcher.dispatch(
        workflow,
        run_id="run-goal-01",
        inputs={"help_key": "studio.five-blocks"},
        auto_approve_checkpoints=False,
    )

    assert result.orchestration_type == ProcessOrchestrationType.NON_DETERMINISTIC
    assert result.status == "WAITING_FINAL_ANCHOR"
    assert result.reflexive_execution_id is not None
    stored_session = await session_store.load_session_record(result.reflexive_execution_id)
    assert stored_session is not None
    assert result.gate_report is not None
    assert result.gate_report.deterministic_passed is True
    assert result.gate_report.deterministic_records[0].self_healed is True
    assert result.gate_report.deterministic_records[0].attempts == 2
    assert result.final_artifact_pointer is not None
    stored_text = claim_check.resolve_artifact_text(result.final_artifact_pointer)
    assert "## Objectif" in stored_text
    assert "## Etapes cles" in stored_text
    assert "TODO" not in stored_text

    lead_call = next(c for c in llm.calls if c.actor_slug == "lead-doc-agent")
    child_call = next(c for c in llm.calls if c.actor_slug == "redacteur-documentation-orcia")
    assert lead_call.allow_sub_agent_delegation is True
    assert "redacteur-documentation-orcia" in lead_call.available_delegate_agents
    assert child_call.allow_sub_agent_delegation is False


async def test_dispatcher_goal_driven_failed_gates_status_when_self_heal_cannot_fix() -> None:
    """Verify `FAILED_GATES` status when a blocking gate remains KO after max self-heal retries."""
    dispatcher, _, _, _ = _build_dispatcher(
        {},
        self_heal_override=lambda text, _diag, _idx: text,
    )
    workflow = WorkflowDefinitionV2(
        id="wf-goal-ko",
        slug="wf-goal-ko",
        title="Processus avec gate bloquante non remediable",
        pack_id="orcia-pack-docs",
        orchestration_type=ProcessOrchestrationType.NON_DETERMINISTIC,
        reflexive_objective="Test echec gate bloquante",
        controls=StepControlsPipeline(
            deterministic=[
                DeterministicControlSpec(
                    id="det-strict",
                    name="Section introuvable",
                    short_label="Section requise",
                    runner_plugin_id="markdown_contract_runner",
                    verifies_description="Exige ## Section Inexistante",
                    on_ko_behavior="blocking",
                    max_self_heal_retries=1,
                    config={"required_headings": ["## Section Inexistante"]},
                )
            ]
        ),
    )
    result = await dispatcher.dispatch(workflow, run_id="run-goal-ko-01")
    assert result.status == "FAILED_GATES"
    assert result.gate_report is not None
    assert result.gate_report.deterministic_passed is False


async def test_dispatcher_milestone_driven_principle_7_encapsulation() -> None:
    """Verify Principle 7: `DETERMINISTIC_DBOS` sub-steps omit internal scratchpad bloat."""
    dispatcher, llm, session_store, claim_check = _build_dispatcher(
        {
            "orchestrateur-etape": [
                ReflexiveTurnDecision(
                    thought_text="Exploration interne privee (brouillon temporaire volumineux).",
                    action_kind="surgical_primitive",
                    primitive=SurgicalPrimitiveName.INSPECT_RESOURCE_LINES,
                    resource_uri="docs/product/capabilities.yaml",
                    start_line=1,
                    end_line=20,
                    tokens_used=140,
                ),
                ReflexiveTurnDecision(
                    thought_text="Synthese propre de la sous-etape.",
                    action_kind="final_answer",
                    final_markdown="# Livrable Jalon\n\n## Cadrage\nAnalyse validee et consolidee.",
                    tokens_used=160,
                ),
            ]
        }
    )

    workflow = WorkflowDefinitionV2(
        id="wf-milestone-01",
        slug="wf-milestone-01",
        title="Processus a jalons garantis",
        version="1.0.0",
        status=WorkflowLifecycleStatus.PUBLISHED,
        pack_id="orcia-pack-sdlc",
        orchestration_type=ProcessOrchestrationType.DETERMINISTIC_DBOS,
        allowed_delegate_agents=["agent-externe-ignore-en-sous-etape"],
        contract=WorkflowContract(required_markdown_sections=["# Livrable Jalon", "## Cadrage"]),
        sub_steps=[
            DeterministicSubStepSpec(
                id="cadrage",
                name="Cadrage structure",
                short_label="Cadrage",
                enabled=True,
                step_executor_type="agent_executor",
                trigger_condition_label="Demarrage",
                role_description="Structurer le cadrage.",
                instruction_prompt_or_ref="pack://sdlc/agents/orchestrateur-etape.md",
                output_description="Note de cadrage",
                requires_human_checkpoint=True,
                checkpoint_label="Validation du cadrage",
            )
        ],
    )

    result = await dispatcher.dispatch(
        workflow,
        run_id="run-milestone-01",
        inputs={"dossier": "DOS-42"},
        auto_approve_checkpoints=True,
    )

    assert result.orchestration_type == ProcessOrchestrationType.DETERMINISTIC_DBOS
    assert result.status == "COMPLETED_APPROVED"
    assert len(result.sub_step_records) == 1
    sub_rec = result.sub_step_records[0]

    assert sub_rec.reflexive_execution_id is not None
    stored_session = await session_store.load_session_record(sub_rec.reflexive_execution_id)
    assert stored_session is not None
    assert sub_rec.artifact_pointer_payload is not None
    serialized_record = sub_rec.model_dump()
    assert "scratchpad" not in serialized_record
    assert "Exploration interne privee" not in str(serialized_record)

    assert all(c.allow_sub_agent_delegation is False for c in llm.calls)
    assert result.final_artifact_pointer is not None
    assert "## Cadrage" in claim_check.resolve_artifact_text(result.final_artifact_pointer)


def test_declarative_packs_load_dual_orchestration_types() -> None:
    """Verify `packs/orcia-docs` (`NON_DETERMINISTIC`) vs `packs/sdlc` (`DETERMINISTIC_DBOS`)."""
    loader = DeclarativePackLoader(REPO_ROOT / "packs")
    bundles = loader.load_all_packs()

    docs_bundle = bundles["orcia-pack-docs"]
    assert len(docs_bundle.workflows) == 1
    docs_wf = docs_bundle.workflows[0]
    assert docs_wf.id == "wf-generate-orcia-documentation"
    assert docs_wf.orchestration_type == ProcessOrchestrationType.NON_DETERMINISTIC
    assert docs_wf.reflexive_objective is not None and len(docs_wf.reflexive_objective) > 20
    assert docs_wf.allowed_delegate_agents == ["redacteur-documentation-orcia"]

    sdlc_bundle = bundles["orcia-pack-sdlc"]
    assert len(sdlc_bundle.workflows) == 4
    for sdlc_wf in sdlc_bundle.workflows:
        assert sdlc_wf.orchestration_type == ProcessOrchestrationType.DETERMINISTIC_DBOS
