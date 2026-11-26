"""Unit tests for Story 31.5 scope read filtering and draft guard edge cases."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult
from uuid_utils import uuid7

from orcia_core.packs._internal._sql_pack_composer_reads import list_draft_packs_sql
from orcia_core.packs._internal._sql_pack_composer_scope import (
    assert_bundle_visible_conn,
    assert_standalone_wf_vsm_visible,
    is_ontology_level_visible,
    pick_first_visible,
)
from orcia_core.permissions.errors import ScopeAccessDeniedError
from orcia_core.storage.pack_draft_guard import (
    guard_or_unlink_pack_drafts_conn,
    list_referencing_pack_drafts_conn,
)


@pytest.mark.asyncio
async def test_reads_scope_filtering_and_guard_branches() -> None:
    """Cover non-admin filtering in `list_draft_packs_sql`, `scope` checks & missing tables."""
    ws_ok, org_ok, ws_other = str(uuid7()), str(uuid7()), str(uuid7())
    now = datetime.now(UTC)

    def _row(bid: str, st: str, sid: str) -> dict[str, Any]:
        return {
            "id": bid,
            "pack_id": f"p-{bid}",
            "slug": f"s-{bid}",
            "name": "N",
            "version": "1.0.0",
            "rbac_namespace": "s",
            "bundle_kind": "CUSTOM",
            "scope_type": st,
            "scope_id": sid,
            "status": "DRAFT",
            "source_origin": "ORCIA_COMPOSER",
            "archive_sha256": "a" * 64,
            "cas_object_key": None,
            "manifest_jsonb": {},
            "declared_slots_jsonb": [],
            "author": None,
            "description": None,
            "created_by_user_id": None,
            "published_at": None,
            "updated_at": now,
        }

    def handler(sql: str, _p: dict[str, Any]) -> FakeSqlResult:
        if "FROM declarative_pack_bundles" in sql:
            return FakeSqlResult(
                mappings=[
                    _row("1", "WORKSPACE", ws_ok),
                    _row("2", "WORKSPACE", ws_other),
                    _row("3", "BU", org_ok),
                    _row("4", "BU", "other-org"),
                    _row("5", "GLOBAL", "global"),
                ]
            )
        if "to_regclass('public.pack_draft_memberships')" in sql:
            return FakeSqlResult(scalar_val=False, has_scalar=True)
        return FakeSqlResult(mappings=[])

    eng = FakeSqlEngine(handler)
    items = await list_draft_packs_sql(
        eng,  # type: ignore[arg-type]
        unrestricted=False,
        allowed_workspace_ids=frozenset({ws_ok}),
        allowed_org_ids=frozenset({org_ok}),
        allow_global=False,
    )
    assert [i.bundle_id for i in items] == ["1", "3"]

    async with eng.connect() as conn:
        assert (
            await list_referencing_pack_drafts_conn(
                conn,  # type: ignore[arg-type]
                fk_column="catalog_item_id",
                target_uuid=str(uuid7()),
            )
            == []
        )
        assert (
            await guard_or_unlink_pack_drafts_conn(
                conn,  # type: ignore[arg-type]
                fk_column="catalog_item_id",
                target_uuid=str(uuid7()),
                entity_type="AGENT",
                entity_label="a",
            )
            == []
        )
        await assert_bundle_visible_conn(
            conn,  # type: ignore[arg-type]
            pack_bundle_id=None,
            draft_scope_type="WORKSPACE",
            draft_scope_id=ws_ok,
            ancestor_orgs=frozenset(),
            instance=None,
        )
    with pytest.raises(ScopeAccessDeniedError):
        assert_standalone_wf_vsm_visible(
            pack_id="ws",
            spec={"owner_workspace_id": ws_other},
            draft_scope_type="WORKSPACE",
            draft_scope_id=ws_ok,
            ancestor_orgs=frozenset(),
            instance=None,
        )
    with pytest.raises(ScopeAccessDeniedError):
        assert_standalone_wf_vsm_visible(
            pack_id="ws",
            spec={"scope_type": "WORKSPACE", "scope_id": ws_other},
            draft_scope_type="WORKSPACE",
            draft_scope_id=ws_ok,
            ancestor_orgs=frozenset(),
            instance=None,
        )
    assert (
        is_ontology_level_visible(
            level="2_DOMAIN",
            scope_id=org_ok,
            draft_scope_type="BU",
            draft_scope_id=org_ok,
            ancestor_orgs=frozenset(),
        )
        is True
    )
    assert (
        is_ontology_level_visible(
            level="2_DOMAIN",
            scope_id="",
            draft_scope_type="BU",
            draft_scope_id=org_ok,
            ancestor_orgs=frozenset(),
        )
        is False
    )
    with pytest.raises(ScopeAccessDeniedError):
        assert_standalone_wf_vsm_visible(
            pack_id=f"ws:{ws_other}:x",
            spec={},
            draft_scope_type="WORKSPACE",
            draft_scope_id=ws_ok,
            ancestor_orgs=frozenset(),
            instance=None,
        )
    with pytest.raises(ScopeAccessDeniedError):
        assert_standalone_wf_vsm_visible(
            pack_id="ws",
            spec={"scope_type": "BU", "scope_id": "other-org"},
            draft_scope_type="WORKSPACE",
            draft_scope_id=ws_ok,
            ancestor_orgs=frozenset(),
            instance=None,
        )

    def scope_handler(sql: str, params: dict[str, Any]) -> FakeSqlResult:
        bid = str(params.get("bid") or "")
        if bid == "missing":
            return FakeSqlResult(mappings=[])
        if bid == "global-b":
            return FakeSqlResult(mappings=[{"scope_type": "GLOBAL", "scope_id": "global"}])
        if bid == "bu-b":
            return FakeSqlResult(mappings=[{"scope_type": "BU", "scope_id": org_ok}])
        return FakeSqlResult(mappings=[{"scope_type": "WORKSPACE", "scope_id": ws_other}])

    eng_scope = FakeSqlEngine(scope_handler)
    async with eng_scope.connect() as sconn:
        await assert_bundle_visible_conn(
            sconn,  # type: ignore[arg-type]
            pack_bundle_id="missing",
            draft_scope_type="WORKSPACE",
            draft_scope_id=ws_ok,
            ancestor_orgs=frozenset(),
            instance=None,
        )
        await assert_bundle_visible_conn(
            sconn,  # type: ignore[arg-type]
            pack_bundle_id="global-b",
            draft_scope_type="WORKSPACE",
            draft_scope_id=ws_ok,
            ancestor_orgs=frozenset(),
            instance=None,
        )
        await assert_bundle_visible_conn(
            sconn,  # type: ignore[arg-type]
            pack_bundle_id="bu-b",
            draft_scope_type="BU",
            draft_scope_id=org_ok,
            ancestor_orgs=frozenset(),
            instance=None,
        )
        with pytest.raises(ScopeAccessDeniedError):
            await pick_first_visible(
                [{"id": "ws-b"}],
                lambda _r: assert_bundle_visible_conn(
                    sconn,  # type: ignore[arg-type]
                    pack_bundle_id="ws-b",
                    draft_scope_type="GLOBAL",
                    draft_scope_id="global",
                    ancestor_orgs=frozenset(),
                    instance=None,
                ),
            )


@pytest.mark.asyncio
async def test_legacy_export_admin_fallback_404_and_synthesized_zip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover admin non-UUID fallback, `404` when repo empty, and CAS-miss zip synthesis."""
    from httpx import ASGITransport, AsyncClient

    from orcia_api.main import create_app

    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV", "local")
    app = create_app()

    class _EmptyRepo:
        _engine = object()

        async def list_bundles_v2(self) -> list[dict[str, Any]]:
            return []

    class _RowRepo:
        _engine = object()

        async def list_bundles_v2(self) -> list[dict[str, Any]]:
            return [
                {
                    "id": str(uuid7()),
                    "pack_id": "orcia-pack-sdlc",
                    "slug": "sdlc",
                    "name": "SDLC",
                    "version": "1.0.0",
                    "bundle_kind": "SYSTEM",
                    "scope_type": "GLOBAL",
                    "scope_id": "global",
                    "cas_object_key": "missing-key",
                    "manifest_jsonb": {},
                }
            ]

    class _NoneCas:
        async def get_archive_zip(self, _k: str) -> bytes | None:
            return None

    app.state.pack_bundle_v2_repository = _EmptyRepo()
    app.state.pack_cas_storage = _NoneCas()
    app.state.db_engine = FakeSqlEngine(lambda _s, _p: FakeSqlResult(mappings=[]))
    monkeypatch.setattr(
        "orcia_api.routers._packs_export_legacy_route.is_pg_runtime_active", lambda _r: True
    )
    karim = app.state.auth_service.resolve_user(persona_key="karim")
    karim_tok = app.state.auth_service.jwt_manager.issue_token_pair(
        user_id=karim.id,
        email=karim.email,
        role=karim.platform_role,
        org_unit_id=karim.primary_org_unit_id,
        archetype=karim.human_profile_archetype,
        auth_mode="LOCAL",
    ).access_token
    karim_hdr = {"Authorization": f"Bearer {karim_tok}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r_404 = await client.post("/api/v1/packs/export/non-uuid-ws", headers=karim_hdr)
        assert r_404.status_code == 404
        r_uuid_404 = await client.post(f"/api/v1/packs/export/{uuid7()}", headers=karim_hdr)
        assert r_uuid_404.status_code == 404
        app.state.pack_bundle_v2_repository = _RowRepo()
        r_miss_pid = await client.post(
            "/api/v1/packs/export/non-uuid-ws?pack_id=missing-pack", headers=karim_hdr
        )
        assert r_miss_pid.status_code == 404
        r_synth = await client.post("/api/v1/packs/export/non-uuid-ws", headers=karim_hdr)
        assert r_synth.status_code == 200
        assert r_synth.headers["content-type"] == "application/zip"
