"""Story 23.5 — Layer 2 PostgreSQL 18 Integration Tests for Federated Search (`GET /api/v1/search`).

Verifies on real `pgvector/pgvector:pg18` + real Composition Root `create_app()`
(ZERO `dependency_overrides`, ZERO manual `app.state.*` injection):
1. Zero invented fallback hits when no PG18 record matches (`hits == []`).
2. `load_federated_search_candidates_pg18` and `GET /api/v1/search` load real rows from:
   `catalog_items`, `workflow_definitions_v2`, `declarative_pack_bundles`, `workspaces`,
   and `assistant_folders`.
3. Speed 1 (`0 $`, `locked_top=True`) + Speed 2 (`speed2_executed=True`, deduplicated by `item_id`,
   `badge='✨ Passage proche'` appended at bottom, second identical query hits Speed 2 cache).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

try:
    from testcontainers.community.postgres import PostgresContainer
except ImportError:
    from testcontainers.postgres import PostgresContainer

from orcia_core.rag import load_federated_search_candidates_pg18
from orcia_kernel.ids import new_uuid7_str

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_23_5_search"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_23_5_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    """Start ephemeral PostgreSQL 18 + pgvector container migrated to Alembic head."""
    with PostgresContainer(
        "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
    ) as pg:
        url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        subprocess.run(
            [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        yield url


@pytest.mark.asyncio
async def test_story_23_5_federated_search_reads_real_pg18_without_invented_data(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boot real `create_app()` via lifespan without overrides and test PG18 search."""
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-23-5-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-23-5-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    from orcia_api.main import create_app

    app = create_app()
    assert app.dependency_overrides == {}

    engine = create_async_engine(database_url)
    try:
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            # 1. Bootstrap first admin, org hierarchy, workspace, and active GLOBAL embedding model
            r_admin = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "search.admin@orcia.ia",
                    "display_name": "Search Admin",
                    "password": "OrciaSearch!2026",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert r_admin.status_code == 200, r_admin.text
            admin_token = r_admin.json()["access_token"]
            headers = {"Authorization": f"Bearer {admin_token}"}

            async with engine.connect() as conn:
                admin_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT id::text FROM users "
                            "WHERE email = 'search.admin@orcia.ia' LIMIT 1"
                        )
                    )
                ).first()
            assert admin_row is not None
            admin_id = str(admin_row[0])

            r_bu = await client.post(
                "/api/v1/org-units",
                headers=headers,
                json={"name": "Direction Search", "slug": "bu-search-235", "kind": "BU"},
            )
            assert r_bu.status_code == 200, r_bu.text
            bu_id = r_bu.json()["id"]

            r_team = await client.post(
                "/api/v1/org-units",
                headers=headers,
                json={
                    "name": "Équipe Search",
                    "slug": "team-search-235",
                    "kind": "TEAM",
                    "parent_id": bu_id,
                },
            )
            assert r_team.status_code == 200, r_team.text
            team_id = r_team.json()["id"]

            r_ws = await client.post(
                "/api/v1/workspaces",
                headers=headers,
                json={
                    "name": "Espace Trésorerie 235",
                    "slug": "ws-tresorerie-235",
                    "owner_org_unit_id": team_id,
                    "visibility_mode": "STANDARD",
                },
            )
            assert r_ws.status_code in (200, 201), r_ws.text
            async with engine.connect() as conn:
                ws_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT id::text FROM workspaces "
                            "WHERE slug = 'ws-tresorerie-235' LIMIT 1"
                        )
                    )
                ).first()
            assert ws_row is not None
            ws_id = str(ws_row[0])

            r_emb = await client.post(
                "/api/v1/settings/ai-models/mappings",
                headers=headers,
                json={
                    "scope_level": "GLOBAL",
                    "scope_id": ws_id,
                    "display_name": "Embedding PG18 Test",
                    "inference_tier": "simple",
                    "effort": "default",
                    "provider_slug": "ollama",
                    "model_family": "ollama",
                    "model_name": "bge-m3:latest",
                    "endpoint_uri": "http://127.0.0.1:11434/v1",
                    "auth_mode": "none_local",
                    "protocol_mode": "openai_compatible",
                    "usage": "embedding",
                },
            )
            assert r_emb.status_code in (200, 201), r_emb.text

            # 2. Query matching NO PG18 record -> 0 invented fallback candidates
            r_empty = await client.get(
                "/api/v1/search",
                headers=headers,
                params={
                    "q": "introuvable_sans_aucun_enregistrement_23_5",
                    "scope": "ALL_WORKSPACES",
                    "workspace_id": ws_id,
                    "include_speed2": "false",
                },
            )
            assert r_empty.status_code == 200, r_empty.text
            empty_json = r_empty.json()
            assert empty_json["hits"] == []
            assert empty_json["speed1_llm_cost_usd"] == 0.0
            assert empty_json["speed2_executed"] is False

            # 3. Insert real rows in the 5 PG18 tables queried by sql_federated_search.py
            folder_id = new_uuid7_str()
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO catalog_items (
                            id, resource_id, uri, title, description, resource_type,
                            source_format, version, sha256, cas_key, visibility_scope,
                            owner_org_unit_id, owner_workspace_id, item_type
                        ) VALUES
                        (
                            CAST(:id1 AS uuid), 'cat-agent-sepa-235', 'orcia://agents/sepa-235',
                            'Agent Conformité SEPA 235', 'Vérification des virements SEPA',
                            'agent', 'ORCIA', '1.0.0', :sha1, :cas1, 'SHARED_WORKSPACE',
                            CAST(:oid AS uuid), CAST(:wid AS uuid), 'CATALOG_RESOURCE'
                        ),
                        (
                            CAST(:id2 AS uuid), 'cat-ds-ledger-235', 'git://repo/ledger-235',
                            'Source Grand Livre 235', 'Dépôt comptable temps réel',
                            'datasource', 'ORCIA', '1.0.0', :sha2, :cas2, 'SHARED_WORKSPACE',
                            CAST(:oid AS uuid), CAST(:wid AS uuid), 'CATALOG_RESOURCE'
                        )
                        """
                    ),
                    {
                        "id1": new_uuid7_str(),
                        "id2": new_uuid7_str(),
                        "sha1": "a" * 64,
                        "cas1": "cas/" + "a" * 64,
                        "sha2": "b" * 64,
                        "cas2": "cas/" + "b" * 64,
                        "oid": team_id,
                        "wid": ws_id,
                    },
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workflow_definitions_v2 (
                            id, workflow_id, slug, version, status, pack_id, spec_jsonb
                        ) VALUES (
                            CAST(:id AS uuid), 'wf-sepa-235', 'wf-sepa-235', '1.0.0',
                            'published', 'pack-fin-235', CAST(:spec AS jsonb)
                        )
                        """
                    ),
                    {
                        "id": new_uuid7_str(),
                        "spec": json.dumps(
                            {
                                "title": "Processus Rapprochement SEPA 235",
                                "summary": "Contrôle automatisé des flux SEPA.",
                            }
                        ),
                    },
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO declarative_pack_bundles (
                            id, pack_id, slug, name, version, rbac_namespace, bundle_sha256
                        ) VALUES (
                            CAST(:id AS uuid), 'pack-fin-235', 'pack-finance-235',
                            'Pack Finance SEPA 235', '2.0.0', 'finance', :sha
                        )
                        """
                    ),
                    {"id": new_uuid7_str(), "sha": "c" * 64},
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO assistant_folders (
                            folder_id, workspace_id, owner_user_id, title, consolidated_summary
                        ) VALUES (
                            CAST(:fid AS uuid), CAST(:wid AS uuid), CAST(:uid AS uuid),
                            'Dossier Trésorerie SEPA 235', 'Synthèse des arbitrages SEPA.'
                        )
                        """
                    ),
                    {"fid": folder_id, "wid": ws_id, "uid": admin_id},
                )

            # Verify direct loader returns all 5 PG18 sources for authenticated admin
            # while fail-closing restricted catalog & private folder rows for anonymous caller
            async with engine.connect() as conn:
                loaded_anon = await load_federated_search_candidates_pg18(conn)
                loaded = await load_federated_search_candidates_pg18(
                    conn, user_id=admin_id, user_role="PLATFORM_ADMIN"
                )
            anon_ids = {c.item_id for c in loaded_anon}
            assert "pg-catalog:cat-agent-sepa-235" not in anon_ids
            assert f"pg-folder:{folder_id}" not in anon_ids
            loaded_ids = {c.item_id for c in loaded}
            assert "pg-catalog:cat-agent-sepa-235" in loaded_ids
            assert "pg-catalog:cat-ds-ledger-235" in loaded_ids
            assert "pg-workflow:wf-sepa-235" in loaded_ids
            assert "pg-pack:pack-fin-235" in loaded_ids
            assert f"pg-workspace:{ws_id}" in loaded_ids
            assert f"pg-folder:{folder_id}" in loaded_ids

            # 4. Speed 1 search via HTTP matches real PG18 entities
            r_speed1 = await client.get(
                "/api/v1/search",
                headers=headers,
                params={
                    "q": "SEPA 235",
                    "scope": "ALL_WORKSPACES",
                    "workspace_id": ws_id,
                    "include_speed2": "false",
                },
            )
            assert r_speed1.status_code == 200, r_speed1.text
            s1_json = r_speed1.json()
            s1_ids = [h["item_id"] for h in s1_json["hits"]]
            assert s1_json["speed2_executed"] is False
            assert s1_json["speed1_llm_cost_usd"] == 0.0
            assert "pg-catalog:cat-agent-sepa-235" in s1_ids
            assert "pg-workflow:wf-sepa-235" in s1_ids
            assert "pg-pack:pack-fin-235" in s1_ids
            assert f"pg-folder:{folder_id}" in s1_ids
            assert all(h["speed_tier"] == 1 and h["locked_top"] is True for h in s1_json["hits"])

            # 5. Speed 1 + Speed 2 (`force_semantic=true` or >= 3 words) deduplicates by `item_id`
            r_speed2 = await client.get(
                "/api/v1/search",
                headers=headers,
                params={
                    "q": "Conformité SEPA 235",
                    "scope": "ALL_WORKSPACES",
                    "workspace_id": ws_id,
                    "include_speed2": "true",
                },
            )
            assert r_speed2.status_code == 200, r_speed2.text
            s2_json = r_speed2.json()
            assert s2_json["speed2_executed"] is True
            assert s2_json["speed2_cache_hit"] is False
            hit_ids = [h["item_id"] for h in s2_json["hits"]]
            assert len(hit_ids) == len(set(hit_ids)), "hits must be deduplicated by item_id"
            assert "pg-catalog:cat-agent-sepa-235" in hit_ids
            assert f"pg-workspace:{ws_id}" in hit_ids
            tier1_hits = [h for h in s2_json["hits"] if h["speed_tier"] == 1]
            tier2_hits = [h for h in s2_json["hits"] if h["speed_tier"] == 2]
            assert len(tier1_hits) >= 1
            assert len(tier2_hits) >= 1
            assert all(h["locked_top"] is True for h in tier1_hits)
            assert all(
                h["locked_top"] is False and h["badge"] == "✨ Passage proche" for h in tier2_hits
            )

            # 6. Second identical Speed 2 call hits cache
            r_speed2_cached = await client.get(
                "/api/v1/search",
                headers=headers,
                params={
                    "q": "Conformité SEPA 235",
                    "scope": "ALL_WORKSPACES",
                    "workspace_id": ws_id,
                    "include_speed2": "true",
                },
            )
            assert r_speed2_cached.status_code == 200, r_speed2_cached.text
            assert r_speed2_cached.json()["speed2_executed"] is True
            assert r_speed2_cached.json()["speed2_cache_hit"] is True
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_story_23_5_federated_search_multi_user_isolation_postgres18(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify multi-user PG18 + Speed 2 cache isolation (0 leak from User A to User B)."""
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-23-5-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-23-5-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    from orcia_api.main import create_app

    app = create_app()
    assert app.dependency_overrides == {}

    engine = create_async_engine(database_url)
    try:
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            # Ensure platform admin + active embedding model exist (order-independent)
            async with engine.connect() as conn:
                user_count = (
                    await conn.execute(sa.text("SELECT COUNT(*)::int FROM users"))
                ).scalar_one()
            if user_count == 0:
                r_boot = await client.post(
                    "/api/v1/bootstrap/welcome-setup/first-admin",
                    json={
                        "email": "search.admin@orcia.ia",
                        "display_name": "Search Admin",
                        "password": "OrciaSearch!2026",  # pragma: allowlist secret
                        "orcia_env": "local",
                    },
                )
                assert r_boot.status_code == 200, r_boot.text
                admin_token = r_boot.json()["access_token"]
            else:
                r_login_admin = await client.post(
                    "/api/v1/auth/login/local",
                    json={
                        "email": "search.admin@orcia.ia",
                        "password": "OrciaSearch!2026",  # pragma: allowlist secret
                    },
                )
                assert r_login_admin.status_code == 200, r_login_admin.text
                admin_token = r_login_admin.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            r_bu = await client.post(
                "/api/v1/org-units",
                headers=admin_headers,
                json={"name": "Direction Isolation", "slug": "bu-iso-235", "kind": "BU"},
            )
            assert r_bu.status_code == 200, r_bu.text
            bu_id = r_bu.json()["id"]

            r_team_a = await client.post(
                "/api/v1/org-units",
                headers=admin_headers,
                json={
                    "name": "Équipe Alpha Iso",
                    "slug": "team-alpha-iso-235",
                    "kind": "TEAM",
                    "parent_id": bu_id,
                },
            )
            assert r_team_a.status_code == 200, r_team_a.text
            team_a_id = r_team_a.json()["id"]

            r_team_b = await client.post(
                "/api/v1/org-units",
                headers=admin_headers,
                json={
                    "name": "Équipe Beta Iso",
                    "slug": "team-beta-iso-235",
                    "kind": "TEAM",
                    "parent_id": bu_id,
                },
            )
            assert r_team_b.status_code == 200, r_team_b.text
            team_b_id = r_team_b.json()["id"]

            r_ws_shared = await client.post(
                "/api/v1/workspaces",
                headers=admin_headers,
                json={
                    "name": "Espace Alpha Iso",
                    "slug": "ws-alpha-iso-235",
                    "owner_org_unit_id": team_a_id,
                    "visibility_mode": "STANDARD",
                },
            )
            assert r_ws_shared.status_code in (200, 201), r_ws_shared.text

            r_ws_priv = await client.post(
                "/api/v1/workspaces",
                headers=admin_headers,
                json={
                    "name": "Espace Confidentiel AliceIsoXYZ",
                    "slug": "ws-priv-alice-iso-235",
                    "owner_org_unit_id": team_a_id,
                    "visibility_mode": "PRIVATE_USER",
                },
            )
            assert r_ws_priv.status_code in (200, 201), r_ws_priv.text

            async with engine.connect() as conn:
                ws_alpha_id = str(
                    (
                        await conn.execute(
                            sa.text(
                                "SELECT id::text FROM workspaces WHERE slug = 'ws-alpha-iso-235'"
                            )
                        )
                    ).scalar_one()
                )
                ws_priv_alice_id = str(
                    (
                        await conn.execute(
                            sa.text(
                                "SELECT id::text FROM workspaces "
                                "WHERE slug = 'ws-priv-alice-iso-235'"
                            )
                        )
                    ).scalar_one()
                )

            if user_count == 0:
                r_emb = await client.post(
                    "/api/v1/settings/ai-models/mappings",
                    headers=admin_headers,
                    json={
                        "scope_level": "GLOBAL",
                        "scope_id": ws_alpha_id,
                        "display_name": "Embedding PG18 Isolation Test",
                        "inference_tier": "simple",
                        "effort": "default",
                        "provider_slug": "ollama",
                        "model_family": "ollama",
                        "model_name": "bge-m3:latest",
                        "endpoint_uri": "http://127.0.0.1:11434/v1",
                        "auth_mode": "none_local",
                        "protocol_mode": "openai_compatible",
                        "usage": "embedding",
                    },
                )
                assert r_emb.status_code in (200, 201), r_emb.text

            # Create User A (member of team_a_id) and User B (member of team_b_id only)
            r_user_a = await client.post(
                "/api/v1/settings/iam/accounts",
                headers=admin_headers,
                json={
                    "account_kind": "HUMAN",
                    "display_name": "Alice Isolée",
                    "email": "alice.isolated@orcia.ia",
                    "principal_id": "alice.isolated@orcia.ia",
                    "roles": ["CONTRIBUTOR"],
                    "team_ids": [team_a_id],
                    "status": "ACTIVE",
                },
            )
            assert r_user_a.status_code == 200, r_user_a.text
            pw_a = r_user_a.json()["temporary_password"]

            r_user_b = await client.post(
                "/api/v1/settings/iam/accounts",
                headers=admin_headers,
                json={
                    "account_kind": "HUMAN",
                    "display_name": "Bob Isolé",
                    "email": "bob.isolated@orcia.ia",
                    "principal_id": "bob.isolated@orcia.ia",
                    "roles": ["CONTRIBUTOR"],
                    "team_ids": [team_b_id],
                    "status": "ACTIVE",
                },
            )
            assert r_user_b.status_code == 200, r_user_b.text
            pw_b = r_user_b.json()["temporary_password"]

            r_login_a = await client.post(
                "/api/v1/auth/login/local",
                json={"email": "alice.isolated@orcia.ia", "password": pw_a},
            )
            assert r_login_a.status_code == 200, r_login_a.text
            headers_a = {"Authorization": f"Bearer {r_login_a.json()['access_token']}"}

            r_login_b = await client.post(
                "/api/v1/auth/login/local",
                json={"email": "bob.isolated@orcia.ia", "password": pw_b},
            )
            assert r_login_b.status_code == 200, r_login_b.text
            headers_b = {"Authorization": f"Bearer {r_login_b.json()['access_token']}"}

            async with engine.connect() as conn:
                user_a_id = str(
                    (
                        await conn.execute(
                            sa.text(
                                "SELECT id::text FROM users WHERE email = 'alice.isolated@orcia.ia'"
                            )
                        )
                    ).scalar_one()
                )

            # Grant User A explicit membership on PRIVATE_USER workspace only (never User B)
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workspace_memberships (
                            id, workspace_id, user_id, role, access_mode
                        ) VALUES (
                            CAST(:id AS uuid),
                            CAST(:wid AS uuid),
                            CAST(:uid AS uuid),
                            'CONTRIBUTOR',
                            'CONTRIBUTOR_ACTION_REQUIRED'
                        )
                        """
                    ),
                    {"id": new_uuid7_str(), "wid": ws_priv_alice_id, "uid": user_a_id},
                )

            # User A creates a PRIVATE folder via real API in ws_alpha_id
            r_folder_a = await client.post(
                "/api/v1/assistant/folders",
                headers=headers_a,
                json={
                    "workspace_id": ws_alpha_id,
                    "title": "Dossier Secret AliceIsoXYZ",
                    "pinned_notes_markdown": "Note privée confidentielle AliceIsoXYZ",
                    "consolidated_summary": "Données confidentielles réservées à AliceIsoXYZ",
                },
            )
            assert r_folder_a.status_code == 200, r_folder_a.text
            folder_a_id = r_folder_a.json()["folder_id"]

            # Verify visibility_mode is PRIVATE in PG18
            async with engine.connect() as conn:
                vis_mode = str(
                    (
                        await conn.execute(
                            sa.text(
                                "SELECT visibility_mode FROM assistant_folders "
                                "WHERE folder_id = CAST(:fid AS uuid)"
                            ),
                            {"fid": folder_a_id},
                        )
                    ).scalar_one()
                )
            assert vis_mode == "PRIVATE"

            # User A searches (Speed 2 enabled) -> sees her PRIVATE folder & PRIVATE_USER workspace
            secret_query = "Confidentiel AliceIsoXYZ Secret"  # pragma: allowlist secret
            r_search_a1 = await client.get(
                "/api/v1/search",
                headers=headers_a,
                params={
                    "q": secret_query,
                    "scope": "ALL_WORKSPACES",
                    "workspace_id": ws_alpha_id,
                    "include_speed2": "true",
                },
            )
            assert r_search_a1.status_code == 200, r_search_a1.text
            a1_json = r_search_a1.json()
            assert a1_json["speed2_executed"] is True
            a1_ids = {h["item_id"] for h in a1_json["hits"]}
            assert f"pg-folder:{folder_a_id}" in a1_ids
            assert f"pg-workspace:{ws_priv_alice_id}" in a1_ids

            # User A 2nd call hits Speed 2 cache (`speed2_cache_hit=True`)
            r_search_a2 = await client.get(
                "/api/v1/search",
                headers=headers_a,
                params={
                    "q": secret_query,
                    "scope": "ALL_WORKSPACES",
                    "workspace_id": ws_alpha_id,
                    "include_speed2": "true",
                },
            )
            assert r_search_a2.status_code == 200, r_search_a2.text
            assert r_search_a2.json()["speed2_cache_hit"] is True

            # User B (distinct unshared CONTRIBUTOR) queries the exact same Speed 2 string -> 0 leak
            r_search_b_speed1 = await client.get(
                "/api/v1/search",
                headers=headers_b,
                params={
                    "q": secret_query,
                    "scope": "ALL_WORKSPACES",
                    "workspace_id": ws_alpha_id,
                    "include_speed2": "false",
                },
            )
            assert r_search_b_speed1.status_code == 200, r_search_b_speed1.text
            assert r_search_b_speed1.json()["hits"] == []

            r_search_b1 = await client.get(
                "/api/v1/search",
                headers=headers_b,
                params={
                    "q": secret_query,
                    "scope": "ALL_WORKSPACES",
                    "workspace_id": ws_alpha_id,
                    "include_speed2": "true",
                },
            )
            assert r_search_b1.status_code == 200, r_search_b1.text
            b1_json = r_search_b1.json()
            assert b1_json["speed2_cache_hit"] is False
            b1_ids = {h["item_id"] for h in b1_json["hits"]}
            assert f"pg-folder:{folder_a_id}" not in b1_ids
            assert f"pg-workspace:{ws_priv_alice_id}" not in b1_ids
            assert not any("AliceIsoXYZ" in f"{h['title']} {h['snippet']}" for h in b1_json["hits"])

            # Even on User B's subsequent Speed 2 cache hit -> 0 leak
            r_search_b2 = await client.get(
                "/api/v1/search",
                headers=headers_b,
                params={
                    "q": secret_query,
                    "scope": "ALL_WORKSPACES",
                    "workspace_id": ws_alpha_id,
                    "include_speed2": "true",
                },
            )
            assert r_search_b2.status_code == 200, r_search_b2.text
            b2_json = r_search_b2.json()
            assert b2_json["speed2_cache_hit"] is True
            b2_ids = {h["item_id"] for h in b2_json["hits"]}
            assert f"pg-folder:{folder_a_id}" not in b2_ids
            assert f"pg-workspace:{ws_priv_alice_id}" not in b2_ids
            assert not any("AliceIsoXYZ" in f"{h['title']} {h['snippet']}" for h in b2_json["hits"])
    finally:
        await engine.dispose()
