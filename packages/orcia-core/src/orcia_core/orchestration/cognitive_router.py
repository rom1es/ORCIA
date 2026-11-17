"""Cognitive LLM Tier Router (`simple|medium|complex|auto`), Effort & DBOS Escalation (`Story 8.2`).

Implements (`AD-10`, `AD-12`, `AD-19`, `AD-21`, `PROC-01`, `Story 6.2`):
- Abstract cognitive tiers (`simple`, `medium`, `complex`, `auto`) and `effort`
- Deterministic `auto` escalation persisted idempotently in `inference_attempts`
- Hierarchical budget quotas and agent anti-loop guards delegated to `CognitiveBudgetGuard`
- Active run pinning guard (`HTTP 409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` with `drain` / `force`)
- End-to-end durable workflow execution (`PROC-01`)
"""

from __future__ import annotations

from collections.abc import Callable

from orcia_core.orchestration._cognitive_budget_guard import (
    BudgetCheckResult,
    CognitiveBudgetGuard,
)
from orcia_core.orchestration._cognitive_router_execution import (
    execute_tier_routing_loop,
)
from orcia_core.orchestration._cognitive_router_models import (
    EFFORT_TOKEN_MULTIPLIER,
    CognitiveRoutingOutcome,
    DurableProc01RunState,
    InferenceAttemptRecord,
    InferenceEffort,
    InferenceTier,
    PinRemovalMode,
    ResolvedInferenceTier,
    WorkspaceLlmTierMapping,
    build_default_tier_mappings,
)
from orcia_core.orchestration._cognitive_router_proc01 import (
    replay_and_resume_proc01_run_helper,
    start_proc01_durable_run_helper,
)
from orcia_core.orchestration._cognitive_router_registry import (
    delete_or_drain_mapping_helper,
    resolve_tier_mapping,
)
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    TierModelNotConfiguredError,
    ValidationDomainError,
)
from orcia_core.ports.finops_telemetry import BudgetCircuitGuardPort
from orcia_kernel.ports import LLMPort


