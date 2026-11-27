"""Shared test fixtures for Story 31.7 Red-Team & Isolation Security Suites (`<= 160 L`)."""

from __future__ import annotations

import io
import json
import stat
import zipfile
from typing import Any

import pytest
from fastapi import FastAPI
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult

from orcia_api.main import create_app
from orcia_core.packs import (
    PackComposerService,
    PackImportService,
    SqlPackBundleV2Repository,
    WorkspacePacksService,
)
from orcia_core.permissions.models import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)

ORG_ROOT = "0192c4e0-0000-7000-8000-000000000001"
ORG_A = "0192c4e0-0000-7000-8000-000000000111"
ORG_B = "0192c4e0-0000-7000-8000-000000000222"
WS_A = "0195f000-0000-7000-8000-000000000311"
WS_B = "0195f000-0000-7000-8000-000000000322"


def zip_of(entries: dict[str, bytes], *, symlink_name: str | None = None) -> bytes:
    """Build deterministic `.zip` bytes with optional symlink entry."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
        if symlink_name is not None:
            info = zipfile.ZipInfo(symlink_name)
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            zf.writestr(info, b"/etc/passwd")
    return buf.getvalue()


def apm_yml(*, scope_type: str = "WORKSPACE", scope_id: str = WS_A, extra: str = "") -> bytes:
    """Render minimal APM v2 `apm.yml` bytes."""
    return (
        "name: RT Pack\nversion: 1.0.0\ndescription: Security archive\n"
        "author: sec@example.org\nlicense: Apache-2.0\n"
        f"{extra}"
        "x-orcia:\n"
        "  pack_id: orcia-pack-rt\n"
        "  slug: rt-pack\n"
        "  bundle_kind: IMPORTED\n"
        f"  scope_type: {scope_type}\n"
        f"  scope_id: {scope_id}\n"
    ).encode()


def setup_packs_red_team_app(
    monkeypatch: pytest.MonkeyPatch,
    *,
    draft_id: str,
    leak_desc: str,
    draft_scope_id: str = WS_B,
    extra_rows: list[dict[str, Any]] | None = None,
) -> tuple[FastAPI, dict[str, str]]:
    """Boot real `create_app()` with multi-tenant topology & `FakeSqlEngine`."""
    for k in ("DATABASE_URL", "ORCIA_ENABLE_PG_SESSION_MAKER"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV", "local")
    app = create_app()
    auth_svc, ev = app.state.auth_service, app.state.auth_service.evaluator
    u_defs = [
        (
            "karim",
            "0195f000-0000-7000-8000-000000000010",
            "PLATFORM_ADMIN",
            ORG_ROOT,
            ("PLATFORM_ADMIN",),
        ),  # noqa: E501
        ("marc", "0195f000-0000-7000-8000-000000000020", "TEAM_LEAD", ORG_A, ("TEAM_LEAD",)),
        (
            "claire",
            "0195f000-0000-7000-8000-000000000030",
            "OBSERVER",
            ORG_A,
            ("OBSERVER", "READ_ONLY_OBSERVER"),
        ),  # noqa: E501
        ("outsider", "0195f000-0000-7000-8000-000000000040", "TEAM_LEAD", ORG_B, ("TEAM_LEAD",)),
    ]
    users: dict[str, UserIdentity] = {}
    for k, uid, role, org, roles in u_defs:
        arch = "OBSERVER" if role == "OBSERVER" else "ARCHITECT"
        usr = UserIdentity(
            id=uid, email=f"{k}@orcia.test", display_name=k.title(), auth_mode="LOCAL",
            human_profile_archetype=arch, platform_role=role, primary_org_unit_id=org, roles=roles,
        )  # fmt: skip
        auth_svc.register_user(usr)
        users[k] = usr
    ev.upsert_org_unit(OrgUnitNode(id=ORG_ROOT, slug="root", name="Root", unit_type="ENTERPRISE"))
    for oid, slug, lead in ((ORG_A, "a", users["marc"].id), (ORG_B, "b", users["outsider"].id)):
        ev.upsert_org_unit(
            OrgUnitNode(
                id=oid, slug=slug, name=slug.upper(), unit_type="TEAM",
                parent_id=ORG_ROOT, lead_user_id=lead,
            )
        )  # fmt: skip
    ev.upsert_workspace(WorkspaceEntity(id=WS_A, slug="ws-a", name="WS A", owner_org_unit_id=ORG_A))
    ev.upsert_workspace(WorkspaceEntity(id=WS_B, slug="ws-b", name="WS B", owner_org_unit_id=ORG_B))
    for mid, uid, role, mode in (
        ("m-ma", users["marc"].id, "TEAM_LEAD", "CONTRIBUTOR_ACTION_REQUIRED"),
        ("m-ca", users["claire"].id, "OBSERVER", "READ_ONLY_OBSERVER"),
    ):
        ev.upsert_membership(
            WorkspaceMembershipEntity(
                id=mid, workspace_id=WS_A, user_id=uid, role=role, access_mode=mode
            )
        )
    tokens = {
        k: auth_svc.jwt_manager.issue_token_pair(
            user_id=u.id,
            email=u.email,
            role=u.platform_role,
            org_unit_id=u.primary_org_unit_id,
            archetype=u.human_profile_archetype,
            auth_mode="LOCAL",
        ).access_token  # fmt: skip
        for k, u in users.items()
    }
    manifest = json.dumps(
        {
            "description": leak_desc,
            "author": "op@example.org",
            "maintainers": [],
            "license": "Apache-2.0",
            "quick_actions": [],
        }
    )
    row: dict[str, Any] = {
        "id": draft_id, "pack_id": "orcia-pack-leak", "slug": "leak-test", "name": "Leak Test",
        "version": "0.1.0", "rbac_namespace": "orcia.pack.leak-test", "bundle_kind": "CUSTOM",
        "scope_type": "WORKSPACE", "scope_id": draft_scope_id, "status": "DRAFT",
        "source_origin": "COMPOSER", "archive_sha256": "a" * 64, "cas_object_key": None,
        "manifest_jsonb": manifest, "declared_slots_jsonb": [], "author": "op@example.org",
        "description": leak_desc, "created_by_user_id": users["karim"].id,
        "published_at": None, "updated_at": None,
    }  # fmt: skip
    all_rows = [row, *(extra_rows or [])]

    def _to_v2_tuple(r: dict[str, Any]) -> tuple[Any, ...]:
        return (
            r["id"],
            r["pack_id"],
            r["slug"],
            r["name"],
            r["version"],
            r["rbac_namespace"],
            r.get("bundle_sha256", r["archive_sha256"]),
            r["bundle_kind"],
            r["scope_type"],
            r["scope_id"],
            r["status"],
            r["archive_sha256"],
            r["cas_object_key"],
            r["source_origin"],
            r.get("declared_slots_jsonb", []),
            r["author"],
            r["description"],
            r["published_at"],
            r["created_by_user_id"],
            "",
            r.get("updated_at") or "",
            r.get("manifest_jsonb", "{}"),
        )

    def _sql(stmt: str, params: dict[str, Any]) -> FakeSqlResult:
        low = stmt.lower()
        if "from declarative_pack_bundles" in low:
            key = str(params.get("k") or params.get("key") or params.get("bid") or "")
            matched = [r for r in all_rows if r["id"] == key or r["pack_id"] == key] if key else []
            chosen = matched or ([row] if key else all_rows)
            return FakeSqlResult(mappings=chosen, rows=[_to_v2_tuple(r) for r in chosen])
        if "from workspaces" in low:
            ws = str(params.get("ws") or draft_scope_id)
            return FakeSqlResult(rows=[(ws, ORG_A if ws == WS_A else ORG_B)], scalar_val=ws)
        return FakeSqlResult(mappings=[], rows=[])

    eng = FakeSqlEngine(_sql)
    app.state.pack_bundle_v2_repository = SqlPackBundleV2Repository(eng)
    app.state.pack_import_service = PackImportService(engine=eng)
    app.state.pack_composer_service = PackComposerService(engine=eng)
    app.state.workspace_packs_service = WorkspacePacksService(engine=eng)
    return app, tokens
