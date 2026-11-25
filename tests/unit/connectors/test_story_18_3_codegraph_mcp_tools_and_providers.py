"""Story 18.3 — Unit tests for Normalized Read-Only Code Graph MCP Tools & Providers.

Tests:
1. 5 normalized read-only tools on CodegraphMcpConnector and providers.
2. 250 lines ceiling and anti-path-traversal protection on codegraph_read_span.
3. GRAPH_MOVED_SINCE_RUN_LOCK drift detection against run_lock_commit_sha.
4. Provider interchangeability (gitnexus <-> sourcegraph_scip via build_codegraph_provider).
5. Strict workspace isolation, SOURCE_CODE restriction, and codegraph opt-in enforcement.
6. FastAPI endpoints: GET /tools and POST /invoke (RFC 9457 errors on 404/403/422).
7. Integration in wf-03-etude-architecture.yaml and bounded_workflow_v2 execution.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_connectors.adapters.codegraph_mcp import (
    TOOL_DEFINITIONS,
    CodegraphMcpConnector,
)
from orcia_connectors.bounded_workflow_v2 import run_bounded_workflow_v2
from orcia_connectors.codegraph.models import (
    compute_drift_warning,
    validate_read_span_params,
)
from orcia_connectors.codegraph.providers import (
    GitNexusMcpHttpProvider,
    SourcegraphScipMcpProvider,
    build_codegraph_provider,
)
from orcia_connectors.codegraph_tool_runner import (
    async_run_codegraph_blast_radius,
    format_codegraph_markdown_section,
)
from orcia_core.permissions.workspace_sources_governance import WorkspaceDatasourceRecord
from orcia_core.workflows.schemas_v2 import WorkflowDefinitionV2


def _make_dummy_sources() -> list[WorkspaceDatasourceRecord]:
    return [
        WorkspaceDatasourceRecord(
            id="ds-git-ok",
            workspace_id="ws-crl-1",
            alias="mon-compte-backend",
            scheme="git",
            uri="git://github.com/mon-compte/backend.git",
            source_nature="SOURCE_CODE",
            codegraph_enabled=True,
            codegraph_status="READY",
            codegraph_head_sha="sha-head-111",
        ),
        WorkspaceDatasourceRecord(
            id="ds-git-disabled",
            workspace_id="ws-crl-1",
            alias="legacy-repo",
            scheme="git",
            uri="git://github.com/mon-compte/legacy.git",
            source_nature="SOURCE_CODE",
            codegraph_enabled=False,
            codegraph_status="DISABLED",
        ),
        WorkspaceDatasourceRecord(
            id="ds-doc-kb",
            workspace_id="ws-crl-1",
            alias="doc-wiki",
            scheme="confluence",
            uri="confluence://wiki.intra/spaces/ARCHI",
            source_nature="DOCUMENT_KB",
            codegraph_enabled=True,
            codegraph_status="READY",
        ),
    ]


@pytest.mark.asyncio
async def test_codegraph_read_span_boundary_and_anti_traversal() -> None:
    """Verify max 250 lines ceiling and rejection of directory traversal / absolute paths."""
    validate_read_span_params("src/main.py", 1, 100)
    validate_read_span_params("src/main.py", 1, 250)

    with pytest.raises(ValueError, match="exceeds maximum limit of 250 lines"):
        validate_read_span_params("src/main.py", 1, 251)

    with pytest.raises(ValueError, match="cannot be less than start_line"):
        validate_read_span_params("src/main.py", 50, 40)

    with pytest.raises(ValueError, match="start_line must be >= 1"):
        validate_read_span_params("src/main.py", 0, 10)

    for bad in [
        "../secrets.py",
        "sub/../../etc/passwd",
        "/etc/shadow",
        "\\windows\\win.ini",
        "main\x00.py",
    ]:
        with pytest.raises(ValueError, match="traversal or absolute path detected"):
            validate_read_span_params(bad, 1, 10)


def test_compute_drift_warning_deterministic() -> None:
    """Verify GRAPH_MOVED_SINCE_RUN_LOCK is computed only when run_lock commit differs."""
    assert (
        compute_drift_warning(indexed_commit_sha="sha-A", run_lock_commit_sha="sha-B")
        == "GRAPH_MOVED_SINCE_RUN_LOCK"
    )
    assert compute_drift_warning(indexed_commit_sha="sha-A", run_lock_commit_sha="sha-A") is None
    assert compute_drift_warning(indexed_commit_sha="sha-A", run_lock_commit_sha=None) is None
    assert compute_drift_warning(indexed_commit_sha=None, run_lock_commit_sha="sha-B") is None


def test_provider_interchangeability_gitnexus_and_scip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify build_codegraph_provider switches cleanly based on CODEGRAPH_PROVIDER."""
    monkeypatch.setenv("CODEGRAPH_PROVIDER", "gitnexus")
    p1 = build_codegraph_provider()
    assert isinstance(p1, GitNexusMcpHttpProvider)
    assert p1.provider_name == "gitnexus"

    monkeypatch.setenv("CODEGRAPH_PROVIDER", "sourcegraph_scip")
    p2 = build_codegraph_provider()
    assert isinstance(p2, SourcegraphScipMcpProvider)
    assert p2.provider_name == "sourcegraph_scip"


