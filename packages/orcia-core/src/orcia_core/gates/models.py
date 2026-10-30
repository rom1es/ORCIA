"""Domain models for Bounded Context 6: Gates (`AD-9`, `AD-10`, `AD-11`, `FR-17`, `Story 4.1`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

GateType = Literal["DETERMINISTIC", "AGENTIC", "HUMAN"]
GateStatus = Literal["PASS", "FAIL", "ERROR", "PENDING_HUMAN_REVIEW"]
SandboxTierLiteral = Literal["TIER_1_WASM", "TIER_2_CONTAINER", "NONE"]

CANONICAL_SPINE_ALLOWED_DEPENDENCIES: tuple[str, ...] = (
    "fastapi",
    "uvicorn",
    "pydantic",
    "orjson",
    "uuid-utils",
    "structlog",
    "sqlalchemy",
    "asyncpg",
    "psycopg",
    "alembic",
    "dbos",
    "dramatiq",
    "redis",
    "httpx",
    "argon2-cffi",
    "cryptography",
    "pyjwt",
    "pyotp",
    "pyyaml",
    "litellm",
    "docling",
    "tree-sitter",
    "wasmtime",
    "opentelemetry-sdk",
    "opentelemetry-instrumentation-fastapi",
    "opentelemetry-instrumentation-sqlalchemy",
    "react",
    "vite",
    "@tanstack/react-router",
    "@tanstack/react-query",
    "@xyflow/react",
    "zustand",
    "tailwindcss",
    "openapi-fetch",
)

CANONICAL_FORBIDDEN_DRIFT_PATTERNS: tuple[dict[str, str], ...] = (
    {
        "rule_id": "DRIFT-NO-SQLITE-IN-INTEGRATION",
        "pattern": "sqlite://",
        "severity": "CRITICAL",
        "message": "Interdiction d'utiliser SQLite en test d'intégration (PostgreSQL 18 requis).",
    },
    {
        "rule_id": "DRIFT-NO-MINIO-AGPL",
        "pattern": "minio/minio",
        "severity": "HIGH",
        "message": "MinIO (AGPL-3.0 archivé) est interdit ; utiliser SeaweedFS S3 (Apache-2.0).",
    },
    {
        "rule_id": "DRIFT-NO-NEXTJS-APP-ROUTER",
        "pattern": "next/navigation",
        "severity": "HIGH",
        "message": "Next.js est interdit (OQ-02) ; utiliser Vite 6 + TanStack Router v1.",
    },
    {
        "rule_id": "DRIFT-NO-DBOS-PRIVATE-API",
        "pattern": "dbos._",
        "severity": "CRITICAL",
        "message": "Appel interdit à une API privée dbos._* (AD-2 Règle 3).",
    },
    {
        "rule_id": "DRIFT-NO-IMPORT-SINGLETON",
        "pattern": "_default_orchestration_service",
        "severity": "HIGH",
        "message": "Singleton d'import interdit (AD-1 / AD-19 M5).",
    },
)


@dataclass(frozen=True, slots=True)
class PatternDriftFinding:
    """Single Pattern Drift violation against `ARCHITECTURE-SPINE.md` (`FR-17`, `AD-9`)."""

    rule_id: str
    forbidden_symbol: str
    severity: str
    message: str


@dataclass(frozen=True, slots=True)
class OntologyAxiomCheckRule:
    """Formal ontology axiom rule checked inside the Tier 1 Sandbox (`AD-7`, `AD-9`)."""

    axiom_key: str
    forbidden_term: str = ""
    required_term: str = ""


@dataclass(frozen=True, slots=True)
class WorkspaceSpineBaseline:
    """Adopted `ARCHITECTURE-SPINE.md` baseline registered for a Workspace (`FR-28`, `AD-16`)."""

    workspace_id: str
    spine_version: str
    status: Literal["ADOPTED"]
    allowed_dependencies: tuple[str, ...]
    forbidden_patterns: tuple[dict[str, str], ...]
    spine_markdown: str
    content_sha256: str
    signed_by_user_id: str
    human_anchor_signature: str


@dataclass(frozen=True, slots=True)
class DeterministicGateInput:
    """Input contract for evaluating a Deterministic Gate in Tier 1 Sandbox (`Story 4.1`)."""

    workspace_id: str
    run_id: str
    step_execution_id: str
    step_key: str
    artifact_payload: dict[str, Any]
    required_sections: tuple[str, ...] = ("artifact",)
    ontology_axioms: tuple[OntologyAxiomCheckRule, ...] = ()
    allowed_dependencies: tuple[str, ...] | None = None
    forbidden_patterns: tuple[dict[str, str], ...] | None = None
    timeout_ms: int = 5000
    max_memory_mb: int = 256
    simulate_timeout_sleep_ms: int = 0
    simulate_network_escape: bool = False
    simulate_fs_escape_path: str | None = None
    simulate_tmp_overflow_mb: int = 0
    simulate_memory_alloc_mb: int = 0


@dataclass(frozen=True, slots=True)
class GateEvaluationEntity:
    """Persisted gate evaluation record (`gate_evaluations` table, `AD-9..11`)."""

    id: str
    workspace_id: str
    run_id: str
    step_execution_id: str
    step_key: str
    gate_type: GateType
    sandbox_tier: SandboxTierLiteral
    status: GateStatus
    score: float
    schema_validation_passed: bool
    ontology_axioms_passed: bool
    pattern_drift_passed: bool
    pattern_drift_findings: tuple[PatternDriftFinding, ...] = ()
    missing_sections: tuple[str, ...] = ()
    violated_axioms: tuple[dict[str, str], ...] = ()
    lens_findings: tuple[dict[str, Any], ...] = ()
    briefing_4blocks: dict[str, Any] = field(default_factory=dict)
    evaluator_model_id: str | None = None
    duration_ms: int = 0
    review_duration_ms: int = 0
    fast_approval_warning: bool = False
    outbox_event_id: str | None = None
    evaluated_at: str = ""
    sandbox_exit_code: int = 0
    sandbox_stderr: str = ""
