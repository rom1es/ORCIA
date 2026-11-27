"""Unit tests for Story 31.5 closure auto-include, hydration & service branches (`<= 240 L`)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult
from uuid_utils import uuid7

from orcia_core.packs._internal._pack_closure_analyzer import (
    analyze_and_optionally_expand_closure_conn,
)
from orcia_core.packs._internal._sql_pack_composer_hydration import (
    decode_json_dict,
    load_draft_members_hydrated_conn,
)
from orcia_core.packs._internal._sql_pack_publish_export import export_bundle_tx
from orcia_core.packs.composer_models import PackDraftMemberInput, PackDraftMemberView
from orcia_core.packs.composer_service import PackComposerService
from orcia_core.packs.errors import PackClosureIncompleteError
from orcia_core.packs.models import PackDraftEntityType, PackScopeType


@pytest.mark.asyncio
async def test_closure_auto_include_and_all_entity_hydration() -> None:
    """Verify BFS closure expansion (`422` vs `auto_include=True`), `require_active` & hydration."""
    ws_id, bid = str(uuid7()), str(uuid7())
    wf_uid, ag_uid, vsm_uid = str(uuid7()), str(uuid7()), str(uuid7())
    c1_uid, c2_uid, rel_uid, ax_uid = str(uuid7()), str(uuid7()), str(uuid7()), str(uuid7())
    inserted_members: list[dict[str, Any]] = []

    def handler(sql: str, params: dict[str, Any]) -> FakeSqlResult:
        if "FROM workspaces" in sql:
            return FakeSqlResult(rows=[(ws_id, None)])
        if "WITH RECURSIVE anc" in sql or "SELECT id FROM org_units" in sql:
            return FakeSqlResult(rows=[])
        if "SELECT status, spec_jsonb FROM workflow_definitions_v2" in sql:
            return FakeSqlResult(
                rows=[
                    (
                        "published",
                        {
                            "title": "Flow",
                            "sub_steps": [
                                {
                                    "id": "s1",
                                    "instruction_prompt_or_ref": "@ag-dep",
                                    "allowed_rag_sources": [],
                                }
                            ],
                        },
                    )
                ]
            )
        if "SELECT spec_jsonb FROM vsm_definitions_v2" in sql:
            return FakeSqlResult(rows=[({"title": "VSM"},)])
        if "SELECT source_concept_id::text, target_concept_id::text FROM ontology_relations" in sql:
            return FakeSqlResult(rows=[(c1_uid, c2_uid)])
        if "SELECT concept_id::text FROM ontology_axioms" in sql:
            return FakeSqlResult(rows=[(c1_uid,)])
        if "SELECT title, metadata_jsonb FROM catalog_items" in sql:
            return FakeSqlResult(rows=[("Ag Dep", {"slug": "ag-dep", "lifecycle_status": "DRAFT"})])
        if "FROM catalog_items" in sql and "ANY" in sql:
            return FakeSqlResult(rows=[(ag_uid, "Ag Dep", '{"slug":"ag-dep"}')])
        if "FROM workflow_definitions_v2" in sql and "ANY" in sql:
            return FakeSqlResult(rows=[(wf_uid, "wf-1", "published", '{"title":"WF 1"}')])
        if "FROM vsm_definitions_v2" in sql and "ANY" in sql:
            return FakeSqlResult(rows=[(vsm_uid, "VSM 1")])
        if "FROM catalog_items" in sql:
            k = params.get("k")
            if k in ("ag-dep", "@ag-dep"):
                return FakeSqlResult(
                    mappings=[
                        {
                            "uid": ag_uid,
                            "eid": "ag-dep",
                            "title": "Ag Dep",
                            "bid": None,
                            "ws_id": ws_id,
                            "metadata_jsonb": {"slug": "ag-dep", "lifecycle_status": "DRAFT"},
                        }
                    ]
                )
            return FakeSqlResult(mappings=[])
        if "FROM ontology_concepts" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "uid": c1_uid,
                        "eid": "c1",
                        "title": "C1",
                        "level": "3_WORKSPACE",
                        "scope_id": ws_id,
                        "st": "ACTIVE",
                        "bid": None,
                    }
                ]
            )
        if "FROM pack_draft_memberships" in sql and "SELECT" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "id": str(uuid7()),
                        "draft_bundle_id": bid,
                        "entity_type": "WORKFLOW_V2",
                        "entity_id": "wf-1",
                        "entity_slug": "wf-1",
                        "catalog_item_id": None,
                        "workflow_v2_id": wf_uid,
                        "vsm_v2_id": None,
                        "ontology_concept_id": None,
                        "ontology_relation_id": None,
                        "ontology_axiom_id": None,
                        "dna_mechanism_id": None,
                        "policy_id": None,
                        "created_at": "",
                    },
                    {
                        "id": str(uuid7()),
                        "draft_bundle_id": bid,
                        "entity_type": "VSM_V2",
                        "entity_id": "vsm-1",
                        "entity_slug": "vsm-1",
                        "catalog_item_id": None,
                        "workflow_v2_id": None,
                        "vsm_v2_id": vsm_uid,
                        "ontology_concept_id": None,
                        "ontology_relation_id": None,
                        "ontology_axiom_id": None,
                        "dna_mechanism_id": None,
                        "policy_id": None,
                        "created_at": "",
                    },
                ]
            )
        if "INSERT INTO pack_draft_memberships" in sql:
            inserted_members.append(dict(params))
        return FakeSqlResult()

    assert decode_json_dict('{"a": 1}') == {"a": 1}
    assert decode_json_dict("bad-json") == {}

    eng = FakeSqlEngine(handler)
    async with eng.begin() as conn:
        hydrated = await load_draft_members_hydrated_conn(conn, draft_bundle_id=bid)  # type: ignore[arg-type]
        assert len(hydrated) == 2 and hydrated[0].title == "WF 1" and hydrated[1].title == "VSM 1"

        seed_members = [
            *hydrated,
            PackDraftMemberView(
                id=str(uuid7()),
                draft_bundle_id=bid,
                entity_type=PackDraftEntityType.ONTOLOGY_RELATION,
                entity_id="rel-1",
                entity_slug="rel-1",
                ontology_relation_id=rel_uid,
            ),
            PackDraftMemberView(
                id=str(uuid7()),
                draft_bundle_id=bid,
                entity_type=PackDraftEntityType.ONTOLOGY_AXIOM,
                entity_id="ax-1",
                entity_slug="ax-1",
                ontology_axiom_id=ax_uid,
            ),
        ]
        with pytest.raises(PackClosureIncompleteError) as exc_inc:
            await analyze_and_optionally_expand_closure_conn(
                conn,  # type: ignore[arg-type]
                bundle_id=bid,
                scope_type="WORKSPACE",
                scope_id=ws_id,
                members=seed_members,
                auto_include_dependencies=False,
                can_mutate_draft=False,
                require_active=False,
                fail_on_incomplete=True,
            )
        assert exc_inc.value.http_status == 422
        assert exc_inc.value.missing_dependencies

        report = await analyze_and_optionally_expand_closure_conn(
            conn,  # type: ignore[arg-type]
            bundle_id=bid,
            scope_type="WORKSPACE",
            scope_id=ws_id,
            members=seed_members,
            auto_include_dependencies=True,
            can_mutate_draft=True,
            require_active=True,
            fail_on_incomplete=False,
        )
        assert report.auto_included_count >= 1
        assert inserted_members
        assert report.non_active_dependencies


@pytest.mark.asyncio
async def test_pack_composer_service_facade_and_non_draft_export() -> None:
    """Verify `PackComposerService` methods and non-draft bundle export path."""
    ws_id, bid = str(uuid7()), str(uuid7())
    bundle_row = {
        "id": bid,
        "pack_id": "orcia-pack-sys",
        "slug": "sys-pack",
        "name": "Sys Pack",
        "version": "1.0.0",
        "rbac_namespace": "sys-pack",
        "bundle_kind": "IMPORTED",
        "scope_type": "WORKSPACE",
        "scope_id": ws_id,
        "status": "PUBLISHED",
        "source_origin": "APM_ZIP",
        "archive_sha256": "a" * 64,
        "cas_object_key": None,
        "manifest_jsonb": {"description": "Sys"},
        "declared_slots_jsonb": [],
        "author": "Author",
        "description": "Sys",
        "created_by_user_id": None,
        "published_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }

    def handler(sql: str, _params: dict[str, Any]) -> FakeSqlResult:
        if "SELECT 1 FROM declarative_pack_bundles" in sql:
            return FakeSqlResult(scalar_val=None, has_scalar=True)
        if "declarative_pack_bundles" in sql:
            return FakeSqlResult(mappings=[bundle_row])
        if "SELECT to_regclass" in sql:
            return FakeSqlResult(scalar_val=None, has_scalar=True)
        if "FROM workspaces" in sql:
            return FakeSqlResult(rows=[(ws_id, None)])
        if "SELECT id FROM org_units" in sql:
            return FakeSqlResult(rows=[])
        if "SELECT title, metadata_jsonb FROM catalog_items" in sql:
            return FakeSqlResult(rows=[("A1", {"slug": "a1", "instructions": "Run."})])
        if "FROM catalog_items" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "id": str(uuid7()),
                        "resource_id": "a1",
                        "uri": "orcia://p/a1",
                        "title": "A1",
                        "description": "Desc",
                        "resource_type": "agent",
                        "item_type": "USER_AGENT",
                        "metadata_jsonb": {"slug": "a1", "instructions": "Run."},
                    }
                ]
            )
        return FakeSqlResult(mappings=[], rows=[])

    svc = PackComposerService()
    with pytest.raises(RuntimeError, match="PostgreSQL 18"):
        await svc.list_drafts()
    eng = FakeSqlEngine(handler)
    svc.set_engine(eng)  # type: ignore[arg-type]
    svc.set_cas_storage(None)
    assert (await svc.list_drafts(scope_type=PackScopeType.WORKSPACE, scope_id=ws_id))[
        0
    ].bundle_id == bid
    assert (await svc.get_draft(bid, include_closure=True)).closure is not None
    assert (await svc.get_draft(bid, include_closure=False)).closure is None
    assert (await svc.create_draft(slug="sys-pack", name="Sys", scope_id=ws_id)).bundle_id == bid
    exp = await export_bundle_tx(eng, bundle_id=bid)  # type: ignore[arg-type]
    assert exp.slug == "sys-pack"
    exp2 = await svc.export_bundle(bid)
    assert exp2.archive_sha256 == exp.archive_sha256
    assert isinstance(
        PackDraftMemberInput(entity_type=PackDraftEntityType.AGENT, entity_id="a1"),
        PackDraftMemberInput,
    )
