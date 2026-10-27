"""Pure domain models for Bounded Context 4: Workflow-as-Code, Templates & Recursive Run Lock.

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

from orcia_core.catalog.models import AdaptiveGatePolicy, RunLockSourceTriplet, ScalarValue
from orcia_core.permissions.models import ExecutionIdentityMode

WorkflowCriticality = Literal["LOW_NON_CRITICAL", "STANDARD", "HIGH_CRITICAL"]
WorkflowExecutionRegime = Literal[
    "INTERACTIVE_COACHING", "BACKGROUND_FAST_PATH", "AUTONOMOUS_CONTRACT"
]
TieBreakPolicy = Literal[
    "ONTOLOGY_AXIOM_FIRST", "DEFER_AND_CONTINUE_WITH_ASSUMPTION", "PAUSE_AND_ESCALATE"
]
WorkflowEngineeringMode = Literal["standard", "brownfield_bootstrap"]
WorkflowStepType = Literal["AGENT", "SKILL", "SUB_WORKFLOW", "POST_ACTION_VERIFICATION"]
WorkflowTriggerType = Literal["WEBHOOK", "LOG_SINK_ALERT", "CRON", "MANUAL_AUTONOMOUS"]
WorkflowTriggerStatus = Literal["ACTIVE", "PAUSED", "CIRCUIT_OPEN"]
WorkflowRunStatus = Literal[
    "INITIALIZED",
    "RUNNING",
    "WAITING_FOR_HUMAN_ARBITRATION",
    "WAITING_FOR_HUMAN_GATE",
    "PAUSED_CIRCUIT_BREAKER",
    "PAUSED_BUDGET_EXCEEDED",
    "COMPLETED",
    "FAILED",
    "ROLLED_BACK",
]

MAX_SUB_WORKFLOW_NESTING_DEPTH = 3


@dataclass(frozen=True, slots=True)
class WorkflowValidationFinding:
    """Line-accurate validation error or warning inside a Workflow-as-Code YAML/JSON manifest."""

    line: int
    rule_code: str
    field_path: str
    message: str


@dataclass(frozen=True, slots=True)
class WorkflowStepSpec:
    """Typed step node inside a validated Workflow-as-Code DAG (`FR-11`, `FR-13`, `FR-30`)."""

    step_key: str
    title: str
    step_type: WorkflowStepType
    instructions: str
    depends_on: tuple[str, ...] = ()
    feedback_target_step_key: str | None = None
    max_agent_retries: int = 3
    agent_uri: str | None = None
    skill_uri: str | None = None
    sub_workflow_uri: str | None = None
    input_mapping: dict[str, str] = field(default_factory=dict)
    output_mapping: dict[str, str] = field(default_factory=dict)
    template_key: str | None = None
    kb_uris: tuple[str, ...] = ()
    human_authored_required: bool = False
    requires_human_gate: bool = False
    declares_intention: bool = False
    writes_code: bool = False
    reverse_doc_from_code: bool = False
    verification_window_seconds: int | None = None
    line_number: int = 1


@dataclass(frozen=True, slots=True)
class WorkflowAsCodeDefinition:
    """Validated declarative Workflow-as-Code DAG supporting `SUB_WORKFLOW <= 3` (`AD-18`)."""

    id: str
    workspace_id: str | None
    uri: str
    title: str
    description: str
    version: str
    criticality: WorkflowCriticality
    execution_regime: WorkflowExecutionRegime
    tie_break_policy: TieBreakPolicy
    mode: WorkflowEngineeringMode
    adaptive_gate_policy: AdaptiveGatePolicy
    max_cost_usd: float
    scalars: dict[str, ScalarValue]
    datasources: tuple[str, ...]
    rules: tuple[str, ...]
    facts: tuple[str, ...]
    steps: tuple[WorkflowStepSpec, ...]
    sha256: str
    max_nesting_depth: int = 0


@dataclass(frozen=True, slots=True)
class WorkflowValidationReport:
    """Result of validating a Workflow-as-Code YAML/JSON manifest."""

    valid: bool
    workflow: WorkflowAsCodeDefinition | None
    findings: tuple[WorkflowValidationFinding, ...]
    resolved_max_nesting_depth: int = 0
    topological_order: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ArtifactTemplateSectionSpec:
    """Section definition inside a Multi-Audience Artifact Template (`FR-12`, `FR-6`)."""

    section_key: str
    title: str
    markdown_body_template: str
    ontology_concept_term: str | None = None
    human_authored_required: bool = False
    mandatory: bool = True
    max_words_chunk: int = 600


@dataclass(frozen=True, slots=True)
class ArtifactTemplateDefinition:
    """Declarative Multi-Audience Artifact Template definition (`FR-12`)."""

    template_key: str
    uri: str
    title: str
    version: str
    description: str
    required_variables: tuple[str, ...]
    sections: tuple[ArtifactTemplateSectionSpec, ...]


@dataclass(frozen=True, slots=True)
class CompiledMarkdownChunk:
    """Cognitive chunk (`<= 800 words`) produced for human review in the Canvas (`FR-6`)."""

    chunk_index: int
    section_key: str
    section_title: str
    markdown_content: str
    word_count: int
    human_authored_required: bool


@dataclass(frozen=True, slots=True)
class CompiledArtifactTemplate:
    """Dual-compiled Multi-Audience Artifact Template (`FR-12`: Human Markdown + Agent Schema)."""

    template_key: str
    uri: str
    version: str
    human_markdown_view: str
    cognitive_chunks: tuple[CompiledMarkdownChunk, ...]
    agent_json_schema: dict[str, Any]
    bound_ontology_terms: tuple[str, ...]
    sha256: str


@dataclass(frozen=True, slots=True)
class SubWorkflowLockEntry:
    """Recursive lock node for a `SUB_WORKFLOW` step inside `run-lock.json` (`FR-30`, `AD-18`)."""

    step_key: str
    workflow_uri: str
    workflow_version: str
    workflow_sha256: str
    effective_workflow_sha256: str
    nesting_depth: int
    applied_override_keys: tuple[str, ...]
    sources: tuple[RunLockSourceTriplet, ...]
    sub_workflow_locks: tuple[SubWorkflowLockEntry, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize recursive sub-workflow lock entry."""
        return {
            "step_key": self.step_key,
            "workflow_uri": self.workflow_uri,
            "workflow_version": self.workflow_version,
            "workflow_sha256": self.workflow_sha256,
            "effective_workflow_sha256": self.effective_workflow_sha256,
            "nesting_depth": self.nesting_depth,
            "applied_override_keys": list(self.applied_override_keys),
            "sources": [
                {
                    "alias": s.alias,
                    "scheme": s.scheme,
                    "uri": s.uri,
                    "resolved_version": s.resolved_version,
                    "sha256": s.sha256,
                    "cas_key": s.cas_key,
                }
                for s in self.sources
            ],
            "sub_workflow_locks": [child.to_dict() for child in self.sub_workflow_locks],
        }


