"""PostgreSQL 18 repository for `workspace_exception_waivers` (Migration `0026_story_11_1`)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orcia_core.orchestration._workspace_governance_models import (
    DnaChainNode,
    ExceptionWaiverRecord,
    NormOntologyLevel,
    WaiverStatus,
)
from orcia_core.orchestration.errors import ResourceNotFoundError


def _parse_dna_chain(raw: Any) -> tuple[DnaChainNode, ...]:
    if isinstance(raw, str):
        parsed = json.loads(raw) if raw else []
    elif isinstance(raw, list):
        parsed = raw
    else:
        parsed = []
    nodes: list[DnaChainNode] = []
    for item in parsed:
        if not isinstance(item, Mapping):
            continue
        nodes.append(
            DnaChainNode(
                node_key=str(item.get("node_key", "node")),
                stereotype=cast(
                    Any,
                    item.get("stereotype", "NORM"),
                ),
                level=cast(
                    NormOntologyLevel,
                    item.get("level", "3_WORKSPACE"),
                ),
                inviolable=bool(item.get("inviolable", False)),
            )
        )
    return tuple(nodes)


def _row_to_waiver(row: RowMapping) -> ExceptionWaiverRecord:
    return ExceptionWaiverRecord(
        waiver_id=UUID(str(row["waiver_id"])),
        workspace_id=UUID(str(row["workspace_id"])),
        source_uri=str(row["source_uri"]),
        source_sha256=str(row["source_sha256"]),
        conflict_rule_id=str(row["conflict_rule_id"]),
        norm_level=cast(NormOntologyLevel, str(row["norm_level"])),
        dna_chain=_parse_dna_chain(row["dna_chain_jsonb"]),
        approved_by_user_id=UUID(str(row["approved_by_user_id"])),
        approved_by_role=str(row["approved_by_role"]),
        reason=str(row["reason"]),
        status=cast(WaiverStatus, str(row["status"])),
        expires_at=cast(datetime, row["expires_at"]),
        created_at=cast(datetime, row["created_at"]),
    )


async def list_workspace_waivers_sql(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    workspace_id: UUID,
    active_only: bool = False,
) -> list[ExceptionWaiverRecord]:
    """List persisted exception waivers for a workspace from PostgreSQL 18."""
    where_clause = "workspace_id = CAST(:workspace_id AS uuid)"
    if active_only:
        where_clause += " AND status = 'ACTIVE'"
    async with session_factory() as session:
        rows = (
            (
                await session.execute(
                    sa.text(
                        f"""
                        SELECT waiver_id, workspace_id, source_uri, source_sha256,
                               conflict_rule_id, norm_level, dna_chain_jsonb,
                               approved_by_user_id, approved_by_role, reason,
                               status, expires_at, created_at
                        FROM workspace_exception_waivers
                        WHERE {where_clause}
                        ORDER BY created_at DESC
                        """
                    ),
                    {"workspace_id": str(workspace_id)},
                )
            )
            .mappings()
            .all()
        )
        return [_row_to_waiver(row) for row in rows]


async def _resolve_approver_user_id(
    session: AsyncSession,
    *,
    approved_by_user_id: UUID,
    approved_by_email: str | None,
) -> UUID:
    by_id = (
        await session.execute(
            sa.text("SELECT id FROM users WHERE id = CAST(:uid AS uuid) LIMIT 1"),
            {"uid": str(approved_by_user_id)},
        )
    ).scalar_one_or_none()
    if by_id is not None:
        return UUID(str(by_id))

    if approved_by_email:
        by_email = (
            await session.execute(
                sa.text("SELECT id FROM users WHERE lower(email) = lower(:email) LIMIT 1"),
                {"email": approved_by_email.strip()},
            )
        ).scalar_one_or_none()
        if by_email is not None:
            return UUID(str(by_email))

    fallback = (
        await session.execute(
            sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1"),
        )
    ).scalar_one_or_none()
    if fallback is not None:
        return UUID(str(fallback))
    raise ResourceNotFoundError(
        detail_override="Aucun compte utilisateur valide trouvé pour signer la dérogation."
    )


async def upsert_workspace_waiver_sql(
    session_factory: async_sessionmaker[AsyncSession],
    waiver: ExceptionWaiverRecord,
    *,
    approved_by_email: str | None = None,
) -> ExceptionWaiverRecord:
    """Persist or update an exception waiver in `workspace_exception_waivers`."""
    dna_payload = json.dumps(
        [
            {
                "node_key": n.node_key,
                "stereotype": n.stereotype,
                "level": n.level,
                "inviolable": n.inviolable,
            }
            for n in waiver.dna_chain
        ]
    )
    async with session_factory() as session, session.begin():
        ws_exists = (
            await session.execute(
                sa.text("SELECT id FROM workspaces WHERE id = CAST(:ws_id AS uuid) LIMIT 1"),
                {"ws_id": str(waiver.workspace_id)},
            )
        ).scalar_one_or_none()
        if ws_exists is None:
            raise ResourceNotFoundError(
                detail_override=f"Espace de travail '{waiver.workspace_id}' introuvable."
            )

        approver_id = await _resolve_approver_user_id(
            session,
            approved_by_user_id=waiver.approved_by_user_id,
            approved_by_email=approved_by_email,
        )

        row = (
            (
                await session.execute(
                    sa.text(
                        """
                        INSERT INTO workspace_exception_waivers (
                            waiver_id, workspace_id, source_uri, source_sha256,
                            conflict_rule_id, norm_level, dna_chain_jsonb,
                            approved_by_user_id, approved_by_role, reason,
                            status, expires_at, created_at
                        ) VALUES (
                            CAST(:waiver_id AS uuid), CAST(:workspace_id AS uuid),
                            :source_uri, :source_sha256, :conflict_rule_id,
                            :norm_level, CAST(:dna_chain_jsonb AS jsonb),
                            CAST(:approved_by_user_id AS uuid), :approved_by_role,
                            :reason, :status, :expires_at, :created_at
                        )
                        ON CONFLICT (workspace_id, source_uri, source_sha256, conflict_rule_id)
                        DO UPDATE SET
                            norm_level = EXCLUDED.norm_level,
                            dna_chain_jsonb = EXCLUDED.dna_chain_jsonb,
                            approved_by_user_id = EXCLUDED.approved_by_user_id,
                            approved_by_role = EXCLUDED.approved_by_role,
                            reason = EXCLUDED.reason,
                            status = EXCLUDED.status,
                            expires_at = EXCLUDED.expires_at
                        RETURNING waiver_id, workspace_id, source_uri, source_sha256,
                                  conflict_rule_id, norm_level, dna_chain_jsonb,
                                  approved_by_user_id, approved_by_role, reason,
                                  status, expires_at, created_at
                        """
                    ),
                    {
                        "waiver_id": str(waiver.waiver_id),
                        "workspace_id": str(waiver.workspace_id),
                        "source_uri": waiver.source_uri,
                        "source_sha256": waiver.source_sha256,
                        "conflict_rule_id": waiver.conflict_rule_id,
                        "norm_level": waiver.norm_level,
                        "dna_chain_jsonb": dna_payload,
                        "approved_by_user_id": str(approver_id),
                        "approved_by_role": waiver.approved_by_role,
                        "reason": waiver.reason,
                        "status": waiver.status,
                        "expires_at": waiver.expires_at,
                        "created_at": waiver.created_at,
                    },
                )
            )
            .mappings()
            .one()
        )
        return _row_to_waiver(row)


async def update_workspace_waiver_status_sql(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    waiver_id: UUID,
    status: WaiverStatus,
) -> None:
    """Update status (`EXPIRED` / `INVALIDATED_SHA_DRIFT` / `REVOKED`) in PG18."""
    async with session_factory() as session, session.begin():
        await session.execute(
            sa.text(
                """
                UPDATE workspace_exception_waivers
                SET status = :status
                WHERE waiver_id = CAST(:waiver_id AS uuid)
                """
            ),
            {"waiver_id": str(waiver_id), "status": status},
        )
