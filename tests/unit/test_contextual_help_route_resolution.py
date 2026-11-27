"""Unit tests for route-aware contextual help resolution and accostage counts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from orcia_api.routers.bootstrap_accostage import _serialize_accostage_status
from orcia_core.bootstrap._internal.sql_accostage_counts import (
    AccostagePg18Counts,
)
from orcia_core.bootstrap.progressive_accostage import AccostageStatusReport
from orcia_core.catalog.contextual_help import (
    ContextualHelpResolutionService,
    normalize_help_pack,
)
from orcia_core.catalog.contextual_help_loader import (
    dict_to_help_article,
    parse_declarative_help_markdown,
    serialize_redis_help_payload,
)
from orcia_core.catalog.contextual_help_redis import (
    get_cached_help_article_async,
    invalidate_help_redis_keys_async,
    invalidate_help_redis_keys_sync,
    set_cached_help_article_async,
)
from orcia_core.catalog.contextual_help_resolver import resolve_overview_fallback
from orcia_kernel.errors import ResourceNotFoundError

REPO_ROOT = Path(__file__).resolve().parents[2]
HELP_ROOT = REPO_ROOT / "docs" / "help"

CANONICAL_ROUTE_EXPECTATIONS: list[tuple[str, str]] = [
    ("/cockpit", "help-base-cockpit"),
    ("/assistant", "help-base-assistant"),
    ("/processes", "help-base-processes"),
    ("/processes/studio/wf-01", "help-base-processes"),
    ("/agents", "help-base-agents"),
    ("/spaces", "help-base-spaces"),
    ("/workspaces/0195f000-0000-7000-8000-000000000001", "help-base-workspaces"),
    ("/workspaces/0195f000-0000-7000-8000-000000000001/sources", "help-base-workspaces"),
    ("/finops", "help-base-finops"),
    ("/activity", "help-base-activity"),
    ("/settings", "help-base-settings"),
    ("/configuration", "help-base-settings"),
    ("/organization", "help-base-organization"),
    ("/profile", "help-base-profile"),
    ("/ontology", "help-base-ontology"),
    ("/gates", "help-base-gates"),
    ("/catalog", "help-base-catalog"),
    ("/wizards", "help-base-wizards"),
    ("/help", "help-base-help"),
    ("/showcase", "help-base-showcase"),
]


@pytest.mark.parametrize("lang", ["fr", "en"])
@pytest.mark.parametrize(("route", "expected_prefix"), CANONICAL_ROUTE_EXPECTATIONS)
def test_canonical_route_resolves_to_dedicated_help_article(
    route: str,
    expected_prefix: str,
    lang: str,
) -> None:
    """Every canonical route resolves to its own docs/help/{fr,en} sheet, never spaces-sources."""
    svc = ContextualHelpResolutionService(repo_root=REPO_ROOT)
    result = svc.resolve_for_route(route=route, pack="core", lang=lang)  # type: ignore[arg-type]

    assert result.active_article.resource_id == f"{expected_prefix}-{lang}"
    assert result.active_article.lang == lang
    assert result.active_article.resource_id != f"help-base-spaces-sources-{lang}"
    assert result.active_article.summary_what_for.strip() != ""
    assert len(result.active_article.step_by_step_items) >= 1
    assert (result.active_article.real_example_text or "").strip() != ""
    assert len(result.active_article.common_pitfalls_items) >= 1
    assert result.active_article.key_terms_items == ()
    assert result.active_article.faq_items == ()


def test_unknown_route_falls_back_to_overview_never_spaces_sources() -> None:
    """Unmapped routes fall back explicitly to the help overview rather than spaces-sources."""
    svc = ContextualHelpResolutionService(repo_root=REPO_ROOT)
    res_fr = svc.resolve_for_route(route="/route-inconnue-demo", pack="core", lang="fr")
    res_en = svc.resolve_for_route(route="/unknown-demo-route", pack="core", lang="en")

    assert res_fr.active_article.resource_id == "help-base-help-fr"
    assert res_en.active_article.resource_id == "help-base-help-en"
    assert "spaces-sources" not in res_fr.active_article.resource_id
    assert "spaces-sources" not in res_en.active_article.resource_id


def test_all_help_markdown_files_contain_four_sections_and_zero_forbidden_placeholders() -> None:
    """All docs/help/{fr,en}/*.md files must parse cleanly with 4 sections and zero Chef1/aqwZSX."""
    md_files = sorted(HELP_ROOT.glob("*/*.md"))
    assert len(md_files) >= 34

    for md_path in md_files:
        raw = md_path.read_text(encoding="utf-8")
        assert "Chef1" not in raw, f"Forbidden placeholder Chef1 found in {md_path}"
        assert "aqwZSX" not in raw, f"Forbidden placeholder aqwZSX found in {md_path}"

        parsed = parse_declarative_help_markdown(raw)
        assert parsed.summary_what_for.strip() != "", f"Missing what-for summary in {md_path}"
        assert len(parsed.step_by_step_items) >= 1, f"Missing steps section in {md_path}"
        assert (parsed.real_example_text or "").strip() != "", (
            f"Missing real example section in {md_path}"
        )
        assert len(parsed.common_pitfalls_items) >= 1, (
            f"Missing common pitfalls section in {md_path}"
        )
        assert parsed.key_terms_items == (), (
            f"Real example leaked into key_terms_items in {md_path}"
        )
        assert parsed.faq_items == (), f"Common pitfalls leaked into faq_items in {md_path}"