@pytest.mark.asyncio
async def test_codegraph_mcp_connector_5_tools_execution() -> None:
    """Verify 5 normalized read-only tools on CodegraphMcpConnector with mock source resolver."""
    dummy_sources = _make_dummy_sources()
    conn = CodegraphMcpConnector(
        provider=SourcegraphScipMcpProvider(),
        workspace_id="ws-crl-1",
        datasources_resolver=lambda _ws: dummy_sources,
    )

    sym = await conn.invoke_tool(
        "codegraph_locate_symbol",
        {"repo_alias": "mon-compte-backend", "query": "UserProfile"},
        workspace_id="ws-crl-1",
    )
    assert sym["repo_alias"] == "mon-compte-backend"

    call_hier = await conn.invoke_tool(
        "codegraph_get_call_hierarchy",
        {"repo_alias": "mon-compte-backend", "symbol": "login", "file_path": "auth.py"},
        workspace_id="ws-crl-1",
    )
    assert call_hier["symbol"] == "login"

    refs = await conn.invoke_tool(
        "codegraph_find_references",
        {"repo_alias": "mon-compte-backend", "symbol": "UserProfile"},
        workspace_id="ws-crl-1",
    )
    assert refs["symbol"] == "UserProfile"

    blast = await conn.invoke_tool(
        "codegraph_calculate_blast_radius",
        {
            "repo_alias": "mon-compte-backend",
            "modified_files": ["src/auth.py", "src/models.py"],
            "run_lock_commit_sha": "different-sha",
        },
        workspace_id="ws-crl-1",
    )
    assert blast["blast_radius_score"] >= 0.5
    assert blast["drift_warning"] == "GRAPH_MOVED_SINCE_RUN_LOCK"

    span = await conn.invoke_tool(
        "codegraph_read_span",
        {
            "repo_alias": "mon-compte-backend",
            "file_path": "src/main.py",
            "start_line": 10,
            "end_line": 20,
        },
        workspace_id="ws-crl-1",
    )
    assert span["total_lines"] == 11


@pytest.mark.asyncio
async def test_codegraph_mcp_connector_confinement_and_rejections() -> None:
    """Verify workspace confinement and opt-in security rejections."""
    dummy_sources = _make_dummy_sources()
    conn = CodegraphMcpConnector(
        provider=SourcegraphScipMcpProvider(),
        workspace_id="ws-crl-1",
        datasources_resolver=lambda _ws: dummy_sources,
    )

    with pytest.raises(PermissionError, match="not attached to workspace"):
        await conn.invoke_tool(
            "codegraph_locate_symbol",
            {"repo_alias": "unknown-repo", "query": "x"},
            workspace_id="ws-crl-1",
        )

    with pytest.raises(PermissionError, match="not of nature SOURCE_CODE"):
        await conn.invoke_tool(
            "codegraph_locate_symbol",
            {"repo_alias": "doc-wiki", "query": "x"},
            workspace_id="ws-crl-1",
        )

    with pytest.raises(PermissionError, match="Codegraph is not enabled"):
        await conn.invoke_tool(
            "codegraph_locate_symbol",
            {"repo_alias": "legacy-repo", "query": "x"},
            workspace_id="ws-crl-1",
        )


