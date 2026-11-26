"""Branch-coverage unit tests for Story 31.2 pack import, delete, deps & router (`<= 300 L`)."""

from __future__ import annotations

import base64
import io
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
import yaml
from fastapi.testclient import TestClient
from tests.unit.fakes.in_memory_pack_cas import InMemoryPackCasStorage

from orcia_api.dependencies.pack_import_deps import (
    get_pack_bundle_v2_repository,
    get_pack_cas_storage,
    get_pack_import_service,
)
from orcia_api.main import create_app
from orcia_core.packs import (
    ApmPackCodec,
    EntityReferencedByPackDraftError,
    PackImportService,
    PackScopeEscalationForbiddenError,
    PackScopeType,
    PackSystemDeleteForbiddenError,
    seed_system_packs_on_engine,
)
from orcia_core.packs._internal._sql_pack_delete_tx import delete_bundle_transactional
from orcia_core.packs._internal._sql_pack_ontology_policy_materializer import (
    append_pack_audit_event,
    materialize_pack_mechanisms_and_policies,
)


class _Res:
    def __init__(
        self,
        *,
        scalar: Any = None,
        mapping: dict[str, Any] | None = None,
        rows: list[Any] | None = None,
    ) -> None:
        self._scalar = scalar
        self._mapping = mapping
        self._rows = rows or []

    def all(self) -> list[Any]:
        return list(self._rows)

    def scalar(self) -> Any:
        return self._scalar

    def scalar_one(self) -> Any:
        return self._scalar

    def first(self) -> Any:
        return (
            self._mapping
            if self._mapping is not None
            else ((self._scalar,) if self._scalar else None)
        )

    def mappings(self) -> _Res:
        return self


class _Conn:
    def __init__(self, resolver: Any) -> None:
        self._resolver = resolver
        self.queries: list[str] = []

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _Res:
        sql = str(stmt)
        self.queries.append(sql)
        return self._resolver(sql, params or {})


class _Engine:
    def __init__(self, resolver: Any) -> None:
        self.conn = _Conn(resolver)

    @asynccontextmanager
    async def begin(self) -> Any:
        yield self.conn


def _sample_zip_with_dna_and_policy(slug: str = "cov-pack") -> bytes:
    buf = io.BytesIO()
    apm = yaml.safe_dump(
        {
            "name": slug,
            "version": "1.0.0",
            "x-orcia": {
                "slug": slug,
                "bundle_kind": "IMPORTED",
                "scope_type": "WORKSPACE",
                "scope_id": "0195f000-0000-7000-8000-000000000301",
                "status": "DRAFT",
            },
        }
    )
    pol = (
        "---\nuri_pattern: 'jira://*'\nconnector_scheme: UNKNOWN_SCHEME\n"
        "required_role: TEAM_LEAD\nsla_hours: 4\n---\nApprove.\n"
    )
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{slug}/apm.yml", apm)
        zf.writestr(
            f"{slug}/ontology/mechanisms/guard.star",
            "def evaluate(ctx):\n    return {'ok': True}\n",
        )
        zf.writestr(f"{slug}/policies/jira-write.policy.md", pol)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_delete_tx_dna_policies_and_audit_branches() -> None:
    """Cover delete success, draft-ref guard on DNA, DNA/policy SQL & missing audit_ledger."""
    bundle = ApmPackCodec().decode_zip_bytes(_sample_zip_with_dna_and_policy())
    bid = "0195f000-0000-7000-8000-000000000950"

    def _ok_resolver(sql: str, _p: dict[str, Any]) -> _Res:
        if "SELECT id::text, pack_id" in sql:
            return _Res(
                mapping={
                    "id": bid,
                    "slug": "cov-pack",
                    "version": "1.0.0",
                    "bundle_kind": "IMPORTED",
                    "scope_type": "WORKSPACE",
                    "scope_id": "ws-1",
                }
            )
        if "FROM connector_schemes" in sql:
            return _Res(rows=[("mcp",), ("git",)])
        if "to_regclass" in sql:
            return _Res(scalar="audit_ledger")
        return _Res(scalar=None)

    eng = _Engine(_ok_resolver)
    await materialize_pack_mechanisms_and_policies(eng.conn, bundle_id=bid, bundle=bundle)  # type: ignore[arg-type]
    assert any("INSERT INTO pack_dna_mechanisms" in q for q in eng.conn.queries)
    assert any("INSERT INTO permission_broker_policies" in q for q in eng.conn.queries)

    deleted = await delete_bundle_transactional(
        eng,  # type: ignore[arg-type]
        bundle_id_or_pack_id=bid,
        actor_id="u1",
        actor_email="a@b.c",
    )
    assert deleted == {"bundle_id": bid, "slug": "cov-pack", "version": "1.0.0"}
    assert any("INSERT INTO audit_ledger" in q for q in eng.conn.queries)

    no_audit_eng = _Engine(lambda _s, _p: _Res(scalar=None))
    await append_pack_audit_event(
        no_audit_eng.conn,  # type: ignore[arg-type]
        event_type="X",
        summary="S",
        scope_path="GLOBAL:global",
        actor_id="u1",
        actor_email=None,
        metadata={},
    )
    assert not any("INSERT INTO audit_ledger" in q for q in no_audit_eng.conn.queries)

    def _mech_ref_resolver(sql: str, _p: dict[str, Any]) -> _Res:
        if "SELECT id::text, pack_id" in sql:
            return _Res(
                mapping={
                    "id": bid,
                    "slug": "cov-pack",
                    "version": "1.0.0",
                    "bundle_kind": "IMPORTED",
                    "scope_type": "WORKSPACE",
                    "scope_id": "ws-1",
                }
            )
        if "JOIN pack_dna_mechanisms d" in sql:
            return _Res(scalar=1)
        return _Res(scalar=None)

    with pytest.raises(EntityReferencedByPackDraftError):
        await delete_bundle_transactional(
            _Engine(_mech_ref_resolver),  # type: ignore[arg-type]
            bundle_id_or_pack_id=bid,
        )


