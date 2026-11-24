"""Helper assertions for PG18 accostage progression and contextual help integration tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_kernel.ids import new_uuid7_str


async def verify_accostage_progression_and_llm_hydration(
    engine: AsyncEngine,
    create_app_fn: Callable[[], Any],
    auth_headers: dict[str, str],
) -> None:
    """Verify 3/6 -> 4/6 -> 5/6 -> 6/6 progression and cold LLM tier hydration in PG18."""
    async with engine.connect() as conn:
        ws_id_row = (
            await conn.execute(
                sa.text("SELECT id FROM workspaces WHERE slug = 'espace-socle' LIMIT 1")
            )
        ).first()
    assert ws_id_row is not None
    ws_uuid = ws_id_row[0]

    active_mapping_id = new_uuid7_str()
    inactive_mapping_id = new_uuid7_str()
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                """
                INSERT INTO workspace_llm_tier_mappings (
                    id, scope_level, scope_id, inference_tier, effort,
                    provider_slug, model_family, model_name, fallback_model_name,
                    endpoint_uri, auth_mode, encrypted_api_key, fallback_order, is_active
                )
                VALUES
                    (
                        CAST(:active_id AS uuid), 'GLOBAL', CAST(:scope_id AS uuid),
                        'complex', 'deep', 'anthropic', 'anthropic-claude',
                        'claude-3-7-sonnet', 'claude-3-5-haiku',
                        'https://api.anthropic.com', 'api_key', 'enc-test-key', 1, TRUE
                    ),
                    (
                        CAST(:inactive_id AS uuid), 'GLOBAL', CAST(:scope_id AS uuid),
                        'simple', 'fast', 'openai', 'openai-gpt',
                        'gpt-4o-mini', NULL,
                        'https://api.openai.com/v1', 'api_key', NULL, 1, FALSE
                    )
                """
            ),
            {
                "active_id": active_mapping_id,
                "inactive_id": inactive_mapping_id,
                "scope_id": str(ws_uuid),
            },
        )

    app_cold_4 = create_app_fn()
    assert app_cold_4.dependency_overrides == {}
    async with (
        app_cold_4.router.lifespan_context(app_cold_4),
        AsyncClient(
            transport=ASGITransport(app=app_cold_4), base_url="http://test"
        ) as cold_client_4,
    ):
        r_acc4 = await cold_client_4.get("/api/v1/bootstrap/accostage-status")
        assert r_acc4.status_code == 200, r_acc4.text
        acc4_json = r_acc4.json()
        assert acc4_json["completed_count"] == 4
        assert acc4_json["total_count"] == 6
        assert acc4_json["badge_label"] == "Accostage 4/6"
        assert acc4_json["models_count"] == 1
        assert "first-llm-model" in acc4_json["completed_milestone_keys"]

        # `platform_settings` is empty: `llm_tiers` must hydrate from active mappings only
        r_setup = await cold_client_4.get(
            "/api/v1/bootstrap/platform-setup-state",
            headers=auth_headers,
        )
        assert r_setup.status_code == 200, r_setup.text
        setup_json = r_setup.json()
        assert len(setup_json["llm_tiers"]) == 1
        assert setup_json["llm_tiers"][0]["tier"] == "complex"
        assert setup_json["llm_tiers"][0]["primaryModel"] == "claude-3-7-sonnet"
        assert setup_json["llm_tiers"][0]["apiKeyConfigured"] is True

    # 5/6: Insert workspace_datasource -> cold create_app() reports 5/6
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                """
                INSERT INTO workspace_datasources (
                    id, workspace_id, alias, scheme, uri, role
                )
                VALUES (
                    CAST(:id AS uuid), CAST(:ws_id AS uuid),
                    'git-core', 'git', 'https://git.example.test/core.git', 'code_repo'
                )
                """
            ),
            {"id": new_uuid7_str(), "ws_id": str(ws_uuid)},
        )

    app_cold_5 = create_app_fn()
    assert app_cold_5.dependency_overrides == {}
    async with (
        app_cold_5.router.lifespan_context(app_cold_5),
        AsyncClient(
            transport=ASGITransport(app=app_cold_5), base_url="http://test"
        ) as cold_client_5,
    ):
        r_acc5 = await cold_client_5.get("/api/v1/bootstrap/accostage-status")
        assert r_acc5.status_code == 200, r_acc5.text
        acc5_json = r_acc5.json()
        assert acc5_json["completed_count"] == 5
        assert acc5_json["badge_label"] == "Accostage 5/6"
        assert acc5_json["sources_count"] == 1
        assert "first-datasource" in acc5_json["completed_milestone_keys"]

    # 6/6: Insert workflow_definitions_v2 -> cold create_app() reports 6/6
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                """
                INSERT INTO workflow_definitions_v2 (
                    id, workflow_id, slug, version, status, pack_id
                )
                VALUES (
                    CAST(:id AS uuid), 'wf-pilot-23-4', 'wf-pilot-23-4',
                    '1.0.0', 'published', 'orcia-pack-core'
                )
                """
            ),
            {"id": new_uuid7_str()},
        )

    app_cold_6 = create_app_fn()
    assert app_cold_6.dependency_overrides == {}
    async with (
        app_cold_6.router.lifespan_context(app_cold_6),
        AsyncClient(
            transport=ASGITransport(app=app_cold_6), base_url="http://test"
        ) as cold_client_6,
    ):
        r_acc6 = await cold_client_6.get("/api/v1/bootstrap/accostage-status")
        assert r_acc6.status_code == 200, r_acc6.text
        acc6_json = r_acc6.json()
        assert acc6_json["completed_count"] == 6
        assert acc6_json["total_count"] == 6
        assert acc6_json["badge_label"] == "Accostage 6/6"
        assert acc6_json["workflows_count"] == 1
        assert acc6_json["completed_milestone_keys"] == [
            "first-admin",
            "first-llm-model",
            "first-org-unit",
            "first-space",
            "first-datasource",
            "pilot-workflow-run",
        ]


async def verify_contextual_help_resolution_and_cache(
    client: AsyncClient,
    engine: AsyncEngine,
    auth_headers: dict[str, str],
) -> None:
    """Verify lazy-seeded contextual help resolution, Redis cache hit, publish, and rollback."""
    resolved_by_route: dict[str, tuple[str, str]] = {}
    resolved_articles_by_route: dict[str, dict[str, object]] = {}
    for route, expected_resource_id in [
        ("/finops", "help-base-finops-fr"),
        ("/assistant", "help-base-assistant-fr"),
        ("/cockpit", "help-base-cockpit-fr"),
        ("/profile", "help-base-profile-fr"),
    ]:
        r_help = await client.get(
            "/api/v1/help/resolve",
            params={"route": route, "lang": "fr", "pack": "core"},
        )
        assert r_help.status_code == 200, r_help.text
        article = r_help.json()["active_article"]
        assert article["resource_id"] == expected_resource_id
        assert article["resource_id"] != "help-base-spaces-sources-fr"
        assert str(article.get("summary_what_for") or "").strip() != ""
        assert len(article.get("step_by_step_items") or []) >= 1
        assert str(article.get("real_example_text") or "").strip() != ""
        assert len(article.get("common_pitfalls_items") or []) >= 1
        resolved_by_route[expected_resource_id] = (
            str(article["resource_id"]),
            str(article["title"]),
        )
        resolved_articles_by_route[route] = article

    # Story 23.3: /assistant and /cockpit return strictly distinct 4-block narratives
    assistant_art = resolved_articles_by_route["/assistant"]
    cockpit_art = resolved_articles_by_route["/cockpit"]
    assert assistant_art["title"] != cockpit_art["title"]
    assert assistant_art["summary_what_for"] != cockpit_art["summary_what_for"]
    assert assistant_art["real_example_text"] != cockpit_art["real_example_text"]
    assert "Le Cockpit regroupe" not in str(assistant_art["summary_what_for"])

    # Verify every resolved article exists verbatim in PG18 `catalog_items`
    async with engine.connect() as conn:
        help_rows = (
            (
                await conn.execute(
                    sa.text(
                        "SELECT resource_id, title, metadata_jsonb FROM catalog_items "
                        "WHERE item_type = 'HELP_ARTICLE'"
                    )
                )
            )
            .mappings()
            .all()
        )
    help_rows_by_id = {str(row["resource_id"]): row for row in help_rows}
    for resource_id, (_, api_title) in resolved_by_route.items():
        assert resource_id in help_rows_by_id
        row = help_rows_by_id[resource_id]
        assert api_title == str(row["title"])
        meta = dict(row["metadata_jsonb"] or {})
        assert str(meta.get("real_example_text") or "").strip() != ""
        assert len(meta.get("common_pitfalls_items") or []) >= 1

    # Verify Redis cache hit on second GET, then hot publish + rollback in PG18
    r_help_cached = await client.get(
        "/api/v1/help/resolve",
        params={"route": "/finops", "lang": "fr", "pack": "core"},
    )
    assert r_help_cached.status_code == 200, r_help_cached.text
    assert r_help_cached.json()["cache_hit"] is True

    r_pub = await client.post(
        "/api/v1/help/publish",
        headers=auth_headers,
        json={
            "resource_id": "help-base-finops-fr",
            "new_version": "1.1.0",
            "new_title": "FinOps : budgets et alertes v1.1",
            "new_summary_what_for": "Résumé mis à jour en PG18.",
            "new_markdown_body": "# FinOps v1.1\n\nContenu mis à jour.",
            "layer": "WORKSPACE",
        },
    )
    assert r_pub.status_code == 200, r_pub.text
    assert r_pub.json()["version"] == "1.1.0"

    r_after_pub = await client.get(
        "/api/v1/help/resolve",
        params={"route": "/finops", "lang": "fr", "pack": "core"},
    )
    assert r_after_pub.status_code == 200
    assert r_after_pub.json()["active_article"]["version"] == "1.1.0"
    assert r_after_pub.json()["rollback_available"] is True

    r_rb = await client.post(
        "/api/v1/help/rollback",
        headers=auth_headers,
        json={"resource_id": "help-base-finops-fr"},
    )
    assert r_rb.status_code == 200, r_rb.text
    assert r_rb.json()["version"] == "1.0.0"
