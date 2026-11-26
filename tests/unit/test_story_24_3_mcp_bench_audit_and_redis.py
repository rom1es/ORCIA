"""Layer 1a unit tests for Story 24.3 (MCP Bench, Audit Ledger, Redis Speed-2, Packs & wfKey)."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_connectors.protocol import ConnectorHealthStatus
from orcia_core.audit_finops.outbox_subscriber import (
    AUDITABLE_EVENT_TYPES,
    AuditLedgerOutboxSubscriber,
    _build_event_summary,
    map_domain_event_to_ledger_entry,
)
from orcia_core.kernel.events import DomainEvent
from orcia_core.orchestration._internal.sql_mcp_exposure import (
    SqlMcpExposureRepository,
    _parse_str_tuple,
    _row_to_spec,
)
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)
from orcia_core.orchestration.governed_mcp_exposure import GovernedMcpExposureService
from orcia_core.orchestration.models import WorkflowAsCodeDefinition, WorkflowStepSpec
from orcia_core.orchestration.remote_test_bench import (
    RemoteServiceTestBenchService,
    check_remote_endpoint_anti_ssrf,
    is_safe_llm_endpoint_url,
)
from orcia_core.orchestration.remote_test_bench_and_mcp_exposure import (
    RemoteServiceTestBenchAndGovernedMcpService,
)
from orcia_core.orchestration.remote_test_bench_models import ExposedMcpAgentSpec
from orcia_core.orchestration.run_lock_service import WorkflowOrchestrationSetupService
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)
from orcia_core.rag._speed2_redis_cache import (
    SPEED2_REDIS_TTL_SECONDS,
    deserialize_speed2_hits,
    get_speed2_cached_async,
    get_speed2_cached_sync,
    serialize_speed2_hits,
    set_speed2_cached_async,
    set_speed2_cached_sync,
)
from orcia_core.rag.two_speed_search import (
    FederatedSearchCandidate,
    FederatedSearchHit,
    TwoSpeedFederatedSearchService,
    build_speed2_redis_cache_key,
)


class _FakeAsyncRedis:
    """In-memory async Redis stub recording `ex` TTLs and exact keys."""

    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}
        self.get_calls: list[str] = []
        self.set_calls: list[tuple[str, int | None]] = []

    async def get(self, key: str) -> bytes | None:
        self.get_calls.append(key)
        return self.store.get(key)

    async def set(self, key: str, value: str | bytes, ex: int | None = None) -> bool:
        self.set_calls.append((key, ex))
        self.store[key] = value.encode("utf-8") if isinstance(value, str) else value
        if ex is not None:
            self.ttls[key] = ex
        return True


class _FakeSyncRedis:
    """In-memory sync Redis stub recording `ex` TTLs and exact keys."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int | None] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.store[key] = value
        self.ttls[key] = ex
        return True


class _FakeMcpRepo:
    """In-memory implementation of `McpExposureRepositoryPort` verifying SHA-256 PAT storage."""

    def __init__(self) -> None:
        self.agents: dict[tuple[str, str], ExposedMcpAgentSpec] = {}
        self.pat_hashes: dict[str, set[str]] = {}

    async def upsert_exposed_agent(
        self, spec: ExposedMcpAgentSpec, *, updated_by: str | None = None
    ) -> ExposedMcpAgentSpec:
        _ = updated_by
        self.agents[(spec.workspace_slug, spec.agent_slug)] = spec
        return spec

    async def list_exposed_agents(self, workspace_slug: str) -> list[ExposedMcpAgentSpec]:
        return [s for (ws, _), s in sorted(self.agents.items()) if ws == workspace_slug]

    async def get_exposed_agent(
        self, workspace_slug: str, agent_slug: str
    ) -> ExposedMcpAgentSpec | None:
        return self.agents.get((workspace_slug, agent_slug))

    async def upsert_pat_token_hash(
        self, *, token_sha256: str, allowed_workspace_slugs: set[str]
    ) -> None:
        self.pat_hashes[token_sha256] = set(allowed_workspace_slugs)

    async def get_pat_allowed_workspaces(self, token_sha256: str) -> set[str] | None:
        return self.pat_hashes.get(token_sha256)


