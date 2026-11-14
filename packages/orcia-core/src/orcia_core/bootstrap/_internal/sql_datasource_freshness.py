"""PostgreSQL 18 persistence for Datasource Webhooks, Freshness & Codegraph (`Story 18.2`).

Idempotent webhook deliveries, transactional Outbox publication, and secure token resolution.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.kernel.events import DomainEvent
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.enterprise_connectors_crypto import (
    extract_url_host,
    unpack_encrypted_secret,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DatasourceWebhookContext:
    """Read-only context required to verify and process incoming datasource webhooks."""

    datasource_id: str
    workspace_id: str
    alias: str
    source_nature: str
    target_ref: str | None
    target_scope: str | None
    fingerprint_hash: str | None
    freshness_status: str
    connector_id: str | None
    connector_base_url: str | None
    connector_scheme: str | None
    webhook_secret_encrypted: str | None
    codegraph_enabled: bool
    codegraph_auth_mode: str
    codegraph_owner_user_id: str | None
    codegraph_status: str


async def get_datasource_webhook_context_from_postgres18(
    engine: AsyncEngine,
    *,
    datasource_id: str,
) -> DatasourceWebhookContext | None:
    """Fetch webhook verification context for a workspace datasource."""
    stmt = sa.text(
        """
        SELECT
            ds.id,
            ds.workspace_id,
            ds.alias,
            ds.source_nature,
            ds.target_ref,
            ds.target_scope,
            ds.fingerprint_hash,
            ds.freshness_status,
            ds.connector_id,
            ec.base_url,
            COALESCE(ec.connector_kind, ds.scheme) AS scheme,
            ec.webhook_secret_encrypted,
            ds.codegraph_enabled,
            ds.codegraph_auth_mode,
            ds.codegraph_owner_user_id,
            ds.codegraph_status
        FROM workspace_datasources ds
        LEFT JOIN enterprise_connectors ec ON ec.id = ds.connector_id
        WHERE ds.id = CAST(:datasource_id AS uuid);
        """
    )
    async with engine.connect() as conn:
        res = await conn.execute(stmt, {"datasource_id": datasource_id})
        row = res.fetchone()
        if row is None:
            return None
        return DatasourceWebhookContext(
            datasource_id=str(row[0]),
            workspace_id=str(row[1]),
            alias=str(row[2]),
            source_nature=str(row[3] or "DOCUMENT_KB"),
            target_ref=str(row[4]) if row[4] else None,
            target_scope=str(row[5]) if row[5] else None,
            fingerprint_hash=str(row[6]) if row[6] else None,
            freshness_status=str(row[7] or "PENDING_INITIAL_SYNC"),
            connector_id=str(row[8]) if row[8] else None,
            connector_base_url=str(row[9]) if row[9] else None,
            connector_scheme=str(row[10]) if row[10] else None,
            webhook_secret_encrypted=str(row[11]) if row[11] else None,
            codegraph_enabled=bool(row[12]),
            codegraph_auth_mode=str(row[13] or "SERVICE_ACCOUNT"),
            codegraph_owner_user_id=str(row[14]) if row[14] else None,
            codegraph_status=str(row[15] or "DISABLED"),
        )


async def record_webhook_delivery_and_outbox(
    engine: AsyncEngine,
    *,
    delivery_id: str,
    workspace_id: str,
    datasource_id: str,
    delivery_key: str,
    provider_event: str,
    remote_fingerprint_sha256: str,
    reconcile_outcome: str,
    outbox_event: DomainEvent | None = None,
) -> bool:
    """Atomically record webhook delivery and publish Outbox event.

    Returns:
        True if delivery was newly inserted.
        False if delivery_key was already processed (idempotent no-op).
    """
    insert_delivery_sql = sa.text(
        """
        INSERT INTO datasource_webhook_deliveries (
            id, workspace_id, datasource_id, delivery_key,
            provider_event, remote_fingerprint_sha256, reconcile_outcome, received_at
        ) VALUES (
            CAST(:id AS uuid),
            CAST(:workspace_id AS uuid),
            CAST(:datasource_id AS uuid),
            :delivery_key,
            :provider_event,
            :remote_fingerprint_sha256,
            :reconcile_outcome,
            NOW()
        )
        ON CONFLICT (datasource_id, delivery_key) DO NOTHING
        RETURNING id;
        """
    )
    insert_outbox_sql = sa.text(
        """
        INSERT INTO domain_events_outbox (
            event_id, event_type, aggregate_type, aggregate_id,
            run_id, workspace_id, payload_jsonb, trace_id, status, attempts
        ) VALUES (
            CAST(:event_id AS uuid), :event_type, :aggregate_type, :aggregate_id,
            CAST(:run_id AS uuid), CAST(:workspace_id AS uuid),
            CAST(:payload_jsonb AS jsonb), :trace_id, :status, :attempts
        )
        ON CONFLICT (event_id) DO NOTHING;
        """
    )

    async with engine.begin() as conn:
        res = await conn.execute(
            insert_delivery_sql,
            {
                "id": delivery_id,
                "workspace_id": workspace_id,
                "datasource_id": datasource_id,
                "delivery_key": delivery_key,
                "provider_event": provider_event,
                "remote_fingerprint_sha256": remote_fingerprint_sha256,
                "reconcile_outcome": reconcile_outcome,
            },
        )
        inserted_id = res.scalar_one_or_none()
        if inserted_id is None:
            return False  # Already processed

        if outbox_event is not None:
            await conn.execute(
                insert_outbox_sql,
                {
                    "event_id": outbox_event.event_id,
                    "event_type": outbox_event.event_type,
                    "aggregate_type": outbox_event.aggregate_type,
                    "aggregate_id": outbox_event.aggregate_id,
                    "run_id": outbox_event.run_id,
                    "workspace_id": outbox_event.workspace_id,
                    "payload_jsonb": json.dumps(outbox_event.payload),
                    "trace_id": outbox_event.trace_id,
                    "status": outbox_event.status,
                    "attempts": outbox_event.attempts,
                },
            )
        return True


async def update_datasource_freshness_state(
    engine: AsyncEngine,
    *,
    datasource_id: str,
    freshness_status: str | None = None,
    fingerprint_hash: str | None = None,
    last_sync_at: datetime | None = None,
    last_probe_at: datetime | None = None,
    codegraph_status: str | None = None,
    codegraph_head_sha: str | None = None,
    codegraph_last_indexed_at: datetime | None = None,
) -> None:
    """Update freshness and codegraph governance attributes in PostgreSQL 18."""
    clauses: list[str] = []
    params: dict[str, Any] = {"datasource_id": datasource_id}

    if freshness_status is not None:
        clauses.append("freshness_status = :freshness_status")
        params["freshness_status"] = freshness_status
    if fingerprint_hash is not None:
        clauses.append("fingerprint_hash = :fingerprint_hash")
        params["fingerprint_hash"] = fingerprint_hash
    if last_sync_at is not None:
        clauses.append("last_sync_at = :last_sync_at")
        params["last_sync_at"] = last_sync_at
    if last_probe_at is not None:
        clauses.append("last_probe_at = :last_probe_at")
        params["last_probe_at"] = last_probe_at
    if codegraph_status is not None:
        clauses.append("codegraph_status = :codegraph_status")
        params["codegraph_status"] = codegraph_status
    if codegraph_head_sha is not None:
        clauses.append("codegraph_head_sha = :codegraph_head_sha")
        params["codegraph_head_sha"] = codegraph_head_sha
    if codegraph_last_indexed_at is not None:
        clauses.append("codegraph_last_indexed_at = :codegraph_last_indexed_at")
        params["codegraph_last_indexed_at"] = codegraph_last_indexed_at

    if not clauses:
        return

    query = sa.text(
        f"""
        UPDATE workspace_datasources
        SET {", ".join(clauses)}
        WHERE id = CAST(:datasource_id AS uuid);
        """
    )
    async with engine.begin() as conn:
        await conn.execute(query, params)


async def resolve_codegraph_indexer_token(
    engine: AsyncEngine,
    *,
    datasource_id: str,
    vault_cipher: PassthroughVaultCipher,
) -> tuple[str | None, str]:
    """Resolve indexing token based on codegraph_auth_mode.

    Returns:
        (token, "SERVICE_ACCOUNT") if service account secret decrypted successfully.
        (token, "WORKSPACE_LEAD_TOKEN") if referent active passthrough token decrypted.
        (None, "PAUSED_REFERENT_RENEWAL_REQUIRED") if token missing, inactive or invalid.
    """
    ctx = await get_datasource_webhook_context_from_postgres18(engine, datasource_id=datasource_id)
    if ctx is None or not ctx.connector_id:
        return None, "PAUSED_REFERENT_RENEWAL_REQUIRED"

    scheme = ctx.connector_scheme or "git"
    host = extract_url_host(ctx.connector_base_url or "")

    if ctx.codegraph_auth_mode == "SERVICE_ACCOUNT":
        stmt_sa = sa.text(
            """
            SELECT encrypted_admin_secret
            FROM enterprise_connectors
            WHERE id = CAST(:connector_id AS uuid);
            """
        )
        async with engine.connect() as conn:
            res_sa = await conn.execute(stmt_sa, {"connector_id": ctx.connector_id})
            enc_secret = res_sa.scalar_one_or_none()
        if not enc_secret:
            return None, "PAUSED_REFERENT_RENEWAL_REQUIRED"
        try:
            token = unpack_encrypted_secret(
                vault_cipher,
                owner_id=ctx.connector_id,
                packed=enc_secret,
                scheme=scheme,
                host=host,
            )
            return token, "SERVICE_ACCOUNT"
        except Exception as exc:
            logger.warning("Failed to decrypt connector admin secret: %s", exc)
            return None, "PAUSED_REFERENT_RENEWAL_REQUIRED"

    # WORKSPACE_LEAD_TOKEN
    owner_id = ctx.codegraph_owner_user_id
    if not owner_id:
        return None, "PAUSED_REFERENT_RENEWAL_REQUIRED"

    stmt_lead = sa.text(
        """
        SELECT t.encrypted_token, a.is_active
        FROM user_connector_passthrough_tokens t
        LEFT JOIN iam_accounts a ON a.id = t.user_id
        WHERE t.user_id = :user_id
          AND t.connector_id = CAST(:connector_id AS uuid)
          AND t.status = 'ACTIVE';
        """
    )
    async with engine.connect() as conn:
        res_lead = await conn.execute(
            stmt_lead,
            {"user_id": owner_id, "connector_id": ctx.connector_id},
        )
        row = res_lead.fetchone()

    if row is None or not row[0] or not row[1]:  # missing, empty token, or user inactive
        return None, "PAUSED_REFERENT_RENEWAL_REQUIRED"

    try:
        token = unpack_encrypted_secret(
            vault_cipher,
            owner_id=owner_id,
            packed=str(row[0]),
            scheme=scheme,
            host=host,
        )
        return token, "WORKSPACE_LEAD_TOKEN"
    except Exception as exc:
        logger.warning("Failed to decrypt workspace lead token: %s", exc)
        return None, "PAUSED_REFERENT_RENEWAL_REQUIRED"
