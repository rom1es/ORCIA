"""Hexagonal Kernel Ports (`AD-1`, `AD-5`, `AD-9`, `AD-10`, `AD-12`, `AD-19`, `AD-20`, `C3`).

Defines pure Protocol interfaces (`BlackboardPort`, `OutboxRelayPort`, `LLMPort`,
`ObjectStoragePort`, `SandboxPort`, `ConnectorPort`, `ClockPort`) and connector registry
with zero framework or SDK dependencies.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol, runtime_checkable

from orcia_kernel.enums import SandboxExecutionTier
from orcia_kernel.errors import ModelOrthogonalityViolationError, OrciaDomainError
from orcia_kernel.events import DomainEvent

ExecutionMode = Literal["COACHING", "FAST_PATH"]
ConnectorHealthState = Literal["HEALTHY", "DEGRADED", "UNREACHABLE"]


@dataclass(frozen=True, slots=True)
class LlmPromptRequest:
    """Immutable LLM prompt request crossing the hexagonal boundary."""

    system_prompt: str
    user_prompt: str
    model_family: str
    model_id: str
    execution_mode: ExecutionMode = "COACHING"
    executor_model_family: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LlmCompletionResponse:
    """Immutable LLM completion response returned by a gateway adapter."""

    content: str
    model_family: str
    model_id: str
    prompt_sha256: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    scenario_tag: str = "STANDARD"


def compute_prompt_sha256(request: LlmPromptRequest) -> str:
    """Compute canonical `sha256:<64-hex>` fingerprint for a prompt request."""
    canonical = (
        f"family={request.model_family}|model={request.model_id}|"
        f"mode={request.execution_mode}|sys={request.system_prompt.strip()}|"
        f"user={request.user_prompt.strip()}"
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def assert_model_orthogonality(executor_model_family: str, evaluator_model_family: str) -> None:
    """Enforce AD-10: evaluator model family must strictly differ from executor model family."""
    exec_norm = executor_model_family.strip().lower()
    eval_norm = evaluator_model_family.strip().lower()
    if not exec_norm or not eval_norm or exec_norm == eval_norm:
        raise ModelOrthogonalityViolationError(
            detail_override=(
                f"Orthogonalité des modèles violée (AD-10): executor_model_family="
                f"'{executor_model_family}' == evaluator_model_family='{evaluator_model_family}'."
            )
        )


@runtime_checkable
class LLMPort(Protocol):
    """Port interface for LLM completion adapters (LiteLLM in prod, Cassette in CI)."""

    async def complete(self, request: LlmPromptRequest) -> LlmCompletionResponse:
        """Execute a completion request while respecting AD-10 orthogonality rules."""
        ...


# Alias kept for backward compatibility
LlmGatewayPort = LLMPort


@runtime_checkable
class ClockPort(Protocol):
    """Deterministic / system UTC clock port."""

    def now_utc(self) -> datetime:
        """Return current timezone-aware UTC datetime."""
        ...


@dataclass(frozen=True, slots=True)
class CasStoredObject:
    """Immutable Content-Addressable Storage object (`cas/<sha256>`)."""

    cas_key: str
    sha256: str
    source_uri: str
    content_bytes: bytes
    content_type: str = "application/octet-stream"


@runtime_checkable
class ObjectStoragePort(Protocol):
    """Port for S3 v4 Content-Addressable Storage (`SeaweedFS` in prod, fake in unit tests)."""

    def put_bytes(
        self,
        *,
        cas_key: str,
        sha256: str,
        source_uri: str,
        content_bytes: bytes,
        content_type: str = "application/octet-stream",
    ) -> CasStoredObject:
        """Store an immutable CAS blob keyed by `cas/<sha256>`."""
        ...

    def get_bytes(self, cas_key: str) -> CasStoredObject | None:
        """Retrieve a CAS blob by `cas/<sha256>` key or return `None`."""
        ...


@runtime_checkable
class BlackboardPort(Protocol):
    """Hexagonal port decoupling `orchestration` from concrete `blackboard` storage (`M1`)."""

    def get_active_artifact(self, run_id: str, step_key: str, artifact_key: str) -> tuple[Any, str]:
        """Resolve `(artifact_value, snapshot_id)` from the latest `ACTIVE` snapshot."""
        ...


@runtime_checkable
class OutboxRelayPort(Protocol):
    """Engine-independent port for publishing and relaying transactional Outbox events (`C3`)."""

    def enqueue_in_transaction(self, event: DomainEvent) -> None:
        """Stage a domain event for insertion in the current Unit of Work transaction."""
        ...

    def relay_pending_batch(self, *, batch_size: int = 100) -> int:
        """Relay up to `batch_size` `PENDING` events idempotently; return count published."""
        ...


@dataclass(frozen=True, slots=True)
class SandboxExecutionRequest:
    """Out-of-process sandbox execution request (`TIER_1_WASM` or `TIER_2_CONTAINER`, `AD-9`)."""

    tier: SandboxExecutionTier
    entrypoint: str
    payload: dict[str, Any]
    timeout_ms: int = 5000
    max_memory_mb: int = 256


@dataclass(frozen=True, slots=True)
class SandboxExecutionResult:
    """Out-of-process sandbox execution result."""

    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


@runtime_checkable
class SandboxPort(Protocol):
    """Out-of-process sandbox execution port (`wasmtime-py` Tier 1 / `gVisor` Tier 2, `Q3`)."""

    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        """Execute a deterministic check or skill in the isolated sandbox runner."""
        ...


@dataclass(frozen=True, slots=True)
class ConnectorCapabilities:
    """Declarative capability metadata exposed by a `ConnectorPort` plugin (`AD-20`, `AC-E3`)."""

    scheme: str
    display_name: str
    pack_name: str
    supports_read: bool = True
    supports_write: bool = False
    supports_passthrough_auth: bool = True
    supports_service_principal: bool = True
    version_resolution_mode: Literal["ref_or_latest", "last_path_segment"] = "ref_or_latest"


@dataclass(frozen=True, slots=True)
class ConnectorFetchResult:
    """Resolved upstream payload returned by `ConnectorPort.fetch(uri)` (`AD-20`, `AC-E3`)."""

    uri: str
    scheme: str
    resolved_version: str
    content_bytes: bytes
    content_type: str = "application/json"
    sha256: str = ""


@dataclass(frozen=True, slots=True)
class ConnectorInvokeResult:
    """Idempotent action invocation result returned by `ConnectorPort.invoke(...)` (`AD-20`)."""

    scheme: str
    action: str
    idempotency_key: str
    replayed_from_idempotency_cache: bool
    status: Literal["SUCCEEDED", "REJECTED"]
    output: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConnectorHealthStatus:
    """Health check status returned by `ConnectorPort.health()` (`AD-20`, `AC-E3`)."""

    scheme: str
    state: ConnectorHealthState
    latency_ms: float = 0.0
    detail: str = "OK"


@runtime_checkable
class ConnectorPort(Protocol):
    """Universal connector contract discovered via `entry_points(group='orcia.connectors')`."""

    def capabilities(self) -> ConnectorCapabilities:
        """Return immutable connector capabilities and scheme metadata."""
        ...

    def fetch(self, uri: str) -> ConnectorFetchResult:
        """Fetch an upstream resource by federated URI (`<scheme>://...`)."""
        ...

    def invoke(
        self, action: str, payload: dict[str, Any], idempotency_key: str
    ) -> ConnectorInvokeResult:
        """Execute a governed action idempotently keyed by `idempotency_key`."""
        ...

    def health(self) -> ConnectorHealthStatus:
        """Check upstream connector reachability and readiness."""
        ...

    def map_error(self, exc: Exception) -> OrciaDomainError:
        """Translate a connector exception into a canonical `OrciaDomainError` (RFC 9457)."""
        ...


_CONNECTOR_LOCK = threading.Lock()
_CONNECTOR_REGISTRY: dict[str, ConnectorPort] = {}
_DEFAULT_SCHEMES: set[str] = {"orcia", "db", "mcp"}
_ENTRY_POINTS_LOADED: bool = False


def register_connector(connector: ConnectorPort) -> None:
    """Register a `ConnectorPort` instance into the dynamic scheme registry (`AD-20`, `AC-E3`)."""
    caps = connector.capabilities()
    scheme = caps.scheme.strip().lower()
    if not scheme:
        raise ValueError("Connector capabilities().scheme must be a non-empty string.")
    with _CONNECTOR_LOCK:
        _CONNECTOR_REGISTRY[scheme] = connector


def unregister_connector(scheme: str) -> None:
    """Remove a dynamically registered connector scheme (used in isolated tests)."""
    norm = scheme.strip().lower()
    with _CONNECTOR_LOCK:
        _CONNECTOR_REGISTRY.pop(norm, None)


def _ensure_entry_points_loaded() -> None:
    global _ENTRY_POINTS_LOADED
    with _CONNECTOR_LOCK:
        if _ENTRY_POINTS_LOADED:
            return
        _ENTRY_POINTS_LOADED = True
    try:
        eps = importlib.metadata.entry_points(group="orcia.connectors")
        for ep in eps:
            loaded = ep.load()
            instance = loaded() if callable(loaded) else loaded
            if isinstance(instance, ConnectorPort):
                register_connector(instance)
    except Exception:
        pass


def get_registered_connector(scheme: str) -> ConnectorPort | None:
    """Return the registered `ConnectorPort` for `scheme` or `None`."""
    _ensure_entry_points_loaded()
    norm = scheme.strip().lower()
    with _CONNECTOR_LOCK:
        return _CONNECTOR_REGISTRY.get(norm)


def list_registered_connector_schemes() -> frozenset[str]:
    """Return the single source of truth for all registered connector schemes (`AD-20`, `AC-E3`)."""
    _ensure_entry_points_loaded()
    with _CONNECTOR_LOCK:
        return frozenset(_DEFAULT_SCHEMES | set(_CONNECTOR_REGISTRY.keys()))


def is_registered_connector_scheme(scheme: str) -> bool:
    """Return True if `scheme` is a registered connector scheme (`AD-20`)."""
    return scheme.strip().lower() in list_registered_connector_schemes()


@dataclass(frozen=True, slots=True)
class StepExecutorContext:
    """Immutable execution context passed to a `StepExecutorPort` (`Story 3.2f`, `AC-F1`)."""

    run_id: str
    root_run_id: str
    workspace_id: str
    workflow_uri: str
    step_key: str
    step_title: str
    step_type: str
    execution_regime: str
    directive: str
    declared_input_uris: tuple[str, ...]
    resolved_inputs: dict[str, Any]
    datasources: tuple[str, ...] = ()
    agent_uri: str | None = None
    skill_uri: str | None = None
    sub_workflow_uri: str | None = None
    max_agent_retries: int = 3
    budget_remaining_usd: float = 10.0
    idempotency_key: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StepExecutorResult:
    """Execution result returned by a `StepExecutorPort` (`Story 3.2f`, `AC-F1`)."""

    step_key: str
    step_type: str
    status: Literal[
        "EXECUTED",
        "WAITING_FOR_HUMAN_ARBITRATION",
        "WAITING_FOR_HUMAN_GATE",
        "FAILED",
    ]
    artifact_payload: dict[str, Any]
    summary: str
    details: str
    cost_usd: float = 0.0
    child_run_id: str | None = None


@runtime_checkable
class StepExecutorPort(Protocol):
    """Universal step executor discovered via `entry_points(group='orcia.step_executors')`."""

    @property
    def step_type(self) -> str:
        """Return the canonical `WorkflowStepType` handled by this executor."""
        ...

    def execute_step(self, context: StepExecutorContext) -> StepExecutorResult:
        """Execute a step deterministically using real ports (`LLMPort`, `ConnectorInvoker`)."""
        ...


_STEP_EXECUTOR_LOCK = threading.Lock()
_STEP_EXECUTOR_REGISTRY: dict[str, StepExecutorPort] = {}
_STEP_EXECUTOR_EPS_LOADED: bool = False


def register_step_executor(executor: StepExecutorPort) -> None:
    """Register a `StepExecutorPort` instance into the dynamic step executor registry (`AC-F1`)."""
    st = executor.step_type.strip().upper()
    if not st:
        raise ValueError("StepExecutorPort.step_type must be a non-empty string.")
    with _STEP_EXECUTOR_LOCK:
        _STEP_EXECUTOR_REGISTRY[st] = executor


def _ensure_step_executor_entry_points_loaded() -> None:
    global _STEP_EXECUTOR_EPS_LOADED
    with _STEP_EXECUTOR_LOCK:
        if _STEP_EXECUTOR_EPS_LOADED:
            return
        _STEP_EXECUTOR_EPS_LOADED = True
    try:
        eps = importlib.metadata.entry_points(group="orcia.step_executors")
        for ep in eps:
            loaded = ep.load()
            instance = loaded() if callable(loaded) else loaded
            if isinstance(instance, StepExecutorPort):
                register_step_executor(instance)
    except Exception:
        pass


def get_registered_step_executor(step_type: str) -> StepExecutorPort | None:
    """Return the registered `StepExecutorPort` for `step_type` or `None` (`AC-F1`)."""
    _ensure_step_executor_entry_points_loaded()
    norm = step_type.strip().upper()
    with _STEP_EXECUTOR_LOCK:
        return _STEP_EXECUTOR_REGISTRY.get(norm)


def list_registered_step_executor_types() -> frozenset[str]:
    """Return all registered step executor types (`AC-F1`)."""
    _ensure_step_executor_entry_points_loaded()
    with _STEP_EXECUTOR_LOCK:
        return frozenset(_STEP_EXECUTOR_REGISTRY.keys())


from orcia_kernel.context_ports import (  # noqa: E402
    AssistantWorkflowBlueprint,
    AssistantWorkflowTemplatePort,
    ContextSliceKind,
    ContextSliceRecord,
    ContextSourcePort,
    IndexerRegimeDescriptor,
    VectorSearchHitRecord,
    VectorStorePort,
    get_registered_indexer_regime,
    list_registered_assistant_templates,
    list_registered_indexer_regimes,
    register_assistant_template,
    register_indexer_regime,
    unregister_assistant_template,
)

__all__ = [
    "AssistantWorkflowBlueprint",
    "AssistantWorkflowTemplatePort",
    "BlackboardPort",
    "CasStoredObject",
    "ClockPort",
    "ConnectorCapabilities",
    "ConnectorFetchResult",
    "ConnectorHealthState",
    "ConnectorHealthStatus",
    "ConnectorInvokeResult",
    "ConnectorPort",
    "ContextSliceKind",
    "ContextSliceRecord",
    "ContextSourcePort",
    "ExecutionMode",
    "IndexerRegimeDescriptor",
    "LLMPort",
    "LlmCompletionResponse",
    "LlmGatewayPort",
    "LlmPromptRequest",
    "ObjectStoragePort",
    "OutboxRelayPort",
    "SandboxExecutionRequest",
    "SandboxExecutionResult",
    "SandboxPort",
    "StepExecutorContext",
    "StepExecutorPort",
    "StepExecutorResult",
    "VectorSearchHitRecord",
    "VectorStorePort",
    "assert_model_orthogonality",
    "compute_prompt_sha256",
    "get_registered_connector",
    "get_registered_indexer_regime",
    "get_registered_step_executor",
    "is_registered_connector_scheme",
    "list_registered_assistant_templates",
    "list_registered_connector_schemes",
    "list_registered_indexer_regimes",
    "list_registered_step_executor_types",
    "register_assistant_template",
    "register_connector",
    "register_indexer_regime",
    "register_step_executor",
    "unregister_assistant_template",
    "unregister_connector",
]
