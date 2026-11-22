"""Unit tests for `GovernedAssistantToolRouter`, Dynamic Catalog & Steps A-E (`Story 26.6b`)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from orcia_core.agents import (
    GovernedAssistantToolRouter,
    RedisToolIdempotencyStore,
    build_authorized_tool_catalog,
)
from orcia_core.permissions import build_default_auth_and_org_service
from orcia_core.permissions.broker import PermissionBrokerService
from orcia_core.permissions.models import UserIdentity, WorkspaceMembershipEntity
from orcia_core.permissions.seeds import DEFAULT_PERMISSION_BROKER_POLICY_SEEDS
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolCatalogContext,
    AssistantToolExecutionRequest,
    McpExposedToolSpec,
    SkillCatalogEntry,
)
from orcia_core.ports.surgical_explorer_port import (
    SurgicalExplorerPort,
    SurgicalLineEntry,
    SurgicalObservation,
    SurgicalPrimitiveName,
)
from orcia_kernel.ports import SandboxExecutionRequest, SandboxExecutionResult, SandboxPort


class _StubSurgicalExplorer(SurgicalExplorerPort):
    def __init__(self, *, content: str = "Line 1 content") -> None:
        self.calls: list[str] = []
        self._content = content

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
        del workspace_id, actor_id, has_read_source, query, max_results
        self.calls.append(primitive.value)
        return SurgicalObservation(
            kind=primitive,
            resource_uri=resource_uri,
            display_filename=resource_uri.rsplit("/", 1)[-1] or "doc.md",
            start_line=start_line,
            end_line=end_line,
            summary=self._content,
            lines=[SurgicalLineEntry(line_number=start_line, content=self._content)],
        )


class _StubAuditSink:
    def __init__(self) -> None:
        self.entries: list[Any] = []

    async def record_entry(self, entry: Any) -> str:
        self.entries.append(entry)
        return f"aud-{len(self.entries)}"


class _FakeSandbox(SandboxPort):
    def __init__(self, *, passed: bool = True) -> None:
        self.passed = passed
        self.requests: list[SandboxExecutionRequest] = []

    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        self.requests.append(request)
        return SandboxExecutionResult(
            passed=self.passed,
            exit_code=0 if self.passed else 1,
            stdout='{"ok": true}' if self.passed else "",
            stderr="" if self.passed else "sandbox error",
            duration_ms=4,
        )


def test_dynamic_catalog_excludes_kb_when_rag_inactive_and_keeps_all_skills() -> None:
    skills = tuple(
        SkillCatalogEntry(
            skill_id=f"sk-{i}",
            slug=f"skill_{i}",
            name=f"Skill {i}",
            objective=f"Objective {i}",
            input_parameters=("artifact_id", "depth"),
            enabled_in_workspace=(i != 12),
        )
        for i in range(13)
    )
    mcp_tools = (
        McpExposedToolSpec(
            tool_name="mcp.none_tool", agent_slug="a", description="Hidden", permission_mode="NONE"
        ),
        McpExposedToolSpec(
            tool_name="mcp.read_tool",
            agent_slug="a",
            description="Read MCP",
            permission_mode="READ_ONLY",
            required_permission="read",
        ),
        McpExposedToolSpec(
            tool_name="mcp.write_tool",
            agent_slug="a",
            description="Write MCP",
            permission_mode="WRITE_PREVIEW",
            is_si_write=True,
            required_permission="execute",
        ),
    )

    cat_no_rag = build_authorized_tool_catalog(
        AssistantToolCatalogContext(
            workspace_id="ws-1",
            user_id="u-1",
            user_role="CONTRIBUTOR",
            rag_active=False,
            skills=skills,
            mcp_tools=mcp_tools,
        )
    )
    names_no_rag = {d.tool_name for d in cat_no_rag}
    assert {
        "check_resource_state",
        "outline_resource_structure",
        "search_workspace_snippets",
        "inspect_resource_lines",
        "ontology.lookup",
    }.issubset(names_no_rag)
    assert "kb.search" not in names_no_rag
    assert len([n for n in names_no_rag if n.startswith("skill_")]) == 12
    assert "skill_skill_12" not in names_no_rag
    assert "mcp.none_tool" not in names_no_rag
    assert "mcp.read_tool" in names_no_rag
    assert "mcp.write_tool" in names_no_rag

    sk0 = next(d for d in cat_no_rag if d.tool_name == "skill_skill_0")
    assert set(sk0.parameters_schema["properties"].keys()) == {"artifact_id", "depth"}

    cat_observer = build_authorized_tool_catalog(
        AssistantToolCatalogContext(
            workspace_id="ws-1",
            user_id="u-obs",
            user_role="OBSERVER",
            rag_active=True,
            skills=skills[:1],
            mcp_tools=mcp_tools,
        )
    )
    obs_names = {d.tool_name for d in cat_observer}
    assert "kb.search" in obs_names
    assert "mcp.read_tool" in obs_names
    assert "mcp.write_tool" not in obs_names
    assert "skill_skill_0" not in obs_names


@pytest.mark.asyncio
async def test_step_a_permission_broker_observer_scope_and_read_source_denials() -> None:
    auth_svc = build_default_auth_and_org_service()
    ws = auth_svc.evaluator.workspaces[0]
    admin = UserIdentity(
        id="u-admin-266b",
        email="admin@orcia.local",
        display_name="Platform Admin",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id=ws.owner_org_unit_id,
    )
    observer = UserIdentity(
        id="u-obs-266b",
        email="obs@orcia.local",
        display_name="Observer",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="OBSERVER",
        primary_org_unit_id=ws.owner_org_unit_id,
    )
    ws_obs_member = WorkspaceMembershipEntity(
        id="mem-obs-ws",
        workspace_id=ws.id,
        user_id=observer.id,
        role="OBSERVER",
        access_mode="READ_ONLY_OBSERVER",
    )
    contributor = UserIdentity(
        id="u-contrib-266b",
        email="contrib@orcia.local",
        display_name="Contributor",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id=ws.owner_org_unit_id,
    )
    ws_contrib_member = WorkspaceMembershipEntity(
        id="mem-contrib-ws",
        workspace_id=ws.id,
        user_id=contributor.id,
        role="CONTRIBUTOR",
        access_mode="CONTRIBUTOR_ACTION_REQUIRED",
    )
    auth_svc.evaluator._memberships = (
        *auth_svc.evaluator._memberships,
        ws_obs_member,
        ws_contrib_member,
    )

    broker = PermissionBrokerService(
        policies=DEFAULT_PERMISSION_BROKER_POLICY_SEEDS,
        evaluator=auth_svc.evaluator,
    )
    audit_sink = _StubAuditSink()
    router = GovernedAssistantToolRouter(
        permission_broker=broker,
        evaluator=auth_svc.evaluator,
        surgical_explorer=_StubSurgicalExplorer(),
        audit_ledger_sink=audit_sink,
    )
    ctx = AssistantToolCatalogContext(
        workspace_id=ws.id,
        user_id=admin.id,
        user_role=admin.platform_role,
        skills=(
            SkillCatalogEntry(
                skill_id="sk-ro",
                slug="analyze_readonly",
                name="Analyze",
                objective="Analyze artifact",
                enabled_in_workspace=True,
            ),
        ),
    )
    cat = router.build_authorized_catalog(ctx)

    denied_sp = await router.execute_tool_call(
        AssistantToolExecutionRequest(
            turn_id="t-1",
            iteration=0,
            tool_call_id="c-sp",
            tool_name="check_resource_state",
            workspace_id=ws.id,
            user_id=admin.id,
            execution_identity="service_principal",
            arguments={"resource_uri": "orcia://workspace/doc.md"},
        ),
        catalog=cat,
    )
    assert denied_sp.verdict == "DENIED"
    assert denied_sp.audit_event_type == "ASSISTANT_TOOL_DENIED"
    assert "ERR_CONFUSED_DEPUTY_BLOCKED" in denied_sp.delimited_output
    assert audit_sink.entries[-1].metadata["reason_code"] == "ERR_CONFUSED_DEPUTY_BLOCKED"

    denied_obs = await router.execute_tool_call(
        AssistantToolExecutionRequest(
            turn_id="t-1",
            iteration=0,
            tool_call_id="c-obs",
            tool_name="skill_analyze_readonly",
            workspace_id=ws.id,
            user_id=observer.id,
            user_role="OBSERVER",
            arguments={"input_text": "run"},
        ),
        catalog=cat,
    )
    assert denied_obs.verdict == "DENIED"
    assert "ERR_OBSERVER_MODE_READ_ONLY" in denied_obs.delimited_output
    assert audit_sink.entries[-1].metadata["reason_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    denied_scope = await router.execute_tool_call(
        AssistantToolExecutionRequest(
            turn_id="t-1",
            iteration=0,
            tool_call_id="c-scope",
            tool_name="check_resource_state",
            workspace_id=ws.id,
            user_id="u-outsider-never-invited",
            user_role="CONTRIBUTOR",
            arguments={"resource_uri": "orcia://workspace/doc.md"},
        ),
        catalog=cat,
    )
    assert denied_scope.verdict == "DENIED"
    assert "ERR_SCOPE_ACCESS_DENIED" in denied_scope.delimited_output
    assert audit_sink.entries[-1].metadata["reason_code"] == "ERR_SCOPE_ACCESS_DENIED"

    denied_broker = await router.execute_tool_call(
        AssistantToolExecutionRequest(
            turn_id="t-1",
            iteration=0,
            tool_call_id="c-ext",
            tool_name="check_resource_state",
            workspace_id=ws.id,
            user_id=contributor.id,
            user_role=contributor.platform_role,
            user_identity=contributor,
            granted_external_roles=(),
            arguments={"resource_uri": "confluence://company/PRIVATE/page-1"},
        ),
        catalog=cat,
    )
    assert denied_broker.verdict == "DENIED"
    assert denied_broker.audit_event_type == "ASSISTANT_TOOL_DENIED"
    assert all(e.event_type == "ASSISTANT_TOOL_DENIED" for e in audit_sink.entries)


@pytest.mark.asyncio
async def test_steps_b_c_d_e_v5_anchor_idempotency_timeout_and_sandbox() -> None:
    executed_count = 0
    audit_sink = _StubAuditSink()
    outbox_events: list[Any] = []
    sandbox = _FakeSandbox(passed=True)

    async def _skill_run(desc: Any, args: dict[str, Any], _ws: str) -> dict[str, Any]:
        nonlocal executed_count
        if desc.tool_name == "skill_slow_op":
            await asyncio.sleep(0.3)
        executed_count += 1
        return {"ok": True, "api_token": "secret-token-should-scrub", "echo": args.get("text", "")}

    async def _outbox_enqueue(event: Any) -> str | None:
        outbox_events.append(event)
        return str(event.event_id)

    router = GovernedAssistantToolRouter(
        surgical_explorer=_StubSurgicalExplorer(content="Normal text with write word in docs"),
        sandbox_port=sandbox,
        audit_ledger_sink=audit_sink,
        idempotency_store=RedisToolIdempotencyStore(),
        skill_runner_fn=_skill_run,
        outbox_enqueue_fn=_outbox_enqueue,
        default_timeout_s=0.05,
    )
    ctx = AssistantToolCatalogContext(
        workspace_id="ws-1",
        user_id="u-1",
        user_role="CONTRIBUTOR",
        skills=(
            SkillCatalogEntry(
                skill_id="sk-anchor",
                slug="edit_anchor",
                name="Edit Anchor",
                objective="Mutate human anchor",
                enabled_in_workspace=True,
                is_si_write=True,
                human_authored_required=True,
            ),
            SkillCatalogEntry(
                skill_id="sk-safe",
                slug="safe_summarize",
                name="Safe Summarize",
                objective="Read-only summarize",
                enabled_in_workspace=True,
                is_si_write=False,
            ),
            SkillCatalogEntry(
                skill_id="sk-slow",
                slug="slow_op",
                name="Slow Op",
                objective="Slow task",
                enabled_in_workspace=True,
                is_si_write=False,
            ),
        ),
    )
    cat = router.build_authorized_catalog(ctx)

    # Read-only tool succeeds even when output contains "write" (no lexical trap)
    ro_res = await router.execute_tool_call(
        AssistantToolExecutionRequest(
            turn_id="turn-9",
            iteration=0,
            tool_call_id="call-ro",
            tool_name="inspect_resource_lines",
            workspace_id="ws-1",
            user_id="u-1",
            user_role="CONTRIBUTOR",
            arguments={
                "resource_uri": "orcia://workspace/readme.md",
                "start_line": 1,
                "end_line": 10,
            },
        ),
        catalog=cat,
    )
    assert ro_res.verdict == "EXECUTED"
    assert [e.event for e in ro_res.sse_events] == ["tool_call", "tool_result"]

    # Step B: Deterministic human-anchor/SI write guard emits approval & outbox event
    v5_res = await router.execute_tool_call(
        AssistantToolExecutionRequest(
            turn_id="turn-9",
            iteration=0,
            tool_call_id="call-v5",
            tool_name="skill_edit_anchor",
            workspace_id="ws-1",
            user_id="u-1",
            user_role="CONTRIBUTOR",
            arguments={"section_key": "architecture_decision"},
        ),
        catalog=cat,
    )
    assert v5_res.verdict == "APPROVAL_REQUIRED"
    assert v5_res.audit_event_type == "ASSISTANT_TOOL_DENIED"
    assert v5_res.approval_proposal is not None
    assert v5_res.approval_proposal["transition_action"] == "CONTINUE_IN_PROCESS"
    assert [e.event for e in v5_res.sse_events] == [
        "tool_call",
        "approval_required",
        "tool_result",
    ]
    assert len(outbox_events) == 1
    assert outbox_events[0].event_type == "HumanArbitrationRequested"

    # Step C & D & E: Executed once + scrubbed + sandboxed + deduplicated on replay
    safe_req = AssistantToolExecutionRequest(
        turn_id="turn-9",
        iteration=1,
        tool_call_id="call-safe-1",
        tool_name="skill_safe_summarize",
        workspace_id="ws-1",
        user_id="u-1",
        user_role="CONTRIBUTOR",
        arguments={"text": "hello", "api_key": "raw-dummy-arg"},  # pragma: allowlist secret
    )
    first_safe = await router.execute_tool_call(safe_req, catalog=cat)
    second_safe = await router.execute_tool_call(safe_req, catalog=cat)
    assert first_safe.verdict == "EXECUTED"
    assert first_safe.audit_event_type == "ASSISTANT_TOOL_INVOKED"
    assert "secret-token-should-scrub" not in first_safe.delimited_output
    assert "[REDACTED_SECRET]" in first_safe.delimited_output
    assert len(sandbox.requests) == 1
    assert second_safe.verdict == "DEDUPLICATED"
    assert executed_count == 1
    invoked_audit = [e for e in audit_sink.entries if e.event_type == "ASSISTANT_TOOL_INVOKED"][-1]
    assert invoked_audit.metadata["masked_arguments"]["api_key"] == "[REDACTED_SECRET]"

    # Step D timeout protection (`asyncio.wait_for`)
    slow_res = await router.execute_tool_call(
        AssistantToolExecutionRequest(
            turn_id="turn-9",
            iteration=2,
            tool_call_id="call-slow",
            tool_name="skill_slow_op",
            workspace_id="ws-1",
            user_id="u-1",
            user_role="CONTRIBUTOR",
            arguments={},
        ),
        catalog=cat,
    )
    assert slow_res.verdict == "TIMED_OUT"
    assert slow_res.audit_event_type == "ASSISTANT_TOOL_DENIED"
    assert slow_res.sse_events[-1].event == "tool_result"


class _FakeAsyncRedis:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}

    async def get(self, key: str) -> bytes | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        del ex
        self.data[key] = value.encode("utf-8")


@pytest.mark.asyncio
async def test_edge_branches_redis_store_sandbox_fail_acl_and_error_handling() -> None:
    from orcia_core.agents import build_tool_idempotency_key
    from orcia_core.agents._assistant_profile_guard import resolve_effective_write_gate
    from orcia_core.agents._assistant_tool_audit import record_tool_audit_ledger
    from orcia_core.agents.errors import PolicyDeniedError
    from orcia_core.agents.reflexive_schemas import ReflexiveSessionSnapshot
    from orcia_core.permissions.models import CatalogAclEntry

    snap = ReflexiveSessionSnapshot(
        execution_id="ex-1",
        actor_slug="assistant-agent",
        objective="obj",
        execution_profile="ASSISTANT",
    )
    snap_proc = ReflexiveSessionSnapshot(
        execution_id="ex-2",
        actor_slug="process-agent",
        objective="obj",
        execution_profile="PROCESS",
    )
    with pytest.raises(PolicyDeniedError):
        resolve_effective_write_gate("ASSISTANT", snap, object())  # type: ignore[arg-type]
    with pytest.raises(PolicyDeniedError):
        resolve_effective_write_gate("PROCESS", snap, None)
    assert resolve_effective_write_gate("PROCESS", snap_proc, None) is None

    # RedisToolIdempotencyStore with fake async Redis
    fake_redis = _FakeAsyncRedis()
    store = RedisToolIdempotencyStore()
    store.set_redis_client(fake_redis)
    k = build_tool_idempotency_key(turn_id="t-r", iteration=0, tool_call_id="c-1")
    assert await store.get_cached_result(k) is None
    await store.save_result(k, {"verdict": "EXECUTED", "delimited_output": "ok"})
    cached = await store.get_cached_result(k)
    assert cached is not None and cached["verdict"] == "EXECUTED"

    # Failing audit sink & outbox callbacks log cleanly without crashing
    class _FailingAuditSink:
        async def record_entry(self, entry: Any) -> str:
            del entry
            raise RuntimeError("audit-db-down")

    async def _failing_outbox(evt: Any) -> str | None:
        del evt
        raise RuntimeError("outbox-db-down")

    # READ_SOURCE ACL denial in Step A
    auth_svc = build_default_auth_and_org_service()
    ws = auth_svc.evaluator.workspaces[0]
    contrib = UserIdentity(
        id="u-acl-denied",
        email="acl@orcia.local",
        display_name="ACL User",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id=ws.owner_org_unit_id,
    )
    auth_svc.evaluator._memberships = (
        *auth_svc.evaluator._memberships,
        WorkspaceMembershipEntity(
            id="mem-acl-1",
            workspace_id=ws.id,
            user_id=contrib.id,
            role="CONTRIBUTOR",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
        ),
    )
    auth_svc.evaluator._catalog_acls = (
        *auth_svc.evaluator._catalog_acls,
        CatalogAclEntry(
            id="acl-secret-doc",
            resource_id="res-secret-doc",
            resource_uri="orcia://workspace/secret.md",
            title="Secret Doc",
            visibility_scope="SHARED_WORKSPACE",
            owner_org_unit_id=ws.owner_org_unit_id,
            owner_workspace_id=ws.id,
            can_discover=True,
            can_execute=True,
            can_read_source=False,
        ),
    )

    async def _boom_mcp(desc: Any, req: Any) -> dict[str, Any]:
        del desc, req
        raise RuntimeError("mcp-boom")

    router = GovernedAssistantToolRouter(
        evaluator=auth_svc.evaluator,
        sandbox_port=_FakeSandbox(passed=False),
        audit_ledger_sink=_FailingAuditSink(),
        outbox_enqueue_fn=_failing_outbox,
        mcp_tool_runner_fn=_boom_mcp,
    )
    cat = router.build_authorized_catalog(
        AssistantToolCatalogContext(
            workspace_id=ws.id,
            user_id=contrib.id,
            user_role="CONTRIBUTOR",
            skills=(
                SkillCatalogEntry(
                    skill_id="sk-sb-fail",
                    slug="sb_fail",
                    name="Sandbox Fail",
                    objective="Test sandbox failure",
                    enabled_in_workspace=True,
                ),
            ),
            mcp_tools=(
                McpExposedToolSpec(
                    tool_name="mcp.boom",
                    agent_slug="a",
                    description="Boom MCP",
                    permission_mode="READ_ONLY",
                    required_permission="read",
                ),
            ),
        )
    )

    unauth = await router.execute_tool_call(
        AssistantToolExecutionRequest(
            turn_id="t-edge",
            iteration=0,
            tool_call_id="c-unauth",
            tool_name="nonexistent_tool",
            workspace_id=ws.id,
            user_id=contrib.id,
            arguments={},
        ),
        catalog=cat,
    )
    assert unauth.verdict == "DENIED"

    acl_denied = await router.execute_tool_call(
        AssistantToolExecutionRequest(
            turn_id="t-edge",
            iteration=0,
            tool_call_id="c-acl",
            tool_name="check_resource_state",
            workspace_id=ws.id,
            user_id=contrib.id,
            user_identity=contrib,
            arguments={"resource_uri": "orcia://workspace/secret.md"},
        ),
        catalog=cat,
    )
    assert acl_denied.verdict == "DENIED"
    assert "ERR_READ_SOURCE_DENIED" in acl_denied.delimited_output

    sb_fail = await router.execute_tool_call(
        AssistantToolExecutionRequest(
            turn_id="t-edge",
            iteration=0,
            tool_call_id="c-sb",
            tool_name="skill_sb_fail",
            workspace_id=ws.id,
            user_id=contrib.id,
            user_role="CONTRIBUTOR",
            arguments={},
        ),
        catalog=cat,
    )
    assert sb_fail.verdict == "ERROR"
    assert "SANDBOX_FAILED" in sb_fail.delimited_output

    mcp_err = await router.execute_tool_call(
        AssistantToolExecutionRequest(
            turn_id="t-edge",
            iteration=0,
            tool_call_id="c-mcp",
            tool_name="mcp.boom",
            workspace_id=ws.id,
            user_id=contrib.id,
            user_role="CONTRIBUTOR",
            arguments={"query": "x"},
        ),
        catalog=cat,
    )
    assert mcp_err.verdict == "ERROR"
    assert "mcp-boom" in mcp_err.delimited_output

    # Direct router without explorer/callbacks handles skill/sandbox/unavailable cleanly
    bare_router = GovernedAssistantToolRouter(sandbox_port=_FakeSandbox(passed=True))
    bare_cat = bare_router.build_authorized_catalog(
        AssistantToolCatalogContext(
            workspace_id="",
            user_id="u-bare",
            user_role="CONTRIBUTOR",
            skills=(
                SkillCatalogEntry(
                    skill_id="sk-bare",
                    slug="bare_skill",
                    name="Bare",
                    objective="Bare",
                    enabled_in_workspace=True,
                ),
            ),
            mcp_tools=(
                McpExposedToolSpec(
                    tool_name="mcp.bare",
                    agent_slug="a",
                    description="Bare MCP",
                    permission_mode="READ_ONLY",
                    required_permission="read",
                ),
            ),
        )
    )
    assert (
        await bare_router.execute_tool_call(
            AssistantToolExecutionRequest(
                turn_id="t-bare",
                iteration=0,
                tool_call_id="c-b1",
                tool_name="check_resource_state",
                workspace_id="",
                user_id="u-bare",
                arguments={"resource_uri": "orcia://doc"},
            ),
            catalog=bare_cat,
        )
    ).verdict == "EXECUTED"
    assert (
        await bare_router.execute_tool_call(
            AssistantToolExecutionRequest(
                turn_id="t-bare",
                iteration=0,
                tool_call_id="c-b2",
                tool_name="skill_bare_skill",
                workspace_id="",
                user_id="u-bare",
                user_role="CONTRIBUTOR",
                arguments={},
            ),
            catalog=bare_cat,
        )
    ).verdict == "EXECUTED"
    assert (
        await bare_router.execute_tool_call(
            AssistantToolExecutionRequest(
                turn_id="t-bare",
                iteration=0,
                tool_call_id="c-b3",
                tool_name="mcp.bare",
                workspace_id="",
                user_id="u-bare",
                user_role="CONTRIBUTOR",
                arguments={},
            ),
            catalog=bare_cat,
        )
    ).verdict == "EXECUTED"
    assert (
        await record_tool_audit_ledger(
            sink=None,
            request=AssistantToolExecutionRequest(
                turn_id="t-bare",
                iteration=0,
                tool_call_id="c-b4",
                tool_name="mcp.bare",
                workspace_id="",
                user_id="u-bare",
                arguments={},
            ),
            event_type="ASSISTANT_TOOL_INVOKED",
            verdict="EXECUTED",
            latency_ms=1.0,
        )
        is None
    )
