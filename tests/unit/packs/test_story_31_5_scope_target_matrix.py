"""Unit tests for Story 31.5 BU/TEAM/GLOBAL bundle & target scope isolation (`<= 140 L`)."""

from __future__ import annotations

from typing import Any

import pytest
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult
from uuid_utils import uuid7

from orcia_core.packs._internal._sql_pack_composer_target_extra import (
    assert_bundle_visible_conn,
    is_ontology_level_visible,
    resolve_ontology_or_policy_row_conn,
)
from orcia_core.packs._internal._sql_pack_composer_targets import resolve_draft_target_conn
from orcia_core.packs.composer_models import PackDraftMemberInput
from orcia_core.packs.models import PackDraftEntityType
from orcia_core.permissions.errors import ScopeAccessDeniedError


@pytest.mark.asyncio
async def test_target_extra_and_scope_matrix() -> None:
    """Verify BU/TEAM/GLOBAL bundle visibility, ontology relation endpoints & policy prefixes."""
    ws_id, org_id, other_ws, b_ws = (str(uuid7()) for _ in range(4))
    assert is_ontology_level_visible(
        level="1_ENTERPRISE",
        scope_id="",
        draft_scope_type="GLOBAL",
        draft_scope_id="global",
        ancestor_orgs=frozenset(),
    )
    assert not is_ontology_level_visible(
        level="2_DOMAIN",
        scope_id=org_id,
        draft_scope_type="GLOBAL",
        draft_scope_id="global",
        ancestor_orgs=frozenset(),
    )
    assert is_ontology_level_visible(
        level="2_DOMAIN",
        scope_id=org_id,
        draft_scope_type="WORKSPACE",
        draft_scope_id=ws_id,
        ancestor_orgs=frozenset({org_id}),
    )
    assert not is_ontology_level_visible(
        level="2_DOMAIN",
        scope_id="",
        draft_scope_type="WORKSPACE",
        draft_scope_id=ws_id,
        ancestor_orgs=frozenset(),
    )

    def handler(sql: str, _params: dict[str, Any]) -> FakeSqlResult:
        if "FROM declarative_pack_bundles" in sql:
            return FakeSqlResult(mappings=[{"scope_type": "WORKSPACE", "scope_id": other_ws}])
        if "WITH RECURSIVE anc" in sql:
            return FakeSqlResult(rows=[])
        if "FROM ontology_relations" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "uid": str(uuid7()),
                        "eid": "rel-bad",
                        "title": "R",
                        "st": "ACTIVE",
                        "bid": None,
                        "src_level": "3_WORKSPACE",
                        "src_scope_id": other_ws,
                        "tgt_level": "1_ENTERPRISE",
                        "tgt_scope_id": "",
                    }
                ]
            )
        if "FROM permission_broker_policies" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "uid": str(uuid7()),
                        "eid": f"ws:{other_ws}:git",
                        "title": "P",
                        "st": "ACTIVE",
                        "bid": None,
                    }
                ]
            )
        if "FROM workflow_definitions_v2" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "uid": str(uuid7()),
                        "eid": "wf-other",
                        "slug": "wf-other",
                        "status": "published",
                        "pack_id": f"workspace:{other_ws}",
                        "bid": None,
                        "spec_jsonb": {"title": "Other"},
                    }
                ]
            )
        return FakeSqlResult(mappings=[])

    eng = FakeSqlEngine(handler)
    async with eng.connect() as conn:
        with pytest.raises(ScopeAccessDeniedError):
            await assert_bundle_visible_conn(
                conn,  # type: ignore[arg-type]
                pack_bundle_id=b_ws,
                draft_scope_type="BU",
                draft_scope_id=org_id,
                ancestor_orgs=frozenset(),
                instance=None,
            )
        with pytest.raises(ScopeAccessDeniedError):
            await assert_bundle_visible_conn(
                conn,  # type: ignore[arg-type]
                pack_bundle_id=b_ws,
                draft_scope_type="GLOBAL",
                draft_scope_id="global",
                ancestor_orgs=frozenset(),
                instance=None,
            )
        with pytest.raises(ScopeAccessDeniedError):
            await resolve_ontology_or_policy_row_conn(
                conn,  # type: ignore[arg-type]
                PackDraftMemberInput(
                    entity_type=PackDraftEntityType.ONTOLOGY_RELATION, entity_id="rel-bad"
                ),
                draft_scope_type="WORKSPACE",
                draft_scope_id=ws_id,
                ancestor_orgs=frozenset(),
                instance=None,
            )
        with pytest.raises(ScopeAccessDeniedError):
            await resolve_ontology_or_policy_row_conn(
                conn,  # type: ignore[arg-type]
                PackDraftMemberInput(entity_type=PackDraftEntityType.POLICY, entity_id="p"),
                draft_scope_type="WORKSPACE",
                draft_scope_id=ws_id,
                ancestor_orgs=frozenset(),
                instance=None,
            )
        with pytest.raises(ScopeAccessDeniedError):
            await resolve_draft_target_conn(
                conn,  # type: ignore[arg-type]
                PackDraftMemberInput(
                    entity_type=PackDraftEntityType.WORKFLOW_V2, entity_id="wf-other"
                ),
                draft_scope_type="BU",
                draft_scope_id=org_id,
                ancestor_orgs=frozenset(),
            )


