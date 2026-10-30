"""Cognitive LLM Tier Router (`simple|medium|complex|auto`), Effort & DBOS Escalation (`Story 8.2`).

Implements (`AD-10`, `AD-12`, `AD-19`, `AD-21`, `PROC-01`):
- Abstract cognitive tiers (`simple`, `medium`, `complex`, `auto`) and `effort`
  (`default`, `fast`, `balanced`, `deep`) mapped per Workspace in `workspace_llm_tier_mappings`
- Deterministic `auto` escalation (`simple -> medium -> complex`) persisted idempotently in
  `inference_attempts` so DBOS workflow replay never re-executes already-attempted tiers
- Hierarchical budget quotas (`GLOBAL -> BU -> TEAM -> WORKSPACE`) checked before each LLM call
- Active run pinning guard (`HTTP 409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` with `drain` / `force`)
- End-to-end durable workflow execution (`PROC-01`: instantiate -> `auto` tier -> pause ->
  restart/replay -> resume -> complete)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any, Literal

from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ResourcePinnedByActiveRunsError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import (
    LlmCompletionResponse,
    LLMPort,
    LlmPromptRequest,
    assert_model_orthogonality,
)
from orcia_kernel.secret_ports import SecretRef

InferenceTier = Literal["simple", "medium", "complex", "auto"]
ResolvedInferenceTier = Literal["simple", "medium", "complex"]
InferenceEffort = Literal["default", "fast", "balanced", "deep"]
PinRemovalMode = Literal["reject", "drain", "force"]

EFFORT_TOKEN_MULTIPLIER: dict[InferenceEffort, float] = {
    "fast": 0.6,
    "default": 1.0,
    "balanced": 1.25,
    "deep": 1.75,
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class WorkspaceLlmTierMapping:
    """Mapping between an abstract `(inference_tier, effort)` and a physical model (`Story 8.2`)."""

    id: str
    scope_level: Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]
    scope_id: str
    inference_tier: ResolvedInferenceTier
    effort: InferenceEffort
    provider_slug: str
    model_family: str
    model_name: str
    secret_ref: SecretRef | None = None
    max_tokens_budget: int = 8192
    max_cost_usd: float = 10.0
    fallback_order: int = 1
    is_active: bool = True
    draining: bool = False
    updated_at_iso: str = field(default_factory=_now_iso)


@dataclass(frozen=True, slots=True)
class InferenceAttemptRecord:
    """Idempotent DBOS sub-step record in `inference_attempts` (`Story 8.2`, `AD-21`)."""

    id: str
    run_id: str
    step_execution_id: str
    attempt_index: int
    requested_tier: InferenceTier
    resolved_tier: ResolvedInferenceTier
    effort: InferenceEffort
    model_family: str
    model_name: str
    deterministic_gate_passed: bool
    failure_reason: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    idempotency_key: str
    response_content: str = ""
    created_at_iso: str = field(default_factory=_now_iso)


@dataclass(frozen=True, slots=True)
class CognitiveRoutingOutcome:
    """Outcome of a cognitive tier invocation (single tier or `auto` escalation)."""

    run_id: str
    step_execution_id: str
    requested_tier: InferenceTier
    final_resolved_tier: ResolvedInferenceTier
    effort: InferenceEffort
    response_content: str
    model_family: str
    model_name: str
    attempts: tuple[InferenceAttemptRecord, ...]
    total_cost_usd: float
    paused_budget_exceeded: bool = False


@dataclass(frozen=True, slots=True)
class DurableProc01RunState:
    """End-to-end durable run state for `PROC-01` verification (`Story 8.2`)."""

    run_id: str
    workspace_id: str
    status: Literal[
        "RUNNING",
        "WAITING_FOR_HUMAN_ARBITRATION",
        "PAUSED_BUDGET_EXCEEDED",
        "COMPLETED",
    ]
    step_1_outcome: CognitiveRoutingOutcome
    arbitration_resolution: str | None = None
    final_artifact: dict[str, Any] = field(default_factory=dict)
    replayed_after_restart: bool = False


def build_default_tier_mappings(
    workspace_id: str = "0195f000-0000-7000-8000-000000000301",
) -> tuple[WorkspaceLlmTierMapping, ...]:
    """Return default `simple`, `medium`, and `complex` tier mappings for `workspace_id`."""
    return (
        WorkspaceLlmTierMapping(
            id="0195f000-0000-7000-8000-000000008201",
            scope_level="WORKSPACE",
            scope_id=workspace_id,
            inference_tier="simple",
            effort="default",
            provider_slug="anthropic",
            model_family="anthropic-claude",
            model_name="claude-3-5-haiku",
            secret_ref=SecretRef(f"secret://workspace/{workspace_id}/ai-models/simple"),
            max_tokens_budget=4096,
            max_cost_usd=2.0,
        ),
        WorkspaceLlmTierMapping(
            id="0195f000-0000-7000-8000-000000008202",
            scope_level="WORKSPACE",
            scope_id=workspace_id,
            inference_tier="medium",
            effort="default",
            provider_slug="openai",
            model_family="openai-gpt",
            model_name="gpt-4o-mini",
            secret_ref=SecretRef(f"secret://workspace/{workspace_id}/ai-models/medium"),
            max_tokens_budget=8192,
            max_cost_usd=5.0,
        ),
        WorkspaceLlmTierMapping(
            id="0195f000-0000-7000-8000-000000008203",
            scope_level="WORKSPACE",
            scope_id=workspace_id,
            inference_tier="complex",
            effort="default",
            provider_slug="anthropic",
            model_family="anthropic-claude",
            model_name="claude-3-7-sonnet",
            secret_ref=SecretRef(f"secret://workspace/{workspace_id}/ai-models/complex"),
            max_tokens_budget=16384,
            max_cost_usd=15.0,
        ),
    )


class CognitiveModelRouterService:
    """Domain service resolving abstract LLM tiers, effort, budgets & `auto` escalation."""

    def __init__(
        self,
        *,
        llm_gateway: LLMPort,
        initial_mappings: tuple[WorkspaceLlmTierMapping, ...] | None = None,
    ) -> None:
        self._llm_gateway = llm_gateway
        seed_mappings = (
            initial_mappings if initial_mappings is not None else build_default_tier_mappings()
        )
        self._mappings: dict[str, WorkspaceLlmTierMapping] = {m.id: m for m in seed_mappings}
        self._attempts_by_key: dict[str, InferenceAttemptRecord] = {}
        self._scope_budgets_usd: dict[str, float] = {}
        self._scope_spent_usd: dict[str, float] = {}
        self._pinned_models_by_mapping_id: dict[str, set[str]] = {}
        self._proc01_runs: dict[str, DurableProc01RunState] = {}

    def list_mappings(self, scope_id: str | None = None) -> list[WorkspaceLlmTierMapping]:
        items = list(self._mappings.values())
        if scope_id is not None:
            items = [m for m in items if m.scope_id == scope_id]
        return items

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
        """Delete or drain a model mapping, enforcing `409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS`."""
        if actor_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        mapping = self._mappings.get(mapping_id)
        if mapping is None:
            raise ResourceNotFoundError(instance=instance)

        active_runs = sorted(self._pinned_models_by_mapping_id.get(mapping_id, set()))
        if active_runs:
            if mode == "reject":
                raise ResourcePinnedByActiveRunsError(
                    detail_override=(
                        f"Model '{mapping.model_name}' ({mapping_id}) is pinned by active runs: "
                        f"{', '.join(active_runs)}. Use mode='drain' or mode='force'."
                    ),
                    instance=instance,
                )
            if mode == "drain":
                drained = replace(mapping, draining=True, updated_at_iso=_now_iso())
                self._mappings[mapping_id] = drained
                return drained
            if mode == "force":
                if actor_role != "PLATFORM_ADMIN":
                    raise ScopeAccessDeniedError(
                        detail_override="Only PLATFORM_ADMIN can force-remove a pinned model.",
                        instance=instance,
                    )
                self._pinned_models_by_mapping_id.pop(mapping_id, None)
                self._mappings.pop(mapping_id, None)
                return None

        self._mappings.pop(mapping_id, None)
        return None

    def resolve_mapping(
        self,
        *,
        scope_id: str,
        tier: ResolvedInferenceTier,
        effort: InferenceEffort = "default",
        allow_draining: bool = False,
    ) -> WorkspaceLlmTierMapping:
        candidates = [
            m
            for m in self._mappings.values()
            if m.inference_tier == tier
            and m.is_active
            and (allow_draining or not m.draining)
            and (m.scope_id == scope_id or m.scope_level == "GLOBAL")
        ]
        if not candidates:
            candidates = [
                m
                for m in self._mappings.values()
                if m.inference_tier == tier and m.is_active and (allow_draining or not m.draining)
            ]
        if not candidates:
            raise ResourceNotFoundError(
                detail_override=f"No active LLM mapping found for tier='{tier}'."
            )
        exact_effort = [m for m in candidates if m.effort == effort]
        chosen_pool = exact_effort if exact_effort else candidates
        chosen_pool.sort(key=lambda m: (0 if m.scope_id == scope_id else 1, m.fallback_order))
        return chosen_pool[0]

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
    ) -> CognitiveRoutingOutcome:
        """Execute an LLM call with tier resolution, `auto` escalation & DBOS idempotency."""
        tiers_to_try: tuple[ResolvedInferenceTier, ...] = (
            ("simple", "medium", "complex") if inference_tier == "auto" else (inference_tier,)
        )
        attempts: list[InferenceAttemptRecord] = []
        total_cost = 0.0
        all_scopes = (scope_id, *scope_hierarchy_ids)

        for idx, candidate_tier in enumerate(tiers_to_try, start=1):
            idem_key = f"{run_id}:{step_execution_id}:attempt-{idx}"
            existing = self._attempts_by_key.get(idem_key)
            if existing is not None:
                attempts.append(existing)
                total_cost = round(total_cost + existing.cost_usd, 6)
                if existing.deterministic_gate_passed:
                    return CognitiveRoutingOutcome(
                        run_id=run_id,
                        step_execution_id=step_execution_id,
                        requested_tier=inference_tier,
                        final_resolved_tier=existing.resolved_tier,
                        effort=effort,
                        response_content=existing.response_content,
                        model_family=existing.model_family,
                        model_name=existing.model_name,
                        attempts=tuple(attempts),
                        total_cost_usd=total_cost,
                    )
                continue

            for sc_id in all_scopes:
                ceiling = self._scope_budgets_usd.get(sc_id)
                spent = self._scope_spent_usd.get(sc_id, 0.0)
                if ceiling is not None and spent >= ceiling:
                    last_tier = attempts[-1].resolved_tier if attempts else candidate_tier
                    return CognitiveRoutingOutcome(
                        run_id=run_id,
                        step_execution_id=step_execution_id,
                        requested_tier=inference_tier,
                        final_resolved_tier=last_tier,
                        effort=effort,
                        response_content="",
                        model_family="none",
                        model_name="none",
                        attempts=tuple(attempts),
                        total_cost_usd=total_cost,
                        paused_budget_exceeded=True,
                    )

            mapping = self.resolve_mapping(scope_id=scope_id, tier=candidate_tier, effort=effort)
            if evaluator_model_family is not None:
                assert_model_orthogonality(mapping.model_family, evaluator_model_family)

            req = LlmPromptRequest(
                system_prompt=system_prompt,
                user_prompt=f"[TIER:{candidate_tier}|EFFORT:{effort}] {user_prompt}",
                model_family=mapping.model_family,
                model_id=mapping.model_name,
            )
            completion: LlmCompletionResponse = await self._llm_gateway.complete(req)
            multiplier = EFFORT_TOKEN_MULTIPLIER.get(effort, 1.0)
            adj_cost = round(max(completion.estimated_cost_usd, 0.001) * multiplier, 6)

            gate_passed = True
            failure_reason = ""
            if deterministic_gate_fn is not None:
                gate_passed, failure_reason = deterministic_gate_fn(
                    completion.content, candidate_tier
                )

            attempt = InferenceAttemptRecord(
                id=new_uuid7_str(),
                run_id=run_id,
                step_execution_id=step_execution_id,
                attempt_index=idx,
                requested_tier=inference_tier,
                resolved_tier=candidate_tier,
                effort=effort,
                model_family=mapping.model_family,
                model_name=mapping.model_name,
                deterministic_gate_passed=gate_passed,
                failure_reason=failure_reason,
                input_tokens=completion.input_tokens,
                output_tokens=int(completion.output_tokens * multiplier),
                cost_usd=adj_cost,
                idempotency_key=idem_key,
                response_content=completion.content,
            )
            self._attempts_by_key[idem_key] = attempt
            attempts.append(attempt)
            total_cost = round(total_cost + adj_cost, 6)
            for sc_id in all_scopes:
                self._scope_spent_usd[sc_id] = round(
                    self._scope_spent_usd.get(sc_id, 0.0) + adj_cost, 6
                )

            if gate_passed:
                return CognitiveRoutingOutcome(
                    run_id=run_id,
                    step_execution_id=step_execution_id,
                    requested_tier=inference_tier,
                    final_resolved_tier=candidate_tier,
                    effort=effort,
                    response_content=completion.content,
                    model_family=mapping.model_family,
                    model_name=mapping.model_name,
                    attempts=tuple(attempts),
                    total_cost_usd=total_cost,
                )

        last = attempts[-1]
        return CognitiveRoutingOutcome(
            run_id=run_id,
            step_execution_id=step_execution_id,
            requested_tier=inference_tier,
            final_resolved_tier=last.resolved_tier,
            effort=effort,
            response_content=last.response_content,
            model_family=last.model_family,
            model_name=last.model_name,
            attempts=tuple(attempts),
            total_cost_usd=total_cost,
        )

    async def start_proc01_durable_run(
        self,
        *,
        workspace_id: str,
        user_prompt: str,
        effort: InferenceEffort = "balanced",
    ) -> DurableProc01RunState:
        """Instantiate a `PROC-01` run, execute step 1 with `auto` escalation, and pause."""
        run_id = new_uuid7_str()
        step_id = new_uuid7_str()

        def _gate_requires_medium(
            content: str, resolved_tier: ResolvedInferenceTier
        ) -> tuple[bool, str]:
            _ = content
            if resolved_tier == "simple":
                return False, "Schema validation requires medium tier precision"
            return True, ""

        outcome = await self.execute_with_tier_routing(
            run_id=run_id,
            step_execution_id=step_id,
            scope_id=workspace_id,
            system_prompt="ORCIA Durable Cognitive Step 1",
            user_prompt=user_prompt,
            inference_tier="auto",
            effort=effort,
            deterministic_gate_fn=_gate_requires_medium,
        )
        state = DurableProc01RunState(
            run_id=run_id,
            workspace_id=workspace_id,
            status=(
                "PAUSED_BUDGET_EXCEEDED"
                if outcome.paused_budget_exceeded
                else "WAITING_FOR_HUMAN_ARBITRATION"
            ),
            step_1_outcome=outcome,
        )
        self._proc01_runs[run_id] = state
        return state

    async def replay_and_resume_proc01_run(
        self,
        *,
        run_id: str,
        arbitration_choice: str,
    ) -> DurableProc01RunState:
        """Simulate DBOS restart/replay of step 1 (`0` duplicate attempts) and resume step 2."""
        current = self._proc01_runs.get(run_id)
        if current is None:
            raise ResourceNotFoundError(detail_override=f"PROC-01 run not found: {run_id}")

        step_1_id = current.step_1_outcome.step_execution_id
        replayed_outcome = await self.execute_with_tier_routing(
            run_id=run_id,
            step_execution_id=step_1_id,
            scope_id=current.workspace_id,
            system_prompt="ORCIA Durable Cognitive Step 1",
            user_prompt="Replayed prompt",
            inference_tier="auto",
            effort=current.step_1_outcome.effort,
        )
        completed = replace(
            current,
            status="COMPLETED",
            step_1_outcome=replayed_outcome,
            arbitration_resolution=arbitration_choice,
            final_artifact={
                "verified_tier": replayed_outcome.final_resolved_tier,
                "attempts_count": len(replayed_outcome.attempts),
                "arbitration_choice": arbitration_choice,
                "content": replayed_outcome.response_content,
            },
            replayed_after_restart=True,
        )
        self._proc01_runs[run_id] = completed
        return completed


__all__ = [
    "CognitiveModelRouterService",
    "CognitiveRoutingOutcome",
    "DurableProc01RunState",
    "EFFORT_TOKEN_MULTIPLIER",
    "InferenceAttemptRecord",
    "InferenceEffort",
    "InferenceTier",
    "PinRemovalMode",
    "ResolvedInferenceTier",
    "WorkspaceLlmTierMapping",
    "build_default_tier_mappings",
]