@pytest.mark.parametrize(
    ("url", "allow_private", "expected"),
    [
        ("http://169.254.169.254/latest/meta-data", False, False),
        ("http://169.254.169.254/latest/meta-data", True, False),
        ("http://[fe80::1]/metadata", False, False),
        ("http://[fe80::1]/metadata", True, False),
        ("http://metadata.google.internal/computeMetadata/v1/", False, False),
        ("http://metadata.google.internal/computeMetadata/v1/", True, False),
        ("https://sub.google.internal/secret", True, False),
        ("http://100.100.100.200/latest/meta-data", True, False),
        ("http://localhost:8000/api", False, False),
        ("http://localhost:8000/api", True, True),
        ("http://10.0.0.15:8080/mcp", False, False),
        ("http://10.0.0.15:8080/mcp", True, True),
        ("http://0.0.0.0:8000", True, False),
        ("http://224.0.0.1/stream", True, False),
        ("https://user:pass@mcp.partner.io/sse", True, False),  # pragma: allowlist secret
        ("ftp://mcp.partner.io/file", True, False),
        ("", False, False),
        ("https://mcp.partner.io/sse", False, True),
    ],
)
def test_is_safe_llm_endpoint_url_ssrf_matrix(
    url: str, allow_private: bool, expected: bool
) -> None:
    """Verify link-local, metadata, loopback, userinfo, and scheme SSRF defenses."""
    assert is_safe_llm_endpoint_url(url, allow_private_network=allow_private) is expected


def test_remote_service_test_bench_steps_and_edge_cases() -> None:
    """Verify `RemoteServiceTestBenchService` across WASM, Observer, Auth, Discovery & Dry-Run."""
    bench = RemoteServiceTestBenchService()

    with pytest.raises(ObserverModeReadOnlyError):
        bench.test_and_discover_remote_service(
            actor_role="READ_ONLY_OBSERVER",
            protocol="MCP_STREAMABLE_HTTP_SSE",
            endpoint_url="https://mcp.partner.io/sse",
            identity_mode="SECRET_REF",
        )

    wasm_ok, wasm_msg = check_remote_endpoint_anti_ssrf(
        endpoint_url="orcia://wasm/local-validator",
        protocol="WASM_SANDBOX",
        allow_private_network=False,
    )
    assert wasm_ok is True
    assert "WASM" in wasm_msg

    bad_scheme_ok, _ = check_remote_endpoint_anti_ssrf(
        endpoint_url="file:///etc/passwd",
        protocol="MCP_STREAMABLE_HTTP_SSE",
        allow_private_network=True,
    )
    assert bad_scheme_ok is False

    bad_secret_res = bench.test_and_discover_remote_service(
        actor_role="PLATFORM_ADMIN",
        protocol="OPENAPI_3_1_REST",
        endpoint_url="https://api.partner.io/spec.json",
        identity_mode="SECRET_REF",
        secret_ref_valid=False,
    )
    assert bad_secret_res.steps[1].status == "FAIL"
    assert bad_secret_res.steps[2].status == "SKIPPED"
    assert bad_secret_res.can_activate is False

    empty_tools_res = bench.test_and_discover_remote_service(
        actor_role="PLATFORM_ADMIN",
        protocol="MCP_STREAMABLE_HTTP_SSE",
        endpoint_url="https://mcp.partner.io/sse",
        identity_mode="SECRET_REF",
        secret_ref_valid=True,
        raw_tool_names=[],
    )
    assert empty_tools_res.steps[2].status == "FAIL"
    assert empty_tools_res.can_activate is False

    oversized_res = bench.test_and_discover_remote_service(
        actor_role="PLATFORM_ADMIN",
        protocol="MCP_STREAMABLE_HTTP_SSE",
        endpoint_url="https://mcp.partner.io/sse",
        identity_mode="SECRET_REF",
        secret_ref_valid=True,
        simulated_dry_run_bytes=2_000_000,
    )
    assert oversized_res.steps[3].status == "FAIL"
    assert oversized_res.can_activate is False


