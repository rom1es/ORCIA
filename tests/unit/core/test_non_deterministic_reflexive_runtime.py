"""Unit tests for Story 16.2 (`NonDeterministicReflexiveRuntime`, `asyncio` SSE & Suspend/Resume).

Validates:
- Pure hexagonal ports (`ReflexiveLlmPort`, `ReflexiveEventStreamPort`, `ReflexiveSessionStorePort`,
  `ReflexiveWriteGatePort`) re-exported from `orcia_core.ports`.
- Locked 2-mode effort mapping (`Standard` -> `(4, 8_000)` vs `Approfondi` -> `(25, 48_000)`).
- Full `Think -> Check -> Analyzed #L1-200 -> Final Answer` loop preserving `\n` and Markdown
  indentation + archiving deliverable via `ClaimCheckStorageService` (`ClaimCheckPointer`).
- Strict separation between `cancel_execution` (`0` extra LLM turns, `LOOP_CANCELLED`) and
  `request_synthesize_now` (`force_final=True` immediate synthesis from `scratchpad`).
- Bounded sub-agent delegation (`max_delegation_depth=1`) with `allow_sub_agent_delegation=False`
  enforced on children and shared `tokens_used` budget.
- Stateless Suspend/Resume on `WritePreviewCard` (`WAITING_WRITE_PREVIEW`, 24h TTL, signed approval
  via `SignedApprovalToken`, human rejection recorded in `scratchpad`, rejection of forged token).
- Zero DBOS imports or decorators inside `orcia_core.agents`.
"""

from __future__ import annotations

import ast
import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from orcia_connectors.protocol import (
    ConnectorHealthStatus,
    OrciaConnectorProtocol,
    SignedApprovalToken,
    WritePreviewCard,
    compute_payload_sha256,
    verify_signed_approval_token,
)
from orcia_connectors.reflexive_write_gate import ConnectorReflexiveWriteGateAdapter
from orcia_connectors.surgical import SurgicalContextExplorer
from orcia_core.agents import (
    NonDeterministicReflexiveRuntime,
    ReflexiveEventStreamBroker,
    SqlReflexiveSessionStore,
)
from orcia_core.agents.reflexive_schemas import (
    AgentTraceEvent,
    PendingWritePreviewSpec,
    ProcessOrchestrationType,
    ReflexiveRuntimeConfig,
    ReflexiveSessionSnapshot,
    ReflexiveTurnDecision,
    TraceEventKind,
)
from orcia_core.kernel.errors import PolicyDeniedError, ValidationDomainError
from orcia_core.ports import (
    ReflexiveEventStreamPort,
    ReflexiveLlmChunk,
    ReflexiveLlmPort,
    ReflexiveSessionStorePort,
    ReflexiveTurnInput,
    ReflexiveWriteApprovalInput,
    ReflexiveWriteGatePort,
    SurgicalPrimitiveName,
)
from orcia_core.storage.claim_check import ClaimCheckStorageService
from orcia_core.workflows.schemas_v2 import EffortLevel

REPO_ROOT = Path(__file__).resolve().parents[3]


