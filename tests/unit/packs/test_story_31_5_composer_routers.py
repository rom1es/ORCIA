"""Unit tests for Story 31.5 FastAPI `/api/v1/packs/composer` & DBAPIError (`<= 260 L`)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import DBAPIError
from uuid_utils import uuid7

from orcia_api.main import create_app
from orcia_core.packs import (
    PackDraftDetail,
    PackDraftEntityType,
    PackDraftMemberView,
    PackExportResult,
)
from orcia_core.permissions.models import (
    OrgUnitNode,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)


@pytest.mark.asyncio
async def test_pack_composer_router_and_dbapi_error_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `/api/v1/packs/composer`, `/api/v1/packs/{id}/export`, 403 guards & DBAPIError."""
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV", "local")
    app: FastAPI = create_app()
    ws_id = "0195f000-0000-7000-8000-000000000301"
    org_id = "0192c4e0-0000-7000-8000-000000000001"
    auth_svc = app.state.auth_service
    default_user = auth_svc.resolve_user()
    ev = auth_svc.evaluator
    ev.upsert_org_unit(OrgUnitNode(id=org_id, slug="root", name="R", unit_type="ENTERPRISE"))
    ev.upsert_workspace(
        WorkspaceEntity(
            id=ws_id,
            slug="ws-315-unit",
            name="WS 315 Unit",
            owner_org_unit_id=org_id,
            visibility_mode="STANDARD",
        )
    )
    ev.upsert_membership(
        WorkspaceMembershipEntity(
            id="mem-315-0",
            workspace_id=ws_id,
            user_id=default_user.id,
            role="TEAM_LEAD",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
        )
    )
    bid = str(uuid7())
    sample_detail = PackDraftDetail(
        bundle_id=bid,
        pack_id="orcia-pack-comp",
        slug="comp",
        name="Comp Pack",
        version="0.1.0",
        scope_type="WORKSPACE",
        scope_id=ws_id,
        members=[
            PackDraftMemberView(
                id=str(uuid7()),
                draft_bundle_id=bid,
                entity_type=PackDraftEntityType.AGENT,
                entity_id="ag-1",
                entity_slug="ag-1",
                catalog_item_id=str(uuid7()),
            )
        ],
    )

    class _StubComposerSvc:
        async def create_draft(self, **_kw: Any) -> PackDraftDetail:
            return sample_detail

        async def list_drafts(self, **_kw: Any) -> list[PackDraftDetail]:
            return [sample_detail]

        async def get_draft(self, *_a: Any, **_kw: Any) -> PackDraftDetail:
            return sample_detail

        async def update_draft(self, *_a: Any, **_kw: Any) -> PackDraftDetail:
            return sample_detail

        async def set_members(self, *_a: Any, **_kw: Any) -> PackDraftDetail:
            return sample_detail

        async def delete_draft(self, *_a: Any, **_kw: Any) -> dict[str, str]:
            return {"bundle_id": bid, "slug": "comp", "version": "0.1.0"}

        async def publish_draft(self, *_a: Any, **_kw: Any) -> PackDraftDetail:
            return sample_detail.model_copy(update={"status": "PUBLISHED"})

        async def export_bundle(self, *_a: Any, **_kw: Any) -> PackExportResult:
            return PackExportResult(
                bundle_id=bid,
                slug="comp",
                version="0.1.0",
                archive_sha256="b" * 64,
                lockfile_bundle_sha256="c" * 64,
                zip_bytes=b"PK\x05\x06" + b"\x00" * 18,
            )

    app.state.pack_composer_service = _StubComposerSvc()

    @app.get("/_test/dbapi/{pgcode}")
    async def _raise_dbapi(pgcode: str) -> None:
        orig = SimpleNamespace(pgcode=pgcode)
        if pgcode == "23503":
            msg = "violates foreign key constraint on pack_draft_memberships"
        elif pgcode == "23503_fk":
            orig = SimpleNamespace(pgcode="23503")
            msg = "violates foreign key constraint on step_executions"
        elif pgcode == "23505_pack":
            orig = SimpleNamespace(pgcode="23505")
            msg = "duplicate key value violates unique constraint on declarative_pack_bundles"
        else:
            msg = "err"
        raise DBAPIError(msg, None, orig)  # type: ignore[arg-type]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r_create = await client.post(
            "/api/v1/packs/composer",
            json={"slug": "comp", "name": "Comp", "scope_type": "WORKSPACE", "scope_id": ws_id},
        )
        assert r_create.status_code == 201
        assert (
            await client.get(f"/api/v1/packs/composer?scope_type=WORKSPACE&scope_id={ws_id}")
        ).status_code == 200
        assert (await client.get(f"/api/v1/packs/composer/{bid}")).status_code == 200
        assert (
            await client.patch(f"/api/v1/packs/composer/{bid}", json={"name": "New"})
        ).status_code == 200
        assert (
            await client.put(
                f"/api/v1/packs/composer/{bid}/members",
                json={"members": [{"entity_type": "AGENT", "entity_id": "ag-1"}]},
            )
        ).status_code == 200
        assert (await client.post(f"/api/v1/packs/composer/{bid}/publish")).json()[
            "status"
        ] == "PUBLISHED"
        exp_comp = await client.post(f"/api/v1/packs/composer/{bid}/export")
        assert exp_comp.status_code == 200
        exp = await client.post(f"/api/v1/packs/{bid}/export")
        assert exp.status_code == 200
        assert exp.headers["x-orcia-archive-sha256"] == "b" * 64
        assert (await client.delete(f"/api/v1/packs/composer/{bid}")).json()["deleted"] is True

        r_obs = await client.post(
            "/api/v1/packs/composer",
            headers={"x-orcia-access-mode": "READ_ONLY_OBSERVER"},
            json={"slug": "comp", "name": "Comp", "scope_type": "WORKSPACE", "scope_id": ws_id},
        )
        assert r_obs.status_code == 403
        assert r_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        assert (await client.get("/_test/dbapi/23503")).json()[
            "error_code"
        ] == "ERR_ENTITY_REFERENCED_BY_PACK_DRAFT"
        assert (await client.get("/_test/dbapi/23503_fk")).json()[
            "error_code"
        ] == "ERR_FOREIGN_KEY_CONSTRAINT_CONFLICT"
        assert (await client.get("/_test/dbapi/23505")).json()[
            "error_code"
        ] == "ERR_UNIQUE_CONSTRAINT_CONFLICT"
        assert (await client.get("/_test/dbapi/23505_pack")).json()[
            "error_code"
        ] == "ERR_PACK_VERSION_CONFLICT"
        assert (await client.get("/_test/dbapi/23514")).status_code == 422
        assert (await client.get("/_test/dbapi/99999")).status_code == 500