@pytest.mark.asyncio
async def test_governed_mcp_exposure_strict_sql_fail_closed_and_sha256_pat() -> None:
    """Verify `strict_sql=True` fails closed without PG18 repo and hashes PATs via SHA-256."""
    strict_svc = GovernedMcpExposureService(repository=None, strict_sql=True)

    with pytest.raises(ValidationDomainError, match="strict_sql=True"):
        strict_svc.register_pat_mcp_token(
            raw_pat_token="pat_mcp_no_repo_01",  # pragma: allowlist secret
            allowed_workspace_slugs={"ws-alpha"},
        )

    with pytest.raises(ValidationDomainError, match="strict_sql=True"):
        await strict_svc.register_pat_mcp_token_async(
            raw_pat_token="pat_mcp_no_repo_01",  # pragma: allowlist secret
            allowed_workspace_slugs={"ws-alpha"},
        )

    with pytest.raises(ValidationDomainError, match="strict_sql=True"):
        strict_svc.configure_agent_mcp_exposure(
            actor_role="TEAM_LEAD",
            workspace_slug="ws-alpha",
            agent_slug="agent-1",
            display_name="Agent 1",
            mcp_exposed=True,
            regime="GOVERNED_STAGED_COPILOT",
        )

    with pytest.raises(ValidationDomainError, match="strict_sql=True"):
        await strict_svc.list_exposed_agents_async(workspace_slug="ws-alpha")

    # Attach PG18 repository dynamically via Facade.set_repository
    fake_repo = _FakeMcpRepo()
    facade = RemoteServiceTestBenchAndGovernedMcpService(strict_sql=True)
    facade.set_repository(fake_repo, strict_sql=True)

    raw_pat = "pat_mcp_secret_24_3_token"  # pragma: allowlist secret
    expected_sha256 = hashlib.sha256(raw_pat.encode("utf-8")).hexdigest()
    returned_hash = await facade.register_pat_mcp_token_async(
        raw_pat_token=raw_pat,
        allowed_workspace_slugs={"ws-alpha"},
    )
    assert returned_hash == expected_sha256
    assert expected_sha256 in fake_repo.pat_hashes
    assert raw_pat not in json.dumps({k: sorted(v) for k, v in fake_repo.pat_hashes.items()})

    spec = await facade.configure_agent_mcp_exposure_async(
        actor_role="TEAM_LEAD",
        workspace_slug="ws-alpha",
        agent_slug="spec-agent",
        display_name="Agent Spec",
        mcp_exposed=True,
        regime="GOVERNED_STAGED_COPILOT",
        updated_by="admin-1",
    )
    assert spec.mcp_exposed is True
    tools = await facade.list_governed_mcp_tools_async(
        workspace_slug="ws-alpha",
        caller_verbs={"execute"},
    )
    assert "agent.spec-agent" in tools
    assert (
        await facade.list_governed_mcp_tools_async(workspace_slug="ws-alpha", caller_verbs={"read"})
        == ()
    )

    invoked = await facade.invoke_governed_mcp_tool_async(
        raw_pat_token=raw_pat,
        workspace_slug="ws-alpha",
        agent_slug="spec-agent",
        caller_role="CONTRIBUTOR",
        caller_verbs={"execute", "read"},
        passthrough_identity="oidc:alice@orcia.io",
        prompt_text="Analyse IBAN_SECRET",
    )
    assert invoked.system_prompt_exposed is not None
    assert "[REDACTED_PII]" in invoked.sanitized_response_text

    with pytest.raises(ScopeAccessDeniedError, match="prefix"):
        await facade.invoke_governed_mcp_tool_async(
            raw_pat_token="invalid_prefix_tok",  # pragma: allowlist secret
            workspace_slug="ws-alpha",
            agent_slug="spec-agent",
            caller_role="CONTRIBUTOR",
            caller_verbs={"execute"},
            passthrough_identity="oidc:alice@orcia.io",
            prompt_text="Ping",
        )

    # Sync register_pat_mcp_token blocked when strict_sql=True and repo is attached
    with pytest.raises(ValidationDomainError, match="register_pat_mcp_token_async"):
        facade.register_pat_mcp_token(
            raw_pat_token=raw_pat,
            allowed_workspace_slugs={"ws-alpha"},
        )

    # Sync invoke invalid prefix
    sync_svc = GovernedMcpExposureService(strict_sql=False)
    with pytest.raises(ScopeAccessDeniedError, match="prefix"):
        sync_svc.invoke_governed_mcp_tool(
            raw_pat_token="bad_prefix",  # pragma: allowlist secret
            workspace_slug="ws-alpha",
            agent_slug="spec-agent",
            caller_role="CONTRIBUTOR",
            caller_verbs={"execute"},
            passthrough_identity="oidc:alice@orcia.io",
            prompt_text="Ping",
        )

    # Async observer, unauthorized workspace, missing passthrough, missing execute, unexposed agent
    with pytest.raises(ObserverModeReadOnlyError):
        await facade.invoke_governed_mcp_tool_async(
            raw_pat_token=raw_pat,
            workspace_slug="ws-alpha",
            agent_slug="spec-agent",
            caller_role="READ_ONLY_OBSERVER",
            caller_verbs={"execute"},
            passthrough_identity="oidc:obs@orcia.io",
            prompt_text="Ping",
        )

    with pytest.raises(ScopeAccessDeniedError, match="not authorized"):
        await facade.invoke_governed_mcp_tool_async(
            raw_pat_token=raw_pat,
            workspace_slug="other-ws",
            agent_slug="spec-agent",
            caller_role="CONTRIBUTOR",
            caller_verbs={"execute"},
            passthrough_identity="oidc:alice@orcia.io",
            prompt_text="Ping",
        )

    with pytest.raises(ValidationDomainError, match="Passthrough"):
        await facade.invoke_governed_mcp_tool_async(
            raw_pat_token=raw_pat,
            workspace_slug="ws-alpha",
            agent_slug="spec-agent",
            caller_role="CONTRIBUTOR",
            caller_verbs={"execute"},
            passthrough_identity="   ",
            prompt_text="Ping",
        )

    with pytest.raises(ScopeAccessDeniedError, match="execute"):
        await facade.invoke_governed_mcp_tool_async(
            raw_pat_token=raw_pat,
            workspace_slug="ws-alpha",
            agent_slug="spec-agent",
            caller_role="CONTRIBUTOR",
            caller_verbs={"read"},
            passthrough_identity="oidc:alice@orcia.io",
            prompt_text="Ping",
        )

    with pytest.raises(ValidationDomainError, match="not exposed"):
        await facade.invoke_governed_mcp_tool_async(
            raw_pat_token=raw_pat,
            workspace_slug="ws-alpha",
            agent_slug="unknown-agent",
            caller_role="CONTRIBUTOR",
            caller_verbs={"execute"},
            passthrough_identity="oidc:alice@orcia.io",
            prompt_text="Ping",
        )


