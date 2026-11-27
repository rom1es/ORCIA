"""Unit tests for Story 31.5 publish & export transactions (`<= 260 L`)."""

from __future__ import annotations

import io
import zipfile
from typing import Any

import pytest
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult
from uuid_utils import uuid7

from orcia_core.packs import PackComposerService
from orcia_core.packs._internal._sql_pack_publish_export import (
    export_bundle_tx,
    publish_draft_pack_tx,
)
from orcia_core.packs.errors import PackVersionConflictError


@pytest.mark.asyncio
async def test_publish_and_export_bundle_tx() -> None:
    """Verify `export_bundle_tx` and `publish_draft_pack_tx` with fake PG18 + CAS."""
    ws_id, bid, cat_uid = str(uuid7()), str(uuid7()), str(uuid7())
    uploaded: list[str] = []

    class _FakeCas:
        async def put_archive_zip(
            self, *, slug: str, version: str, archive_sha256: str, zip_bytes: bytes
        ) -> str:
            key = f"packs/{slug}/{version}/{archive_sha256}.zip"
            uploaded.append(key)
            return key

        async def get_archive_zip(self, cas_key: str) -> bytes | None:
            return None

        async def head_archive_zip(self, cas_key: str) -> bool:
            return False

    def handler(sql: str, _params: dict[str, Any]) -> FakeSqlResult:
        if "declarative_pack_bundles" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "id": bid,
                        "pack_id": "orcia-pack-pub",
                        "slug": "pub-pack",
                        "name": "Pub Pack",
                        "version": "1.0.0",
                        "rbac_namespace": "pub-pack",
                        "bundle_kind": "CUSTOM",
                        "scope_type": "WORKSPACE",
                        "scope_id": ws_id,
                        "status": "DRAFT",
                        "source_origin": "ORCIA_COMPOSER",
                        "archive_sha256": "a" * 64,
                        "cas_object_key": None,
                        "manifest_jsonb": {"description": "Pub"},
                        "declared_slots_jsonb": [],
                        "author": "Author",
                        "description": "Pub",
                        "created_by_user_id": None,
                        "published_at": None,
                        "updated_at": "",
                    }
                ]
            )
        if "FROM pack_draft_memberships" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "id": str(uuid7()),
                        "draft_bundle_id": bid,
                        "entity_type": "AGENT",
                        "entity_id": "ag-1",
                        "entity_slug": "ag-1",
                        "catalog_item_id": cat_uid,
                        "workflow_v2_id": None,
                        "vsm_v2_id": None,
                        "ontology_concept_id": None,
                        "ontology_relation_id": None,
                        "ontology_axiom_id": None,
                        "dna_mechanism_id": None,
                        "policy_id": None,
                        "created_at": "",
                    }
                ]
            )
        if "SELECT title, metadata_jsonb FROM catalog_items" in sql:
            return FakeSqlResult(
                rows=[
                    (
                        "Agent 1",
                        {"slug": "ag-1", "instructions": "Assist.", "lifecycle_status": "ACTIVE"},
                    )
                ]
            )
        if "FROM catalog_items" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "id": cat_uid,
                        "resource_id": "ag-1",
                        "uri": "orcia://ws/agents/ag-1",
                        "title": "Agent 1",
                        "description": "Helper",
                        "resource_type": "agent",
                        "item_type": "USER_AGENT",
                        "metadata_jsonb": {
                            "slug": "ag-1",
                            "instructions": "Assist.",
                            "lifecycle_status": "ACTIVE",
                        },
                    }
                ],
            )
        if "FROM workspaces" in sql:
            return FakeSqlResult(rows=[(ws_id, None)])
        if "SELECT id FROM org_units" in sql:
            return FakeSqlResult(rows=[(str(uuid7()),)])
        if "SELECT to_regclass" in sql:
            return FakeSqlResult(scalar_val=None, has_scalar=True)
        return FakeSqlResult(rows=[])

    eng = FakeSqlEngine(handler)
    exp = await export_bundle_tx(eng, bundle_id=bid)  # type: ignore[arg-type]
    assert exp.slug == "pub-pack"
    with zipfile.ZipFile(io.BytesIO(exp.zip_bytes), "r") as zf:
        assert "pub-pack/apm.lock.yaml" in zf.namelist()

    svc = PackComposerService(engine=eng, cas_storage=_FakeCas())  # type: ignore[arg-type]
    pub = await svc.publish_draft(bid, actor_id="u1")
    assert pub.bundle_id == bid
    assert len(uploaded) == 1

    with pytest.raises(PackVersionConflictError):
        await publish_draft_pack_tx(
            FakeSqlEngine(
                lambda sql, _p: FakeSqlResult(
                    mappings=[
                        {
                            "id": bid,
                            "pack_id": "p",
                            "slug": "p",
                            "name": "P",
                            "version": "1.0.0",
                            "rbac_namespace": "p",
                            "bundle_kind": "CUSTOM",
                            "scope_type": "WORKSPACE",
                            "scope_id": ws_id,
                            "status": "PUBLISHED",
                            "source_origin": "ORCIA_COMPOSER",
                            "archive_sha256": "a" * 64,
                            "cas_object_key": None,
                            "manifest_jsonb": {},
                            "declared_slots_jsonb": [],
                            "author": None,
                            "description": None,
                            "created_by_user_id": None,
                            "published_at": None,
                            "updated_at": "",
                        }
                    ]
                )
            ),  # type: ignore[arg-type]
            draft_id=bid,
        )
