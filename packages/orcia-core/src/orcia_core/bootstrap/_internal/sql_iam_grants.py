"""PostgreSQL 18 persistence adapter for `role_permission_grants` SecOps exceptions (`Story 17.3`).

Supports granular `resource_kind` (`ALL`, `WORKFLOW`, `AGENT`, `DATASOURCE`, `CONNECTOR`) and
`effect` (`ALLOW`, `DENY`, `INHERITANCE_BLOCK`) with idempotent `ON CONFLICT` upserts.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.permissions.errors import ResourceNotFoundError
from orcia_core.permissions.role_matrix import (
    GrantResourceKind,
    PermissionEffect,
    PermissionVerb,
    RolePermissionGrant,
    SubjectType,
)


def _fmt_ts(val: object) -> str:
    if isinstance(val, datetime):
        return val.isoformat().replace("+00:00", "Z")
    return str(val or "")


def _parse_conditions(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
        except ValueError:
            return {}
        if isinstance(decoded, dict):
            return dict(decoded)
    return {}


def _row_to_grant(row: Any) -> RolePermissionGrant:
    effect_str = str(row[5] or "ALLOW")
    inh_flag = bool(row[6]) or effect_str == "INHERITANCE_BLOCK"
    return RolePermissionGrant(
        id=str(row[0]),
        subject_type=cast(SubjectType, str(row[1])),
        subject_id=str(row[2]),
        scope_path=str(row[3]),
        verb=cast(PermissionVerb, str(row[4])),
        effect=cast(PermissionEffect, effect_str),
        inheritance_block=inh_flag,
        resource_kind=cast(GrantResourceKind, str(row[7] or "ALL")),
        conditions=_parse_conditions(row[8]),
        hidden_when_unauthorized=bool(row[9]),
        granted_by_user_id=str(row[10]) if row[10] is not None else None,
        created_at_iso=_fmt_ts(row[11]),
    )


async def _ensure_iam_grants_schema(conn: AsyncConnection) -> None:
    reg = (
        await conn.execute(sa.text("SELECT to_regclass('public.role_permission_grants')"))
    ).scalar()
    if reg is None:
        await conn.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS role_permission_grants (
                    id UUID PRIMARY KEY,
                    subject_type VARCHAR(32) NOT NULL
                        CHECK (subject_type IN ('USER', 'ROLE', 'SERVICE_PRINCIPAL')),
                    subject_id VARCHAR(128) NOT NULL,
                    scope_path VARCHAR(512) NOT NULL,
                    verb VARCHAR(32) NOT NULL
                        CHECK (verb IN ('create', 'read', 'update', 'delete', 'execute', 'grant')),
                    effect VARCHAR(32) NOT NULL DEFAULT 'ALLOW'
                        CHECK (effect IN ('ALLOW', 'DENY', 'INHERITANCE_BLOCK')),
                    inheritance_block BOOLEAN NOT NULL DEFAULT FALSE,
                    resource_kind VARCHAR(32) NOT NULL DEFAULT 'ALL'
                        CHECK (
                            resource_kind IN (
                                'ALL', 'WORKFLOW', 'AGENT', 'DATASOURCE', 'CONNECTOR'
                            )
                        ),
                    conditions_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                    hidden_when_unauthorized BOOLEAN NOT NULL DEFAULT FALSE,
                    granted_by_user_id UUID NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            sa.text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_role_permission_grants_resource_scope
                    ON role_permission_grants (
                        subject_type, subject_id, scope_path, resource_kind, verb, effect
                    )
                """
            )
        )
        return

    has_res_kind = (
        await conn.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'role_permission_grants'
                  AND column_name = 'resource_kind'
                """
            )
        )
    ).first()
    if has_res_kind is None:
        await conn.execute(
            sa.text(
                """
                ALTER TABLE role_permission_grants
                    DROP CONSTRAINT IF EXISTS role_permission_grants_effect_check
                """
            )
        )
        await conn.execute(
            sa.text("ALTER TABLE role_permission_grants ALTER COLUMN effect TYPE VARCHAR(32)")
        )
        await conn.execute(
            sa.text(
                """
                ALTER TABLE role_permission_grants
                    ADD CONSTRAINT role_permission_grants_effect_check
                        CHECK (effect IN ('ALLOW', 'DENY', 'INHERITANCE_BLOCK')),
                    ADD COLUMN IF NOT EXISTS resource_kind VARCHAR(32) NOT NULL DEFAULT 'ALL'
                        CHECK (
                            resource_kind IN (
                                'ALL', 'WORKFLOW', 'AGENT', 'DATASOURCE', 'CONNECTOR'
                            )
                        ),
                    DROP CONSTRAINT IF EXISTS
                        role_permission_grants_subject_type_subject_id_scope_path_ve_key
                """
            )
        )
        await conn.execute(
            sa.text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_role_permission_grants_resource_scope
                    ON role_permission_grants (
                        subject_type, subject_id, scope_path, resource_kind, verb, effect
                    )
                """
            )
        )


