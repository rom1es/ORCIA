"""PG18 + SeaweedFS S3 & 8-entity seeding helpers for Story 31.5 integration test (`<= 160 L`)."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import sqlalchemy as sa
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from tests.integration._story_31_4_pack_fixture import run_alembic_head
from uuid_utils import uuid7

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def pg18_and_seaweed_urls_315() -> Iterator[tuple[str, str]]:
    """Start ephemeral PG18 (`/tmp` Unix socket) + SeaweedFS S3 (`4.17`)."""
    sock_dir = Path(tempfile.mkdtemp(prefix="orcia_31_5_pg18_"))
    sock_dir.chmod(0o777)
    pg_box = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(sock_dir), "/var/run/postgresql", "rw")
    )
    s3_box = (
        DockerContainer("chrislusf/seaweedfs:4.17")
        .with_command("server -s3 -s3.port=9000 -ip.bind=0.0.0.0 -dir=/tmp")
        .with_env("AWS_ACCESS_KEY_ID", "orcia_seaweed")
        .with_env("AWS_SECRET_ACCESS_KEY", "orcia_seaweed_secret")  # pragma: allowlist secret
        .with_exposed_ports(9000)
    )
    try:
        with pg_box as pg, s3_box as s3:
            for _ in range(150):
                out_b, err_b = pg.get_logs()
                logs = (out_b + err_b).decode("utf-8", errors="ignore")
                if (
                    logs.count("database system is ready to accept connections") >= 2
                    and (sock_dir / ".s.PGSQL.5432").exists()
                ):
                    break
                time.sleep(0.2)
            wait_for_logs(s3, "Start Seaweed S3 API Server", timeout=30)
            s3_url = f"http://127.0.0.1:{int(s3.get_exposed_port(9000))}"
            pg_auth = "orcia:orcia_dev_secret"  # pragma: allowlist secret
            pg_url = f"postgresql+asyncpg://{pg_auth}@/orcia?host={sock_dir}"
            run_alembic_head(pg_url)
            yield pg_url, s3_url
    finally:
        shutil.rmtree(sock_dir, ignore_errors=True)


async def seed_story_31_5_entities(
    eng: Any,
    *,
    org_id: str,
    ws_a: str,
    ds_a_id: str,
) -> dict[str, str]:
    """Seed standalone entities across all 8 typed FK target tables in PG18."""
    ids = {
        "agent_id": "ag-315-reviewer",
        "skill_id": "sk-315-lint",
        "wf_id": "wf-315-delivery",
        "vsm_id": "vsm-315-flow",
        "c1_key": "ws315:sla",
        "c2_key": "ws315:slo",
        "rel_key": "ws315:rel-supports",
        "ax_key": "ws315:ax-positive",
        "dna_slug": "dna_check_315",
        "pol_key": "ws315-git-ro",
    }
    star_src = "def evaluate(p):\n    return {'passed': bool(p.get('ok'))}\n"
    star_sha = hashlib.sha256(star_src.encode("utf-8")).hexdigest()
    src_bundle_id = str(uuid7())
    c1_uid, c2_uid = str(uuid7()), str(uuid7())

    async with eng.begin() as conn:
        await conn.execute(
            sa.text(
                "INSERT INTO catalog_items (id, resource_id, uri, title, description, "
                "resource_type, source_format, version, sha256, cas_key, visibility_scope, "
                "owner_org_unit_id, owner_workspace_id, item_type, metadata_jsonb) "
                "VALUES "
                "(CAST(:sk_uid AS uuid), :sk_id, 'orcia://ws/skills/sk-315-lint', 'Skill 315', "
                "'Lint skill', 'skill', 'ORCIA', '1.0.0', :sha, :cas, 'SHARED_WORKSPACE', "
                "CAST(:org AS uuid), CAST(:ws AS uuid), 'USER_SKILL', CAST(:sk_meta AS jsonb)),"
                "(CAST(:ag_uid AS uuid), :ag_id, 'orcia://ws/agents/ag-315-reviewer', "
                "'Reviewer 315', 'Reviews changes', 'agent', 'ORCIA', '1.0.0', :sha, :cas, "
                "'SHARED_WORKSPACE', CAST(:org AS uuid), CAST(:ws AS uuid), 'USER_AGENT', "
                "CAST(:ag_meta AS jsonb))"
            ),
            {
                "sk_uid": str(uuid7()),
                "ag_uid": str(uuid7()),
                "sk_id": ids["skill_id"],
                "ag_id": ids["agent_id"],
                "sha": "a" * 64,
                "cas": "cas/" + ("a" * 64),
                "org": org_id,
                "ws": ws_a,
                "sk_meta": json.dumps(
                    {
                        "slug": "sk-315-lint",
                        "command_handle": "/sk-315-lint",
                        "instructions": "Run lint check cleanly.",
                        "lifecycle_status": "ACTIVE",
                        "owner_workspace_id": ws_a,
                    }
                ),
                "ag_meta": json.dumps(
                    {
                        "slug": "ag-315-reviewer",
                        "instructions": "Review code using repo connector.",
                        "skill_ids": ["sk-315-lint"],
                        "connector_slots": [ds_a_id],
                        "posture": "REVIEWER",
                        "human_partner_role": "TECH_LEAD",
                        "llm_model_tier": "claude-3-7-sonnet",
                        "lifecycle_status": "ACTIVE",
                        "owner_workspace_id": ws_a,
                    }
                ),
            },
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workflow_definitions_v2 "
                "(id, workflow_id, slug, version, status, pack_id, execution_mode, spec_jsonb) "
                "VALUES (CAST(:uid AS uuid), :wid, :wid, '1.0.0', 'published', 'workspace', "
                "'native_orcia', CAST(:spec AS jsonb))"
            ),
            {
                "uid": str(uuid7()),
                "wid": ids["wf_id"],
                "spec": json.dumps(
                    {
                        "id": ids["wf_id"],
                        "pack_id": "workspace",
                        "slug": ids["wf_id"],
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
                                "agent_ref": "ag-315-reviewer",
                                "allowed_rag_sources": [ds_a_id],
                            }
                        ],
                    }
                ),
            },
        )
        await conn.execute(
            sa.text(
                "INSERT INTO vsm_definitions_v2 (id, vsm_id, slug, pack_id, title, spec_jsonb) "
                "VALUES (CAST(:uid AS uuid), :vid, :vid, 'workspace', 'VSM 315', "
                "CAST(:spec AS jsonb))"
            ),
            {
                "uid": str(uuid7()),
                "vid": ids["vsm_id"],
                "spec": json.dumps(
                    {
                        "id": ids["vsm_id"],
                        "pack_id": "workspace",
                        "slug": ids["vsm_id"],
                        "title": "VSM 315",
                        "subtitle": "Flow",
                        "source_note": "Src",
                        "guiding_principle": "Principle",
                        "phases": [],
                        "nodes": [],
                    }
                ),
            },
        )
        await conn.execute(
            sa.text(
                "INSERT INTO ontology_concepts (id, concept_key, canonical_term, level, scope_id, "
                "definition_text) VALUES "
                "(CAST(:c1 AS uuid), :k1, 'SLA', '3_WORKSPACE', :ws, 'Target latency'),"
                "(CAST(:c2 AS uuid), :k2, 'SLO', '3_WORKSPACE', :ws, 'Objective')"
            ),
            {"c1": c1_uid, "c2": c2_uid, "k1": ids["c1_key"], "k2": ids["c2_key"], "ws": ws_a},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO ontology_relations (id, relation_key, source_concept_id, "
                "target_concept_id, relation_type, cardinality) "
                "VALUES (CAST(:id AS uuid), :rk, CAST(:c1 AS uuid), CAST(:c2 AS uuid), "
                "'SUPPORTS', '1..N')"
            ),
            {"id": str(uuid7()), "rk": ids["rel_key"], "c1": c1_uid, "c2": c2_uid},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO ontology_axioms (id, axiom_key, concept_id, level, scope_id, "
                "rule_expression, immutable) VALUES (CAST(:id AS uuid), :ak, CAST(:c1 AS uuid), "
                "'3_WORKSPACE', :ws, 'sla_hours > 0', FALSE)"
            ),
            {"id": str(uuid7()), "ak": ids["ax_key"], "c1": c1_uid, "ws": ws_a},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO declarative_pack_bundles (id, pack_id, slug, name, version, "
                "rbac_namespace, bundle_sha256, archive_sha256, bundle_kind, scope_type, scope_id, "
                "status, source_origin) VALUES (CAST(:id AS uuid), 'orcia-pack-src315', 'src315', "
                "'Source 315', '1.0.0', 'src315', :sha, :sha, 'IMPORTED', 'WORKSPACE', :ws, "
                "'PUBLISHED', 'APM_ZIP')"
            ),
            {"id": src_bundle_id, "sha": "b" * 64, "ws": ws_a},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO pack_dna_mechanisms (id, pack_bundle_id, mechanism_slug, name, "
                "starlark_source, source_sha256) VALUES (CAST(:id AS uuid), CAST(:bid AS uuid), "
                ":mslug, 'DNA Check 315', :src, :sha)"
            ),
            {
                "id": str(uuid7()),
                "bid": src_bundle_id,
                "mslug": ids["dna_slug"],
                "src": star_src,
                "sha": star_sha,
            },
        )
        await conn.execute(
            sa.text(
                "INSERT INTO permission_broker_policies (id, policy_key, uri_pattern, "
                "connector_scheme, required_role, approver_team, request_url_template, sla_hours, "
                "procedure_markdown) VALUES (CAST(:id AS uuid), :pk, 'git://ws315/*', 'git', "
                "'DEVELOPER', 'sec-ops', 'git://ws315/req', 8, 'Request read access.')"
            ),
            {"id": str(uuid7()), "pk": ids["pol_key"]},
        )
    return ids


__all__ = ["REPO_ROOT", "pg18_and_seaweed_urls_315", "seed_story_31_5_entities"]
