"""Hexagonal Kernel Ports (`AD-1`, `AD-5`, `AD-9`, `AD-10`, `AD-12`, `AD-19`, `AD-20`, `C3`).

Defines pure Protocol interfaces (`BlackboardPort`, `OutboxRelayPort`, `LLMPort`,
`ObjectStoragePort`, `SandboxPort`, `ConnectorPort`, `ClockPort`) and connector registry
with zero framework or SDK dependencies.
"""

from __future__ import annotations

import importlib.metadata
import threading
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from orcia_core.kernel._ports_models import (
    CasStoredObject,
    ExecutionMode,
    LlmCompletionResponse,
    LlmPromptRequest,
    SandboxExecutionRequest,
    SandboxExecutionResult,
    StepExecutorContext,
    StepExecutorResult,
    assert_model_orthogonality,
    compute_prompt_sha256,
)
from orcia_core.kernel.connector_ports import (
    AccessRequestChannelPort,
    ConnectorCapabilities,
    ConnectorFetchResult,
    ConnectorHealthState,
    ConnectorHealthStatus,
    ConnectorInvokeResult,
    ConnectorPort,
    ResourceLeasePort,
    ResourceLeaseRecord,
    get_access_request_channel,
    get_registered_connector,
    is_registered_connector_scheme,
    list_registered_connector_schemes,
    register_access_request_channel,
    register_connector,
    unregister_connector,
)
from orcia_core.kernel.context_ports import (
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
from orcia_core.kernel.events import DomainEvent
from orcia_core.kernel.secret_ports import (
    SecretProviderPort,
    SecretRef,
    SecretRotationAuditEntry,
    WorkspaceEnvelopeKeyRecord,
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


@runtime_checkable
class SandboxPort(Protocol):
    """Out-of-process sandbox execution port (`wasmtime-py` Tier 1 / `gVisor` Tier 2, `Q3`)."""

    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        """Execute a deterministic check or skill in the isolated sandbox runner."""
        ...


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


__all__ = [
    "AccessRequestChannelPort",
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
    "ResourceLeasePort",
    "ResourceLeaseRecord",
    "SandboxExecutionRequest",
    "SandboxExecutionResult",
    "SandboxPort",
    "SecretProviderPort",
    "SecretRef",
    "SecretRotationAuditEntry",
    "StepExecutorContext",
    "StepExecutorPort",
    "StepExecutorResult",
    "VectorSearchHitRecord",
    "VectorStorePort",
    "WorkspaceEnvelopeKeyRecord",
    "assert_model_orthogonality",
    "compute_prompt_sha256",
    "get_access_request_channel",
    "get_registered_connector",
    "get_registered_indexer_regime",
    "get_registered_step_executor",
    "is_registered_connector_scheme",
    "list_registered_assistant_templates",
    "list_registered_connector_schemes",
    "list_registered_indexer_regimes",
    "list_registered_step_executor_types",
    "register_access_request_channel",
    "register_assistant_template",
    "register_connector",
    "register_indexer_regime",
    "register_step_executor",
    "unregister_assistant_template",
    "unregister_connector",
]
