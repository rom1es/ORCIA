"""Assistant Agent Synthesis & SSE Formatting Helpers (`Story 3.3`, `Story 26.1`)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration.assistant_agent_models import (
    AssistantTurnResult,
    AssistantWorkflowProposal,
    SavedAndLaunchedWorkflowResult,
)
from orcia_core.orchestration.assistant_composer import (
    blueprint_to_proposal,
    resolve_assistant_blueprint,
)
from orcia_core.orchestration.assistant_harness import AssembledAssistantPrompt, AssistantIntentKind
from orcia_core.orchestration.errors import TierModelNotConfiguredError
from orcia_core.orchestration.step_executors import _run_llm_sync
from orcia_core.permissions.models import UserIdentity
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.context_ports import AssistantWorkflowBlueprint
from orcia_kernel.ports import LLMPort, LlmPromptRequest

logger = get_logger("orcia.core.orchestration.assistant_agent")


def classify_assistant_intent(
    user_prompt: str, *, has_active_proposal: bool = False
) -> AssistantIntentKind:
    """Node 1 (`1_INTENT_ROUTER`): classify user intent and enforce Constitutional Rule 1."""
    lower = user_prompt.strip().lower()
    if any(
        phrase in lower
        for phrase in (
            "remplis-le pour moi",
            "remplis la section humaine",
            "rédige l'ancre humaine",
            "write the human anchor for me",
            "fill the human anchor",
        )
    ):
        return "HUMAN_ANCHOR_WRITE_REFUSAL"
    if has_active_proposal and any(
        kw in lower for kw in ("modifie", "ajoute", "étape", "step", "ajuste", "modify", "add step")
    ):
        return "WORKFLOW_MODIFY"
    if any(
        kw in lower
        for kw in (
            "workflow",
            "composer",
            "propose un workflow",
            "créer un workflow",
            "comparer",
            "rapprochement",
            "audit",
        )
    ):
        return "WORKFLOW_COMPOSE"
    if any(kw in lower for kw in ("lance", "exécute", "launch", "start run")):
        return "WORKFLOW_LAUNCH"
    return "QA_COACHING"


def execute_saved_and_launched_workflow(
    setup: Any,
    engine: Any,
    user: UserIdentity,
    *,
    workspace_id: str,
    manifest_yaml: str,
) -> SavedAndLaunchedWorkflowResult:
    """Register composed YAML workflow in Workspace and run it through DBOS/Durable engine."""
    if setup is None or engine is None:
        raise RuntimeError(
            "WorkflowOrchestrationSetupService and DurableOrchestrationEngine are required."
        )
    definition = setup.register_workflow_manifest(user, manifest_yaml, workspace_id=workspace_id)
    run = setup.instantiate_workflow_run(
        user, workflow_uri=definition.uri, workspace_id=workspace_id
    )
    engine.initialize_run_steps(run, definition)
    executed_keys: list[str] = []
    for step in definition.steps:
        engine.execute_step(user, run_id=run.id, step_key=step.step_key, commit_immediately=True)
        executed_keys.append(step.step_key)
    active_snaps = engine.blackboard.get_active_snapshots(run.id)
    updated_run = next((r for r in setup.runs if r.id == run.id), None)
    return SavedAndLaunchedWorkflowResult(
        workflow_uri=definition.uri,
        version=definition.version,
        run_id=run.id,
        execution_regime=definition.execution_regime,
        run_status=str(updated_run.status if updated_run is not None else "COMPLETED"),
        executed_step_keys=tuple(executed_keys),
        snapshot_count=len(active_snaps),
    )


def synthesize_assistant_turn_response(
    *,
    llm_gateway: LLMPort,
    cognitive_router: Any | None,
    assembled: AssembledAssistantPrompt,
    intent: AssistantIntentKind,
    proposal: AssistantWorkflowProposal | None,
    workspace_id: str,
) -> str:
    """Synthesize Node 5 text reply via CognitiveRouter / Cassette LLM."""
    prefix = assembled.profile_adaptation.response_prefix_fr
    indicators = ", ".join(assembled.profile_adaptation.highlighted_indicators)
    if intent == "HUMAN_ANCHOR_WRITE_REFUSAL":
        return (
            f"{prefix} Refus constitutionnel (`human_authored_required: true`, `FR-4`, `AD-3`) : "
            "Je ne peux pas rédiger ni pré-remplir une Ancre Humaine à votre place afin de "
            "préserver votre maîtrise intellectuelle (*Think*). Question socratique : "
            "quels sont les 2 invariants métier non négociables que vous souhaitez fixer "
            f"pour le périmètre `{workspace_id}` ?"
        )
    model_family, model_id = "", ""
    if cognitive_router is not None:
        try:
            resolved = cognitive_router.resolve_mapping(
                scope_id=workspace_id, tier="complex", effort="default"
            )
            model_family, model_id = resolved.model_family, resolved.model_name
        except Exception as exc:
            logger.warning(
                "assistant_agent.cognitive_router_resolve_failed",
                workspace_id=workspace_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )
    if not model_family or not model_id:
        if isinstance(llm_gateway, DeterministicCassetteLLM):
            model_family, model_id = "cassette", "cassette/assistant-agent"
        else:
            raise TierModelNotConfiguredError(
                inference_tier="complex", instance=f"assistant_agent:{workspace_id}"
            )
    llm_out = _run_llm_sync(
        llm_gateway,
        LlmPromptRequest(
            system_prompt=assembled.system_prompt,
            user_prompt=assembled.user_prompt,
            model_family=model_family,
            model_id=model_id,
            execution_mode="COACHING",
            metadata={"workspace_id": workspace_id, "intent": intent},
        ),
    )
    uris_note = (
        f" Sources citées : {', '.join(assembled.cited_uris[:3])}."
        if assembled.cited_uris
        else f" Périmètre : `orcia://workspaces/{workspace_id}`."
    )
    if proposal is not None:
        return (
            f"{prefix} ({indicators}) — Proposition de workflow `{proposal.workflow_uri}` "
            f"({len(proposal.nodes)} étapes, régime `{proposal.execution_regime}`) prête dans "
            f"le Canvas `@xyflow/react`.{uris_note} [{llm_out.prompt_sha256[:16]}]"
        )
    return f"{prefix} ({indicators}) — {llm_out.content}.{uris_note} [{llm_out.prompt_sha256[:16]}]"


def iter_assistant_turn_sse_events(turn: AssistantTurnResult) -> Iterator[dict[str, Any]]:
    """Yield SSE event dicts (`node_trace`, `token`, `workflow_proposal`, `done`)."""
    for tr in turn.node_traces:
        yield {
            "event": "node_trace",
            "data": {
                "node_id": tr.node_id,
                "node_order": tr.node_order,
                "duration_ms": tr.duration_ms,
                "summary": tr.summary,
            },
        }
    lines = turn.response_text.splitlines(keepends=True) or [turn.response_text]
    chunk_size = max(1, len(lines) // 4)
    for idx in range(0, len(lines), chunk_size):
        yield {
            "event": "token",
            "data": {
                "turn_id": turn.turn_id,
                "token": "".join(lines[idx : idx + chunk_size]),
                "first_token_latency_ms": turn.first_token_latency_ms,
            },
        }
    if turn.workflow_proposal is not None:
        yield {
            "event": "workflow_proposal",
            "data": {
                "proposal_id": turn.workflow_proposal.proposal_id,
                "workflow_uri": turn.workflow_proposal.workflow_uri,
                "title": turn.workflow_proposal.title,
                "execution_regime": turn.workflow_proposal.execution_regime,
                "node_count": len(turn.workflow_proposal.nodes),
            },
        }
    yield {
        "event": "done",
        "data": {
            "turn_id": turn.turn_id,
            "intent": turn.intent,
            "first_token_latency_ms": turn.first_token_latency_ms,
        },
    }


def resolve_intent_workflow_proposal(
    *,
    intent: AssistantIntentKind,
    user_prompt: str,
    workspace_id: str,
    active_proposals: dict[str, AssistantWorkflowProposal],
    has_active: bool,
) -> tuple[AssistantWorkflowBlueprint | None, AssistantWorkflowProposal | None]:
    """Resolve workflow blueprint & proposal for compose/modify intents."""
    if intent == "WORKFLOW_COMPOSE":
        bp = resolve_assistant_blueprint(
            user_prompt=user_prompt, workspace_id=workspace_id, modification_instruction=None
        )
        prop = blueprint_to_proposal(bp)
        active_proposals[workspace_id] = prop
        return bp, prop
    if intent == "WORKFLOW_MODIFY":
        active_prop = active_proposals.get(workspace_id)
        combined = (
            f"{active_prop.title} {active_prop.workflow_uri} {user_prompt}"
            if active_prop is not None
            else user_prompt
        )
        bp = resolve_assistant_blueprint(
            user_prompt=combined, workspace_id=workspace_id, modification_instruction=user_prompt
        )
        prop = blueprint_to_proposal(bp)
        active_proposals[workspace_id] = prop
        return bp, prop
    return None, (active_proposals.get(workspace_id) if has_active else None)
