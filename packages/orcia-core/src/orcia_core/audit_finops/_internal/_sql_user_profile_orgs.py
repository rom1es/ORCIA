"""PostgreSQL 18 user identity & org-unit attachment queries (`Story 20.4`)."""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.audit_finops._internal._sql_scope_filter import is_missing_table_error
from orcia_core.audit_finops.user_profile_service import derive_user_handle
from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.core.audit_finops.user_profile")


def _parse_json_str_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str) and raw.strip():
        try:
            decoded = json.loads(raw)
        except ValueError:
            return []
        if isinstance(decoded, list):
            return [str(x).strip() for x in decoded if str(x).strip()]
    return []


async def load_user_identity_and_orgs(
    conn: AsyncConnection,
    *,
    user_id: str,
    user_email: str,
    display_name: str,
    roles: tuple[str, ...],
) -> tuple[
    str,
    str,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    """Load user display name, email, roles and BU/Team attachments from PG18."""
    eff_display_name = display_name
    eff_email = user_email
    eff_roles: list[str] = list(dict.fromkeys(r for r in roles if r))
    user_keys: set[str] = {k.strip().lower() for k in (user_id, user_email) if k and k.strip()}

    try:
        iam_row = (
            await conn.execute(
                sa.text(
                    """
                    SELECT principal_id, display_name, email, roles_jsonb
                    FROM iam_accounts
                    WHERE LOWER(principal_id) = LOWER(:uid)
                       OR (:uemail <> '' AND LOWER(email) = LOWER(:uemail))
                    LIMIT 1
                    """
                ),
                {"uid": user_id, "uemail": user_email},
            )
        ).fetchone()
        if iam_row is not None:
            if iam_row[0]:
                user_keys.add(str(iam_row[0]).strip().lower())
            if iam_row[1] and not eff_display_name.strip():
                eff_display_name = str(iam_row[1]).strip()
            if iam_row[2] and not eff_email.strip():
                eff_email = str(iam_row[2]).strip()
                user_keys.add(eff_email.lower())
            for r in _parse_json_str_list(iam_row[3]):
                if r not in eff_roles:
                    eff_roles.append(r)
    except Exception as exc:
        if not is_missing_table_error(exc):
            logger.warning("user_profile_iam_lookup_failed", error_type=type(exc).__name__)

    led_bus: list[str] = []
    ontology_bus: list[str] = []
    led_teams: list[str] = []
    member_teams: list[str] = []

    try:
        ou_rows = (
            await conn.execute(
                sa.text(
                    """
                    SELECT name, unit_type, lead_user_id,
                           lead_user_ids_jsonb, ontology_lead_user_ids_jsonb,
                           member_user_ids_jsonb
                    FROM org_units
                    ORDER BY unit_type ASC, name ASC
                    """
                )
            )
        ).fetchall()
        for row in ou_rows:
            name = str(row[0] or "").strip()
            unit_type = str(row[1] or "").strip().upper()
            if not name:
                continue
            lead_multi = {k.lower() for k in _parse_json_str_list(row[3])}
            if row[2] and str(row[2]).strip():
                lead_multi.add(str(row[2]).strip().lower())
            onto_leads = {k.lower() for k in _parse_json_str_list(row[4])}
            members = {k.lower() for k in _parse_json_str_list(row[5])}

            if user_keys & lead_multi:
                if unit_type in ("BU", "TRIBE") and name not in led_bus:
                    led_bus.append(name)
                elif unit_type in ("TEAM", "SUB_TEAM") and name not in led_teams:
                    led_teams.append(name)
            if (
                unit_type in ("BU", "TRIBE")
                and (user_keys & onto_leads)
                and name not in ontology_bus
            ):
                ontology_bus.append(name)
            if (
                unit_type in ("TEAM", "SUB_TEAM")
                and (user_keys & members)
                and name not in member_teams
                and name not in led_teams
            ):
                member_teams.append(name)
    except Exception as exc:
        if not is_missing_table_error(exc):
            logger.warning("user_profile_org_units_lookup_failed", error_type=type(exc).__name__)

    return (
        eff_display_name or derive_user_handle(eff_email, eff_display_name),
        eff_email,
        tuple(eff_roles) if eff_roles else ("CONTRIBUTOR",),
        tuple(led_bus),
        tuple(ontology_bus),
        tuple(led_teams),
        tuple(member_teams),
    )
