"""Unit tests for route-aware contextual help resolution and accostage counts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from orcia_api.routers.bootstrap_accostage import _serialize_accostage_status
from orcia_core.bootstrap._internal.sql_accostage_counts import (
    AccostagePg18Counts,
    get_accostage_pg18_counts,
)
from orcia_core.bootstrap.progressive_accostage import AccostageStatusReport
from orcia_core.catalog.contextual_help import (
    ContextualHelpResolutionService,
    normalize_help_pack,
)
from orcia_core.catalog.contextual_help_loader import parse_declarative_help_markdown
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
    assert len(result.active_article.key_terms_items) >= 1
    assert len(result.active_article.faq_items) >= 1


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
        assert len(parsed.key_terms_items) >= 1, f"Missing example/terms section in {md_path}"
        assert len(parsed.faq_items) >= 1, f"Missing pitfalls/FAQ section in {md_path}"


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
    assert serialized.boot_epoch == "boot-epoch-1"


@pytest.mark.asyncio
async def test_get_accostage_pg18_counts_maps_sql_row_and_empty_result() -> None:
    """`get_accostage_pg18_counts` accurately converts SQL count rows and handles None rows."""

    class _FakeResult:
        def __init__(self, row: tuple[int, int, int, int, int] | None) -> None:
            self._row = row

        def first(self) -> tuple[int, int, int, int, int] | None:
            return self._row

    class _FakeConn:
        def __init__(self, row: tuple[int, int, int, int, int] | None) -> None:
            self._row = row

        async def execute(self, _stmt: Any) -> _FakeResult:
            return _FakeResult(self._row)

    class _FakeConnectCtx:
        def __init__(self, row: tuple[int, int, int, int, int] | None) -> None:
            self._row = row

        async def __aenter__(self) -> _FakeConn:
            return _FakeConn(self._row)

        async def __aexit__(self, *_args: object) -> None:
            return None

    class _FakeEngine:
        def __init__(self, row: tuple[int, int, int, int, int] | None) -> None:
            self._row = row

        def connect(self) -> _FakeConnectCtx:
            return _FakeConnectCtx(self._row)

    populated = await get_accostage_pg18_counts(_FakeEngine((2, 3, 4, 1, 5)))  # type: ignore[arg-type]
    assert populated.admin_created is True
    assert populated.users_count == 2
    assert populated.org_units_count == 3
    assert populated.workspaces_count == 4
    assert populated.models_count == 1
    assert populated.sources_count == 5

    empty = await get_accostage_pg18_counts(_FakeEngine(None))  # type: ignore[arg-type]
    assert empty.admin_created is False
    assert empty.users_count == 0
    assert empty.org_units_count == 0


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


@pytest.mark.asyncio
async def test_sql_contextual_help_not_found_and_missing_table_branches() -> None:
    """Verify SQL contextual help handles empty rows, missing history, and missing tables."""
    from orcia_core.catalog._internal.sql_contextual_help import (
        list_pg_help_articles_sql,
        publish_hot_help_article_sql,
        rollback_help_article_sql,
        seed_help_articles_to_pg18_sql,
    )

    class _UndefinedTableError(Exception):
        pass

    class _EmptyMappingsResult:
        def mappings(self) -> _EmptyMappingsResult:
            return self

        def first(self) -> None:
            return None

        def all(self) -> list[Any]:
            return []

    class _RowMappingsResult:
        def __init__(self, row: dict[str, Any]) -> None:
            self._row = row

        def mappings(self) -> _RowMappingsResult:
            return self

        def first(self) -> dict[str, Any]:
            return self._row

    class _SqlEngineStub:
        def __init__(self, *, mode: str) -> None:
            self._mode = mode

        def connect(self) -> _SqlConnCtx:
            return _SqlConnCtx(self._mode)

        def begin(self) -> _SqlConnCtx:
            return _SqlConnCtx(self._mode)

    class _SqlConnCtx:
        def __init__(self, mode: str) -> None:
            self._mode = mode

        async def __aenter__(self) -> _SqlConn:
            return _SqlConn(self._mode)

        async def __aexit__(self, *_args: object) -> None:
            return None

    class _SqlConn:
        def __init__(self, mode: str) -> None:
            self._mode = mode

        async def execute(self, _stmt: Any, _params: Any = None) -> Any:
            if self._mode == "missing_table":
                raise _UndefinedTableError('relation "catalog_items" does not exist')
            if self._mode == "no_prev_version":
                return _RowMappingsResult(
                    {
                        "resource_id": "help-x",
                        "uri": "orcia://system/help/x",
                        "title": "X",
                        "description": "",
                        "version": "1.0.0",
                        "sha256": "a" * 64,
                        "cas_key": "cas/x",
                        "metadata_jsonb": {},
                    }
                )
            return _EmptyMappingsResult()

    empty_engine: Any = _SqlEngineStub(mode="empty")
    missing_engine: Any = _SqlEngineStub(mode="missing_table")
    no_prev_engine: Any = _SqlEngineStub(mode="no_prev_version")

    assert (
        await publish_hot_help_article_sql(
            empty_engine,
            resource_id="help-none",
            new_version="1.1.0",
            new_title="T",
            new_summary_what_for="S",
            new_markdown_body="# B",
        )
        is None
    )
    assert await rollback_help_article_sql(empty_engine, resource_id="help-none") is None
    with pytest.raises(ResourceNotFoundError):
        await rollback_help_article_sql(no_prev_engine, resource_id="help-x")

    assert await list_pg_help_articles_sql(missing_engine, lang="fr") == []
    assert (
        await publish_hot_help_article_sql(
            missing_engine,
            resource_id="help-x",
            new_version="1.1.0",
            new_title="T",
            new_summary_what_for="S",
            new_markdown_body="# B",
        )
        is None
    )
    assert await rollback_help_article_sql(missing_engine, resource_id="help-x") is None
    assert await seed_help_articles_to_pg18_sql(missing_engine, []) == 0
    sample = parse_declarative_help_markdown(
        "---\nid: s\ntitle: S\nlang: fr\nbound_routes:\n  - /cockpit\n---\n"
        "## À quoi sert cet écran\nS.\n## En 3 gestes\n- A.\n"
        "## Un exemple réel\n- B.\n## Ce qui coince souvent\n- C.\n"
    )
    assert await seed_help_articles_to_pg18_sql(missing_engine, [sample]) == 0
