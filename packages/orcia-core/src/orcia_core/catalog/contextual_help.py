"""Story 9.5 — Hybrid Contextual Help (`HelpArticle` in `catalog_items` + `cas/<sha256>`).

Implements:
- Git-seeded Markdown help files (`docs/help/{fr,en}/` & `packages/orcia-pack-*/help/{fr,en}/`)
  stored under `item_type = 'HELP_ARTICLE'` in `catalog_items` with CAS body `cas/<sha256>`,
  protecting any hot-published `@v(N+1)` version from being overwritten by startup seeding.
- `< 10 ms` resolution via Redis key `help:route:<route>:<pack>:<lang>` applying the 4-layer
  override hierarchy (`BASE -> PACK -> WORKSPACE -> USER`, `AD-14`).
- 1-click `⏪ Rollback` restoring `@v(N-1)` from CAS (`Principes D & D.4`, `AD-5`, `AD-14`).
"""

from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from orcia_core.catalog._internal.sql_contextual_help import (
    list_pg_help_articles_sql,
    publish_hot_help_article_sql,
    rollback_help_article_sql,
)
from orcia_core.observability.logging import get_logger
from orcia_kernel.errors import ResourceNotFoundError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

logger = get_logger("orcia.core.catalog.contextual_help")

HelpArticleLayer = Literal["BASE", "PACK", "WORKSPACE", "USER"]
HelpLanguageCode = Literal["fr", "en"]

HELP_ITEM_TYPE: str = "HELP_ARTICLE"
LAYER_PRECEDENCE: dict[HelpArticleLayer, int] = {
    "BASE": 1,
    "PACK": 2,
    "WORKSPACE": 3,
    "USER": 4,
}


@dataclass(frozen=True, slots=True)
class HelpArticleCatalogItem:
    """Domain representation of a `HELP_ARTICLE` stored in `catalog_items` + `cas/<sha256>`."""

    resource_id: str
    uri: str
    title: str
    version: str
    lang: HelpLanguageCode
    layer: HelpArticleLayer
    pack_name: str | None
    bound_routes: tuple[str, ...]
    summary_what_for: str
    step_by_step_items: tuple[str, ...]
    key_terms_items: tuple[str, ...]
    faq_items: tuple[str, ...]
    cas_key: str
    sha256: str
    markdown_body: str
    item_type: str = HELP_ITEM_TYPE
    previous_version: str | None = None
    previous_cas_key: str | None = None
    is_autonomous_generated: bool = False
    autonomous_run_id: str | None = None
    contract_label: str | None = None
    trigger_label: str | None = None


@dataclass(frozen=True, slots=True)
class ContextualHelpResolutionResult:
    """Resolved contextual help payload returned by `GET /api/v1/help/resolve` (`< 10 ms`)."""

    route: str
    pack: str
    lang: HelpLanguageCode
    redis_cache_key: str
    cache_hit: bool
    merged_layers: tuple[HelpArticleLayer, ...]
    active_article: HelpArticleCatalogItem
    rollback_available: bool
    ask_assistant_prefill: str
    is_autonomous_generated: bool = False
    run_id: str | None = None
    contract_label: str | None = None
    trigger_label: str | None = None
    previous_version_available: bool = False


def normalize_help_pack(pack: str) -> str:
    """Normalize legacy `orcia-core` pack identifier onto canonical `core`."""
    cleaned = pack.strip()
    if not cleaned or cleaned == "orcia-core":
        return "core"
    return cleaned


def build_help_redis_cache_key(route: str, pack: str, lang: str) -> str:
    """Build the canonical Redis cache key `help:route:<route>:<pack>:<lang>` (`Story 9.5`)."""
    norm_route = route.strip() or "/cockpit"
    norm_pack = normalize_help_pack(pack)
    norm_lang = lang.strip().lower() or "fr"
    return f"help:route:{norm_route}:{norm_pack}:{norm_lang}"


def _parse_version_tuple(version_str: str) -> tuple[int, ...]:
    cleaned = version_str.strip().lstrip("v@")
    parts: list[int] = []
    for token in cleaned.split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0, 0, 0)


