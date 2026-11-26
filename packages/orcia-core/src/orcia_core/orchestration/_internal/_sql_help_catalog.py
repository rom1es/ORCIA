"""PostgreSQL persistence for generated `HELP_ARTICLE` items (`Story 11.5`, `MAJOR-01`)."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from uuid_utils import uuid7


async def persist_help_catalog_items_sql(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    article_id: str,
    version: str,
    pack_slug: str,
    title_fr: str,
    title_en: str,
    bound_routes: list[str],
    glossary_terms: list[str],
    fr_sha: str,
    en_sha: str,
    summary_fr: str = "",
    summary_en: str = "",
    fr_markdown: str = "",
    en_markdown: str = "",
    autonomous_run_id: str | None = None,
    contract_label: str | None = None,
    trigger_label: str | None = None,
) -> None:
    """Upsert `HELP_ARTICLE` rows in `catalog_items`, preserving `@v(N-1)` for rollback."""
    root_org_id = UUID("0192c4e0-0000-7000-8000-000000000001")
    layer = "PACK" if pack_slug not in ("", "core") else "BASE"
    async with session_factory() as session, session.begin():
        await session.execute(
            sa.text(
                """
                INSERT INTO org_units (id, slug, name, unit_type, parent_id)
                VALUES (:id, 'orcia-root-org', 'ORCIA Root Org', 'ENTERPRISE', NULL)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": root_org_id},
        )
        entries = (
            ("fr", title_fr, fr_sha, summary_fr, fr_markdown),
            ("en", title_en, en_sha, summary_en, en_markdown),
        )
        for lang_code, title, sha, summary, markdown_body in entries:
            res_id = f"{article_id}-{lang_code}"
            uri = f"orcia://packs/{pack_slug}/help/{article_id}/{lang_code}"
            existing = (
                (
                    await session.execute(
                        sa.text(
                            """
                            SELECT title, version, sha256, cas_key, metadata_jsonb
                            FROM catalog_items
                            WHERE resource_id = :res_id
                            LIMIT 1;
                            """
                        ),
                        {"res_id": res_id},
                    )
                )
                .mappings()
                .first()
            )
            meta: dict[str, Any] = {
                "bound_routes": bound_routes,
                "glossary_terms": glossary_terms,
                "authority_role": "REFERENCE",
                "lang": lang_code,
                "pack_name": pack_slug,
                "layer": layer,
                "summary_what_for": summary,
                "markdown_body": markdown_body,
                "is_autonomous_generated": bool(autonomous_run_id),
            }
            if autonomous_run_id:
                meta["autonomous_run_id"] = autonomous_run_id
            if contract_label:
                meta["contract_label"] = contract_label
            if trigger_label:
                meta["trigger_label"] = trigger_label
            if existing is not None and str(existing["version"]) != version:
                prev_meta = dict(existing["metadata_jsonb"] or {})
                meta["previous_version"] = str(existing["version"])
                meta["previous_sha256"] = str(existing["sha256"])
                meta["previous_cas_key"] = str(existing["cas_key"])
                meta["previous_title"] = str(existing["title"])
                if prev_meta.get("summary_what_for"):
                    meta["previous_summary_what_for"] = str(prev_meta["summary_what_for"])
                if prev_meta.get("markdown_body"):
                    meta["previous_markdown_body"] = str(prev_meta["markdown_body"])

            await session.execute(
                sa.text(
                    """
                    INSERT INTO catalog_items (
                        id, resource_id, uri, title, description,
                        resource_type, source_format, version, sha256, cas_key,
                        visibility_scope, owner_org_unit_id, owner_workspace_id,
                        item_type, metadata_jsonb
                    ) VALUES (
                        :id, :resource_id, :uri, :title, :description,
                        'template', 'ORCIA', :version, :sha256, :cas_key,
                        'PUBLISHED_ORG', :owner_org_unit_id, NULL,
                        'HELP_ARTICLE', CAST(:metadata_jsonb AS jsonb)
                    )
                    ON CONFLICT (resource_id) WHERE pack_bundle_id IS NULL DO UPDATE
                    SET title = EXCLUDED.title,
                        version = EXCLUDED.version,
                        sha256 = EXCLUDED.sha256,
                        cas_key = EXCLUDED.cas_key,
                        metadata_jsonb = EXCLUDED.metadata_jsonb
                    """
                ),
                {
                    "id": UUID(str(uuid7())),
                    "resource_id": res_id,
                    "uri": uri,
                    "title": title,
                    "description": f"HelpArticle ({lang_code}) — REFERENCE",
                    "version": version,
                    "sha256": sha,
                    "cas_key": f"cas/{sha}",
                    "owner_org_unit_id": root_org_id,
                    "metadata_jsonb": json.dumps(meta),
                },
            )
