"""SQL queries & row mappers for `SqlPermissionBrokerRepository` (`0004`, `0013/14`, `0020`)."""

from __future__ import annotations

from typing import Literal, cast
from uuid import UUID, uuid5

import sqlalchemy as sa
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.permissions.broker_models import (
    BrokerStepState,
    BrokerTicketStatus,
    PermissionBrokerPolicy,
    PermissionBrokerTicket,
)
from orcia_core.permissions.errors import ResourceNotFoundError
from orcia_core.permissions.models import ExecutionIdentityMode
from orcia_kernel.ids import new_uuid7_str

_ORCIA_BROKER_NS = UUID("0195f000-0000-7000-8000-00000000b000")

SQL_UPDATE_POLICY = sa.text(
    """
    UPDATE permission_broker_policies
       SET uri_pattern = :up,
           connector_scheme = :scheme,
           required_role = :role,
           approver_team = :team,
           request_url_template = :tpl,
           sla_hours = :sla,
           procedure_markdown = :proc,
           service_principal_allowed = :sp,
           approved_by_admin_id = CAST(:admin AS uuid),
           human_anchor_author_id = CAST(:anchor AS uuid),
           human_anchor_signature = :sig,
           freshness_ttl_days = :ttl
     WHERE id = CAST(:id AS uuid)
    RETURNING *
    """
)

SQL_INSERT_POLICY = sa.text(
    """
    INSERT INTO permission_broker_policies (
        id, policy_key, uri_pattern, connector_scheme,
        required_role, approver_team, request_url_template,
        sla_hours, procedure_markdown, service_principal_allowed,
        approved_by_admin_id, human_anchor_author_id,
        human_anchor_signature, freshness_ttl_days
    ) VALUES (
        CAST(:id AS uuid), :pk, :up, :scheme,
        :role, :team, :tpl, :sla, :proc, :sp,
        CAST(:admin AS uuid), CAST(:anchor AS uuid), :sig, :ttl
    )
    ON CONFLICT DO NOTHING
    RETURNING *
    """
)

SQL_UPSERT_TICKET = sa.text(
    """
    INSERT INTO permission_broker_tickets (
        id, ticket_key, workspace_id, requester_user_id, policy_id,
        step_key, step_number, step_state, status, target_uri,
        connector_scheme, execution_identity, upstream_http_status,
        required_role, approver_team, sla_hours, request_url,
        permission_broker_hint, procedure_markdown
    ) VALUES (
        CAST(:id AS uuid), :ticket_key, CAST(:ws AS uuid),
        CAST(:req_user AS uuid), CAST(:pol_id AS uuid),
        :step_key, :step_num, :step_state, :status, :target_uri,
        :scheme, :exec_id, :http_status,
        :req_role, :approver, :sla, :req_url, :hint, :proc
    )
    ON CONFLICT (ticket_key) DO UPDATE SET
        step_state = EXCLUDED.step_state,
        status = EXCLUDED.status,
        request_url = EXCLUDED.request_url,
        updated_at = NOW()
    RETURNING *
    """
)


def coerce_broker_uuid(raw_id: str | None) -> UUID:
    """Convert string ID to UUID (deterministic UUIDv5 for non-UUID keys)."""
    if raw_id is None or not raw_id.strip():
        return UUID(new_uuid7_str())
    cleaned = raw_id.strip()
    try:
        return UUID(cleaned)
    except ValueError:
        return uuid5(_ORCIA_BROKER_NS, cleaned)


async def ensure_scheme_row(conn: AsyncConnection, scheme: str) -> None:
    """Idempotently ensure `scheme` exists in `connector_schemes`."""
    norm = scheme.strip().lower()
    await conn.execute(
        sa.text(
            "INSERT INTO connector_schemes (id, scheme, display_name, pack_name, is_active) "
            "VALUES (CAST(:id AS uuid), :scheme, :name, 'orcia-core', TRUE) "
            "ON CONFLICT (scheme) DO NOTHING"
        ),
        {
            "id": str(uuid5(_ORCIA_BROKER_NS, f"scheme:{norm}")),
            "scheme": norm,
            "name": f"{norm.upper()} Connector",
        },
    )


async def resolve_nullable_user(conn: AsyncConnection, user_id: str | None) -> UUID | None:
    """Resolve `users.id` if present in PG18, else return `None`."""
    if not user_id or not user_id.strip():
        return None
    row = (
        await conn.execute(
            sa.text("SELECT id FROM users WHERE id::text = :uid LIMIT 1"),
            {"uid": user_id.strip()},
        )
    ).first()
    return UUID(str(row[0])) if row is not None else None