def is_version_strictly_newer(candidate_version: str, baseline_version: str) -> bool:
    """Return True if `candidate_version` (`@v(N+1)`) is strictly newer than `baseline_version`."""
    return _parse_version_tuple(candidate_version) > _parse_version_tuple(baseline_version)


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

    step_items: list[str] = []
    term_items: list[str] = []
    faq_items: list[str] = []
    current_bucket: list[str] | None = None

    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("### "):
            heading = s[4:].lower()
            if "pas-à-pas" in heading or "step-by-step" in heading:
                current_bucket = step_items
            elif "termes" in heading or "key terms" in heading:
                current_bucket = term_items
            elif "questions" in heading or "frequently" in heading:
                current_bucket = faq_items
            else:
                current_bucket = None
            continue
        if current_bucket is not None:
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

    return HelpArticleCatalogItem(
        resource_id=meta.get("resource_id", f"help-{digest[:12]}"),
        uri=meta.get("uri", f"orcia://system/help/{digest[:12]}"),
        title=meta.get("title", "Aide Contextuelle ORCIA"),
        version=meta.get("version", "1.0.0"),
        lang=lang_val,
        layer=layer_val,
        pack_name=meta.get("pack_name") or None,
        bound_routes=tuple(bound_routes) if bound_routes else ("/cockpit",),
        summary_what_for=meta.get("summary_what_for", ""),
        step_by_step_items=tuple(step_items),
        key_terms_items=tuple(term_items),
        faq_items=tuple(faq_items),
        cas_key=cas_key,
        sha256=digest,
        markdown_body=body,
    )