def test_serialize_accostage_status_reflects_pg18_counts() -> None:
    """Accostage serialization surfaces PG18 admin_created, org_units_count, and workspaces."""
    report = AccostageStatusReport(
        completed_count=1,
        total_count=6,
        badge_label="Accostage 1/6",
        llm_tier_mode="UNCONFIGURED",
        distinct_families=(),
        assistant_trial_enabled=False,
        agentic_gates_ad10_enabled=False,
        amber_warning_badge=None,
        completed_milestone_keys=("first-admin",),
        first_admin_initialized=True,
        first_admin_email="admin@orcia.test",
        first_admin_display_name="Claire Admin",
    )
    counts = AccostagePg18Counts(
        users_count=1,
        org_units_count=0,
        workspaces_count=2,
        models_count=1,
        sources_count=3,
        workflows_count=2,
    )

    serialized = _serialize_accostage_status(
        report,
        trace_id="0195f000000070008000000000002206",
        boot_epoch="boot-epoch-1",
        counts=counts,
    )
    assert serialized.admin_created is True
    assert serialized.users_count == 1
    assert serialized.org_units_count == 0
    assert serialized.workspaces_count == 2
    assert serialized.models_count == 1
    assert serialized.sources_count == 3
    assert serialized.workflows_count == 2
    assert serialized.boot_epoch == "boot-epoch-1"


def test_help_pack_normalization_and_overview_fallback_edge_cases() -> None:
    """Verify legacy pack normalization, fallback without fixed IDs, and error paths."""
    assert normalize_help_pack("") == "core"
    assert normalize_help_pack("orcia-core") == "core"
    assert normalize_help_pack("orcia-pack-sdlc") == "orcia-pack-sdlc"

    sample_cockpit = parse_declarative_help_markdown(
        "---\n"
        "id: custom-cockpit\n"
        "title: Cockpit Custom\n"
        "lang: fr\n"
        "bound_routes:\n"
        "  - /cockpit\n"
        "---\n"
        "## À quoi sert cet écran\n"
        "Synthèse.\n"
        "## En 3 gestes\n"
        "- Ouvrir.\n"
        "## Un exemple réel\n"
        "- Exemple.\n"
        "## Ce qui coince souvent\n"
        "- Rien.\n"
    )
    fallback_art = resolve_overview_fallback(
        {"help-base-custom-cockpit-fr": sample_cockpit},
        route="/unmapped",
        lang="fr",
    )
    assert fallback_art.resource_id == "help-base-custom-cockpit-fr"

    with pytest.raises(ResourceNotFoundError):
        resolve_overview_fallback({}, route="/unmapped", lang="fr")

    svc = ContextualHelpResolutionService(repo_root=REPO_ROOT)
    with pytest.raises(ResourceNotFoundError):
        svc.publish_hot_version(
            resource_id="help-missing",
            new_version="2.0.0",
            new_title="Missing",
            new_summary_what_for="Missing",
            new_markdown_body="# Missing",
        )
    with pytest.raises(ResourceNotFoundError):
        svc.rollback_to_previous_version("help-base-finops-fr")