def test_sql_mcp_exposure_helpers_and_unconfigured_repo() -> None:
    """Verify `_parse_str_tuple`, `_row_to_spec`, and RuntimeError when session_maker absent."""
    assert _parse_str_tuple('["ws-a", "ws-b"]') == ("ws-a", "ws-b")
    assert _parse_str_tuple(["ws-c"]) == ("ws-c",)
    assert _parse_str_tuple(None) == ()

    spec = _row_to_spec(
        {  # type: ignore[arg-type]
            "agent_slug": "a1",
            "workspace_slug": "ws-1",
            "display_name": "Agent One",
            "mcp_exposed": 1,
            "regime": "UNKNOWN_FALLBACK",
            "system_prompt_layers_1_to_4": None,
            "secret_refs_jsonb": '["vault://x"]',
            "human_authored_required": 0,
        }
    )
    assert spec.regime == "CONSULTATION_ANALYSIS"
    assert spec.secret_refs == ("vault://x",)

    repo = SqlMcpExposureRepository()
    with pytest.raises(RuntimeError, match="PG18 engine/session"):
        repo._require_session_maker()


@pytest.mark.asyncio
async def test_outbox_subscriber_admin_connection_test_event_contract() -> None:
    """Verify `ADMIN_CONNECTION_TEST` event type is auditable, scrubbed, and mapped properly."""
    assert "ADMIN_CONNECTION_TEST" in AUDITABLE_EVENT_TYPES
    mock_sink = AsyncMock()
    mock_sink.record_entry.return_value = "ledger-24-3-id"
    subscriber = AuditLedgerOutboxSubscriber(sink=mock_sink)

    evt = DomainEvent(
        event_id=str(uuid.uuid4()),
        event_type="ADMIN_CONNECTION_TEST",
        aggregate_type="connector",
        aggregate_id="https://mcp.partner.io/sse",
        run_id=None,
        workspace_id="ws-root",
        payload={
            "target_type": "MCP_CONNECTOR",
            "target_id": "https://mcp.partner.io/sse",
            "test_status": "SUCCESS",
            "api_key": "sk-never-leak-24-3",  # pragma: allowlist secret
            "latency_ms": 42,
        },
        trace_id="0" * 32,
    )
    summary = _build_event_summary(evt)
    assert "MCP_CONNECTOR" in summary
    assert "SUCCESS" in summary

    entry = map_domain_event_to_ledger_entry(evt)
    assert entry.event_type == "ADMIN_CONNECTION_TEST"
    assert entry.actor_type == "ADMIN_CONNECTION_TEST"
    assert entry.metadata["api_key"] == "[REDACTED_SECRET]"

    recorded_id = await subscriber.on_domain_event(evt)
    assert recorded_id == "ledger-24-3-id"
    assert mock_sink.record_entry.call_count == 1