async def resolve_required_user(
    conn: AsyncConnection, *, user_id: str, email: str | None = None
) -> UUID:
    """Resolve `users.id` by ID or email, falling back to first user in PG18."""
    row = (
        await conn.execute(
            sa.text(
                "SELECT id FROM users "
                "WHERE id::text = :uid OR (:email <> '' AND lower(email) = lower(:email)) "
                "LIMIT 1"
            ),
            {"uid": user_id.strip(), "email": (email or "").strip()},
        )
    ).first()
    if row is not None:
        return UUID(str(row[0]))
    fallback = (
        await conn.execute(sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1"))
    ).first()
    if fallback is not None:
        return UUID(str(fallback[0]))
    raise ResourceNotFoundError(detail_code="ERR_BROKER_NO_DB_USER")


async def resolve_nullable_workspace(
    conn: AsyncConnection, workspace_id: str | None
) -> UUID | None:
    """Resolve `workspaces.id` by UUID or slug if present."""
    if not workspace_id or not workspace_id.strip():
        return None
    row = (
        await conn.execute(
            sa.text("SELECT id FROM workspaces WHERE id::text = :ws OR slug = :ws LIMIT 1"),
            {"ws": workspace_id.strip()},
        )
    ).first()
    return UUID(str(row[0])) if row is not None else None


def row_to_policy(row: RowMapping) -> PermissionBrokerPolicy:
    """Map PG18 `permission_broker_policies` row into `PermissionBrokerPolicy`."""
    return PermissionBrokerPolicy(
        id=str(row["id"]),
        policy_key=str(row["policy_key"]),
        uri_pattern=str(row["uri_pattern"]),
        connector_scheme=str(row["connector_scheme"]),
        required_role=str(row["required_role"]),
        approver_team=str(row["approver_team"]),
        request_url_template=str(row["request_url_template"]),
        sla_hours=int(row["sla_hours"]),
        procedure_markdown=str(row["procedure_markdown"] or ""),
        service_principal_allowed=bool(row["service_principal_allowed"]),
        approved_by_admin_id=(
            str(row["approved_by_admin_id"]) if row["approved_by_admin_id"] is not None else None
        ),
        human_anchor_author_id=(
            str(row["human_anchor_author_id"])
            if row["human_anchor_author_id"] is not None
            else None
        ),
        human_anchor_signature=(
            str(row["human_anchor_signature"])
            if row["human_anchor_signature"] is not None
            else None
        ),
        freshness_ttl_days=int(row["freshness_ttl_days"]),
    )


def row_to_ticket(row: RowMapping) -> PermissionBrokerTicket:
    """Map PG18 `permission_broker_tickets` row (`request_url`) into `PermissionBrokerTicket`."""
    req_url = str(row["request_url"])
    status_raw = int(row["upstream_http_status"])
    http_status: Literal[401, 403] = 401 if status_raw == 401 else 403
    return PermissionBrokerTicket(
        id=str(row["id"]),
        ticket_key=str(row["ticket_key"]),
        workspace_id=str(row["workspace_id"]) if row["workspace_id"] is not None else None,
        requester_user_id=str(row["requester_user_id"]),
        policy_id=str(row["policy_id"]),
        step_key=str(row["step_key"]),
        step_number=int(row["step_number"]),
        step_state=cast(BrokerStepState, str(row["step_state"])),
        status=cast(BrokerTicketStatus, str(row["status"])),
        target_uri=str(row["target_uri"]),
        connector_scheme=str(row["connector_scheme"]),
        execution_identity=cast(ExecutionIdentityMode, str(row["execution_identity"])),
        upstream_http_status=http_status,
        required_role=str(row["required_role"]),
        approver_team=str(row["approver_team"]),
        sla_hours=int(row["sla_hours"]),
        jira_request_url=req_url,
        permission_broker_hint=str(row["permission_broker_hint"]),
        procedure_markdown=str(row["procedure_markdown"] or ""),
        request_url=req_url,
    )


async def upsert_policy_on_conn(
    conn: AsyncConnection, policy: PermissionBrokerPolicy, *, update_existing: bool
) -> PermissionBrokerPolicy:
    """Idempotently insert/update `permission_broker_policies` safe against concurrent seeds."""
    await ensure_scheme_row(conn, policy.connector_scheme)
    admin_uuid = await resolve_nullable_user(conn, policy.approved_by_admin_id)
    anchor_uuid = await resolve_nullable_user(conn, policy.human_anchor_author_id)
    pol_uuid = str(coerce_broker_uuid(policy.id))
    find_sql = sa.text(
        "SELECT * FROM permission_broker_policies "
        "WHERE pack_bundle_id IS NULL "
        "AND (id = CAST(:id AS uuid) OR policy_key = :pk OR uri_pattern = :up) LIMIT 1"
    )
    find_args = {"id": pol_uuid, "pk": policy.policy_key, "up": policy.uri_pattern}
    existing = (await conn.execute(find_sql, find_args)).mappings().first()
    params = {
        "up": policy.uri_pattern,
        "scheme": policy.connector_scheme,
        "role": policy.required_role,
        "team": policy.approver_team,
        "tpl": policy.request_url_template,
        "sla": policy.sla_hours,
        "proc": policy.procedure_markdown,
        "sp": policy.service_principal_allowed,
        "admin": str(admin_uuid) if admin_uuid is not None else None,
        "anchor": str(anchor_uuid) if anchor_uuid is not None else None,
        "sig": policy.human_anchor_signature,
        "ttl": policy.freshness_ttl_days,
    }
    if existing is None:
        ins_res = await conn.execute(
            SQL_INSERT_POLICY, {**params, "id": pol_uuid, "pk": policy.policy_key}
        )
        inserted = ins_res.mappings().first()
        if inserted is not None:
            return row_to_policy(inserted)
        existing = (await conn.execute(find_sql, find_args)).mappings().one()
    if not update_existing:
        return row_to_policy(existing)
    row = (
        (await conn.execute(SQL_UPDATE_POLICY, {**params, "id": str(existing["id"])}))
        .mappings()
        .one()
    )
    return row_to_policy(row)
