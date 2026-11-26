"""Unit tests for Story 31.4 P0/P1 router & authorization order guards (`<= 250 L`)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.packs import PackSlotUnboundError
from orcia_core.permissions.models import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)
from orcia_core.workflows.schemas_v2 import WorkflowDefinitionV2

WS_ID = "0195f000-0000-7000-8000-000000000401"
ORG_ID = "0192c4e0-0000-7000-8000-000000000001"


def _isolated_app(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV", "local")
    app = create_app()
    auth_svc = app.state.auth_service
    ev = auth_svc.evaluator
    ev.upsert_org_unit(OrgUnitNode(id=ORG_ID, slug="root", name="R", unit_type="ENTERPRISE"))
    ev.upsert_workspace(
        WorkspaceEntity(
            id=WS_ID,
            slug="ws-314-p0",
            name="WS 314 P0",
            owner_org_unit_id=ORG_ID,
            visibility_mode="STANDARD",
        )
    )
    default_user = auth_svc.resolve_user()
    ev.upsert_membership(
        WorkspaceMembershipEntity(
            id="mem-314-p0-def",
            workspace_id=WS_ID,
            user_id=default_user.id,
            role="TEAM_LEAD",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
        )
    )
    return app


def test_observer_role_in_user_roles_rejected_everywhere(monkeypatch: pytest.MonkeyPatch) -> None:
    """P2-2: `READ_ONLY_OBSERVER` in `user.roles` is rejected (`403`) on packs & workflows."""
    app = _isolated_app(monkeypatch)
    obs_user = UserIdentity(
        id="0195f000-0000-7000-8000-000000000402",
        email="obs-role@orcia.test",
        display_name="Role Observer",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="CONTRIBUTOR",
        roles=("READ_ONLY_OBSERVER",),
        primary_org_unit_id=ORG_ID,
    )
    app.state.auth_service.register_user(obs_user)
    obs_tok = app.state.auth_service.jwt_manager.issue_token_pair(
        user_id=obs_user.id,
        email=obs_user.email,
        role=obs_user.platform_role,
        org_unit_id=ORG_ID,
        archetype=obs_user.human_profile_archetype,
        auth_mode="LOCAL",
    ).access_token
    app.state.auth_service.evaluator.upsert_membership(
        WorkspaceMembershipEntity(
            id="mem-obs-role",
            workspace_id=WS_ID,
            user_id=obs_user.id,
            role="CONTRIBUTOR",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
        )
    )
    client = TestClient(app)
    r_pack = client.post(
        f"/api/v1/workspaces/{WS_ID}/packs/sdlc/activate",
        headers={"Authorization": f"Bearer {obs_tok}"},
        json={},
    )
    assert r_pack.status_code == 403
    assert r_pack.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    r_wf = client.post(
        "/api/v1/workflows/v2/any-wf/runs",
        headers={"Authorization": f"Bearer {obs_tok}"},
        json={"workspace_id": WS_ID, "inputs": {"a": "b"}},
    )
    assert r_wf.status_code == 403
    assert r_wf.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"


def test_workflow_v2_omitted_workspace_fails_closed_and_resolves_slug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P0-3 + P2-3: run-start readiness runs with `workspace_id=None`, & slug resolves to UUID."""
    app = _isolated_app(monkeypatch)
    monkeypatch.setattr(
        "orcia_api.routers._workflows_pack_lock_helpers.is_pg_runtime_active",
        lambda _req: True,
    )
    calls: list[tuple[str | None, str | None]] = []

    class _ReadinessStub:
        def has_engine(self) -> bool:
            return True

        async def enforce_run_start_readiness(
            self,
            *,
            workspace_id: str | None,
            workflow_pack_id: str | None = None,
            instance: str | None = None,
        ) -> list[Any]:
            calls.append((workspace_id, workflow_pack_id))
            if workspace_id is None:
                raise PackSlotUnboundError(
                    pack_slug="alpha-pack", missing_slots=["code-repo"], instance=instance
                )
            return []

        async def pin_run_lock(self, **_kwargs: Any) -> None:
            return None

    app.state.workspace_packs_service = _ReadinessStub()
    wf = WorkflowDefinitionV2(
        id="wf-p03", slug="wf-p03", title="WF P03", pack_id="orcia-pack-alpha"
    )

    class _WfStore:
        async def list_persisted_workflows(self) -> list[WorkflowDefinitionV2]:
            return [wf]

    class _DummyDispatcher:
        async def dispatch(self, *_args: Any, **kwargs: Any) -> Any:
            from orcia_connectors.bounded_workflow_v2 import BoundedWorkflowRunState

            return BoundedWorkflowRunState(
                run_id=kwargs["run_id"],
                workflow_id=wf.id,
                workflow_slug=wf.slug,
                workflow_title=wf.title,
                workflow_version=wf.version,
                orchestration_type=wf.orchestration_type,
                execution_mode=wf.execution_mode,
                status="COMPLETED_APPROVED",
                inputs=kwargs["inputs"],
            )

    app.state.workflows_v2_sql_store = _WfStore()
    app.state.process_execution_dispatcher = _DummyDispatcher()
    client = TestClient(app)

    no_ws = client.post("/api/v1/workflows/v2/wf-p03/runs", json={"inputs": {"x": "1"}})
    assert no_ws.status_code == 422
    assert no_ws.json()["error_code"] == "ERR_PACK_SLOT_UNBOUND"
    assert calls[0] == (None, "orcia-pack-alpha")

    slug_ws = client.post(
        "/api/v1/workflows/v2/wf-p03/runs",
        json={"workspace_id": "ws-314-p0", "inputs": {"x": "1"}},
    )
    assert slug_ws.status_code == 200
    assert calls[1] == (WS_ID, "orcia-pack-alpha")


