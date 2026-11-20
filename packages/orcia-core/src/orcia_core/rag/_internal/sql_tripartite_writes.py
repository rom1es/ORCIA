"""PostgreSQL 18 write operations for `tripartite_trace_edges` and `kb_stale_alerts`."""

from __future__ import annotations

import json

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.rag._internal.sql_rag_writes import parse_uuid_or_none, workspace_exists
from orcia_core.rag.models import KbStaleAlertEntity, TripartiteTraceEdgeEntity


async def upsert_tripartite_edges_pg(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    edges: tuple[TripartiteTraceEdgeEntity, ...],
) -> tuple[TripartiteTraceEdgeEntity, ...]:
    """Persist `tripartite_trace_edges` into PostgreSQL 18 (`ON CONFLICT DO UPDATE`)."""
    if not edges:
        return ()
    persisted: list[TripartiteTraceEdgeEntity] = []
    async with session_factory() as session, session.begin():
        checked_ws: dict[str, bool] = {}
        for edge in edges:
            wid = parse_uuid_or_none(edge.workspace_id)
            if wid is None:
                continue
            if wid not in checked_ws:
                checked_ws[wid] = await workspace_exists(session, wid)
            if not checked_ws[wid]:
                continue
            eid = parse_uuid_or_none(edge.id) or new_uuid7_str()
            row_id = str(
                (
                    await session.execute(
                        sa.text(
                            """
                            INSERT INTO tripartite_trace_edges (
                                id, edge_key, workspace_id, source_uri, source_node_type,
                                target_uri, target_node_type, relation_type, jira_issue_key
                            ) VALUES (
                                CAST(:id AS uuid), :edge_key, CAST(:wid AS uuid),
                                :src_uri, :src_type, :tgt_uri, :tgt_type,
                                :rel_type, :jira_key
                            )
                            ON CONFLICT (edge_key) DO UPDATE SET
                                jira_issue_key = COALESCE(
                                    EXCLUDED.jira_issue_key,
                                    tripartite_trace_edges.jira_issue_key
                                )
                            RETURNING id::text
                            """
                        ),
                        {
                            "id": eid,
                            "edge_key": edge.edge_key[:128],
                            "wid": wid,
                            "src_uri": edge.source_uri,
                            "src_type": edge.source_node_type,
                            "tgt_uri": edge.target_uri,
                            "tgt_type": edge.target_node_type,
                            "rel_type": edge.relation_type,
                            "jira_key": edge.jira_issue_key,
                        },
                    )
                ).scalar_one()
            )
            persisted.append(
                TripartiteTraceEdgeEntity(
                    id=row_id,
                    edge_key=edge.edge_key[:128],
                    workspace_id=wid,
                    source_uri=edge.source_uri,
                    source_node_type=edge.source_node_type,
                    target_uri=edge.target_uri,
                    target_node_type=edge.target_node_type,
                    relation_type=edge.relation_type,
                    jira_issue_key=edge.jira_issue_key,
                )
            )
    return tuple(persisted)


async def upsert_kb_stale_alert_pg(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    alert: KbStaleAlertEntity,
) -> KbStaleAlertEntity | None:
    """Persist a `kb_stale_alerts` record linked to an existing `kb_documents` row."""
    wid = parse_uuid_or_none(alert.workspace_id)
    if wid is None:
        return None
    async with session_factory() as session, session.begin():
        doc_id = (
            await session.execute(
                sa.text(
                    "SELECT id::text FROM kb_documents "
                    "WHERE workspace_id = CAST(:wid AS uuid) AND doc_key = :doc_key LIMIT 1"
                ),
                {"wid": wid, "doc_key": alert.document_key[:128]},
            )
        ).scalar_one_or_none()
        if doc_id is None:
            return None
        aid = parse_uuid_or_none(alert.id) or new_uuid7_str()
        await session.execute(
            sa.text(
                """
                INSERT INTO kb_stale_alerts (
                    id, alert_key, workspace_id, document_id, alert_reason,
                    diagnostic_marker, justifying_jira_key, impacted_run_ids_jsonb, resolved
                ) VALUES (
                    CAST(:id AS uuid), :alert_key, CAST(:wid AS uuid), CAST(:doc_id AS uuid),
                    :reason, :marker, :jira_key, CAST(:runs_json AS jsonb), :resolved
                )
                ON CONFLICT (alert_key) DO UPDATE SET
                    justifying_jira_key = EXCLUDED.justifying_jira_key,
                    resolved = EXCLUDED.resolved
                """
            ),
            {
                "id": aid,
                "alert_key": alert.alert_key[:128],
                "wid": wid,
                "doc_id": str(doc_id),
                "reason": alert.alert_reason,
                "marker": alert.diagnostic_marker[:64],
                "jira_key": alert.justifying_jira_key,
                "runs_json": json.dumps(list(alert.impacted_run_ids)),
                "resolved": bool(alert.resolved),
            },
        )
        return alert
