"""Pure route matching and 4-layer merge functions for contextual help resolution."""

from __future__ import annotations

from orcia_core.catalog.contextual_help_models import (
    LAYER_PRECEDENCE,
    HelpArticleCatalogItem,
    HelpArticleLayer,
    HelpLanguageCode,
    normalize_help_pack,
    normalize_help_route,
)
from orcia_kernel.errors import ResourceNotFoundError


def collect_matching_articles(
    *,
    route: str,
    pack: str,
    lang: HelpLanguageCode,
    articles: dict[str, HelpArticleCatalogItem],
) -> list[HelpArticleCatalogItem]:
    """Collect matching help articles ordered by 4-layer precedence (`AD-14`)."""
    norm_pack = normalize_help_pack(pack)
    _, candidate_routes = normalize_help_route(route)
    matched: list[HelpArticleCatalogItem] = []
    for candidate in candidate_routes:
        for art in articles.values():
            if art.lang != lang:
                continue
            art_pack = normalize_help_pack(art.pack_name) if art.pack_name else None
            if art.layer == "PACK" and art_pack not in (None, norm_pack):
                continue
            if candidate in art.bound_routes:
                matched.append(art)
        if matched:
            break
    matched.sort(key=lambda item: LAYER_PRECEDENCE.get(item.layer, 1))
    return matched


def resolve_overview_fallback(
    pool: dict[str, HelpArticleCatalogItem],
    *,
    route: str,
    lang: HelpLanguageCode,
) -> HelpArticleCatalogItem:
    """Resolve explicit overview help (`/help` or `/cockpit`) when no route matches."""
    for preferred_id in (f"help-base-help-{lang}", f"help-base-cockpit-{lang}"):
        if preferred_id in pool:
            return pool[preferred_id]
    for art in pool.values():
        if art.lang == lang and ("/help" in art.bound_routes or "/cockpit" in art.bound_routes):
            return art
    raise ResourceNotFoundError(
        detail_override=f"Aucune fiche d'aide trouvée pour route={route} ({lang})."
    )


def merge_matched_layers(
    matching: list[HelpArticleCatalogItem],
) -> tuple[HelpArticleCatalogItem, tuple[HelpArticleLayer, ...]]:
    """Merge matched layers keeping highest-precedence metadata and deduplicated lists."""
    winner = matching[-1]
    merged = HelpArticleCatalogItem(
        resource_id=winner.resource_id,
        uri=winner.uri,
        title=winner.title,
        version=winner.version,
        lang=winner.lang,
        layer=winner.layer,
        pack_name=winner.pack_name,
        bound_routes=winner.bound_routes,
        summary_what_for=winner.summary_what_for,
        step_by_step_items=tuple(dict.fromkeys(s for a in matching for s in a.step_by_step_items)),
        key_terms_items=tuple(dict.fromkeys(t for a in matching for t in a.key_terms_items)),
        faq_items=tuple(dict.fromkeys(f for a in matching for f in a.faq_items)),
        cas_key=winner.cas_key,
        sha256=winner.sha256,
        markdown_body=winner.markdown_body,
        previous_version=winner.previous_version,
        previous_cas_key=winner.previous_cas_key,
        is_autonomous_generated=winner.is_autonomous_generated,
        autonomous_run_id=winner.autonomous_run_id,
        contract_label=winner.contract_label,
        trigger_label=winner.trigger_label,
        real_example_text=next(
            (a.real_example_text for a in reversed(matching) if a.real_example_text), None
        ),
        common_pitfalls_items=tuple(
            dict.fromkeys(p for a in matching for p in a.common_pitfalls_items)
        ),
    )
    return merged, tuple(a.layer for a in matching)


def build_assistant_prefill(route: str, title: str, lang: HelpLanguageCode) -> str:
    """Build localized contextual prompt prefill for Ask-Assistant CTA."""
    if lang == "en":
        return f"Help me understand screen {route} ({title})"
    return f"Explique-moi comment utiliser l'écran {route} ({title})"