@dataclass(frozen=True, slots=True)
class RecursiveRunLockManifest:
    """Extended `run-lock.json` pinning sources, 4-layer overrides, KB hash & sub-workflows."""

    run_id: str
    workspace_id: str
    workflow_uri: str
    workflow_version: str
    workflow_sha256: str
    effective_workflow_sha256: str
    overrides_sha256: str
    kb_snapshot_hash: str
    applied_override_keys: tuple[str, ...]
    sources: tuple[RunLockSourceTriplet, ...]
    sub_workflow_locks: tuple[SubWorkflowLockEntry, ...]
    manifest_sha256: str

    def to_dict(self) -> dict[str, Any]:
        """Return canonical dictionary representation of recursive `run-lock.json`."""
        return {
            "run_id": self.run_id,
            "workspace_id": self.workspace_id,
            "workflow_uri": self.workflow_uri,
            "workflow_version": self.workflow_version,
            "workflow_sha256": self.workflow_sha256,
            "effective_workflow_sha256": self.effective_workflow_sha256,
            "overrides_sha256": self.overrides_sha256,
            "kb_snapshot_hash": self.kb_snapshot_hash,
            "applied_override_keys": list(self.applied_override_keys),
            "sources": [
                {
                    "alias": s.alias,
                    "scheme": s.scheme,
                    "uri": s.uri,
                    "resolved_version": s.resolved_version,
                    "sha256": s.sha256,
                    "cas_key": s.cas_key,
                }
                for s in self.sources
            ],
            "sub_workflow_locks": [sub.to_dict() for sub in self.sub_workflow_locks],
            "manifest_sha256": self.manifest_sha256,
        }

    def to_json(self) -> str:
        """Serialize recursive `run-lock.json` deterministically."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)


@dataclass(frozen=True, slots=True)
class WorkflowTriggerEntity:
    """Governed autonomous workflow trigger (`WEBHOOK`, `LOG_SINK_ALERT`, `CRON`, `AD-18`)."""

    id: str
    trigger_key: str
    workspace_id: str
    workflow_def_id: str
    trigger_type: WorkflowTriggerType
    cron_expr: str | None = None
    webhook_secret_vault_ref: str | None = None
    cooldown_window_seconds: int = 300
    service_principal_id: str | None = None
    max_runs_per_hour: int = 10
    max_daily_cost_usd: float = 25.0
    max_consecutive_failures: int = 3
    post_hoc_sampling_rate: float = 0.10
    contract_signature_id: str | None = None
    status: WorkflowTriggerStatus = "ACTIVE"


@dataclass(frozen=True, slots=True)
class WorkflowRunEntity:
    """Instantiated Workflow Run or nested Sub-Workflow Run (`nesting_depth <= 3`, `AD-18`)."""

    id: str
    run_key: str
    workspace_id: str
    workflow_def_id: str
    workflow_uri: str
    parent_run_id: str | None
    parent_step_execution_id: str | None
    root_run_id: str
    nesting_depth: int
    execution_regime: WorkflowExecutionRegime
    criticality: WorkflowCriticality
    trigger_id: str | None
    trigger_idempotency_key: str | None
    status: WorkflowRunStatus
    initiated_by_user_id: str | None
    execution_identity_mode: ExecutionIdentityMode
    budget_max_usd: float
    run_lock: RecursiveRunLockManifest
