"""Extra PG18 fixture helpers for Story 31.5 RBAC, cleanup & round-trip tests."""

from __future__ import annotations

import hashlib
import json

import sqlalchemy as sa
from uuid_utils import uuid7


def issue_tok_hdr(app: object, *, uid: str, email: str, role: str, org_id: str) -> dict[str, str]:
    """Issue a Bearer header for a test user using the live app JWT manager."""
    tok = app.state.auth_service.jwt_manager.issue_token_pair(  # type: ignore[attr-defined]
        user_id=uid,
        email=email,
        role=role,
        org_unit_id=org_id,
        archetype="ARCHITECT",
        auth_mode="LOCAL",
    )
    return {"Authorization": f"Bearer {tok.access_token}"}


async def seed_extra_315_fixtures(
    eng: object,
    *,
    org_id: str,
    ws_a: str,
    ws_b: str,
    ds_a_id: str,
    eids: dict[str, str],
) -> dict[str, str]:
    """Seed free agent, INSTRUCTION, HELP_ARTICLE, SYSTEM GLOBAL bundle, VSM & ws_b user."""
    sha = "c" * 64
    sys_bid, sys_sk_uid, wsb_uid = str(uuid7()), str(uuid7()), str(uuid7())
    obs_uid, org_b_id = str(uuid7()), str(uuid7())
    async with eng.begin() as conn:  # type: ignore[attr-defined]
        await conn.execute(
            sa.text(
                "INSERT INTO org_units (id, slug, name, unit_type, parent_id) "
                "VALUES (CAST(:ob AS uuid), 'bu-315-b', 'BU B', 'BU', NULL)"
            ),
            {"ob": org_b_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO users (id, email, display_name, auth_mode, human_profile_archetype, "
                "platform_role, primary_org_unit_id) VALUES "
                "(CAST(:ub AS uuid), 'wsb315@orcia.test', 'WSB Lead', 'LOCAL', 'ARCHITECT', "
                "'CONTRIBUTOR', CAST(:ob AS uuid)),"
                "(CAST(:uo AS uuid), 'obs315@orcia.test', 'Observer 315', 'LOCAL', 'ARCHITECT', "
                "'OBSERVER', CAST(:org AS uuid))"
            ),
            {"ub": wsb_uid, "ob": org_b_id, "uo": obs_uid, "org": org_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workspace_memberships (id, workspace_id, user_id, role, access_mode) "
                "VALUES (CAST(:mid AS uuid), CAST(:ws AS uuid), CAST(:ub AS uuid), "
                "'TEAM_LEAD', 'CONTRIBUTOR_ACTION_REQUIRED')"
            ),
            {"mid": str(uuid7()), "ws": ws_b, "ub": wsb_uid},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO declarative_pack_bundles (id, pack_id, slug, name, version, "
                "rbac_namespace, bundle_sha256, archive_sha256, bundle_kind, scope_type, scope_id, "
                "status, source_origin) VALUES (CAST(:bid AS uuid), 'orcia-pack-sys315', "
                "'sys315', 'System 315', '1.0.0', 'sys315', :sha, :sha, 'SYSTEM', 'GLOBAL', "
                "'global', 'PUBLISHED', 'LOCAL_SYSTEM')"
            ),
            {"bid": sys_bid, "sha": hashlib.sha256(b"sys315").hexdigest()},
        )
        items = (
            (
                sys_sk_uid,
                "sys-315-skill",
                "skill",
                "USER_SKILL",
                sys_bid,
                {
                    "slug": "sys-315-skill",
                    "instructions": "Global skill.",
                    "lifecycle_status": "ACTIVE",
                },
            ),
            (
                str(uuid7()),
                "ag-free-315",
                "agent",
                "USER_AGENT",
                None,
                {
                    "slug": "ag-free-315",
                    "instructions": "Free agent.",
                    "lifecycle_status": "ACTIVE",
                },
            ),
            (
                str(uuid7()),
                "instr-315",
                "template",
                "INSTRUCTION",
                None,
                {
                    "slug": "instr-315",
                    "markdown_body": "# Follow checklist",
                    "lifecycle_status": "ACTIVE",
                },
            ),
            (
                str(uuid7()),
                "help-315",
                "template",
                "HELP_ARTICLE",
                None,
                {
                    "slug": "help-315",
                    "summary_what_for": "Help summary",
                    "markdown_body": "# Help Body 315\nUse safely.",
                    "lifecycle_status": "ACTIVE",
                },
            ),
        )
        for uid, rid, rtype, itype, pbid, meta in items:
            await conn.execute(
                sa.text(
                    "INSERT INTO catalog_items (id, resource_id, uri, title, description, "
                    "resource_type, source_format, version, sha256, cas_key, visibility_scope, "
                    "owner_org_unit_id, owner_workspace_id, item_type, pack_bundle_id, "
                    "metadata_jsonb) VALUES (CAST(:uid AS uuid), :rid, :uri, :rid, 'Desc', "
                    ":rt, 'ORCIA', '1.0.0', :sha, :cas, :vis, CAST(:org AS uuid), "
                    "CAST(:ws AS uuid), :it, CAST(:pbid AS uuid), CAST(:meta AS jsonb))"
                ),
                {
                    "uid": uid,
                    "rid": rid,
                    "uri": f"orcia://ws/{rid}",
                    "rt": rtype,
                    "sha": sha,
                    "cas": f"cas/{sha}",
                    "vis": "PUBLISHED_ORG" if pbid else "SHARED_WORKSPACE",
                    "org": org_id,
                    "ws": None if pbid else ws_a,
                    "it": itype,
                    "pbid": pbid,
                    "meta": json.dumps(meta),
                },
            )
        wf_spec = {
            "id": eids["wf_id"],
            "pack_id": "workspace",
            "slug": eids["wf_id"],
            "title": "Delivery 315",
            "version": "1.0.0",
            "status": "published",
            "sub_steps": [
                {
                    "id": "step-1",
                    "name": "Review",
                    "short_label": "Rev",
                    "trigger_condition_label": "Start",
                    "role_description": "Check",
                    "instruction_prompt_or_ref": "orcia://workspaces/ws/agents/ag-315-reviewer",
                    "output_description": "Report",
                    "checkpoint_label": "Approve",
                    "agent_ref": eids["agent_id"],
                    "toolbox_mcp_permissions": [{"git": ds_a_id}],
                }
            ],
        }
        vsm_spec = {
            "id": eids["vsm_id"],
            "pack_id": "workspace",
            "slug": eids["vsm_id"],
            "title": "VSM 315",
            "subtitle": "Flow",
            "source_note": "Src",
            "guiding_principle": "Principle",
            "phases": [{"id": "p1", "label": "Build"}],
            "nodes": [
                {
                    "node_type": "step",
                    "num": "1",
                    "phase_id": "p1",
                    "title": "Review Node",
                    "input_actuel": "i",
                    "input_ia": "i",
                    "output_actuel": "o",
                    "output_ia": "o",
                    "actor_actuel": "a",
                    "actor_ia": "a",
                    "validation_actuel": "v",
                    "validation_ia": "v",
                    "agent_ref": eids["agent_id"],
                    "linked_workflow_id": eids["wf_id"],
                    "controls": {"non_deterministic": []},
                }
            ],
        }
        await conn.execute(
            sa.text(
                "UPDATE workflow_definitions_v2 SET spec_jsonb = CAST(:s AS jsonb) WHERE slug = :id"
            ),
            {"s": json.dumps(wf_spec), "id": eids["wf_id"]},
        )
        await conn.execute(
            sa.text(
                "UPDATE vsm_definitions_v2 SET spec_jsonb = CAST(:s AS jsonb) WHERE slug = :id"
            ),
            {"s": json.dumps(vsm_spec), "id": eids["vsm_id"]},
        )
        team_id, bu_bid, kpi_uid = str(uuid7()), str(uuid7()), str(uuid7())
        await conn.execute(
            sa.text(
                "INSERT INTO org_units (id, slug, name, unit_type, parent_id) "
                "VALUES (CAST(:tid AS uuid), 'team-315-a', 'Team A', 'TEAM', CAST(:org AS uuid))"
            ),
            {"tid": team_id, "org": org_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO declarative_pack_bundles (id, pack_id, slug, name, version, "
                "rbac_namespace, bundle_sha256, archive_sha256, bundle_kind, scope_type, scope_id, "
                "status, source_origin) VALUES (CAST(:bid AS uuid), 'orcia-pack-bupack315', "
                "'bupack315', 'BU Pack 315', '1.0.0', 'bupack315', :sha, :sha, 'ORG', 'BU', "
                ":org, 'PUBLISHED', 'APM_ZIP')"
            ),
            {"bid": bu_bid, "sha": sha, "org": org_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO ontology_concepts (id, concept_key, canonical_term, level, scope_id, "
                "definition_text, pack_bundle_id) VALUES (CAST(:cid AS uuid), "
                "'pack:bupack315:kpi', 'KPI', '2_DOMAIN', 'bupack315', 'Pack domain KPI', "
                "CAST(:bid AS uuid))"
            ),
            {"cid": kpi_uid, "bid": bu_bid},
        )
    return {
        "sys_bid": sys_bid,
        "wsb_uid": wsb_uid,
        "obs_uid": obs_uid,
        "team_id": team_id,
    }


__all__ = ["issue_tok_hdr", "seed_extra_315_fixtures"]
