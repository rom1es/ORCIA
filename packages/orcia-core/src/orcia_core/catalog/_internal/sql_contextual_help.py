"""PostgreSQL 18 queries for `HELP_ARTICLE` in `catalog_items` (`Story 9.5`, `MAJOR-01`)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.catalog._internal._sql_contextual_help_seed import (
    is_missing_table_error,
    seed_help_articles_to_pg18_sql,
)
from orcia_core.catalog.errors import ResourceNotFoundError
from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.core.catalog.sql_contextual_help")

__all__ = [
    "list_pg_help_articles_sql",
    "publish_hot_help_article_sql",
    "rollback_help_article_sql",
    "row_to_help_dict",
    "seed_help_articles_to_pg18_sql",
]


def row_to_help_dict(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize a `catalog_items` row mapping for `HelpArticleCatalogItem` hydration."""
    meta = dict(row.get("metadata_jsonb") or {})
    routes = meta.get("bound_routes") or []
    bound_routes = tuple(str(r) for r in routes) if isinstance(routes, list) else ("/cockpit",)
    result: dict[str, Any] = {
        "resource_id": str(row["resource_id"]),
        "uri": str(row["uri"]),
        "title": str(row["title"]),
        "version": str(row["version"]),
        "sha256": str(row["sha256"]),
        "cas_key": str(row["cas_key"]),
        "lang": "en" if str(meta.get("lang") or "fr").lower() == "en" else "fr",
        "layer": str(meta.get("layer") or "BASE").upper(),
        "pack_name": meta.get("pack_name"),
        "bound_routes": bound_routes,
        "summary_what_for": str(meta.get("summary_what_for") or row.get("description") or ""),
        "step_by_step_items": tuple(str(x) for x in (meta.get("step_by_step_items") or [])),
        "key_terms_items": tuple(str(x) for x in (meta.get("key_terms_items") or [])),
        "faq_items": tuple(str(x) for x in (meta.get("faq_items") or [])),
        "markdown_body": str(meta.get("markdown_body") or ""),
        "previous_version": (
            str(meta["previous_version"]) if meta.get("previous_version") else None
        ),
        "previous_cas_key": (
            str(meta["previous_cas_key"]) if meta.get("previous_cas_key") else None
        ),
        "is_autonomous_generated": bool(meta.get("is_autonomous_generated", False)),
        "autonomous_run_id": (
            str(meta["autonomous_run_id"]) if meta.get("autonomous_run_id") else None
        ),
        "contract_label": (str(meta["contract_label"]) if meta.get("contract_label") else None),
        "trigger_label": (str(meta["trigger_label"]) if meta.get("trigger_label") else None),
    }
    if "real_example_text" in meta:
        result["real_example_text"] = meta.get("real_example_text")
    if "common_pitfalls_items" in meta:
        result["common_pitfalls_items"] = tuple(
            str(x) for x in (meta.get("common_pitfalls_items") or [])
        )
    return result


