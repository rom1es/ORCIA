"""Unit tests for Story 31.4 workspace pack activation, slots & run-lock endpoints."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.packs import (
    EffectiveSlotBindingView,
    PackSlotSpec,
    PackSlotTargetKind,
    PackSlotUnboundError,
    SlotBindingInput,
    WorkspacePackView,
)
from orcia_core.permissions.models import (
    OrgUnitNode,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)
from orcia_core.workflows.schemas_v2 import WorkflowDefinitionV2

WS_ID = "0195f000-0000-7000-8000-000000000301"
RUN_ID = "run-0195f000-0000-7000-8000-000000000999"


def _make_isolated_app(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV", "local")
    app = create_app()
    auth_svc = app.state.auth_service
    default_user = auth_svc.resolve_user()
    karim = auth_svc.resolve_user(persona_key="karim")
    ev = auth_svc.evaluator
    org_id = "0192c4e0-0000-7000-8000-000000000001"
    ev.upsert_org_unit(OrgUnitNode(id=org_id, slug="root", name="R", unit_type="ENTERPRISE"))
    ev.upsert_workspace(
        WorkspaceEntity(
            id=WS_ID,
            slug="ws-314-unit",
            name="WS 314 Unit",
            owner_org_unit_id=org_id,
            visibility_mode="STANDARD",
        )
    )
    for idx, uid in enumerate({default_user.id, karim.id}):
        ev.upsert_membership(
            WorkspaceMembershipEntity(
                id=f"mem-314-{idx}",
                workspace_id=WS_ID,
                user_id=uid,
                role="TEAM_LEAD",
                access_mode="CONTRIBUTOR_ACTION_REQUIRED",
            )
        )
    return app


class _StubWorkspacePacksService:
    def __init__(self, *, fail_missing_slot: bool = False) -> None:
        self.fail_missing_slot = fail_missing_slot
        self.bound_calls: list[tuple[str, str, list[SlotBindingInput]]] = []
        self.reordered: list[str] = []

    def has_engine(self) -> bool:
        return True

    async def list_workspace_packs(self, _ws: str, **_kw: Any) -> list[WorkspacePackView]:
        return [
            WorkspacePackView(
                bundle_id="0195f000-0000-7000-8000-000000000801",
                pack_id="orcia-pack-sdlc",
                slug="sdlc",
                name="SDLC Pack",
                version="2.4.0",
                bundle_kind="SYSTEM",
                scope_type="GLOBAL",
                scope_id="global",
                status="PUBLISHED",
                archive_sha256="a" * 64,
                is_active=True,
                priority_order=1,
                declared_slots=[PackSlotSpec(slot_key="git-repo", scheme="git", required=True)],
                missing_slots=["git-repo"] if self.fail_missing_slot else [],
                readiness_ok=not self.fail_missing_slot,
            )
        ]

    async def activate_pack(
        self, *, workspace_id: str, pack_slug: str, **_kw: Any
    ) -> dict[str, Any]:
        if self.fail_missing_slot:
            raise PackSlotUnboundError(pack_slug=pack_slug, missing_slots=["git-repo"])
        return {
            "activation_id": "act-1",
            "workspace_id": workspace_id,
            "pack_bundle_id": "b-1",
            "pack_slug": pack_slug,
            "version": "2.4.0",
            "priority_order": 1,
            "is_active": True,
            "activated_at_iso": "2026-11-26T12:00:00Z",
        }

    async def deactivate_pack(
        self, *, workspace_id: str, pack_slug: str, **_kw: Any
    ) -> dict[str, Any]:
        return {
            "workspace_id": workspace_id,
            "pack_bundle_id": "b-1",
            "pack_slug": pack_slug,
            "is_active": False,
        }

    async def reorder_packs(
        self, *, ordered_pack_slugs: Sequence[str], **_kw: Any
    ) -> list[dict[str, Any]]:
        self.reordered = list(ordered_pack_slugs)
        return [
            {"pack_slug": s, "pack_bundle_id": f"b-{i}", "priority_order": i}
            for i, s in enumerate(ordered_pack_slugs, start=1)
        ]

    async def bind_pack_slots(
        self,
        *,
        workspace_id: str,
        pack_slug: str,
        bindings: Sequence[SlotBindingInput],
        **_kw: Any,
    ) -> list[EffectiveSlotBindingView]:
        self.bound_calls.append((workspace_id, pack_slug, list(bindings)))
        return [
            EffectiveSlotBindingView(
                id="bind-1",
                workspace_id=workspace_id,
                pack_bundle_id="b-1",
                pack_slug=pack_slug,
                slot_key=b.slot_key,
                target_kind=b.target_kind,
                target_id=b.target_id,
                bound_datasource_id=(
                    b.target_id
                    if b.target_kind == PackSlotTargetKind.WORKSPACE_DATASOURCE
                    else None
                ),
                connector_scheme=b.connector_scheme or "git",
                bound_by="u-admin",
                bound_at_iso="2026-11-26T12:00:00Z",
                is_effective_bound=(b.target_kind != PackSlotTargetKind.UNBOUND),
            )
            for b in bindings
        ]

    async def enforce_run_start_readiness(self, **_kw: Any) -> list[Any]:
        if self.fail_missing_slot:
            raise PackSlotUnboundError(pack_slug="sdlc", missing_slots=["git-repo"])
        return []

    async def get_run_lock(self, *, run_id: str) -> dict[str, Any] | None:
        if run_id != RUN_ID:
            return None
        p = {"pack_bundle_id": "b-1", "pack_slug": "sdlc", "version": "2.4.0"}
        p.update({"archive_sha256": "a" * 64, "priority_order": 1, "resolved_pack_slots": []})
        return {
            "run_id": RUN_ID,
            "workspace_id": WS_ID,
            "workflow_id": "wf-1",
            "workflow_slug": "wf-1",
            "workflow_version": "1.0.0",
            "pinned_packs": [p],
            "resolved_pack_slots": [],
            "manifest_sha256": "c" * 64,
            "locked_at_iso": "2026-11-26T12:00:00Z",
        }


def test_workspace_packs_router_happy_paths_422_and_observer_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify GET/activate/deactivate/reorder/slots/run-lock routes & RFC 9457 guards."""
    app = _make_isolated_app(monkeypatch)
    stub = _StubWorkspacePacksService(fail_missing_slot=True)
    app.state.workspace_packs_service = stub
    client = TestClient(app)

    # Observer blocked on all mutations
    for method, url, payload in (
        ("post", f"/api/v1/workspaces/{WS_ID}/packs/sdlc/activate", {}),
        ("delete", f"/api/v1/workspaces/{WS_ID}/packs/sdlc/deactivate", None),
        ("put", f"/api/v1/workspaces/{WS_ID}/packs/reorder", {"ordered_pack_slugs": ["sdlc"]}),
        (
            "put",
            f"/api/v1/workspaces/{WS_ID}/packs/sdlc/slots",
            {"bindings": [{"slot_key": "git-repo", "target_kind": "INTERNAL"}]},
        ),
    ):
        kwargs: dict[str, Any] = {"headers": {"x-orcia-access-mode": "READ_ONLY_OBSERVER"}}
        if payload is not None:
            kwargs["json"] = payload
        resp = getattr(client, method)(url, **kwargs)
        assert resp.status_code == 403
        assert resp.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    # Unknown workspace -> 404
    missing_ws = client.get("/api/v1/workspaces/0195f000-0000-7000-8000-00000000ffff/packs")
    assert missing_ws.status_code == 404

    # List shows missing_slots
    list_resp = client.get(f"/api/v1/workspaces/{WS_ID}/packs")
    assert list_resp.status_code == 200
    assert list_resp.json()["packs"][0]["missing_slots"] == ["git-repo"]

    # Activate with unbound required slot -> 422 ERR_PACK_SLOT_UNBOUND
    act_err = client.post(
        f"/api/v1/workspaces/{WS_ID}/packs/sdlc/activate",
        headers={"Accept-Language": "fr"},
    )
    assert act_err.status_code == 422
    assert act_err.json()["error_code"] == "ERR_PACK_SLOT_UNBOUND"
    assert "git-repo" in act_err.json()["detail"]

    # Bind slot -> activate -> reorder -> deactivate -> get run lock
    bind_payload = {
        "bindings": [
            {"slot_key": "git-repo", "target_kind": "WORKSPACE_DATASOURCE", "target_id": "d1"}
        ]
    }
    bind_resp = client.put(f"/api/v1/workspaces/{WS_ID}/packs/sdlc/slots", json=bind_payload)
    assert bind_resp.status_code == 200
    assert bind_resp.json()["slot_bindings"][0]["is_effective_bound"] is True

    stub.fail_missing_slot = False
    act_ok = client.post(f"/api/v1/workspaces/{WS_ID}/packs/sdlc/activate", json={})
    assert act_ok.status_code == 200 and act_ok.json()["priority_order"] == 1
    reord = client.put(
        f"/api/v1/workspaces/{WS_ID}/packs/reorder",
        json={"ordered_pack_slugs": ["orcia-docs", "sdlc"]},
    )
    assert [p["pack_slug"] for p in reord.json()["packs"]] == ["orcia-docs", "sdlc"]
    deact = client.delete(f"/api/v1/workspaces/{WS_ID}/packs/sdlc/deactivate")
    assert deact.status_code == 200 and deact.json()["is_active"] is False
    lock_resp = client.get(f"/api/v1/runs/{RUN_ID}/lock")
    assert lock_resp.status_code == 200
    assert lock_resp.json()["pinned_packs"][0]["pack_slug"] == "sdlc"
    missing_lock_url = "/api/v1/runs/run-0195f000-0000-7000-8000-000000000000/lock"
    assert client.get(missing_lock_url).status_code == 404