def test_orchestration_auth_checked_before_pack_slot_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P1-5: `/api/v1/orchestration/runs/instantiate` rejects 403/404 before calling slot guard."""
    app = _isolated_app(monkeypatch)
    monkeypatch.setattr(
        "orcia_api.routers.orchestration.is_pg_runtime_active",
        lambda _req: True,
    )
    readiness_calls: list[tuple[str | None, str | None]] = []

    class _SpyPackSvc:
        def has_engine(self) -> bool:
            return True

        async def enforce_run_start_readiness(
            self, *, workspace_id: str | None, workflow_pack_id: str | None = None, **_kw: Any
        ) -> list[Any]:
            readiness_calls.append((workspace_id, workflow_pack_id))
            raise PackSlotUnboundError(pack_slug="p", missing_slots=["git-repo"])

    app.state.workspace_packs_service = _SpyPackSvc()
    orch_ev = app.state.orchestration_service.evaluator
    if orch_ev is not app.state.auth_service.evaluator:
        orch_ev.upsert_org_unit(
            OrgUnitNode(id=ORG_ID, slug="root", name="R", unit_type="ENTERPRISE")
        )
        orch_ev.upsert_workspace(
            WorkspaceEntity(
                id=WS_ID,
                slug="ws-314-p0",
                name="WS 314 P0",
                owner_org_unit_id=ORG_ID,
                visibility_mode="STANDARD",
            )
        )
        default_user = app.state.auth_service.resolve_user()
        orch_ev.upsert_membership(
            WorkspaceMembershipEntity(
                id="mem-314-p0-orch",
                workspace_id=WS_ID,
                user_id=default_user.id,
                role="TEAM_LEAD",
                access_mode="CONTRIBUTOR_ACTION_REQUIRED",
            )
        )
    other_org = "0192c4e0-0000-7000-8000-000000000099"
    non_member = UserIdentity(
        id="0195f000-0000-7000-8000-000000000403",
        email="outsider@orcia.test",
        display_name="Outsider",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id=other_org,
    )
    app.state.auth_service.register_user(non_member)
    out_tok = app.state.auth_service.jwt_manager.issue_token_pair(
        user_id=non_member.id,
        email=non_member.email,
        role=non_member.platform_role,
        org_unit_id=other_org,
        archetype=non_member.human_profile_archetype,
        auth_mode="LOCAL",
    ).access_token

    client = TestClient(app)
    r_403 = client.post(
        "/api/v1/orchestration/runs/instantiate",
        headers={"Authorization": f"Bearer {out_tok}"},
        json={"workflow_uri": "orcia://packs/alpha/wf/x", "workspace_id": WS_ID},
    )
    assert r_403.status_code == 403
    assert readiness_calls == []

    r_404 = client.post(
        "/api/v1/orchestration/runs/instantiate",
        json={"workflow_uri": "orcia://packs/alpha/wf/missing", "workspace_id": WS_ID},
    )
    assert r_404.status_code == 404
    assert readiness_calls == []
