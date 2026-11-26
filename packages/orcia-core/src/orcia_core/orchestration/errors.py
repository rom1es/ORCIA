"""Orchestration domain errors (`AD-19`, `AD-20`, `Story 3.2a`, `Story 3.2e`)."""

from __future__ import annotations

from orcia_core.orchestration._error_catalog import ORCHESTRATION_ERROR_CATALOG
from orcia_core.orchestration._orchestration_extra_error_catalog import (
    ORCHESTRATION_EXTRA_ERROR_CATALOG,
)
from orcia_core.orchestration._orchestration_ops_error_catalog import (
    ORCHESTRATION_OPS_ERROR_CATALOG,
)
from orcia_core.orchestration._orchestration_runtime_error_catalog import (
    ORCHESTRATION_RUNTIME_ERROR_CATALOG,
)
from orcia_kernel.errors import (
    CriticalWorkflowRequiresHumanGateError,
    HumanAnchorRequiredError,
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
    register_domain_error_catalog,
)

register_domain_error_catalog(ORCHESTRATION_ERROR_CATALOG)
register_domain_error_catalog(ORCHESTRATION_EXTRA_ERROR_CATALOG)
register_domain_error_catalog(ORCHESTRATION_OPS_ERROR_CATALOG)
register_domain_error_catalog(ORCHESTRATION_RUNTIME_ERROR_CATALOG)


class IntentionBeforeCodeRequiredError(OrciaDomainError):
    error_code = "ERR_INTENTION_BEFORE_CODE_REQUIRED"
    http_status, type_slug = 422, "intention-before-code-required"


class UnknownWorkflowPolicyError(OrciaDomainError):
    error_code = "ERR_UNKNOWN_WORKFLOW_POLICY"
    http_status, type_slug = 422, "unknown-workflow-policy"


class SubWorkflowMaxDepthExceededError(OrciaDomainError):
    error_code = "ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED"
    http_status, type_slug = 422, "sub-workflow-max-depth-exceeded"


class SubWorkflowCycleDetectedError(OrciaDomainError):
    error_code = "ERR_SUB_WORKFLOW_CYCLE_DETECTED"
    http_status, type_slug = 422, "sub-workflow-cycle-detected"


class StepAlreadyClaimedByPeerError(OrciaDomainError):
    error_code = "ERR_STEP_ALREADY_CLAIMED_BY_PEER"
    http_status, type_slug = 409, "step-already-claimed-by-peer"


class StepClaimNotHeldError(OrciaDomainError):
    error_code = "ERR_STEP_CLAIM_NOT_HELD"
    http_status, type_slug = 403, "step-claim-not-held"


class StaleFencingTokenError(OrciaDomainError):
    error_code = "ERR_STALE_FENCING_TOKEN"
    http_status, type_slug = 409, "stale-fencing-token"


class ResourceLeaseHeldByOtherRunError(OrciaDomainError):
    error_code = "ERR_RESOURCE_LEASE_HELD_BY_OTHER_RUN"
    http_status, type_slug = 409, "resource-lease-held-by-other-run"


class CyclicResourceWaitDetectedError(OrciaDomainError):
    error_code = "ERR_CYCLIC_RESOURCE_WAIT_DETECTED"
    http_status, type_slug = 409, "cyclic-resource-wait-detected"


class ResourcePinnedByActiveRunsError(OrciaDomainError):
    error_code = "ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS"
    http_status, type_slug = 409, "resource-pinned-by-active-runs"


class ImmutableHarnessBoundaryError(OrciaDomainError):
    error_code = "ERR_IMMUTABLE_HARNESS_BOUNDARY"
    http_status, type_slug = 422, "immutable-harness-boundary"


class FunnelRuleViolationError(OrciaDomainError):
    error_code = "ERR_FUNNEL_RULE_VIOLATION"
    http_status, type_slug = 403, "funnel-rule-violation"


