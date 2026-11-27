"""Unit tests for Story 31.5 surrogate UUID FK resolution across all 8 tables (`<= 260 L`)."""

from __future__ import annotations

from typing import Any

import pytest
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult
from uuid_utils import uuid7

from orcia_core.kernel.errors import ResourceNotFoundError
from orcia_core.packs._internal._sql_pack_composer_targets import resolve_draft_target_conn
from orcia_core.packs.composer_models import PackDraftMemberInput
from orcia_core.packs.models import PackDraftEntityType
from orcia_core.permissions.errors import ScopeAccessDeniedError


@pytest.mark.asyncio
async def test_resolve_draft_target_all_8_fk_types_and_guards() -> None:
    """Verify surrogate UUID FK resolution across all 8 tables + cross-workspace 403 / 404."""
    ws_id, other_ws, uid = str(uuid7()), str(uuid7()), str(uuid7())

    def handler(sql: str, params: dict[str, Any]) -> FakeSqlResult:
        k = params.get("k")
        if "FROM workspaces" in sql:
            return FakeSqlResult(rows=[(ws_id, None)])
        if "WITH RECURSIVE anc" in sql:
            return FakeSqlResult(rows=[])
        if k == "missing":
            return FakeSqlResult(mappings=[])
        if k == "cross-ws":
            return FakeSqlResult(
                mappings=[
                    {
                        "uid": uid,
                        "eid": "cross-ws",
                        "title": "X",
                        "bid": None,
                        "ws_id": other_ws,
                        "metadata_jsonb": {},
                    }
                ]
            )
        if "FROM catalog_items" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "uid": uid,
                        "eid": k,
                        "title": "Catalog",
                        "bid": None,
                        "ws_id": ws_id,
                        "metadata_jsonb": {"slug": k, "lifecycle_status": "ACTIVE"},
                    }
                ]
            )
        if "FROM workflow_definitions_v2" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "uid": uid,
                        "eid": k,
                        "slug": k,
                        "status": "published",
                        "bid": None,
                        "spec_jsonb": {"title": "WF"},
                    }
                ]
            )
        if "FROM vsm_definitions_v2" in sql:
            return FakeSqlResult(
                mappings=[{"uid": uid, "eid": k, "slug": k, "title": "VSM", "bid": None}]
            )
        if "FROM ontology_concepts" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "uid": uid,
                        "eid": k,
                        "title": "Term",
                        "level": "3_WORKSPACE",
                        "scope_id": other_ws if k == "cross-onto" else ws_id,
                        "st": "ACTIVE",
                        "bid": None,
                    }
                ]
            )
        return FakeSqlResult(
            mappings=[{"uid": uid, "eid": k, "title": "Item", "st": "ACTIVE", "bid": None}]
        )

    eng = FakeSqlEngine(handler)
    async with eng.connect() as conn:
        for etype in (
            PackDraftEntityType.AGENT,
            PackDraftEntityType.WORKFLOW_V2,
            PackDraftEntityType.VSM_V2,
            PackDraftEntityType.ONTOLOGY_CONCEPT,
            PackDraftEntityType.ONTOLOGY_RELATION,
            PackDraftEntityType.ONTOLOGY_AXIOM,
            PackDraftEntityType.DNA_MECHANISM,
            PackDraftEntityType.POLICY,
        ):
            res = await resolve_draft_target_conn(
                conn,  # type: ignore[arg-type]
                PackDraftMemberInput(entity_type=etype, entity_id="ent-1"),
                draft_scope_type="WORKSPACE",
                draft_scope_id=ws_id,
            )
            assert res.fk_uuid == uid

        with pytest.raises(ScopeAccessDeniedError):
            await resolve_draft_target_conn(
                conn,  # type: ignore[arg-type]
                PackDraftMemberInput(entity_type=PackDraftEntityType.AGENT, entity_id="cross-ws"),
                draft_scope_type="WORKSPACE",
                draft_scope_id=ws_id,
            )
        with pytest.raises(ScopeAccessDeniedError):
            await resolve_draft_target_conn(
                conn,  # type: ignore[arg-type]
                PackDraftMemberInput(
                    entity_type=PackDraftEntityType.ONTOLOGY_CONCEPT, entity_id="cross-onto"
                ),
                draft_scope_type="WORKSPACE",
                draft_scope_id=ws_id,
            )
        with pytest.raises(ResourceNotFoundError):
            await resolve_draft_target_conn(
                conn,  # type: ignore[arg-type]
                PackDraftMemberInput(entity_type=PackDraftEntityType.AGENT, entity_id="missing"),
                draft_scope_type="WORKSPACE",
                draft_scope_id=ws_id,
            )
