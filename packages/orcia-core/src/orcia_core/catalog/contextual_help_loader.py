"""Markdown loader, parser & serializers for Hybrid Contextual Help (`Story 9.5`, `REM-19`)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from orcia_core.catalog.contextual_help_models import (
    HelpArticleCatalogItem,
    HelpArticleLayer,
    HelpLanguageCode,
)

_STEPS_HEADING_RE = re.compile(
    r"(pas-à-pas|step-by-step|en\s+\d+\s+gestes|in\s+\d+\s+steps|étapes|steps)",
    re.IGNORECASE,
)
_REAL_EXAMPLE_HEADING_RE = re.compile(
    r"(un exemple réel|exemple réel|a real example|real example)",
    re.IGNORECASE,
)
_COMMON_PITFALLS_HEADING_RE = re.compile(
    r"(ce qui coince(?:\s+souvent)?|common pitfalls|pitfalls)",
    re.IGNORECASE,
)
_TERMS_HEADING_RE = re.compile(
    r"(termes|key terms|repères|notions)",
    re.IGNORECASE,
)
_FAQ_HEADING_RE = re.compile(
    r"(questions|frequently)",
    re.IGNORECASE,
)
_WHAT_FOR_HEADING_RE = re.compile(
    r"(à quoi sert|what this screen|what is this screen|objectif)",
    re.IGNORECASE,
)


def parse_declarative_help_markdown(raw_markdown: str) -> HelpArticleCatalogItem:
    """Parse a declarative YAML-frontmatter Markdown help file and compute `cas/<sha256>`."""
    text = raw_markdown.strip()
    meta: dict[str, str] = {}
    bound_routes: list[str] = []
    body = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            frontmatter_lines = parts[1].strip().splitlines()
            body = parts[2].strip()
            in_routes = False
            for line in frontmatter_lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("- ") and in_routes:
                    bound_routes.append(stripped[2:].strip().strip("\"'"))
                    continue
                if ":" in stripped:
                    in_routes = False
                    k, v = stripped.split(":", 1)
                    key = k.strip()
                    val = v.strip().strip("\"'")
                    if key == "bound_routes":
                        in_routes = True
                    else:
                        meta[key] = val

    what_for_lines: list[str] = []
    step_items: list[str] = []
    real_example_lines: list[str] = []
    common_pitfalls_items: list[str] = []
    term_items: list[str] = []
    faq_items: list[str] = []
    current_bucket: list[str] | None = None

    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith(("## ", "### ")):
            heading = s.lstrip("#").strip()
            if _WHAT_FOR_HEADING_RE.search(heading):
                current_bucket = what_for_lines
            elif _STEPS_HEADING_RE.search(heading):
                current_bucket = step_items
            elif _REAL_EXAMPLE_HEADING_RE.search(heading):
                current_bucket = real_example_lines
            elif _COMMON_PITFALLS_HEADING_RE.search(heading):
                current_bucket = common_pitfalls_items
            elif _TERMS_HEADING_RE.search(heading):
                current_bucket = term_items
            elif _FAQ_HEADING_RE.search(heading):
                current_bucket = faq_items
            else:
                current_bucket = None
            continue
        if current_bucket is not None:
            if current_bucket is what_for_lines:
                cleaned_bullet = s
            elif current_bucket is real_example_lines:
                cleaned_bullet = s[2:].strip() if s.startswith(("- ", "* ")) else s
            else:
                cleaned_bullet = s.lstrip("-1234567890. ").strip()
            if cleaned_bullet:
                current_bucket.append(cleaned_bullet)

    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    cas_key = f"cas/{digest}"
    lang_val: HelpLanguageCode = "en" if meta.get("lang") == "en" else "fr"
    raw_layer = meta.get("layer", "BASE").upper()
    layer_val: HelpArticleLayer = (
        raw_layer  # type: ignore[assignment]
        if raw_layer in ("BASE", "PACK", "WORKSPACE", "USER")
        else "BASE"
    )
    fallback_id = f"help-base-{meta['id']}-{lang_val}" if meta.get("id") else f"help-{digest[:12]}"
    summary_what_for = meta.get("summary_what_for") or " ".join(what_for_lines).strip()
    real_example_text = (
        meta.get("real_example_text") or " ".join(real_example_lines).strip() or None
    )

    return HelpArticleCatalogItem(
        resource_id=meta.get("resource_id") or fallback_id,
        uri=meta.get("uri") or f"orcia://system/help/{meta.get('id', digest[:12])}/{lang_val}",
        title=meta.get("title", "Aide Contextuelle ORCIA"),
        version=meta.get("version", "1.0.0"),
        lang=lang_val,
        layer=layer_val,
        pack_name=meta.get("pack_name") or None,
        bound_routes=tuple(bound_routes) if bound_routes else ("/cockpit",),
        summary_what_for=summary_what_for,
        step_by_step_items=tuple(step_items),
        key_terms_items=tuple(term_items),
        faq_items=tuple(faq_items),
        cas_key=cas_key,
        sha256=digest,
        markdown_body=body,
        real_example_text=real_example_text,
        common_pitfalls_items=tuple(common_pitfalls_items),
    )


def load_git_help_articles(repo_root: Path) -> list[HelpArticleCatalogItem]:
    """Load all Markdown help files from `docs/help/{fr,en}/`, `packs/*/help/`, and legacy dirs."""
    search_dirs: list[Path] = [
        repo_root / "docs" / "help" / "fr",
        repo_root / "docs" / "help" / "en",
    ]
    packs_root = repo_root / "packs"
    if packs_root.exists():
        for pack_dir in sorted(packs_root.iterdir()):
            if pack_dir.is_dir():
                search_dirs.append(pack_dir / "help" / "fr")
                search_dirs.append(pack_dir / "help" / "en")
    legacy_packs_root = repo_root / "packages"
    if legacy_packs_root.exists():
        for pack_dir in sorted(legacy_packs_root.glob("orcia-pack-*")):
            search_dirs.append(pack_dir / "help" / "fr")
            search_dirs.append(pack_dir / "help" / "en")

    articles: list[HelpArticleCatalogItem] = []
    for folder in search_dirs:
        if not folder.exists():
            continue
        for md_file in sorted(folder.glob("*.md")):
            raw = md_file.read_text(encoding="utf-8")
            articles.append(parse_declarative_help_markdown(raw))
    return articles


def dict_to_help_article(data: dict[str, Any]) -> HelpArticleCatalogItem:
    """Hydrate a `HelpArticleCatalogItem` from a database or Redis JSON dictionary."""
    raw_layer = str(data.get("layer") or "BASE").upper()
    layer_val: HelpArticleLayer = (
        raw_layer  # type: ignore[assignment]
        if raw_layer in ("BASE", "PACK", "WORKSPACE", "USER")
        else "BASE"
    )
    lang_val: HelpLanguageCode = "en" if data.get("lang") == "en" else "fr"
    markdown_body = str(data.get("markdown_body") or "")
    raw_real_example = data.get("real_example_text")
    real_example_text = str(raw_real_example).strip() or None if raw_real_example else None
    common_pitfalls = tuple(str(x) for x in (data.get("common_pitfalls_items") or ()))

    # Backfill dedicated 4-block fields from markdown_body for pre-23.3 DB/Redis records
    if (
        "real_example_text" not in data
        and "common_pitfalls_items" not in data
        and markdown_body.strip()
    ):
        reparsed = parse_declarative_help_markdown(markdown_body)
        real_example_text = reparsed.real_example_text
        common_pitfalls = reparsed.common_pitfalls_items

    return HelpArticleCatalogItem(
        resource_id=str(data["resource_id"]),
        uri=str(data["uri"]),
        title=str(data["title"]),
        version=str(data["version"]),
        lang=lang_val,
        layer=layer_val,
        pack_name=str(data["pack_name"]) if data.get("pack_name") else None,
        bound_routes=tuple(str(r) for r in (data.get("bound_routes") or ("/cockpit",))),
        summary_what_for=str(data.get("summary_what_for") or ""),
        step_by_step_items=tuple(str(x) for x in (data.get("step_by_step_items") or ())),
        key_terms_items=tuple(str(x) for x in (data.get("key_terms_items") or ())),
        faq_items=tuple(str(x) for x in (data.get("faq_items") or ())),
        cas_key=str(data["cas_key"]),
        sha256=str(data["sha256"]),
        markdown_body=markdown_body,
        previous_version=(str(data["previous_version"]) if data.get("previous_version") else None),
        previous_cas_key=(str(data["previous_cas_key"]) if data.get("previous_cas_key") else None),
        is_autonomous_generated=bool(data.get("is_autonomous_generated", False)),
        autonomous_run_id=(
            str(data["autonomous_run_id"]) if data.get("autonomous_run_id") else None
        ),
        contract_label=str(data["contract_label"]) if data.get("contract_label") else None,
        trigger_label=str(data["trigger_label"]) if data.get("trigger_label") else None,
        real_example_text=real_example_text,
        common_pitfalls_items=common_pitfalls,
    )


def serialize_redis_help_payload(
    article: HelpArticleCatalogItem, merged_layers: tuple[HelpArticleLayer, ...]
) -> str:
    """Serialize a resolved `HelpArticleCatalogItem` and merged layers for Redis caching."""
    return json.dumps(
        {
            "merged_layers": list(merged_layers),
            "article": {
                "resource_id": article.resource_id,
                "uri": article.uri,
                "title": article.title,
                "version": article.version,
                "lang": article.lang,
                "layer": article.layer,
                "pack_name": article.pack_name,
                "bound_routes": list(article.bound_routes),
                "summary_what_for": article.summary_what_for,
                "step_by_step_items": list(article.step_by_step_items),
                "key_terms_items": list(article.key_terms_items),
                "faq_items": list(article.faq_items),
                "cas_key": article.cas_key,
                "sha256": article.sha256,
                "markdown_body": article.markdown_body,
                "previous_version": article.previous_version,
                "previous_cas_key": article.previous_cas_key,
                "is_autonomous_generated": article.is_autonomous_generated,
                "autonomous_run_id": article.autonomous_run_id,
                "contract_label": article.contract_label,
                "trigger_label": article.trigger_label,
                "real_example_text": article.real_example_text,
                "common_pitfalls_items": list(article.common_pitfalls_items),
            },
        },
        ensure_ascii=False,
    )
