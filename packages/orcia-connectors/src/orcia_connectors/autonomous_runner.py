"""Autonomous Contract Workflow Execution Runner (`Story 7.1`, `AD-18`).

Enforces:
- Active non-revoked `AutonomyContract` check at every step boundary (`AD-21.5`).
- `HIGH_CRITICAL` workflows rejected (`422 ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE`).
- Deterministic gates (`PASS`, including `validate_help_article` for `generate-and-attach-help`)
  AND agentic gates (`agentic_score >= 0.85`, `fact_verification >= 0.90`,
  `ontology_conflicts == 0`, `stale_warnings == 0`).
- Scoped `SignedApprovalToken.issue_autonomous(...)` + `ConnectorInvoker` + `SecretProviderPort`.
- Outcome `COMMITTED_AUTONOMOUS` vs `PAUSED_AUTONOMOUS_ESCALATION` with `AutonomousEscalated`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from orcia_connectors._autonomous_runner_models import (
    AutonomousActionRequest,
    AutonomousGateInput,
    AutonomousRunOutcome,
    AutonomousRunStatus,
)
from orcia_connectors._autonomous_runner_models import (
    escalate_outcome as _escalate_outcome,
)
from orcia_connectors._autonomous_runner_models import (
    evaluate_gate_thresholds as _evaluate_gate_thresholds,
)
from orcia_connectors._connectors_locales import BOUNDED_WORKFLOW_LOCALES
from orcia_connectors.protocol import (
    OrciaConnectorProtocol,
    SignedApprovalToken,
    compute_payload_sha256,
    verify_signed_approval_token,
)
from orcia_core.kernel.enums import DEFAULT_LOCALE
from orcia_core.kernel.errors import CriticalWorkflowRequiresHumanGateError, PolicyDeniedError
from orcia_core.kernel.events import DomainEvent, RunTerminated
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.kernel.secret_ports import SecretProviderPort, SecretRef
from orcia_core.observability.logging import get_logger, scrub_sensitive_dict
from orcia_core.permissions.autonomy_contracts import AutonomyContract
from orcia_core.permissions.connector_invoker import ConnectorInvoker
from orcia_core.workflows.schemas_v2 import StepControlsPipeline

logger = get_logger("orcia.connectors.autonomous_runner")
_DEFAULT_AUTONOMOUS_ARTIFACT_TEXT = BOUNDED_WORKFLOW_LOCALES[DEFAULT_LOCALE][
    "autonomous_default_artifact"
]


async def execute_autonomous_contract_run(
    *,
    contract: AutonomyContract,
    criticality: str,
    actions: list[AutonomousActionRequest],
    gates: AutonomousGateInput | None = None,
    run_id: str | None = None,
    controls_pipeline: StepControlsPipeline | None = None,
    artifact_text: str = _DEFAULT_AUTONOMOUS_ARTIFACT_TEXT,
    contract_refresh_fn: Callable[[], Awaitable[AutonomyContract | None]] | None = None,
    kill_switch_check_fn: Callable[[str], Awaitable[bool]] | None = None,
    connector_invoker: ConnectorInvoker | None = None,
    connectors_by_scheme: dict[str, OrciaConnectorProtocol] | None = None,
    secret_provider: SecretProviderPort | None = None,
    trace_id: str = "00000000000000000000000000000000",
    scope_path: str = "GLOBAL",
) -> tuple[AutonomousRunOutcome, list[DomainEvent]]:
    """Execute a workflow run under `AUTONOMOUS_CONTRACT` with step-boundary revocation checks."""
    if criticality.strip().upper() == "HIGH_CRITICAL":
        raise CriticalWorkflowRequiresHumanGateError()

    resolved_run_id = run_id or new_uuid7_str()
    gate_input = gates or AutonomousGateInput()

    # Step boundary 1: verify active non-revoked contract & emergency stop guard (`AD-21.5`)
    if kill_switch_check_fn is not None and await kill_switch_check_fn(resolved_run_id):
        return (
            AutonomousRunOutcome(
                run_id=resolved_run_id,
                workspace_id=contract.workspace_id,
                workflow_id=contract.workflow_id,
                contract_id=contract.id,
                status="KILL_SWITCH_STOPPED",
                escalation_reason="KILL_SWITCH_STOPPED",
            ),
            [],
        )
    current_contract = await contract_refresh_fn() if contract_refresh_fn else contract
    if current_contract is None or current_contract.status != "ACTIVE":
        outcome, esc_event = _escalate_outcome(
            run_id=resolved_run_id,
            contract=contract,
            reason="CONTRACT_REVOKED",
            trace_id=trace_id,
            scope_path=scope_path,
        )
        return outcome, [esc_event]

    # Step boundary 2: deterministic & agentic gate thresholds
    gate_failure = _evaluate_gate_thresholds(
        workflow_id=current_contract.workflow_id,
        contract=current_contract,
        gates=gate_input,
        controls_pipeline=controls_pipeline,
        artifact_text=artifact_text,
    )
    if gate_failure is not None:
        outcome, esc_event = _escalate_outcome(
            run_id=resolved_run_id,
            contract=current_contract,
            reason=gate_failure,
            trace_id=trace_id,
            scope_path=scope_path,
        )
        return outcome, [esc_event]

    # Step boundary 3: validate actions are strictly scoped to contract.allowed_write_actions
    allowed_set = set(current_contract.allowed_write_actions)
    for req in actions:
        if req.action_key not in allowed_set:
            outcome, esc_event = _escalate_outcome(
                run_id=resolved_run_id,
                contract=current_contract,
                reason=f"ACTION_OUTSIDE_CONTRACT_SCOPE:{req.action_key}",
                trace_id=trace_id,
                scope_path=scope_path,
            )
            return outcome, [esc_event]

    issued_tokens: list[SignedApprovalToken] = []
    executed_actions: list[dict[str, Any]] = []
    invoker = connector_invoker or ConnectorInvoker()

    for idx, req in enumerate(actions):
        # Re-check emergency stop & revocation at each step boundary (AD-21.5)
        if kill_switch_check_fn is not None and await kill_switch_check_fn(resolved_run_id):
            return (
                AutonomousRunOutcome(
                    run_id=resolved_run_id,
                    workspace_id=current_contract.workspace_id,
                    workflow_id=current_contract.workflow_id,
                    contract_id=current_contract.id,
                    status="KILL_SWITCH_STOPPED",
                    escalation_reason="KILL_SWITCH_STOPPED",
                    issued_tokens=issued_tokens,
                    executed_actions=executed_actions,
                ),
                [],
            )
        if contract_refresh_fn is not None:
            latest = await contract_refresh_fn()
            if latest is None or latest.status != "ACTIVE":
                outcome, esc_event = _escalate_outcome(
                    run_id=resolved_run_id,
                    contract=current_contract,
                    reason="CONTRACT_REVOKED_MID_RUN",
                    trace_id=trace_id,
                    scope_path=scope_path,
                )
                return outcome, [esc_event]

        clean_payload = scrub_sensitive_dict(dict(req.payload))
        # Resolve SecretRef in memory only at execution point (never persisted in tokens/audit)
        if req.secret_ref_uri and secret_provider is not None:
            _resolved = secret_provider.resolve_secret(
                SecretRef(uri=req.secret_ref_uri, workspace_id=current_contract.workspace_id)
            )
            del _resolved

        if kill_switch_check_fn is not None and await kill_switch_check_fn(resolved_run_id):
            return (
                AutonomousRunOutcome(
                    run_id=resolved_run_id,
                    workspace_id=current_contract.workspace_id,
                    workflow_id=current_contract.workflow_id,
                    contract_id=current_contract.id,
                    status="KILL_SWITCH_STOPPED",
                    escalation_reason="KILL_SWITCH_STOPPED",
                    issued_tokens=issued_tokens,
                    executed_actions=executed_actions,
                ),
                [],
            )
        payload_sha = compute_payload_sha256(req.action_key, clean_payload)
        token = SignedApprovalToken.issue_autonomous(
            contract_id=current_contract.id,
            service_principal_id=current_contract.service_principal_id,
            action_key=req.action_key,
            payload_sha256=payload_sha,
            run_id=resolved_run_id,
        )
        verify_signed_approval_token(token, action=req.action_key, payload=clean_payload)
        issued_tokens.append(token)

        if kill_switch_check_fn is not None and await kill_switch_check_fn(resolved_run_id):
            return (
                AutonomousRunOutcome(
                    run_id=resolved_run_id,
                    workspace_id=current_contract.workspace_id,
                    workflow_id=current_contract.workflow_id,
                    contract_id=current_contract.id,
                    status="KILL_SWITCH_STOPPED",
                    escalation_reason="KILL_SWITCH_STOPPED",
                    issued_tokens=issued_tokens,
                    executed_actions=executed_actions,
                ),
                [],
            )
        adapter = (connectors_by_scheme or {}).get(req.scheme.strip().lower())
        if adapter is not None:
            result = await adapter.execute_write(token, req.action_key, clean_payload)
            executed_actions.append(
                {
                    "action_key": req.action_key,
                    "scheme": req.scheme,
                    "idempotency_key": f"{resolved_run_id}:{req.action_key}:{idx}",
                    "result": scrub_sensitive_dict(result),
                }
            )
        else:
            try:
                outcome_inv = await invoker.invoke_async(
                    scheme=req.scheme,
                    action=req.action_key,
                    payload=clean_payload,
                    idempotency_key=f"{resolved_run_id}:{req.action_key}:{idx}",
                    max_cost_usd=current_contract.max_cost_per_run_usd,
                )
                executed_actions.append(
                    {
                        "action_key": req.action_key,
                        "scheme": req.scheme,
                        "idempotency_key": outcome_inv.idempotency_key,
                        "result": scrub_sensitive_dict(outcome_inv.sanitized_output),
                    }
                )
            except PolicyDeniedError:
                outcome, esc_event = _escalate_outcome(
                    run_id=resolved_run_id,
                    contract=current_contract,
                    reason=f"POLICY_DENIED:{req.action_key}",
                    trace_id=trace_id,
                    scope_path=scope_path,
                )
                return outcome, [esc_event]
            except Exception as exc:
                logger.warning(
                    "autonomous_connector_invocation_failed",
                    action_key=req.action_key,
                    scheme=req.scheme,
                    error_type=type(exc).__name__,
                )
                outcome, esc_event = _escalate_outcome(
                    run_id=resolved_run_id,
                    contract=current_contract,
                    reason=f"CONNECTOR_EXECUTION_FAILED:{type(exc).__name__}",
                    trace_id=trace_id,
                    scope_path=scope_path,
                )
                return outcome, [esc_event]

    terminated_event = RunTerminated.create(
        run_id=resolved_run_id,
        workspace_id=current_contract.workspace_id,
        final_status="COMMITTED_AUTONOMOUS",
        total_cost_usd=gate_input.estimated_cost_usd,
        trace_id=trace_id,
    )
    return (
        AutonomousRunOutcome(
            run_id=resolved_run_id,
            workspace_id=current_contract.workspace_id,
            workflow_id=current_contract.workflow_id,
            contract_id=current_contract.id,
            status="COMMITTED_AUTONOMOUS",
            issued_tokens=issued_tokens,
            executed_actions=executed_actions,
            outbox_events=[
                {"event_id": terminated_event.event_id, "event_type": terminated_event.event_type}
            ],
        ),
        [terminated_event],
    )


__all__ = [
    "AutonomousActionRequest",
    "AutonomousGateInput",
    "AutonomousRunOutcome",
    "AutonomousRunStatus",
    "execute_autonomous_contract_run",
]