@pytest.mark.asyncio
async def test_help_redis_helpers_tolerate_transient_cache_errors() -> None:
    """Redis cache helpers swallow transient client failures without crashing help resolution."""

    class _FailingSyncRedis:
        def delete(self, *_keys: str) -> None:
            raise RuntimeError("redis down")

    class _FailingAsyncRedis:
        async def get(self, _key: str) -> None:
            raise RuntimeError("redis get down")

        async def setex(self, _key: str, _ttl: int, _val: str) -> None:
            raise RuntimeError("redis setex down")

        async def delete(self, *_keys: str) -> None:
            raise RuntimeError("redis del down")

    sample = parse_declarative_help_markdown(
        "---\n"
        "id: redis-resilience\n"
        "title: Redis Test\n"
        "lang: fr\n"
        "bound_routes:\n"
        "  - /finops\n"
        "---\n"
        "## À quoi sert cet écran\n"
        "Test.\n"
        "## En 3 gestes\n"
        "- Etape.\n"
        "## Un exemple réel\n"
        "- Exemple.\n"
        "## Ce qui coince souvent\n"
        "- Rien.\n"
    )
    invalidate_help_redis_keys_sync(_FailingSyncRedis(), sample)
    await invalidate_help_redis_keys_async(_FailingAsyncRedis(), sample)
    await set_cached_help_article_async(_FailingAsyncRedis(), "k", sample, ("BASE",))
    assert await get_cached_help_article_async(_FailingAsyncRedis(), "k") is None


def test_parse_declarative_help_markdown_separates_dedicated_4_blocks_and_terms_faq() -> None:
    """`parse_declarative_help_markdown` maps dedicated 4-block headings cleanly."""
    md_fr = (
        "---\n"
        "id: demo-fr\n"
        "title: Guide Démo\n"
        "lang: fr\n"
        "bound_routes:\n"
        "  - /assistant\n"
        "---\n"
        "## À quoi sert cet écran\n"
        "Aide à piloter les échanges.\n"
        "## En 3 gestes\n"
        "1. Choisir un espace.\n"
        "2. Poser une question.\n"
        "3. Vérifier les citations.\n"
        "## Un exemple réel\n"
        "- Nadia pose une question sur la conformité.\n"
        "## Ce qui coince souvent\n"
        "- Champ bloqué sans modèle configuré.\n"
        "## Termes clés\n"
        "- Citation vérifiée\n"
        "## Questions fréquentes\n"
        "- Pourquoi les notes ?\n"
    )
    parsed_fr = parse_declarative_help_markdown(md_fr)
    assert parsed_fr.summary_what_for == "Aide à piloter les échanges."
    assert parsed_fr.step_by_step_items == (
        "Choisir un espace.",
        "Poser une question.",
        "Vérifier les citations.",
    )
    assert parsed_fr.real_example_text == "Nadia pose une question sur la conformité."
    assert parsed_fr.common_pitfalls_items == ("Champ bloqué sans modèle configuré.",)
    assert parsed_fr.key_terms_items == ("Citation vérifiée",)
    assert parsed_fr.faq_items == ("Pourquoi les notes ?",)

    md_en = (
        "---\n"
        "id: demo-en\n"
        "title: Demo Guide\n"
        "lang: en\n"
        "bound_routes:\n"
        "  - /assistant\n"
        "---\n"
        "## What this screen is for\n"
        "Guides conversations.\n"
        "## In 3 steps\n"
        "1. Pick a space.\n"
        "2. Ask a question.\n"
        "3. Inspect citations.\n"
        "## A real example\n"
        "Marc checks compliance risks.\n"
        "## Common pitfalls\n"
        "- Prompt input is locked without models.\n"
    )
    parsed_en = parse_declarative_help_markdown(md_en)
    assert parsed_en.summary_what_for == "Guides conversations."
    assert parsed_en.real_example_text == "Marc checks compliance risks."
    assert parsed_en.common_pitfalls_items == ("Prompt input is locked without models.",)
    assert parsed_en.key_terms_items == ()
    assert parsed_en.faq_items == ()


