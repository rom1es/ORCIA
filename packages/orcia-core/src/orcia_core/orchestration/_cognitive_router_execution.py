"""Core execution loop for cognitive tier routing and auto-escalation (`Story 8.2`, `Story 6.2`).

Extracted to enforce strict module size (< 300 lines) in cognitive_router.py.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from orcia_core.orchestration._cognitive_router_models import (
    EFFORT_TOKEN_MULTIPLIER,
    CognitiveRoutingOutcome,
    InferenceAttemptRecord,
    InferenceEffort,
    InferenceTier,
    ResolvedInferenceTier,
    make_paused_outcome,
)
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import (
    LlmCompletionResponse,
    LlmPromptRequest,
    assert_model_orthogonality,
)

if TYPE_CHECKING:
    from orcia_core.orchestration.cognitive_router import CognitiveModelRouterService


async def execute_tier_routing_loop(
    service: CognitiveModelRouterService,
    *,
    run_id: str,
    step_execution_id: str,
    scope_id: str,
    system_prompt: str,
    user_prompt: str,
    inference_tier: InferenceTier = "medium",
    effort: InferenceEffort = "default",
    evaluator_model_family: str | None = None,
    deterministic_gate_fn: Callable[[str, ResolvedInferenceTier], tuple[bool, str]] | None = None,
    scope_hierarchy_ids: tuple[str, ...] = (),
    max_agent_retries: int = 3,
    run_budget_ceiling_usd: float | None = None,
    run_spent_usd: float = 0.0,
) -> CognitiveRoutingOutcome:
    """Execute an LLM call with tier resolution, `auto` escalation & DBOS idempotency."""
    tiers_to_try: tuple[ResolvedInferenceTier, ...] = (
        ("simple", "medium", "complex") if inference_tier == "auto" else (inference_tier,)
    )
    attempts: list[InferenceAttemptRecord] = []
    total_cost = 0.0
    all_scopes = (scope_id, *scope_hierarchy_ids)

    for idx, candidate_tier in enumerate(tiers_to_try, start=1):
        retry_check = service.budget_guard.check_retries_ceiling(
            attempt_count=idx - 1,
            max_agent_retries=max_agent_retries,
            run_id=run_id,
            step_execution_id=step_execution_id,
            workspace_id=scope_id,
        )
        if not retry_check.allowed:
            last_t = attempts[-1].resolved_tier if attempts else candidate_tier
            return make_paused_outcome(
                run_id=run_id,
                step_execution_id=step_execution_id,
                requested_tier=inference_tier,
                resolved_tier=last_t,
                effort=effort,
                attempts=attempts,
                total_cost_usd=total_cost,
                paused_max_retries=True,
            )

        idem_key = f"{run_id}:{step_execution_id}:attempt-{idx}"
        existing = service.get_cached_attempt(idem_key)
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

        budget_res = await service.budget_guard.evaluate_allowance(
            run_id=run_id,
            step_execution_id=step_execution_id,
            workspace_id=scope_id,
            all_scopes=all_scopes,
            scope_budgets_usd=service.scope_budgets_usd,
            scope_spent_usd=service.scope_spent_usd,
            estimated_step_cost_usd=0.001,
            run_budget_ceiling_usd=run_budget_ceiling_usd,
            run_spent_usd=run_spent_usd + total_cost,
        )
        if not budget_res.allowed:
            last_tier = attempts[-1].resolved_tier if attempts else candidate_tier
            return make_paused_outcome(
                run_id=run_id,
                step_execution_id=step_execution_id,
                requested_tier=inference_tier,
                resolved_tier=last_tier,
                effort=effort,
                attempts=attempts,
                total_cost_usd=total_cost,
                paused_budget_exceeded=True,
            )

        mapping = service.resolve_mapping(scope_id=scope_id, tier=candidate_tier, effort=effort)
        if evaluator_model_family is not None:
            assert_model_orthogonality(mapping.model_family, evaluator_model_family)

        req = LlmPromptRequest(
            system_prompt=system_prompt,
            user_prompt=f"[TIER:{candidate_tier}|EFFORT:{effort}] {user_prompt}",
            model_family=mapping.model_family,
            model_id=mapping.model_name,
        )
        completion: LlmCompletionResponse = await service.llm_gateway.complete(req)
        multiplier = EFFORT_TOKEN_MULTIPLIER.get(effort, 1.0)
        adj_cost = round(max(completion.estimated_cost_usd, 0.001) * multiplier, 6)

        gate_passed = True
        failure_reason = ""
        if deterministic_gate_fn is not None:
            gate_passed, failure_reason = deterministic_gate_fn(completion.content, candidate_tier)

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
        service.record_attempt(idem_key, attempt)
        attempts.append(attempt)
        total_cost = round(total_cost + adj_cost, 6)
        service.add_scope_spent(all_scopes, adj_cost)

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


__all__ = ["execute_tier_routing_loop"]
