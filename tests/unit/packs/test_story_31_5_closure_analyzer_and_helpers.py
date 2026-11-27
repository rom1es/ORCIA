"""Unit tests for Story 31.5 transitive closure ref extraction & prose linter (`<= 120 L`)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from orcia_core.packs import PackComposerService, PackImportService
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
from orcia_core.packs._internal._pack_export_views import views_from_non_draft_entities
from orcia_core.packs.composer_models import PackDraftMemberView
from orcia_core.packs.models import PackDraftEntityType
from orcia_core.storage.pack_draft_guard import _validated_fk_column

pytestmark = pytest.mark.story("31.5")


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


def test_pack_services_require_engine_views_and_draft_guard_fk_validation() -> None:
    """Cover unconfigured engine guards, non-draft agent view conversion, and FK allowlist."""
    composer = PackComposerService()
    with pytest.raises(RuntimeError, match="AsyncEngine"):
        composer._require_engine()
    composer.set_engine(object())  # type: ignore[arg-type]
    composer.set_cas_storage(None)

    importer = PackImportService()
    with pytest.raises(RuntimeError, match="AsyncEngine"):
        importer._require_engine()
    importer.set_cas_storage(None)

    raw_entities = SimpleNamespace(
        catalog_items=[
            {
                "id": "0195f000-0000-7000-8000-000000000111",
                "item_type": "USER_AGENT",
                "resource_id": "ws:a1",
            }
        ],
        workflows_v2=[],
        vsms_v2=[],
        concepts=[],
        relations=[],
        axioms=[],
        dna_mechanisms=[],
        policies=[],
    )
    views = views_from_non_draft_entities("b1", raw_entities)
    assert views[0].entity_type == PackDraftEntityType.AGENT

    with pytest.raises(ValueError, match="Unsupported pack_draft_memberships"):
        _validated_fk_column("evil_column; DROP TABLE")