class ScriptedReflexiveLlmDouble(ReflexiveLlmPort):
    """Deterministic scripted `ReflexiveLlmPort` test double tracking every call."""

    def __init__(
        self,
        decisions_by_actor: dict[str, list[ReflexiveTurnDecision]],
        *,
        turn_delay_seconds: float = 0.0,
    ) -> None:
        self._decisions_by_actor = {k: list(v) for k, v in decisions_by_actor.items()}
        self._turn_delay_seconds = turn_delay_seconds
        self.calls: list[ReflexiveTurnInput] = []

    async def decide_next_turn(self, turn_input: ReflexiveTurnInput) -> ReflexiveTurnDecision:
        if self._turn_delay_seconds > 0:
            await asyncio.sleep(self._turn_delay_seconds)
        self.calls.append(turn_input)
        if turn_input.force_final:
            return ReflexiveTurnDecision(
                thought_text=(
                    "Synthèse anticipée demandée par l'utilisateur.\n Consolidation immédiate."
                ),
                action_kind="final_answer",
                final_markdown=(
                    "## Synthèse immédiate\n\n"
                    f"Éléments consolidés : {len(turn_input.scratchpad)} observation(s)."
                ),
                tokens_used=250,
            )
        queue = self._decisions_by_actor.get(turn_input.actor_slug, [])
        if not queue:
            return ReflexiveTurnDecision(
                thought_text="Fin de file atteinte.",
                action_kind="final_answer",
                final_markdown="# Livrable par défaut\n",
                tokens_used=120,
            )
        return queue.pop(0)

    async def stream_turn_deltas(
        self,
        turn_input: ReflexiveTurnInput,
        decision: ReflexiveTurnDecision,
    ) -> AsyncIterator[ReflexiveLlmChunk]:
        del turn_input
        if decision.thought_text:
            midpoint = max(1, len(decision.thought_text) // 2)
            yield ReflexiveLlmChunk(thinking_delta=decision.thought_text[:midpoint])
            yield ReflexiveLlmChunk(thinking_delta=decision.thought_text[midpoint:])
        if decision.action_kind == "final_answer" and decision.final_markdown:
            midpoint = max(1, len(decision.final_markdown) // 2)
            yield ReflexiveLlmChunk(answer_delta=decision.final_markdown[:midpoint])
            yield ReflexiveLlmChunk(answer_delta=decision.final_markdown[midpoint:])


class FakeEnterpriseWriteConnector(OrciaConnectorProtocol):
    """In-memory `OrciaConnectorProtocol` enforcing `verify_signed_approval_token`."""

    connector_type = "mcp:enterprise-docs"

    def __init__(self) -> None:
        self.executed_writes: list[dict[str, Any]] = []

    async def healthcheck(self) -> ConnectorHealthStatus:
        return ConnectorHealthStatus(connector_type=self.connector_type, ok=True, latency_ms=1)

    async def read(self, resource_uri: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"uri": resource_uri, "query": query or {}}

    async def preview_write(self, action: str, payload: dict[str, Any]) -> WritePreviewCard:
        return WritePreviewCard(
            connector_type=self.connector_type,
            target_resource_uri=str(payload.get("target_uri", "catalog://docs/spec-01")),
            action_summary=f"Publication gouvernée ({action})",
            diff_or_payload_preview={"action": action, "payload": payload},
            payload_sha256=compute_payload_sha256(action, payload),
        )

    async def execute_write(
        self,
        approval_token: SignedApprovalToken,
        action: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        verify_signed_approval_token(approval_token, action=action, payload=payload)
        record = {
            "action": action,
            "payload": payload,
            "approver_user_id": approval_token.approver_user_id,
            "preview_id": approval_token.preview_id,
        }
        self.executed_writes.append(record)
        return {"status": "APPLIED", **record}


def test_two_locked_effort_modes_and_ports_compliance() -> None:
    """Verify `Standard` `(4, 8_000)` vs `Approfondi` `(25, 48_000)` and runtime_checkable ports."""
    for std_level in (EffortLevel.DEFAULT, EffortLevel.LOW, EffortLevel.MEDIUM):
        cfg_std = ReflexiveRuntimeConfig.from_effort_level(std_level)
        assert cfg_std.effort_mode == "standard"
        assert (cfg_std.max_turns, cfg_std.max_budget_tokens) == (4, 8_000)

    cfg_deep = ReflexiveRuntimeConfig.from_effort_level(EffortLevel.HIGH)
    assert cfg_deep.effort_mode == "approfondi"
    assert (cfg_deep.max_turns, cfg_deep.max_budget_tokens) == (25, 48_000)
    assert ProcessOrchestrationType.NON_DETERMINISTIC.value == "non_deterministic"
    assert ProcessOrchestrationType.DETERMINISTIC_DBOS.value == "deterministic_dbos"

    store = SqlReflexiveSessionStore(session_maker=None)
    stream = ReflexiveEventStreamBroker(redis_url=None)
    gate = ConnectorReflexiveWriteGateAdapter(
        connectors={"mcp:enterprise-docs": FakeEnterpriseWriteConnector()}
    )
    assert isinstance(store, ReflexiveSessionStorePort)
    assert isinstance(stream, ReflexiveEventStreamPort)
    assert isinstance(gate, ReflexiveWriteGatePort)


@pytest.mark.asyncio
async def test_full_reflexive_loop_preserves_markdown_newlines_and_stores_claim_check() -> None:
    """Verify `Think -> Check -> Analyzed #L1-30 -> Final Answer` SSE + ClaimCheckPointer."""
    markdown_answer = (
        "# Synthèse d'Architecture\n\n"
        "- Source inspectée : `[S1]` `capabilities.yaml` (`#L1-30`)\n\n"
        "```python\n"
        "def verifier_contrat(entree: str) -> bool:\n"
        "    return bool(entree.strip())\n"
        "```\n"
    )
    llm = ScriptedReflexiveLlmDouble(
        {
            "assistant": [
                ReflexiveTurnDecision(
                    group_title="Vérification du registre des capacités",
                    thought_text=(
                        "1. Vérifions d'abord l'état du fichier.\n   - Cible : capabilities.yaml"
                    ),
                    action_kind="surgical_primitive",
                    primitive=SurgicalPrimitiveName.CHECK_RESOURCE_STATE,
                    resource_uri="docs/product/capabilities.yaml",
                    tokens_used=300,
                ),
                ReflexiveTurnDecision(
                    thought_text="2. Lisons les lignes #L1-30 de capabilities.yaml.",
                    action_kind="surgical_primitive",
                    primitive=SurgicalPrimitiveName.INSPECT_RESOURCE_LINES,
                    resource_uri="docs/product/capabilities.yaml",
                    start_line=1,
                    end_line=30,
                    tokens_used=450,
                ),
                ReflexiveTurnDecision(
                    thought_text="3. Rédigeons la réponse structurée avec bloc de code indenté.",
                    action_kind="final_answer",
                    final_markdown=markdown_answer,
                    tokens_used=500,
                ),
            ]
        }
    )
    explorer = SurgicalContextExplorer()
    store = SqlReflexiveSessionStore(session_maker=None)
    stream = ReflexiveEventStreamBroker(redis_url=None)
    claim_check = ClaimCheckStorageService()
    runtime = NonDeterministicReflexiveRuntime(
        llm_port=llm,
        surgical_explorer=explorer,
        session_store=store,
        event_stream=stream,
        claim_check_storage=claim_check,
    )

    snapshot = await runtime.run_execution(
        actor_slug="assistant",
        objective="Analyser le registre des capacités #L1-30",
        config=ReflexiveRuntimeConfig.from_effort_level(EffortLevel.HIGH, workspace_id="ws-16-2"),
    )

    assert snapshot.status == "COMPLETED"
    assert snapshot.turns_used == 3
    assert snapshot.tokens_used == 1250
    assert snapshot.final_markdown == markdown_answer
    assert snapshot.artifact_pointer is not None
    assert len(snapshot.artifact_pointer.sha256) == 64
    assert claim_check.resolve_artifact_text(snapshot.artifact_pointer) == markdown_answer

    kinds = [ev.kind for ev in snapshot.trace_events]
    assert TraceEventKind.GROUP_HEADER in kinds
    assert TraceEventKind.THOUGHT_DELTA in kinds
    assert TraceEventKind.THOUGHT_COMPLETED in kinds
    assert TraceEventKind.CHECK_EXECUTED in kinds
    assert TraceEventKind.FILE_ANALYZED in kinds
    assert TraceEventKind.ANSWER_TOKEN_DELTA in kinds
    assert kinds[-1] == TraceEventKind.LOOP_COMPLETED

    analyzed_ev = next(
        ev for ev in snapshot.trace_events if ev.kind == TraceEventKind.FILE_ANALYZED
    )
    assert analyzed_ev.formatted_badge == "Analyzed Y capabilities.yaml #L1-30"
    assert (analyzed_ev.start_line, analyzed_ev.end_line) == (1, 30)

    # Streamed answer deltas reassemble verbatim with `\n` and 4-space indentation preserved
    streamed_answer = "".join(
        ev.delta_text or ""
        for ev in snapshot.trace_events
        if ev.kind == TraceEventKind.ANSWER_TOKEN_DELTA
    )
    assert streamed_answer == markdown_answer
    assert "    return bool(entree.strip())\n" in streamed_answer


@pytest.mark.asyncio
async def test_cancel_execution_vs_request_synthesize_now_separation() -> None:
    """Verify `cancel_execution` (`0` extra turns) vs `request_synthesize_now` (`force_final`)."""
    many_explorations = [
        ReflexiveTurnDecision(
            thought_text=f"Exploration étape {idx}",
            action_kind="surgical_primitive",
            primitive=SurgicalPrimitiveName.CHECK_RESOURCE_STATE,
            resource_uri="packs/sdlc/pack.yaml",
            tokens_used=200,
        )
        for idx in range(6)
    ]

    # Case A: Cancel (`■ Arrêter`) stops immediately with 0 extra LLM turns
    llm_cancel = ScriptedReflexiveLlmDouble(
        {"agent-a": list(many_explorations)},
        turn_delay_seconds=0.04,
    )
    runtime_cancel = NonDeterministicReflexiveRuntime(
        llm_port=llm_cancel,
        surgical_explorer=SurgicalContextExplorer(),
        session_store=SqlReflexiveSessionStore(session_maker=None),
        event_stream=ReflexiveEventStreamBroker(redis_url=None),
        claim_check_storage=ClaimCheckStorageService(),
    )
    task_cancel = asyncio.create_task(
        runtime_cancel.run_execution(
            execution_id="exec-cancel-01",
            actor_slug="agent-a",
            objective="Explorer longuement",
            config=ReflexiveRuntimeConfig.from_effort_level(EffortLevel.HIGH),
        )
    )
    await asyncio.sleep(0.05)
    calls_at_cancel = len(llm_cancel.calls)
    cancelled_snap = await runtime_cancel.cancel_execution("exec-cancel-01")
    final_cancel_snap = await task_cancel
    assert cancelled_snap.status == "CANCELLED"
    assert final_cancel_snap.status == "CANCELLED"
    assert final_cancel_snap.trace_events[-1].kind == TraceEventKind.LOOP_CANCELLED
    assert len(llm_cancel.calls) <= calls_at_cancel + 1
    assert len(llm_cancel.calls) < 4

    # Case B: `Synthétiser maintenant` sets `force_final=True` so next turn produces final synthesis
    llm_synth = ScriptedReflexiveLlmDouble(
        {"agent-b": list(many_explorations)},
        turn_delay_seconds=0.04,
    )
    runtime_synth = NonDeterministicReflexiveRuntime(
        llm_port=llm_synth,
        surgical_explorer=SurgicalContextExplorer(),
        session_store=SqlReflexiveSessionStore(session_maker=None),
        event_stream=ReflexiveEventStreamBroker(redis_url=None),
        claim_check_storage=ClaimCheckStorageService(),
    )
    task_synth = asyncio.create_task(
        runtime_synth.run_execution(
            execution_id="exec-synth-01",
            actor_slug="agent-b",
            objective="Explorer puis synthétiser à la demande",
            config=ReflexiveRuntimeConfig.from_effort_level(EffortLevel.HIGH),
        )
    )
    await asyncio.sleep(0.05)
    await runtime_synth.request_synthesize_now("exec-synth-01")
    final_synth_snap = await task_synth
    assert final_synth_snap.status == "COMPLETED"
    assert "Synthèse immédiate" in final_synth_snap.final_markdown
    assert final_synth_snap.artifact_pointer is not None
    assert any(call.force_final for call in llm_synth.calls)


@pytest.mark.asyncio
async def test_bounded_sub_agent_delegation_depth_1_and_shared_token_budget() -> None:
    """Verify `max_delegation_depth=1` blocks child re-delegation and shares token budget."""
    llm = ScriptedReflexiveLlmDouble(
        {
            "orchestrator-goal": [
                ReflexiveTurnDecision(
                    thought_text="Déléguons l'analyse détaillée à `@redacteur-doc`.",
                    action_kind="delegate_sub_agent",
                    delegate_agent_slug="redacteur-doc",
                    delegate_sub_objective="Inspecter packs/orcia-docs/pack.yaml",
                    tokens_used=400,
                ),
                ReflexiveTurnDecision(
                    thought_text="Consolidons le retour du sous-agent.",
                    action_kind="final_answer",
                    final_markdown="# Dossier consolidé avec sous-agent\n",
                    tokens_used=350,
                ),
            ],
            "redacteur-doc": [
                # Attempt a nested delegation from child (must be blocked because depth == 1)
                ReflexiveTurnDecision(
                    thought_text="Tentative de sous-délégation imbriquée.",
                    action_kind="delegate_sub_agent",
                    delegate_agent_slug="autre-agent",
                    delegate_sub_objective="Sous-délégation interdite",
                    tokens_used=200,
                ),
                ReflexiveTurnDecision(
                    thought_text="Synthèse du sous-agent spécialiste.",
                    action_kind="final_answer",
                    final_markdown="Extrait validé par redacteur-doc.",
                    tokens_used=300,
                ),
            ],
        }
    )
    runtime = NonDeterministicReflexiveRuntime(
        llm_port=llm,
        surgical_explorer=SurgicalContextExplorer(),
        session_store=SqlReflexiveSessionStore(session_maker=None),
        event_stream=ReflexiveEventStreamBroker(redis_url=None),
        claim_check_storage=ClaimCheckStorageService(),
    )
    snap = await runtime.run_execution(
        actor_slug="orchestrator-goal",
        objective="Produire la documentation gouvernée",
        config=ReflexiveRuntimeConfig.from_effort_level(
            EffortLevel.HIGH,
            allow_sub_agent_delegation=True,
            available_delegate_agents=("redacteur-doc",),
        ),
    )

    assert snap.status == "COMPLETED"
    # Parent (400 + 350) + Child (200 + 300) = 1250 shared tokens
    assert snap.tokens_used == 1250
    child_calls = [c for c in llm.calls if c.actor_slug == "redacteur-doc"]
    assert len(child_calls) >= 1
    assert all(not c.allow_sub_agent_delegation for c in child_calls)
    assert not any(c.actor_slug == "autre-agent" for c in llm.calls)
    assert any(ev.kind == TraceEventKind.AGENT_DELEGATED for ev in snap.trace_events)


@pytest.mark.asyncio
async def test_stateless_suspend_and_resume_on_write_preview_card_f5_and_token_security() -> None:
    """Verify `WAITING_WRITE_PREVIEW` releases coroutine, survives reload, and checks token."""
    connector = FakeEnterpriseWriteConnector()
    write_gate = ConnectorReflexiveWriteGateAdapter(
        connectors={connector.connector_type: connector}
    )
    shared_store = SqlReflexiveSessionStore(session_maker=None)
    shared_stream = ReflexiveEventStreamBroker(redis_url=None)
    claim_check = ClaimCheckStorageService()

    write_payload = {"target_uri": "catalog://docs/guide-01", "body": "# Guide mis à jour\n"}
    llm_phase_1 = ScriptedReflexiveLlmDouble(
        {
            "doc-agent": [
                ReflexiveTurnDecision(
                    thought_text="Proposons la mise à jour externe gouvernée.",
                    action_kind="propose_external_write_preview",
                    connector_type=connector.connector_type,
                    write_action="publish_document",
                    write_target_uri="catalog://docs/guide-01",
                    write_summary="Publier le guide v1.1",
                    write_payload=write_payload,
                    tokens_used=320,
                )
            ]
        }
    )
    runtime_1 = NonDeterministicReflexiveRuntime(
        llm_port=llm_phase_1,
        surgical_explorer=SurgicalContextExplorer(),
        session_store=shared_store,
        event_stream=shared_stream,
        write_gate=write_gate,
        claim_check_storage=claim_check,
    )

    paused = await runtime_1.run_execution(
        execution_id="exec-write-01",
        actor_slug="doc-agent",
        objective="Mettre à jour le guide documentaire",
        config=ReflexiveRuntimeConfig.from_effort_level(EffortLevel.DEFAULT),
    )
    assert paused.status == "WAITING_WRITE_PREVIEW"
    assert paused.pending_write_preview is not None
    assert paused.trace_events[-1].kind == TraceEventKind.WRITE_PREVIEW_REQUESTED
    assert len(connector.executed_writes) == 0
    assert runtime_1.active_task_count == 0  # Zero blocked coroutine held in RAM!

    # Simulate F5 / fresh runtime process reloading solely from `shared_store`
    llm_phase_2 = ScriptedReflexiveLlmDouble(
        {
            "doc-agent": [
                ReflexiveTurnDecision(
                    thought_text="Écriture confirmée, finalisons le compte-rendu.",
                    action_kind="final_answer",
                    final_markdown="# Publication externe confirmée\n",
                    tokens_used=280,
                )
            ]
        }
    )
    runtime_2 = NonDeterministicReflexiveRuntime(
        llm_port=llm_phase_2,
        surgical_explorer=SurgicalContextExplorer(),
        session_store=shared_store,
        event_stream=shared_stream,
        write_gate=write_gate,
        claim_check_storage=claim_check,
    )

    preview: PendingWritePreviewSpec = paused.pending_write_preview
    reloaded = await runtime_2.get_session_snapshot("exec-write-01")
    assert reloaded is not None
    assert reloaded.status == "WAITING_WRITE_PREVIEW"

    # 1. Forged `SignedApprovalToken` signature MUST be rejected with PolicyDeniedError
    forged_approval = ReflexiveWriteApprovalInput(
        preview_id=preview.preview_id,
        approver_user_id="user-admin-01",
        approved_at_utc=datetime.now(UTC).isoformat(),
        payload_sha256=preview.payload_sha256,
        broker_signature="0" * 64,
    )
    with pytest.raises(PolicyDeniedError):
        await runtime_2.resume_after_write_decision(
            "exec-write-01",
            approved=True,
            approval=forged_approval,
        )
    assert len(connector.executed_writes) == 0

    # 2. Valid Permission Broker `SignedApprovalToken` executes write and completes at turn + 1
    card = WritePreviewCard(
        preview_id=preview.preview_id,
        connector_type=preview.connector_type,
        target_resource_uri=preview.target_resource_uri,
        action_summary=preview.action_summary,
        diff_or_payload_preview=preview.diff_or_payload_preview,
        payload_sha256=preview.payload_sha256,
    )
    signed = SignedApprovalToken.issue(preview_card=card, approver_user_id="user-admin-01")
    valid_approval = ReflexiveWriteApprovalInput(
        preview_id=signed.preview_id,
        approver_user_id=signed.approver_user_id,
        approved_at_utc=signed.approved_at_utc,
        payload_sha256=signed.payload_sha256,
        broker_signature=signed.broker_signature,
    )
    completed = await runtime_2.resume_after_write_decision(
        "exec-write-01",
        approved=True,
        approval=valid_approval,
    )
    assert completed.status == "COMPLETED"
    assert completed.pending_write_preview is None
    assert len(connector.executed_writes) == 1
    assert completed.turns_used == 2
    assert completed.tokens_used == 600
    assert completed.artifact_pointer is not None


@pytest.mark.asyncio
async def test_write_preview_human_rejection_and_ttl_24h_expiration() -> None:
    """Verify human rejection records refusal in `scratchpad` (0 writes) and expired TTL fails."""
    connector = FakeEnterpriseWriteConnector()
    write_gate = ConnectorReflexiveWriteGateAdapter(
        connectors={connector.connector_type: connector}
    )
    store = SqlReflexiveSessionStore(session_maker=None)
    llm = ScriptedReflexiveLlmDouble(
        {
            "doc-agent": [
                ReflexiveTurnDecision(
                    thought_text="Proposons l'écriture.",
                    action_kind="propose_external_write_preview",
                    connector_type=connector.connector_type,
                    write_action="publish_document",
                    write_target_uri="catalog://docs/guide-02",
                    write_summary="Publier le guide v2",
                    write_payload={"target_uri": "catalog://docs/guide-02", "body": "Brouillon"},
                    tokens_used=200,
                ),
                ReflexiveTurnDecision(
                    thought_text="Prenons acte du refus humain et livrons le brouillon local.",
                    action_kind="final_answer",
                    final_markdown="# Brouillon conservé sans publication externe\n",
                    tokens_used=210,
                ),
            ]
        }
    )
    runtime = NonDeterministicReflexiveRuntime(
        llm_port=llm,
        surgical_explorer=SurgicalContextExplorer(),
        session_store=store,
        event_stream=ReflexiveEventStreamBroker(redis_url=None),
        write_gate=write_gate,
        claim_check_storage=ClaimCheckStorageService(),
    )

    paused = await runtime.run_execution(
        execution_id="exec-reject-01",
        actor_slug="doc-agent",
        objective="Proposer une publication",
        config=ReflexiveRuntimeConfig.from_effort_level(EffortLevel.DEFAULT),
    )
    assert paused.status == "WAITING_WRITE_PREVIEW"

    resumed = await runtime.resume_after_write_decision(
        "exec-reject-01",
        approved=False,
        rejection_reason="Validation éditoriale supplémentaire requise avant publication.",
    )
    assert resumed.status == "COMPLETED"
    assert len(connector.executed_writes) == 0
    assert any(
        "Validation éditoriale supplémentaire requise" in entry.summary
        for entry in resumed.scratchpad
    )

    # Expired TTL (> 24h) session cannot be resumed
    expired_snap: ReflexiveSessionSnapshot = paused.model_copy(
        update={
            "execution_id": "exec-expired-01",
            "expires_at_utc": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
        }
    )
    await store.save_session_record(
        "exec-expired-01",
        workspace_id=expired_snap.workspace_id,
        actor_slug=expired_snap.actor_slug,
        orchestration_mode=expired_snap.orchestration_type.value,
        effort_level=expired_snap.effort_level.value,
        status=expired_snap.status,
        snapshot_payload=expired_snap.model_dump(mode="json"),
        expires_at_utc=expired_snap.expires_at_utc,
    )
    with pytest.raises(ValidationDomainError):
        await runtime.resume_after_write_decision(
            "exec-expired-01",
            approved=False,
            rejection_reason="Trop tard",
        )


def test_zero_dbos_imports_or_decorators_in_orcia_core_agents() -> None:
    """Verify `orcia_core/agents/` contains zero `dbos` imports or `@DBOS.*` decorators."""
    agents_dir = REPO_ROOT / "packages" / "orcia-core" / "src" / "orcia_core" / "agents"
    py_files = sorted(agents_dir.rglob("*.py"))
    assert len(py_files) >= 3
    for py_file in py_files:
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("dbos"), f"DBOS import in {py_file}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("dbos"), f"DBOS from-import in {py_file}"
        assert "@DBOS." not in source
        assert "AgentTraceEvent" in source or py_file.name != "reflexive_schemas.py"
    assert AgentTraceEvent is not None