async def _resolve_existing_user_uuid(conn: AsyncConnection, raw_user_id: str | None) -> str | None:
    if not raw_user_id:
        return None
    try:
        UUID(raw_user_id.strip())
    except ValueError:
        return None
    users_reg = (await conn.execute(sa.text("SELECT to_regclass('public.users')"))).scalar()
    if users_reg is None:
        return None
    found = (
        await conn.execute(
            sa.text("SELECT id FROM users WHERE id = CAST(:uid AS uuid) LIMIT 1"),
            {"uid": raw_user_id.strip()},
        )
    ).first()
    return str(found[0]) if found is not None else None


async def list_iam_grants_from_postgres18(engine: AsyncEngine) -> list[RolePermissionGrant]:
    async with engine.begin() as conn:
        await _ensure_iam_grants_schema(conn)
        rows = (
            await conn.execute(
                sa.text(
                    """
                    SELECT id, subject_type, subject_id, scope_path, verb, effect,
                           inheritance_block, resource_kind, conditions_jsonb,
                           hidden_when_unauthorized, granted_by_user_id, created_at
                    FROM role_permission_grants
                    ORDER BY created_at DESC, id ASC
                    """
                )
            )
        ).fetchall()
        return [_row_to_grant(r) for r in rows]


async def create_iam_grants_on_postgres18(
    engine: AsyncEngine,
    grants: Sequence[RolePermissionGrant],
) -> list[RolePermissionGrant]:
    if not grants:
        return []
    persisted: list[RolePermissionGrant] = []
    async with engine.begin() as conn:
        await _ensure_iam_grants_schema(conn)
        for grant in grants:
            resolved_grantor = await _resolve_existing_user_uuid(conn, grant.granted_by_user_id)
            row = (
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO role_permission_grants (
                            id, subject_type, subject_id, scope_path, verb, effect,
                            inheritance_block, resource_kind, conditions_jsonb,
                            hidden_when_unauthorized, granted_by_user_id, created_at
                        )
                        VALUES (
                            CAST(:id AS uuid), :subject_type, :subject_id, :scope_path,
                            :verb, :effect, :inheritance_block, :resource_kind,
                            CAST(:conditions_json AS jsonb), :hidden_when_unauthorized,
                            CAST(:granted_by AS uuid), NOW()
                        )
                        ON CONFLICT (
                            subject_type, subject_id, scope_path, resource_kind, verb, effect
                        )
                        DO UPDATE SET
                            inheritance_block = EXCLUDED.inheritance_block,
                            conditions_jsonb = EXCLUDED.conditions_jsonb,
                            hidden_when_unauthorized = EXCLUDED.hidden_when_unauthorized
                        RETURNING id, subject_type, subject_id, scope_path, verb, effect,
                                  inheritance_block, resource_kind, conditions_jsonb,
                                  hidden_when_unauthorized, granted_by_user_id, created_at
                        """
                    ),
                    {
                        "id": grant.id,
                        "subject_type": grant.subject_type,
                        "subject_id": grant.subject_id,
                        "scope_path": grant.scope_path,
                        "verb": grant.verb,
                        "effect": grant.effect,
                        "inheritance_block": grant.inheritance_block,
                        "resource_kind": grant.resource_kind,
                        "conditions_json": json.dumps(grant.conditions, ensure_ascii=False),
                        "hidden_when_unauthorized": grant.hidden_when_unauthorized,
                        "granted_by": resolved_grantor,
                    },
                )
            ).one()
            persisted.append(_row_to_grant(row))
    return persisted


async def delete_iam_grant_on_postgres18(
    engine: AsyncEngine,
    grant_id: str,
    *,
    instance: str | None = None,
) -> str:
    try:
        UUID(grant_id.strip())
    except ValueError as exc:
        raise ResourceNotFoundError(instance=instance) from exc
    async with engine.begin() as conn:
        await _ensure_iam_grants_schema(conn)
        res = await conn.execute(
            sa.text("DELETE FROM role_permission_grants WHERE id = CAST(:id AS uuid) RETURNING id"),
            {"id": grant_id.strip()},
        )
        deleted = res.first()
        if deleted is None:
            raise ResourceNotFoundError(instance=instance)
        return str(deleted[0])
