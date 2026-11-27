"""Unit tests for closure helpers, views, workflow scrubber & scope reads (`<= 270 L`)."""

from __future__ import annotations

from uuid_utils import uuid7

from orcia_core.packs._internal._pack_closure_helpers import (
    extract_refs_from_payload,
    normalized_lookup_candidates,
)
from orcia_core.packs._internal._pack_closure_lint import aliases_for_member, norm_ref
from orcia_core.packs._internal._pack_export_loaders import RawExportEntities
from orcia_core.packs._internal._pack_export_scrubber import TenantInfraIdentifiers
from orcia_core.packs._internal._pack_export_views import views_from_non_draft_entities
from orcia_core.packs._internal._pack_export_workflow_scrubber import (
    scrub_vsm_v2_spec,
    scrub_workflow_v2_spec,
)
from orcia_core.packs.models import PackDraftEntityType, PackSlotSpec


def test_closure_helpers_views_and_workflow_scrubber_branches() -> None:
    """Exercise all extraction, norm, views, and workflow/VSM scrubbing branches."""
    assert norm_ref("") == ""
    assert norm_ref("pack:sdlc:item@1.0") == "item"
    assert norm_ref("/bare") == "bare"
    assert norm_ref("a/b") == "b"
    assert normalized_lookup_candidates("pack:sdlc:sla") == ["pack:sdlc:sla", "sla", "sdlc"]
    aliases = aliases_for_member(PackDraftEntityType.ONTOLOGY_CONCEPT, "pack:p:sla", "sla")
    assert "sla" in aliases and "p:sla" in aliases

    ag_refs = extract_refs_from_payload(
        PackDraftEntityType.AGENT,
        "ag",
        {
            "meta": {
                "skill_ids": ["s1"],
                "ontology_views": ["c1"],
                "instruction_refs": ["i1"],
                "policy_keys": ["p1"],
            }
        },
    )
    assert {r.entity_type for r in ag_refs} == {
        PackDraftEntityType.SKILL,
        PackDraftEntityType.ONTOLOGY_CONCEPT,
        PackDraftEntityType.INSTRUCTION,
        PackDraftEntityType.POLICY,
    }
    wf_refs = extract_refs_from_payload(
        PackDraftEntityType.WORKFLOW_V2,
        "wf",
        {
            "spec": {
                "vsm_id": "v1",
                "allowed_delegate_agents": ["ag1"],
                "knowledge_feedback_target_agent": "ag2",
                "contract": {"output_schema_uri": "orcia://packs/p/instructions/out"},
                "controls": {
                    "non_deterministic": [{"agent_ref": "eval-ag"}],
                    "deterministic": [
                        {"config": {"mechanism_slug": "m1", "ontology_axiom_keys": ["ax1"]}}
                    ],
                },
                "sub_steps": [
                    {
                        "instruction_prompt_or_ref": "orcia://packs/p/instructions/step-i",
                        "skill_refs": ["sk2"],
                        "sub_workflow_id": "wf2",
                        "mechanism_slug": "m2",
                        "ontology_axiom_keys": ["ax2"],
                    },
                    {"instruction_prompt_or_ref": "orcia://packs/p/skills/sk3"},
                ],
            }
        },
    )
    assert any(r.entity_type == PackDraftEntityType.INSTRUCTION for r in wf_refs)
    assert any(r.entity_type == PackDraftEntityType.DNA_MECHANISM for r in wf_refs)
    vsm_refs = extract_refs_from_payload(
        PackDraftEntityType.VSM_V2,
        "vsm",
        {
            "spec": {
                "nodes": [
                    {
                        "linked_workflow_id": "wf1",
                        "agent_ref": "ag1",
                        "controls": {"non_deterministic": [{"agent_ref": "eval2"}]},
                    }
                ]
            }
        },
    )
    assert len(vsm_refs) == 3

    ds_id = str(uuid7())
    infra = TenantInfraIdentifiers(
        tenant_uuids=frozenset({ds_id}),
        tenant_emails=frozenset({"owner@internal.test"}),
        datasource_slots_by_ref={ds_id: {"slot_key": "repo", "scheme": "git"}},
    )
    slots: dict[str, PackSlotSpec] = {}
    wf = scrub_workflow_v2_spec(
        {
            "id": "wf1",
            "slug": "wf1",
            "title": "WF1",
            "pack_id": "ws",
            "contract": {
                "output_schema_uri": "orcia://workspaces/ws/agents/a1",
                "parameters": [{"name": "p1", "label": "P1", "catalog_entity_uri_pattern": ds_id}],
            },
            "controls": {
                "deterministic": [
                    {
                        "id": "d1",
                        "name": "D1",
                        "short_label": "D1",
                        "runner_plugin_id": "r1",
                        "verifies_description": "v",
                        "on_ko_behavior": "block",
                        "config": {"ds": ds_id, "owner": "owner@internal.test", "n": 1},
                    }
                ]
            },
            "sub_steps": [
                {
                    "id": "s1",
                    "name": "S1",
                    "short_label": "S1",
                    "trigger_condition_label": "Go",
                    "role_description": "Role",
                    "instruction_prompt_or_ref": "Do",
                    "output_description": "Out",
                    "checkpoint_label": "Chk",
                    "toolbox_mcp_permissions": [{"git": ds_id}],
                }
            ],
        },
        pack_slug="p",
        infra=infra,
        slots_by_key=slots,
    )
    assert wf.controls.deterministic[0].config["ds"] == "slot://repo"
    assert wf.controls.deterministic[0].config["owner"] == ""

    vsm = scrub_vsm_v2_spec(
        {
            "id": "v1",
            "slug": "v1",
            "title": "V1",
            "subtitle": "S",
            "source_note": "N",
            "guiding_principle": "G",
            "pack_id": "ws",
            "knowledge_foundation": {"k": ds_id},
            "phases": [{"id": "p1", "label": "P1"}],
            "nodes": [
                {
                    "node_type": "step",
                    "num": "1",
                    "phase_id": "p1",
                    "title": "T1",
                    "human_co_author": "owner@internal.test",
                    "input_actuel": "i",
                    "input_ia": "i",
                    "output_actuel": "o",
                    "output_ia": "o",
                    "actor_actuel": "a",
                    "actor_ia": "a",
                    "validation_actuel": "v",
                    "validation_ia": "v",
                    "humans_actuel": [{"email": "owner@internal.test"}],
                    "controls": {"non_deterministic": []},
                }
            ],
        },
        pack_slug="p",
        infra=infra,
        slots_by_key=slots,
    )
    assert vsm.knowledge_foundation["k"] == "slot://repo"

    views = views_from_non_draft_entities(
        "b1",
        RawExportEntities(
            catalog_items=[
                {"id": "1", "resource_id": "s1", "item_type": "USER_SKILL"},
                {"id": "2", "resource_id": "h1", "item_type": "HELP_ARTICLE"},
                {"id": "3", "resource_id": "i1", "item_type": "INSTRUCTION"},
            ],
            workflows_v2=[{"id": "4", "workflow_id": "w1", "slug": "w1"}],
            vsms_v2=[{"id": "5", "vsm_id": "v1", "slug": "v1"}],
            concepts=[{"id": "6", "concept_key": "pack:p:c1"}],
            relations=[{"id": "7", "relation_key": "pack:p:r1"}],
            axioms=[{"id": "8", "axiom_key": "pack:p:a1"}],
            dna_mechanisms=[{"id": "9", "mechanism_slug": "m1"}],
            policies=[{"id": "10", "policy_key": "p:pol"}],
        ),
    )
    assert len(views) == 10

    from orcia_core.packs._internal._pack_export_workflow_scrubber import _scrub_controls_pipeline

    assert _scrub_controls_pipeline("raw", pack_slug="p", infra=infra, slots_by_key=slots) == "raw"
    piped = _scrub_controls_pipeline(
        {
            "non_deterministic": [
                "raw-entry",
                {"agent_ref": "orcia://workspaces/ws/agents/a1", "model_override": "gpt-4o"},
            ]
        },
        pack_slug="p",
        infra=infra,
        slots_by_key=slots,
    )
    assert piped["non_deterministic"][1]["agent_ref"] == "orcia://packs/p/agents/a1"
    wf2 = scrub_workflow_v2_spec(
        {
            "id": "wf2",
            "slug": "wf2",
            "title": "WF2",
            "pack_id": "ws",
            "model_override": "claude-sonnet-4",
            "global_system_prompt_or_ref": ds_id,
            "knowledge_feedback_target_agent": "orcia://workspaces/ws/agents/a1",
            "allowed_delegate_agents": ["orcia://workspaces/ws/agents/a2"],
            "sub_steps": [],
        },
        pack_slug="p",
        infra=infra,
        slots_by_key=slots,
    )
    assert wf2.allowed_delegate_agents == ["orcia://packs/p/agents/a2"]
    vsm2 = scrub_vsm_v2_spec(
        {
            "id": "v2",
            "slug": "v2",
            "title": "V2",
            "subtitle": "S",
            "source_note": "N",
            "guiding_principle": "G",
            "pack_id": "ws",
            "agents_catalog": {"a": {"ref": ds_id}},
            "phases": [],
            "nodes": [],
        },
        pack_slug="p",
        infra=infra,
        slots_by_key=slots,
    )
    assert vsm2.agents_catalog["a"]["ref"] == "slot://repo"
