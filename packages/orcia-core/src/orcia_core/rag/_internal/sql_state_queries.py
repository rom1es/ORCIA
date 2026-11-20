"""PostgreSQL 18 read queries for KB documents, tripartite edges, and stale alerts."""

from __future__ import annotations

import json
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orcia_core.rag.models import (
    KbDocumentEntity,
    KbStaleAlertEntity,
    StaleAlertReason,
    TripartiteNodeType,
    TripartiteRelationType,
    TripartiteTraceEdgeEntity,
)


def _parse_str_tuple(raw: Any) -> tuple[str, ...]:
    if isinstance(raw, str):
        parsed = json.loads(raw) if raw else []
    elif isinstance(raw, list):
        parsed = raw
    else:
        parsed = []
    return tuple(str(x) for x in parsed)


async def query_kb_documents_pg(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    workspace_id: str | None = None,
    limit: int = 200,
) -> tuple[KbDocumentEntity, ...]:
    """List persisted `kb_documents` from PostgreSQL 18."""
    where_sql = "WHERE d.workspace_id = CAST(:workspace_id AS uuid)" if workspace_id else ""
    params: dict[str, Any] = {"limit": limit}
    if workspace_id:
        params["workspace_id"] = workspace_id
    async with session_factory() as session:
        rows = (
            (
                await session.execute(
                    sa.text(
                        f"""
                        SELECT
                            d.id::text AS id,
                            d.doc_key,
                            d.workspace_id::text AS workspace_id,
                            d.datasource_id::text AS datasource_id,
                            COALESCE(wd.alias, d.source_scheme) AS datasource_alias,
                            d.source_uri,
                            d.source_scheme,
                            d.indexing_regime,
                            d.title,
                            d.revision_tag,
                            d.content_sha256,
                            d.freshness_ttl_days,
                            d.is_stale
                        FROM kb_documents d
                        LEFT JOIN workspace_datasources wd ON wd.id = d.datasource_id
                        {where_sql}
                        ORDER BY d.created_at DESC, d.doc_key ASC
                        LIMIT :limit
                        """
                    ),
                    params,
                )
            )
            .mappings()
            .all()
        )
        return tuple(
            KbDocumentEntity(
                id=str(r["id"]),
                doc_key=str(r["doc_key"]),
                workspace_id=str(r["workspace_id"]),
                datasource_id=str(r["datasource_id"]),
                datasource_alias=str(r["datasource_alias"]),
                source_uri=str(r["source_uri"]),
                source_scheme=str(r["source_scheme"]),
                indexing_regime=str(r["indexing_regime"]),
                title=str(r["title"]),
                revision_tag=str(r["revision_tag"]),
                content_sha256=str(r["content_sha256"]),
                freshness_ttl_days=int(r["freshness_ttl_days"]),
                is_stale=bool(r["is_stale"]),
            )
            for r in rows
        )


async def query_tripartite_edges_pg(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    workspace_id: str | None = None,
    limit: int = 200,
) -> tuple[TripartiteTraceEdgeEntity, ...]:
    """List persisted `tripartite_trace_edges` from PostgreSQL 18."""
    where_sql = "WHERE workspace_id = CAST(:workspace_id AS uuid)" if workspace_id else ""
    params: dict[str, Any] = {"limit": limit}
    if workspace_id:
        params["workspace_id"] = workspace_id
    async with session_factory() as session:
        rows = (
            (
                await session.execute(
                    sa.text(
                        f"""
                        SELECT
                            id::text AS id,
                            edge_key,
                            workspace_id::text AS workspace_id,
                            source_uri,
                            source_node_type,
                            target_uri,
                            target_node_type,
                            relation_type,
                            jira_issue_key
                        FROM tripartite_trace_edges
                        {where_sql}
                        ORDER BY created_at DESC, edge_key ASC
                        LIMIT :limit
                        """
                    ),
                    params,
                )
            )
            .mappings()
            .all()
        )
        return tuple(
            TripartiteTraceEdgeEntity(
                id=str(r["id"]),
                edge_key=str(r["edge_key"]),
                workspace_id=str(r["workspace_id"]),
                source_uri=str(r["source_uri"]),
                source_node_type=cast(TripartiteNodeType, str(r["source_node_type"])),
                target_uri=str(r["target_uri"]),
                target_node_type=cast(TripartiteNodeType, str(r["target_node_type"])),
                relation_type=cast(TripartiteRelationType, str(r["relation_type"])),
                jira_issue_key=str(r["jira_issue_key"]) if r["jira_issue_key"] else None,
            )
            for r in rows
        )


async def query_kb_stale_alerts_pg(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    workspace_id: str | None = None,
    limit: int = 200,
) -> tuple[KbStaleAlertEntity, ...]:
    """List persisted `kb_stale_alerts` from PostgreSQL 18."""
    where_sql = "WHERE a.workspace_id = CAST(:workspace_id AS uuid)" if workspace_id else ""
    params: dict[str, Any] = {"limit": limit}
    if workspace_id:
        params["workspace_id"] = workspace_id
    async with session_factory() as session:
        rows = (
            (
                await session.execute(
                    sa.text(
                        f"""
                        SELECT
                            a.id::text AS id,
                            a.alert_key,
                            a.workspace_id::text AS workspace_id,
                            COALESCE(d.doc_key, a.document_id::text) AS document_key,
                            COALESCE(d.source_uri, '') AS source_uri,
                            a.alert_reason,
                            a.diagnostic_marker,
                            a.justifying_jira_key,
                            a.impacted_run_ids_jsonb,
                            a.resolved
                        FROM kb_stale_alerts a
                        LEFT JOIN kb_documents d ON d.id = a.document_id
                        {where_sql}
                        ORDER BY a.created_at DESC, a.alert_key ASC
                        LIMIT :limit
                        """
                    ),
                    params,
                )
            )
            .mappings()
            .all()
        )
        return tuple(
            KbStaleAlertEntity(
                id=str(r["id"]),
                alert_key=str(r["alert_key"]),
                workspace_id=str(r["workspace_id"]),
                document_key=str(r["document_key"]),
                source_uri=str(r["source_uri"]),
                alert_reason=cast(StaleAlertReason, str(r["alert_reason"])),
                diagnostic_marker=str(r["diagnostic_marker"]),
                justifying_jira_key=(
                    str(r["justifying_jira_key"]) if r["justifying_jira_key"] else None
                ),
                impacted_run_ids=_parse_str_tuple(r["impacted_run_ids_jsonb"]),
                resolved=bool(r["resolved"]),
            )
            for r in rows
        )
