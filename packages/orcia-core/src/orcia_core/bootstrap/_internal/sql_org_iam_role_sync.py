"""Bidirectional synchronization between `org_units` and `iam_accounts` (`CAP-067` / B1 Strict).

Transactional helpers ensuring multi-lead consistency, automatic `BU_LEAD`/`TEAM_LEAD` role
cleanup upon unassignment, lead assignment via IAM directory, and `auth_source` resolution.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import replace
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.bootstrap._internal.sql_local_auth import _resolve_platform_role
from orcia_core.bootstrap._internal.sql_org_known_users import (
    load_known_org_users_from_postgres18,
)
from orcia_core.permissions.errors import OrgUnitNotFoundError
from orcia_core.permissions.iam_accounts import IamAccountRecord, IamAuthSource
from orcia_core.permissions.org_user_validation import resolve_and_validate_org_unit_leads
from orcia_core.permissions.role_matrix import VALID_IAM_ROLES


def parse_str_list(raw: object) -> list[str]:
    """Parse JSONB array or string representation into string list."""
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


async def resolve_canonical_lead_user_ids(
    conn: AsyncConnection,
    *,
    lead_user_ids: Sequence[str] | None,
    lead_user_id: str | None,
) -> tuple[tuple[str, ...], str | None]:
    """Validate and resolve multiple or single lead user IDs against known platform users."""
    known_users = await load_known_org_users_from_postgres18(conn)
    return resolve_and_validate_org_unit_leads(
        lead_user_ids=lead_user_ids,
        lead_user_id=lead_user_id,
        known_users=known_users,
    )


async def resolve_default_human_auth_source(conn: AsyncConnection) -> IamAuthSource:
    """Return 'OIDC_FEDERATED' if platform auth mode is SSO, else 'LOCAL_PASSWORD'."""
    reg = (
        await conn.execute(sa.text("SELECT to_regclass('public.platform_auth_settings')"))
    ).scalar()
    if reg is None:
        return "LOCAL_PASSWORD"
    row = (
        await conn.execute(
            sa.text("SELECT auth_mode FROM platform_auth_settings WHERE singleton_key = 'GLOBAL'")
        )
    ).first()
    if row is not None and str(row[0] or "").strip().upper() == "SSO":
        return "OIDC_FEDERATED"
    return "LOCAL_PASSWORD"


async def _count_led_units_for_user(
    conn: AsyncConnection, uid: str, unit_types: tuple[str, ...]
) -> int:
    types_clause = ", ".join(f"'{t}'" for t in unit_types)
    cnt = (
        await conn.execute(
            sa.text(
                f"""
                SELECT COUNT(*) FROM org_units
                WHERE unit_type IN ({types_clause})
                  AND (lead_user_ids_jsonb @> to_jsonb(CAST(:uid AS text))
                       OR LOWER(lead_user_id) = LOWER(:uid)
                       OR EXISTS (
                           SELECT 1 FROM jsonb_array_elements_text(lead_user_ids_jsonb) elem
                           WHERE LOWER(elem) = LOWER(:uid)
                       ))
                """
            ),
            {"uid": uid},
        )
    ).scalar()
    return int(cnt or 0)


async def sync_iam_lead_roles_from_org_units(
    conn: AsyncConnection,
    impacted_user_ids: Sequence[str],
) -> None:
    """Synchronize `BU_LEAD` and `TEAM_LEAD` roles in `iam_accounts` and `users` (B1 Strict)."""
    iam_reg = (await conn.execute(sa.text("SELECT to_regclass('public.iam_accounts')"))).scalar()
    if iam_reg is None or not impacted_user_ids:
        return

    users_reg = (await conn.execute(sa.text("SELECT to_regclass('public.users')"))).scalar()
    for uid in {u.strip() for u in impacted_user_ids if u.strip()}:
        bu_cnt = await _count_led_units_for_user(conn, uid, ("BU", "TRIBE"))
        team_cnt = await _count_led_units_for_user(conn, uid, ("TEAM", "SUB_TEAM"))

        acc = (
            await conn.execute(
                sa.text(
                    """
                    SELECT id, principal_id, email, roles_jsonb FROM iam_accounts
                    WHERE LOWER(principal_id) = LOWER(:uid)
                       OR (email IS NOT NULL AND LOWER(email) = LOWER(:uid))
                    """
                ),
                {"uid": uid},
            )
        ).first()
        if acc is None:
            continue

        acc_id, acc_email = str(acc[0]), str(acc[2] or "").strip().lower() or None
        roles = set(parse_str_list(acc[3]))
        roles.add("BU_LEAD") if bu_cnt >= 1 else roles.discard("BU_LEAD")
        roles.add("TEAM_LEAD") if team_cnt >= 1 else roles.discard("TEAM_LEAD")
        if not roles:
            roles.add("CONTRIBUTOR")

        ordered_roles: list[str] = [str(r) for r in VALID_IAM_ROLES if r in roles]
        await conn.execute(
            sa.text(
                "UPDATE iam_accounts SET roles_jsonb = CAST(:roles_json AS jsonb), "
                "updated_at = NOW() WHERE id = CAST(:id AS uuid)"
            ),
            {"roles_json": json.dumps(ordered_roles), "id": acc_id},
        )
        if users_reg is not None and acc_email:
            next_platform_role = _resolve_platform_role(ordered_roles)
            await conn.execute(
                sa.text(
                    "UPDATE users SET platform_role = :role WHERE LOWER(email) = LOWER(:email)"
                ),
                {"role": next_platform_role, "email": acc_email},
            )


async def _sync_single_role_lead_units(
    conn: AsyncConnection,
    *,
    nodes: list[Any],
    uids: set[str],
    role_name: str,
    roles: Sequence[str],
    target_ids: Sequence[str] | None,
    remove_all: bool,
    principal_id: str,
) -> None:
    if remove_all or (role_name not in roles and target_ids is None):
        for n in nodes:
            current = parse_str_list(n[5])
            if any(lead_ref.lower() in uids for lead_ref in current):
                remaining = [lead_ref for lead_ref in current if lead_ref.lower() not in uids]
                await _update_unit_leads(conn, str(n[0]), remaining)
    elif target_ids is not None:
        by_id = {str(n[0]): n for n in nodes}
        by_slug = {str(n[1]).lower(): n for n in nodes}
        target_uuids: set[str] = set()
        for ref in target_ids:
            clean = ref.strip()
            if not clean:
                continue
            matched = by_id.get(clean) or by_slug.get(clean.lower())
            if matched is None:
                raise OrgUnitNotFoundError(instance=f"/org/units/{clean}")
            target_uuids.add(str(matched[0]))

        for n in nodes:
            nid = str(n[0])
            current = parse_str_list(n[5])
            has_user = any(lead_ref.lower() in uids for lead_ref in current)
            should_lead = nid in target_uuids
            if should_lead and not has_user:
                await _update_unit_leads(conn, nid, [*current, principal_id])
            elif not should_lead and has_user:
                await _update_unit_leads(
                    conn, nid, [lead_ref for lead_ref in current if lead_ref.lower() not in uids]
                )


async def sync_lead_units_from_iam_account(
    conn: AsyncConnection,
    *,
    principal_id: str,
    email: str | None,
    roles: Sequence[str],
    led_bu_ids: Sequence[str] | None = None,
    led_team_ids: Sequence[str] | None = None,
    remove_all: bool = False,
) -> None:
    """Synchronize `org_units.lead_user_ids_jsonb` when an IAM account is mutated."""
    ou_reg = (await conn.execute(sa.text("SELECT to_regclass('public.org_units')"))).scalar()
    if ou_reg is None:
        return

    rows = (
        await conn.execute(
            sa.text(
                "SELECT id, slug, name, unit_type, lead_user_id, lead_user_ids_jsonb FROM org_units"
            )
        )
    ).fetchall()

    bu_nodes = [r for r in rows if str(r[3]).upper() in ("BU", "TRIBE")]
    team_nodes = [r for r in rows if str(r[3]).upper() in ("TEAM", "SUB_TEAM")]
    uids = {
        principal_id.strip().lower(),
        *((email.strip().lower(),) if email and email.strip() else ()),
    }

    await _sync_single_role_lead_units(
        conn,
        nodes=bu_nodes,
        uids=uids,
        role_name="BU_LEAD",
        roles=roles,
        target_ids=led_bu_ids,
        remove_all=remove_all,
        principal_id=principal_id,
    )
    await _sync_single_role_lead_units(
        conn,
        nodes=team_nodes,
        uids=uids,
        role_name="TEAM_LEAD",
        roles=roles,
        target_ids=led_team_ids,
        remove_all=remove_all,
        principal_id=principal_id,
    )


async def _update_unit_leads(conn: AsyncConnection, unit_id: str, next_leads: list[str]) -> None:
    primary = next_leads[0] if next_leads else None
    await conn.execute(
        sa.text(
            "UPDATE org_units SET lead_user_ids_jsonb = CAST(:leads_json AS jsonb), "
            "lead_user_id = :lead_id WHERE id = :id"
        ),
        {
            "leads_json": json.dumps(next_leads, ensure_ascii=False),
            "lead_id": primary,
            "id": UUID(unit_id),
        },
    )


async def hydrate_iam_accounts_led_units(
    conn: AsyncConnection,
    accounts: Sequence[IamAccountRecord],
) -> list[IamAccountRecord]:
    """Hydrate `led_bu_ids` and `led_team_ids` tuples on `IamAccountRecord` items."""
    ou_reg = (await conn.execute(sa.text("SELECT to_regclass('public.org_units')"))).scalar()
    if ou_reg is None or not accounts:
        return list(accounts)

    rows = (
        await conn.execute(
            sa.text("SELECT id, unit_type, lead_user_id, lead_user_ids_jsonb FROM org_units")
        )
    ).fetchall()

    hydrated: list[IamAccountRecord] = []
    for acc in accounts:
        uids = {
            acc.principal_id.strip().lower(),
            *((acc.email.strip().lower(),) if acc.email and acc.email.strip() else ()),
        }
        led_bus: list[str] = []
        led_teams: list[str] = []

        for row in rows:
            uid = str(row[0])
            kind = str(row[1]).upper()
            leads = parse_str_list(row[3])
            lead_single = str(row[2] or "").strip()
            if lead_single and lead_single not in leads:
                leads.append(lead_single)

            if any(lead_ref.lower() in uids for lead_ref in leads):
                (led_bus if kind in ("BU", "TRIBE") else led_teams).append(uid)

        hydrated.append(replace(acc, led_bu_ids=tuple(led_bus), led_team_ids=tuple(led_teams)))
    return hydrated