class ContextualHelpResolutionService:
    """Service managing Git-seeded `HELP_ARTICLE` items, CAS blobs, Redis cache, and Rollback."""

    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        redis_client: Any | None = None,
        engine: AsyncEngine | None = None,
    ) -> None:
        self._articles_by_id: dict[str, HelpArticleCatalogItem] = {}
        self._cas_blobs: dict[str, str] = {}
        self._redis_cache: dict[str, HelpArticleCatalogItem] = {}
        self._history_by_id: dict[str, list[HelpArticleCatalogItem]] = {}
        self._redis_client = redis_client
        self._engine = engine
        root = repo_root or self._detect_repo_root()
        if root is not None:
            self.seed_from_git_directories(root)

    def _invalidate_redis_keys(self, article: HelpArticleCatalogItem) -> None:
        self._redis_cache.clear()
        if self._redis_client is None:
            return
        pack = normalize_help_pack(article.pack_name or "core")
        for rt in article.bound_routes:
            rkey = build_help_redis_cache_key(rt, pack, article.lang)
            try:
                res = self._redis_client.delete(rkey)
                if inspect.isawaitable(res) and hasattr(res, "close"):
                    # Async clients are awaited in `_invalidate_redis_keys_async`.
                    res.close()
            except Exception as exc:
                logger.warning("help_redis_delete_sync_failed", key=rkey, error=str(exc))

    async def _invalidate_redis_keys_async(self, article: HelpArticleCatalogItem) -> None:
        self._redis_cache.clear()
        if self._redis_client is None:
            return
        pack = normalize_help_pack(article.pack_name or "core")
        for rt in article.bound_routes:
            rkey = build_help_redis_cache_key(rt, pack, article.lang)
            try:
                res = self._redis_client.delete(rkey)
                if inspect.isawaitable(res):
                    await res
            except Exception as exc:
                logger.warning("help_redis_delete_async_failed", key=rkey, error=str(exc))

    @staticmethod
    def _detect_repo_root() -> Path | None:
        curr = Path(__file__).resolve()
        for parent in curr.parents:
            if (parent / "docs" / "help").exists():
                return parent
        return None

    def seed_from_git_directories(self, repo_root: Path) -> int:
        """Idempotently load `docs/help/{fr,en}/*.md` and `packages/orcia-pack-*/help/`."""
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

        seeded_count = 0
        for folder in search_dirs:
            if not folder.exists():
                continue
            for md_file in sorted(folder.glob("*.md")):
                raw = md_file.read_text(encoding="utf-8")
                article = parse_declarative_help_markdown(raw)
                if self.upsert_seeded_article(article):
                    seeded_count += 1
        return seeded_count

    def upsert_seeded_article(self, article: HelpArticleCatalogItem) -> bool:
        """Upsert a Git-seeded `HELP_ARTICLE` without ever overwriting a newer `@v(N+1)` version."""
        existing = self._articles_by_id.get(article.resource_id)
        if existing is not None and is_version_strictly_newer(existing.version, article.version):
            # Preserve newer hot-published @v(N+1) version!
            return False
        self._cas_blobs[article.cas_key] = article.markdown_body
        self._articles_by_id[article.resource_id] = article
        self._redis_cache.clear()
        return True

    def publish_hot_version(
        self,
        *,
        resource_id: str,
        new_version: str,
        new_title: str,
        new_summary_what_for: str,
        new_markdown_body: str,
        layer: HelpArticleLayer | None = None,
        is_autonomous_generated: bool = False,
        autonomous_run_id: str | None = None,
        contract_label: str | None = None,
        trigger_label: str | None = None,
    ) -> HelpArticleCatalogItem:
        """Publish a hot `@v(N+1)` help article in `cas/<sha256>` and preserve `@v(N-1)`."""
        existing = self._articles_by_id.get(resource_id)
        if existing is None:
            raise ResourceNotFoundError(detail_override=f"HelpArticle introuvable : {resource_id}")

        self._history_by_id.setdefault(resource_id, []).append(existing)
        digest = hashlib.sha256(new_markdown_body.encode("utf-8")).hexdigest()
        cas_key = f"cas/{digest}"
        self._cas_blobs[cas_key] = new_markdown_body

        updated = HelpArticleCatalogItem(
            resource_id=existing.resource_id,
            uri=existing.uri,
            title=new_title,
            version=new_version,
            lang=existing.lang,
            layer=layer if layer is not None else existing.layer,
            pack_name=existing.pack_name,
            bound_routes=existing.bound_routes,
            summary_what_for=new_summary_what_for,
            step_by_step_items=existing.step_by_step_items,
            key_terms_items=existing.key_terms_items,
            faq_items=existing.faq_items,
            cas_key=cas_key,
            sha256=digest,
            markdown_body=new_markdown_body,
            previous_version=existing.version,
            previous_cas_key=existing.cas_key,
            is_autonomous_generated=is_autonomous_generated,
            autonomous_run_id=autonomous_run_id,
            contract_label=contract_label,
            trigger_label=trigger_label,
        )
        self._articles_by_id[resource_id] = updated
        self._invalidate_redis_keys(updated)
        return updated

    def rollback_to_previous_version(self, resource_id: str) -> HelpArticleCatalogItem:
        """Execute a 1-click `⏪ Rollback` restoring `@v(N-1)` and flushing the Redis help cache."""
        history = self._history_by_id.get(resource_id, [])
        if not history:
            raise ResourceNotFoundError(
                detail_override=f"Aucune version antérieure @v(N-1) disponible pour {resource_id}."
            )
        restored = history.pop()
        self._articles_by_id[resource_id] = restored
        self._invalidate_redis_keys(restored)
        return restored

    def resolve_for_route(
        self,
        *,
        route: str,
        pack: str = "orcia-pack-sdlc",
        lang: HelpLanguageCode = "fr",
    ) -> ContextualHelpResolutionResult:
        """Resolve contextual help in `< 10 ms` using Redis cache and 4-layer merge (`AD-14`)."""
        cache_key = build_help_redis_cache_key(route, pack, lang)
        cached = self._redis_cache.get(cache_key)
        matching_layers = self._collect_matching_articles(route=route, pack=pack, lang=lang)
        merged_layer_names = tuple(a.layer for a in matching_layers)

        if cached is not None:
            has_rollback = bool(self._history_by_id.get(cached.resource_id))
            return ContextualHelpResolutionResult(
                route=route,
                pack=pack,
                lang=lang,
                redis_cache_key=cache_key,
                cache_hit=True,
                merged_layers=merged_layer_names or (cached.layer,),
                active_article=cached,
                rollback_available=has_rollback,
                ask_assistant_prefill=self._build_assistant_prefill(route, cached.title, lang),
                is_autonomous_generated=cached.is_autonomous_generated,
                run_id=cached.autonomous_run_id,
                contract_label=cached.contract_label,
                trigger_label=cached.trigger_label,
                previous_version_available=has_rollback,
            )

        if not matching_layers:
            # Fallback to any article in requested language
            fallback = next(
                (a for a in self._articles_by_id.values() if a.lang == lang),
                None,
            )
            if fallback is None:
                raise ResourceNotFoundError(
                    detail_override=f"Aucune fiche d'aide trouvée pour route={route} ({lang})."
                )
            matching_layers = [fallback]
            merged_layer_names = (fallback.layer,)

        # 4-layer merge (BASE -> PACK -> WORKSPACE -> USER): highest precedence wins
        winner = matching_layers[-1]
        merged_steps = tuple(
            dict.fromkeys(step for art in matching_layers for step in art.step_by_step_items)
        )
        merged_terms = tuple(
            dict.fromkeys(term for art in matching_layers for term in art.key_terms_items)
        )
        merged_faqs = tuple(dict.fromkeys(faq for art in matching_layers for faq in art.faq_items))
        resolved_article = HelpArticleCatalogItem(
            resource_id=winner.resource_id,
            uri=winner.uri,
            title=winner.title,
            version=winner.version,
            lang=winner.lang,
            layer=winner.layer,
            pack_name=winner.pack_name,
            bound_routes=winner.bound_routes,
            summary_what_for=winner.summary_what_for,
            step_by_step_items=merged_steps,
            key_terms_items=merged_terms,
            faq_items=merged_faqs,
            cas_key=winner.cas_key,
            sha256=winner.sha256,
            markdown_body=winner.markdown_body,
            previous_version=winner.previous_version,
            previous_cas_key=winner.previous_cas_key,
            is_autonomous_generated=winner.is_autonomous_generated,
            autonomous_run_id=winner.autonomous_run_id,
            contract_label=winner.contract_label,
            trigger_label=winner.trigger_label,
        )
        self._redis_cache[cache_key] = resolved_article
        has_rollback = bool(
            self._history_by_id.get(resolved_article.resource_id)
            or resolved_article.previous_version
        )
        return ContextualHelpResolutionResult(
            route=route,
            pack=pack,
            lang=lang,
            redis_cache_key=cache_key,
            cache_hit=False,
            merged_layers=merged_layer_names,
            active_article=resolved_article,
            rollback_available=has_rollback,
            ask_assistant_prefill=self._build_assistant_prefill(
                route, resolved_article.title, lang
            ),
            is_autonomous_generated=resolved_article.is_autonomous_generated,
            run_id=resolved_article.autonomous_run_id,
            contract_label=resolved_article.contract_label,
            trigger_label=resolved_article.trigger_label,
            previous_version_available=has_rollback,
        )

    def _collect_matching_articles(
        self,
        *,
        route: str,
        pack: str,
        lang: HelpLanguageCode,
        articles: dict[str, HelpArticleCatalogItem] | None = None,
    ) -> list[HelpArticleCatalogItem]:
        pool = articles if articles is not None else self._articles_by_id
        norm_pack = normalize_help_pack(pack)
        matched: list[HelpArticleCatalogItem] = []
        for art in pool.values():
            if art.lang != lang:
                continue
            art_pack = normalize_help_pack(art.pack_name) if art.pack_name else None
            if art.layer == "PACK" and art_pack not in (None, norm_pack):
                continue
            if route in art.bound_routes:
                matched.append(art)
        matched.sort(key=lambda item: LAYER_PRECEDENCE.get(item.layer, 1))
        return matched

    @staticmethod
    def _dict_to_article(data: dict[str, Any]) -> HelpArticleCatalogItem:
        raw_layer = str(data.get("layer") or "BASE").upper()
        layer_val: HelpArticleLayer = (
            raw_layer  # type: ignore[assignment]
            if raw_layer in ("BASE", "PACK", "WORKSPACE", "USER")
            else "BASE"
        )
        lang_val: HelpLanguageCode = "en" if data.get("lang") == "en" else "fr"
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
            markdown_body=str(data.get("markdown_body") or ""),
            previous_version=(
                str(data["previous_version"]) if data.get("previous_version") else None
            ),
            previous_cas_key=(
                str(data["previous_cas_key"]) if data.get("previous_cas_key") else None
            ),
            is_autonomous_generated=bool(data.get("is_autonomous_generated", False)),
            autonomous_run_id=(
                str(data["autonomous_run_id"]) if data.get("autonomous_run_id") else None
            ),
            contract_label=str(data["contract_label"]) if data.get("contract_label") else None,
            trigger_label=str(data["trigger_label"]) if data.get("trigger_label") else None,
        )

    @staticmethod
    def _serialize_redis_payload(
        article: HelpArticleCatalogItem, merged_layers: tuple[HelpArticleLayer, ...]
    ) -> str:
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
                },
            },
            ensure_ascii=False,
        )

    async def publish_hot_version_async(
        self,
        *,
        resource_id: str,
        new_version: str,
        new_title: str,
        new_summary_what_for: str,
        new_markdown_body: str,
        layer: HelpArticleLayer | None = None,
        is_autonomous_generated: bool = False,
        autonomous_run_id: str | None = None,
        contract_label: str | None = None,
        trigger_label: str | None = None,
    ) -> HelpArticleCatalogItem:
        """Async publish `@v(N+1)` synced across PG18 `catalog_items`, memory, and Redis."""
        if self._engine is not None:
            pg_dict = await publish_hot_help_article_sql(
                self._engine,
                resource_id=resource_id,
                new_version=new_version,
                new_title=new_title,
                new_summary_what_for=new_summary_what_for,
                new_markdown_body=new_markdown_body,
                layer=layer,
            )
            if pg_dict is not None:
                art = self._dict_to_article(pg_dict)
                self._articles_by_id[resource_id] = art
                await self._invalidate_redis_keys_async(art)
                return art
        updated = self.publish_hot_version(
            resource_id=resource_id,
            new_version=new_version,
            new_title=new_title,
            new_summary_what_for=new_summary_what_for,
            new_markdown_body=new_markdown_body,
            layer=layer,
            is_autonomous_generated=is_autonomous_generated,
            autonomous_run_id=autonomous_run_id,
            contract_label=contract_label,
            trigger_label=trigger_label,
        )
        await self._invalidate_redis_keys_async(updated)
        return updated

    async def rollback_to_previous_version_async(self, resource_id: str) -> HelpArticleCatalogItem:
        """Async 1-click `⏪ Rollback` restoring `@v(N-1)` in PG18 & flushing Redis."""
        if self._engine is not None:
            pg_dict = await rollback_help_article_sql(self._engine, resource_id=resource_id)
            if pg_dict is not None:
                restored = self._dict_to_article(pg_dict)
                self._articles_by_id[resource_id] = restored
                await self._invalidate_redis_keys_async(restored)
                return restored
        restored = self.rollback_to_previous_version(resource_id)
        await self._invalidate_redis_keys_async(restored)
        return restored

    async def resolve_for_route_async(
        self,
        *,
        route: str,
        pack: str = "core",
        lang: HelpLanguageCode = "fr",
    ) -> ContextualHelpResolutionResult:
        """Resolve contextual help using Redis cache + PG18 `catalog_items` (`MAJOR-01`)."""
        norm_pack = normalize_help_pack(pack)
        cache_key = build_help_redis_cache_key(route, norm_pack, lang)
        if self._redis_client is not None:
            try:
                raw_res = self._redis_client.get(cache_key)
                raw = await raw_res if inspect.isawaitable(raw_res) else raw_res
                if raw:
                    text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
                    cached_obj = json.loads(text)
                    cached_art = self._dict_to_article(cached_obj["article"])
                    has_rb = bool(
                        self._history_by_id.get(cached_art.resource_id)
                        or cached_art.previous_version
                    )
                    layers = tuple(cached_obj.get("merged_layers") or (cached_art.layer,))
                    return ContextualHelpResolutionResult(
                        route=route,
                        pack=norm_pack,
                        lang=lang,
                        redis_cache_key=cache_key,
                        cache_hit=True,
                        merged_layers=layers,
                        active_article=cached_art,
                        rollback_available=has_rb,
                        ask_assistant_prefill=self._build_assistant_prefill(
                            route, cached_art.title, lang
                        ),
                        is_autonomous_generated=cached_art.is_autonomous_generated,
                        run_id=cached_art.autonomous_run_id,
                        contract_label=cached_art.contract_label,
                        trigger_label=cached_art.trigger_label,
                        previous_version_available=has_rb,
                    )
            except Exception as exc:
                logger.warning("help_redis_get_failed", key=cache_key, error=str(exc))

        if self._engine is not None:
            pg_rows = await list_pg_help_articles_sql(self._engine, lang=lang)
            pool = dict(self._articles_by_id)
            for row in pg_rows:
                pg_art = self._dict_to_article(row)
                pool[pg_art.resource_id] = pg_art
            matching = self._collect_matching_articles(
                route=route, pack=norm_pack, lang=lang, articles=pool
            )
            if not matching:
                fb = next((a for a in pool.values() if a.lang == lang), None)
                if fb is None:
                    raise ResourceNotFoundError(
                        detail_override=f"Aucune fiche d'aide trouvée pour route={route} ({lang})."
                    )
                matching = [fb]
            winner = matching[-1]
            resolved = HelpArticleCatalogItem(
                resource_id=winner.resource_id,
                uri=winner.uri,
                title=winner.title,
                version=winner.version,
                lang=winner.lang,
                layer=winner.layer,
                pack_name=winner.pack_name,
                bound_routes=winner.bound_routes,
                summary_what_for=winner.summary_what_for,
                step_by_step_items=tuple(
                    dict.fromkeys(s for a in matching for s in a.step_by_step_items)
                ),
                key_terms_items=tuple(
                    dict.fromkeys(t for a in matching for t in a.key_terms_items)
                ),
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
            )
            merged_layers = tuple(a.layer for a in matching)
            if self._redis_client is not None:
                try:
                    payload = self._serialize_redis_payload(resolved, merged_layers)
                    set_res = self._redis_client.set(cache_key, payload, ex=300)
                    if inspect.isawaitable(set_res):
                        await set_res
                except Exception as exc:
                    logger.warning("help_redis_set_failed", key=cache_key, error=str(exc))
            has_rb = bool(resolved.previous_version)
            return ContextualHelpResolutionResult(
                route=route,
                pack=norm_pack,
                lang=lang,
                redis_cache_key=cache_key,
                cache_hit=False,
                merged_layers=merged_layers,
                active_article=resolved,
                rollback_available=has_rb,
                ask_assistant_prefill=self._build_assistant_prefill(route, resolved.title, lang),
                is_autonomous_generated=resolved.is_autonomous_generated,
                run_id=resolved.autonomous_run_id,
                contract_label=resolved.contract_label,
                trigger_label=resolved.trigger_label,
                previous_version_available=has_rb,
            )

        res = self.resolve_for_route(route=route, pack=norm_pack, lang=lang)
        if self._redis_client is not None:
            try:
                payload = self._serialize_redis_payload(res.active_article, res.merged_layers)
                set_res = self._redis_client.set(cache_key, payload, ex=300)
                if inspect.isawaitable(set_res):
                    await set_res
            except Exception as exc:
                logger.warning("help_redis_set_failed", key=cache_key, error=str(exc))
        return res

    @staticmethod
    def _build_assistant_prefill(route: str, title: str, lang: HelpLanguageCode) -> str:
        if lang == "en":
            return f"Help me understand screen {route} ({title})"
        return f"Explique-moi comment utiliser l'écran {route} ({title})"
