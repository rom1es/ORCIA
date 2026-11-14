---
document_type: BACKEND_TECHNICAL_SPECIFICATION
epic_id: EPIC-11
version: "2.0.0"
target_packages:
  - "packages/orcia-core/src/orcia_core/agents/"
  - "packages/orcia-core/src/orcia_core/workflows/"
  - "packages/orcia-connectors/src/orcia_connectors/"
  - "apps/api/src/orcia_api/routers/"
---

# Architecture Backend (v2) — Séparation Runtime Non-Déterministe (`asyncio`) et Moteur Déterministe (`DBOS`)

Cette architecture implémente la règle stricte d'orchestration d'ORCIA :
1. **L'Assistant et les Agents** sont **toujours** orchestrés par `NonDeterministicReflexiveRuntime` (`asyncio` pur + Redis SSE, **sans `@DBOS.workflow` ni `@DBOS.step`**).
2. **Les Processus** portent un attribut discriminant `orchestration_type: ProcessOrchestrationType` :
   * `NON_DETERMINISTIC` $\rightarrow$ Exécuté par `NonDeterministicProcessRunner` (planification dynamique d'étapes et d'agents en mémoire + Gates finales).
   * `DETERMINISTIC_DBOS` $\rightarrow$ Exécuté par `run_bounded_workflow_v2` sous **DBOS** (machine à états persistée dans PostgreSQL). Lorsqu'une étape DBOS invoque un Agent, l'activité DBOS appelle en interne `NonDeterministicReflexiveRuntime` (encapsulation Macro-Déterministe / Micro-Non-Déterministe du Principe 7 de l'ADR-02).

---

## 1. Schémas Pydantic v2 (`packages/orcia-core/src/orcia_core/agents/reflexive_schemas.py`)

```python
from enum import StrEnum
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from orcia_core.workflows.schemas_v2 import ClaimCheckPointer, CognitiveEffortLevel


class ProcessOrchestrationType(StrEnum):
    """Sélecteur du moteur d'orchestration pour un Processus ORCIA."""

    NON_DETERMINISTIC = (
        "non_deterministic"  # Planification dynamique par LLM (Style Antigravity, sans DBOS)
    )
    DETERMINISTIC_DBOS = (
        "deterministic_dbos"  # Machine à états stricte et durable (DBOS / PostgreSQL)
    )


class SurgicalPrimitiveName(StrEnum):
    CHECK_RESOURCE_STATE = "check_resource_state"
    OUTLINE_RESOURCE_STRUCTURE = "outline_resource_structure"
    SEARCH_WORKSPACE_SNIPPETS = "search_workspace_snippets"
    INSPECT_RESOURCE_LINES = "inspect_resource_lines"


class ReflexiveRuntimeConfig(BaseModel):
    """Configuration de l'orchestrateur non-déterministe (utilisé par Assistant, Agents et Processus Non-Déterministes)."""

    model_config = ConfigDict(extra="forbid")

    default_effort: CognitiveEffortLevel = CognitiveEffortLevel.BALANCED
    max_lines_per_inspection: int = Field(default=200, ge=50, le=250)
    allowed_surgical_primitives: list[SurgicalPrimitiveName] = Field(
        default_factory=lambda: list(SurgicalPrimitiveName)
    )
    allow_sub_agent_delegation: bool = Field(
        default=False,
        description="Activé pour les Processus Non-Déterministes pouvant déléguer à plusieurs agents du Pack",
    )
    show_thoughts_in_ui: bool = True
    show_line_ranges_in_ui: bool = True

    def resolve_bounds(
        self, effort_override: CognitiveEffortLevel | None = None
    ) -> tuple[int, int]:
        effort = effort_override or self.default_effort
        return {
            CognitiveEffortLevel.FAST: (4, 4_000),
            CognitiveEffortLevel.BALANCED: (10, 16_000),
            CognitiveEffortLevel.DEEP: (25, 48_000),
        }.get(effort, (10, 16_000))


class TraceEventKind(StrEnum):
    GROUP_HEADER = "trace.group_header"
    THOUGHT_COMPLETED = "trace.thought_completed"
    CHECK_EXECUTED = "trace.check_executed"
    FILE_ANALYZED = "trace.file_analyzed"
    AGENT_DELEGATED = "trace.agent_delegated"
    WRITE_PREVIEW_REQUESTED = "trace.write_preview_requested"
    STATUS_WORKING = "trace.status_working"
    LOOP_COMPLETED = "trace.loop_completed"


class AgentTraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    execution_id: str
    turn_index: int
    kind: TraceEventKind
    timestamp_utc: str
    group_title: str | None = None
    duration_seconds: float | None = None
    thought_markdown: str | None = None
    check_label: str | None = None
    check_output_summary: str | None = None
    delegated_agent_slug: str | None = None
    resource_uri: str | None = None
    display_filename: str | None = None
    file_badge_code: str | None = None  # "M↓", "Y", "TS", "PY", "DOC"
    start_line: int | None = None
    end_line: int | None = None
    total_lines: int | None = None
    cumulative_tokens: int = 0
    max_turns: int = 10


class ReflexiveTurnDecision(BaseModel):
    """Décision dynamique prise à chaque tour par l'Assistant, l'Agent ou le Processus Non-Déterministe."""

    model_config = ConfigDict(extra="forbid")

    current_group_header: str
    thought: str
    next_action_type: Literal[
        "call_surgical_read_tool",
        "call_skill_or_mcp_read",
        "delegate_to_specialist_agent",
        "propose_external_write_preview",
        "ask_human_clarification",
        "final_answer",
    ]
    target_name: str | None = Field(
        default=None,
        description="Nom de la primitive chirurgicale, du skill, de l'outil MCP ou de l'agent délégué",
    )
    arguments: dict[str, Any] = Field(default_factory=dict)
    final_response_markdown: str | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
```

---

## 2. Le Moteur Non-Déterministe Pur (`packages/orcia-core/src/orcia_core/agents/reflexive_runtime.py`)

Aucun décorateur `@DBOS.workflow()` ni `@DBOS.step` n'est utilisé ici. Le moteur tourne en `asyncio` natif, publie en direct sur **Redis Pub/Sub (SSE)** et gère les pauses d'écriture (`Write-Preview Gate`) via un canal de signalisation Redis asynchrone léger :

```python
import time
import asyncio
from orcia_core.agents.reflexive_schemas import (
    ReflexiveRuntimeConfig,
    AgentTraceEvent,
    TraceEventKind,
    ReflexiveTurnDecision,
)
from orcia_core.workflows.schemas_v2 import ClaimCheckPointer, CognitiveEffortLevel


class NonDeterministicReflexiveRuntime:
    """
    Orchestrateur non-déterministe (style Antigravity) pour :
    1. Mon Assistant
    2. Les Agents LLM
    3. Les Processus configurés en mode NON_DETERMINISTIC
    """

    def __init__(
        self, redis_pubsub, surgical_explorer, permission_broker, claim_check_store, llm_gateway
    ):
        self.redis = redis_pubsub
        self.explorer = surgical_explorer
        self.broker = permission_broker
        self.store = claim_check_store
        self.llm = llm_gateway

    async def execute_reflexive_loop(
        self,
        execution_id: str,
        actor_slug: str,
        system_instructions: str,
        user_objective: str,
        config: ReflexiveRuntimeConfig,
        scoped_token: str,
        effort_override: CognitiveEffortLevel | None = None,
    ) -> dict:
        max_turns, max_tokens = config.resolve_bounds(effort_override)
        scratchpad: list[dict] = []
        trace_events: list[AgentTraceEvent] = []
        cumulative_tokens = 0
        last_group_header = ""

        for turn in range(1, max_turns + 1):
            early_stop = await self.redis.check_early_stop_flag(execution_id)
            force_final = (
                (turn == max_turns) or (cumulative_tokens >= int(max_tokens * 0.9)) or early_stop
            )

            # 1. THINK : Raisonnement et planification dynamique du prochain pas (sans DBOS)
            t0 = time.monotonic()
            decision, tokens_used = await self.llm.decide_next_reflexive_step(
                actor_slug=actor_slug,
                system_instructions=system_instructions,
                user_objective=user_objective,
                scratchpad=scratchpad,
                allow_delegation=config.allow_sub_agent_delegation,
                force_final=force_final,
            )
            thought_duration = round(max(1.0, time.monotonic() - t0), 1)
            cumulative_tokens += tokens_used

            if decision.current_group_header != last_group_header:
                last_group_header = decision.current_group_header
                await self._emit(
                    trace_events,
                    execution_id,
                    turn,
                    TraceEventKind.GROUP_HEADER,
                    group_title=last_group_header,
                    cumulative_tokens=cumulative_tokens,
                    max_turns=max_turns,
                )

            if config.show_thoughts_in_ui and decision.thought:
                await self._emit(
                    trace_events,
                    execution_id,
                    turn,
                    TraceEventKind.THOUGHT_COMPLETED,
                    duration_seconds=thought_duration,
                    thought_markdown=decision.thought,
                    cumulative_tokens=cumulative_tokens,
                    max_turns=max_turns,
                )

            # 2. FINAL ANSWER : Fin de la boucle non-déterministe & archivage unique Claim-Check S3
            if decision.next_action_type == "final_answer" or force_final:
                pointer: ClaimCheckPointer = await self.store.put_artifact_and_trace(
                    execution_id=execution_id,
                    markdown_content=decision.final_response_markdown or "",
                    citations=decision.citations,
                    trace_events=[e.model_dump() for e in trace_events],
                )
                await self._emit(
                    trace_events,
                    execution_id,
                    turn,
                    TraceEventKind.LOOP_COMPLETED,
                    cumulative_tokens=cumulative_tokens,
                    max_turns=max_turns,
                )
                return {
                    "status": "COMPLETED",
                    "orchestration_mode": "non_deterministic",
                    "artifact_pointer": pointer.model_dump(),
                    "turns_used": turn,
                    "tokens_used": cumulative_tokens,
                }

            # 3. ACT & OBSERVE : Exploration chirurgicale (#L1-200) ou Vérification d'état (Check ...)
            if decision.next_action_type == "call_surgical_read_tool":
                obs = await self.explorer.execute_primitive(
                    primitive_name=decision.target_name,
                    arguments=decision.arguments,
                    scoped_token=scoped_token,
                )
                scratchpad.append({"turn": turn, "observation": obs})
                if obs["kind"] == "file_lines":
                    await self._emit(
                        trace_events,
                        execution_id,
                        turn,
                        TraceEventKind.FILE_ANALYZED,
                        resource_uri=obs["resource_uri"],
                        display_filename=obs["display_filename"],
                        file_badge_code=obs["file_badge_code"],
                        start_line=obs["start_line"],
                        end_line=obs["end_line"],
                        total_lines=obs["total_lines"],
                        cumulative_tokens=cumulative_tokens,
                        max_turns=max_turns,
                    )
                else:
                    await self._emit(
                        trace_events,
                        execution_id,
                        turn,
                        TraceEventKind.CHECK_EXECUTED,
                        check_label=obs["check_label"],
                        check_output_summary=obs["summary"],
                        cumulative_tokens=cumulative_tokens,
                        max_turns=max_turns,
                    )
                continue

            # 4. DÉLÉGATION DYNAMIQUE À UN AGENT (Utilisé par les Processus Non-Déterministes)
            if (
                decision.next_action_type == "delegate_to_specialist_agent"
                and config.allow_sub_agent_delegation
            ):
                await self._emit(
                    trace_events,
                    execution_id,
                    turn,
                    TraceEventKind.AGENT_DELEGATED,
                    delegated_agent_slug=decision.target_name,
                    check_label=decision.arguments.get("sub_objective", ""),
                    cumulative_tokens=cumulative_tokens,
                    max_turns=max_turns,
                )
                sub_result = await self.execute_sub_agent(
                    parent_execution_id=execution_id,
                    agent_slug=decision.target_name,
                    sub_objective=decision.arguments.get("sub_objective", ""),
                    scoped_token=scoped_token,
                )
                scratchpad.append(
                    {"turn": turn, "delegated_agent": decision.target_name, "result": sub_result}
                )
                continue

            # 5. WRITE-PREVIEW GATE : Validation humaine obligatoire avant toute écriture externe
            if decision.next_action_type == "propose_external_write_preview":
                preview_card = await self.broker.prepare_write_preview(
                    scoped_token=scoped_token,
                    connector_action=decision.target_name,
                    payload=decision.arguments,
                )
                await self._emit(
                    trace_events,
                    execution_id,
                    turn,
                    TraceEventKind.WRITE_PREVIEW_REQUESTED,
                    check_label=preview_card.action_summary,
                    cumulative_tokens=cumulative_tokens,
                    max_turns=max_turns,
                )
                approval = await self.redis.wait_for_human_write_approval(
                    execution_id, preview_card.preview_id
                )
                if approval.approved:
                    write_res = await self.broker.execute_approved_write(
                        approval_token=approval.signed_token,
                        connector_action=decision.target_name,
                        payload=decision.arguments,
                    )
                    scratchpad.append({"turn": turn, "write_executed": write_res})
                else:
                    scratchpad.append(
                        {"turn": turn, "write_rejected_by_human": approval.rejection_reason}
                    )

        return {"status": "MAX_TURNS_REACHED", "turns_used": max_turns}
```

---

## 3. Articulation dans « Mes Processus » : `ProcessExecutionDispatcher` (`packages/orcia-core/src/orcia_core/workflows/dispatcher.py`)

Lorsqu'un utilisateur lance un **Processus** dans ORCIA, le dispatcher aiguille vers le bon moteur selon `workflow_spec.orchestration_type` :

```python
from orcia_core.agents.reflexive_schemas import ProcessOrchestrationType
from orcia_core.workflows.schemas_v2 import WorkflowDefinitionV2


class ProcessExecutionDispatcher:
    """
    Aiguilleur central des Processus ORCIA :
    - Si orchestration_type == NON_DETERMINISTIC : exécute `NonDeterministicReflexiveRuntime`
      avec `allow_sub_agent_delegation=True`, puis passe le livrable dans le `GatePipelineExecutor`.
    - Si orchestration_type == DETERMINISTIC_DBOS : démarre le workflow durable `@DBOS.workflow()`
      `run_bounded_workflow_v2` dans PostgreSQL.
    """

    async def start_process(
        self, workflow: WorkflowDefinitionV2, inputs: dict, scoped_token: str
    ) -> dict:
        if workflow.orchestration_type == ProcessOrchestrationType.NON_DETERMINISTIC:
            # Exécution dynamique de bout en bout sans DBOS
            result = await self.reflexive_runtime.execute_reflexive_loop(
                execution_id=inputs["run_id"],
                actor_slug=workflow.slug,
                system_instructions=workflow.system_prompt_inline or "",
                user_objective=self._format_objective_with_contract(workflow, inputs),
                config=workflow.reflexive_config,
                scoped_token=scoped_token,
            )
            # Application des Gates de sortie (Déterministes puis Contradictoires) sur l'artefact produit
            gate_report = await self.gate_executor.evaluate_output(
                workflow=workflow, artifact_pointer=result["artifact_pointer"]
            )
            return {"mode": "non_deterministic", "result": result, "gate_report": gate_report}

        # Sinon : Processus Déterministe orchestré par DBOS
        handle = await self.dbos_launcher.start_durable_workflow(workflow, inputs, scoped_token)
        return {"mode": "deterministic_dbos", "workflow_handle_id": handle.workflow_id}
```
