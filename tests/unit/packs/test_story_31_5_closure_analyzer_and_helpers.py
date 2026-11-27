"""Unit tests for Story 31.5 transitive closure analyzer & prose linter (`<= 270 L`)."""

from __future__ import annotations

from typing import Any

import pytest
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult
from uuid_utils import uuid7

from orcia_core.packs._internal._pack_closure_analyzer import (
    analyze_and_optionally_expand_closure_conn,
)
from orcia_core.packs._internal._pack_closure_helpers import (
    aliases_for_member,
    extract_agent_refs,
    extract_refs_from_payload,
    extract_vsm_refs,
    extract_workflow_refs,
    fk_uuid_for_member,
    lint_prose_bare_handles,
    normalized_lookup_candidates,
)
from orcia_core.packs.composer_models import PackDraftMemberView
from orcia_core.packs.errors import PackClosureIncompleteError
from orcia_core.packs.models import PackDraftEntityType


def test_closure_helpers_extraction_and_prose_linter() -> None:
    """Verify ref extraction across agent, workflow, VSM, relation, axiom & bare-handle lint."""
    ag_refs = extract_agent_refs("reviewer", {"skill_ids": ["ws:lint"], "ontology_views": ["SLA"]})
    assert [(r.entity_type, r.lookup_key) for r in ag_refs] == [
        (PackDraftEntityType.SKILL, "ws:lint"),
        (PackDraftEntityType.ONTOLOGY_CONCEPT, "SLA"),
    ]
    wf_refs = extract_workflow_refs(
        "wf-1",
        {
            "vsm_id": "vsm-1",
            "allowed_delegate_agents": ["helper"],
            "knowledge_feedback_target_agent": "curator",
            "sub_steps": [
                {
                    "agent_ref": "@planner",
                    "instruction_prompt_or_ref": "orcia://packs/p/skills/plan",
                    "skill_refs": ["/check"],
                    "linked_workflow_id": "orcia://packs/p/workflows/sub-wf",
                    "dna_mechanism_slug": "check_rule",
                    "ontology_axiom_keys": ["ax-1"],
                },
                {"instruction_prompt_or_ref": "@solo"},
                {"instruction_prompt_or_ref": "orcia://packs/p/agents/deep-agent"},
            ],
        },
    )
    types = {r.entity_type for r in wf_refs}
    assert PackDraftEntityType.VSM_V2 in types
    assert PackDraftEntityType.AGENT in types
    assert PackDraftEntityType.SKILL in types
    assert PackDraftEntityType.WORKFLOW_V2 in types
    assert PackDraftEntityType.DNA_MECHANISM in types
    assert PackDraftEntityType.ONTOLOGY_AXIOM in types

    vsm_refs = extract_vsm_refs(
        "vsm-1", {"nodes": [{"linked_workflow_id": "wf-1", "owner_agent_ref": "reviewer"}]}
    )
    assert len(vsm_refs) == 2

    assert "lint" in aliases_for_member(PackDraftEntityType.SKILL, "ws:lint", "lint")
    assert normalized_lookup_candidates("@pack/reviewer") == ["@pack/reviewer", "reviewer"]
    assert (
        fk_uuid_for_member(
            PackDraftMemberView(
                id="1",
                draft_bundle_id="b",
                entity_type=PackDraftEntityType.POLICY,
                entity_id="p1",
                entity_slug="p1",
                policy_id="u1",
            )
        )
        == "u1"
    )
    assert (
        len(
            extract_refs_from_payload(
                PackDraftEntityType.ONTOLOGY_RELATION,
                "r1",
                {"source_concept_id": "c1", "target_concept_id": "c2"},
            )
        )
        == 2
    )
    assert (
        len(
            extract_refs_from_payload(
                PackDraftEntityType.ONTOLOGY_AXIOM, "a1", {"concept_id": "c1"}
            )
        )
        == 1
    )

    warnings = lint_prose_bare_handles(
        "AGENT",
        "reviewer",
        "Delegate to @planner and run /check before @custom/qualified or /custom/ok.",
        known_agent_slugs=frozenset({"planner"}),
        known_skill_slugs=frozenset({"check"}),
    )
    assert {w.token for w in warnings} == {"@planner", "/check"}