async def list_pg_help_articles_sql(
    engine: AsyncEngine,
    *,
    lang: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch `HELP_ARTICLE` rows from PostgreSQL `catalog_items`."""
    stmt = (
        sa.text(
            """
            SELECT resource_id, uri, title, description, version, sha256, cas_key, metadata_jsonb
            FROM catalog_items
            WHERE item_type = 'HELP_ARTICLE'
              AND COALESCE(metadata_jsonb->>'lang', 'fr') = :lang
            ORDER BY resource_id ASC;
            """
        )
        if lang is not None
        else sa.text(
            """
            SELECT resource_id, uri, title, description, version, sha256, cas_key, metadata_jsonb
            FROM catalog_items
            WHERE item_type = 'HELP_ARTICLE'
            ORDER BY resource_id ASC;
            """
        )
    )
    params = {"lang": lang} if lang is not None else {}
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(stmt, params)).mappings().all()
            return [row_to_help_dict(dict(r)) for r in rows]
    except Exception as exc:
        if is_missing_table_error(exc):
            logger.warning("list_pg_help_articles_sql_skipped", error=str(exc))
            return []
        raise


async def publish_hot_help_article_sql(
    engine: AsyncEngine,
    *,
    resource_id: str,
    new_version: str,
    new_title: str,
    new_summary_what_for: str,
    new_markdown_body: str,
    layer: str | None = None,
) -> dict[str, Any] | None:
    """Update `catalog_items` `HELP_ARTICLE` to `@v(N+1)` while preserving `@v(N-1)` metadata."""
    digest = hashlib.sha256(new_markdown_body.encode("utf-8")).hexdigest()
    cas_key = f"cas/{digest}"
    try:
        async with engine.begin() as conn:
            row = (
                (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT resource_id, uri, title, description, version, sha256,
                                   cas_key, metadata_jsonb
                            FROM catalog_items
                            WHERE resource_id = :res_id AND item_type = 'HELP_ARTICLE'
                            LIMIT 1;
                            """
                        ),
                        {"res_id": resource_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                return None
            meta = dict(row["metadata_jsonb"] or {})
            meta["previous_version"] = str(row["version"])
            meta["previous_sha256"] = str(row["sha256"])
            meta["previous_cas_key"] = str(row["cas_key"])
            meta["previous_title"] = str(row["title"])
            meta["previous_summary_what_for"] = str(
                meta.get("summary_what_for") or row.get("description") or ""
            )
            if meta.get("markdown_body"):
                meta["previous_markdown_body"] = str(meta["markdown_body"])
            meta["summary_what_for"] = new_summary_what_for
            meta["markdown_body"] = new_markdown_body
            if layer is not None:
                meta["layer"] = layer
            await conn.execute(
                sa.text(
                    """
                    UPDATE catalog_items
                    SET title = :title,
                        version = :ver,
                        sha256 = :sha,
                        cas_key = :cas,
                        metadata_jsonb = CAST(:meta AS jsonb)
                    WHERE resource_id = :res_id;
                    """
                ),
                {
                    "title": new_title,
                    "ver": new_version,
                    "sha": digest,
                    "cas": cas_key,
                    "meta": json.dumps(meta),
                    "res_id": resource_id,
                },
            )
            updated = dict(row)
            updated.update(
                title=new_title,
                version=new_version,
                sha256=digest,
                cas_key=cas_key,
                metadata_jsonb=meta,
            )
            return row_to_help_dict(updated)
    except Exception as exc:
        if is_missing_table_error(exc):
            logger.warning("publish_hot_help_article_sql_skipped", error=str(exc))
            return None
        raise


async def rollback_help_article_sql(
    engine: AsyncEngine,
    *,
    resource_id: str,
) -> dict[str, Any] | None:
    """Restore `@v(N-1)` for a `HELP_ARTICLE` in PostgreSQL `catalog_items`."""
    try:
        async with engine.begin() as conn:
            row = (
                (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT resource_id, uri, title, description, version, sha256,
                                   cas_key, metadata_jsonb
                            FROM catalog_items
                            WHERE resource_id = :res_id AND item_type = 'HELP_ARTICLE'
                            LIMIT 1;
                            """
                        ),
                        {"res_id": resource_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                return None
            meta = dict(row["metadata_jsonb"] or {})
            prev_ver = meta.get("previous_version")
            if not prev_ver:
                raise ResourceNotFoundError(
                    detail_code="ERR_HELP_ARTICLE_PREVIOUS_VERSION_NOT_FOUND",
                    detail_params={"resource_id": resource_id},
                )
            prev_sha = str(meta.get("previous_sha256") or row["sha256"])
            prev_cas = str(meta.get("previous_cas_key") or f"cas/{prev_sha}")
            prev_title = str(meta.get("previous_title") or row["title"])
            prev_summary = str(meta.get("previous_summary_what_for") or "")
            if prev_summary:
                meta["summary_what_for"] = prev_summary
            if meta.get("previous_markdown_body"):
                meta["markdown_body"] = str(meta["previous_markdown_body"])
            for k in (
                "previous_version",
                "previous_sha256",
                "previous_cas_key",
                "previous_title",
                "previous_summary_what_for",
                "previous_markdown_body",
                "autonomous_run_id",
            ):
                meta.pop(k, None)
            meta["is_autonomous_generated"] = False
            await conn.execute(
                sa.text(
                    """
                    UPDATE catalog_items
                    SET title = :title,
                        version = :ver,
                        sha256 = :sha,
                        cas_key = :cas,
                        metadata_jsonb = CAST(:meta AS jsonb)
                    WHERE resource_id = :res_id;
                    """
                ),
                {
                    "title": prev_title,
                    "ver": str(prev_ver),
                    "sha": prev_sha,
                    "cas": prev_cas,
                    "meta": json.dumps(meta),
                    "res_id": resource_id,
                },
            )
            restored = dict(row)
            restored.update(
                title=prev_title,
                version=str(prev_ver),
                sha256=prev_sha,
                cas_key=prev_cas,
                metadata_jsonb=meta,
            )
            return row_to_help_dict(restored)
    except ResourceNotFoundError:
        raise
    except Exception as exc:
        if is_missing_table_error(exc):
            logger.warning("rollback_help_article_sql_skipped", error=str(exc))
            return None
        raise
