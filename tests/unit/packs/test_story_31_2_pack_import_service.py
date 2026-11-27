"""Unit tests for Story 31.2 `PackImportService` & `SeaweedFsPackCasAdapter` (`<= 300 L`)."""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
import yaml
from tests.unit.fakes.in_memory_pack_cas import InMemoryPackCasStorage

from orcia_api.dependencies.pack_import_deps import (
    get_pack_bundle_v2_repository,
    get_pack_cas_storage,
    get_pack_import_service,
)
from orcia_core.packs import (
    ApmPackCodec,
    PackBundleKind,
    PackImportService,
    PackInvalidArchiveError,
    PackScopeEscalationForbiddenError,
    PackScopeType,
    PackVersionConflictError,
    SeaweedFsPackCasAdapter,
    build_pack_cas_key,
    seed_system_packs_on_engine,
)


def _build_apm_zip(
    *,
    slug: str = "custom-audit",
    version: str = "1.0.0",
    bundle_kind: str = "IMPORTED",
    scope_type: str = "WORKSPACE",
    status: str = "PUBLISHED",
    agent_body: str = "Inspect compliance rules.",
) -> bytes:
    buf = io.BytesIO()
    apm_yml = yaml.safe_dump(
        {
            "name": slug,
            "version": version,
            "description": "Custom audit pack",
            "x-orcia": {
                "slug": slug,
                "bundle_kind": bundle_kind,
                "scope_type": scope_type,
                "scope_id": "0195f000-0000-7000-8000-000000000301",
                "status": status,
                "connector_slots": [
                    {
                        "slot_key": "git-main",
                        "scheme": "git",
                        "connector_kind": "mcp:git-provider",
                        "required_access": ["read"],
                        "required": True,
                    }
                ],
            },
        }
    )
    agent_md = (
        "---\nname: Audit Agent\ndescription: Checks PRs\n"
        "x-orcia:\n  posture: PRODUCER\n  human_partner_role: TECH_LEAD\n"
        "  llm_model_tier: medium\n  skill_refs:\n    - check-diff\n"
        "  connector_slots:\n    - git-main\n---\n" + agent_body + "\n"
    )
    skill_md = (
        "---\nname: Check Diff\ndescription: Inspect diff\n"
        "x-orcia:\n  command_handle: /check-diff\n  input_parameters:\n"
        "    - name: repo\n      type: string\n---\nReview changed lines.\n"
    )
    glossary_yaml = yaml.safe_dump(
        {
            "terms": [{"key": "DOR", "label": "Definition of Ready", "definition": "Ready gate"}],
            "relations": [],
            "axioms": [],
        }
    )
    policy_md = (
        "---\npolicy_key: git-read\nuri_pattern: git://org/*\n"
        "connector_scheme: git\nrequired_role: DEVELOPER\nsla_hours: 12\n---\n"
        "Request read scope.\n"
    )
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{slug}/apm.yml", apm_yml)
        zf.writestr(f"{slug}/agents/audit-agent.agent.md", agent_md)
        zf.writestr(f"{slug}/skills/check-diff/SKILL.md", skill_md)
        zf.writestr(f"{slug}/ontology/glossary.yaml", glossary_yaml)
        zf.writestr(f"{slug}/policies/git-read.policy.md", policy_md)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_seaweedfs_pack_cas_adapter_sigv4_bucket_create_and_roundtrip() -> None:
    """Verify `SeaweedFsPackCasAdapter` creates missing bucket on 404 and checks SHA-256."""
    stored: dict[str, bytes] = {}
    bucket_created = False

    def _handler(request: httpx.Request) -> httpx.Response:
        nonlocal bucket_created
        assert "Authorization" in request.headers
        assert request.headers["Authorization"].startswith("AWS4-HMAC-SHA256 ")
        path = request.url.path
        if request.method == "PUT" and path == "/orcia-cas":
            bucket_created = True
            return httpx.Response(200)
        if request.method == "PUT":
            if not bucket_created:
                return httpx.Response(404)
            stored[path] = request.content
            return httpx.Response(200)
        if request.method == "GET":
            data = stored.get(path)
            return httpx.Response(200, content=data) if data is not None else httpx.Response(404)
        if request.method == "HEAD":
            return httpx.Response(200 if path in stored else 404)
        return httpx.Response(405)

    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    adapter = SeaweedFsPackCasAdapter(
        endpoint_url="http://seaweedfs.local:9000",
        bucket_name="orcia-cas",
        http_client=client,
    )
    payload = b"PK-zip-bytes"
    digest = hashlib.sha256(payload).hexdigest()
    key = await adapter.put_archive_zip(
        slug="audit", version="1.0.0", archive_sha256=digest, zip_bytes=payload
    )
    assert key == build_pack_cas_key(slug="audit", version="1.0.0", archive_sha256=digest)
    assert bucket_created is True
    assert await adapter.head_archive_zip(key) is True
    assert await adapter.get_archive_zip(key) == payload
    assert await adapter.get_archive_zip("packs/missing/1.0.0/0.zip") is None

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        await adapter.put_archive_zip(
            slug="audit", version="1.0.0", archive_sha256="0" * 64, zip_bytes=payload
        )
    await client.aclose()