@pytest.mark.asyncio
async def test_speed2_redis_cache_key_isolation_and_ttl_300s() -> None:
    """Verify Speed-2 Redis keys isolate 6 context dimensions and enforce `TTL = 300s`."""
    assert SPEED2_REDIS_TTL_SECONDS == 300

    base = build_speed2_redis_cache_key(
        "ws-1",
        "architecture paiement sepa",
        user_id="user-1",
        user_role="CONTRIBUTOR",
        scope="WORKSPACE",
        active_screen_route="/cockpit",
        locale="fr",
    )
    variants = [
        build_speed2_redis_cache_key(
            "ws-1",
            "architecture paiement sepa",
            user_id="user-2",
            user_role="CONTRIBUTOR",
            scope="WORKSPACE",
            active_screen_route="/cockpit",
            locale="fr",
        ),
        build_speed2_redis_cache_key(
            "ws-1",
            "architecture paiement sepa",
            user_id="user-1",
            user_role="PLATFORM_ADMIN",
            scope="WORKSPACE",
            active_screen_route="/cockpit",
            locale="fr",
        ),
        build_speed2_redis_cache_key(
            "ws-2",
            "architecture paiement sepa",
            user_id="user-1",
            user_role="CONTRIBUTOR",
            scope="WORKSPACE",
            active_screen_route="/cockpit",
            locale="fr",
        ),
        build_speed2_redis_cache_key(
            "ws-1",
            "architecture paiement sepa",
            user_id="user-1",
            user_role="CONTRIBUTOR",
            scope="ALL_WORKSPACES",
            active_screen_route="/cockpit",
            locale="fr",
        ),
        build_speed2_redis_cache_key(
            "ws-1",
            "architecture paiement sepa",
            user_id="user-1",
            user_role="CONTRIBUTOR",
            scope="WORKSPACE",
            active_screen_route="/spaces",
            locale="fr",
        ),
        build_speed2_redis_cache_key(
            "ws-1",
            "architecture paiement sepa",
            user_id="user-1",
            user_role="CONTRIBUTOR",
            scope="WORKSPACE",
            active_screen_route="/cockpit",
            locale="en",
        ),
    ]
    assert len({base, *variants}) == 7

    fake_async_redis = _FakeAsyncRedis()
    svc = TwoSpeedFederatedSearchService(
        candidates=(
            FederatedSearchCandidate(
                item_id="cand-sem-1",
                family="SOURCES_SNIPPETS",
                title="Mécanisme de compensation SEPA",
                snippet="Règlement interbancaire instantané.",
                workspace_id="ws-1",
                screen_route="/cockpit",
                deep_link_uri="/spaces#cand-sem-1",
                allowed_roles=("CONTRIBUTOR", "PLATFORM_ADMIN"),
                embedding=tuple([0.2] * 16),
            ),
        ),
        redis_client=fake_async_redis,
    )

    miss_res = await svc.execute_search_async(
        query="compensation interbancaire instantanée",
        scope="WORKSPACE",
        active_workspace_id="ws-1",
        active_screen_route="/cockpit",
        user_id="user-1",
        user_role="CONTRIBUTOR",
        locale="fr",
        query_embedding=tuple([0.2] * 16),
    )
    assert miss_res.speed2_executed is True
    assert miss_res.speed2_cache_hit is False
    assert miss_res.speed2_cache_ttl_seconds == 300
    assert miss_res.speed2_redis_key == build_speed2_redis_cache_key(
        "ws-1",
        "compensation interbancaire instantanée",
        user_id="user-1",
        user_role="CONTRIBUTOR",
        scope="WORKSPACE",
        active_screen_route="/cockpit",
        locale="fr",
    )
    assert fake_async_redis.ttls[miss_res.speed2_redis_key] == 300

    # Same user/role/locale hits cache
    hit_res = await svc.execute_search_async(
        query="compensation interbancaire instantanée",
        scope="WORKSPACE",
        active_workspace_id="ws-1",
        active_screen_route="/cockpit",
        user_id="user-1",
        user_role="CONTRIBUTOR",
        locale="fr",
        query_embedding=tuple([0.2] * 16),
    )
    assert hit_res.speed2_cache_hit is True

    # Different user MUST miss cache (zero cross-user leakage)
    other_user_res = await svc.execute_search_async(
        query="compensation interbancaire instantanée",
        scope="WORKSPACE",
        active_workspace_id="ws-1",
        active_screen_route="/cockpit",
        user_id="user-2",
        user_role="CONTRIBUTOR",
        locale="fr",
        query_embedding=tuple([0.2] * 16),
    )
    assert other_user_res.speed2_cache_hit is False
    assert other_user_res.speed2_redis_key != miss_res.speed2_redis_key

    # Sync Redis helper roundtrip & resilience checks
    fake_sync_redis = _FakeSyncRedis()
    hit_tuple = (
        FederatedSearchHit(
            item_id="h1",
            family="SOURCES_SNIPPETS",
            title="Titre",
            snippet="Extrait",
            workspace_id="ws-1",
            screen_route="/cockpit",
            deep_link_uri="/cockpit#h1",
            speed_tier=2,
            locked_top=False,
            score=0.91,
        ),
    )
    set_speed2_cached_sync(fake_sync_redis, "k-sync", hit_tuple)
    assert fake_sync_redis.ttls["k-sync"] == 300
    loaded_sync = get_speed2_cached_sync(fake_sync_redis, "k-sync", FederatedSearchHit)
    assert loaded_sync is not None and loaded_sync[0].item_id == "h1"

    assert deserialize_speed2_hits(None, FederatedSearchHit) is None
    assert deserialize_speed2_hits('{"not": "list"}', FederatedSearchHit) is None
    assert serialize_speed2_hits(hit_tuple).startswith("[")
    assert await get_speed2_cached_async(None, "k", FederatedSearchHit) is None
    await set_speed2_cached_async(None, "k", hit_tuple)


