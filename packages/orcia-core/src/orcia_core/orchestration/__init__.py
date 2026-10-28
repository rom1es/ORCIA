"""Bounded Context 4: Durable Workflow Orchestration, Workflow-as-Code & Recursive Run Lock."""

from __future__ import annotations

from typing import Any

from orcia_core.orchestration import seeds as _seeds
from orcia_core.orchestration.connector_invoker import (
    CircuitBreakerState,
    ConnectorCircuitBreaker,
    ConnectorInvocationOutcome,
    ConnectorInvoker,
    scrub_connector_secrets,
)
from orcia_core.orchestration.engine import (
    DurableOrchestrationEngine,
    JitStepHydrator,
    MemlogMarkerPluginProtocol,
    register_memlog_marker_plugin,
)
from orcia_core.orchestration.models import (
    MAX_SUB_WORKFLOW_NESTING_DEPTH,
    ArtifactTemplateDefinition,
    ArtifactTemplateSectionSpec,
    CompiledArtifactTemplate,
    CompiledMarkdownChunk,
    RecursiveRunLockManifest,
    SubWorkflowLockEntry,
    TieBreakPolicy,
    WorkflowAsCodeDefinition,
    WorkflowCriticality,
    WorkflowEngineeringMode,
    WorkflowExecutionRegime,
    WorkflowRunEntity,
    WorkflowRunStatus,
    WorkflowStepSpec,
    WorkflowStepType,
    WorkflowTriggerEntity,
    WorkflowTriggerStatus,
    WorkflowTriggerType,
    WorkflowValidationFinding,
    WorkflowValidationReport,
)
from orcia_core.orchestration.run_lock_service import WorkflowOrchestrationSetupService
from orcia_core.orchestration.seeds import build_default_orchestration_setup_service
from orcia_core.orchestration.step_executors import (
    AgentStepExecutor,
    HttpActionStepExecutor,
    HumanTaskStepExecutor,
    PostActionVerificationStepExecutor,
    SkillStepExecutor,
    SubWorkflowStepExecutor,
    register_default_step_executors,
)
from orcia_core.orchestration.template_compiler import MultiAudienceTemplateCompiler
from orcia_core.orchestration.yaml_loader import (
    WorkflowPolicyPluginProtocol,
    register_workflow_policy_plugin,
)
from orcia_core.orchestration.yaml_validator import WorkflowAsCodeValidator

DOMAIN_NAME: str = "orchestration"


def __getattr__(name: str) -> Any:
    if name in (
        "DEFAULT_ADR_TEMPLATE_SEED",
        "DEFAULT_CHILD_SUB_WORKFLOW_YAML",
        "DEFAULT_LEAF_SUB_WORKFLOW_YAML",
        "DEFAULT_ROOT_WORKFLOW_YAML",
    ):
        return getattr(_seeds, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AgentStepExecutor",
    "ArtifactTemplateDefinition",
    "ArtifactTemplateSectionSpec",
    "CircuitBreakerState",
    "CompiledArtifactTemplate",
    "CompiledMarkdownChunk",
    "ConnectorCircuitBreaker",
    "ConnectorInvocationOutcome",
    "ConnectorInvoker",
    "DEFAULT_CHILD_SUB_WORKFLOW_YAML",
    "DEFAULT_LEAF_SUB_WORKFLOW_YAML",
    "DEFAULT_ROOT_WORKFLOW_YAML",
    "DOMAIN_NAME",
    "DurableOrchestrationEngine",
    "HttpActionStepExecutor",
    "HumanTaskStepExecutor",
    "JitStepHydrator",
    "MAX_SUB_WORKFLOW_NESTING_DEPTH",
    "MemlogMarkerPluginProtocol",
    "MultiAudienceTemplateCompiler",
    "PostActionVerificationStepExecutor",
    "RecursiveRunLockManifest",
    "SkillStepExecutor",
    "SubWorkflowLockEntry",
    "SubWorkflowStepExecutor",
    "TieBreakPolicy",
    "WorkflowAsCodeDefinition",
    "WorkflowAsCodeValidator",
    "WorkflowCriticality",
    "WorkflowEngineeringMode",
    "WorkflowExecutionRegime",
    "WorkflowOrchestrationSetupService",
    "WorkflowPolicyPluginProtocol",
    "WorkflowRunEntity",
    "WorkflowRunStatus",
    "WorkflowStepSpec",
    "WorkflowStepType",
    "WorkflowTriggerEntity",
    "WorkflowTriggerStatus",
    "WorkflowTriggerType",
    "WorkflowValidationFinding",
    "WorkflowValidationReport",
    "build_default_orchestration_setup_service",
    "register_default_step_executors",
    "register_memlog_marker_plugin",
    "register_workflow_policy_plugin",
    "scrub_connector_secrets",
]