def test_dict_to_help_article_backfills_legacy_records_without_dedicated_keys() -> None:
    """`dict_to_help_article` backfills dedicated 4-block fields for pre-23.3 rows."""
    legacy_payload: dict[str, Any] = {
        "resource_id": "help-base-assistant-fr",
        "uri": "orcia://system/help/assistant/fr",
        "title": "Mon Assistant",
        "version": "1.0.0",
        "lang": "fr",
        "layer": "BASE",
        "pack_name": None,
        "bound_routes": ["/assistant"],
        "summary_what_for": "Résumé.",
        "step_by_step_items": ["Étape 1"],
        "key_terms_items": [],
        "faq_items": [],
        "cas_key": "cas/abc",
        "sha256": "abc",
        "markdown_body": (
            "## À quoi sert cet écran\nRésumé.\n"
            "## En 2 gestes\n1. Étape 1\n"
            "## Un exemple réel\nMarc vérifie la conformité.\n"
            "## Ce qui coince souvent\n- Modèle absent.\n"
        ),
    }
    hydrated = dict_to_help_article(legacy_payload)
    assert hydrated.real_example_text == "Marc vérifie la conformité."
    assert hydrated.common_pitfalls_items == ("Modèle absent.",)

    explicit_payload = {
        **legacy_payload,
        "real_example_text": "Exemple explicite.",
        "common_pitfalls_items": ["Piège explicite."],
    }
    explicit = dict_to_help_article(explicit_payload)
    assert explicit.real_example_text == "Exemple explicite."
    assert explicit.common_pitfalls_items == ("Piège explicite.",)

    redis_json = serialize_redis_help_payload(explicit, ("BASE",))
    assert '"real_example_text": "Exemple explicite."' in redis_json
    assert '"common_pitfalls_items": ["Piège explicite."]' in redis_json


def test_assistant_help_markdown_matches_selector_terminology_without_cockpit_bleed() -> None:
    """`docs/help/{fr,en}/assistant.md` align with Standard/Approfondi without Cockpit text."""
    fr_raw = (HELP_ROOT / "fr" / "assistant.md").read_text(encoding="utf-8")
    en_raw = (HELP_ROOT / "en" / "assistant.md").read_text(encoding="utf-8")

    assert "Polyvalent · Standard" in fr_raw
    assert "Approfondi" in fr_raw
    for legacy_fr in (
        "Réponse rapide",
        "Avec un agent",
        "Analyse approfondie",
        "Le Cockpit regroupe",
    ):
        assert legacy_fr not in fr_raw

    assert "Versatile · Standard" in en_raw
    assert "In-Depth" in en_raw
    for legacy_en in (
        "Quick reply",
        "With an agent",
        "Deep analysis",
        "The Cockpit brings together",
    ):
        assert legacy_en not in en_raw


def test_row_to_help_dict_hydrates_dedicated_4_blocks() -> None:
    """`row_to_help_dict` hydrates 4-block fields and handles legacy fallback."""
    from orcia_core.catalog._internal.sql_contextual_help import row_to_help_dict

    article = parse_declarative_help_markdown(
        (HELP_ROOT / "fr" / "assistant.md").read_text(encoding="utf-8")
    )
    stored_meta = {
        "lang": article.lang,
        "pack_name": article.pack_name,
        "bound_routes": list(article.bound_routes),
        "summary_what_for": article.summary_what_for,
        "step_by_step_items": list(article.step_by_step_items),
        "real_example_text": article.real_example_text,
        "common_pitfalls_items": list(article.common_pitfalls_items),
        "key_terms_items": list(article.key_terms_items),
        "faq_items": list(article.faq_items),
        "markdown_body": article.markdown_body,
    }
    row_dict = row_to_help_dict(
        {
            "resource_id": article.resource_id,
            "uri": article.uri,
            "title": article.title,
            "description": article.summary_what_for,
            "version": article.version,
            "sha256": article.sha256,
            "cas_key": article.cas_key,
            "metadata_jsonb": stored_meta,
        }
    )
    assert row_dict["real_example_text"] == article.real_example_text
    assert row_dict["common_pitfalls_items"] == article.common_pitfalls_items

    legacy_row_dict = row_to_help_dict(
        {
            "resource_id": article.resource_id,
            "uri": article.uri,
            "title": article.title,
            "description": article.summary_what_for,
            "version": article.version,
            "sha256": article.sha256,
            "cas_key": article.cas_key,
            "metadata_jsonb": {
                "lang": "fr",
                "layer": "BASE",
                "bound_routes": ["/assistant"],
                "markdown_body": article.markdown_body,
            },
        }
    )
    assert "real_example_text" not in legacy_row_dict
    assert "common_pitfalls_items" not in legacy_row_dict
    rehydrated_legacy = dict_to_help_article(legacy_row_dict)
    assert rehydrated_legacy.real_example_text == article.real_example_text
    assert rehydrated_legacy.common_pitfalls_items == article.common_pitfalls_items


