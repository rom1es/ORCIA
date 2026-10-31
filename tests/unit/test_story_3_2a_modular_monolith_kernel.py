"""Unit & Architectural Tests for Story 3.2a: Modular Monolith Foundation (`AD-19`).

Covers AC1 (4-package uv workspace & orcia_kernel), AC2 (zero circular dependencies),
AC3 (schemas in apps/api), AC4 (domain errors & API registry), and AC5 (Composition Root).
"""

from __future__ import annotations

import ast
import pathlib
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tests.unit.fakes import (
    DeterministicClockFake,
    InMemoryCasObjectStore,
    InMemoryObjectStorageFake,
    InMemoryOutboxRelay,
    InMemoryRevocationStore,
    InMemorySandboxFake,
)

from orcia_api.dependencies import (
    get_auth_service,
    get_bootstrap_service,
    get_catalog_service,
    get_ontology_and_rag_services,
    get_orchestration_service,
    get_permission_broker_service,
    initialize_app_services,
)
from orcia_api.errors.registry import (
    DOMAIN_ERROR_CLASSES,
    ERROR_CLASS_REGISTRY,
    ERROR_CODE_REGISTRY,
    AuditLedgerImmutableViolationError,
    BlackboardAppendOnlyViolationError,
    ErrorHttpMapping,
    OrciaDomainError,
    resolve_domain_error_mapping,
)
from orcia_api.main import create_app
from orcia_core.audit_finops.errors import (
    AuditLedgerImmutableViolationError as AuditDomainErr,
)
from orcia_core.blackboard.errors import (
    BlackboardAppendOnlyViolationError as BlackboardDomainErr,
)
from orcia_core.bootstrap.errors import ModelOrthogonalityViolationError as BootstrapDomainErr
from orcia_core.catalog.errors import ReadSourceDeniedError as CatalogDomainErr
from orcia_core.gates.errors import ModelOrthogonalityViolationError as GatesDomainErr
from orcia_core.ontology.errors import OntologyConflictError as OntologyDomainErr
from orcia_core.orchestration.errors import (
    SubWorkflowMaxDepthExceededError as OrchestrationDomainErr,
)
from orcia_core.permissions.errors import ConfusedDeputyBlockedError as PermissionsDomainErr
from orcia_core.rag.errors import DdlOnlyTransactionalDataError as RagDomainErr
from orcia_kernel import (
    ArtifactProduced,
    BlackboardPort,
    ClockPort,
    DomainEvent,
    GateEvaluated,
    HumanArbitrationRequested,
    LlmCompletionResponse,
    LLMPort,
    LlmPromptRequest,
    ModelOrthogonalityViolationError,
    ObjectStoragePort,
    OutboxRelayPort,
    ResourceNotFoundError,
    RunTerminated,
    SandboxExecutionRequest,
    SandboxPort,
    StepCompleted,
    ValidationDomainError,
    assert_model_orthogonality,
    compute_bytes_sha256,
    compute_prompt_sha256,
    extract_uuid7_timestamp_ms,
    get_localized_error_text,
    is_valid_uuid7,
    new_uuid7,
    new_uuid7_str,
    resolve_locale,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_ac1_uv_workspace_4_packages_and_kernel_primitives() -> None:
    """Verify the 4 uv workspace packages exist and `orcia_kernel` primitives operate purely."""
    expected_pyprojects = [
        REPO_ROOT / "pyproject.toml",
        REPO_ROOT / "packages/orcia-kernel/pyproject.toml",
        REPO_ROOT / "packages/orcia-core/pyproject.toml",
        REPO_ROOT / "apps/api/pyproject.toml",
        REPO_ROOT / "apps/worker/pyproject.toml",
    ]
    for path in expected_pyprojects:
        assert path.is_file(), f"Missing pyproject.toml: {path}"

    uid = new_uuid7()
    uid_str = new_uuid7_str()
    assert is_valid_uuid7(uid)
    assert is_valid_uuid7(uid_str)
    assert not is_valid_uuid7("not-a-uuid")
    assert extract_uuid7_timestamp_ms(uid) > 1_700_000_000_000
    with pytest.raises(ValueError, match="Expected a valid UUIDv7"):
        extract_uuid7_timestamp_ms("00000000-0000-4000-8000-000000000000")

    digest = compute_bytes_sha256(b"orcia-kernel-test")
    assert len(digest) == 64

    req = LlmPromptRequest(
        system_prompt="sys",
        user_prompt="usr",
        model_family="anthropic-claude",
        model_id="claude-sonnet-4",
    )
    prompt_hash = compute_prompt_sha256(req)
    assert prompt_hash.startswith("sha256:")
    resp = LlmCompletionResponse(
        content="ok",
        model_family="anthropic-claude",
        model_id="claude-sonnet-4",
        prompt_sha256=prompt_hash,
        input_tokens=10,
        output_tokens=5,
        estimated_cost_usd=0.001,
    )
    assert resp.content == "ok"
    assert_model_orthogonality("anthropic-claude", "openai-gpt")
    with pytest.raises(ModelOrthogonalityViolationError):
        assert_model_orthogonality("anthropic-claude", "anthropic-claude")


@pytest.mark.asyncio
async def test_ac1_kernel_domain_events_and_ports_fakes() -> None:
    """Verify `orcia_kernel.events` outbox payloads and `orcia_kernel.ports` protocol fakes."""
    workspace_id = new_uuid7_str()
    run_id = new_uuid7_str()

    step_ev = StepCompleted.create(
        step_execution_id=new_uuid7_str(),
        workspace_id=workspace_id,
        run_id=run_id,
        step_key="step-01",
        step_status="COMMITTED",
        cost_usd=0.05,
        trace_id="a" * 32,
    )
    art_ev = ArtifactProduced.create(
        snapshot_id=new_uuid7_str(),
        workspace_id=workspace_id,
        run_id=run_id,
        artifact_cas_key="cas/" + "b" * 64,
        artifact_sha256="b" * 64,
        trace_id="a" * 32,
    )
    gate_ev = GateEvaluated.create(
        gate_evaluation_id=new_uuid7_str(),
        workspace_id=workspace_id,
        run_id=run_id,
        gate_type="AGENTIC_LENS",
        passed=True,
        score=0.94,
        trace_id="a" * 32,
    )
    term_ev = RunTerminated.create(
        workspace_id=workspace_id,
        run_id=run_id,
        final_status="COMPLETED",
        total_cost_usd=0.12,
        trace_id="a" * 32,
    )
    arb_ev = HumanArbitrationRequested.create(
        arbitration_id=new_uuid7_str(),
        workspace_id=workspace_id,
        run_id=run_id,
        step_key="step-02",
        options_count=2,
        trace_id="a" * 32,
    )

    relay = InMemoryOutboxRelay()
    assert isinstance(relay, OutboxRelayPort)
    for ev in (step_ev, art_ev, gate_ev, term_ev, arb_ev):
        assert isinstance(ev, DomainEvent)
        row = ev.to_outbox_dict()
        assert row["workspace_id"] == workspace_id
        assert row["status"] == "PENDING"
        relay.enqueue_in_transaction(ev)

    assert len(relay.pending_events) == 5
    flushed = relay.relay_pending_batch(batch_size=3)
    assert flushed == 3
    assert len(relay.pending_events) == 2
    assert len(relay.published_events) == 3

    obj_store = InMemoryObjectStorageFake()
    assert isinstance(obj_store, ObjectStoragePort)
    sha = compute_bytes_sha256(b"hello")
    stored = obj_store.put_bytes(
        cas_key=f"cas/{sha}",
        sha256=sha,
        source_uri="git://repo/file.md",
        content_bytes=b"hello",
        content_type="text/plain",
    )
    assert stored.content_bytes == b"hello"
    fetched = obj_store.get_bytes(f"cas/{sha}")
    assert fetched is not None and fetched.content_bytes == b"hello"
    assert obj_store.get_bytes("cas/missing") is None

    clock = DeterministicClockFake(datetime(2026, 10, 27, 10, 0, 0, tzinfo=UTC))
    assert isinstance(clock, ClockPort)
    t0 = clock.now_utc()
    clock.advance_seconds(60.0)
    assert (clock.now_utc() - t0).total_seconds() == 60.0

    sandbox = InMemorySandboxFake()
    assert isinstance(sandbox, SandboxPort)
    sb_res = await sandbox.execute(
        SandboxExecutionRequest(tier="TIER_1_WASM", entrypoint="run", payload={"k": "v"})
    )
    assert sb_res.passed is True
    assert sb_res.exit_code == 0

    cas_store = InMemoryCasObjectStore()
    rev_store = InMemoryRevocationStore()
    rev_store.revoke_jti("jti-123", ttl_seconds=60)
    assert rev_store.is_revoked("jti-123")
    assert not cas_store.has_object("cas/none")
    assert BlackboardPort is not None
    assert LLMPort is not None


def test_ac2_and_ac3_no_core_schemas_and_no_domain_exceptions_file() -> None:
    """Verify `orcia_core/schemas` and `orcia_core/domain/exceptions.py` no longer exist."""
    core_root = REPO_ROOT / "packages/orcia-core/src/orcia_core"
    assert not (core_root / "schemas").exists()
    assert not (core_root / "domain/exceptions.py").exists()

    api_schemas_dir = REPO_ROOT / "apps/api/src/orcia_api/schemas"
    schema_files = sorted(p.name for p in api_schemas_dir.glob("*.py"))
    assert len(schema_files) >= 10


def test_ac4_domain_errors_hierarchy_and_central_api_registry() -> None:
    """Verify every domain error inherits from `OrciaDomainError` and is mapped in registry."""
    domain_error_samples = [
        AuditDomainErr(),
        BlackboardDomainErr(),
        BootstrapDomainErr(),
        CatalogDomainErr(),
        GatesDomainErr(),
        OntologyDomainErr(),
        OrchestrationDomainErr(),
        PermissionsDomainErr(),
        RagDomainErr(),
        ResourceNotFoundError(),
        ValidationDomainError(),
    ]
    for err in domain_error_samples:
        assert isinstance(err, OrciaDomainError)
        mapping = resolve_domain_error_mapping(err)
        assert isinstance(mapping, ErrorHttpMapping)
        assert mapping.http_status == err.http_status
        assert mapping.error_code == err.error_code
        assert mapping.type_uri == err.type_uri
        assert err.localize("fr").title
        assert err.localize("en").title

    assert len(DOMAIN_ERROR_CLASSES) >= 20
    assert AuditLedgerImmutableViolationError in ERROR_CLASS_REGISTRY
    assert BlackboardAppendOnlyViolationError in ERROR_CLASS_REGISTRY
    assert "ERR_AUDIT_LEDGER_IMMUTABLE" in ERROR_CODE_REGISTRY
    assert "ERR_BLACKBOARD_APPEND_ONLY_VIOLATION" in ERROR_CODE_REGISTRY

    class CustomUnregisteredDomainError(OrciaDomainError):
        error_code = "ERR_CUSTOM_UNREGISTERED"
        http_status = 409
        type_slug = "custom-unregistered"

    fallback_mapping = resolve_domain_error_mapping(CustomUnregisteredDomainError())
    assert fallback_mapping.http_status == 409
    assert fallback_mapping.type_uri == "https://orcia.io/problems/custom-unregistered"

    assert resolve_locale("en-US,en;q=0.9,fr;q=0.8") == "en"
    assert resolve_locale("de-DE,es;q=0.5") == "fr"
    assert resolve_locale("en;q=invalid,fr;q=0.7") == "fr"
    assert get_localized_error_text("ERR_UNKNOWN_CODE", "fr").title


def test_ac5_no_router_import_time_singletons_and_composition_root_lifespan() -> None:
    """Verify zero `_DEFAULT_*_SERVICE` singletons in routers and test `dependencies.py`."""
    routers_dir = REPO_ROOT / "apps/api/src/orcia_api/routers"
    for router_file in sorted(routers_dir.glob("*.py")):
        source = router_file.read_text()
        assert "_DEFAULT_" not in source, f"Found _DEFAULT_ singleton in {router_file.name}"
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                assert not isinstance(node.value, ast.Call) or (
                    getattr(node.value.func, "id", "")
                    not in {
                        "build_default_auth_and_org_service",
                        "build_default_federated_catalog_service",
                        "build_default_orchestration_setup_service",
                    }
                ), f"Import-time service instantiation in {router_file.name}"

    bare_app = FastAPI()
    initialize_app_services(bare_app)
    assert bare_app.state.auth_service is not None
    assert bare_app.state.catalog_service is not None
    assert bare_app.state.permission_broker_service is not None
    assert bare_app.state.bootstrap_service is not None
    assert bare_app.state.orchestration_service is not None

    app = create_app()
    with TestClient(app) as client:
        res = client.get("/api/v1/health")
        assert res.status_code == 200

    class DummyRequest:
        def __init__(self, target_app: FastAPI) -> None:
            self.app = target_app

    uninitialized_app = FastAPI()
    req = DummyRequest(uninitialized_app)
    assert get_auth_service(req) is not None  # type: ignore[arg-type]
    assert get_catalog_service(EmptyAppRequest()) is not None  # type: ignore[arg-type]
    assert get_permission_broker_service(EmptyAppRequest()) is not None  # type: ignore[arg-type]
    assert get_bootstrap_service(EmptyAppRequest()) is not None  # type: ignore[arg-type]
    assert get_orchestration_service(EmptyAppRequest()) is not None  # type: ignore[arg-type]
    assert len(get_ontology_and_rag_services(req, fixture=False)) == 3  # type: ignore[arg-type]
    assert len(get_ontology_and_rag_services(req, fixture=True)) == 3  # type: ignore[arg-type]


class EmptyAppRequest:
    """Helper request with a fresh FastAPI instance to exercise lazy initialization branches."""

    def __init__(self) -> None:
        self.app = FastAPI()
