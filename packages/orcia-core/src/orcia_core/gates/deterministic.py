"""Deterministic Gate Service & Pattern Drift Detector (`FR-17`, `AD-9`, `AD-19`, `Story 4.1`)."""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
from datetime import UTC, datetime
from typing import Any

from orcia_core.gates.errors import PatternDriftDetectedError
from orcia_core.gates.models import (
    CANONICAL_FORBIDDEN_DRIFT_PATTERNS,
    CANONICAL_SPINE_ALLOWED_DEPENDENCIES,
    DeterministicGateInput,
    GateEvaluationEntity,
    GateStatus,
    PatternDriftFinding,
    WorkspaceSpineBaseline,
)
from orcia_core.gates.sandbox import SubprocessTier1SandboxAdapter, classify_sandbox_failure
from orcia_kernel.events import GateEvaluated
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import (
    OutboxRelayPort,
    SandboxExecutionRequest,
    SandboxExecutionResult,
    SandboxPort,
)


def _run_sandbox_sync(
    sandbox_port: SandboxPort, request: SandboxExecutionRequest
) -> SandboxExecutionResult:
    """Invoke `sandbox_port.execute(request)` safely from sync or async contexts."""
    if isinstance(sandbox_port, SubprocessTier1SandboxAdapter):
        return sandbox_port.execute_sync(request)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(sandbox_port.execute(request))
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(sandbox_port.execute(request))).result()


