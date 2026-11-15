"""PostgreSQL 18 persistence mutations for Workspace Datasources (`Story 18.1`).

Create, update, delete, and manual sync triggering with zero circular dependencies.
"""

from __future__ import annotations

from typing import cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

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
from orcia_core.rag.errors import NoActiveEmbeddingModelError


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
    """Create a new workspace datasource and evaluate its sync health."""
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
    try:
        wid_uuid = UUID(workspace_id.strip())
        ds_uuid = UUID(datasource_id.strip())
    except (ValueError, AttributeError):
        raise ResourceNotFoundError(instance=instance) from None

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

        next_alias = alias.strip() if alias and alias.strip() else str(current[2])
        next_uri = uri.strip() if uri and uri.strip() else str(current[4])
        next_cid_str = _opt(connector_id, 5)
        next_cid = UUID(next_cid_str) if next_cid_str else None
        next_mode = sync_identity_mode or cast(SyncIdentityMode, str(current[6]))
        next_sa = _opt(service_account_id, 7)
        next_ref = _opt(referent_user_id, 8)
        next_nature = source_nature or cast(SourceNature, str(current[10] or "DOCUMENT_KB"))
        next_sync_mode = sync_mode or cast(SourceSyncMode, str(current[11] or "POLLING_24H"))
        next_target_scope = _opt(target_scope, 12)
        next_target_ref = _opt(target_ref, 13)
        next_cg_enabled = codegraph_enabled if codegraph_enabled is not None else bool(current[18])
        next_cg_auth = codegraph_auth_mode or cast(
            CodegraphAuthMode, str(current[19] or "SERVICE_ACCOUNT")
        )
        next_cg_owner = _opt(codegraph_owner_user_id, 20)

        row = (
            await conn.execute(
                sa.text(
                    f"""
                    UPDATE workspace_datasources
                    SET alias = :alias,
                        uri = :uri,
                        connector_id = :cid,
                        sync_identity_mode = :mode,
                        service_account_id = :sa_id,
                        referent_user_id = :ref_id,
                        source_nature = :nature,
                        sync_mode = :sync_mode,
                        target_scope = :target_scope,
                        target_ref = :target_ref,
                        codegraph_enabled = :cg_enabled,
                        codegraph_auth_mode = :cg_auth,
                        codegraph_owner_user_id = :cg_owner
                    WHERE id = :ds_id AND workspace_id = :wid
                    RETURNING {_RETURNING_COLS}
                    """
                ),
                {
                    "alias": next_alias,
                    "uri": next_uri,
                    "cid": next_cid,
                    "mode": next_mode,
                    "sa_id": next_sa,
                    "ref_id": next_ref,
                    "nature": next_nature,
                    "sync_mode": next_sync_mode,
                    "target_scope": next_target_scope,
                    "target_ref": next_target_ref,
                    "cg_enabled": next_cg_enabled,
                    "cg_auth": next_cg_auth,
                    "cg_owner": next_cg_owner,
                    "ds_id": ds_uuid,
                    "wid": wid_uuid,
                },
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
    try:
        wid_uuid = UUID(workspace_id.strip())
        ds_uuid = UUID(datasource_id.strip())
    except (ValueError, AttributeError):
        raise ResourceNotFoundError(instance=instance) from None

    async with engine.begin() as conn:
        await ensure_workspace_datasources_schema(conn)
        deleted = (
            await conn.execute(
                sa.text(
                    """
                    DELETE FROM workspace_datasources
                    WHERE id = :ds_id AND workspace_id = :wid
                    RETURNING id
                    """
                ),
                {"ds_id": ds_uuid, "wid": wid_uuid},
            )
        ).scalar()
        if deleted is None:
            raise ResourceNotFoundError(instance=instance)


async def trigger_workspace_datasource_sync_on_postgres18(
    engine: AsyncEngine,
    *,
    workspace_id: str,
    datasource_id: str,
    instance: str | None = None,
) -> WorkspaceDatasourceRecord:
    """Trigger manual sync: update last_sync_at, freshness_status and codegraph status."""
    try:
        wid_uuid = UUID(workspace_id.strip())
        ds_uuid = UUID(datasource_id.strip())
    except (ValueError, AttributeError):
        raise ResourceNotFoundError(instance=instance) from None

    no_model_needed = False
    record: WorkspaceDatasourceRecord | None = None

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

        current_nature = str(current[10] or "DOCUMENT_KB")
        if current_nature != "SOURCE_CODE":
            active_model = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT id FROM workspace_llm_tier_mappings
                        WHERE usage = 'embedding' AND is_active = TRUE AND scope_level = 'GLOBAL'
                        LIMIT 1;
                        """
                    )
                )
            ).fetchone()
            if active_model is None:
                await conn.execute(
                    sa.text(
                        """
                        UPDATE workspace_datasources
                        SET freshness_status = 'AWAITING_EMBEDDING_MODEL'
                        WHERE id = :ds_id AND workspace_id = :wid
                        """
                    ),
                    {"ds_id": ds_uuid, "wid": wid_uuid},
                )
                no_model_needed = True

        if not no_model_needed:
            row = (
                await conn.execute(
                    sa.text(
                        f"""
                        UPDATE workspace_datasources
                        SET last_sync_at = NOW(),
                            freshness_status = 'SYNCED',
                            codegraph_status = CASE
                                WHEN codegraph_enabled
                                    AND codegraph_status != 'PAUSED_REFERENT_RENEWAL_REQUIRED'
                                THEN 'READY'
                                ELSE codegraph_status
                            END,
                            codegraph_last_indexed_at = CASE
                                WHEN codegraph_enabled THEN NOW()
                                ELSE codegraph_last_indexed_at
                            END
                        WHERE id = :ds_id AND workspace_id = :wid
                        RETURNING {_RETURNING_COLS}
                        """
                    ),
                    {"ds_id": ds_uuid, "wid": wid_uuid},
                )
            ).fetchone()
            assert row is not None
            record = await build_datasource_record_from_conn(conn, row, wid_uuid)

    if no_model_needed:
        # Transaction committed above before raising domain error
        # TODO(19-7-reindexation-bloquante-idempotente-suivi-progression-et-verrouillage-assistant): # noqa: E501
        # Déclencher la réindexation globale bloquante des sources en attente.
        raise NoActiveEmbeddingModelError(
            detail_override=(
                "Aucun modèle d'embedding actif configuré au niveau GLOBAL. "
                "Ingestion documentaire bloquée."
            )
        )

    assert record is not None
    return record
