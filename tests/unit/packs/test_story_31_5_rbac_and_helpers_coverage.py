"""Unit tests covering Story 31.5 RBAC guards, composer helpers & extra scope targets."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request as StarletteRequest

from orcia_api.main import create_app
from orcia_api.routers._pack_composer_helpers import (
    compute_caller_composer_scopes,
    enforce_composer_scope_access,
    execute_export_pack_zip_handler,
    serialize_closure_report,
)
from orcia_core.packs import (
    ClosureMissingDependency,
    PackClosureReport,
    PackDraftDetail,
    PackScopeEscalationForbiddenError,
    ProseLintWarning,
)
from orcia_core.permissions.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError
from orcia_core.permissions.models import (
    OrgUnitNode,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)


@pytest.mark.asyncio
async def test_composer_helpers_scopes_observer_export_and_serialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover every branch of `_pack_composer_helpers.py` and `DELETE` RBAC / legacy export."""
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV", "local")
    app: FastAPI = create_app()
    org_root = "0192c4e0-0000-7000-8000-000000000001"
    org_bu = "0192c4e0-0000-7000-8000-000000000099"
    ws_priv = "0195f000-0000-7000-8000-000000000388"
    ws_pub = "0195f000-0000-7000-8000-000000000389"
    auth_svc = app.state.auth_service
    marc = auth_svc.resolve_user(persona_key="marc")
    claire = auth_svc.resolve_user(persona_key="claire")
    ev = auth_svc.evaluator
    ev.upsert_org_unit(OrgUnitNode(id=org_root, slug="root", name="Root", unit_type="ENTERPRISE"))
    ev.upsert_org_unit(
        OrgUnitNode(
            id=org_bu,
            slug="bu",
            name="BU",
            unit_type="BU",
            parent_id=org_root,
            lead_user_id=marc.id,
        )
    )
    ev.upsert_workspace(
        WorkspaceEntity(
            id=ws_priv,
            slug="priv",
            name="Priv",
            owner_org_unit_id=org_root,
            ui_visibility_mode="PRIVATE_USER",
            personal_owner_user_id="someone-else",
        )
    )
    ev.upsert_workspace(
        WorkspaceEntity(
            id=ws_pub,
            slug="pub",
            name="Pub",
            owner_org_unit_id=org_bu,
            visibility_mode="STANDARD",
        )
    )
    ev.upsert_membership(
        WorkspaceMembershipEntity(
            id="m-k-priv",
            workspace_id=ws_priv,
            user_id=marc.id,
            role="TEAM_LEAD",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
        )
    )
    ev.upsert_membership(
        WorkspaceMembershipEntity(
            id="m-c-pub",
            workspace_id=ws_pub,
            user_id=claire.id,
            role="OBSERVER",
            access_mode="READ_ONLY_OBSERVER",
        )
    )

    rep = PackClosureReport(
        complete=False,
        missing_dependencies=[
            ClosureMissingDependency(
                entity_type="SKILL",
                entity_id="s1",
                reason="MISSING",
                referenced_by="WORKFLOW_V2:wf",
            )
        ],
        non_active_dependencies=[
            ClosureMissingDependency(
                entity_type="AGENT",
                entity_id="a1",
                reason="DRAFT",
                referenced_by="WORKFLOW_V2:wf",
            )
        ],
        prose_lint_warnings=[
            ProseLintWarning(
                entity_type="AGENT", entity_slug="a1", token="@b", message="Qualify handle"
            )
        ],
        auto_included_count=1,
    )
    assert serialize_closure_report(None) is None
    ser_rep = serialize_closure_report(rep)
    assert ser_rep is not None and ser_rep.auto_included_count == 1

    def _req(persona: str) -> StarletteRequest:
        return StarletteRequest(
            {
                "type": "http",
                "app": app,
                "method": "GET",
                "path": "/api/v1/packs/composer",
                "query_string": f"persona_key={persona}".encode(),
                "headers": [],
            }
        )

    r_marc = _req("marc")
    r_claire = _req("claire")
    _, is_admin, allowed_ws, allowed_orgs = await compute_caller_composer_scopes(
        r_marc, persona_key="marc"
    )
    assert not is_admin and ws_priv not in allowed_ws and org_bu in allowed_orgs

    with pytest.raises(ObserverModeReadOnlyError):
        await enforce_composer_scope_access(
            r_claire, scope_type="BU", scope_id=org_bu, require_write=True, persona_key="claire"
        )
    with pytest.raises(PackScopeEscalationForbiddenError):
        await enforce_composer_scope_access(
            r_marc, scope_type="GLOBAL", scope_id="global", require_write=True, persona_key="marc"
        )
    # GLOBAL read allowed even for observer claire
    u_g, _ = await enforce_composer_scope_access(
        r_claire, scope_type="GLOBAL", scope_id="global", require_write=False, persona_key="claire"
    )
    assert u_g.id == claire.id
    # BU write allowed for marc (lead), denied for claire on unrelated BU
    await enforce_composer_scope_access(
        r_marc, scope_type="BU", scope_id=org_bu, require_write=True, persona_key="marc"
    )
    with pytest.raises(ScopeAccessDeniedError):
        await enforce_composer_scope_access(
            r_claire,
            scope_type="BU",
            scope_id="0192c4e0-0000-7000-8000-000000000777",
            require_write=False,
            persona_key="claire",
        )
    with pytest.raises(ScopeAccessDeniedError):
        await enforce_composer_scope_access(
            r_marc, scope_type="BU", scope_id=org_root, require_write=True, persona_key="marc"
        )

    class _StubExportSvc:
        def __init__(self, stype: str, sid: str) -> None:
            self._st, self._sid = stype, sid

        async def get_draft(self, bid: str, **_kw: Any) -> PackDraftDetail:
            return PackDraftDetail(
                bundle_id=bid,
                pack_id="orcia-pack-g",
                slug="g",
                name="G",
                version="1.0.0",
                bundle_kind="SYSTEM" if self._st == "GLOBAL" else "CUSTOM",
                scope_type=self._st,
                scope_id=self._sid,
                status="PUBLISHED" if self._st == "GLOBAL" else "DRAFT",
            )

        async def export_bundle(self, bid: str, **_kw: Any) -> Any:
            from orcia_core.packs import PackExportResult

            return PackExportResult(
                bundle_id=bid,
                slug="g",
                version="1.0.0",
                archive_sha256="a" * 64,
                lockfile_bundle_sha256="b" * 64,
                zip_bytes=b"PK",
            )

    resp_obs = await execute_export_pack_zip_handler(
        "b1",
        request=r_claire,
        svc=_StubExportSvc("GLOBAL", "global"),  # type: ignore[arg-type]
        persona_key="claire",
    )
    assert resp_obs.status_code == 200
    with pytest.raises(ObserverModeReadOnlyError):
        await execute_export_pack_zip_handler(
            "b2",
            request=r_claire,
            svc=_StubExportSvc("WORKSPACE", ws_pub),  # type: ignore[arg-type]
            auto_include_dependencies=True,
            persona_key="claire",
        )

    # Cross-workspace 403 on DELETE instructions/help/legacy export for non-admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (
            await client.delete("/api/v1/catalog/instructions/inst-1?persona_key=marc")
        ).status_code == 404
        assert (await client.delete("/api/v1/help/art-1?persona_key=marc")).status_code == 404
        assert (
            await client.post("/api/v1/packs/export/ws-other?persona_key=marc")
        ).status_code == 403
