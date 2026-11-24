"""Async PostgreSQL 18 seed helper for `HELP_ARTICLE` in `catalog_items` (`Story 9.5`)."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.observability.logging import get_logger
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.core.catalog.sql_contextual_help")


def is_missing_table_error(exc: Exception) -> bool:
    """Return True if exception represents a missing table error."""
    msg = str(exc)
    return "UndefinedTableError" in type(exc).__name__ or "does not exist" in msg


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
                    "real_example_text": art.real_example_text,
                    "common_pitfalls_items": list(art.common_pitfalls_items),
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
        if is_missing_table_error(exc):
            logger.warning("seed_help_articles_to_pg18_sql_skipped", error=str(exc))
            return 0
        raise
