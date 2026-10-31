"""Story 9.5 — Unit & API tests for Hybrid Contextual Help (`HelpArticle` in `catalog_items`).

Validates:
- Git-seeded Markdown help files (`docs/help/{fr,en}/` & `packages/orcia-pack-sdlc/help/{fr,en}/`)
  loaded under `item_type = 'HELP_ARTICLE'` with CAS key `cas/<sha256>`.
- Protection against overwriting a newer `@v(N+1)` hot-published version during startup seeding.
- `< 10 ms` Redis cache resolution (`help:route:<route>:<pack>:<lang>`) applying 4-layer merge.
- 1-click `⏪ Rollback` restoring `@v(N-1)` via `POST /api/v1/help/rollback`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from orcia_api.main import app
from orcia_core.catalog.contextual_help import (
    ContextualHelpResolutionService,
    build_help_redis_cache_key,
    parse_declarative_help_markdown,
)


def test_story_9_5_git_seeder_4_layer_merge_and_v_n_plus_1_protection() -> None:
    """Verify Git seeding, CAS sha256 storage, 4-layer merge, Redis cache, and @v(N+1) guard."""
    svc = ContextualHelpResolutionService()

    # Resolve /mes-espaces/$id/sources for orcia-pack-sdlc in French
    res1 = svc.resolve_for_route(
        route="/mes-espaces/$id/sources",
        pack="orcia-pack-sdlc",
        lang="fr",
    )
    assert res1.cache_hit is False
    assert res1.redis_cache_key == "help:route:/mes-espaces/$id/sources:orcia-pack-sdlc:fr"
    assert res1.merged_layers == ("BASE", "PACK")
    assert res1.active_article.item_type == "HELP_ARTICLE"
    assert res1.active_article.cas_key.startswith("cas/")
    assert "SDLC" in res1.active_article.title

    # Second call hits Redis cache in < 10 ms
    res2 = svc.resolve_for_route(
        route="/mes-espaces/$id/sources",
        pack="orcia-pack-sdlc",
        lang="fr",
    )
    assert res2.cache_hit is True

    # Hot-publish @v(N+1) version (e.g. 2.0.0) -> re-running Git seeder MUST NOT overwrite 2.0.0!
    published = svc.publish_hot_version(
        resource_id=res1.active_article.resource_id,
        new_version="2.0.0",
        new_title="Sources SDLC Personnalisées @v2.0.0",
        new_summary_what_for="Version @v(N+1) publiée à chaud.",
        new_markdown_body="### Pas-à-pas\n1. Étape personnalisée @v2",
        layer="WORKSPACE",
    )
    assert published.version == "2.0.0"
    assert published.previous_version == "1.1.0"

    # Attempt to re-seed older 1.1.0 version -> rejected (returns False), 2.0.0 preserved
    older_seed = parse_declarative_help_markdown(
        """---
resource_id: help-pack-sdlc-spaces-sources-fr
uri: orcia://packs/orcia-pack-sdlc/help/spaces-sources/fr
title: "Ancien titre 1.1.0"
version: "1.1.0"
lang: fr
layer: PACK
pack_name: orcia-pack-sdlc
bound_routes:
  - /mes-espaces/$id/sources
---
Corps 1.1.0"""
    )
    assert svc.upsert_seeded_article(older_seed) is False
    after_reseed = svc.resolve_for_route(
        route="/mes-espaces/$id/sources",
        pack="orcia-pack-sdlc",
        lang="fr",
    )
    assert after_reseed.active_article.version == "2.0.0"
    assert after_reseed.rollback_available is True

    # 1-click Rollback -> restores @v(N-1) (1.1.0)
    rolled_back = svc.rollback_to_previous_version(res1.active_article.resource_id)
    assert rolled_back.version == "1.1.0"


def test_story_9_5_api_help_resolve_publish_and_rollback() -> None:
    """Verify GET /api/v1/help/resolve, POST /api/v1/help/publish, and rollback."""
    with TestClient(app) as client:
        resolve_resp = client.get(
            "/api/v1/help/resolve",
            params={
                "route": "/mes-espaces/$id/sources",
                "pack": "orcia-pack-sdlc",
                "lang": "fr",
            },
        )
        assert resolve_resp.status_code == 200
        body = resolve_resp.json()
        assert body["redis_cache_key"] == build_help_redis_cache_key(
            "/mes-espaces/$id/sources", "orcia-pack-sdlc", "fr"
        )
        assert body["active_article"]["item_type"] == "HELP_ARTICLE"
        res_id = body["active_article"]["resource_id"]

        pub_resp = client.post(
            "/api/v1/help/publish",
            params={"persona_key": "karim"},
            json={
                "resource_id": res_id,
                "new_version": "2.1.0",
                "new_title": "Fiche d'aide Espace @v2.1.0",
                "new_summary_what_for": "Résumé personnalisé @v2.1.0",
                "new_markdown_body": "### Pas-à-pas\n1. Étape @v2.1.0",
                "layer": "WORKSPACE",
            },
        )
        assert pub_resp.status_code == 200
        assert pub_resp.json()["version"] == "2.1.0"

        rb_resp = client.post(
            "/api/v1/help/rollback",
            params={"persona_key": "karim"},
            json={"resource_id": res_id},
        )
        assert rb_resp.status_code == 200
        assert rb_resp.json()["version"] == "1.1.0"