@pytest.mark.asyncio
async def test_import_service_directory_overrides_and_empty_seed(tmp_path: Path) -> None:
    """Cover `import_directory`, scope overrides, setters, and empty seed."""

    def _dir_resolver(sql: str, _p: dict[str, Any]) -> _Res:
        if "FOR UPDATE" in sql:
            return _Res(mapping=None)
        if "SELECT id FROM org_units" in sql or "INSERT INTO org_units" in sql:
            return _Res(scalar="0195f000-0000-7000-8000-000000000001")
        return _Res(scalar="0195f000-0000-7000-8000-000000000999")

    cas = InMemoryPackCasStorage()
    eng = _Engine(_dir_resolver)
    svc = PackImportService(engine=None, cas_storage=None)
    with pytest.raises(RuntimeError, match="AsyncEngine"):
        await svc.delete_bundle("b1")
    svc.set_engine(eng)  # type: ignore[arg-type]
    svc.set_cas_storage(cas)

    pack_dir = tmp_path / "dir-pack"
    pack_dir.mkdir()
    (pack_dir / "apm.yml").write_text("name: dir-pack\nversion: 1.0.0\n", encoding="utf-8")
    res = await svc.import_directory(
        pack_dir,
        scope_type=PackScopeType.WORKSPACE,
        scope_id="0195f000-0000-7000-8000-000000000301",
    )
    assert res.slug == "dir-pack"
    assert res.cas_object_key is not None

    with pytest.raises(PackScopeEscalationForbiddenError):
        await svc.import_zip_bytes(
            _sample_zip_with_dna_and_policy(),
            scope_type=PackScopeType.GLOBAL,
            allow_system_kind=False,
        )

    assert await seed_system_packs_on_engine(eng, packs_root=tmp_path / "missing") == []  # type: ignore[arg-type]


def test_pack_import_deps_and_router_edge_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover `pack_import_deps.py`, multipart errors, JSON import & export CAS hit / 404."""
    req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db_engine=None)))
    assert get_pack_cas_storage(req) is None  # type: ignore[arg-type]
    monkeypatch.setenv("ORCIA_SEAWEEDFS_ENDPOINT_URL", "http://127.0.0.1:8333")
    cas = get_pack_cas_storage(req)  # type: ignore[arg-type]
    assert cas is not None and get_pack_cas_storage(req) is cas  # type: ignore[arg-type]
    repo = get_pack_bundle_v2_repository(req)  # type: ignore[arg-type]
    svc = get_pack_import_service(req)  # type: ignore[arg-type]
    fake_eng = object()
    req.app.state.db_engine = fake_eng
    assert get_pack_bundle_v2_repository(req) is repo  # type: ignore[arg-type]
    assert get_pack_import_service(req) is svc  # type: ignore[arg-type]

    app = create_app()
    fake_svc = SimpleNamespace(
        import_zip_bytes=AsyncMock(
            return_value=SimpleNamespace(
                bundle_id="b1",
                pack_id="p1",
                slug="cov-pack",
                name="Cov Pack",
                version="1.0.0",
                bundle_kind="IMPORTED",
                scope_type="WORKSPACE",
                scope_id="ws-1",
                status="DRAFT",
                archive_sha256="a" * 64,
                cas_object_key="packs/cov-pack/1.0.0/" + ("a" * 64) + ".zip",
                idempotent_noop=False,
                counts={},
            )
        ),
        delete_bundle=AsyncMock(side_effect=PackSystemDeleteForbiddenError(detail_override="sys")),
    )
    app.dependency_overrides[get_pack_import_service] = lambda: fake_svc
    client = TestClient(app)

    bad_mp = client.post("/api/v1/packs/import", data={"scope_type": "WORKSPACE"})
    assert bad_mp.status_code == 422
    b64 = base64.b64encode(_sample_zip_with_dna_and_policy()).decode("ascii")
    ok_json = client.post(
        "/api/v1/packs/import",
        json={
            "zip_base64": b64,
            "scope_type": "WORKSPACE",
            "scope_id": "ws-1",
            "replace_draft": True,
        },
    )
    assert ok_json.status_code == 200 and ok_json.json()["slug"] == "cov-pack"
    assert client.delete("/api/v1/packs/0195f000-0000-7000-8000-000000000001").status_code == 403
    assert client.post("/api/v1/packs/export/ws-1").status_code == 403
    karim = app.state.auth_service.resolve_user(persona_key="karim")
    ktok = app.state.auth_service.jwt_manager.issue_token_pair(
        user_id=karim.id,
        email=karim.email,
        role=karim.platform_role,
        org_unit_id=karim.primary_org_unit_id,
        archetype=karim.human_profile_archetype,
        auth_mode="LOCAL",
    ).access_token
    r_nf = client.post("/api/v1/packs/export/ws-1", headers={"Authorization": f"Bearer {ktok}"})
    assert r_nf.status_code == 404
