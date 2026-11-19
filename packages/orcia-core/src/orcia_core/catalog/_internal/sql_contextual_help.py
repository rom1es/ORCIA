"""PostgreSQL 18 queries for `HELP_ARTICLE` in `catalog_items` (`Story 9.5`, `MAJOR-01`)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.observability.logging import get_logger
from orcia_kernel.errors import ResourceNotFoundError
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.core.catalog.sql_contextual_help")


def _is_missing_table_error(exc: Exception) -> bool:
    msg = str(exc)
    return "UndefinedTableError" in type(exc).__name__ or "does not exist" in msg


def row_to_help_dict(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize a `catalog_items` row mapping for `HelpArticleCatalogItem` hydration."""
    meta = dict(row.get("metadata_jsonb") or {})
    routes = meta.get("bound_routes") or []
    bound_routes = tuple(str(r) for r in routes) if isinstance(routes, list) else ("/cockpit",)
    return {
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
        if _is_missing_table_error(exc):
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
        if _is_missing_table_error(exc):
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
                    detail_override=(
                        f"Aucune version antérieure @v(N-1) disponible pour {resource_id}."
                    )
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
        if _is_missing_table_error(exc):
            logger.warning("rollback_help_article_sql_skipped", error=str(exc))
            return None
        raise


async def seed_help_articles_to_pg18_sql(
    engine: AsyncEngine,
    articles: Iterable[Any],
) -> int:
    """Idempotently seed `HELP_ARTICLE` rows into `catalog_items` without overwriting `@v(N+1)`."""
    items = list(articles)
    if not items:
        return 0
    try:
        async with engine.begin() as conn:
            org_row = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT id
                        FROM org_units
                        ORDER BY (CASE WHEN unit_type = 'ENTERPRISE' THEN 0 ELSE 1 END), id ASC
                        LIMIT 1
                        """
                    )
                )
            ).first()
            if org_row is None:
                return 0
            owner_org_unit_id = org_row[0]
            inserted = 0
            stmt = sa.text(
                """
                INSERT INTO catalog_items (
                    id, resource_id, uri, title, description, resource_type, source_format,
                    version, sha256, cas_key, visibility_scope, owner_org_unit_id,
                    owner_workspace_id, item_type, metadata_jsonb
                )
                VALUES (
                    :id, :resource_id, :uri, :title, :description, 'template', 'ORCIA',
                    :version, :sha256, :cas_key, 'PUBLISHED_ORG', :owner_org_unit_id,
                    NULL, 'HELP_ARTICLE', CAST(:metadata_jsonb AS jsonb)
                )
                ON CONFLICT (resource_id) DO NOTHING;
                """
            )
            for art in items:
                meta = {
                    "lang": art.lang,
                    "layer": art.layer,
                    "pack_name": art.pack_name,
                    "bound_routes": list(art.bound_routes),
                    "summary_what_for": art.summary_what_for,
                    "step_by_step_items": list(art.step_by_step_items),
                    "key_terms_items": list(art.key_terms_items),
                    "faq_items": list(art.faq_items),
                    "markdown_body": art.markdown_body,
                }
                res = await conn.execute(
                    stmt,
                    {
                        "id": UUID(new_uuid7_str()),
                        "resource_id": art.resource_id,
                        "uri": art.uri,
                        "title": art.title,
                        "description": art.summary_what_for,
                        "version": art.version,
                        "sha256": art.sha256,
                        "cas_key": art.cas_key,
                        "owner_org_unit_id": owner_org_unit_id,
                        "metadata_jsonb": json.dumps(meta, ensure_ascii=False),
                    },
                )
                inserted += int(res.rowcount or 0)
            return inserted
    except Exception as exc:
        if _is_missing_table_error(exc):
            logger.warning("seed_help_articles_to_pg18_sql_skipped", error=str(exc))
            return 0
        raise