class CognitiveModelRouterService:
    """Domain service resolving abstract LLM tiers, effort, budgets & `auto` escalation."""

    def __init__(
        self,
        *,
        llm_gateway: LLMPort,
        initial_mappings: tuple[WorkspaceLlmTierMapping, ...] | None = None,
        budget_guard: CognitiveBudgetGuard | None = None,
        external_budget_guard_port: BudgetCircuitGuardPort | None = None,
    ) -> None:
        self._llm_gateway = llm_gateway
        seed = initial_mappings if initial_mappings is not None else build_default_tier_mappings()
        self._mappings: dict[str, WorkspaceLlmTierMapping] = {m.id: m for m in seed}
        self._attempts_by_key: dict[str, InferenceAttemptRecord] = {}
        self._scope_budgets_usd: dict[str, float] = {}
        self._scope_spent_usd: dict[str, float] = {}
        self._pinned_models_by_mapping_id: dict[str, set[str]] = {}
        self._proc01_runs: dict[str, DurableProc01RunState] = {}
        self._budget_guard = budget_guard or CognitiveBudgetGuard(
            external_guard_port=external_budget_guard_port
        )

    @property
    def budget_guard(self) -> CognitiveBudgetGuard:
        return self._budget_guard

    @property
    def llm_gateway(self) -> LLMPort:
        return self._llm_gateway

    @property
    def scope_budgets_usd(self) -> dict[str, float]:
        return self._scope_budgets_usd

    @property
    def scope_spent_usd(self) -> dict[str, float]:
        return self._scope_spent_usd

    def get_cached_attempt(self, key: str) -> InferenceAttemptRecord | None:
        return self._attempts_by_key.get(key)

    def record_attempt(self, key: str, attempt: InferenceAttemptRecord) -> None:
        self._attempts_by_key[key] = attempt

    def add_scope_spent(self, scopes: tuple[str, ...], amount: float) -> None:
        for sc in scopes:
            self._scope_spent_usd[sc] = round(self._scope_spent_usd.get(sc, 0.0) + amount, 6)

    def list_mappings(self, scope_id: str | None = None) -> list[WorkspaceLlmTierMapping]:
        items = list(self._mappings.values())
        return [m for m in items if m.scope_id == scope_id] if scope_id is not None else items

    def list_attempts(
        self, run_id: str, step_execution_id: str | None = None
    ) -> list[InferenceAttemptRecord]:
        items = [a for a in self._attempts_by_key.values() if a.run_id == run_id]
        if step_execution_id is not None:
            items = [a for a in items if a.step_execution_id == step_execution_id]
        return sorted(items, key=lambda a: a.attempt_index)

    def set_scope_budget_ceiling(
        self, scope_id: str, max_cost_usd: float, *, actor_role: str = "PLATFORM_ADMIN"
    ) -> None:
        if actor_role == "OBSERVER":
            raise ObserverModeReadOnlyError()
        if max_cost_usd < 0:
            raise ValidationDomainError(detail_override="max_cost_usd must be non-negative.")
        self._scope_budgets_usd[scope_id] = max_cost_usd

    def pin_mapping_for_active_run(self, mapping_id: str, run_id: str) -> None:
        self._pinned_models_by_mapping_id.setdefault(mapping_id, set()).add(run_id)

    def unpin_mapping_for_run(self, mapping_id: str, run_id: str) -> None:
        runs = self._pinned_models_by_mapping_id.get(mapping_id)
        if runs is not None:
            runs.discard(run_id)

    def upsert_mapping(
        self, mapping: WorkspaceLlmTierMapping, *, actor_role: str = "PLATFORM_ADMIN"
    ) -> WorkspaceLlmTierMapping:
        if actor_role == "OBSERVER":
            raise ObserverModeReadOnlyError()
        self._mappings[mapping.id] = mapping
        return mapping

    def delete_or_drain_mapping(
        self,
        mapping_id: str,
        *,
        mode: PinRemovalMode = "reject",
        actor_role: str = "PLATFORM_ADMIN",
        instance: str | None = None,
    ) -> WorkspaceLlmTierMapping | None:
        return delete_or_drain_mapping_helper(
            self._mappings,
            self._pinned_models_by_mapping_id,
            mapping_id,
            mode=mode,
            actor_role=actor_role,
            instance=instance,
        )

    def resolve_mapping(
        self,
        *,
        scope_id: str,
        tier: ResolvedInferenceTier,
        effort: InferenceEffort = "default",
        allow_draining: bool = False,
    ) -> WorkspaceLlmTierMapping:
        return resolve_tier_mapping(
            self._mappings,
            scope_id=scope_id,
            tier=tier,
            effort=effort,
            allow_draining=allow_draining,
        )

    async def execute_with_tier_routing(
        self,
        *,
        run_id: str,
        step_execution_id: str,
        scope_id: str,
        system_prompt: str,
        user_prompt: str,
        inference_tier: InferenceTier = "medium",
        effort: InferenceEffort = "default",
        evaluator_model_family: str | None = None,
        deterministic_gate_fn: Callable[[str, ResolvedInferenceTier], tuple[bool, str]]
        | None = None,
        scope_hierarchy_ids: tuple[str, ...] = (),
        max_agent_retries: int = 3,
        run_budget_ceiling_usd: float | None = None,
        run_spent_usd: float = 0.0,
    ) -> CognitiveRoutingOutcome:
        """Execute an LLM call with tier resolution, `auto` escalation & DBOS idempotency."""
        return await execute_tier_routing_loop(
            self,
            run_id=run_id,
            step_execution_id=step_execution_id,
            scope_id=scope_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            inference_tier=inference_tier,
            effort=effort,
            evaluator_model_family=evaluator_model_family,
            deterministic_gate_fn=deterministic_gate_fn,
            scope_hierarchy_ids=scope_hierarchy_ids,
            max_agent_retries=max_agent_retries,
            run_budget_ceiling_usd=run_budget_ceiling_usd,
            run_spent_usd=run_spent_usd,
        )

    async def start_proc01_durable_run(
        self,
        *,
        workspace_id: str,
        user_prompt: str,
        effort: InferenceEffort = "balanced",
    ) -> DurableProc01RunState:
        state = await start_proc01_durable_run_helper(
            self,
            workspace_id=workspace_id,
            user_prompt=user_prompt,
            effort=effort,
        )
        self._proc01_runs[state.run_id] = state
        return state

    async def replay_and_resume_proc01_run(
        self,
        *,
        run_id: str,
        arbitration_choice: str,
    ) -> DurableProc01RunState:
        current = self._proc01_runs.get(run_id)
        completed = await replay_and_resume_proc01_run_helper(
            self,
            current,
            run_id=run_id,
            arbitration_choice=arbitration_choice,
        )
        self._proc01_runs[run_id] = completed
        return completed


__all__ = [
    "BudgetCheckResult",
    "CognitiveBudgetGuard",
    "CognitiveModelRouterService",
    "CognitiveRoutingOutcome",
    "DurableProc01RunState",
    "EFFORT_TOKEN_MULTIPLIER",
    "InferenceAttemptRecord",
    "InferenceEffort",
    "InferenceTier",
    "PinRemovalMode",
    "ResolvedInferenceTier",
    "TierModelNotConfiguredError",
    "WorkspaceLlmTierMapping",
    "build_default_tier_mappings",
]
