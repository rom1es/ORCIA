"""Unit tests for Story 31.5 anti-hostage delete guards & audit ledger (`<= 280 L`)."""

from __future__ import annotations

from typing import Any

import pytest
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult
from uuid_utils import uuid7

from orcia_core.kernel.errors import (
    EntityReferencedByPackDraftError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)
from orcia_core.orchestration._internal._sql_agents_delete import (
    delete_agent_from_postgres18,
    delete_catalog_item_guarded,
    delete_skill_with_agent_sync,
)
from orcia_core.orchestration.agents_and_skills_models import ManagedAgentRecord
from orcia_core.storage.entity_delete_tx import delete_entity_guarded_tx
from orcia_core.storage.pack_draft_guard import guard_or_unlink_pack_drafts_conn


@pytest.mark.asyncio
async def test_pack_draft_guard_and_entity_delete_tx() -> None:
    """Verify anti-hostage `409`, `?unlink_from_draft_packs=true`, `audit_ledger` & cascade."""
    ws_id, target_uid, draft_id = str(uuid7()), str(uuid7()), str(uuid7())
    audit_events: list[str] = []
    deleted_sql: list[str] = []

    def handler(sql: str, params: dict[str, Any]) -> FakeSqlResult:
        if "SELECT (to_regclass('public.pack_draft_memberships')" in sql:
            return FakeSqlResult(scalar_val=True, has_scalar=True)
        if "SELECT to_regclass('public.audit_ledger')" in sql:
            return FakeSqlResult(scalar_val="audit_ledger", has_scalar=True)
        if "FROM pack_draft_memberships m" in sql:
            if params.get("tid") == target_uid:
                return FakeSqlResult(
                    mappings=[
                        {
                            "bundle_id": draft_id,
                            "pack_slug": "my-draft",
                            "version": "0.1.0",
                            "title": "My Draft",
                        }
                    ]
                )
            return FakeSqlResult(mappings=[])
        if "DELETE FROM pack_draft_memberships" in sql:
            return FakeSqlResult(mappings=[{"id": str(uuid7()), "draft_bundle_id": draft_id}])
        if "DELETE FROM" in sql:
            deleted_sql.append(sql)
            return FakeSqlResult()
        if "INSERT INTO audit_ledger" in sql:
            if "PACK_DRAFT_MEMBER_UNLINKED_ON_ENTITY_DELETE" in sql:
                audit_events.append("PACK_DRAFT_MEMBER_UNLINKED_ON_ENTITY_DELETE")
            return FakeSqlResult()
        if "FROM catalog_items" in sql:
            if params.get("rid") == "pack-owned":
                return FakeSqlResult(
                    mappings=[
                        {
                            "uid": target_uid,
                            "ws_id": ws_id,
                            "bid": draft_id,
                            "visibility_scope": "PACK",
                        }
                    ]
                )
            if params.get("rid") == "missing-item":
                return FakeSqlResult(mappings=[])
            return FakeSqlResult(
                mappings=[
                    {"uid": target_uid, "ws_id": ws_id, "bid": None, "visibility_scope": "TEAM"}
                ]
            )
        if "FROM ontology_concepts" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "uid": target_uid,
                        "key_val": "k1",
                        "label_val": "Term 1",
                        "bid": None,
                        "level": "3_WORKSPACE",
                        "scope_id": ws_id,
                    }
                ]
            )
        if "FROM ontology_relations" in sql:
            return FakeSqlResult(mappings=[{"uid": str(uuid7()), "bid": None}])
        if "FROM ontology_axioms" in sql:
            return FakeSqlResult(mappings=[{"uid": str(uuid7()), "bid": None}])
        return FakeSqlResult()

    eng = FakeSqlEngine(handler)
    async with eng.begin() as conn:
        with pytest.raises(ValueError, match="Unsupported"):
            await guard_or_unlink_pack_drafts_conn(
                conn,  # type: ignore[arg-type]
                fk_column="bad_col",
                target_uuid=target_uid,
                entity_type="AGENT",
                entity_label="a1",
            )
        with pytest.raises(EntityReferencedByPackDraftError) as exc_ref:
            await guard_or_unlink_pack_drafts_conn(
                conn,  # type: ignore[arg-type]
                fk_column="catalog_item_id",
                target_uuid=target_uid,
                entity_type="AGENT",
                entity_label="a1",
                unlink_from_draft_packs=False,
            )
        assert exc_ref.value.http_status == 409
        assert exc_ref.value.draft_packs[0]["pack_slug"] == "my-draft"

    unlinked = await delete_agent_from_postgres18(
        eng,
        "a1",
        unlink_from_draft_packs=True,
        actor_id="u1",  # type: ignore[arg-type]
    )
    assert len(unlinked) == 1
    assert "PACK_DRAFT_MEMBER_UNLINKED_ON_ENTITY_DELETE" in audit_events
    assert any("DELETE FROM catalog_items" in s for s in deleted_sql)

    ag_rec = ManagedAgentRecord(
        agent_id="ag1",
        slug="ag1",
        uri="orcia://agents/ag1",
        name="Ag1",
        handle="@ag1",
        role_mission="R",
        instructions="I",
        thinking_level="medium",
    )
    await delete_skill_with_agent_sync(
        eng,
        "s1",
        (ag_rec,),
        unlink_from_draft_packs=True,
    )
    with pytest.raises(ScopeAccessDeniedError):
        await delete_catalog_item_guarded(eng, "pack-owned", "INSTRUCTION", raise_if_missing=True)
    with pytest.raises(ResourceNotFoundError):
        await delete_catalog_item_guarded(
            eng, "missing-item", "HELP_ARTICLE", raise_if_missing=True
        )
    with pytest.raises(ScopeAccessDeniedError):

        def _deny_draft(_b: str, _st: str, _sid: str) -> None:
            raise ScopeAccessDeniedError()

        await delete_catalog_item_guarded(
            eng,
            "instr-1",
            "INSTRUCTION",
            unlink_from_draft_packs=True,
            authorize_draft_cb=_deny_draft,
        )
    uid_del, unl_del = await delete_catalog_item_guarded(
        eng, "instr-1", "INSTRUCTION", unlink_from_draft_packs=True
    )
    assert uid_del and len(unl_del) == 1

    with pytest.raises(ValidationDomainError):
        await delete_entity_guarded_tx(
            eng,
            entity_type="UNKNOWN",
            entity_id_or_key="x",  # type: ignore[arg-type]
        )
    with pytest.raises(ResourceNotFoundError):
        await delete_entity_guarded_tx(
            eng,
            entity_type="POLICY",
            entity_id_or_key="",  # type: ignore[arg-type]
        )
    out = await delete_entity_guarded_tx(
        eng,
        entity_type="ONTOLOGY_CONCEPT",
        entity_id_or_key="k1",
        unlink_from_draft_packs=True,  # type: ignore[arg-type]
    )
    assert out.deleted_id == "k1"
    assert len(out.unlinked_draft_packs) == 1