def test_fastapi_codegraph_endpoints() -> None:
    """Verify FastAPI GET /tools and POST /invoke endpoints."""
    from orcia_core.permissions.models import WorkspaceEntity

    app = create_app()
    default_user = app.state.auth_service.resolve_user()
    app.state.auth_service.evaluator.upsert_workspace(
        WorkspaceEntity(
            id="ws-test-123",
            slug="ws-test-123",
            name="Codegraph Test WS",
            owner_org_unit_id=default_user.primary_org_unit_id,
            visibility_mode="STANDARD",
        )
    )
    client = TestClient(app)

    # 1. GET /tools
    resp_tools = client.get("/api/v1/workspaces/ws-test-123/codegraph/tools")
    assert resp_tools.status_code == 200
    data_tools = resp_tools.json()
    assert data_tools["workspace_id"] == "ws-test-123"
    assert len(data_tools["tools"]) == len(TOOL_DEFINITIONS)
    tool_names = [t["name"] for t in data_tools["tools"]]
    assert "codegraph_calculate_blast_radius" in tool_names

    # 2. POST /invoke with non-existent repo in unattached workspace -> 404
    resp_invoke = client.post(
        "/api/v1/workspaces/ws-test-123/codegraph/invoke",
        json={
            "tool_name": "codegraph_locate_symbol",
            "arguments": {"repo_alias": "ghost-repo", "query": "sym"},
        },
    )
    assert resp_invoke.status_code == 404
    err_body = resp_invoke.json()
    assert err_body["error_code"] == "ERR_RESOURCE_NOT_FOUND"

    # 3. POST /invoke with invalid line span > 250 -> 422
    resp_inv_422 = client.post(
        "/api/v1/workspaces/ws-test-123/codegraph/invoke",
        json={
            "tool_name": "codegraph_read_span",
            "arguments": {
                "repo_alias": "ghost-repo",
                "file_path": "../etc/passwd",
                "start_line": 1,
                "end_line": 300,
            },
        },
    )
    assert resp_inv_422.status_code == 422


def test_wf_03_etude_architecture_yaml_and_workflow_runner() -> None:
    """Verify wf-03-etude-architecture.yaml has mcp:codegraph and bounded_workflow_v2 runs it."""
    wf_path = Path("packs/sdlc/workflows/wf-03-etude-architecture.yaml")
    assert wf_path.exists()
    content = yaml.safe_load(wf_path.read_text(encoding="utf-8"))

    comprendre_step = next(s for s in content["sub_steps"] if s["id"] == "comprendre")
    mcp_perms = comprendre_step.get("toolbox_mcp_permissions", [])
    assert any(p["connector_id"] == "mcp:codegraph" and p["scope"] == "read" for p in mcp_perms)

    wf_def = WorkflowDefinitionV2.model_validate(content)
    run_state = run_bounded_workflow_v2(
        wf_def,
        run_id="run-test-blast-1",
        inputs={
            "repo_alias": "mon-compte-crl",
            "modified_files": ["apps/api/main.py", "packages/core/models.py"],
            "run_lock_commit_sha": "locked-sha-abc",
            "indexed_commit_sha": "indexed-sha-xyz",
        },
        auto_approve_checkpoints=True,
    )

    assert run_state.status == "COMPLETED_APPROVED"
    assert len(run_state.sub_step_records) >= 1
    step_0 = run_state.sub_step_records[0]
    assert step_0.codegraph_impact is not None
    assert step_0.codegraph_impact["drift_warning"] == "GRAPH_MOVED_SINCE_RUN_LOCK"

    audit_events = [a["event"] for a in run_state.audit_trail]
    assert "CODEGRAPH_TOOL_EXECUTED" in audit_events

    md_section = format_codegraph_markdown_section(step_0.codegraph_impact)
    assert "Rayon d'Impact Code Graph" in md_section
    assert "GRAPH_MOVED_SINCE_RUN_LOCK" in md_section