class DirectSiWriteRequiresProcessGateError(OrciaDomainError):
    error_code = "ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE"
    http_status, type_slug = 422, "direct-si-write-requires-process-gate"


class ThreadTurnLockHeldError(OrciaDomainError):
    error_code = "ERR_THREAD_TURN_LOCK_HELD"
    http_status, type_slug = 409, "thread-turn-lock-held"


class EnterpriseDirectiveWaiverForbiddenError(OrciaDomainError):
    error_code = "ERR_ENTERPRISE_DIRECTIVE_WAIVER_FORBIDDEN"
    http_status, type_slug = 403, "enterprise-directive-waiver-forbidden"


class PathTraversalDeniedError(OrciaDomainError):
    error_code = "ERR_PATH_TRAVERSAL_DENIED"
    http_status, type_slug = 403, "path-traversal-denied"


class OrthogonalJudgeSovereigntyViolationError(OrciaDomainError):
    error_code = "ERR_ORTHOGONAL_JUDGE_SOVEREIGNTY_VIOLATION"
    http_status, type_slug = 422, "orthogonal-judge-sovereignty-violation"


class AgentDraftLifecycleBlockedError(OrciaDomainError):
    """Raised when an operation targets a DRAFT or unready agent (`Story 30.5`, `UX30-15`)."""

    error_code = "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"
    http_status, type_slug = 422, "draft-agent-lifecycle-blocked"

    def __init__(
        self,
        *,
        detail_override: str | None = None,
        detail_code: str | None = None,
        detail_params: dict[str, str | int] | None = None,
        instance: str | None = None,
    ) -> None:
        super().__init__(
            detail_override=detail_override,
            detail_code=detail_code,
            detail_params=detail_params,
            instance=instance,
        )


class TierModelNotConfiguredError(OrciaDomainError):
    """Raised when an inference tier has no active configured AI model."""

    error_code = "ERR_TIER_MODEL_NOT_CONFIGURED"
    http_status, type_slug = 422, "tier-model-not-configured"

    def __init__(
        self,
        inference_tier: str = "",
        *,
        detail_override: str | None = None,
        detail_code: str | None = None,
        detail_params: dict[str, str | int] | None = None,
        instance: str | None = None,
    ) -> None:
        self.inference_tier = inference_tier
        resolved_code = detail_code or (
            "ERR_TIER_MODEL_NOT_CONFIGURED_WITH_TIER" if inference_tier else None
        )
        resolved_params = detail_params or (
            {"inference_tier": inference_tier} if inference_tier else None
        )
        super().__init__(
            detail_override=detail_override,
            detail_code=resolved_code,
            detail_params=resolved_params,
            instance=instance,
        )


__all__ = [
    "AgentDraftLifecycleBlockedError",
    "CriticalWorkflowRequiresHumanGateError",
    "CyclicResourceWaitDetectedError",
    "DirectSiWriteRequiresProcessGateError",
    "EnterpriseDirectiveWaiverForbiddenError",
    "FunnelRuleViolationError",
    "HumanAnchorRequiredError",
    "ImmutableHarnessBoundaryError",
    "IntentionBeforeCodeRequiredError",
    "ORCHESTRATION_ERROR_CATALOG",
    "ORCHESTRATION_EXTRA_ERROR_CATALOG",
    "ObserverModeReadOnlyError",
    "OrciaDomainError",
    "OrthogonalJudgeSovereigntyViolationError",
    "PathTraversalDeniedError",
    "ResourceLeaseHeldByOtherRunError",
    "ResourceNotFoundError",
    "ResourcePinnedByActiveRunsError",
    "ScopeAccessDeniedError",
    "StaleFencingTokenError",
    "StepAlreadyClaimedByPeerError",
    "StepClaimNotHeldError",
    "SubWorkflowCycleDetectedError",
    "SubWorkflowMaxDepthExceededError",
    "ThreadTurnLockHeldError",
    "TierModelNotConfiguredError",
    "UnknownWorkflowPolicyError",
    "ValidationDomainError",
]
