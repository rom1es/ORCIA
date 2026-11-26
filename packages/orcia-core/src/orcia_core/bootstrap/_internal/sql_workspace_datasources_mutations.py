"""PostgreSQL 18 persistence mutations for Workspace Datasources (`Story 18.1`, `Story 25.5`).

Create, update, delete with active embedding guard for RAG sources (`AD-24`).
"""

from __future__ import annotations

from typing import cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.bootstrap._internal._sql_workspace_datasources_sync import (
    assert_active_global_embedding_model_for_rag_source,
    trigger_workspace_datasource_sync_on_postgres18,
)
from orcia_core.bootstrap._internal.sql_iam_account_helpers import (
    ensure_iam_accounts_schema,
)
from orcia_core.bootstrap._internal.sql_workspace_datasources_queries import (
    _RETURNING_COLS,
    _SELECT_DATASOURCES_SQL,
    build_datasource_record_from_conn,
    ensure_workspace_datasources_schema,
)
from orcia_core.kernel import new_uuid7_str
from orcia_core.permissions.errors import (
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.permissions.workspace_sources_governance import (
    CodegraphAuthMode,
    SourceNature,
    SourceSyncMode,
    SyncIdentityMode,
    WorkspaceDatasourceRecord,
    infer_source_nature_from_scheme,
)
from orcia_core.storage.run_lock_guard import assert_resource_not_pinned_by_active_runs_conn


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
    source_nature: SourceNature | None = None,
    sync_mode: SourceSyncMode = "POLLING_24H",
    target_scope: str | None = None,
    target_ref: str | None = None,
    codegraph_enabled: bool = False,
    codegraph_auth_mode: CodegraphAuthMode = "SERVICE_ACCOUNT",
    codegraph_owner_user_id: str | None = None,
    instance: str | None = None,
) -> WorkspaceDatasourceRecord:
    """Create a new workspace datasource; reject RAG sources if no GLOBAL embedding is active."""
    cleaned_alias = alias.strip()
    cleaned_uri = uri.strip()
    if not cleaned_alias or not cleaned_uri:
        raise ValidationDomainError(
            detail_override="Alias and URI are required for datasource.",
            instance=instance,
        )

    resolved_nature = (
        source_nature if source_nature is not None else infer_source_nature_from_scheme(scheme)
    )

    try:
        wid_uuid = UUID(workspace_id.strip())
        cid_uuid = UUID(connector_id.strip()) if connector_id else None
    except (ValueError, AttributeError):
        raise ResourceNotFoundError(instance=instance) from None
    ds_id = new_uuid7_str()

    async with engine.begin() as conn:
        await ensure_workspace_datasources_schema(conn)
        await ensure_iam_accounts_schema(conn)

        ws_exists = (
            await conn.execute(
                sa.text("SELECT id FROM workspaces WHERE id = :wid"),
                {"wid": wid_uuid},
            )
        ).scalar()
        if ws_exists is None:
            raise ResourceNotFoundError(instance=instance)

        await assert_active_global_embedding_model_for_rag_source(
            conn,
            source_nature=resolved_nature,
            instance=instance,
        )

        row = (
            await conn.execute(
                sa.text(
                    f"""
                    INSERT INTO workspace_datasources (
                        id, workspace_id, alias, scheme, uri, role,
                        connector_id, sync_identity_mode, service_account_id,
                        referent_user_id, source_nature, sync_mode,
                        target_scope, target_ref, codegraph_enabled,
                        codegraph_auth_mode, codegraph_owner_user_id,
                        codegraph_status, created_at
                    )
                    VALUES (
                        :id, :wid, :alias, :scheme, :uri, 'read_only_corpus',
                        :cid, :mode, :sa_id, :ref_id, :nature, :sync_mode,
                        :target_scope, :target_ref, :cg_enabled, :cg_auth,
                        :cg_owner, 'DISABLED', NOW()
                    )
                    RETURNING {_RETURNING_COLS}
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
                    "nature": resolved_nature,
                    "sync_mode": sync_mode,
                    "target_scope": target_scope.strip() if target_scope else None,
                    "target_ref": target_ref.strip() if target_ref else None,
                    "cg_enabled": codegraph_enabled,
                    "cg_auth": codegraph_auth_mode,
                    "cg_owner": (
                        codegraph_owner_user_id.strip() if codegraph_owner_user_id else None
                    ),
                },
            )
        ).fetchone()
        assert row is not None

        return await build_datasource_record_from_conn(conn, row, wid_uuid)


def _parse_wid_ds_uuids(
    workspace_id: str, datasource_id: str, instance: str | None
) -> tuple[UUID, UUID]:
    try:
        return UUID(workspace_id.strip()), UUID(datasource_id.strip())
    except (ValueError, AttributeError):
        raise ResourceNotFoundError(instance=instance) from None


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
    source_nature: SourceNature | None = None,
    sync_mode: SourceSyncMode | None = None,
    target_scope: str | None = None,
    target_ref: str | None = None,
    codegraph_enabled: bool | None = None,
    codegraph_auth_mode: CodegraphAuthMode | None = None,
    codegraph_owner_user_id: str | None = None,
    instance: str | None = None,
) -> WorkspaceDatasourceRecord:
    """Update workspace datasource and re-evaluate health."""
    wid_uuid, ds_uuid = _parse_wid_ds_uuids(workspace_id, datasource_id, instance)

    async with engine.begin() as conn:
        await ensure_workspace_datasources_schema(conn)
        await ensure_iam_accounts_schema(conn)

        current = (
            await conn.execute(
                sa.text(
                    f"{_SELECT_DATASOURCES_SQL} "
                    "WHERE id = :ds_id AND workspace_id = :wid FOR UPDATE"
                ),
                {"ds_id": ds_uuid, "wid": wid_uuid},
            )
        ).fetchone()
        if current is None:
            raise ResourceNotFoundError(instance=instance)

        def _opt(v: str | None, idx: int) -> str | None:
            return v.strip() if v is not None else (str(current[idx]) if current[idx] else None)

        next_cid_str = _opt(connector_id, 5)
        prev_nature = str(current[10] or "DOCUMENT_KB")
        next_nature = source_nature or cast(SourceNature, prev_nature)
        if next_nature != "SOURCE_CODE" and next_nature != prev_nature:
            await assert_active_global_embedding_model_for_rag_source(
                conn, source_nature=next_nature, instance=instance
            )

        params = {
            "alias": alias.strip() if alias and alias.strip() else str(current[2]),
            "uri": uri.strip() if uri and uri.strip() else str(current[4]),
            "cid": UUID(next_cid_str) if next_cid_str else None,
            "mode": sync_identity_mode or cast(SyncIdentityMode, str(current[6])),
            "sa_id": _opt(service_account_id, 7),
            "ref_id": _opt(referent_user_id, 8),
            "nature": next_nature,
            "sync_mode": sync_mode or cast(SourceSyncMode, str(current[11] or "POLLING_24H")),
            "target_scope": _opt(target_scope, 12),
            "target_ref": _opt(target_ref, 13),
            "cg_enabled": codegraph_enabled if codegraph_enabled is not None else bool(current[18]),
            "cg_auth": codegraph_auth_mode
            or cast(CodegraphAuthMode, str(current[19] or "SERVICE_ACCOUNT")),
            "cg_owner": _opt(codegraph_owner_user_id, 20),
            "ds_id": ds_uuid,
            "wid": wid_uuid,
        }
        row = (
            await conn.execute(
                sa.text(
                    f"""
                    UPDATE workspace_datasources
                    SET alias = :alias, uri = :uri, connector_id = :cid,
                        sync_identity_mode = :mode, service_account_id = :sa_id,
                        referent_user_id = :ref_id, source_nature = :nature,
                        sync_mode = :sync_mode, target_scope = :target_scope,
                        target_ref = :target_ref, codegraph_enabled = :cg_enabled,
                        codegraph_auth_mode = :cg_auth, codegraph_owner_user_id = :cg_owner
                    WHERE id = :ds_id AND workspace_id = :wid
                    RETURNING {_RETURNING_COLS}
                    """
                ),
                params,
            )
        ).fetchone()
        assert row is not None
        return await build_datasource_record_from_conn(conn, row, wid_uuid)


async def delete_workspace_datasource_on_postgres18(
    engine: AsyncEngine,
    *,
    workspace_id: str,
    datasource_id: str,
    instance: str | None = None,
) -> None:
    """Delete workspace datasource, raising ResourceNotFoundError if missing."""
    wid_uuid, ds_uuid = _parse_wid_ds_uuids(workspace_id, datasource_id, instance)
    async with engine.begin() as conn:
        await ensure_workspace_datasources_schema(conn)
        await assert_resource_not_pinned_by_active_runs_conn(
            conn,
            target_kind="WORKSPACE_DATASOURCE",
            target_id=str(ds_uuid),
            instance=instance,
        )
        deleted = (
            await conn.execute(
                sa.text(
                    "DELETE FROM workspace_datasources WHERE id = :ds_id AND workspace_id = :wid "
                    "RETURNING id"
                ),
                {"ds_id": ds_uuid, "wid": wid_uuid},
            )
        ).scalar()
        if deleted is None:
            raise ResourceNotFoundError(instance=instance)


__all__ = [
    "create_workspace_datasource_on_postgres18",
    "delete_workspace_datasource_on_postgres18",
    "trigger_workspace_datasource_sync_on_postgres18",
    "update_workspace_datasource_on_postgres18",
]
