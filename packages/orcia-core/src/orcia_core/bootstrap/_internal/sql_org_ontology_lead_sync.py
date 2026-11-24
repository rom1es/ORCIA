"""Bidirectional B1 synchronization for `ONTOLOGY_LEAD` between `org_units` and `iam_accounts`.

Zero orphan SQL helpers: consumed by `sql_org_units.py` and `sql_iam_accounts.py`.
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
from orcia_core.bootstrap._internal.sql_org_iam_role_sync import parse_str_list
from orcia_core.bootstrap._internal.sql_org_known_users import (
    load_known_org_users_from_postgres18,
)
from orcia_core.permissions.errors import OrgUnitNotFoundError, ValidationDomainError
from orcia_core.permissions.iam_accounts import IamAccountRecord
from orcia_core.permissions.org_user_validation import resolve_and_validate_org_unit_leads
from orcia_core.permissions.role_matrix import VALID_IAM_ROLES


async def resolve_canonical_ontology_lead_user_ids(
    conn: AsyncConnection,
    *,
    ontology_lead_user_ids: Sequence[str] | None,
) -> tuple[str, ...]:
    """Validate and resolve ontology lead user IDs against known active human users."""
    if not ontology_lead_user_ids:
        return ()
    known_users = await load_known_org_users_from_postgres18(conn)
    resolved, _ = resolve_and_validate_org_unit_leads(
        lead_user_ids=ontology_lead_user_ids,
        lead_user_id=None,
        known_users=known_users,
    )
    return resolved


async def _count_ontology_led_bus_for_user(conn: AsyncConnection, uid: str) -> int:
    cnt = (
        await conn.execute(
            sa.text(
                """
                SELECT COUNT(*) FROM org_units
                WHERE unit_type = 'BU'
                  AND EXISTS (
                      SELECT 1
                      FROM jsonb_array_elements_text(ontology_lead_user_ids_jsonb) elem
                      WHERE LOWER(elem) = LOWER(:uid)
                  )
                """
            ),
            {"uid": uid},
        )
    ).scalar()
    return int(cnt or 0)


async def sync_iam_ontology_lead_roles_from_org_units(
    conn: AsyncConnection,
    impacted_user_ids: Sequence[str],
) -> None:
    """Synchronize `ONTOLOGY_LEAD` role in `iam_accounts` and `users` from BU assignments."""
    iam_reg = (await conn.execute(sa.text("SELECT to_regclass('public.iam_accounts')"))).scalar()
    if iam_reg is None or not impacted_user_ids:
        return

    users_reg = (await conn.execute(sa.text("SELECT to_regclass('public.users')"))).scalar()
    for uid in {u.strip() for u in impacted_user_ids if u and u.strip()}:
        bu_cnt = await _count_ontology_led_bus_for_user(conn, uid)
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
        if bu_cnt >= 1:
            roles.add("ONTOLOGY_LEAD")
        else:
            roles.discard("ONTOLOGY_LEAD")
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


async def _update_bu_ontology_leads(
    conn: AsyncConnection, unit_id: str, next_leads: list[str]
) -> None:
    await conn.execute(
        sa.text(
            """
            UPDATE org_units
            SET ontology_lead_user_ids_jsonb = CAST(:leads_json AS jsonb)
            WHERE id = :id
            """
        ),
        {
            "leads_json": json.dumps(next_leads, ensure_ascii=False),
            "id": UUID(unit_id),
        },
    )


async def sync_ontology_lead_bus_from_iam_account(
    conn: AsyncConnection,
    *,
    principal_id: str,
    email: str | None,
    roles: Sequence[str],
    ontology_led_bu_ids: Sequence[str] | None = None,
    remove_all: bool = False,
) -> None:
    """Synchronize `org_units.ontology_lead_user_ids_jsonb` (BU only) on IAM account mutation."""
    ou_reg = (await conn.execute(sa.text("SELECT to_regclass('public.org_units')"))).scalar()
    if ou_reg is None:
        return

    rows = (
        await conn.execute(
            sa.text("SELECT id, slug, unit_type, ontology_lead_user_ids_jsonb FROM org_units")
        )
    ).fetchall()

    bu_nodes: list[Any] = [r for r in rows if str(r[2]).upper() == "BU"]
    team_nodes_by_ref: dict[str, Any] = {}
    for r in rows:
        if str(r[2]).upper() != "BU":
            team_nodes_by_ref[str(r[0])] = r
            team_nodes_by_ref[str(r[1]).lower()] = r

    uids = {
        principal_id.strip().lower(),
        *((email.strip().lower(),) if email and email.strip() else ()),
    }

    if remove_all or ("ONTOLOGY_LEAD" not in roles and ontology_led_bu_ids is None):
        for n in bu_nodes:
            current = parse_str_list(n[3])
            if any(ref.lower() in uids for ref in current):
                remaining = [ref for ref in current if ref.lower() not in uids]
                await _update_bu_ontology_leads(conn, str(n[0]), remaining)
        return

    if ontology_led_bu_ids is None:
        return

    by_id = {str(n[0]): n for n in bu_nodes}
    by_slug = {str(n[1]).lower(): n for n in bu_nodes}
    target_uuids: set[str] = set()
    for ref in ontology_led_bu_ids:
        clean = ref.strip()
        if not clean:
            continue
        if clean in team_nodes_by_ref or clean.lower() in team_nodes_by_ref:
            raise ValidationDomainError(
                detail_code="ERR_ORG_ONTOLOGY_LEAD_BU_ONLY",
                instance=f"/org/units/{clean}",
            )
        matched = by_id.get(clean) or by_slug.get(clean.lower())
        if matched is None:
            raise OrgUnitNotFoundError(instance=f"/org/units/{clean}")
        target_uuids.add(str(matched[0]))

    for n in bu_nodes:
        nid = str(n[0])
        current = parse_str_list(n[3])
        has_user = any(ref.lower() in uids for ref in current)
        should_lead = nid in target_uuids
        if should_lead and not has_user:
            await _update_bu_ontology_leads(conn, nid, [*current, principal_id])
        elif not should_lead and has_user:
            await _update_bu_ontology_leads(
                conn, nid, [ref for ref in current if ref.lower() not in uids]
            )


async def hydrate_iam_accounts_ontology_led_bus(
    conn: AsyncConnection,
    accounts: Sequence[IamAccountRecord],
) -> list[IamAccountRecord]:
    """Hydrate `ontology_led_bu_ids` on `IamAccountRecord` items from `org_units`."""
    ou_reg = (await conn.execute(sa.text("SELECT to_regclass('public.org_units')"))).scalar()
    if ou_reg is None or not accounts:
        return list(accounts)

    rows = (
        await conn.execute(
            sa.text("SELECT id, ontology_lead_user_ids_jsonb FROM org_units WHERE unit_type = 'BU'")
        )
    ).fetchall()

    hydrated: list[IamAccountRecord] = []
    for acc in accounts:
        uids = {
            acc.principal_id.strip().lower(),
            *((acc.email.strip().lower(),) if acc.email and acc.email.strip() else ()),
        }
        onto_bus: list[str] = []
        for row in rows:
            uid = str(row[0])
            leads = parse_str_list(row[1])
            if any(ref.lower() in uids for ref in leads):
                onto_bus.append(uid)
        hydrated.append(replace(acc, ontology_led_bu_ids=tuple(onto_bus)))
    return hydrated


__all__ = [
    "hydrate_iam_accounts_ontology_led_bus",
    "resolve_canonical_ontology_lead_user_ids",
    "sync_iam_ontology_lead_roles_from_org_units",
    "sync_ontology_lead_bus_from_iam_account",
]
