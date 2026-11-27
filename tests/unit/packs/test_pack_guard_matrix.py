"""Table-driven guard matrix & service delegation tests for Declarative Packs (`31.4`/`31.5`)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from uuid_utils import uuid7

from orcia_core.packs import (
    EffectiveSlotBindingView,
    PackSlotSpec,
    PackSlotTargetKind,
    PinnedPackManifestEntry,
    WorkspacePacksService,
)
from orcia_core.packs._internal._sql_run_lock_reads import map_v2_status_to_workflow_run_status
from orcia_core.packs.errors import EntityReferencedByPackDraftError
from orcia_core.packs.slot_guard import is_binding_compatible_with_slot
from orcia_core.permissions.models import (
    OrgUnitNode,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)

pytestmark = [pytest.mark.story("31.4"), pytest.mark.story("31.5"), pytest.mark.story("32.4")]

WS_A = "0195f000-0000-7000-8000-000000000601"
WS_B = "0195f000-0000-7000-8000-000000000602"
ORG_ROOT = "0192c4e0-0000-7000-8000-000000000001"
ORG_B = "0192c4e0-0000-7000-8000-000000000699"


def _configure_ws_matrix(app: FastAPI) -> tuple[str, str]:
    auth_svc = app.state.auth_service
    marc = auth_svc.resolve_user(persona_key="marc")
    ev = auth_svc.evaluator
    ev.upsert_org_unit(OrgUnitNode(id=ORG_ROOT, slug="root", name="R", unit_type="ENTERPRISE"))
    ev.upsert_org_unit(OrgUnitNode(id=ORG_B, slug="org-b", name="B", unit_type="BU"))
    ev.upsert_workspace(
        WorkspaceEntity(id=WS_A, slug="ws-a", name="WS A", owner_org_unit_id=ORG_ROOT)
    )
    ev.upsert_workspace(WorkspaceEntity(id=WS_B, slug="ws-b", name="WS B", owner_org_unit_id=ORG_B))
    ev.upsert_membership(
        WorkspaceMembershipEntity(
            id="m-m-a",
            workspace_id=WS_A,
            user_id=marc.id,
            role="TEAM_LEAD",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
        )
    )
    tok_marc = auth_svc.jwt_manager.issue_token_pair(
        user_id=marc.id,
        email=marc.email,
        role=marc.platform_role,
        org_unit_id=marc.primary_org_unit_id,
        archetype=marc.human_profile_archetype,
        auth_mode="LOCAL",
    ).access_token
    claire = auth_svc.resolve_user(persona_key="claire")
    tok_obs = auth_svc.jwt_manager.issue_token_pair(
        user_id=claire.id,
        email=claire.email,
        role=claire.platform_role,
        org_unit_id=claire.primary_org_unit_id,
        archetype=claire.human_profile_archetype,
        auth_mode="LOCAL",
    ).access_token
    return tok_marc, tok_obs


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "method", "path", "body", "expected_code"),
    [
        (
            "observer",
            "POST",
            f"/api/v1/workspaces/{WS_A}/packs/sdlc/activate",
            {},
            "ERR_OBSERVER_MODE_READ_ONLY",
        ),
        (
            "observer",
            "DELETE",
            f"/api/v1/workspaces/{WS_A}/packs/sdlc/deactivate",
            None,
            "ERR_OBSERVER_MODE_READ_ONLY",
        ),
        (
            "observer",
            "PUT",
            f"/api/v1/workspaces/{WS_A}/packs/reorder",
            {"ordered_pack_slugs": ["sdlc"]},
            "ERR_OBSERVER_MODE_READ_ONLY",
        ),
        (
            "observer",
            "PUT",
            f"/api/v1/workspaces/{WS_A}/packs/sdlc/slots",
            {"bindings": [{"slot_key": "git_repo", "target_kind": "UNBOUND"}]},
            "ERR_OBSERVER_MODE_READ_ONLY",
        ),
        (
            "observer",
            "POST",
            "/api/v1/packs/composer",
            {"slug": "x", "name": "X", "scope_type": "WORKSPACE", "scope_id": WS_A},
            "ERR_OBSERVER_MODE_READ_ONLY",
        ),
        (
            "observer",
            "DELETE",
            "/api/v1/agents-and-skills/agents/ag-1?unlink_from_draft_packs=true",
            None,
            "ERR_OBSERVER_MODE_READ_ONLY",
        ),
        (
            "observer",
            "DELETE",
            "/api/v1/workflows/v2/wf-1?unlink_from_draft_packs=true",
            None,
            "ERR_OBSERVER_MODE_READ_ONLY",
        ),
        (
            "cross_tenant",
            "GET",
            f"/api/v1/workspaces/{WS_B}/packs",
            None,
            "ERR_SCOPE_ACCESS_DENIED",
        ),
        (
            "cross_tenant",
            "POST",
            f"/api/v1/workspaces/{WS_B}/packs/sdlc/activate",
            {},
            "ERR_SCOPE_ACCESS_DENIED",
        ),
        (
            "cross_tenant",
            "PUT",
            f"/api/v1/workspaces/{WS_B}/packs/sdlc/slots",
            {"bindings": [{"slot_key": "git_repo", "target_kind": "UNBOUND"}]},
            "ERR_SCOPE_ACCESS_DENIED",
        ),
        (
            "cross_tenant",
            "POST",
            "/api/v1/packs/composer",
            {"slug": "x", "name": "X", "scope_type": "WORKSPACE", "scope_id": WS_B},
            "ERR_SCOPE_ACCESS_DENIED",
        ),
    ],
)
async def test_pack_routes_observer_and_cross_tenant_403_matrix(
    seeded_test_app: FastAPI,
    mode: str,
    method: str,
    path: str,
    body: dict[str, Any] | None,
    expected_code: str,
) -> None:
    """Enforce 403 observer and cross-tenant guards across pack & composer endpoints."""
    tok_marc, tok_obs = _configure_ws_matrix(seeded_test_app)
    hdr = {"Authorization": f"Bearer {tok_obs if mode == 'observer' else tok_marc}"}
    async with AsyncClient(
        transport=ASGITransport(app=seeded_test_app), base_url="http://test"
    ) as client:
        resp = await client.request(method, path, headers=hdr, json=body)
    assert resp.status_code == 403, f"{mode} {method} {path}: {resp.text}"
    assert resp.json()["error_code"] == expected_code


@pytest.mark.asyncio
async def test_anti_hostage_409_error_contract_and_slot_compatibility() -> None:
    """Verify anti-hostage 409 error payload, slot compatibility & status mapper."""
    err = EntityReferencedByPackDraftError(
        draft_packs=[{"bundle_id": str(uuid7()), "pack_slug": "draft-p", "version": "0.1.0"}],
    )
    assert err.http_status == 409
    assert err.error_code == "ERR_ENTITY_REFERENCED_BY_PACK_DRAFT"
    assert len(err.draft_packs) == 1
    assert (
        map_v2_status_to_workflow_run_status("WAITING_FOR_HUMAN_ARBITRATION")
        == "WAITING_FOR_HUMAN_ARBITRATION"
    )
    assert (
        map_v2_status_to_workflow_run_status("PAUSED_BUDGET_EXCEEDED") == "PAUSED_BUDGET_EXCEEDED"
    )
    assert not is_binding_compatible_with_slot(
        EffectiveSlotBindingView(
            workspace_id=WS_A,
            pack_slug="p",
            slot_key="k",
            target_kind=PackSlotTargetKind.INTERNAL,
            is_effective_bound=True,
        ),
        PackSlotSpec(slot_key="k", scheme="git"),
    )


@pytest.mark.asyncio
async def test_workspace_packs_service_delegates_without_fake_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `WorkspacePacksService` delegates cleanly when engine is configured."""
    svc = WorkspacePacksService()
    svc.set_engine(object())  # type: ignore[arg-type]
    assert svc.has_engine() is True

    mod_path = "orcia_core.packs.workspace_packs_service"
    for fn_name in (
        "list_workspace_packs_sql",
        "bind_workspace_pack_slots_sql",
        "activate_workspace_pack_sql",
        "deactivate_workspace_pack_sql",
        "reorder_workspace_packs_sql",
        "validate_and_snapshot_workspace_packs_sql",
        "pin_workflow_v2_run_lock_sql",
        "sync_workflow_v2_run_status_sql",
        "attach_pinned_packs_to_run_lock_sql",
        "get_run_lock_manifest_sql",
    ):
        monkeypatch.setattr(f"{mod_path}.{fn_name}", AsyncMock(return_value=[]))

    entry = PinnedPackManifestEntry(
        pack_bundle_id="b1",
        pack_slug="alpha",
        version="1.0.0",
        archive_sha256="a" * 64,
        priority_order=1,
    )
    assert await svc.list_workspace_packs(WS_A) == []
    assert (
        await svc.bind_pack_slots(workspace_id=WS_A, pack_slug="a", bindings=[], actor_id="u") == []
    )
    await svc.activate_pack(workspace_id=WS_A, pack_slug="a", actor_id="u")
    await svc.deactivate_pack(workspace_id=WS_A, pack_slug="a", actor_id="u")
    await svc.reorder_packs(workspace_id=WS_A, ordered_pack_slugs=["a"], actor_id="u")
    await svc.enforce_run_start_readiness(workspace_id=WS_A)
    await svc.pin_run_lock(
        run_id="run-1",
        workspace_id=WS_A,
        workflow_id="w",
        workflow_slug="w",
        workflow_version="1",
        workflow_sha256="a" * 64,
        status="RUNNING",
        actor_user_id=None,
        pinned_packs=[],
    )
    await svc.sync_run_status(run_id="run-1", status="COMPLETED")
    await svc.attach_pinned_packs_to_run_lock(run_id="run-1", pinned_packs=[entry])
    await svc.get_run_lock(run_id="run-1")