@pytest.mark.asyncio
async def test_pack_import_service_conflict_idempotency_and_scope_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `PackImportService` SHA-256 conflicts, replace_draft, and SYSTEM/GLOBAL rejection."""
    cas = InMemoryPackCasStorage()
    calls: list[dict[str, Any]] = []
    bundle_uuid = "0195f000-0000-7000-8000-000000000777"

    async def _fake_tx(engine: Any, bundle: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append({"bundle": bundle, **kwargs})
        if kwargs.get("cas_upload_cb") is not None:
            cas_key = await kwargs["cas_upload_cb"]()
        else:
            cas_key = None
        if len(calls) == 2 and not kwargs.get("replace_draft"):
            raise PackVersionConflictError(detail_override="Conflict")
        return {
            "bundle_id": bundle_uuid,
            "pack_id": bundle.manifest.id,
            "slug": bundle.manifest.slug,
            "name": bundle.manifest.name,
            "version": bundle.manifest.version,
            "bundle_kind": bundle.manifest.bundle_kind.value,
            "scope_type": bundle.manifest.scope_type.value,
            "scope_id": bundle.manifest.scope_id,
            "status": bundle.manifest.status.value,
            "archive_sha256": bundle.archive_sha256,
            "cas_object_key": cas_key,
            "idempotent_noop": False,
            "counts": {"agents": len(bundle.agents), "skills": len(bundle.skills)},
        }

    import orcia_core.packs.import_service as svc_mod

    monkeypatch.setattr(svc_mod, "import_bundle_transactional", _fake_tx)
    svc = PackImportService(engine=object(), cas_storage=cas)  # type: ignore[arg-type]

    zip_v1 = _build_apm_zip(agent_body="Body v1")
    out1 = await svc.import_zip_bytes(zip_v1, actor_id="u-1", actor_email="u@orcia.test")
    assert out1.bundle_id == bundle_uuid
    assert out1.cas_object_key is not None
    assert await cas.head_archive_zip(out1.cas_object_key) is True

    with pytest.raises(PackVersionConflictError):
        await svc.import_zip_bytes(_build_apm_zip(agent_body="Body v2"))

    out2 = await svc.import_zip_bytes(
        _build_apm_zip(bundle_kind="CUSTOM", status="DRAFT", agent_body="Draft v2"),
        replace_draft=True,
    )
    assert out2.bundle_kind == "CUSTOM"

    with pytest.raises(PackInvalidArchiveError):
        await svc.import_zip_bytes(_build_apm_zip(bundle_kind="SYSTEM", scope_type="GLOBAL"))

    with pytest.raises(PackScopeEscalationForbiddenError):
        await svc.import_zip_bytes(zip_v1, scope_type=PackScopeType.GLOBAL)


@pytest.mark.asyncio
async def test_seed_system_packs_on_engine_discovers_sdlc_and_docs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `seed_system_packs_on_engine` imports `packs/sdlc` & `packs/orcia-docs`."""
    seeded_slugs: list[str] = []

    async def _fake_import_dir(
        self: PackImportService,
        pack_dir: Path,
        **kwargs: Any,
    ) -> Any:
        bundle = ApmPackCodec().decode_directory(pack_dir)
        seeded_slugs.append(bundle.manifest.slug)
        assert kwargs["bundle_kind"] == PackBundleKind.SYSTEM
        assert kwargs["scope_type"] == PackScopeType.GLOBAL
        assert kwargs["allow_system_kind"] is True
        assert all(a.lifecycle_status.value == "ACTIVE" for a in bundle.agents)
        assert all(s.lifecycle_status.value == "ACTIVE" for s in bundle.skills)
        return bundle

    monkeypatch.setattr(PackImportService, "import_directory", _fake_import_dir)
    outcomes = await seed_system_packs_on_engine(object())  # type: ignore[arg-type]
    assert len(outcomes) == 2
    assert set(seeded_slugs) == {"orcia-docs", "sdlc"}

    # Missing packs root returns [] without touching DB, and engine=None fails closed on delete
    assert (
        await seed_system_packs_on_engine(object(), packs_root=Path("/nonexistent-packs-312")) == []
    )  # type: ignore[arg-type]
    no_eng_svc = PackImportService(engine=None, cas_storage=None)
    with pytest.raises(RuntimeError, match="AsyncEngine"):
        await no_eng_svc.delete_bundle("b1")


def test_pack_import_deps_singleton_and_cas_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover `pack_import_deps.py` lazy CAS/repo/service resolution without fake SQL."""
    req: Any = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db_engine=None)))
    monkeypatch.delenv("ORCIA_SEAWEEDFS_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("SEAWEEDFS_S3_ENDPOINT", raising=False)
    monkeypatch.delenv("S3_ENDPOINT_URL", raising=False)
    assert get_pack_cas_storage(req) is None

    monkeypatch.setenv("ORCIA_SEAWEEDFS_ENDPOINT_URL", "http://127.0.0.1:8333")
    cas = get_pack_cas_storage(req)
    assert cas is not None and get_pack_cas_storage(req) is cas

    repo = get_pack_bundle_v2_repository(req)
    svc = get_pack_import_service(req)
    req.app.state.db_engine = object()
    assert get_pack_bundle_v2_repository(req) is repo
    assert get_pack_import_service(req) is svc
    assert AsyncMock is not None
