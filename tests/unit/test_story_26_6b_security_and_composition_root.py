"""Comprehensive Security, Composition Root & Branch Coverage Tests (`Story 26.6b`)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI, Request

from orcia_api.dependencies import (
    build_assistant_tool_catalog_context_async,
    get_assistant_reflexive_runtime_service,
    get_governed_assistant_tool_router,
    get_reflexive_runtime_service,
    get_surgical_explorer_service,
)
from orcia_api.dependencies._assistant_tools_helpers import (
    build_tool_execution_callbacks,
    collect_authorized_mcp_specs,
)
from orcia_api.routers._assistant_tool_loop_rounds import (
    build_approval_proposal_text,
    execute_sync_tool_followup,
    granted_roles_for_tool_call,
)
from orcia_api.routers._assistant_turn_producer import execute_turn_producer_task
from orcia_core.agents import (
    NonDeterministicReflexiveRuntime,
    ReflexiveRuntimeConfig,
    ReflexiveTurnDecision,
    ReflexiveTurnInput,
)
from orcia_core.agents._assistant_tool_audit import (
    _parse_optional_uuid,
    enqueue_arbitration_outbox_event,
)
from orcia_core.agents._assistant_tool_execution import (
    ToolDispatchDependencies,
    _execute_surgical_tool,
    execute_with_timeout,
)
from orcia_core.agents._assistant_tool_guards import evaluate_permission_broker_step
from orcia_core.agents._runtime_helpers import (
    assert_snapshot_not_expired,
    build_child_delegation_config,
    build_scratchpad_entry_from_observation,
)
from orcia_core.agents.errors import ReflexiveSessionExpiredError, ResourceNotFoundError
from orcia_core.agents.reflexive_schemas import ReflexiveSessionSnapshot
from orcia_core.ontology import OntologyConceptEntity, OntologyGovernanceService
from orcia_core.orchestration.agents_and_skills_manager import AgentsAndSkillsManagementService
from orcia_core.orchestration.redis_rate_limiter import RedisAssistantRateLimiter
from orcia_core.orchestration.redis_turn_registry import RedisAssistantTurnRegistry
from orcia_core.orchestration.remote_test_bench_and_mcp_exposure import (
    RemoteServiceTestBenchAndGovernedMcpService,
)
from orcia_core.permissions import build_default_auth_and_org_service
from orcia_core.permissions.models import (
    CatalogAclEntry,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolExecutionRequest,
    AuthorizedToolDescriptor,
)
from orcia_core.ports.assistant_turn_stream_port import AssistantTurnRecord
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.ports.llm_streaming_port import (
    Finish,
    LlmChatTurnOutcome,
    LlmEndpointConfig,
    LlmStreamingPort,
    LlmStreamRequest,
    ToolCallDelta,
    typed_event_to_delta,
)
from orcia_core.ports.reflexive_runtime_ports import (
    ReflexiveEventStreamPort,
    ReflexiveLlmPort,
    ReflexiveSessionStorePort,
)
from orcia_core.ports.surgical_explorer_port import (
    SurgicalExplorerPort,
    SurgicalObservation,
    SurgicalOutlineNode,
    SurgicalPrimitiveName,
    SurgicalSnippetMatch,
)
from orcia_core.rag.models import HybridRagHit


def _make_request(app: FastAPI) -> Request:
    return Request({"type": "http", "headers": [], "app": app, "path": "/api/v1/test"})


def _build_test_app_and_users() -> tuple[FastAPI, Any, UserIdentity, UserIdentity, WorkspaceEntity]:
    app = FastAPI()
    auth_svc = build_default_auth_and_org_service()
    ws = WorkspaceEntity(
        id="0192c4e0-0000-7000-8000-000000009901",
        slug="ws-alpha",
        name="Workspace Alpha",
        owner_org_unit_id=auth_svc.evaluator.org_units[0].id,
        visibility_mode="STANDARD",
    )
    ws_other = WorkspaceEntity(
        id="0192c4e0-0000-7000-8000-000000009902",
        slug="ws-beta",
        name="Workspace Beta",
        owner_org_unit_id=auth_svc.evaluator.org_units[0].id,
        visibility_mode="STANDARD",
    )
    auth_svc.evaluator.upsert_workspace(ws)
    auth_svc.evaluator.upsert_workspace(ws_other)

    contrib = UserIdentity(
        id="0192c4e0-0000-7000-8000-000000009911",
        email="contrib@orcia.local",
        display_name="Contrib Alpha",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id=auth_svc.evaluator.org_units[0].id,
    )
    observer = UserIdentity(
        id="0192c4e0-0000-7000-8000-000000009912",
        email="obs@orcia.local",
        display_name="Observer Alpha",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="OBSERVER",
        primary_org_unit_id=auth_svc.evaluator.org_units[0].id,
    )
    for user in (contrib, observer):
        auth_svc._users_by_id[user.id] = user
        auth_svc._users_by_email[user.email.lower()] = user
    auth_svc.evaluator.upsert_membership(
        WorkspaceMembershipEntity(
            id="mem-alpha-contrib",
            workspace_id=ws.id,
            user_id=contrib.id,
            role="CONTRIBUTOR",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
        )
    )
    auth_svc.evaluator.upsert_membership(
        WorkspaceMembershipEntity(
            id="mem-alpha-obs",
            workspace_id=ws.id,
            user_id=observer.id,
            role="OBSERVER",
            access_mode="READ_ONLY_OBSERVER",
        )
    )
    app.state.auth_service = auth_svc
    app.state.agents_and_skills_service = AgentsAndSkillsManagementService()
    app.state.remote_test_bench_and_mcp_service = RemoteServiceTestBenchAndGovernedMcpService()
    return app, auth_svc, contrib, observer, ws


def test_p0_authorize_read_source_and_rag_acl_surgical_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, auth_svc, contrib, observer, ws = _build_test_app_and_users()
    auth_svc.evaluator._catalog_acls = (
        *auth_svc.evaluator._catalog_acls,
        CatalogAclEntry(
            id="acl-masked-p0",
            resource_id="res-masked-p0",
            resource_uri="git://repo/masked.py",
            title="Masked",
            visibility_scope="SHARED_WORKSPACE",
            owner_org_unit_id=ws.owner_org_unit_id,
            owner_workspace_id=ws.id,
            can_discover=True,
            can_execute=True,
            can_read_source=False,
        ),
        CatalogAclEntry(
            id="acl-open-p0",
            resource_id="res-open-p0",
            resource_uri="git://repo/open.py",
            title="Open",
            visibility_scope="SHARED_WORKSPACE",
            owner_org_unit_id=ws.owner_org_unit_id,
            owner_workspace_id=ws.id,
            can_discover=True,
            can_execute=True,
            can_read_source=True,
        ),
    )
    req = _make_request(app)
    explorer: Any = get_surgical_explorer_service(req)
    auth_fn = explorer._read_source_authorizer
    assert auth_fn("git://repo/open.py", ws.id, None)[0] is False
    assert auth_fn("git://repo/open.py", ws.id, "u-anonymous")[0] is False
    assert auth_fn("git://repo/open.py", ws.id, "missing-actor")[0] is False
    assert auth_fn("git://repo/open.py", ws.id, observer.id)[0] is False
    assert auth_fn("git://repo/masked.py", ws.id, contrib.id)[0] is False
    assert auth_fn("git://repo/open.py", "ws-nonexistent", contrib.id)[0] is False
    assert auth_fn("git://repo/open.py", ws.id, contrib.id) == (True, None)

    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    app.state.llm_gateway = object()
    asst_rt = get_assistant_reflexive_runtime_service(req)
    proc_rt = get_reflexive_runtime_service(req)
    assert isinstance(asst_rt, NonDeterministicReflexiveRuntime)
    assert asst_rt._execution_profile == "ASSISTANT"
    assert asst_rt._write_gate is None
    assert proc_rt._execution_profile == "PROCESS"
    assert proc_rt._write_gate is not None


@pytest.mark.asyncio
async def test_p0_p1_rag_search_ontology_mcp_and_catalog_isolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, auth_svc, contrib, observer, ws = _build_test_app_and_users()
    auth_svc.evaluator._catalog_acls = (
        *auth_svc.evaluator._catalog_acls,
        CatalogAclEntry(
            id="acl-rag-denied",
            resource_id="res-rag-denied",
            resource_uri="git://org/secret-rag.md",
            title="Secret RAG",
            visibility_scope="SHARED_WORKSPACE",
            owner_org_unit_id=ws.owner_org_unit_id,
            owner_workspace_id=ws.id,
            can_discover=True,
            can_execute=True,
            can_read_source=False,
        ),
        CatalogAclEntry(
            id="acl-rag-ok",
            resource_id="res-rag-ok",
            resource_uri="git://org/public-rag.md",
            title="Public RAG",
            visibility_scope="SHARED_WORKSPACE",
            owner_org_unit_id=ws.owner_org_unit_id,
            owner_workspace_id=ws.id,
            can_discover=True,
            can_execute=True,
            can_read_source=True,
        ),
    )

    class _FakeEmb(EmbeddingPort):
        async def embed_query(self, text: str) -> tuple[float, ...]:
            del text
            return (0.1, 0.2)

        async def embed(self, texts: Any) -> list[list[float]]:
            return [[0.1, 0.2] for _ in texts]

    class _InMemoryRagStub:
        def __init__(self, _sm: Any) -> None:
            pass

        async def search_hybrid_rrf(self, **_kw: Any) -> list[HybridRagHit]:
            return [
                HybridRagHit(
                    chunk_key="c1",
                    parent_chunk_key="p1",
                    document_key="d1",
                    datasource_alias="repo",
                    source_uri="git://org/secret-rag.md",
                    revision_tag="main",
                    contextual_header="Secret",
                    injected_content="Secret payload",
                    bm25_rank=1,
                    vector_rank=1,
                    rrf_score=0.9,
                    is_stale=False,
                ),
                HybridRagHit(
                    chunk_key="c2",
                    parent_chunk_key="p2",
                    document_key="d2",
                    datasource_alias="repo",
                    source_uri="git://org/public-rag.md",
                    revision_tag="main",
                    contextual_header="Public",
                    injected_content="Public payload",
                    bm25_rank=2,
                    vector_rank=2,
                    rrf_score=0.8,
                    is_stale=False,
                ),
            ]

    ont_svc = OntologyGovernanceService(
        concepts=(
            OntologyConceptEntity(
                id="c-ent",
                concept_key="ent-key",
                canonical_term="Enterprise Principle",
                level="1_ENTERPRISE",
                scope_id="scope-global",
                definition_text="Global invariant",
            ),
            OntologyConceptEntity(
                id="c-alpha",
                concept_key="alpha-key",
                canonical_term="Alpha Concept",
                level="3_WORKSPACE",
                scope_id=ws.id,
                definition_text="Scoped to Alpha",
            ),
            OntologyConceptEntity(
                id="c-beta",
                concept_key="beta-key",
                canonical_term="Beta Secret Concept",
                level="3_WORKSPACE",
                scope_id="0192c4e0-0000-7000-8000-000000009902",
                definition_text="Scoped to Beta ONLY",
            ),
        )
    )
    app.state.ontology_rag_runtime_bundle = (ont_svc, object(), object())
    app.state.embedding_port = _FakeEmb()

    monkeypatch.setattr(
        "orcia_api.dependencies._assistant_tools_helpers._build_sql_rag_repo",
        lambda _req: _InMemoryRagStub(None),
    )

    ag_svc: AgentsAndSkillsManagementService = app.state.agents_and_skills_service
    from orcia_core.orchestration.agents_and_skills_models import build_managed_skill_record

    ag_svc._skills["sk-alpha"] = build_managed_skill_record(
        resolved_id="sk-alpha",
        slug="alpha_si",
        clean_name="Alpha SI",
        clean_obj="Alpha SI write",
        params=("target",),
        clean_inst="Do write",
        clean_fmt="md",
        version="1.0.0",
        existing=None,
        visibility_scope="TEAM",
        source_pack_key=None,
        enabled_in_workspace=True,
        is_si_write=True,
        human_authored_required=True,
        owner_workspace_id=ws.id,
    )
    ag_svc._skills["sk-beta"] = build_managed_skill_record(
        resolved_id="sk-beta",
        slug="beta_other",
        clean_name="Beta Skill",
        clean_obj="Beta",
        params=(),
        clean_inst="Beta",
        clean_fmt="md",
        version="1.0.0",
        existing=None,
        visibility_scope="TEAM",
        source_pack_key=None,
        enabled_in_workspace=True,
        owner_workspace_id="0192c4e0-0000-7000-8000-000000009902",
    )
    ag_svc._skills["sk-priv"] = build_managed_skill_record(
        resolved_id="sk-priv",
        slug="priv_other",
        clean_name="Private Other",
        clean_obj="Private",
        params=(),
        clean_inst="Private",
        clean_fmt="md",
        version="1.0.0",
        existing=None,
        visibility_scope="PRIVATE",
        source_pack_key=None,
        enabled_in_workspace=True,
        owner_workspace_id=ws.id,
        owner_user_id="someone-else",
    )

    mcp_svc: RemoteServiceTestBenchAndGovernedMcpService = (
        app.state.remote_test_bench_and_mcp_service
    )
    await mcp_svc.configure_agent_mcp_exposure_async(
        actor_role="PLATFORM_ADMIN",
        workspace_slug=ws.slug,
        agent_slug="alpha-mcp-ro",
        display_name="Alpha Read MCP",
        mcp_exposed=True,
        regime="CONSULTATION_ANALYSIS",
        system_prompt_layers_1_to_4="Prompt",
        secret_refs=(),
        human_authored_required=False,
    )

    req = _make_request(app)
    anon_ctx = await build_assistant_tool_catalog_context_async(
        req, user=None, workspace_id="scope-global"
    )
    assert anon_ctx.user_role == "OBSERVER"
    assert anon_ctx.user_permissions == frozenset()

    unknown_ws_ctx = await build_assistant_tool_catalog_context_async(
        req, user=contrib, workspace_id="ws-nonexistent"
    )
    assert unknown_ws_ctx.user_permissions == frozenset()

    alpha_ctx = await build_assistant_tool_catalog_context_async(
        req, user=contrib, workspace_id=ws.id
    )
    skill_ids = {s.skill_id for s in alpha_ctx.skills}
    assert "sk-alpha" in skill_ids
    assert "sk-beta" not in skill_ids
    assert "sk-priv" not in skill_ids
    sk_alpha = next(s for s in alpha_ctx.skills if s.skill_id == "sk-alpha")
    assert sk_alpha.is_si_write is True and sk_alpha.human_authored_required is True
    assert any(m.agent_slug == "alpha-mcp-ro" for m in alpha_ctx.mcp_tools)

    rag_fn, onto_fn, skill_fn, mcp_fn = build_tool_execution_callbacks(req)
    assert await rag_fn(ws.id, "query", 5, None) == []
    assert await rag_fn(ws.id, "   ", 5, contrib) == []
    assert await rag_fn(ws.id, "query", 5, observer) == []
    contrib_hits = await rag_fn(ws.id, "query", 5, contrib)
    assert [h["source_uri"] for h in contrib_hits] == ["git://org/public-rag.md"]

    # Skill runner & agent mcp_tool_permissions coverage
    ag_svc._agents["ag-mcp-1"] = type(
        "Ag",
        (),
        {
            "agent_id": "ag-mcp-1",
            "slug": "ag-mcp",
            "name": "Agent MCP",
            "enabled_in_workspace": True,
            "mcp_exposed": True,
            "lifecycle_status": "ACTIVE",
            "visibility_scope": "TEAM",
            "owner_workspace_id": ws.id,
            "owner_user_id": None,
            "mcp_tool_permissions": (("none_tool", "NONE"), ("write_tool", "WRITE_PREVIEW")),
        },
    )()
    specs_ag = await collect_authorized_mcp_specs(
        req, workspace_id=ws.id, loaded_agents=list(ag_svc._agents.values())
    )
    assert any(s.tool_name == "mcp_ag_mcp_write_tool" and s.is_si_write for s in specs_ag)
    disabled_sk = build_managed_skill_record(
        resolved_id="sk-disabled",
        slug="disabled_s",
        clean_name="Disabled",
        clean_obj="Disabled",
        params=(),
        clean_inst="Disabled",
        clean_fmt="md",
        version="1.0.0",
        existing=None,
        visibility_scope="TEAM",
        source_pack_key=None,
        enabled_in_workspace=False,
        owner_workspace_id=ws.id,
    )
    from orcia_api.dependencies._assistant_tools_ontology import is_record_visible_in_workspace

    assert (
        is_record_visible_in_workspace(disabled_sk, ws_uuid=ws.id, ws_slug=ws.slug, user=contrib)
        is False
    )
    assert (
        is_record_visible_in_workspace(
            ag_svc._skills["sk-priv"], ws_uuid=ws.id, ws_slug=ws.slug, user=None
        )
        is False
    )

    sk_out = await skill_fn(
        AuthorizedToolDescriptor(
            tool_name="skill_alpha_si",
            description="Alpha",
            parameters_schema={},
            category="skill",
            skill_id="sk-alpha",
        ),
        {"input_text": "hello"},
        ws.id,
    )
    assert sk_out["status"] == "SUCCEEDED"

    # Observer & uninvited workspace access branches + READ_ONLY_OBSERVER membership
    ro_member = UserIdentity(
        id="0192c4e0-0000-7000-8000-000000009919",
        email="ro_mem@orcia.local",
        display_name="RO Mem",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="org-unlisted",
    )
    auth_svc.evaluator.upsert_membership(
        WorkspaceMembershipEntity(
            id="mem-alpha-ro-mem",
            workspace_id=ws.id,
            user_id=ro_member.id,
            role="CONTRIBUTOR",
            access_mode="READ_ONLY_OBSERVER",
        )
    )
    ro_ctx = await build_assistant_tool_catalog_context_async(
        req, user=ro_member, workspace_id=ws.id
    )
    assert ro_ctx.user_role == "READ_ONLY_OBSERVER"
    assert ro_ctx.user_permissions == frozenset({"read"})
    obs_ctx = await build_assistant_tool_catalog_context_async(
        req, user=observer, workspace_id=ws.id
    )
    assert obs_ctx.user_permissions == frozenset({"read"})
    uninv_ctx = await build_assistant_tool_catalog_context_async(
        req, user=ro_member, workspace_id="0192c4e0-0000-7000-8000-000000009902"
    )
    assert uninv_ctx.user_permissions == frozenset()

    # Ontology lookup with TEAM -> BU hierarchy + level filter
    from orcia_core.permissions.models import OrgUnitNode

    auth_svc.evaluator.upsert_org_unit(
        OrgUnitNode(
            id="bu-ont-1", slug="bu-ont", name="BU Ont", unit_type="BU", parent_id="org-root"
        )
    )
    auth_svc.evaluator.upsert_org_unit(
        OrgUnitNode(
            id="team-ont-1",
            slug="team-ont",
            name="Team Ont",
            unit_type="TEAM",
            parent_id="bu-ont-1",
        )
    )
    ws_team = WorkspaceEntity(
        id="0192c4e0-0000-7000-8000-000000009903",
        slug="ws-team",
        name="WS Team",
        owner_org_unit_id="team-ont-1",
        visibility_mode="STANDARD",
    )
    auth_svc.evaluator.upsert_workspace(ws_team)
    onto_items = await onto_fn(ws.id, "nonmatching_Fallback", None)
    terms = {it["canonical_term"] for it in onto_items}
    assert "Alpha Concept" in terms
    assert "Enterprise Principle" in terms
    assert "Beta Secret Concept" not in terms
    onto_lvl = await onto_fn(ws_team.id, "Alpha", "1_ENTERPRISE")
    assert all("1_ENTERPRISE" in str(it["level"]) for it in onto_lvl)

    # Cached router + READ_ONLY_OBSERVER Step A guard branch
    r1 = get_governed_assistant_tool_router(req)
    assert get_governed_assistant_tool_router(req) is r1
    ro_exec_verdict = await evaluate_permission_broker_step(
        request=AssistantToolExecutionRequest(
            turn_id="t-ro",
            iteration=0,
            tool_call_id="c-ro",
            tool_name="skill_alpha_si",
            workspace_id=ws.id,
            user_id=ro_member.id,
            user_role="CONTRIBUTOR",
            user_identity=ro_member,
            arguments={},
        ),
        descriptor=AuthorizedToolDescriptor(
            tool_name="skill_alpha_si",
            description="SI",
            parameters_schema={},
            category="skill",
            read_only=False,
            required_permission="execute",
        ),
        permission_broker=None,
        evaluator=auth_svc.evaluator,
    )
    assert ro_exec_verdict.allowed is False
    assert ro_exec_verdict.reason_code == "ERR_OBSERVER_MODE_READ_ONLY"

    mcp_desc = AuthorizedToolDescriptor(
        tool_name="mcp_agent_alpha_mcp_ro",
        description="Read MCP",
        parameters_schema={},
        category="mcp_tool",
        read_only=True,
        mcp_agent_slug="alpha-mcp-ro",
    )
    mcp_res = await mcp_fn(
        mcp_desc,
        AssistantToolExecutionRequest(
            turn_id="t-mcp",
            iteration=0,
            tool_call_id="c-mcp",
            tool_name="mcp_agent_alpha_mcp_ro",
            workspace_id=ws.id,
            user_id=contrib.id,
            user_email=contrib.email,
            user_role="CONTRIBUTOR",
            arguments={"query": "Analyze backlog"},
        ),
    )
    assert mcp_res["status"] == "EXECUTED"
    assert mcp_res["audit_actor_type"] == "MCP_IDE_CLIENT"
    assert "Analyze backlog" in mcp_res["response_text"]
    assert "arguments" not in mcp_res

    specs = await collect_authorized_mcp_specs(req, workspace_id=ws.id, loaded_agents=[])
    assert any(s.source_uri_or_scope == f"mcp://{ws.slug}/alpha-mcp-ro" for s in specs)
    assert get_governed_assistant_tool_router(req) is not None


@pytest.mark.asyncio
async def test_p1_approval_halt_zero_502_and_surgical_has_read_source() -> None:
    captured_read_flags: list[bool] = []

    class _RecordingExplorer(SurgicalExplorerPort):
        async def execute_primitive(
            self,
            primitive: SurgicalPrimitiveName,
            *,
            resource_uri: str,
            workspace_id: str,
            actor_id: str,
            has_read_source: bool = True,
            query: str = "",
            start_line: int = 1,
            end_line: int = 200,
            max_results: int = 20,
        ) -> SurgicalObservation:
            del workspace_id, actor_id, query, start_line, end_line, max_results
            captured_read_flags.append(has_read_source)
            return SurgicalObservation(
                kind=primitive, resource_uri=resource_uri, display_filename="d.md"
            )

    desc_ro = AuthorizedToolDescriptor(
        tool_name="check_resource_state",
        description="Check",
        parameters_schema={},
        category="surgical_read",
        read_only=True,
        required_permission="read",
    )
    await _execute_surgical_tool(
        desc_ro,
        AssistantToolExecutionRequest(
            turn_id="t",
            iteration=0,
            tool_call_id="c1",
            tool_name="check_resource_state",
            workspace_id="ws-1",
            user_id="u-obs",
            user_role="OBSERVER",
            arguments={"resource_uri": "orcia://d.md"},
        ),
        _RecordingExplorer(),
    )
    await _execute_surgical_tool(
        desc_ro,
        AssistantToolExecutionRequest(
            turn_id="t",
            iteration=0,
            tool_call_id="c2",
            tool_name="check_resource_state",
            workspace_id="ws-1",
            user_id="u-con",
            user_role="CONTRIBUTOR",
            arguments={"resource_uri": "orcia://d.md"},
        ),
        _RecordingExplorer(),
    )
    assert captured_read_flags == [False, True]

    # Step A fails closed on unknown non-global workspace
    app, auth_svc, contrib, _, ws = _build_test_app_and_users()
    del app
    unknown_verdict = await evaluate_permission_broker_step(
        request=AssistantToolExecutionRequest(
            turn_id="t",
            iteration=0,
            tool_call_id="c3",
            tool_name="check_resource_state",
            workspace_id="ws-does-not-exist",
            user_id=contrib.id,
            user_role="CONTRIBUTOR",
            arguments={},
        ),
        descriptor=desc_ro,
        permission_broker=None,
        evaluator=auth_svc.evaluator,
    )
    assert unknown_verdict.allowed is False
    assert unknown_verdict.reason_code == "ERR_SCOPE_ACCESS_DENIED"

    # Roles helper + sync followup fresh UUIDv7
    mcp_ro_desc = AuthorizedToolDescriptor(
        tool_name="mcp_ro",
        description="MCP",
        parameters_schema={},
        category="mcp_tool",
        read_only=True,
        is_si_write=False,
        human_authored_required=False,
    )
    assert granted_roles_for_tool_call([mcp_ro_desc], "mcp_ro", "CONTRIBUTOR") == (
        "ROLE_MCP_TOOL_EXECUTOR",
    )
    assert granted_roles_for_tool_call([mcp_ro_desc], "mcp_ro", "OBSERVER") == ()

    recorded_turn_ids: list[str] = []

    class _StubRouter:
        async def execute_tool_call(
            self, request: AssistantToolExecutionRequest, **_kw: Any
        ) -> Any:
            recorded_turn_ids.append(request.turn_id)
            from orcia_core.ports.assistant_tool_executor_port import (
                AssistantToolExecutionResult,
                AssistantToolSseEvent,
            )

            return AssistantToolExecutionResult(
                tool_call_id=request.tool_call_id,
                tool_name=request.tool_name,
                verdict="APPROVAL_REQUIRED",
                delimited_output="<untrusted_tool_output>blocked</untrusted_tool_output>",
                raw_scrubbed_summary="blocked",
                audit_event_type="ASSISTANT_TOOL_DENIED",
                approval_proposal={"human_arbitration_uri": "orcia://arbitration/1"},
                sse_events=(
                    AssistantToolSseEvent(event="tool_call", data={"tool_name": request.tool_name}),
                    AssistantToolSseEvent(event="approval_required", data={"reason": "V5"}),
                    AssistantToolSseEvent(
                        event="tool_result", data={"verdict": "APPROVAL_REQUIRED"}
                    ),
                ),
            )

    class _OnlyToolStreamPort(LlmStreamingPort):
        async def complete_chat(self, request: LlmStreamRequest) -> LlmChatTurnOutcome | None:
            del request
            return None

        async def stream_chat_sse(self, request: LlmStreamRequest) -> Any:
            del request
            tc = {"id": "tc-si", "name": "skill_write", "arguments": "{}"}
            yield typed_event_to_delta(
                ToolCallDelta(tool_call_id="tc-si", name="skill_write", arguments_delta="{}")
            )
            yield typed_event_to_delta(Finish(finish_reason="tool_calls", tool_calls=(tc,)))

    ep = LlmEndpointConfig(
        provider="openai",
        model_name="gpt-4.1-mini",
        endpoint_uri="https://api.openai.com/v1/chat/completions",
        auth_mode="none",
        supports_tools=True,
    )
    si_desc = AuthorizedToolDescriptor(
        tool_name="skill_write",
        description="Write",
        parameters_schema={},
        category="skill",
        read_only=False,
        is_si_write=True,
    )
    sync_txt, _, _, _ = await execute_sync_tool_followup(
        tool_router=_StubRouter(),  # type: ignore[arg-type]
        catalog=(si_desc,),
        active_port=_OnlyToolStreamPort(),
        ep=ep,
        messages=[{"role": "user", "content": "Go"}],
        tool_calls=[{"id": "tc-sync", "name": "skill_write", "arguments": "{}"}],
        workspace_id=ws.id,
        user_id=contrib.id,
        user=contrib,
        active_hat="ARCHITECT",
        trace_id="0" * 32,
        locale="fr",
    )
    assert "orcia://arbitration/1" in sync_txt
    assert UUID(recorded_turn_ids[0]).version == 7

    registry = RedisAssistantTurnRegistry()
    rate_limiter = RedisAssistantRateLimiter()
    rec = AssistantTurnRecord(
        turn_id="turn-approval-no502",
        workspace_id=ws.id,
        user_id=contrib.id,
        status="RUNNING",
        user_prompt="Write to Jira",
        assembled_system_prompt="Sys",
        speed_mode="SPEED_2_AGENT_TOOLS",
        trace_id="0" * 32,
    )
    await registry.register_turn(rec)
    await execute_turn_producer_task(
        registry=registry,
        rate_limiter=rate_limiter,
        initial_record=rec,
        lease_token="lease-1",
        liveness_ttl_s=30,
        t0=0.0,
        default_thinking="t",
        fallback_response_text=None,
        ep=ep,
        http_client_getter=lambda: None,  # type: ignore[arg-type, return-value]
        messages_builder=lambda: [{"role": "user", "content": "Write"}],
        tools_builder=lambda: [si_desc.to_llm_tool_schema()],
        conversation_history_count=0,
        folder_pinned_notes=None,
        llm_port=_OnlyToolStreamPort(),
        user_email=contrib.email,
        user_display_name=contrib.display_name,
        audit_ledger_sink=None,
        locale="en",
        instance="/api/v1/assistant/turns",
        tool_router=_StubRouter(),  # type: ignore[arg-type]
        tool_catalog=(si_desc,),
        user_identity=contrib,
    )
    evts = await registry.read_events(
        "turn-approval-no502", after_cursor="0-0", count=50, block_ms=0
    )
    names = [e.event for e in evts]
    assert "approval_required" in names
    assert "turn_completed" in names
    assert "stream_error" not in names


@pytest.mark.asyncio
async def test_coverage_branches_for_audit_runtime_and_helpers() -> None:
    assert _parse_optional_uuid(None) is None
    assert _parse_optional_uuid("not-a-uuid") is None
    assert await enqueue_arbitration_outbox_event(outbox_enqueue_fn=None, event=None) is None

    from orcia_core.kernel.events import HumanArbitrationRequested

    async def _fail_outbox(_ev: Any) -> str | None:
        raise RuntimeError("boom")

    assert (
        await enqueue_arbitration_outbox_event(
            outbox_enqueue_fn=_fail_outbox,
            event=HumanArbitrationRequested.create(
                arbitration_id="a1", run_id=None, workspace_id=None, step_key="s1", options_count=2
            ),
        )
        is None
    )
    assert build_approval_proposal_text([], locale="en") == ""

    # Child delegation propagates ASSISTANT profile
    asst_snap = ReflexiveSessionSnapshot(
        execution_id="ex-p",
        actor_slug="assistant-agent",
        objective="Obj",
        execution_profile="ASSISTANT",
    )
    child_cfg = build_child_delegation_config(asst_snap)
    assert child_cfg.execution_profile == "ASSISTANT"

    # Snapshot expiry naive & Z timestamps + scratchpad variants
    past_naive = (datetime.now(UTC) - timedelta(minutes=5)).replace(tzinfo=None).isoformat()
    with pytest.raises(ReflexiveSessionExpiredError):
        assert_snapshot_not_expired(
            ReflexiveSessionSnapshot(
                execution_id="ex-exp", actor_slug="a", objective="o", expires_at_utc=past_naive
            )
        )
    future_z = (datetime.now(UTC) + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    assert_snapshot_not_expired(
        ReflexiveSessionSnapshot(
            execution_id="ex-ok", actor_slug="a", objective="o", expires_at_utc=future_z
        )
    )
    assert build_scratchpad_entry_from_observation(
        turn_index=0,
        obs=SurgicalObservation(
            kind=SurgicalPrimitiveName.INSPECT_RESOURCE_LINES,
            resource_uri="u",
            display_filename="f",
            redacted=True,
        ),
    ).excerpt.startswith("[Extrait")
    assert (
        "s1"
        in build_scratchpad_entry_from_observation(
            turn_index=1,
            obs=SurgicalObservation(
                kind=SurgicalPrimitiveName.SEARCH_WORKSPACE_SNIPPETS,
                resource_uri="u",
                display_filename="f",
                snippets=[
                    SurgicalSnippetMatch(
                        resource_uri="u",
                        display_filename="f",
                        start_line=1,
                        end_line=2,
                        line_anchor="#L1",
                        excerpt="s1",
                    )
                ],
            ),
        ).excerpt
    )
    assert (
        "Fn"
        in build_scratchpad_entry_from_observation(
            turn_index=2,
            obs=SurgicalObservation(
                kind=SurgicalPrimitiveName.OUTLINE_RESOURCE_STRUCTURE,
                resource_uri="u",
                display_filename="f",
                outline=[SurgicalOutlineNode(kind="fn", title="Fn", line_number=3)],
            ),
        ).excerpt
    )

    # Runtime edge branches (start_background_execution, ResourceNotFoundError, step_delay_ms)
    class _MemStore(ReflexiveSessionStorePort):
        def __init__(self) -> None:
            self.rows: dict[str, dict[str, Any]] = {}

        async def save_session_record(self, execution_id: str, **kw: Any) -> None:
            self.rows[execution_id] = dict(kw["snapshot_payload"])

        async def load_session_record(self, execution_id: str) -> dict[str, Any] | None:
            return self.rows.get(execution_id)

    class _EvStream(ReflexiveEventStreamPort):
        async def publish_event(self, execution_id: str, event: dict[str, Any]) -> None:
            del execution_id, event

    class _SimpleLlm(ReflexiveLlmPort):
        async def decide_next_turn(self, turn_input: ReflexiveTurnInput) -> ReflexiveTurnDecision:
            del turn_input
            return ReflexiveTurnDecision(action_kind="final_answer", thought_text="Done")

        async def stream_turn_deltas(self, turn_input: ReflexiveTurnInput, decision: Any) -> Any:
            del turn_input, decision
            if False:
                yield None

    class _NoopExp(SurgicalExplorerPort):
        async def execute_primitive(self, primitive: SurgicalPrimitiveName, **kw: Any) -> Any:
            del kw
            return SurgicalObservation(kind=primitive, resource_uri="u", display_filename="f")

    store = _MemStore()
    rt = NonDeterministicReflexiveRuntime(
        llm_port=_SimpleLlm(),
        surgical_explorer=_NoopExp(),
        session_store=store,
        event_stream=_EvStream(),
        execution_profile="ASSISTANT",
    )
    _, task = rt.start_background_execution(
        actor_slug="assistant-agent",
        objective="Quick check",
        config=ReflexiveRuntimeConfig(execution_profile="PROCESS", step_delay_ms=1),
    )
    bg_snap = await task
    assert bg_snap.execution_profile == "ASSISTANT"
    assert bg_snap.status == "COMPLETED"
    assert (await rt.cancel_execution(bg_snap.execution_id)).status == "COMPLETED"

    with pytest.raises(ResourceNotFoundError):
        await rt.cancel_execution("missing-id")
    with pytest.raises(ResourceNotFoundError):
        await rt.request_synthesize_now("missing-id")
    with pytest.raises(ResourceNotFoundError):
        await rt.resume_after_write_decision("missing-id", approved=True)

    idle_snap = ReflexiveSessionSnapshot(
        execution_id="ex-idle-synth",
        actor_slug="assistant-agent",
        objective="Synth",
        execution_profile="ASSISTANT",
        status="RUNNING",
    )
    await store.save_session_record(idle_snap.execution_id, snapshot_payload=idle_snap.model_dump())
    resumed = await rt.request_synthesize_now("ex-idle-synth", resume_if_idle=True)
    assert resumed.status == "COMPLETED"

    # Unused timeout helper edge
    status_tag, _, _ = await execute_with_timeout(
        descriptor=AuthorizedToolDescriptor(
            tool_name="check_resource_state",
            description="Check",
            parameters_schema={},
            category="surgical_read",
            read_only=True,
        ),
        request=AssistantToolExecutionRequest(
            turn_id="t",
            iteration=0,
            tool_call_id="c",
            tool_name="check_resource_state",
            workspace_id="w",
            user_id="u",
            arguments={},
        ),
        deps=ToolDispatchDependencies(surgical_explorer=None),
    )
    assert status_tag == "EXECUTED"
    await asyncio.sleep(0)

    # `assistant_agent_synthesis.py` branch coverage
    from orcia_core.orchestration.assistant_agent_models import AssistantTurnResult
    from orcia_core.orchestration.assistant_agent_synthesis import (
        classify_assistant_intent,
        iter_assistant_turn_sse_events,
        synthesize_assistant_turn_response,
        synthesize_assistant_turn_response_async,
    )
    from orcia_core.orchestration.assistant_harness import AssistantHarness
    from orcia_core.orchestration.errors import TierModelNotConfiguredError

    assert classify_assistant_intent("lance le run") == "WORKFLOW_LAUNCH"
    assembled = AssistantHarness().assemble_prompt(
        user_prompt="Prompt",
        human_profile_archetype="ARCHITECT",
        workspace_id="ws-1",
        intent="QA_COACHING",
    )
    with pytest.raises(RuntimeError, match="active event loop"):
        synthesize_assistant_turn_response(
            llm_gateway=None,
            cognitive_router=None,
            assembled=assembled,
            intent="QA_COACHING",
            proposal=None,
            workspace_id="ws-1",
        )
    with pytest.raises(TierModelNotConfiguredError):
        await synthesize_assistant_turn_response_async(
            llm_gateway=None,
            cognitive_router=None,
            assembled=assembled,
            intent="QA_COACHING",
            proposal=None,
            workspace_id="ws-1",
        )

    class _MockCog:
        def resolve_mapping(self, **_kw: Any) -> Any:
            return type("M", (), {"model_family": "openai", "model_name": "gpt-4.1-mini"})()

    with pytest.raises(TierModelNotConfiguredError):
        await synthesize_assistant_turn_response_async(
            llm_gateway=None,
            cognitive_router=_MockCog(),
            assembled=assembled,
            intent="QA_COACHING",
            proposal=None,
            workspace_id="ws-1",
        )
    ev_list = list(
        iter_assistant_turn_sse_events(
            AssistantTurnResult(
                turn_id="t-1",
                workflow_uri="orcia://assistant/default",
                workspace_id="ws-1",
                human_profile_archetype="ARCHITECT",
                intent="QA_COACHING",
                response_text="ok",
                first_token_latency_ms=1.0,
                node_traces=(),
                assembled_prompt=assembled,
                workflow_proposal=None,
            )
        )
    )
    assert ev_list[-1]["event"] == "done"


@pytest.mark.asyncio
async def test_p2_dependencies_edge_branches_for_90_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from orcia_api.dependencies._assistant_tools_helpers import _build_sql_rag_repo
    from orcia_api.dependencies._assistant_tools_ontology import (
        is_record_visible_in_workspace,
        run_workspace_ontology_lookup,
    )
    from orcia_api.dependencies.assistant_tools import _is_rag_active_for_turn
    from orcia_core.kernel.events import HumanArbitrationRequested
    from orcia_core.orchestration.agents_and_skills_models import build_managed_skill_record
    from orcia_core.rag.errors import NoActiveEmbeddingModelError

    app, auth_svc, contrib, _, ws = _build_test_app_and_users()
    req = _make_request(app)

    # `_build_sql_rag_repo` branches
    assert _build_sql_rag_repo(req) is None
    app.state.session_maker = lambda: None
    assert _build_sql_rag_repo(req) is not None
    app.state.session_maker = None

    # `_is_rag_active_for_turn` branches
    class _StubEmb(EmbeddingPort):
        async def embed_query(self, text: str) -> tuple[float, ...]:
            del text
            return (0.1,)

        async def embed(self, texts: Any) -> list[list[float]]:
            return [[0.1] for _ in texts]

    assert await _is_rag_active_for_turn(req, embedding_port=_StubEmb()) is True

    async def _boom_emb(_r: Request) -> Any:
        raise RuntimeError("emb-down")

    monkeypatch.setattr(
        "orcia_api.dependencies.assistant_tools.get_optional_embedding_port", _boom_emb
    )
    assert await _is_rag_active_for_turn(req, embedding_port=None) is False

    # `scope-global` + PG load fallback in `build_assistant_tool_catalog_context_async`
    app.state.db_engine = object()

    async def _boom_pg(_eng: Any, **_kw: Any) -> Any:
        raise RuntimeError("pg-down")

    monkeypatch.setattr(
        "orcia_api.dependencies.assistant_tools.load_agents_and_skills_from_postgres18", _boom_pg
    )
    monkeypatch.setattr(
        "orcia_api.dependencies._assistant_tools_ontology.load_ontology_governance_service_pg",
        _boom_pg,
    )
    g_ctx = await build_assistant_tool_catalog_context_async(
        req, user=contrib, workspace_id="scope-global"
    )
    assert g_ctx.user_permissions == frozenset({"read", "execute"})
    app.state.db_engine = None

    # `_rag_search` without embedding port and with `NoActiveEmbeddingModelError`
    rag_fn, _, _, _ = build_tool_execution_callbacks(req)
    monkeypatch.setattr(
        "orcia_api.dependencies._assistant_tools_helpers._build_sql_rag_repo", lambda _r: object()
    )
    monkeypatch.setattr(
        "orcia_api.dependencies._assistant_tools_helpers.get_optional_embedding_port",
        lambda _r: asyncio.sleep(0, result=None),
    )
    assert await rag_fn(ws.id, "query", 5, contrib) == []

    class _NoEmbRag:
        async def search_hybrid_rrf(self, **_kw: Any) -> list[Any]:
            raise NoActiveEmbeddingModelError(instance="rag")

    monkeypatch.setattr(
        "orcia_api.dependencies._assistant_tools_helpers._build_sql_rag_repo",
        lambda _r: _NoEmbRag(),
    )
    monkeypatch.setattr(
        "orcia_api.dependencies._assistant_tools_helpers.get_optional_embedding_port",
        lambda _r: asyncio.sleep(0, result=_StubEmb()),
    )
    assert await rag_fn(ws.id, "query", 5, contrib) == []

    class _EmptyRag:
        async def search_hybrid_rrf(self, **_kw: Any) -> list[Any]:
            return []

    monkeypatch.setattr(
        "orcia_api.dependencies._assistant_tools_helpers._build_sql_rag_repo",
        lambda _r: _EmptyRag(),
    )
    assert await rag_fn(ws.id, "query", 5, contrib) == []

    # `collect_authorized_mcp_specs` disabled/unexposed + exception branch
    class _BrokenMcpSvc:
        async def list_exposed_agents_async(self, *, workspace_slug: str) -> list[Any]:
            del workspace_slug
            raise RuntimeError("mcp-down")

    app.state.remote_test_bench_and_mcp_service = _BrokenMcpSvc()
    disabled_ag = type("Ag", (), {"enabled_in_workspace": False, "mcp_exposed": False})()
    assert (
        await collect_authorized_mcp_specs(req, workspace_id=ws.id, loaded_agents=[disabled_ag])
        == []
    )

    # `is_record_visible_in_workspace` PRIVATE owned by caller & empty ontology fallback
    own_priv = build_managed_skill_record(
        resolved_id="sk-own-priv",
        slug="own_priv",
        clean_name="Own Priv",
        clean_obj="Obj",
        params=(),
        clean_inst="Inst",
        clean_fmt="md",
        version="1.0.0",
        existing=None,
        visibility_scope="PRIVATE",
        source_pack_key=None,
        enabled_in_workspace=True,
        owner_workspace_id=ws.id,
        owner_user_id=contrib.id,
    )
    assert is_record_visible_in_workspace(own_priv, ws_uuid=ws.id, ws_slug=ws.slug, user=contrib)

    ont_only_beta = OntologyGovernanceService(
        concepts=(
            OntologyConceptEntity(
                id="c-b",
                concept_key="b-key",
                canonical_term="Beta Only",
                level="3_WORKSPACE",
                scope_id="0192c4e0-0000-7000-8000-000000009902",
                definition_text="Beta",
            ),
        )
    )
    app.state.ontology_rag_runtime_bundle = (ont_only_beta, object(), object())
    monkeypatch.setattr(
        "orcia_api.dependencies._assistant_tools_ontology.get_optional_embedding_port",
        lambda _r: asyncio.sleep(0, result=None),
    )
    assert await run_workspace_ontology_lookup(req, ws_id=ws.id, query="Beta", level=None) == []

    # Router outbox enqueue helper without db_engine + PG18 skills success + redis attach
    app.state.redis_client = object()
    app.state.governed_assistant_tool_router = None
    router = get_governed_assistant_tool_router(req)
    outbox_cb = router._outbox_enqueue_fn
    assert outbox_cb is not None
    assert (
        await outbox_cb(
            HumanArbitrationRequested.create(
                arbitration_id="a-2", run_id=None, workspace_id=None, step_key="s", options_count=2
            )
        )
        is None
    )

    async def _ok_pg(_eng: Any, **_kw: Any) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
        return (own_priv,), ()

    app.state.db_engine = object()
    monkeypatch.setattr(
        "orcia_api.dependencies.assistant_tools.load_agents_and_skills_from_postgres18", _ok_pg
    )
    app.state.remote_test_bench_and_mcp_service = RemoteServiceTestBenchAndGovernedMcpService()
    pg_ctx = await build_assistant_tool_catalog_context_async(req, user=contrib, workspace_id=ws.id)
    assert any(s.skill_id == own_priv.skill_id for s in pg_ctx.skills)