@pytest.mark.asyncio
async def test_pack_owned_ontology_p1_1_and_team_ancestor_p1_2() -> None:
    """Verify pack-owned ontology (`2_DOMAIN`, pack slug) & `TEAM` ancestor resolution."""
    from datetime import UTC, datetime

    from orcia_core.packs._internal._pack_closure_analyzer import (
        analyze_and_optionally_expand_closure_conn,
    )
    from orcia_core.packs._internal._sql_pack_composer_members import set_draft_pack_members_sql
    from orcia_core.packs._internal._sql_pack_composer_scope import pick_first_visible
    from orcia_core.permissions.errors import ResourceNotFoundError

    bu_id, team_id, bu_bundle_id = str(uuid7()), str(uuid7()), str(uuid7())
    draft_id, concept_uid, rel_uid = str(uuid7()), str(uuid7()), str(uuid7())
    now = datetime.now(UTC)

    def handler(sql: str, params: dict[str, Any]) -> FakeSqlResult:
        if "WITH RECURSIVE anc" in sql:
            return FakeSqlResult(rows=[(team_id,), (bu_id,)])
        if "FROM declarative_pack_bundles" in sql and "WHERE id = CAST" in sql:
            return FakeSqlResult(mappings=[{"scope_type": "BU", "scope_id": bu_id}])
        if "FROM declarative_pack_bundles" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "id": draft_id,
                        "pack_id": "orcia-pack-t",
                        "slug": "t",
                        "name": "T",
                        "version": "1.0.0",
                        "rbac_namespace": "t",
                        "bundle_kind": "CUSTOM",
                        "scope_type": "TEAM",
                        "scope_id": team_id,
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
                ]
            )
        if "FROM ontology_concepts" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "uid": concept_uid,
                        "eid": "pack:bu-pack:sla",
                        "title": "SLA",
                        "level": "2_DOMAIN",
                        "scope_id": "bu-pack",
                        "st": "ACTIVE",
                        "bid": bu_bundle_id,
                    }
                ]
            )
        if "FROM ontology_relations" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "uid": rel_uid,
                        "eid": "pack:bu-pack:rel",
                        "title": "SUPPORTS",
                        "st": "ACTIVE",
                        "bid": bu_bundle_id,
                        "src_level": "2_DOMAIN",
                        "src_scope_id": "bu-pack",
                        "src_bid": bu_bundle_id,
                        "tgt_level": "2_DOMAIN",
                        "tgt_scope_id": "bu-pack",
                        "tgt_bid": bu_bundle_id,
                    }
                ]
            )
        if "FROM pack_draft_memberships" in sql:
            return FakeSqlResult(mappings=[])
        return FakeSqlResult(mappings=[])

    eng = FakeSqlEngine(handler)
    async with eng.connect() as conn:
        res_c = await resolve_ontology_or_policy_row_conn(
            conn,  # type: ignore[arg-type]
            PackDraftMemberInput(
                entity_type=PackDraftEntityType.ONTOLOGY_CONCEPT, entity_id="pack:bu-pack:sla"
            ),
            draft_scope_type="TEAM",
            draft_scope_id=team_id,
            ancestor_orgs=frozenset({team_id, bu_id}),
            instance=None,
        )
        assert res_c["uid"] == concept_uid
        res_r = await resolve_ontology_or_policy_row_conn(
            conn,  # type: ignore[arg-type]
            PackDraftMemberInput(
                entity_type=PackDraftEntityType.ONTOLOGY_RELATION, entity_id="pack:bu-pack:rel"
            ),
            draft_scope_type="TEAM",
            draft_scope_id=team_id,
            ancestor_orgs=frozenset({team_id, bu_id}),
            instance=None,
        )
        assert res_r["uid"] == rel_uid
        with pytest.raises(ResourceNotFoundError):
            await pick_first_visible([], lambda _x: None)
        rep = await analyze_and_optionally_expand_closure_conn(
            conn,  # type: ignore[arg-type]
            bundle_id=draft_id,
            scope_type="TEAM",
            scope_id=team_id,
            members=[],
        )
        assert rep.complete is True

    detail = await set_draft_pack_members_sql(
        eng,  # type: ignore[arg-type]
        draft_id,
        [
            PackDraftMemberInput(
                entity_type=PackDraftEntityType.ONTOLOGY_CONCEPT, entity_id="pack:bu-pack:sla"
            )
        ],
        actor_id="u1",
        actor_email="u1@orcia.test",
        trace_id="t1",
    )
    assert detail.bundle_id == draft_id
