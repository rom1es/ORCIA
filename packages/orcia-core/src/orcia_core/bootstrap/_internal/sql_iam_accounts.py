"""PostgreSQL 18 persistence adapter for `iam_accounts` directory & Day-0 sync (`Story 17.3`).

Enforces closed 6-role validation (`422 ERR_IAM_INVALID_ROLE`), unique principal constraint
(`409 ERR_IAM_DUPLICATE_PRINCIPAL`), transactional anti-lockout (`SELECT ... FOR UPDATE` ->
`422 ERR_ADMIN_LOCKOUT_PREVENTED`), Day-0 admin auto-sync (`["PLATFORM_ADMIN", "SECOPS"]`),
and `org_units.member_user_ids_jsonb` team membership sync.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import replace
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.bootstrap._internal.sql_iam_account_helpers import (
    ensure_iam_accounts_schema,
    load_accounts_from_conn,
    resolve_day0_admin_candidate,
    row_to_account,
    sync_team_memberships_in_org_units,
)
from orcia_core.permissions.errors import (
    DuplicateIamPrincipalError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.permissions.iam_accounts import (
    DEFAULT_DAY0_ADMIN_ROLES,
    IamAccountKind,
    IamAccountRecord,
    IamAccountStatus,
    IamAuthSource,
    assert_anti_lockout_on_accounts,
    normalize_principal_id,
    normalize_team_ids,
    validate_iam_roles,
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
        return existing


async def create_iam_account_on_postgres18(
    engine: AsyncEngine,
    *,
    principal_id: str | None = None,
    display_name: str,
    email: str | None = None,
    account_kind: IamAccountKind = "HUMAN",
    auth_source: IamAuthSource | None = None,
    roles: Sequence[str],
    team_ids: Sequence[str] | None = None,
    status: IamAccountStatus = "ACTIVE",
    instance: str | None = None,
) -> IamAccountRecord:
    cleaned_name = display_name.strip()
    if not cleaned_name:
        raise ValidationDomainError(
            detail_override="Le nom affiché du compte ne peut pas être vide.",
            instance=instance,
        )
    valid_roles = validate_iam_roles(roles, instance=instance)
    cleaned_email = (email or "").strip().lower() or None
    norm_principal = normalize_principal_id(
        principal_id,
        email=cleaned_email,
        display_name=cleaned_name,
        account_kind=account_kind,
        instance=instance,
    )
    norm_teams = normalize_team_ids(team_ids)
    effective_source: IamAuthSource = auth_source or (
        "SERVICE_TOKEN" if account_kind == "SERVICE_PRINCIPAL" else "OIDC_FEDERATED"
    )
    new_id = new_uuid7_str()

    async with engine.begin() as conn:
        await ensure_iam_accounts_schema(conn)
        existing = await load_accounts_from_conn(conn, for_update=True)
        if any(a.principal_id.lower() == norm_principal.lower() for a in existing):
            raise DuplicateIamPrincipalError(instance=instance)
        row = (
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO iam_accounts (
                        id, principal_id, display_name, email, account_kind, auth_source,
                        roles_jsonb, team_ids_jsonb, status, created_at, updated_at
                    )
                    VALUES (
                        CAST(:id AS uuid), :principal_id, :display_name, :email,
                        :account_kind, :auth_source, CAST(:roles_json AS jsonb),
                        CAST(:teams_json AS jsonb), :status, NOW(), NOW()
                    )
                    RETURNING id, principal_id, display_name, email, account_kind, auth_source,
                              roles_jsonb, team_ids_jsonb, status, created_at, updated_at
                    """
                ),
                {
                    "id": new_id,
                    "principal_id": norm_principal,
                    "display_name": cleaned_name[:160],
                    "email": cleaned_email[:255] if cleaned_email else None,
                    "account_kind": account_kind,
                    "auth_source": effective_source,
                    "roles_json": json.dumps(list(valid_roles)),
                    "teams_json": json.dumps(list(norm_teams)),
                    "status": status,
                },
            )
        ).one()
        if norm_teams:
            await sync_team_memberships_in_org_units(conn, norm_principal, norm_teams)
        return row_to_account(row)


async def update_iam_account_on_postgres18(
    engine: AsyncEngine,
    account_id: str,
    *,
    display_name: str | None = None,
    email: str | None = None,
    email_provided: bool = False,
    roles: Sequence[str] | None = None,
    team_ids: Sequence[str] | None = None,
    status: IamAccountStatus | None = None,
    instance: str | None = None,
) -> IamAccountRecord:
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

        next_name = target.display_name
        if display_name is not None:
            stripped = display_name.strip()
            if not stripped:
                raise ValidationDomainError(
                    detail_override="Le nom affiché du compte ne peut pas être vide.",
                    instance=instance,
                )
            next_name = stripped[:160]

        next_email = ((email or "").strip().lower() or None) if email_provided else target.email
        next_roles = (
            validate_iam_roles(roles, instance=instance) if roles is not None else target.roles
        )
        next_teams = normalize_team_ids(team_ids) if team_ids is not None else target.team_ids
        next_status = status if status is not None else target.status

        mutated = replace(
            target,
            display_name=next_name,
            email=next_email,
            roles=next_roles,
            team_ids=next_teams,
            status=next_status,
        )
        assert_anti_lockout_on_accounts(existing, mutated_account=mutated, instance=instance)

        row = (
            await conn.execute(
                sa.text(
                    """
                    UPDATE iam_accounts
                    SET display_name = :display_name,
                        email = :email,
                        roles_jsonb = CAST(:roles_json AS jsonb),
                        team_ids_jsonb = CAST(:teams_json AS jsonb),
                        status = :status,
                        updated_at = NOW()
                    WHERE id = CAST(:id AS uuid)
                    RETURNING id, principal_id, display_name, email, account_kind, auth_source,
                              roles_jsonb, team_ids_jsonb, status, created_at, updated_at
                    """
                ),
                {
                    "id": target.id,
                    "display_name": next_name,
                    "email": next_email[:255] if next_email else None,
                    "roles_json": json.dumps(list(next_roles)),
                    "teams_json": json.dumps(list(next_teams)),
                    "status": next_status,
                },
            )
        ).one()
        if team_ids is not None:
            await sync_team_memberships_in_org_units(conn, target.principal_id, next_teams)
        return row_to_account(row)


async def delete_iam_account_on_postgres18(
    engine: AsyncEngine,
    account_id: str,
    *,
    instance: str | None = None,
) -> str:
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
        await conn.execute(
            sa.text("DELETE FROM iam_accounts WHERE id = CAST(:id AS uuid)"),
            {"id": target.id},
        )
        return target.id
