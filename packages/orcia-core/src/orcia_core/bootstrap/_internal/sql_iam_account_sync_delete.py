"""PostgreSQL 18 Day-0 sync and deletion helpers for `iam_accounts` (`Story 17.3` & `25.1`)."""

from __future__ import annotations

import json
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.bootstrap._internal.sql_iam_account_helpers import (
    ensure_iam_accounts_schema,
    load_accounts_from_conn,
    resolve_day0_admin_candidate,
    sync_team_memberships_in_org_units,
)
from orcia_core.bootstrap._internal.sql_org_iam_role_sync import (
    hydrate_iam_accounts_led_units,
    sync_lead_units_from_iam_account,
)
from orcia_core.bootstrap._internal.sql_org_ontology_lead_sync import (
    hydrate_iam_accounts_ontology_led_bus,
    sync_ontology_lead_bus_from_iam_account,
)
from orcia_core.permissions.errors import ResourceNotFoundError
from orcia_core.permissions.iam_accounts import (
    DEFAULT_DAY0_ADMIN_ROLES,
    IamAccountRecord,
    assert_anti_lockout_on_accounts,
)
from orcia_kernel.ids import new_uuid7_str


async def sync_and_list_iam_accounts_from_postgres18(
    engine: AsyncEngine,
) -> list[IamAccountRecord]:
    """Synchronize Day-0 initial admin (`PLATFORM_ADMIN + SECOPS`) and list all IAM accounts."""
    async with engine.begin() as conn:
        await ensure_iam_accounts_schema(conn)
        existing = await load_accounts_from_conn(conn)
        candidate = await resolve_day0_admin_candidate(conn)
        if candidate is not None:
            cand_email, cand_name = candidate
            already_seeded = any(a.principal_id.lower() == cand_email for a in existing)
            if not already_seeded:
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO iam_accounts (
                            id, principal_id, display_name, email, account_kind, auth_source,
                            roles_jsonb, team_ids_jsonb, status, created_at, updated_at
                        )
                        VALUES (
                            CAST(:id AS uuid), :principal_id, :display_name, :email,
                            'HUMAN', 'LOCAL_BOOTSTRAP', CAST(:roles_json AS jsonb),
                            '[]'::jsonb, 'ACTIVE', NOW(), NOW()
                        )
                        ON CONFLICT (principal_id) DO NOTHING
                        """
                    ),
                    {
                        "id": new_uuid7_str(),
                        "principal_id": cand_email,
                        "display_name": cand_name[:160],
                        "email": cand_email[:255],
                        "roles_json": json.dumps(list(DEFAULT_DAY0_ADMIN_ROLES)),
                    },
                )
                if cand_email != "admin@orcia.local":
                    await conn.execute(
                        sa.text("DELETE FROM iam_accounts WHERE principal_id = 'admin@orcia.local'")
                    )
                existing = await load_accounts_from_conn(conn)
        elif not existing:
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO iam_accounts (
                        id, principal_id, display_name, email, account_kind, auth_source,
                        roles_jsonb, team_ids_jsonb, status, created_at, updated_at
                    )
                    VALUES (
                        CAST(:id AS uuid), 'admin@orcia.local',
                        'Administrateur Plateforme (Jour 0)', 'admin@orcia.local',
                        'HUMAN', 'LOCAL_BOOTSTRAP', CAST(:roles_json AS jsonb),
                        '[]'::jsonb, 'ACTIVE', NOW(), NOW()
                    )
                    ON CONFLICT (principal_id) DO NOTHING
                    """
                ),
                {
                    "id": new_uuid7_str(),
                    "roles_json": json.dumps(list(DEFAULT_DAY0_ADMIN_ROLES)),
                },
            )
            existing = await load_accounts_from_conn(conn)
        hydrated = await hydrate_iam_accounts_led_units(conn, existing)
        return await hydrate_iam_accounts_ontology_led_bus(conn, hydrated)


async def delete_iam_account_on_postgres18(
    engine: AsyncEngine,
    account_id: str,
    *,
    instance: str | None = None,
) -> str:
    """Delete an IAM account atomically with anti-lockout and org unit membership cleanup."""
    try:
        UUID(account_id.strip())
    except ValueError as exc:
        raise ResourceNotFoundError(instance=instance) from exc

    async with engine.begin() as conn:
        await ensure_iam_accounts_schema(conn)
        existing = await load_accounts_from_conn(conn, for_update=True)
        target = next((a for a in existing if a.id == account_id.strip()), None)
        if target is None:
            raise ResourceNotFoundError(instance=instance)

        assert_anti_lockout_on_accounts(
            existing,
            deleted_account_id=target.id,
            instance=instance,
        )
        await sync_team_memberships_in_org_units(
            conn,
            target.principal_id,
            (),
            remove_all=True,
        )
        await sync_lead_units_from_iam_account(
            conn,
            principal_id=target.principal_id,
            email=target.email,
            roles=(),
            remove_all=True,
        )
        await sync_ontology_lead_bus_from_iam_account(
            conn,
            principal_id=target.principal_id,
            email=target.email,
            roles=(),
            remove_all=True,
        )
        await conn.execute(
            sa.text("DELETE FROM iam_accounts WHERE id = CAST(:id AS uuid)"),
            {"id": target.id},
        )
        return target.id


__all__ = [
    "delete_iam_account_on_postgres18",
    "sync_and_list_iam_accounts_from_postgres18",
]
