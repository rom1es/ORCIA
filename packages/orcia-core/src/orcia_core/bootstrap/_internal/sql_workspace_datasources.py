"""PostgreSQL 18 persistence adapter for Workspace Datasources (Story 17.4).

Provides:
- List workspace datasources with deterministic health evaluation (`ACTIVE` vs
  `PAUSED_REFERENT_RENEWAL_REQUIRED`);
- Create workspace datasource with `SERVICE_ACCOUNT` or `TEAM_REFERENT_USER` identity mode;
- Update workspace datasource (e.g. referent renewal / switch sync identity mode);
- DDL helper `ensure_workspace_datasources_schema` for non-Alembic fast-path test environments.
"""

from __future__ import annotations

from typing import cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.bootstrap._internal.sql_iam_account_helpers import (
    ensure_iam_accounts_schema,
    load_accounts_from_conn,
    parse_str_list,
)
from orcia_core.kernel import new_uuid7_str
from orcia_core.permissions.enterprise_connectors import (
    SyncIdentityMode,
    WorkspaceDatasourceRecord,
    evaluate_datasource_sync_health,
)
from orcia_core.permissions.errors import (
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.permissions.models import OrgUnitNode, OrgUnitType


async def ensure_workspace_datasources_schema(conn: AsyncConnection) -> None:
    """Ensure `workspace_datasources` table exists and has Story 17.4 columns."""
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
                UNIQUE (workspace_id, alias)
            );
            """
        )
    )
    # Check if columns added by migration exist, if table already existed without them
    await conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'workspace_datasources' AND column_name = 'connector_id'
                ) THEN
                    ALTER TABLE workspace_datasources
                        ADD COLUMN connector_id UUID NULL
                            REFERENCES enterprise_connectors(id) ON DELETE SET NULL,
                        ADD COLUMN sync_identity_mode VARCHAR(32) NOT NULL
                            DEFAULT 'SERVICE_ACCOUNT',
                        ADD COLUMN service_account_id VARCHAR(128) NULL,
                        ADD COLUMN referent_user_id VARCHAR(128) NULL;
                END IF;
            END $$;
            """
        )
    )


