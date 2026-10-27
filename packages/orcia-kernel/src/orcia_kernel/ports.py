"""Hexagonal Kernel Ports (`AD-1`, `AD-5`, `AD-9`, `AD-10`, `AD-12`, `AD-19`, `C3`).

Defines pure Protocol interfaces (`BlackboardPort`, `OutboxRelayPort`, `LLMPort`,
`ObjectStoragePort`, `SandboxPort`, `ClockPort`) with zero framework or SDK dependencies.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol, runtime_checkable

from orcia_kernel.enums import SandboxExecutionTier
from orcia_kernel.errors import ModelOrthogonalityViolationError
from orcia_kernel.events import DomainEvent

ExecutionMode = Literal["COACHING", "FAST_PATH"]


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
    """Engine-independent port for publishing and relaying transactional Outbox events (`C3`).

    Can be implemented either via a `Dramatiq` actor or a scheduled `DBOS` workflow using
    `SELECT ... FOR UPDATE SKIP LOCKED` on `domain_events_outbox`.
    """

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