@pytest.mark.asyncio
async def test_contextual_help_service_hot_publish_rollback_and_async_memory_paths() -> None:
    """Verify hot publish, rollback, version guard, and async fallback paths on help service."""
    svc = ContextualHelpResolutionService(repo_root=REPO_ROOT)

    assert await svc.ensure_seeded_in_postgres18_async() == 0

    first = await svc.resolve_for_route_async(route="/assistant", pack="core", lang="fr")
    assert first.cache_hit is False
    assert (first.active_article.real_example_text or "").strip() != ""
    assert len(first.active_article.common_pitfalls_items) >= 1

    # Second sync resolve hits in-memory cache
    cached = svc.resolve_for_route(route="/assistant", pack="core", lang="fr")
    assert cached.cache_hit is True

    # Hot publish @v(N+1) preserves 4 blocks & prevents older Git seed from overwriting
    updated = await svc.publish_hot_version_async(
        resource_id="help-base-assistant-fr",
        new_version="1.2.0",
        new_title="Mon Assistant v1.2",
        new_summary_what_for="Résumé v1.2.",
        new_markdown_body=(
            "## À quoi sert cet écran\nRésumé v1.2.\n"
            "## En 2 gestes\n1. Choisir.\n2. Envoyer.\n"
            "## Un exemple réel\nExemple v1.2.\n"
            "## Ce qui coince souvent\n- Piège v1.2.\n"
        ),
        layer="WORKSPACE",
        is_autonomous_generated=True,
        autonomous_run_id="run-123",
    )
    assert updated.version == "1.2.0"
    assert updated.real_example_text == "Exemple v1.2."
    assert updated.common_pitfalls_items == ("Piège v1.2.",)

    older_seed = parse_declarative_help_markdown(
        (HELP_ROOT / "fr" / "assistant.md").read_text(encoding="utf-8")
    )
    assert svc.upsert_seeded_article(older_seed) is False

    restored = await svc.rollback_to_previous_version_async("help-base-assistant-fr")
    assert restored.version == "1.0.0"
    assert "Marc sélectionne" in (restored.real_example_text or "")


def test_default_help_pack_is_core_and_sdlc_pack_does_not_override_spaces_root() -> None:
    """Default pack is `core` in API/core and `packs/sdlc` only binds `/spaces/.../sources`."""
    import inspect

    from orcia_api.routers.portal_and_help import resolve_contextual_help

    sig_sync = inspect.signature(ContextualHelpResolutionService.resolve_for_route)
    sig_async = inspect.signature(ContextualHelpResolutionService.resolve_for_route_async)
    sig_api = inspect.signature(resolve_contextual_help)
    assert sig_sync.parameters["pack"].default == "core"
    assert sig_async.parameters["pack"].default == "core"
    assert sig_api.parameters["pack"].default.default == "core"

    for lang in ("fr", "en"):
        sdlc_md = (REPO_ROOT / "packs" / "sdlc" / "help" / lang / "spaces-sources.md").read_text(
            encoding="utf-8"
        )
        parsed = parse_declarative_help_markdown(sdlc_md)
        assert "/spaces" not in parsed.bound_routes

        svc = ContextualHelpResolutionService(repo_root=REPO_ROOT)
        spaces_res = svc.resolve_for_route(route="/spaces", lang=lang)  # type: ignore[arg-type]
        assert spaces_res.pack == "core"
        assert spaces_res.active_article.resource_id == f"help-base-spaces-{lang}"
