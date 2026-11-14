"""PostgreSQL 18 persistence queries for Workspace Datasources (`Story 18.1`).

Queries and context resolution with zero circular dependencies and zero forbidden domain keywords.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.bootstrap._internal.sql_iam_account_helpers import (
    ensure_iam_accounts_schema,
    load_accounts_from_conn,
    parse_str_list,
)
from orcia_core.permissions.errors import ResourceNotFoundError
from orcia_core.permissions.models import OrgUnitNode, OrgUnitType
from orcia_core.permissions.workspace_sources_governance import (
    CodegraphAuthMode,
    CodegraphStatus,
    SourceFreshnessStatus,
    SourceNature,
    SourceSyncMode,
    SyncIdentityMode,
    WorkspaceDatasourceRecord,
    evaluate_codegraph_governance_health,
    evaluate_datasource_sync_health,
)


async def ensure_workspace_datasources_schema(conn: AsyncConnection) -> None:
    """Ensure `workspace_datasources` table exists and has Story 18.1 columns."""
    await conn.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS workspace_datasources (
                id UUID PRIMARY KEY,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                alias VARCHAR(128) NOT NULL,
                scheme VARCHAR(32) NOT NULL,
                uri TEXT NOT NULL,
                role VARCHAR(64) NOT NULL DEFAULT 'read_only_corpus',
                execution_identity VARCHAR(32) NOT NULL DEFAULT 'passthrough',
                freshness_ttl_days INT NOT NULL DEFAULT 30,
                connector_id UUID NULL REFERENCES enterprise_connectors(id) ON DELETE SET NULL,
                sync_identity_mode VARCHAR(32) NOT NULL DEFAULT 'SERVICE_ACCOUNT',
                service_account_id VARCHAR(128) NULL,
                referent_user_id VARCHAR(128) NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                source_nature VARCHAR(32) NOT NULL DEFAULT 'DOCUMENT_KB',
                sync_mode VARCHAR(32) NOT NULL DEFAULT 'POLLING_24H',
                target_scope VARCHAR(255) NULL,
                target_ref VARCHAR(128) NULL,
                last_sync_at TIMESTAMPTZ NULL,
                last_probe_at TIMESTAMPTZ NULL,
                fingerprint_hash VARCHAR(64) NULL,
                freshness_status VARCHAR(32) NOT NULL DEFAULT 'PENDING_INITIAL_SYNC',
                codegraph_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                codegraph_auth_mode VARCHAR(32) NOT NULL DEFAULT 'SERVICE_ACCOUNT',
                codegraph_owner_user_id VARCHAR(128) NULL,
                codegraph_status VARCHAR(40) NOT NULL DEFAULT 'DISABLED',
                codegraph_last_indexed_at TIMESTAMPTZ NULL,
                codegraph_head_sha VARCHAR(64) NULL,
                UNIQUE (workspace_id, alias)
            );
            """
        )
    )
    await conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'workspace_datasources' AND column_name = 'source_nature'
                ) THEN
                    ALTER TABLE workspace_datasources
                        ADD COLUMN source_nature VARCHAR(32) NOT NULL DEFAULT 'DOCUMENT_KB',
                        ADD COLUMN sync_mode VARCHAR(32) NOT NULL DEFAULT 'POLLING_24H',
                        ADD COLUMN target_scope VARCHAR(255) NULL,
                        ADD COLUMN target_ref VARCHAR(128) NULL,
                        ADD COLUMN last_sync_at TIMESTAMPTZ NULL,
                        ADD COLUMN last_probe_at TIMESTAMPTZ NULL,
                        ADD COLUMN fingerprint_hash VARCHAR(64) NULL,
                        ADD COLUMN freshness_status VARCHAR(32)
                            NOT NULL DEFAULT 'PENDING_INITIAL_SYNC',
                        ADD COLUMN codegraph_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                        ADD COLUMN codegraph_auth_mode VARCHAR(32)
                            NOT NULL DEFAULT 'SERVICE_ACCOUNT',
                        ADD COLUMN codegraph_owner_user_id VARCHAR(128) NULL,
                        ADD COLUMN codegraph_status VARCHAR(40) NOT NULL DEFAULT 'DISABLED',
                        ADD COLUMN codegraph_last_indexed_at TIMESTAMPTZ NULL,
                        ADD COLUMN codegraph_head_sha VARCHAR(64) NULL;
                END IF;
            END $$;
            """
        )
    )


async def resolve_workspace_context(
    conn: AsyncConnection,
    workspace_id_uuid: UUID,
) -> tuple[OrgUnitNode | None, set[tuple[str, str]]]:
    """Load owner OrgUnitNode and active passthrough token pairs for health evaluation."""
    ws_row = (
        await conn.execute(
            sa.text("SELECT owner_org_unit_id FROM workspaces WHERE id = :wid"),
            {"wid": workspace_id_uuid},
        )
    ).fetchone()

    owner_org_unit: OrgUnitNode | None = None
    if ws_row is not None and ws_row[0] is not None:
        ou_id = str(ws_row[0])
        ou_row = (
            await conn.execute(
                sa.text(
                    """
                    SELECT id, slug, name, unit_type, parent_id, billing_enabled,
                           lead_user_id, member_user_ids_jsonb
                    FROM org_units
                    WHERE id = :ou_id
                    """
                ),
                {"ou_id": ou_id},
            )
        ).fetchone()
        if ou_row is not None:
            raw_members = ou_row[7]
            members = tuple(parse_str_list(raw_members))
            owner_org_unit = OrgUnitNode(
                id=str(ou_row[0]),
                slug=str(ou_row[1]),
                name=str(ou_row[2]),
                unit_type=cast(OrgUnitType, str(ou_row[3]).upper()),
                parent_id=str(ou_row[4]) if ou_row[4] is not None else None,
                billing_enabled=bool(ou_row[5]),
                lead_user_id=str(ou_row[6]).strip() if ou_row[6] else None,
                member_user_ids=members,
            )

    token_rows = (
        await conn.execute(
            sa.text(
                """
                SELECT LOWER(user_id), LOWER(connector_id::text)
                FROM user_connector_passthrough_tokens
                WHERE status = 'ACTIVE'
                """
            )
        )
    ).fetchall()
    active_token_pairs = {(str(r[0]), str(r[1])) for r in token_rows}

    return owner_org_unit, active_token_pairs


def row_to_datasource_record(
    r: Sequence[Any],
    *,
    owner_org_unit: OrgUnitNode | None,
    accounts: Sequence[Any],
    active_token_pairs: set[tuple[str, str]],
) -> WorkspaceDatasourceRecord:
    """Map SQL row to WorkspaceDatasourceRecord with evaluated health statuses."""
    cid_str = str(r[5]) if r[5] is not None else None
    mode = cast(SyncIdentityMode, str(r[6] or "SERVICE_ACCOUNT"))
    sa_id = str(r[7]) if r[7] else None
    ref_id = str(r[8]) if r[8] else None

    # Cast accounts to IamAccountRecord
    from orcia_core.permissions.iam_accounts import IamAccountRecord

    typed_accounts = cast(list[IamAccountRecord], accounts)

    status, reason = evaluate_datasource_sync_health(
        sync_identity_mode=mode,
        referent_user_id=ref_id,
        connector_id=cid_str,
        owner_org_unit=owner_org_unit,
        iam_accounts=typed_accounts,
        active_token_pairs=active_token_pairs,
    )

    cg_enabled = bool(r[18])
    cg_mode = cast(CodegraphAuthMode, str(r[19] or "SERVICE_ACCOUNT"))
    cg_owner = str(r[20]) if r[20] else None
    raw_cg_status = cast(CodegraphStatus, str(r[21] or "DISABLED"))

    cg_status, cg_reason = evaluate_codegraph_governance_health(
        codegraph_enabled=cg_enabled,
        codegraph_auth_mode=cg_mode,
        codegraph_owner_user_id=cg_owner,
        connector_id=cid_str,
        owner_org_unit=owner_org_unit,
        iam_accounts=typed_accounts,
        active_token_pairs=active_token_pairs,
        current_status=raw_cg_status,
    )

    return WorkspaceDatasourceRecord(
        id=str(r[0]),
        workspace_id=str(r[1]),
        alias=str(r[2]),
        scheme=str(r[3]),
        uri=str(r[4]),
        connector_id=cid_str,
        sync_identity_mode=mode,
        service_account_id=sa_id,
        referent_user_id=ref_id,
        sync_status=status,
        sync_status_reason=reason,
        created_at_iso=r[9].isoformat() if r[9] else "",
        source_nature=cast(SourceNature, str(r[10] or "DOCUMENT_KB")),
        sync_mode=cast(SourceSyncMode, str(r[11] or "POLLING_24H")),
        target_scope=str(r[12]) if r[12] else None,
        target_ref=str(r[13]) if r[13] else None,
        last_sync_at_iso=r[14].isoformat() if r[14] else None,
        last_probe_at_iso=r[15].isoformat() if r[15] else None,
        fingerprint_hash=str(r[16]) if r[16] else None,
        freshness_status=cast(SourceFreshnessStatus, str(r[17] or "PENDING_INITIAL_SYNC")),
        codegraph_enabled=cg_enabled,
        codegraph_auth_mode=cg_mode,
        codegraph_owner_user_id=cg_owner,
        codegraph_status=cg_status,
        codegraph_status_reason=cg_reason,
        codegraph_last_indexed_at_iso=r[22].isoformat() if r[22] else None,
        codegraph_head_sha=str(r[23]) if r[23] else None,
    )


_RETURNING_COLS = """
id, workspace_id, alias, scheme, uri,
connector_id, sync_identity_mode, service_account_id,
referent_user_id, created_at,
source_nature, sync_mode, target_scope, target_ref,
last_sync_at, last_probe_at, fingerprint_hash,
freshness_status, codegraph_enabled, codegraph_auth_mode,
codegraph_owner_user_id, codegraph_status,
codegraph_last_indexed_at, codegraph_head_sha
"""

_SELECT_DATASOURCES_SQL = f"SELECT {_RETURNING_COLS} FROM workspace_datasources"


async def build_datasource_record_from_conn(
    conn: AsyncConnection,
    row: tuple[object, ...],
    wid_uuid: UUID,
) -> WorkspaceDatasourceRecord:
    """Helper to resolve workspace context and map row to WorkspaceDatasourceRecord."""
    owner_org_unit, active_token_pairs = await resolve_workspace_context(conn, wid_uuid)
    accounts = await load_accounts_from_conn(conn)
    return row_to_datasource_record(
        row,
        owner_org_unit=owner_org_unit,
        accounts=accounts,
        active_token_pairs=active_token_pairs,
    )


async def list_workspace_datasources_from_postgres18(
    engine: AsyncEngine,
    *,
    workspace_id: str,
) -> list[WorkspaceDatasourceRecord]:
    """List datasources of a workspace with dynamically evaluated sync & codegraph health."""
    wid_uuid = UUID(workspace_id)
    async with engine.begin() as conn:
        await ensure_workspace_datasources_schema(conn)
        await ensure_iam_accounts_schema(conn)
        owner_org_unit, active_token_pairs = await resolve_workspace_context(conn, wid_uuid)
        accounts = await load_accounts_from_conn(conn)

        rows = (
            await conn.execute(
                sa.text(
                    f"{_SELECT_DATASOURCES_SQL} "
                    "WHERE workspace_id = :wid ORDER BY created_at ASC, alias ASC"
                ),
                {"wid": wid_uuid},
            )
        ).fetchall()

        return [
            row_to_datasource_record(
                r,
                owner_org_unit=owner_org_unit,
                accounts=accounts,
                active_token_pairs=active_token_pairs,
            )
            for r in rows
        ]


async def get_workspace_datasource_from_postgres18(
    engine: AsyncEngine,
    *,
    workspace_id: str,
    datasource_id: str,
    instance: str | None = None,
) -> WorkspaceDatasourceRecord:
    """Fetch single workspace datasource by id with evaluated health."""
    wid_uuid = UUID(workspace_id)
    ds_uuid = UUID(datasource_id)
    async with engine.begin() as conn:
        await ensure_workspace_datasources_schema(conn)
        await ensure_iam_accounts_schema(conn)
        row = (
            await conn.execute(
                sa.text(f"{_SELECT_DATASOURCES_SQL} WHERE id = :ds_id AND workspace_id = :wid"),
                {"ds_id": ds_uuid, "wid": wid_uuid},
            )
        ).fetchone()
        if row is None:
            raise ResourceNotFoundError(instance=instance)

        return await build_datasource_record_from_conn(conn, row, wid_uuid)