async def _resolve_workspace_context(
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


async def list_workspace_datasources_from_postgres18(
    engine: AsyncEngine,
    *,
    workspace_id: str,
) -> list[WorkspaceDatasourceRecord]:
    """List datasources of a workspace with dynamically evaluated sync health."""
    wid_uuid = UUID(workspace_id)
    async with engine.begin() as conn:
        await ensure_workspace_datasources_schema(conn)
        await ensure_iam_accounts_schema(conn)
        owner_org_unit, active_token_pairs = await _resolve_workspace_context(conn, wid_uuid)
        accounts = await load_accounts_from_conn(conn)

        rows = (
            await conn.execute(
                sa.text(
                    """
                    SELECT id, workspace_id, alias, scheme, uri,
                           connector_id, sync_identity_mode, service_account_id,
                           referent_user_id, created_at
                    FROM workspace_datasources
                    WHERE workspace_id = :wid
                    ORDER BY created_at ASC, alias ASC
                    """
                ),
                {"wid": wid_uuid},
            )
        ).fetchall()

        records: list[WorkspaceDatasourceRecord] = []
        for r in rows:
            cid_str = str(r[5]) if r[5] is not None else None
            mode = cast(SyncIdentityMode, str(r[6] or "SERVICE_ACCOUNT"))
            sa_id = str(r[7]) if r[7] else None
            ref_id = str(r[8]) if r[8] else None

            status, reason = evaluate_datasource_sync_health(
                sync_identity_mode=mode,
                referent_user_id=ref_id,
                connector_id=cid_str,
                owner_org_unit=owner_org_unit,
                iam_accounts=accounts,
                active_token_pairs=active_token_pairs,
            )

            records.append(
                WorkspaceDatasourceRecord(
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
                )
            )
        return records


async def create_workspace_datasource_on_postgres18(
    engine: AsyncEngine,
    *,
    workspace_id: str,
    alias: str,
    scheme: str,
    uri: str,
    connector_id: str | None = None,
    sync_identity_mode: SyncIdentityMode = "SERVICE_ACCOUNT",
    service_account_id: str | None = None,
    referent_user_id: str | None = None,
    instance: str | None = None,
) -> WorkspaceDatasourceRecord:
    """Create a new workspace datasource and evaluate its sync health."""
    cleaned_alias = alias.strip()
    cleaned_uri = uri.strip()
    if not cleaned_alias or not cleaned_uri:
        raise ValidationDomainError(
            detail_override="Alias and URI are required for datasource.",
            instance=instance,
        )

    wid_uuid = UUID(workspace_id)
    cid_uuid = UUID(connector_id) if connector_id else None
    ds_id = new_uuid7_str()

    async with engine.begin() as conn:
        await ensure_workspace_datasources_schema(conn)
        await ensure_iam_accounts_schema(conn)

        # Check workspace exists
        ws_exists = (
            await conn.execute(
                sa.text("SELECT id FROM workspaces WHERE id = :wid"),
                {"wid": wid_uuid},
            )
        ).scalar()
        if ws_exists is None:
            raise ResourceNotFoundError(instance=instance)

        row = (
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO workspace_datasources (
                        id, workspace_id, alias, scheme, uri, role,
                        connector_id, sync_identity_mode, service_account_id,
                        referent_user_id, created_at
                    )
                    VALUES (
                        :id, :wid, :alias, :scheme, :uri, 'read_only_corpus',
                        :cid, :mode, :sa_id,
                        :ref_id, NOW()
                    )
                    RETURNING id, workspace_id, alias, scheme, uri,
                              connector_id, sync_identity_mode, service_account_id,
                              referent_user_id, created_at
                    """
                ),
                {
                    "id": UUID(ds_id),
                    "wid": wid_uuid,
                    "alias": cleaned_alias,
                    "scheme": scheme.strip().lower(),
                    "uri": cleaned_uri,
                    "cid": cid_uuid,
                    "mode": sync_identity_mode,
                    "sa_id": service_account_id.strip() if service_account_id else None,
                    "ref_id": referent_user_id.strip() if referent_user_id else None,
                },
            )
        ).fetchone()
        assert row is not None

        owner_org_unit, active_token_pairs = await _resolve_workspace_context(conn, wid_uuid)
        accounts = await load_accounts_from_conn(conn)

        status, reason = evaluate_datasource_sync_health(
            sync_identity_mode=sync_identity_mode,
            referent_user_id=referent_user_id,
            connector_id=connector_id,
            owner_org_unit=owner_org_unit,
            iam_accounts=accounts,
            active_token_pairs=active_token_pairs,
        )

        return WorkspaceDatasourceRecord(
            id=str(row[0]),
            workspace_id=str(row[1]),
            alias=str(row[2]),
            scheme=str(row[3]),
            uri=str(row[4]),
            connector_id=str(row[5]) if row[5] is not None else None,
            sync_identity_mode=sync_identity_mode,
            service_account_id=str(row[7]) if row[7] else None,
            referent_user_id=str(row[8]) if row[8] else None,
            sync_status=status,
            sync_status_reason=reason,
            created_at_iso=row[9].isoformat() if row[9] else "",
        )


async def update_workspace_datasource_on_postgres18(
    engine: AsyncEngine,
    *,
    workspace_id: str,
    datasource_id: str,
    alias: str | None = None,
    uri: str | None = None,
    connector_id: str | None = None,
    sync_identity_mode: SyncIdentityMode | None = None,
    service_account_id: str | None = None,
    referent_user_id: str | None = None,
    instance: str | None = None,
) -> WorkspaceDatasourceRecord:
    """Update workspace datasource (renew referent, change sync mode) and evaluate health."""
    wid_uuid = UUID(workspace_id)
    ds_uuid = UUID(datasource_id)

    async with engine.begin() as conn:
        await ensure_workspace_datasources_schema(conn)
        await ensure_iam_accounts_schema(conn)

        current = (
            await conn.execute(
                sa.text(
                    """
                    SELECT id, workspace_id, alias, scheme, uri,
                           connector_id, sync_identity_mode, service_account_id,
                           referent_user_id, created_at
                    FROM workspace_datasources
                    WHERE id = :ds_id AND workspace_id = :wid
                    FOR UPDATE
                    """
                ),
                {"ds_id": ds_uuid, "wid": wid_uuid},
            )
        ).fetchone()
        if current is None:
            raise ResourceNotFoundError(instance=instance)

        next_alias = alias.strip() if alias and alias.strip() else str(current[2])
        next_uri = uri.strip() if uri and uri.strip() else str(current[4])
        next_cid_str = (
            connector_id.strip()
            if connector_id is not None
            else (str(current[5]) if current[5] is not None else None)
        )
        next_cid = UUID(next_cid_str) if next_cid_str else None
        next_mode = (
            sync_identity_mode
            if sync_identity_mode is not None
            else cast(SyncIdentityMode, str(current[6]))
        )
        next_sa = (
            service_account_id.strip()
            if service_account_id is not None
            else (str(current[7]) if current[7] else None)
        )
        next_ref = (
            referent_user_id.strip()
            if referent_user_id is not None
            else (str(current[8]) if current[8] else None)
        )

        row = (
            await conn.execute(
                sa.text(
                    """
                    UPDATE workspace_datasources
                    SET alias = :alias,
                        uri = :uri,
                        connector_id = :cid,
                        sync_identity_mode = :mode,
                        service_account_id = :sa_id,
                        referent_user_id = :ref_id
                    WHERE id = :ds_id AND workspace_id = :wid
                    RETURNING id, workspace_id, alias, scheme, uri,
                              connector_id, sync_identity_mode, service_account_id,
                              referent_user_id, created_at
                    """
                ),
                {
                    "alias": next_alias,
                    "uri": next_uri,
                    "cid": next_cid,
                    "mode": next_mode,
                    "sa_id": next_sa,
                    "ref_id": next_ref,
                    "ds_id": ds_uuid,
                    "wid": wid_uuid,
                },
            )
        ).fetchone()
        assert row is not None

        owner_org_unit, active_token_pairs = await _resolve_workspace_context(conn, wid_uuid)
        accounts = await load_accounts_from_conn(conn)

        status, reason = evaluate_datasource_sync_health(
            sync_identity_mode=next_mode,
            referent_user_id=next_ref,
            connector_id=next_cid_str,
            owner_org_unit=owner_org_unit,
            iam_accounts=accounts,
            active_token_pairs=active_token_pairs,
        )

        return WorkspaceDatasourceRecord(
            id=str(row[0]),
            workspace_id=str(row[1]),
            alias=str(row[2]),
            scheme=str(row[3]),
            uri=str(row[4]),
            connector_id=str(row[5]) if row[5] is not None else None,
            sync_identity_mode=next_mode,
            service_account_id=str(row[7]) if row[7] else None,
            referent_user_id=str(row[8]) if row[8] else None,
            sync_status=status,
            sync_status_reason=reason,
            created_at_iso=row[9].isoformat() if row[9] else "",
        )
