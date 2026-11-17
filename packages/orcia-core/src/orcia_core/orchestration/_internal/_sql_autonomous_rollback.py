"""PostgreSQL 18 rollback helper for `HELP_ARTICLE` & autonomous runs (`Story 7.4`)."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._internal._sql_scope_filter import safe_uuid
from orcia_core.catalog.contextual_help import build_help_redis_cache_key
from orcia_core.orchestration._internal._sql_workflow_triggers_queries import (
    insert_outbox_and_audit,
)
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort
from orcia_kernel.events import DomainEvent
from orcia_kernel.ids import new_uuid7_str


async def restore_help_article_and_rollback_run_sql(
    engine: AsyncEngine,
    *,
    run_id: str,
    reviewer_user_id: str,
    comment: str | None,
    help_resource_id: str | None,
    contract_id: str | None,
    event: DomainEvent,
    audit_sink: AuditLedgerSinkPort | None = None,
) -> dict[str, Any] | None:
    """Rollback run to `ROLLED_BACK`, mark post-hoc invalidated & restore `HELP_ARTICLE` @v(N-1)."""
    run_uuid = safe_uuid(run_id)
    if run_uuid is None:
        return None

    async with engine.begin() as conn:
        run_row = (
            (
                await conn.execute(
                    sa.text(
                        """
                    UPDATE workflow_runs
                    SET status = 'ROLLED_BACK'
                    WHERE id = :run_id
                    RETURNING id::text AS run_id, workspace_id::text AS workspace_id, status;
                    """
                    ),
                    {"run_id": run_uuid},
                )
            )
            .mappings()
            .first()
        )
        if run_row is None:
            return None

        resolved_contract_id = contract_id
        if not resolved_contract_id:
            resolved_contract_id = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT id::text
                        FROM autonomy_contracts
                        WHERE workspace_id = CAST(:ws_id AS uuid)
                        ORDER BY (status = 'ACTIVE') DESC, signed_at DESC
                        LIMIT 1;
                        """
                    ),
                    {"ws_id": str(run_row["workspace_id"])},
                )
            ).scalar_one_or_none()

        if resolved_contract_id:
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO autonomous_post_hoc_audits (
                        id, run_id, workspace_id, contract_id, review_status,
                        reviewer_user_id, review_comment, sampled_at, reviewed_at
                    ) VALUES (
                        :id, :run_id, :ws_id, :contract_id, 'INVALIDATED_ROLLED_BACK',
                        :reviewer_id, :comment, NOW(), NOW()
                    )
                    ON CONFLICT (run_id) DO UPDATE SET
                        review_status = 'INVALIDATED_ROLLED_BACK',
                        reviewer_user_id = EXCLUDED.reviewer_user_id,
                        review_comment = EXCLUDED.review_comment,
                        reviewed_at = NOW();
                    """
                ),
                {
                    "id": UUID(new_uuid7_str()),
                    "run_id": run_uuid,
                    "ws_id": UUID(str(run_row["workspace_id"])),
                    "contract_id": UUID(resolved_contract_id),
                    "reviewer_id": safe_uuid(reviewer_user_id),
                    "comment": comment,
                },
            )

        restored_version = "1.0.0"
        invalidated_keys: list[str] = []
        target_res_id = help_resource_id
        if target_res_id is None:
            found_res = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT resource_id
                        FROM catalog_items
                        WHERE item_type = 'HELP_ARTICLE'
                          AND metadata_jsonb->>'autonomous_run_id' = :run_id_str
                        LIMIT 1;
                        """
                    ),
                    {"run_id_str": run_id},
                )
            ).scalar_one_or_none()
            if found_res:
                target_res_id = str(found_res)

        if target_res_id:
            cat_row = (
                (
                    await conn.execute(
                        sa.text(
                            """
                        SELECT resource_id, version, sha256, cas_key, metadata_jsonb
                        FROM catalog_items
                        WHERE resource_id = :res_id AND item_type = 'HELP_ARTICLE'
                        LIMIT 1;
                        """
                        ),
                        {"res_id": target_res_id},
                    )
                )
                .mappings()
                .first()
            )
            if cat_row is not None:
                meta = dict(cat_row["metadata_jsonb"] or {})
                prev_ver = str(meta.get("previous_version") or "1.0.0")
                prev_sha = str(meta.get("previous_sha256") or cat_row["sha256"])
                prev_cas = str(meta.get("previous_cas_key") or f"cas/{prev_sha}")
                meta["is_autonomous_generated"] = False
                meta.pop("autonomous_run_id", None)
                await conn.execute(
                    sa.text(
                        """
                        UPDATE catalog_items
                        SET version = :ver,
                            sha256 = :sha,
                            cas_key = :cas,
                            metadata_jsonb = CAST(:meta AS jsonb)
                        WHERE resource_id = :res_id;
                        """
                    ),
                    {
                        "ver": prev_ver,
                        "sha": prev_sha,
                        "cas": prev_cas,
                        "meta": json.dumps(meta),
                        "res_id": target_res_id,
                    },
                )
                restored_version = prev_ver
                lang = str(meta.get("lang") or "fr")
                pack = str(meta.get("pack_name") or "core")
                routes = meta.get("bound_routes") or []
                if isinstance(routes, list):
                    for rt in routes:
                        invalidated_keys.append(build_help_redis_cache_key(str(rt), pack, lang))

        await insert_outbox_and_audit(conn, event, audit_sink)
        return {
            "run_id": str(run_row["run_id"]),
            "workspace_id": str(run_row["workspace_id"]),
            "status": str(run_row["status"]),
            "restored_version": restored_version,
            "help_resource_id": target_res_id,
            "invalidated_redis_keys": invalidated_keys,
        }
