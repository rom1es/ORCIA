"""Shared test fixtures for Story 31.7 Red-Team & Isolation Security Suites (`<= 175 L`)."""

from __future__ import annotations

import io
import stat
import zipfile
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI

from orcia_api.main import create_app
from orcia_core.packs import ApmPackCodec, PackPiiOrInfraLeakError
from orcia_core.packs._internal._pack_export_scrubber import (
    TenantInfraIdentifiers,
    scan_rendered_files_for_leaks,
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
    """Configure a multi-tenant `create_app()` with real security decoders & port stubs."""
    for k in ("DATABASE_URL", "ORCIA_ENABLE_PG_SESSION_MAKER"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
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
        ),
        ("marc", "0195f000-0000-7000-8000-000000000020", "TEAM_LEAD", ORG_A, ("TEAM_LEAD",)),
        (
            "claire",
            "0195f000-0000-7000-8000-000000000030",
            "OBSERVER",
            ORG_A,
            ("OBSERVER", "READ_ONLY_OBSERVER"),
        ),
        ("outsider", "0195f000-0000-7000-8000-000000000040", "TEAM_LEAD", ORG_B, ("TEAM_LEAD",)),
    ]
    users: dict[str, UserIdentity] = {}
    for k, uid, role, org, roles in u_defs:
        arch = "OBSERVER" if role == "OBSERVER" else "ARCHITECT"
        usr = UserIdentity(
            id=uid,
            email=f"{k}@orcia.test",
            display_name=k.title(),
            auth_mode="LOCAL",
            human_profile_archetype=arch,
            platform_role=role,  # type: ignore[arg-type]
            primary_org_unit_id=org,
            roles=roles,
        )
        auth_svc.register_user(usr)
        users[k] = usr
    ev.upsert_org_unit(OrgUnitNode(id=ORG_ROOT, slug="root", name="Root", unit_type="ENTERPRISE"))
    for oid, slug, lead in ((ORG_A, "a", users["marc"].id), (ORG_B, "b", users["outsider"].id)):
        ev.upsert_org_unit(
            OrgUnitNode(
                id=oid,
                slug=slug,
                name=slug.upper(),
                unit_type="TEAM",
                parent_id=ORG_ROOT,
                lead_user_id=lead,
            )
        )
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
        ).access_token
        for k, u in users.items()
    }
    row: dict[str, Any] = {
        "id": draft_id,
        "pack_id": "orcia-pack-leak",
        "slug": "leak-test",
        "name": "Leak Test",
        "version": "0.1.0",
        "bundle_kind": "CUSTOM",
        "scope_type": "WORKSPACE",
        "scope_id": draft_scope_id,
        "status": "DRAFT",
        "description": leak_desc,
    }
    all_rows = [row, *(extra_rows or [])]

    async def _import_zip_bytes(zip_bytes: bytes, **_kw: Any) -> Any:
        # Execute real archive & hook security decoder before any persistence.
        ApmPackCodec().decode_zip_bytes(zip_bytes)
        raise AssertionError("Expected security decoder to fail before persistence")

    async def _export_bundle(bid: str, **_kw: Any) -> Any:
        infra = TenantInfraIdentifiers(
            tenant_uuids=frozenset({WS_A, WS_B}),
            tenant_emails=frozenset({"admin@tenant.internal"}),
            tenant_hosts=frozenset({"git.corp.internal"}),
        )
        scan_rendered_files_for_leaks(
            {"apm.yml": f"name: leak-test\ndescription: {leak_desc}\n".encode()}, infra
        )
        raise PackPiiOrInfraLeakError(leak_findings=["unexpected_clean"])

    app.state.pack_bundle_v2_repository = SimpleNamespace(
        _engine=object(),
        list_bundles_v2=AsyncMock(return_value=all_rows),
        get_bundle_v2=AsyncMock(return_value=row),
    )
    app.state.pack_import_service = SimpleNamespace(
        _engine=object(),
        get_bundle=AsyncMock(return_value=row),
        import_zip_bytes=_import_zip_bytes,
    )
    draft_detail = SimpleNamespace(**row, bundle_id=draft_id, members=[])
    app.state.pack_composer_service = SimpleNamespace(
        _engine=object(),
        get_draft=AsyncMock(return_value=draft_detail),
        export_bundle=_export_bundle,
    )
    app.state.workspace_packs_service = SimpleNamespace(has_engine=lambda: True)
    return app, tokens