@pytest.mark.asyncio
async def test_codegraph_mcp_connector_read_api_and_edge_cases() -> None:
    """Verify read() method, tools discovery, and missing argument validation."""
    dummy_sources = _make_dummy_sources()
    dummy_sources.append(
        WorkspaceDatasourceRecord(
            id="ds-paused",
            workspace_id="ws-crl-1",
            alias="paused-repo",
            scheme="git",
            uri="git://github.com/mon-compte/paused.git",
            source_nature="SOURCE_CODE",
            codegraph_enabled=True,
            codegraph_status="PAUSED_REFERENT_RENEWAL_REQUIRED",
        )
    )

    async def _async_resolver(_ws: str) -> list[WorkspaceDatasourceRecord]:
        return dummy_sources

    conn = CodegraphMcpConnector(
        provider=SourcegraphScipMcpProvider(),
        workspace_id="ws-crl-1",
        datasources_resolver=_async_resolver,
    )

    # 1. read("tools")
    t1 = await conn.read("tools")
    assert len(t1["tools"]) == 5
    t2 = await conn.read("codegraph://tools")
    assert len(t2["tools"]) == 5

    # 2. read tool invocation
    res_read = await conn.read(
        "codegraph://codegraph_locate_symbol",
        {"query": "Test", "repo_alias": "mon-compte-backend"},
    )
    assert res_read["query"] == "Test"

    # 3. PAUSED_REFERENT_RENEWAL_REQUIRED
    with pytest.raises(PermissionError, match="inactive for repository"):
        await conn.invoke_tool(
            "codegraph_locate_symbol",
            {"query": "Test", "repo_alias": "paused-repo"},
            workspace_id="ws-crl-1",
        )

    # 4. Missing arguments
    from orcia_core.kernel.errors import ValidationDomainError

    with pytest.raises(ValidationDomainError, match="repo_alias is required"):
        await conn.invoke_tool("codegraph_locate_symbol", {}, workspace_id="ws-crl-1")

    with pytest.raises(ValidationDomainError, match="query is required"):
        await conn.invoke_tool(
            "codegraph_locate_symbol", {"repo_alias": "mon-compte-backend"}, workspace_id="ws-crl-1"
        )

    with pytest.raises(ValidationDomainError, match="symbol and file_path are required"):
        await conn.invoke_tool(
            "codegraph_get_call_hierarchy",
            {"repo_alias": "mon-compte-backend"},
            workspace_id="ws-crl-1",
        )

    with pytest.raises(ValidationDomainError, match="symbol is required"):
        await conn.invoke_tool(
            "codegraph_find_references",
            {"repo_alias": "mon-compte-backend"},
            workspace_id="ws-crl-1",
        )

    with pytest.raises(ValidationDomainError, match="modified_files must be a list"):
        await conn.invoke_tool(
            "codegraph_calculate_blast_radius",
            {"repo_alias": "mon-compte-backend", "modified_files": "not-a-list"},
            workspace_id="ws-crl-1",
        )

    with pytest.raises(ValidationDomainError, match="Unknown codegraph tool"):
        await conn.invoke_tool(
            "codegraph_unknown_tool",
            {"repo_alias": "mon-compte-backend"},
            workspace_id="ws-crl-1",
        )

    # 5. async_run_codegraph_blast_radius with connector injected
    from orcia_core.workflows.schemas_v2 import DeterministicSubStepSpec

    sub_step = DeterministicSubStepSpec(
        id="step-perm",
        name="Perm",
        short_label="P",
        trigger_condition_label="on",
        role_description="role",
        instruction_prompt_or_ref="prompt",
        output_description="out",
        checkpoint_label="cp",
        toolbox_mcp_permissions=[{"connector_id": "mcp:codegraph", "scope": "read"}],
    )
    blast_res = await async_run_codegraph_blast_radius(
        sub_step,
        {"repo_alias": "mon-compte-backend", "modified_files": ["src/app.py"]},
        workspace_id="ws-crl-1",
        connector=conn,
    )
    assert blast_res is not None
    assert blast_res["repo_alias"] == "mon-compte-backend"