@pytest.mark.asyncio
async def test_closure_analyzer_blocks_incomplete_and_auto_includes_transitive_deps() -> None:
    """Verify `422 ERR_PACK_CLOSURE_INCOMPLETE`, `auto_include_dependencies=True` & DRAFT block."""
    ws_id, bundle_id = str(uuid7()), str(uuid7())
    wf_uid, ag_uid, sk_uid = str(uuid7()), str(uuid7()), str(uuid7())
    inserted: list[str] = []

    def handler(sql: str, params: dict[str, Any]) -> FakeSqlResult:
        if "FROM workspaces" in sql:
            return FakeSqlResult(rows=[(ws_id, None)])
        if "WITH RECURSIVE anc" in sql:
            return FakeSqlResult(rows=[])
        if "FROM workflow_definitions_v2" in sql and "WHERE id = CAST(:uid AS uuid)" in sql:
            return FakeSqlResult(
                rows=[
                    (
                        "published",
                        {
                            "sub_steps": [
                                {"agent_ref": "planner", "skill_refs": []},
                            ]
                        },
                    )
                ]
            )
        if "FROM catalog_items WHERE id = CAST(:uid AS uuid)" in sql:
            if params["uid"] == ag_uid:
                return FakeSqlResult(
                    rows=[
                        (
                            "Planner",
                            {
                                "instructions": "Ask @planner and /lint-skill.",
                                "skill_ids": ["lint-skill"],
                                "lifecycle_status": "ACTIVE",
                            },
                        )
                    ]
                )
            return FakeSqlResult(
                rows=[("Lint", {"instructions": "Run lint.", "lifecycle_status": "ACTIVE"})]
            )
        if "FROM catalog_items" in sql and "WHERE (id::text = :k OR resource_id = :k)" in sql:
            k = params["k"]
            if k == "planner":
                return FakeSqlResult(
                    mappings=[
                        {
                            "uid": ag_uid,
                            "eid": "planner",
                            "title": "Planner",
                            "bid": None,
                            "ws_id": ws_id,
                            "metadata_jsonb": {"slug": "planner", "lifecycle_status": "ACTIVE"},
                        }
                    ]
                )
            if k == "lint-skill":
                return FakeSqlResult(
                    mappings=[
                        {
                            "uid": sk_uid,
                            "eid": "lint-skill",
                            "title": "Lint Skill",
                            "bid": None,
                            "ws_id": ws_id,
                            "metadata_jsonb": {"slug": "lint-skill", "lifecycle_status": "ACTIVE"},
                        }
                    ]
                )
            return FakeSqlResult(mappings=[])
        if "INSERT INTO pack_draft_memberships" in sql:
            inserted.append(f"{params['etype']}:{params['eid']}")
            return FakeSqlResult()
        return FakeSqlResult(mappings=[])

    eng = FakeSqlEngine(handler)
    wf_member = PackDraftMemberView(
        id="m-wf",
        draft_bundle_id=bundle_id,
        entity_type=PackDraftEntityType.WORKFLOW_V2,
        entity_id="wf-main",
        entity_slug="wf-main",
        lifecycle_status="PUBLISHED",
        workflow_v2_id=wf_uid,
    )
    async with eng.begin() as conn:
        with pytest.raises(PackClosureIncompleteError) as exc_info:
            await analyze_and_optionally_expand_closure_conn(
                conn,  # type: ignore[arg-type]
                bundle_id=bundle_id,
                scope_type="WORKSPACE",
                scope_id=ws_id,
                members=[wf_member],
                auto_include_dependencies=False,
                fail_on_incomplete=True,
            )
        assert exc_info.value.http_status == 422
        assert exc_info.value.missing_dependencies[0]["entity_id"] == "planner"

        report = await analyze_and_optionally_expand_closure_conn(
            conn,  # type: ignore[arg-type]
            bundle_id=bundle_id,
            scope_type="WORKSPACE",
            scope_id=ws_id,
            members=[wf_member],
            auto_include_dependencies=True,
            can_mutate_draft=True,
            fail_on_incomplete=True,
        )
        assert report.complete is True
        assert report.auto_included_count == 2
        assert inserted == ["AGENT:planner", "SKILL:lint-skill"]
        assert {w.token for w in report.prose_lint_warnings} == {"@planner", "/lint-skill"}

    draft_ag = PackDraftMemberView(
        id="m-ag",
        draft_bundle_id=bundle_id,
        entity_type=PackDraftEntityType.AGENT,
        entity_id="draft-bot",
        entity_slug="draft-bot",
        lifecycle_status="DRAFT",
        catalog_item_id=sk_uid,
    )
    async with eng.connect() as conn:
        with pytest.raises(PackClosureIncompleteError) as exc_draft:
            await analyze_and_optionally_expand_closure_conn(
                conn,  # type: ignore[arg-type]
                bundle_id=bundle_id,
                scope_type="WORKSPACE",
                scope_id=ws_id,
                members=[draft_ag],
                require_active=True,
                fail_on_incomplete=True,
            )
        assert exc_draft.value.missing_dependencies[0]["reason"] == "NON_ACTIVE_STATUS"
