"""PostgreSQL 18 repository for `permission_broker_policies` and `permission_broker_tickets`.

Aligned on Alembic migrations `0004_story_1_4`, `0013/0014_story_3_2e`,
and `0020_story_4_4_contract` (`request_url` column, `REM-13`).
"""

from __future__ import annotations

from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.permissions._internal._sql_permission_broker_queries import (
    SQL_INSERT_POLICY,
    SQL_UPDATE_POLICY,
    SQL_UPSERT_TICKET,
    coerce_broker_uuid,
    ensure_scheme_row,
    resolve_nullable_user,
    resolve_nullable_workspace,
    resolve_required_user,
    row_to_policy,
    row_to_ticket,
)
from orcia_core.permissions.broker_models import (
    BrokerStepState,
    BrokerTicketStatus,
    PermissionBrokerPolicy,
    PermissionBrokerTicket,
)


class SqlPermissionBrokerRepository:
    """Async SQLAlchemy PG18 repository for Permission Broker policies and tickets."""

    def __init__(self, engine: object) -> None:
        self._engine: AsyncEngine = cast(AsyncEngine, engine)

    async def pg_tables_ready(self) -> bool:
        """Return `True` when `permission_broker_tickets` exists in PG18."""
        async with self._engine.connect() as conn:
            reg = (
                await conn.execute(
                    sa.text("SELECT to_regclass('public.permission_broker_tickets')")
                )
            ).scalar()
            return reg is not None

    async def _upsert_policy_on_conn(
        self, conn: AsyncConnection, policy: PermissionBrokerPolicy, *, update_existing: bool
    ) -> PermissionBrokerPolicy:
        await ensure_scheme_row(conn, policy.connector_scheme)
        admin_uuid = await resolve_nullable_user(conn, policy.approved_by_admin_id)
        anchor_uuid = await resolve_nullable_user(conn, policy.human_anchor_author_id)
        existing = (
            (
                await conn.execute(
                    sa.text(
                        "SELECT * FROM permission_broker_policies "
                        "WHERE policy_key = :pk OR uri_pattern = :up LIMIT 1"
                    ),
                    {"pk": policy.policy_key, "up": policy.uri_pattern},
                )
            )
            .mappings()
            .first()
        )
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
        if existing is not None:
            if not update_existing:
                return row_to_policy(existing)
            row = (
                (await conn.execute(SQL_UPDATE_POLICY, {**params, "id": str(existing["id"])}))
                .mappings()
                .one()
            )
            return row_to_policy(row)
        row = (
            (
                await conn.execute(
                    SQL_INSERT_POLICY,
                    {**params, "id": str(coerce_broker_uuid(policy.id)), "pk": policy.policy_key},
                )
            )
            .mappings()
            .one()
        )
        return row_to_policy(row)

    async def ensure_policies_seeded(
        self, policies: tuple[PermissionBrokerPolicy, ...]
    ) -> list[PermissionBrokerPolicy]:
        """Idempotently seed default/fallback policies into `permission_broker_policies`."""
        async with self._engine.begin() as conn:
            for pol in policies:
                await self._upsert_policy_on_conn(conn, pol, update_existing=False)
            rows = (
                (
                    await conn.execute(
                        sa.text("SELECT * FROM permission_broker_policies ORDER BY created_at ASC")
                    )
                )
                .mappings()
                .all()
            )
            return [row_to_policy(r) for r in rows]

    async def upsert_policy(self, policy: PermissionBrokerPolicy) -> PermissionBrokerPolicy:
        """Persist or update a KB policy in `permission_broker_policies`."""
        async with self._engine.begin() as conn:
            return await self._upsert_policy_on_conn(conn, policy, update_existing=True)

    async def list_policies(self) -> list[PermissionBrokerPolicy]:
        """List all persisted policies from PG18."""
        async with self._engine.connect() as conn:
            rows = (
                (
                    await conn.execute(
                        sa.text("SELECT * FROM permission_broker_policies ORDER BY created_at ASC")
                    )
                )
                .mappings()
                .all()
            )
            return [row_to_policy(r) for r in rows]

    async def find_workspace_datasource(
        self, target_uri: str, *, workspace_id: str | None = None
    ) -> dict[str, Any] | None:
        """Look up matching `workspace_datasources` row for `target_uri`."""
        async with self._engine.connect() as conn:
            params: dict[str, Any] = {"uri": target_uri.strip()}
            ws_clause = ""
            if workspace_id:
                ws_uuid = await resolve_nullable_workspace(conn, workspace_id)
                if ws_uuid is not None:
                    ws_clause = "AND workspace_id = CAST(:ws AS uuid)"
                    params["ws"] = str(ws_uuid)
            row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT id, workspace_id, alias, scheme, uri, role, execution_identity "
                            "FROM workspace_datasources "
                            f"WHERE (uri = :uri OR :uri LIKE uri || '%') {ws_clause} "
                            "ORDER BY length(uri) DESC LIMIT 1"
                        ),
                        params,
                    )
                )
                .mappings()
                .first()
            )
            return dict(row) if row is not None else None

    async def list_tickets(self, workspace_id: str | None = None) -> list[PermissionBrokerTicket]:
        """List persisted Permission Broker tickets from PG18."""
        async with self._engine.connect() as conn:
            if workspace_id:
                ws_uuid = await resolve_nullable_workspace(conn, workspace_id)
                if ws_uuid is not None:
                    rows = (
                        (
                            await conn.execute(
                                sa.text(
                                    "SELECT * FROM permission_broker_tickets "
                                    "WHERE workspace_id IS NULL "
                                    "OR workspace_id = CAST(:ws AS uuid) "
                                    "ORDER BY created_at DESC"
                                ),
                                {"ws": str(ws_uuid)},
                            )
                        )
                        .mappings()
                        .all()
                    )
                    return [row_to_ticket(r) for r in rows]
            rows = (
                (
                    await conn.execute(
                        sa.text("SELECT * FROM permission_broker_tickets ORDER BY created_at DESC")
                    )
                )
                .mappings()
                .all()
            )
            return [row_to_ticket(r) for r in rows]

    async def insert_ticket(
        self,
        ticket: PermissionBrokerTicket,
        *,
        policy: PermissionBrokerPolicy,
        requester_email: str | None = None,
    ) -> PermissionBrokerTicket:
        """Persist a blocked step ticket into `permission_broker_tickets` (`request_url`)."""
        async with self._engine.begin() as conn:
            await ensure_scheme_row(conn, ticket.connector_scheme)
            persisted_pol = await self._upsert_policy_on_conn(conn, policy, update_existing=False)
            req_uuid = await resolve_required_user(
                conn, user_id=ticket.requester_user_id, email=requester_email
            )
            ws_uuid = await resolve_nullable_workspace(conn, ticket.workspace_id)
            row = (
                (
                    await conn.execute(
                        SQL_UPSERT_TICKET,
                        {
                            "id": str(coerce_broker_uuid(ticket.id)),
                            "ticket_key": ticket.ticket_key[:128],
                            "ws": str(ws_uuid) if ws_uuid is not None else None,
                            "req_user": str(req_uuid),
                            "pol_id": str(coerce_broker_uuid(persisted_pol.id)),
                            "step_key": ticket.step_key[:128],
                            "step_num": ticket.step_number,
                            "step_state": ticket.step_state,
                            "status": ticket.status,
                            "target_uri": ticket.target_uri,
                            "scheme": ticket.connector_scheme,
                            "exec_id": ticket.execution_identity,
                            "http_status": ticket.upstream_http_status,
                            "req_role": ticket.required_role[:128],
                            "approver": ticket.approver_team[:128],
                            "sla": ticket.sla_hours,
                            "req_url": ticket.request_url,
                            "hint": ticket.permission_broker_hint,
                            "proc": ticket.procedure_markdown,
                        },
                    )
                )
                .mappings()
                .one()
            )
            return row_to_ticket(row)

    async def get_ticket(self, ticket_id_or_key: str) -> PermissionBrokerTicket | None:
        """Fetch a ticket by UUID `id` or `ticket_key`."""
        cleaned = ticket_id_or_key.strip()
        async with self._engine.connect() as conn:
            row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT * FROM permission_broker_tickets "
                            "WHERE id::text = :k OR ticket_key = :k LIMIT 1"
                        ),
                        {"k": cleaned},
                    )
                )
                .mappings()
                .first()
            )
            return row_to_ticket(row) if row is not None else None

    async def update_ticket_state(
        self,
        ticket_id_or_key: str,
        *,
        step_state: BrokerStepState,
        status: BrokerTicketStatus,
    ) -> PermissionBrokerTicket | None:
        """Transition ticket `step_state` and `status` in PG18."""
        cleaned = ticket_id_or_key.strip()
        async with self._engine.begin() as conn:
            row = (
                (
                    await conn.execute(
                        sa.text(
                            "UPDATE permission_broker_tickets "
                            "SET step_state = :step_state, status = :status, updated_at = NOW() "
                            "WHERE id::text = :k OR ticket_key = :k RETURNING *"
                        ),
                        {"k": cleaned, "step_state": step_state, "status": status},
                    )
                )
                .mappings()
                .first()
            )
            return row_to_ticket(row) if row is not None else None


__all__ = ["SqlPermissionBrokerRepository"]
