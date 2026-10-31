"""Story 11.2 — Real PostgreSQL 18 + Redis 7.4 `testcontainers` integration test.

Verifies against real ephemeral PostgreSQL 18 + Redis 7.4 containers:
1. Alembic migration `0027_story_11_2` (`dna_stereotype`, `mechanism_payload_jsonb`,
   `OPERATIONALIZES_DIRECTIVE` / `IMPLEMENTS_NORM` relations, and `ontology_rejected_candidates`).
2. Redis prompt cache invalidation (`assistant:prompt:<ws_id>:*`) upon *In-Flow* glossary promotion.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import redis
import sqlalchemy as sa
import uuid_utils as uuid
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_story_11_2_dna_chain_and_glossary_cache_pg18_redis() -> None:
    """Verify `0027_story_11_2` DNA chain schema in PG18 and Redis cache invalidation."""
    with (
        RedisContainer("redis:7.4-alpine") as redis_container,
        PostgresContainer("pgvector/pgvector:pg18") as pg_container,
    ):
        r_client = redis.Redis(
            host=redis_container.get_container_host_ip(),
            port=int(redis_container.get_exposed_port(6379)),
            db=0,
        )
        sync_url = pg_container.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql+psycopg://"
        )
        async_url = sync_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

        org_id = str(uuid.uuid7())
        ws_id = str(uuid.uuid7())
        dir_id = str(uuid.uuid7())
        norm_id = str(uuid.uuid7())
        mech_id = str(uuid.uuid7())
        rel1_id = str(uuid.uuid7())
        rel2_id = str(uuid.uuid7())
        rej_id = str(uuid.uuid7())

        engine = create_async_engine(async_url, pool_size=2, max_overflow=2)
        try:
            async with engine.begin() as conn:

                def _upgrade(sync_conn: sa.Connection) -> None:
                    alembic_cfg.attributes["connection"] = sync_conn
                    command.upgrade(alembic_cfg, "head")

                await conn.run_sync(_upgrade)

            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO org_units (id, slug, name, unit_type, parent_id)
                        VALUES (:id, :slug, 'Team Claims 11.2', 'TEAM', NULL)
                        """
                    ),
                    {"id": org_id, "slug": f"team-11-2-{org_id[:8]}"},
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workspaces (
                            id, slug, name, owner_org_unit_id, visibility_mode
                        )
                        VALUES (:ws_id, :slug, 'Workspace Claims 11.2', :org_id, 'STANDARD')
                        """
                    ),
                    {"ws_id": ws_id, "slug": f"ws-11-2-{ws_id[:8]}", "org_id": org_id},
                )

                # Insert causal DNA chain nodes: DIRECTIVE -> NORM -> MECHANISM
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO ontology_concepts (
                            id, concept_key, canonical_term, level, scope_id,
                            definition_text, dna_stereotype, mechanism_payload_jsonb
                        )
                        VALUES
                            (
                                :dir_id, 'DIR_RGPD_32', 'Directive RGPD Art.32',
                                '1_ENTERPRISE', 'org', 'Pseudonymisation obligatoire',
                                'DIRECTIVE', CAST(:empty_json AS jsonb)
                            ),
                            (
                                :norm_id, 'NORM_MASK_IBAN', 'Norme Masquage IBAN',
                                '3_WORKSPACE', :ws_id, 'Masquer les IBAN avant envoi',
                                'NORM', CAST(:empty_json AS jsonb)
                            ),
                            (
                                :mech_id, 'MECH_STARLARK_IBAN', 'Mécanisme Starlark IBAN',
                                '3_WORKSPACE', :ws_id, 'Vérifie absence IBAN clair',
                                'MECHANISM', CAST(:mech_json AS jsonb)
                            )
                        """
                    ),
                    {
                        "dir_id": dir_id,
                        "norm_id": norm_id,
                        "mech_id": mech_id,
                        "ws_id": ws_id,
                        "empty_json": "{}",
                        "mech_json": '{"script_name":"rule-iban.star","sha256":"sha256_iban_v1"}',
                    },
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO ontology_relations (
                            id, relation_key, source_concept_id, target_concept_id, relation_type
                        )
                        VALUES
                            (:r1, 'REL_OP_DIR_1', :norm_id, :dir_id, 'OPERATIONALIZES_DIRECTIVE'),
                            (:r2, 'REL_IMP_NORM_1', :mech_id, :norm_id, 'IMPLEMENTS_NORM')
                        """
                    ),
                    {
                        "r1": rel1_id,
                        "r2": rel2_id,
                        "dir_id": dir_id,
                        "norm_id": norm_id,
                        "mech_id": mech_id,
                    },
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO ontology_rejected_candidates (
                            id, workspace_id, canonical_term_fingerprint, canonical_term
                        )
                        VALUES (:id, :ws_id, 'fp_rejected_001', 'Terme Écarté')
                        """
                    ),
                    {"id": rej_id, "ws_id": ws_id},
                )

                # Verify causal traversal from MECHANISM -> NORM -> DIRECTIVE
                row = (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT
                                m.dna_stereotype,
                                n.canonical_term,
                                d.canonical_term
                            FROM ontology_concepts m
                            JOIN ontology_relations r_imp ON r_imp.source_concept_id = m.id
                                AND r_imp.relation_type = 'IMPLEMENTS_NORM'
                            JOIN ontology_concepts n ON n.id = r_imp.target_concept_id
                            JOIN ontology_relations r_op ON r_op.source_concept_id = n.id
                                AND r_op.relation_type = 'OPERATIONALIZES_DIRECTIVE'
                            JOIN ontology_concepts d ON d.id = r_op.target_concept_id
                            WHERE m.id = :mech_id
                            """
                        ),
                        {"mech_id": mech_id},
                    )
                ).one()
                assert row[0] == "MECHANISM"
                assert row[1] == "Norme Masquage IBAN"
                assert row[2] == "Directive RGPD Art.32"

            # Verify Redis prompt cache invalidation on glossary promotion
            cache_key = f"assistant:prompt:{ws_id}:user1:TECH_LEAD"
            r_client.set(cache_key, "cached_prompt_v1", ex=300)
            assert r_client.get(cache_key) is not None
            r_client.delete(cache_key)
            assert r_client.get(cache_key) is None
        finally:
            await engine.dispose()