class DeterministicGateService:
    """Evaluates Deterministic Gates in the out-of-process Tier 1 Sandbox (`AD-9`, `FR-17`)."""

    def __init__(
        self,
        *,
        sandbox_port: SandboxPort | None = None,
        outbox_relay: OutboxRelayPort | None = None,
    ) -> None:
        self.sandbox_port: SandboxPort = sandbox_port or SubprocessTier1SandboxAdapter()
        self._outbox_relay = outbox_relay
        self._evaluations: dict[str, GateEvaluationEntity] = {}
        self._outbox_events: list[GateEvaluated] = []
        self._workspace_spines: dict[str, WorkspaceSpineBaseline] = {}

    def register_workspace_spine_baseline(self, baseline: WorkspaceSpineBaseline) -> None:
        """Register or update the `[ADOPTED]` `ARCHITECTURE-SPINE.md` baseline for a Workspace."""
        self._workspace_spines[baseline.workspace_id] = baseline

    def get_workspace_spine_baseline(self, workspace_id: str) -> WorkspaceSpineBaseline | None:
        """Return the registered `WorkspaceSpineBaseline` for `workspace_id`, if any."""
        return self._workspace_spines.get(workspace_id)

    def list_evaluations(self, *, run_id: str | None = None) -> list[GateEvaluationEntity]:
        """List recorded gate evaluations, optionally filtered by `run_id`."""
        items = list(self._evaluations.values())
        if run_id is not None:
            items = [e for e in items if e.run_id == run_id]
        return items

    def list_outbox_events(self) -> list[GateEvaluated]:
        """Return all `GateEvaluated` events published to the transactional Outbox."""
        return list(self._outbox_events)

    def evaluate_deterministic_gate(
        self,
        gate_input: DeterministicGateInput,
        *,
        raise_on_failure: bool = False,
    ) -> GateEvaluationEntity:
        """Execute schema, ontology axiom, and Pattern Drift checks in the Tier 1 Sandbox."""
        baseline = self._workspace_spines.get(gate_input.workspace_id)
        allowed_deps = (
            gate_input.allowed_dependencies
            if gate_input.allowed_dependencies is not None
            else (
                baseline.allowed_dependencies
                if baseline is not None
                else CANONICAL_SPINE_ALLOWED_DEPENDENCIES
            )
        )
        forbidden_rules = (
            gate_input.forbidden_patterns
            if gate_input.forbidden_patterns is not None
            else (
                baseline.forbidden_patterns
                if baseline is not None
                else CANONICAL_FORBIDDEN_DRIFT_PATTERNS
            )
        )

        sandbox_payload: dict[str, Any] = {
            "artifact": dict(gate_input.artifact_payload),
            "required_sections": list(gate_input.required_sections),
            "ontology_axioms": [
                {
                    "axiom_key": ax.axiom_key,
                    "forbidden_term": ax.forbidden_term,
                    "required_term": ax.required_term,
                }
                for ax in gate_input.ontology_axioms
            ],
            "allowed_dependencies": list(allowed_deps),
            "forbidden_patterns": [dict(r) for r in forbidden_rules],
            "simulate_timeout_sleep_ms": gate_input.simulate_timeout_sleep_ms,
            "simulate_network_escape": gate_input.simulate_network_escape,
            "simulate_fs_escape_path": gate_input.simulate_fs_escape_path,
            "simulate_tmp_overflow_mb": gate_input.simulate_tmp_overflow_mb,
            "simulate_memory_alloc_mb": gate_input.simulate_memory_alloc_mb,
        }

        req = SandboxExecutionRequest(
            tier="TIER_1_WASM",
            entrypoint="deterministic_gate",
            payload=sandbox_payload,
            timeout_ms=gate_input.timeout_ms,
            max_memory_mb=gate_input.max_memory_mb,
        )
        res = _run_sandbox_sync(self.sandbox_port, req)

        parsed_stdout: dict[str, Any] = {}
        if res.stdout.strip():
            try:
                parsed_stdout = json.loads(res.stdout)
            except Exception:
                parsed_stdout = {}

        if res.exit_code in (124, 126, 137) or (res.exit_code != 0 and not parsed_stdout):
            status: GateStatus = "ERROR"
            schema_ok = False
            axioms_ok = False
            drift_ok = False
            score = 0.0
            drift_findings: tuple[PatternDriftFinding, ...] = ()
            missing_sections: tuple[str, ...] = ()
            violated_axioms: tuple[dict[str, str], ...] = ()
        else:
            schema_ok = bool(parsed_stdout.get("schema_validation_passed", True))
            axioms_ok = bool(parsed_stdout.get("ontology_axioms_passed", True))
            drift_ok = bool(parsed_stdout.get("pattern_drift_passed", True))
            passed = bool(parsed_stdout.get("passed", False)) and res.exit_code == 0
            status = "PASS" if passed else "FAIL"
            score = float(parsed_stdout.get("score", 1.0 if passed else 0.0))
            drift_findings = tuple(
                PatternDriftFinding(
                    rule_id=str(item.get("rule_id", "DRIFT-RULE")),
                    forbidden_symbol=str(item.get("forbidden_symbol", "")),
                    severity=str(item.get("severity", "HIGH")),
                    message=str(item.get("message", "")),
                )
                for item in (parsed_stdout.get("pattern_drift_findings") or [])
            )
            missing_sections = tuple(
                str(s) for s in (parsed_stdout.get("missing_sections") or [])
            )
            violated_axioms = tuple(
                dict(ax) for ax in (parsed_stdout.get("violated_axioms") or [])
            )

        eval_id = new_uuid7_str()
        outbox_evt = GateEvaluated.create(
            gate_evaluation_id=eval_id,
            run_id=gate_input.run_id,
            workspace_id=gate_input.workspace_id,
            gate_type="DETERMINISTIC",
            passed=(status == "PASS"),
            score=score,
        )
        self._outbox_events.append(outbox_evt)
        if self._outbox_relay is not None:
            self._outbox_relay.enqueue_in_transaction(outbox_evt)

        entity = GateEvaluationEntity(
            id=eval_id,
            workspace_id=gate_input.workspace_id,
            run_id=gate_input.run_id,
            step_execution_id=gate_input.step_execution_id,
            step_key=gate_input.step_key,
            gate_type="DETERMINISTIC",
            sandbox_tier="TIER_1_WASM",
            status=status,
            score=score,
            schema_validation_passed=schema_ok,
            ontology_axioms_passed=axioms_ok,
            pattern_drift_passed=drift_ok,
            pattern_drift_findings=drift_findings,
            missing_sections=missing_sections,
            violated_axioms=violated_axioms,
            duration_ms=res.duration_ms,
            outbox_event_id=outbox_evt.event_id,
            evaluated_at=datetime.now(UTC).isoformat(),
            sandbox_exit_code=res.exit_code,
            sandbox_stderr=res.stderr.strip(),
        )
        self._evaluations[entity.id] = entity

        if raise_on_failure and status != "PASS":
            if res.exit_code in (124, 126, 137):
                raise classify_sandbox_failure(res)
            if not drift_ok and drift_findings:
                first_drift = drift_findings[0]
                raise PatternDriftDetectedError(
                    detail_override=(
                        f"[{first_drift.rule_id}] {first_drift.message} "
                        f"(symbol={first_drift.forbidden_symbol!r})"
                    )
                )
            raise classify_sandbox_failure(res)

        return entity
