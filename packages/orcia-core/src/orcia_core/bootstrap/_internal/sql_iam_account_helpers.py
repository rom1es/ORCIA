"""Internal SQL row-mapping, schema bootstrap, Day-0 admin resolution, and `org_units` team sync
helpers for `sql_iam_accounts.py` (`Story 17.3`).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.permissions.iam_accounts import (
    IamAccountKind,
    IamAccountRecord,
    IamAccountStatus,
    IamAuthSource,
    normalize_team_ids,
)
from orcia_core.permissions.role_matrix import OfficialIamRole


def parse_str_list(raw: object) -> list[str]:
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
        except ValueError:
            return []
        if isinstance(decoded, list):
            return [str(x).strip() for x in decoded if str(x).strip()]
    return []


def fmt_ts(val: object) -> str:
    if isinstance(val, datetime):
        return val.isoformat().replace("+00:00", "Z")
    return str(val or "")


def row_to_account(row: Any) -> IamAccountRecord:
    raw_roles = parse_str_list(row[6])
    roles = tuple(cast(OfficialIamRole, r) for r in raw_roles)
    return IamAccountRecord(
        id=str(row[0]),
        principal_id=str(row[1]),
        display_name=str(row[2]),
        email=str(row[3]) if row[3] is not None else None,
        account_kind=cast(IamAccountKind, str(row[4])),
        auth_source=cast(IamAuthSource, str(row[5])),
        roles=roles,
        team_ids=normalize_team_ids(parse_str_list(row[7])),
        status=cast(IamAccountStatus, str(row[8])),
        created_at_iso=fmt_ts(row[9]),
        updated_at_iso=fmt_ts(row[10]),
    )


async def ensure_iam_accounts_schema(conn: AsyncConnection) -> None:
    reg = (await conn.execute(sa.text("SELECT to_regclass('public.iam_accounts')"))).scalar()
    if reg is not None:
        await conn.execute(
            sa.text(
                """
                DO $$
                DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'public.iam_accounts'::regclass
                          AND contype = 'c'
                          AND pg_get_constraintdef(oid) ILIKE '%auth_source%'
                          AND pg_get_constraintdef(oid) NOT ILIKE '%LOCAL_PASSWORD%'
                    ) LOOP
                        EXECUTE 'ALTER TABLE iam_accounts DROP CONSTRAINT IF EXISTS '
                            || quote_ident(r.conname);
                        ALTER TABLE iam_accounts
                            ADD CONSTRAINT chk_iam_accounts_auth_source
                            CHECK (auth_source IN (
                                'LOCAL_BOOTSTRAP', 'LOCAL_PASSWORD',
                                'OIDC_FEDERATED', 'SERVICE_TOKEN'
                            ));
                    END LOOP;
                END $$;
                """
            )
        )
        return
    await conn.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS iam_accounts (
                id UUID PRIMARY KEY,
                principal_id VARCHAR(128) UNIQUE NOT NULL,
                display_name VARCHAR(160) NOT NULL,
                email VARCHAR(255) NULL,
                account_kind VARCHAR(32) NOT NULL
                    CHECK (account_kind IN ('HUMAN', 'SERVICE_PRINCIPAL')),
                auth_source VARCHAR(32) NOT NULL
                    CHECK (auth_source IN (
                        'LOCAL_BOOTSTRAP', 'LOCAL_PASSWORD', 'OIDC_FEDERATED', 'SERVICE_TOKEN'
                    )),
                roles_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                team_ids_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE', 'INVITED', 'DISABLED')),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    await conn.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_iam_accounts_kind_status
                ON iam_accounts (account_kind, status)
            """
        )
    )


async def load_accounts_from_conn(
    conn: AsyncConnection,
    *,
    for_update: bool = False,
) -> list[IamAccountRecord]:
    lock_clause = " FOR UPDATE" if for_update else ""
    rows = (
        await conn.execute(
            sa.text(
                f"""
                SELECT id, principal_id, display_name, email, account_kind, auth_source,
                       roles_jsonb, team_ids_jsonb, status, created_at, updated_at
                FROM iam_accounts
                ORDER BY created_at ASC, id ASC{lock_clause}
                """
            )
        )
    ).fetchall()
    accounts = [row_to_account(r) for r in rows]
    return sorted(
        accounts,
        key=lambda a: (0 if "PLATFORM_ADMIN" in a.roles else 1, a.created_at_iso, a.id),
    )


async def resolve_day0_admin_candidate(conn: AsyncConnection) -> tuple[str, str] | None:
    users_reg = (await conn.execute(sa.text("SELECT to_regclass('public.users')"))).scalar()
    if users_reg is not None:
        user_row = (
            await conn.execute(
                sa.text(
                    """
                    SELECT email, display_name
                    FROM users
                    WHERE is_active = TRUE
                    ORDER BY CASE WHEN platform_role = 'PLATFORM_ADMIN' THEN 0 ELSE 1 END,
                             id ASC
                    LIMIT 1
                    """
                )
            )
        ).first()
        if user_row is not None and str(user_row[0] or "").strip():
            email = str(user_row[0]).strip().lower()
            name = str(user_row[1] or "").strip() or email
            return email, name

    ps_reg = (
        await conn.execute(sa.text("SELECT to_regclass('public.platform_settings')"))
    ).scalar()
    if ps_reg is not None:
        ps_row = (
            await conn.execute(
                sa.text(
                    """
                    SELECT value_jsonb
                    FROM platform_settings
                    WHERE scope_level = 'GLOBAL'
                      AND category = 'iam'
                      AND key = 'platform_setup_state_v1'
                    LIMIT 1
                    """
                )
            )
        ).first()
        if ps_row is not None and ps_row[0]:
            payload = json.loads(ps_row[0]) if isinstance(ps_row[0], str) else ps_row[0]
            if isinstance(payload, dict):
                admin_obj = payload.get("platformAdmin")
                if isinstance(admin_obj, dict):
                    email = str(admin_obj.get("email") or "").strip().lower()
                    name = str(
                        admin_obj.get("fullName") or admin_obj.get("displayName") or email
                    ).strip()
                    if email:
                        return email, name or email
    return None


async def sync_team_memberships_in_org_units(
    conn: AsyncConnection,
    principal_id: str,
    desired_team_ids: Sequence[str],
    *,
    remove_all: bool = False,
) -> None:
    ou_reg = (await conn.execute(sa.text("SELECT to_regclass('public.org_units')"))).scalar()
    if ou_reg is None:
        return
    desired_set = set() if remove_all else {t.strip() for t in desired_team_ids if t.strip()}
    query = (
        "SELECT id, slug, member_user_ids_jsonb FROM org_units"
        if remove_all
        else "SELECT id, slug, member_user_ids_jsonb FROM org_units WHERE unit_type = 'TEAM'"
    )
    rows = (await conn.execute(sa.text(query))).fetchall()
    for row in rows:
        team_uuid = str(row[0])
        team_slug = str(row[1])
        current_members = parse_str_list(row[2])
        should_belong = (team_uuid in desired_set) or (team_slug in desired_set)
        has_member = principal_id in current_members
        if should_belong and not has_member:
            next_members = [*current_members, principal_id]
        elif not should_belong and has_member:
            next_members = [m for m in current_members if m != principal_id]
        else:
            continue
        await conn.execute(
            sa.text(
                """
                UPDATE org_units
                SET member_user_ids_jsonb = CAST(:members_json AS jsonb)
                WHERE id = :team_id
                """
            ),
            {
                "members_json": json.dumps(next_members, ensure_ascii=False),
                "team_id": UUID(team_uuid),
            },
        )
