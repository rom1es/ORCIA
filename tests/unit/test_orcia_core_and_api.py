"""Layer 1 Unit & Property-Based Tests for `packages/orcia-core`, `apps/api`, and `apps/worker`."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st

from orcia_api.main import create_app
from orcia_core import (
    BOUNDED_CONTEXTS,
    audit_finops,
    blackboard,
    catalog,
    gates,
    ontology,
    orchestration,
    permissions,
    rag,
)
from orcia_core.bootstrap.seeder import (
    ASSISTANT_WORKFLOW_URI,
    DEFAULT_HUMAN_PROFILE_ARCHETYPES,
    SYSTEM_BOOTSTRAP_WORKFLOW_URIS,
    UpsertSpec,
    build_postgres_upsert_sql,
)
from orcia_core.domain.exceptions import (
    HumanAnchorRequiredError,
    ModelOrthogonalityViolationError,
    ObserverModeReadOnlyError,
    ReadSourceDeniedError,
    ResourceNotFoundError,
    ValidationDomainError,
    get_localized_error_text,
    resolve_locale,
)
from orcia_core.domain.identifiers import (
    extract_uuid7_timestamp_ms,
    is_valid_uuid7,
    new_uuid7,
    new_uuid7_str,
)
from orcia_core.observability.logging import (
    bind_trace_context,
    clear_trace_context,
    configure_structlog,
    generate_trace_id,
    get_current_trace_context,
    get_current_trace_id,
    get_logger,
    resolve_or_create_trace_id,
)
from orcia_core.schemas.shell import build_default_shell_navigation
from orcia_worker.broker import (
    ProcessedPingRegistry,
    configure_broker,
    default_ping_registry,
    execute_system_ping,
    system_ping_actor,
)

FORBIDDEN_HEXAGONAL_IMPORTS = {"fastapi", "sqlalchemy", "dramatiq", "redis", "litellm"}


def test_hexagonal_purity_domain_and_ports() -> None:
    """Enforce AD-1: `domain/` and `ports/` never import framework or adapter libraries."""
    repo_root = Path(__file__).resolve().parents[2]
    core_src = repo_root / "packages" / "orcia-core" / "src" / "orcia_core"

    for subdir in ("domain", "ports"):
        target_dir = core_src / subdir
        for py_file in target_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top_pkg = alias.name.split(".")[0]
                        assert top_pkg not in FORBIDDEN_HEXAGONAL_IMPORTS
                elif isinstance(node, ast.ImportFrom) and node.module:
                    top_pkg = node.module.split(".")[0]
                    assert top_pkg not in FORBIDDEN_HEXAGONAL_IMPORTS


def test_eight_bounded_contexts_registered() -> None:
    """Verify all 8 bounded contexts of ORCIA Core are present and importable."""
    assert len(BOUNDED_CONTEXTS) == 8
    modules = (
        orchestration,
        blackboard,
        catalog,
        ontology,
        rag,
        gates,
        permissions,
        audit_finops,
    )
    assert tuple(m.DOMAIN_NAME for m in modules) == BOUNDED_CONTEXTS


def test_uuid7_generation_and_monotonic_timestamp() -> None:
    """Verify UUIDv7 generation, validation, and timestamp extraction."""
    u1 = new_uuid7()
    u2_str = new_uuid7_str()
    assert is_valid_uuid7(u1)
    assert is_valid_uuid7(u2_str)
    assert not is_valid_uuid7("not-a-uuid")
    assert not is_valid_uuid7("550e8400-e29b-41d4-a716-446655440000")  # UUIDv4

    ts1 = extract_uuid7_timestamp_ms(u1)
    ts2 = extract_uuid7_timestamp_ms(u2_str)
    assert ts2 >= ts1

    with pytest.raises(ValueError, match="Expected a valid UUIDv7"):
        extract_uuid7_timestamp_ms("550e8400-e29b-41d4-a716-446655440000")


@given(st.integers(min_value=1, max_value=25))
def test_property_uuid7_batch_uniqueness_and_monotonicity(batch_size: int) -> None:
    """Property test: generated UUIDv7 identifiers are unique and non-decreasing in timestamp."""
    generated = [new_uuid7() for _ in range(batch_size)]
    assert len(set(generated)) == batch_size
    timestamps = [extract_uuid7_timestamp_ms(u) for u in generated]
    assert timestamps == sorted(timestamps)


def test_domain_exceptions_and_i18n_error_catalog() -> None:
    """Verify locale resolution (FR default, EN supported, q-weights) and domain exceptions."""
    assert resolve_locale(None) == "fr"
    assert resolve_locale("") == "fr"
    assert resolve_locale("de-DE, es;q=0.8") == "fr"
    assert resolve_locale("fr-FR,fr;q=0.9,en;q=0.8") == "fr"
    assert resolve_locale("en-US,en;q=0.9,fr;q=0.8") == "en"
    assert resolve_locale("fr;q=0.4, en;q=0.9") == "en"
    assert resolve_locale("en;q=0, fr;q=0.8") == "fr"
    assert resolve_locale("en;q=invalid, fr;q=0.5") == "fr"

    err_obs = ObserverModeReadOnlyError(instance="/api/v1/runs/1")
    assert err_obs.http_status == 403
    assert err_obs.error_code == "ERR_OBSERVER_MODE_READ_ONLY"
    assert err_obs.type_uri == "https://orcia.io/problems/observer-mode-read-only"
    assert "lecture seule" in err_obs.localize("fr").title.lower()
    assert "read-only" in err_obs.localize("en").title.lower()

    err_anchor = HumanAnchorRequiredError()
    assert err_anchor.http_status == 422
    assert err_anchor.error_code == "ERR_HUMAN_ANCHOR_REQUIRED"

    err_source = ReadSourceDeniedError(permission_broker_hint="jira://IAM/REQ-1")
    assert err_source.http_status == 403
    assert err_source.permission_broker_hint == "jira://IAM/REQ-1"

    err_ortho = ModelOrthogonalityViolationError(detail_override="Custom detail")
    assert err_ortho.localize("en").detail == "Custom detail"

    err_not_found = ResourceNotFoundError()
    assert err_not_found.http_status == 404

    err_val = ValidationDomainError()
    assert err_val.http_status == 422

    fallback = get_localized_error_text("ERR_UNKNOWN_CODE", "fr")
    assert "interne" in fallback.title.lower()


def test_observability_trace_context_and_structlog() -> None:
    """Verify W3C traceparent parsing, trace_id generation, and context binding."""
    configure_structlog()
    clear_trace_context()

    auto_id = get_current_trace_id()
    assert len(auto_id) == 32

    w3c_trace = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    extracted = resolve_or_create_trace_id(traceparent=w3c_trace)
    assert extracted == "4bf92f3577b34da6a3ce929d0e0e4736"

    # W3C Trace Context spec: all-zero 16-hex parent-id must be rejected
    zero_parent_trace = "00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01"
    rejected_zero_parent = resolve_or_create_trace_id(traceparent=zero_parent_trace)
    assert rejected_zero_parent != "4bf92f3577b34da6a3ce929d0e0e4736"
    assert len(rejected_zero_parent) == 32

    header_trace = "0192c4e0000070008000000000000099"
    assert resolve_or_create_trace_id(x_trace_id=header_trace) == header_trace
    assert len(resolve_or_create_trace_id(traceparent="invalid", x_trace_id="bad")) == 32

    ctx = bind_trace_context(
        header_trace,
        workspace_id="ws-1",
        run_id="run-1",
        step_id="step-1",
    )
    assert get_current_trace_context() == ctx
    log = get_logger("orcia.test")
    log.info("test.event", status="ok")
    clear_trace_context()


def test_bootstrap_seeder_specs_and_upsert_sql() -> None:
    """Verify idempotent upsert SQL builder and system bootstrap constants."""
    assert ASSISTANT_WORKFLOW_URI == "orcia://system/workflows/assistant-agent"
    assert len(SYSTEM_BOOTSTRAP_WORKFLOW_URIS) == 6
    assert len(DEFAULT_HUMAN_PROFILE_ARCHETYPES) == 6

    spec = UpsertSpec(
        table="catalog_items",
        conflict_columns=("uri",),
        value_columns=("title", "sha256"),
    )
    sql = build_postgres_upsert_sql(spec)
    assert "INSERT INTO catalog_items (uri, title, sha256)" in sql
    expected_on_conflict = (
        "ON CONFLICT (uri) DO UPDATE SET title = EXCLUDED.title, sha256 = EXCLUDED.sha256;"
    )
    assert expected_on_conflict in sql

    with pytest.raises(ValueError, match="Unsafe SQL identifier"):
        build_postgres_upsert_sql(
            UpsertSpec(table="bad-table; DROP", conflict_columns=("id",), value_columns=("v",))
        )
    with pytest.raises(ValueError, match="conflict_columns must not be empty"):
        build_postgres_upsert_sql(
            UpsertSpec(table="catalog_items", conflict_columns=(), value_columns=("v",))
        )
    with pytest.raises(ValueError, match="value_columns must not be empty"):
        build_postgres_upsert_sql(
            UpsertSpec(table="catalog_items", conflict_columns=("id",), value_columns=())
        )


def test_fastapi_health_shell_and_rfc9457_localization() -> None:
    """Verify FastAPI /api/v1/health, /api/v1/navigation/shell, and RFC 9457 error envelopes."""
    app = create_app()

    @app.get("/api/v1/test-custom-instance")
    async def _raise_custom_instance() -> None:
        raise ObserverModeReadOnlyError(instance="orcia://custom/instance/run-42")

    client = TestClient(app, raise_server_exceptions=False)

    custom_trace = generate_trace_id()
    health_res = client.get("/api/v1/health", headers={"X-Trace-Id": custom_trace})
    assert health_res.status_code == 200
    assert health_res.headers["X-Trace-Id"] == custom_trace
    assert health_res.json()["status"] == "ok"
    assert health_res.json()["trace_id"] == custom_trace

    # Verify W3C traceparent header propagation on HTTP endpoint
    w3c_header = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    tp_res = client.get("/api/v1/health", headers={"traceparent": w3c_header})
    assert tp_res.status_code == 200
    assert tp_res.headers["X-Trace-Id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert tp_res.json()["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"

    shell_res = client.get("/api/v1/navigation/shell")
    assert shell_res.status_code == 200
    shell_data = shell_res.json()
    assert len(shell_data["modules"]) == 8
    assert shell_data["active_scope_id"] == "scope-ws-orcia"

    # Observer mode guard (403 ERR_OBSERVER_MODE_READ_ONLY) in French (default) and English
    obs_fr = client.get(
        "/api/v1/navigation/shell?scope_id=scope-global&require_contributor=true",
        headers={"Accept-Language": "fr-FR"},
    )
    assert obs_fr.status_code == 403
    assert obs_fr.headers["content-type"].startswith("application/problem+json")
    assert obs_fr.headers["Content-Language"] == "fr"
    assert obs_fr.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"
    assert "lecture seule" in obs_fr.json()["title"].lower()

    obs_en = client.get(
        "/api/v1/navigation/shell?scope_id=scope-global&require_contributor=true",
        headers={"Accept-Language": "fr;q=0.4, en-US;q=0.9"},
    )
    assert obs_en.status_code == 403
    assert obs_en.headers["Content-Language"] == "en"
    assert obs_en.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"
    assert "read-only" in obs_en.json()["title"].lower()

    # Custom instance on OrciaDomainError is preserved in RFC 9457 ProblemDetails
    custom_inst_res = client.get("/api/v1/test-custom-instance")
    assert custom_inst_res.status_code == 403
    assert custom_inst_res.json()["instance"] == "orcia://custom/instance/run-42"

    # Unknown scope -> 404 ERR_RESOURCE_NOT_FOUND
    not_found = client.get("/api/v1/navigation/shell?scope_id=unknown-scope")
    assert not_found.status_code == 404
    assert not_found.json()["error_code"] == "ERR_RESOURCE_NOT_FOUND"

    # Unknown route -> 404 RFC 9457
    route_404 = client.get("/api/v1/non-existent-route", headers={"Accept-Language": "en"})
    assert route_404.status_code == 404
    assert route_404.json()["error_code"] == "ERR_RESOURCE_NOT_FOUND"

    # Validation error -> 422 ERR_VALIDATION_FAILED
    val_err = client.get("/api/v1/navigation/shell?scope_id=")
    assert val_err.status_code == 422
    assert val_err.json()["error_code"] == "ERR_VALIDATION_FAILED"


def test_worker_idempotent_system_ping_actor() -> None:
    """Verify Dramatiq broker configuration and idempotent actor execution."""
    configure_broker(use_stub=True)
    registry = ProcessedPingRegistry()
    trace_id = generate_trace_id()

    first = execute_system_ping("ping-key-1", trace_id, registry=registry)
    assert first.already_processed is False

    second = execute_system_ping("ping-key-1", trace_id, registry=registry)
    assert second.already_processed is True

    default_ping_registry.clear()
    system_ping_actor("ping-key-actor", trace_id)
    assert default_ping_registry.mark_if_new("ping-key-actor") is False
    default_ping_registry.clear()
    registry.clear()

    with pytest.raises(ValueError, match="idempotency_key must not be empty"):
        registry.mark_if_new("   ")

    nav = build_default_shell_navigation(trace_id)
    assert len(nav.modules) == 8


def test_centralized_env_config_loader(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify centralized `.env` loader (`orcia_core.config`) for DB, Redis, API, and Web."""
    from orcia_core.config import (
        generate_strong_secret,
        get_env,
        get_env_int,
        init_or_rotate_env_secrets,
        load_orcia_env,
        resolve_api_host_and_port,
        resolve_database_url,
        resolve_redis_url,
        resolve_web_host_and_port,
    )

    with pytest.raises(ValueError, match="nbytes must be >= 16"):
        generate_strong_secret(8)

    custom_env = tmp_path / ".env.custom"
    custom_env.write_text(
        "ORCIA_WEB_HOST=127.0.0.1\n"
        "ORCIA_WEB_PORT=3150\n"
        "ORCIA_API_HOST=127.0.0.1\n"
        "ORCIA_API_PORT=8150\n"
        "POSTGRES_HOST=127.0.0.1\n"
        "POSTGRES_PORT=5439\n"
        "POSTGRES_USER=orcia_custom\n"
        "POSTGRES_PASSWORD=secret_pw\n"
        "POSTGRES_DB=orcia_custom_db\n"
        "REDIS_HOST=127.0.0.1\n"
        "REDIS_PORT=6389\n"
        "REDIS_DB=2\n"
        "ORCIA_JWT_SIGNING_SECRET=change-me\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("ORCIA_WEB_PORT", raising=False)
    monkeypatch.delenv("ORCIA_API_PORT", raising=False)
    monkeypatch.delenv("POSTGRES_PORT", raising=False)
    monkeypatch.delenv("REDIS_PORT", raising=False)
    monkeypatch.delenv("ORCIA_JWT_SIGNING_SECRET", raising=False)
    monkeypatch.delenv("ORCIA_PASSTHROUGH_MASTER_KEY", raising=False)

    loaded_path = load_orcia_env(env_file=custom_env, override=True)
    assert loaded_path == custom_env
    assert get_env("ORCIA_WEB_PORT") == "3150"
    assert get_env_int("ORCIA_WEB_PORT", 3100) == 3150
    assert resolve_web_host_and_port() == ("127.0.0.1", 3150)
    assert resolve_api_host_and_port() == ("127.0.0.1", 8150)
    expected_db = (
        "postgresql+asyncpg://orcia_custom:secret_pw@"  # pragma: allowlist secret
        "127.0.0.1:5439/orcia_custom_db"
    )
    assert resolve_database_url() == expected_db
    assert resolve_redis_url() == "redis://127.0.0.1:6389/2"

    # Support Docker/K8s <VAR>_FILE secret mounting and fail-fast on missing file
    secret_file = tmp_path / "pg_pass.secret"
    secret_file.write_text("k8s_mounted_secret\n", encoding="utf-8")
    monkeypatch.setenv("POSTGRES_PASSWORD_FILE", str(secret_file))
    assert get_env("POSTGRES_PASSWORD") == "k8s_mounted_secret"
    monkeypatch.setenv("POSTGRES_PASSWORD_FILE", str(tmp_path / "missing.secret"))
    with pytest.raises(ValueError, match="POSTGRES_PASSWORD_FILE"):
        get_env("POSTGRES_PASSWORD")
    monkeypatch.delenv("POSTGRES_PASSWORD_FILE", raising=False)

    # Rotate weak placeholder secrets in-place and append missing ones
    rotated = init_or_rotate_env_secrets(env_file=custom_env, force_rotate=False)
    assert rotated["ORCIA_JWT_SIGNING_SECRET"] is True
    assert rotated["ORCIA_PASSTHROUGH_MASTER_KEY"] is True
    first_jwt = get_env("ORCIA_JWT_SIGNING_SECRET")
    assert len(first_jwt) >= 32 and first_jwt != "change-me-jwt-signing-secret"

    # Second run without force_rotate preserves strong secrets
    rotated_again = init_or_rotate_env_secrets(env_file=custom_env, force_rotate=False)
    assert rotated_again["ORCIA_JWT_SIGNING_SECRET"] is False
    assert get_env("ORCIA_JWT_SIGNING_SECRET") == first_jwt

    # Force rotation replaces even strong secrets
    forced = init_or_rotate_env_secrets(env_file=custom_env, force_rotate=True)
    assert forced["ORCIA_JWT_SIGNING_SECRET"] is True
    assert get_env("ORCIA_JWT_SIGNING_SECRET") != first_jwt

    monkeypatch.setenv("ORCIA_WEB_PORT", "not-an-int")
    assert get_env_int("ORCIA_WEB_PORT", 3100) == 3100

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://explicit/db")
    monkeypatch.setenv("REDIS_URL", "redis://explicit:6379/0")
    assert resolve_database_url() == "postgresql+asyncpg://explicit/db"
    assert resolve_redis_url() == "redis://explicit:6379/0"

    # Stdlib fallback loader when python-dotenv is absent
    import orcia_core.config as config_mod

    fallback_env = tmp_path / ".env.fallback"
    fallback_env.write_text(
        "# comment line\n"
        "\n"
        "INVALID_LINE_WITHOUT_EQUALS\n"
        "export ORCIA_WEB_PORT='3199'\n"
        'ORCIA_API_HOST="0.0.0.0"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(config_mod, "_dotenv_load", None)
    monkeypatch.delenv("ORCIA_WEB_PORT", raising=False)
    load_orcia_env(env_file=fallback_env, override=True)
    assert get_env_int("ORCIA_WEB_PORT", 3100) == 3199
    assert get_env("ORCIA_API_HOST") == "0.0.0.0"
