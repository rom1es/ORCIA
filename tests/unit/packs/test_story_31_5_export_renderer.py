"""Unit tests for Story 31.5 deterministic `.zip` & `apm.lock.yaml` renderer (`<= 280 L`)."""

from __future__ import annotations

import io
import zipfile

import pytest
from uuid_utils import uuid7

from orcia_core.packs._internal._apm_entry_router import ParsedPackEntries, ingest_pack_entry
from orcia_core.packs._internal._pack_export_loaders import RawExportEntities
from orcia_core.packs._internal._pack_export_renderer import build_and_scan_export_archive
from orcia_core.packs._internal._pack_export_scrubber import TenantInfraIdentifiers
from orcia_core.packs.errors import PackClosureIncompleteError
from orcia_core.packs.models import PackReadinessStatus


def test_build_and_scan_export_archive_deterministic_and_scrubbed() -> None:
    """Verify deterministic `.zip` SHA-256, `apm.lock.yaml`, slot de-binding & VSM/WF scrub."""
    ds_id = str(uuid7())
    c1_id, c2_id = str(uuid7()), str(uuid7())
    infra = TenantInfraIdentifiers(
        tenant_uuids=frozenset({ds_id, c1_id, c2_id}),
        tenant_emails=frozenset({"owner@internal.test"}),
        datasource_slots_by_ref={
            ds_id: {"slot_key": "code_repo", "scheme": "git", "connector_kind": "git"}
        },
    )
    entities = RawExportEntities(
        catalog_items=[
            {
                "id": str(uuid7()),
                "resource_id": "rev-agent",
                "item_type": "USER_AGENT",
                "resource_type": "agent",
                "title": "Reviewer",
                "description": "Reviews code",
                "metadata_jsonb": {
                    "slug": "reviewer",
                    "instructions": "Review carefully.",
                    "skill_ids": ["orcia://workspaces/ws-1/skills/lint-code"],
                    "connector_slots": [ds_id],
                    "allowed_rag_sources": ["all_workspace_sources", ds_id],
                    "llm_model_tier": "claude-3-7-sonnet",
                    "posture": "REVIEWER",
                    "human_partner_role": "TECH_LEAD",
                },
            },
            {
                "id": str(uuid7()),
                "resource_id": "lint-code",
                "item_type": "USER_SKILL",
                "resource_type": "skill",
                "title": "Lint",
                "description": "Lint skill",
                "metadata_jsonb": {
                    "slug": "lint-code",
                    "command_handle": "/lint-code",
                    "instructions": "Run deterministic lint.",
                    "lifecycle_status": "DRAFT",
                    "input_parameters": ["target"],
                },
            },
            {
                "id": str(uuid7()),
                "resource_id": "instr-std",
                "item_type": "INSTRUCTION",
                "resource_type": "instruction",
                "title": "Standards",
                "description": "Code standards",
                "metadata_jsonb": {"apply_to": "**/*.py", "body_markdown": "Use strict typing."},
            },
            {
                "id": str(uuid7()),
                "resource_id": "help-fr",
                "item_type": "HELP_ARTICLE",
                "resource_type": "help_article",
                "title": "Aide",
                "description": "Guide",
                "metadata_jsonb": {
                    "lang": "fr",
                    "bound_routes": ["/packs"],
                    "summary_what_for": "Pour les packs.",
                    "markdown_body": "Aide markdown_body complete.",
                },
            },
        ],
        workflows_v2=[
            {
                "id": str(uuid7()),
                "workflow_id": "vsm-helper",
                "slug": "vsm-helper",
                "version": "1.0.0",
                "status": "draft",
                "spec_jsonb": {
                    "id": "vsm-helper",
                    "pack_id": "workspace",
                    "slug": "vsm-helper",
                    "title": "Review Flow",
                    "version": "1.0.0",
                    "status": "draft",
                    "model_override": "claude-3-7-sonnet",
                    "global_system_prompt_or_ref": "orcia://workspaces/ws-1/agents/reviewer",
                    "knowledge_feedback_target_agent": "orcia://workspaces/ws-1/agents/reviewer",
                    "contract": {"output_schema_uri": "orcia://workspaces/ws-1/agents/reviewer"},
                    "controls": {
                        "non_deterministic": [
                            {
                                "id": "nd1",
                                "name": "Eval",
                                "short_label": "Eval",
                                "evaluator_type": "adversarial_agent",
                                "agent_ref": "orcia://workspaces/ws-1/agents/reviewer",
                                "model_override": "gpt-4o",
                                "verifies_description": "Verify",
                                "on_ko_behavior": "block",
                            }
                        ]
                    },
                    "sub_steps": [
                        {
                            "id": "s1",
                            "name": "Review",
                            "short_label": "Rev",
                            "trigger_condition_label": "Start",
                            "role_description": "Check",
                            "instruction_prompt_or_ref": "orcia://workspaces/ws-1/agents/reviewer",
                            "output_description": "Report",
                            "checkpoint_label": "Approve",
                            "allowed_rag_sources": [ds_id],
                            "toolbox_mcp_permissions": [{"git": ds_id}],
                        }
                    ],
                },
            }
        ],
        vsms_v2=[
            {
                "id": str(uuid7()),
                "vsm_id": "vsm-deliv",
                "slug": "vsm-deliv",
                "title": "Delivery",
                "spec_jsonb": {
                    "id": "vsm-deliv",
                    "pack_id": "ws",
                    "slug": "vsm-deliv",
                    "title": "Delivery",
                    "subtitle": "Delivery sub",
                    "source_note": "Note",
                    "guiding_principle": "Quality first",
                    "phases": [{"id": "p1", "label": "Plan"}],
                    "agents_catalog": {
                        "rev": {"connector_slots": [ds_id], "email": "owner@internal.test"}
                    },
                    "nodes": [
                        {
                            "node_type": "step",
                            "num": "1",
                            "phase_id": "p1",
                            "title": "Step 1",
                            "agent_ref": "orcia://workspaces/ws-1/agents/reviewer",
                            "linked_workflow_id": "orcia://workspaces/ws-1/workflows/vsm-helper",
                            "input_actuel": "In",
                            "input_ia": "In",
                            "output_actuel": "Out",
                            "output_ia": "Out",
                            "actor_actuel": "Dev",
                            "actor_ia": "AI",
                            "validation_actuel": "Ok",
                            "validation_ia": "Ok",
                            "tools_actuel": [ds_id],
                        }
                    ],
                },
            }
        ],
        concepts=[
            {
                "id": c1_id,
                "concept_key": "pack:custom-pack:SLA",
                "canonical_term": "SLA",
                "definition_text": "Target latency",
            },
            {
                "id": c2_id,
                "concept_key": "pack:custom-pack:SLO",
                "canonical_term": "SLO",
                "definition_text": "Objective",
            },
        ],
        relations=[
            {
                "id": str(uuid7()),
                "relation_key": "pack:custom-pack:rel:0",
                "source_concept_id": c1_id,
                "target_concept_id": c2_id,
                "relation_type": "SUPPORTS",
                "cardinality": "1..N",
            }
        ],
        axioms=[
            {
                "id": str(uuid7()),
                "axiom_key": "pack:custom-pack:ax:0",
                "concept_id": c1_id,
                "rule_expression": "sla_hours > 0",
                "immutable": True,
            }
        ],
        dna_mechanisms=[
            {
                "mechanism_slug": "check_sla",
                "name": "Check SLA",
                "starlark_source": "def evaluate(p):\n  return {'passed': True}\n",
                "source_sha256": "a" * 64,
            }
        ],
        policies=[
            {
                "policy_key": "custom-pack:git-ro",
                "uri_pattern": "git://*",
                "connector_scheme": "git",
                "required_role": "DEVELOPER",
                "sla_hours": 12,
                "procedure_markdown": "Request access.",
            }
        ],
    )
    row = {
        "id": str(uuid7()),
        "pack_id": "orcia-pack-custom-pack",
        "slug": "custom-pack",
        "name": "Custom Pack",
        "version": "1.2.0",
        "author": "owner@internal.test",
        "description": "Portable bundle",
        "manifest_jsonb": {"maintainers": ["owner@internal.test", "Maintainer Name"]},
        "declared_slots_jsonb": [],
    }
    b1, files1, lock1, zip1, sha1 = build_and_scan_export_archive(
        bundle_row=row, entities=entities, infra=infra
    )
    _b2, _f2, _l2, zip2, sha2 = build_and_scan_export_archive(
        bundle_row=row, entities=entities, infra=infra
    )
    assert zip1 == zip2
    assert sha1 == sha2
    assert b1.agents[0].skill_refs == ["lint-code"]
    assert b1.agents[0].connector_slots == ["code_repo"]
    assert b1.skills[0].lifecycle_status == PackReadinessStatus.DRAFT
    assert "Aide markdown_body complete." in b1.help_articles[0].body_markdown
    assert b1.manifest.declared_slots[0].slot_key == "code_repo"
    assert lock1["bundle_sha256"]

    # Workflow named `vsm-helper` must still parse back as WorkflowDefinitionV2 (P2-1)
    acc = ParsedPackEntries()
    ingest_pack_entry(
        acc, rel_path="workflows/vsm-helper.yaml", blob=files1["workflows/vsm-helper.yaml"]
    )
    assert len(acc.workflows) == 1 and not acc.vsm_specs

    with zipfile.ZipFile(io.BytesIO(zip1), "r") as zf:
        names = zf.namelist()
        assert "custom-pack/apm.lock.yaml" in names
        assert "custom-pack/ontology/glossary.yaml" in names

    # Missing ontology concept endpoint on relation must fail closed (P2-2)
    broken = RawExportEntities(
        concepts=[entities.concepts[0]],
        relations=entities.relations,
        axioms=[],
    )
    with pytest.raises(PackClosureIncompleteError):
        build_and_scan_export_archive(bundle_row=row, entities=broken, infra=infra)
