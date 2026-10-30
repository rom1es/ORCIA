"""Bounded Context 6: Gates (Deterministic Sandbox, Orthogonal Lens DAG & Adaptive Human Gates)."""

from __future__ import annotations

from orcia_core.gates.deterministic import DeterministicGateService
from orcia_core.gates.errors import (
    DeterministicGateFailedError,
    FunctionalConnectorError,
    ModelOrthogonalityViolationError,
    OrciaDomainError,
    PatternDriftDetectedError,
    PolicyDeniedError,
    UpstreamTimeoutError,
    ValidationDomainError,
)
from orcia_core.gates.models import (
    CANONICAL_FORBIDDEN_DRIFT_PATTERNS,
    CANONICAL_SPINE_ALLOWED_DEPENDENCIES,
    DeterministicGateInput,
    GateEvaluationEntity,
    GateStatus,
    GateType,
    OntologyAxiomCheckRule,
    PatternDriftFinding,
    SandboxTierLiteral,
    WorkspaceSpineBaseline,
)
from orcia_core.gates.sandbox import (
    SubprocessTier1SandboxAdapter,
    classify_sandbox_failure,
)
from orcia_core.gates.tier2_sandbox import (
    BimodalSandboxAdapter,
    ContainerRuntimeType,
    ContainerSandboxRunner,
    ContainerSandboxSpec,
    TddRemediationCheckInput,
    TddRemediationCheckResult,
    build_tier2_container_cli_args,
)

DOMAIN_NAME: str = "gates"

__all__ = [
    "CANONICAL_FORBIDDEN_DRIFT_PATTERNS",
    "CANONICAL_SPINE_ALLOWED_DEPENDENCIES",
    "DOMAIN_NAME",
    "BimodalSandboxAdapter",
    "ContainerRuntimeType",
    "ContainerSandboxRunner",
    "ContainerSandboxSpec",
    "DeterministicGateFailedError",
    "DeterministicGateInput",
    "DeterministicGateService",
    "FunctionalConnectorError",
    "GateEvaluationEntity",
    "GateStatus",
    "GateType",
    "ModelOrthogonalityViolationError",
    "OntologyAxiomCheckRule",
    "OrciaDomainError",
    "PatternDriftDetectedError",
    "PatternDriftFinding",
    "PolicyDeniedError",
    "SandboxTierLiteral",
    "SubprocessTier1SandboxAdapter",
    "TddRemediationCheckInput",
    "TddRemediationCheckResult",
    "UpstreamTimeoutError",
    "ValidationDomainError",
    "WorkspaceSpineBaseline",
    "build_tier2_container_cli_args",
    "classify_sandbox_failure",
]
