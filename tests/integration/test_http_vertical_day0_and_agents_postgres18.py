"""TEST-07 — Intégration verticale HTTP → FastAPI → PostgreSQL 18 (`AD-17` couche 2, garde-fou n°2).

Chaque test sollicite la route FastAPI (`AsyncClient` + `ASGITransport`) **et** vérifie par un
`SELECT` sur un vrai PostgreSQL 18 (`pgvector/pgvector:pg18`, testcontainers) que l'état est
persisté.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_NAME = "orcia_http_vertical"
DB_USER = "orcia"
DB_PASSWORD = "orcia_http_vertical_pw"  # pragma: allowlist secret
ADMIN_EMAIL = "http.vertical.admin@orcia.test"
ADMIN_PASSWORD = "Http-Vertical-Passw0rd!"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    with PostgresContainer(
        "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
    ) as pg:
        url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        env = {
            "PATH": "/usr/bin:/bin",
            "DATABASE_URL": url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        subprocess.run(
            [str(REPO_ROOT / ".venv" / "bin" / "alembic"), "-c", "infra/migrations/alembic.ini"]
            + ["upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        yield url


@pytest.fixture
def app_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-http-vertical-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-http-vertical-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_api.main import create_app

    def _build_client() -> AsyncClient:
        app = create_app()
        initialize_app_services(app)
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _build_client


@pytest.mark.asyncio
async def test_first_admin_http_persists_hashed_account_and_is_single_use(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    payload = {
        "email": ADMIN_EMAIL,
        "display_name": "Admin HTTP Vertical",
        "password": ADMIN_PASSWORD,
        "orcia_env": "local",
    }
    engine = create_async_engine(database_url)
    try:
        async with app_client_factory() as client:
            first = await client.post("/api/v1/bootstrap/welcome-setup/first-admin", json=payload)
            assert first.status_code == 200, first.text

            second = await client.post("/api/v1/bootstrap/welcome-setup/first-admin", json=payload)
            assert second.status_code == 409, second.text
            assert second.json()["error_code"]

        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    sa.text(
                        "SELECT platform_role, password_hash_argon2id, is_active "
                        "FROM users WHERE email = :e"
                    ),
                    {"e": ADMIN_EMAIL},
                )
            ).all()
        assert len(rows) == 1, "exactement un premier administrateur en base"
        role, password_hash, is_active = rows[0]
        assert role == "PLATFORM_ADMIN" and is_active is True
        assert password_hash.startswith("$argon2id$"), "mot de passe jamais stocké en clair"
        assert ADMIN_PASSWORD not in password_hash
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_agent_creation_http_persists_in_catalog_items(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    agent_name = "Agent Vertical HTTP PG18"
    engine = create_async_engine(database_url)
    try:
        async with app_client_factory() as client:
            res = await client.post(
                "/api/v1/agents-and-skills/agents?persona_key=marc",
                json={
                    "name": agent_name,
                    "role_mission": "Valider la persistance verticale.",
                    "instructions": "Répondre brièvement.",
                },
            )
            assert res.status_code == 200, res.text

        async with engine.connect() as conn:
            count = (
                await conn.execute(
                    sa.text(
                        "SELECT count(*) FROM catalog_items WHERE catalog_items::text ILIKE :n"
                    ),
                    {"n": f"%{agent_name}%"},
                )
            ).scalar_one()
        assert count >= 1, "l'agent créé par HTTP doit être présent dans catalog_items"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_platform_setup_state_http_put_persists_settings_org_workspaces_and_llm_in_pg18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Verify `PUT /api/v1/bootstrap/platform-setup-state` writes to 4 PG18 tables and reloads."""
    engine = create_async_engine(database_url)
    try:
        async with app_client_factory() as client:
            put_res = await client.put(
                "/api/v1/bootstrap/platform-setup-state",
                json={
                    "org_units": [
                        {
                            "id": "bu-vertical-claims",
                            "name": "BU Sinistres Vertical",
                            "slug": "bu-vertical-claims",
                            "level": "BU",
                        }
                    ],
                    "rbac_grants": [{"id": "g-vert-1", "role": "TEAM_LEAD", "scope": "GLOBAL"}],
                    "llm_tiers": [
                        {
                            "tier": "medium",
                            "primaryModel": "openai/gpt-4o-vertical",
                            "modelFamily": "openai",
                        }
                    ],
                    "workspaces": [
                        {
                            "workspaceId": "ws-vertical-alpha",
                            "name": "Espace Sinistres Vertical",
                            "slug": "ws-vertical-alpha",
                            "visibilityMode": "STANDARD",
                            "lifecyclePhase": "RUN",
                        }
                    ],
                    "datasources": [{"id": "ds-v1", "uri": "git://claims/vertical"}],
                    "packs": [{"packKey": "orcia-pack-sdlc"}],
                    "workflows": [],
                    "runs": [],
                    "catalog_items": [],
                    "ontology_concepts": [],
                    "audit_events": [],
                },
            )
            assert put_res.status_code == 200, put_res.text
            assert len(put_res.json()["workspaces"]) == 1

            get_res = await client.get("/api/v1/bootstrap/platform-setup-state")
            assert get_res.status_code == 200, get_res.text
            assert get_res.json()["org_units"][0]["slug"] == "bu-vertical-claims"

        async with engine.connect() as conn:
            settings_count = (
                await conn.execute(
                    sa.text(
                        "SELECT count(*) FROM platform_settings "
                        "WHERE key = 'platform_setup_state_v1'"
                    )
                )
            ).scalar_one()
            org_count = (
                await conn.execute(
                    sa.text("SELECT count(*) FROM org_units WHERE slug = 'bu-vertical-claims'")
                )
            ).scalar_one()
            ws_count = (
                await conn.execute(
                    sa.text("SELECT count(*) FROM workspaces WHERE slug = 'ws-vertical-alpha'")
                )
            ).scalar_one()
            llm_count = (
                await conn.execute(
                    sa.text(
                        "SELECT count(*) FROM llm_model_endpoints "
                        "WHERE model_name = 'openai/gpt-4o-vertical'"
                    )
                )
            ).scalar_one()
        assert settings_count == 1
        assert org_count == 1
        assert ws_count == 1
        assert llm_count == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_skill_creation_and_progressive_llm_http_persist_in_pg18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Verify `POST /api/v1/agents-and-skills/skills` & `progressive-llm` persist in PG18."""
    skill_name = "Skill Vertical HTTP PG18"
    engine = create_async_engine(database_url)
    try:
        async with app_client_factory() as client:
            skill_res = await client.post(
                "/api/v1/agents-and-skills/skills?persona_key=marc",
                json={
                    "name": skill_name,
                    "objective": "Outil de vérification SQL verticale.",
                    "instructions": "Exécuter la requête de vérification et synthétiser.",
                    "input_parameters": ["ticket_id"],
                },
            )
            assert skill_res.status_code == 200, skill_res.text

            llm_res = await client.post(
                "/api/v1/bootstrap/welcome-setup/progressive-llm?persona_key=karim",
                json={
                    "endpoint_key": "tier-vertical-fast",
                    "provider_slug": "anthropic",
                    "model_family": "anthropic",
                    "model_name": "claude-3-7-sonnet-vertical",
                    "endpoint_uri": "https://llm.vertical.internal/v1",
                },
            )
            assert llm_res.status_code == 200, llm_res.text

        async with engine.connect() as conn:
            skill_count = (
                await conn.execute(
                    sa.text(
                        "SELECT count(*) FROM catalog_items WHERE catalog_items::text ILIKE :n"
                    ),
                    {"n": f"%{skill_name}%"},
                )
            ).scalar_one()
            ep_count = (
                await conn.execute(
                    sa.text(
                        "SELECT count(*) FROM llm_model_endpoints "
                        "WHERE endpoint_key = 'tier-vertical-fast'"
                    )
                )
            ).scalar_one()
        assert skill_count >= 1
        assert ep_count == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_pack_builder_and_help_hot_attach_http_persist_in_pg18_catalog_and_outbox(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Verify Epics 11.4 & 11.5 HTTP routes persist `BUSINESS_PACK` and `HELP_ARTICLE` in PG18."""
    starlark_rule = (
        "def evaluate(ctx):\n"
        '    data = orcia_sys.input("CheckPayload")\n'
        "    orcia_sys.assert_rule(\n"
        '        rule_id="NORM-VERT-01",\n'
        '        condition=(data.get("ok", False) == True),\n'
        '        message="Champ ok requis.",\n'
        '        evidence_ref="ok"\n'
        "    )\n"
    )
    engine = create_async_engine(database_url)
    try:
        async with app_client_factory() as client:
            pack_res = await client.post(
                "/api/v1/pack-builder/processes/create-pack",
                json={
                    "pack_slug": "vertical-qa",
                    "title": "Pack QA Vertical PG18",
                    "version": "1.0.0",
                    "domain_name": "QA_VERTICAL",
                    "human_anchor_intent": (
                        "Vérifier de bout en bout la persistance PostgreSQL 18 depuis FastAPI."
                    ),
                    "dna_seeds": [
                        {
                            "directive_code": "DIR-VERT-01",
                            "directive_title": "Directive Qualité Verticale",
                            "norm_code": "NORM-VERT-01",
                            "norm_title": "Norme de contrôle obligatoire",
                            "mechanism_code": "MECH-VERT-01",
                            "rule_id": "NORM-VERT-01",
                            "starlark_source": starlark_rule,
                            "passing_test_payload": {"ok": True},
                            "failing_test_payload": {"ok": False},
                        }
                    ],
                    "human_profiles": ["QA Lead"],
                    "agents": ["@Agent-QA"],
                    "workflows": ["qa/verify-vertical"],
                    "actor_role": "ARCHITECT",
                    "actor_id": "karim-qa",
                },
            )
            assert pack_res.status_code == 201, pack_res.text

            help_res = await client.post(
                "/api/v1/pack-builder/processes/generate-and-attach-help",
                json={
                    "article_id": "help.vertical.cockpit",
                    "article_slug": "vertical-cockpit",
                    "version": "1.0.0",
                    "pack_slug": "vertical-qa",
                    "title_fr": "Aide Verticale Cockpit",
                    "title_en": "Vertical Cockpit Help",
                    "bound_routes": ["/cockpit"],
                    "roles_allowed": ["CONTRIBUTOR", "ARCHITECT"],
                    "glossary_terms": ["RunLock"],
                    "related_workflows": ["qa/verify-vertical"],
                    "purpose_fr": "Valider l'attachement à chaud dans PostgreSQL 18.",
                    "purpose_en": "Validate hot attachment in PostgreSQL 18.",
                    "steps_fr": ["Ouvrir le Cockpit", "Vérifier la fiche"],
                    "steps_en": ["Open Cockpit", "Verify card"],
                    "faq_fr": ["Est-ce persisté en base ?"],
                    "faq_en": ["Is it persisted in DB?"],
                    "ui_component_name": "StreamlinedCockpitView",
                    "trigger_regime": "STAGED_HUMAN_REVIEW",
                    "known_glossary_terms": ["RunLock"],
                    "actor_role": "ARCHITECT",
                },
            )
            assert help_res.status_code == 201, help_res.text

            # Also exercise Epics 9, 10 & 11 HTTP routes on the same live app instance
            pref_res = await client.patch(
                "/api/v1/users/me/preferences?persona_key=marc",
                json={"theme": "dark", "locale": "fr"},
            )
            assert pref_res.status_code == 200

            gov_res = await client.put(
                "/api/v1/assistant/governance/mode-a/user?persona_key=marc",
                json={
                    "workspace_id": "ws-vertical-alpha",
                    "response_tone": "SYNTHETIC",
                    "favorite_format": "BULLETS_SUMMARY",
                    "default_hat": "TECH_LEAD",
                    "personal_instructions": "Toujours citer les preuves.",
                },
            )
            assert gov_res.status_code == 200, gov_res.text

            folder_res = await client.post(
                "/api/v1/assistant/folders?persona_key=marc",
                json={
                    "workspace_id": "ws-vertical-alpha",
                    "title": "Dossier Vertical HTTP",
                    "pinned_notes_markdown": "# Notes verticales",
                    "working_attachments_uris": [],
                    "consolidated_summary": "Résumé initial",
                    "evidence_tags": ["S1"],
                    "has_restricted_sources": False,
                },
            )
            assert folder_res.status_code == 200

        async with engine.connect() as conn:
            pack_row = (
                await conn.execute(
                    sa.text(
                        "SELECT item_type, version FROM catalog_items "
                        "WHERE resource_id = 'pack-vertical-qa'"
                    )
                )
            ).first()
            help_count = (
                await conn.execute(
                    sa.text(
                        "SELECT count(*) FROM catalog_items "
                        "WHERE resource_id IN ("
                        "'help.vertical.cockpit-fr', 'help.vertical.cockpit-en'"
                        ") AND item_type = 'HELP_ARTICLE'"
                    )
                )
            ).scalar_one()
            outbox_count = (
                await conn.execute(
                    sa.text(
                        "SELECT count(*) FROM domain_events_outbox "
                        "WHERE aggregate_id = 'orcia://packs/orcia-pack-vertical-qa'"
                    )
                )
            ).scalar_one()
        assert pack_row is not None
        assert pack_row[0] == "BUSINESS_PACK"
        assert pack_row[1] == "1.0.0"
        assert help_count == 2
        assert outbox_count >= 1
    finally:
        await engine.dispose()