def test_packs_health_endpoint_healthy_degraded_and_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `GET /api/v1/packs/health` computes healthy/degraded counts accurately."""
    import orcia_api.routers.packs as packs_router

    app = create_app()

    async def _mock_pg_bundles(_repo: Any) -> list[dict[str, object]]:
        return [
            {
                "id": "0195f000-0000-7000-8000-000000000011",
                "pack_id": "orcia-pack-sdlc",
                "slug": "sdlc",
                "name": "SDLC",
                "version": "2.4.0",
                "declared_slots": [
                    {
                        "slot_key": "jira-tracker",
                        "scheme": "jira",
                        "connector_kind": "mcp:atlassian-jira",
                        "required_access": ["read"],
                    },
                    {
                        "slot_key": "git-repo",
                        "scheme": "git",
                        "connector_kind": "mcp:git-provider",
                        "required_access": ["read"],
                    },
                ],
                "manifest": {},
            }
        ]

    monkeypatch.setattr(packs_router, "_list_pg_bundles", _mock_pg_bundles)
    client = TestClient(app)

    # Default healthy state
    resp_ok = client.get("/api/v1/packs/health")
    assert resp_ok.status_code == 200
    data_ok = resp_ok.json()
    assert data_ok["total_count"] >= 1
    assert data_ok["healthy_count"] == data_ok["total_count"]
    assert data_ok["all_healthy"] is True

    # Degraded state when one connector fails healthcheck & another is missing
    class _DegradedConnector:
        async def healthcheck(self) -> ConnectorHealthStatus:
            return ConnectorHealthStatus(
                connector_type="mcp:atlassian-jira",
                ok=False,
                latency_ms=12,
                error_message="Jira unreachable",
            )

    class _HealthyConnector:
        async def healthcheck(self) -> ConnectorHealthStatus:
            return ConnectorHealthStatus(
                connector_type="mcp:git-provider",
                ok=True,
                latency_ms=4,
                error_message=None,
            )

    def _mock_adapters() -> dict[str, Any]:
        return {
            "mcp:atlassian-jira": _DegradedConnector(),
            "mcp:git-provider": _HealthyConnector(),
        }

    monkeypatch.setattr(packs_router, "get_default_enterprise_connectors", _mock_adapters)
    resp_deg = client.get("/api/v1/packs/health")
    assert resp_deg.status_code == 200
    data_deg = resp_deg.json()
    assert data_deg["all_healthy"] is False
    assert data_deg["healthy_count"] < data_deg["total_count"]
    jira_item = next(
        c for c in data_deg["connectors"] if c["connector_type"] == "mcp:atlassian-jira"
    )
    assert jira_item["health"]["ok"] is False
    assert jira_item["health"]["error_message"] == "Jira unreachable"

    # Disabled connector in PG18 overrides adapter check
    from datetime import UTC, datetime

    from orcia_core.permissions.enterprise_connectors import (
        ConnectorSecretStatus,
        EnterpriseConnectorRecord,
    )

    async def _mock_pg_connectors(_req: Any) -> dict[str, EnterpriseConnectorRecord]:
        now_iso = datetime.now(UTC).isoformat()
        return {
            "jira": EnterpriseConnectorRecord(
                id="0195f000-0000-7000-8000-000000000777",
                connector_kind="JIRA",
                name="Jira Entreprise",
                base_url="https://jira.internal",
                auth_mode="PERSONAL_ACCESS_TOKEN",
                enabled=False,
                admin_secret_status=ConnectorSecretStatus(configured=False),
                created_at_iso=now_iso,
                updated_at_iso=now_iso,
            )
        }

    monkeypatch.setattr(packs_router, "_load_pg_connectors_by_kind", _mock_pg_connectors)
    resp_disabled = client.get("/api/v1/packs/health")
    assert resp_disabled.status_code == 200
    disabled_jira = next(
        c for c in resp_disabled.json()["connectors"] if c["connector_type"] == "mcp:atlassian-jira"
    )
    assert disabled_jira["health"]["ok"] is False
    assert "désactivé" in str(disabled_jira["health"]["error_message"])

    # Also verify GET /api/v1/packs and POST /api/v1/packs/export/{workspace_id}
    resp_list = client.get("/api/v1/packs")
    assert resp_list.status_code == 200
    assert len(resp_list.json()["packs"]) >= 1

    resp_export = client.post("/api/v1/packs/export/ws-story-24-3")
    assert resp_export.status_code == 200
    assert resp_export.headers["content-type"] == "application/zip"


def test_run_lock_service_resolves_real_wf_key_and_assistant_agent_alias() -> None:
    """Verify `instantiate_workflow_run` uses the selected `wfKey` URI & `assistant-agent`."""
    org_id = "0195f000-0000-7000-8000-000000000101"
    ws_id = "0195f000-0000-7000-8000-000000000301"
    user_id = "0195f000-0000-7000-8000-000000000201"
    org = OrgUnitNode(id=org_id, slug="eng", name="Engineering", unit_type="TEAM")
    ws = WorkspaceEntity(
        id=ws_id,
        slug="ws-cockpit",
        name="Cockpit WS",
        owner_org_unit_id=org_id,
    )
    user = UserIdentity(
        id=user_id,
        email="lead@orcia.test",
        display_name="Lead",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id=org_id,
    )
    membership = WorkspaceMembershipEntity(
        id="0195f000-0000-7000-8000-000000000401",
        workspace_id=ws_id,
        role="TEAM_LEAD",
        access_mode="CONTRIBUTOR_ACTION_REQUIRED",
        user_id=user_id,
    )
    evaluator = MatrixPermissionEvaluator(
        org_units=(org,), workspaces=(ws,), memberships=(membership,)
    )

    def _wf(wf_id: str, uri: str, title: str) -> WorkflowAsCodeDefinition:
        return WorkflowAsCodeDefinition(
            id=wf_id,
            workspace_id=ws_id,
            uri=uri,
            title=title,
            description="Test workflow",
            version="1.0.0",
            criticality="STANDARD",
            execution_regime="HUMAN_LED",
            tie_break_policy="ALWAYS_ASK_HUMAN",
            mode="standard",
            adaptive_gate_policy="STANDARD",
            max_cost_usd=5.0,
            scalars={},
            datasources=(),
            rules=(),
            facts=(),
            steps=(
                WorkflowStepSpec(
                    step_key="step-1",
                    title="Step 1",
                    step_type="AGENT",
                    instructions="Analyze",
                ),
            ),
            sha256="a" * 64,
        )

    wf_default = _wf(
        "wf-claims",
        "orcia://workflows/claims-engineering-delivery",
        "Claims Delivery",
    )
    wf_custom = _wf(
        "wf-custom",
        "orcia://workflows/incident-triage",
        "Incident Triage",
    )

    svc = WorkflowOrchestrationSetupService(
        evaluator=evaluator,
        workflows=(wf_default, wf_custom),
    )

    # Real wfKey selected in Cockpit resolves to wf_custom (not hardcoded claims-engineering)
    run_custom = svc.instantiate_workflow_run(
        user,
        workflow_uri="orcia://workflows/incident-triage",
        workspace_id=ws_id,
    )
    assert run_custom.workflow_uri == "orcia://workflows/incident-triage"
    assert run_custom.workflow_def_id == "wf-custom"

    # assistant-agent alias resolves cleanly without 404
    run_assistant = svc.instantiate_workflow_run(
        user,
        workflow_uri="orcia://system/workflows/assistant-agent",
        workspace_id=ws_id,
    )
    assert run_assistant.workflow_def_id == "wf-claims"

    with pytest.raises(ResourceNotFoundError):
        svc.instantiate_workflow_run(
            user,
            workflow_uri="orcia://workflows/nonexistent-wf",
            workspace_id=ws_id,
        )