def test_workflow_v2_run_start_fails_closed_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Workflow-v2 run start must reject 422 ERR_PACK_SLOT_UNBOUND before calling dispatcher."""
    app = _make_isolated_app(monkeypatch)
    monkeypatch.setattr(
        "orcia_api.routers._workflows_pack_lock_helpers.is_pg_runtime_active",
        lambda _req: True,
    )
    stub = _StubWorkspacePacksService(fail_missing_slot=True)
    app.state.workspace_packs_service = stub

    wf = WorkflowDefinitionV2(
        id="wf-314-test", slug="wf-314-test", title="WF 31.4 Test", pack_id="orcia-pack-sdlc"
    )

    class _StubWfStore:
        async def list_persisted_workflows(self) -> list[WorkflowDefinitionV2]:
            return [wf]

    class _SpyDispatcher:
        called = False

        async def dispatch(self, *_args: Any, **_kwargs: Any) -> Any:
            self.called = True
            raise AssertionError("dispatcher must not be called")

    spy = _SpyDispatcher()
    app.state.workflows_v2_sql_store = _StubWfStore()
    app.state.process_execution_dispatcher = spy

    client = TestClient(app)
    resp = client.post(
        "/api/v1/workflows/v2/wf-314-test/runs",
        json={"workspace_id": WS_ID, "inputs": {"objective": "Ship"}},
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "ERR_PACK_SLOT_UNBOUND"
    assert "git-repo" in resp.json()["detail"]
    assert spy.called is False
