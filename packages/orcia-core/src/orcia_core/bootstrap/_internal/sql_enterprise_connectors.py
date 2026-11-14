"""PostgreSQL 18 persistence adapter for Enterprise Connectors (Story 17.4).

Provides:
- CRUD for `enterprise_connectors` (`AES-256-GCM` via `PassthroughVaultCipher`);
- User account profile resolution linking IAM accounts to FinOps teams;
- User personal passthrough tokens (`user_connector_passthrough_tokens`);
- DDL helper `ensure_enterprise_connectors_schema` for tests.
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.kernel import new_uuid7_str
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.enterprise_connectors import (
    ConnectorSecretStatus,
    EnterpriseConnectorAuthMode,
    EnterpriseConnectorKind,
    EnterpriseConnectorRecord,
    UserPassthroughConnectorView,
    compute_secret_fingerprint,
    extract_url_host,
    pack_encrypted_secret,
    validate_safe_connector_base_url,
)
from orcia_core.permissions.errors import (
    ResourceNotFoundError,
    ValidationDomainError,
)


@dataclass(frozen=True, slots=True)
class UserAccountOrgUnitSummary:
    """Read-only view of a team or org unit attached to a user for FinOps transparency."""

    id: str
    slug: str
    name: str
    unit_type: str
    billing_enabled: bool
    is_lead: bool = False


@dataclass(frozen=True, slots=True)
class UserAccountProfileRecord:
    """User account identity and FinOps team attachments for `👤 Mon Compte`."""

    principal_id: str
    display_name: str
    email: str
    roles: tuple[str, ...]
    teams: tuple[UserAccountOrgUnitSummary, ...]
    billing_org_units: tuple[UserAccountOrgUnitSummary, ...]


async def ensure_enterprise_connectors_schema(conn: AsyncConnection) -> None:
    """Idempotently ensure `enterprise_connectors` and `user_connector_passthrough_tokens` exist."""
    await conn.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS enterprise_connectors (
                id UUID PRIMARY KEY,
                connector_kind VARCHAR(32) NOT NULL,
                name VARCHAR(160) NOT NULL,
                base_url VARCHAR(512) NOT NULL,
                auth_mode VARCHAR(32) NOT NULL,
                encrypted_admin_secret TEXT NULL,
                admin_secret_fingerprint VARCHAR(32) NULL,
                admin_secret_updated_at TIMESTAMPTZ NULL,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    await conn.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS user_connector_passthrough_tokens (
                id UUID PRIMARY KEY,
                user_id VARCHAR(128) NOT NULL,
                connector_id UUID NOT NULL REFERENCES enterprise_connectors(id) ON DELETE CASCADE,
                external_author_login VARCHAR(160) NULL,
                encrypted_token TEXT NOT NULL,
                secret_fingerprint VARCHAR(32) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (user_id, connector_id)
            );
            """
        )
    )


def _row_to_connector_record(row: Any) -> EnterpriseConnectorRecord:
    has_secret = bool(row[5])
    return EnterpriseConnectorRecord(
        id=str(row[0]),
        connector_kind=cast(EnterpriseConnectorKind, str(row[1])),
        name=str(row[2]),
        base_url=str(row[3]),
        auth_mode=cast(EnterpriseConnectorAuthMode, str(row[4])),
        admin_secret_status=ConnectorSecretStatus(
            configured=has_secret,
            fingerprint=str(row[6]) if (has_secret and row[6]) else None,
            updated_at_iso=row[7].isoformat() if (has_secret and row[7]) else None,
        ),
        enabled=bool(row[8]),
        created_at_iso=row[9].isoformat() if row[9] else "",
        updated_at_iso=row[10].isoformat() if row[10] else "",
    )


async def list_enterprise_connectors_from_postgres18(
    engine: AsyncEngine,
) -> list[EnterpriseConnectorRecord]:
    """List all platform-level Enterprise Connectors."""
    async with engine.begin() as conn:
        await ensure_enterprise_connectors_schema(conn)
        rows = (
            await conn.execute(
                sa.text(
                    """
                    SELECT id, connector_kind, name, base_url, auth_mode,
                           encrypted_admin_secret, admin_secret_fingerprint,
                           admin_secret_updated_at, enabled, created_at, updated_at
                    FROM enterprise_connectors
                    ORDER BY created_at ASC, name ASC
                    """
                )
            )
        ).fetchall()
        return [_row_to_connector_record(r) for r in rows]


async def create_enterprise_connector_on_postgres18(
    engine: AsyncEngine,
    *,
    cipher: PassthroughVaultCipher,
    connector_kind: EnterpriseConnectorKind,
    name: str,
    base_url: str,
    auth_mode: EnterpriseConnectorAuthMode,
    admin_secret_value: str | None = None,
    enabled: bool = True,
    instance: str | None = None,
) -> EnterpriseConnectorRecord:
    """Create a new platform-level Enterprise Connector with optional AES-256-GCM secret."""
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValidationDomainError(
            detail_override="Connector name is required.",
            instance=instance,
        )
    safe_url = validate_safe_connector_base_url(base_url, instance=instance)
    cid = new_uuid7_str()
    enc_secret: str | None = None
    fingerprint: str | None = None
    if admin_secret_value and admin_secret_value.strip():
        plain = admin_secret_value.strip()
        enc_secret = pack_encrypted_secret(
            cipher,
            owner_id=f"admin:{cid}",
            plaintext=plain,
            scheme=connector_kind,
            host=extract_url_host(safe_url),
        )
        fingerprint = compute_secret_fingerprint(cid, plain)

    async with engine.begin() as conn:
        await ensure_enterprise_connectors_schema(conn)
        row = (
            await conn.execute(
                sa.text(
                    f"""
                    INSERT INTO enterprise_connectors (
                        id, connector_kind, name, base_url, auth_mode,
                        encrypted_admin_secret, admin_secret_fingerprint,
                        admin_secret_updated_at, enabled, created_at, updated_at
                    )
                    VALUES (
                        :id, :kind, :name, :base_url, :auth_mode,
                        :enc_secret, :fingerprint,
                        {"NOW()" if enc_secret is not None else "NULL"},
                        :enabled, NOW(), NOW()
                    )
                    RETURNING id, connector_kind, name, base_url, auth_mode,
                              encrypted_admin_secret, admin_secret_fingerprint,
                              admin_secret_updated_at, enabled, created_at, updated_at
                    """
                ),
                {
                    "id": UUID(cid),
                    "kind": connector_kind,
                    "name": cleaned_name,
                    "base_url": safe_url,
                    "auth_mode": auth_mode,
                    "enc_secret": enc_secret,
                    "fingerprint": fingerprint,
                    "enabled": enabled,
                },
            )
        ).fetchone()
        assert row is not None
        return _row_to_connector_record(row)


async def update_enterprise_connector_on_postgres18(
    engine: AsyncEngine,
    connector_id: str,
    *,
    cipher: PassthroughVaultCipher,
    name: str | None = None,
    base_url: str | None = None,
    auth_mode: EnterpriseConnectorAuthMode | None = None,
    enabled: bool | None = None,
    admin_secret_value: str | None = None,
    clear_admin_secret: bool = False,
    instance: str | None = None,
) -> EnterpriseConnectorRecord:
    """Update an existing Enterprise Connector and manage its AES-256-GCM admin secret."""
    cid_uuid = UUID(connector_id)
    async with engine.begin() as conn:
        await ensure_enterprise_connectors_schema(conn)
        current = (
            await conn.execute(
                sa.text(
                    """
                    SELECT id, connector_kind, name, base_url, auth_mode,
                           encrypted_admin_secret, admin_secret_fingerprint,
                           admin_secret_updated_at, enabled, created_at, updated_at
                    FROM enterprise_connectors
                    WHERE id = :id
                    FOR UPDATE
                    """
                ),
                {"id": cid_uuid},
            )
        ).fetchone()
        if current is None:
            raise ResourceNotFoundError(instance=instance)

        next_url = (
            validate_safe_connector_base_url(base_url, instance=instance)
            if base_url is not None
            else str(current[3])
        )
        next_name = name.strip() if name and name.strip() else str(current[2])
        next_mode = auth_mode if auth_mode is not None else str(current[4])
        next_enabled = enabled if enabled is not None else bool(current[8])

        enc_secret: str | None = current[5]
        fingerprint: str | None = current[6]
        update_secret_timestamp = False

        if clear_admin_secret:
            enc_secret = None
            fingerprint = None
            update_secret_timestamp = True
        elif admin_secret_value and admin_secret_value.strip():
            plain = admin_secret_value.strip()
            enc_secret = pack_encrypted_secret(
                cipher,
                owner_id=f"admin:{connector_id}",
                plaintext=plain,
                scheme=str(current[1]),
                host=extract_url_host(next_url),
            )
            fingerprint = compute_secret_fingerprint(connector_id, plain)
            update_secret_timestamp = True

        ts_col = "NOW()" if update_secret_timestamp else "admin_secret_updated_at"
        row = (
            await conn.execute(
                sa.text(
                    f"""
                    UPDATE enterprise_connectors
                    SET name = :name,
                        base_url = :base_url,
                        auth_mode = :auth_mode,
                        enabled = :enabled,
                        encrypted_admin_secret = :enc_secret,
                        admin_secret_fingerprint = :fingerprint,
                        admin_secret_updated_at = {ts_col},
                        updated_at = NOW()
                    WHERE id = :id
                    RETURNING id, connector_kind, name, base_url, auth_mode,
                              encrypted_admin_secret, admin_secret_fingerprint,
                              admin_secret_updated_at, enabled, created_at, updated_at
                    """
                ),
                {
                    "id": cid_uuid,
                    "name": next_name,
                    "base_url": next_url,
                    "auth_mode": next_mode,
                    "enabled": next_enabled,
                    "enc_secret": enc_secret,
                    "fingerprint": fingerprint,
                },
            )
        ).fetchone()
        assert row is not None
        return _row_to_connector_record(row)


async def delete_enterprise_connector_on_postgres18(
    engine: AsyncEngine,
    connector_id: str,
    *,
    instance: str | None = None,
) -> None:
    """Delete an Enterprise Connector and cascade its passthrough tokens."""
    cid_uuid = UUID(connector_id)
    async with engine.begin() as conn:
        await ensure_enterprise_connectors_schema(conn)
        res = await conn.execute(
            sa.text("DELETE FROM enterprise_connectors WHERE id = :id"),
            {"id": cid_uuid},
        )
        if res.rowcount == 0:
            raise ResourceNotFoundError(instance=instance)


async def get_user_account_profile_from_postgres18(
    engine: AsyncEngine,
    *,
    user_id: str,
    default_roles: Sequence[str] = ("CONTRIBUTOR",),
) -> UserAccountProfileRecord:
    """Resolve user profile identity, active roles, and FinOps team attachments."""
    uid_norm = user_id.strip().lower()
    async with engine.begin() as conn:
        await ensure_enterprise_connectors_schema(conn)
        acc_row = (
            await conn.execute(
                sa.text(
                    """
                    SELECT principal_id, display_name, email, roles_jsonb, status
                    FROM iam_accounts
                    WHERE LOWER(principal_id) = :uid OR LOWER(email) = :uid
                    LIMIT 1
                    """
                ),
                {"uid": uid_norm},
            )
        ).fetchone()

        if acc_row is not None:
            principal_id = str(acc_row[0])
            display_name = str(acc_row[1]) if acc_row[1] else principal_id
            email = str(acc_row[2]) if acc_row[2] else principal_id
            roles_raw = acc_row[3]
            if isinstance(roles_raw, list):
                roles = tuple(str(r) for r in roles_raw)
            elif isinstance(roles_raw, str):
                try:
                    roles = tuple(json.loads(roles_raw))
                except ValueError:
                    roles = tuple(default_roles)
            else:
                roles = tuple(default_roles)
        else:
            principal_id = user_id.strip()
            display_name = user_id.strip().split("@")[0].capitalize()
            email = user_id.strip()
            roles = tuple(default_roles)

        # Load org units to resolve attached teams and FinOps billing units
        ou_rows = (
            await conn.execute(
                sa.text(
                    """
                    SELECT id, slug, name, unit_type, billing_enabled,
                           lead_user_id, member_user_ids_jsonb
                    FROM org_units
                    ORDER BY unit_type ASC, name ASC
                    """
                )
            )
        ).fetchall()

        teams: list[UserAccountOrgUnitSummary] = []
        billing_units: list[UserAccountOrgUnitSummary] = []
        user_keys = {uid_norm, principal_id.lower(), email.lower()} - {""}

        for r in ou_rows:
            lead_id = str(r[5]).strip().lower() if r[5] else ""
            members_raw = r[6]
            members_list: list[str] = []
            if isinstance(members_raw, list):
                members_list = [str(m).strip().lower() for m in members_raw]
            elif isinstance(members_raw, str):
                with contextlib.suppress(ValueError):
                    members_list = [str(m).strip().lower() for m in json.loads(members_raw)]

            is_lead = lead_id in user_keys
            is_member = bool(user_keys & set(members_list))
            if is_lead or is_member:
                summary = UserAccountOrgUnitSummary(
                    id=str(r[0]),
                    slug=str(r[1]),
                    name=str(r[2]),
                    unit_type=str(r[3]),
                    billing_enabled=bool(r[4]),
                    is_lead=is_lead,
                )
                if str(r[3]).upper() == "TEAM":
                    teams.append(summary)
                if bool(r[4]):
                    billing_units.append(summary)

        return UserAccountProfileRecord(
            principal_id=principal_id,
            display_name=display_name,
            email=email,
            roles=roles,
            teams=tuple(teams),
            billing_org_units=tuple(billing_units),
        )


async def list_user_passthrough_tokens_from_postgres18(
    engine: AsyncEngine,
    *,
    user_id: str,
) -> list[UserPassthroughConnectorView]:
    """List per-user passthrough connection status across all enabled connectors."""
    uid_norm = user_id.strip().lower()
    async with engine.begin() as conn:
        await ensure_enterprise_connectors_schema(conn)
        rows = (
            await conn.execute(
                sa.text(
                    """
                    SELECT c.id, c.connector_kind, c.name, c.base_url, c.auth_mode,
                           t.external_author_login, t.secret_fingerprint, t.status, t.updated_at
                    FROM enterprise_connectors c
                    LEFT JOIN user_connector_passthrough_tokens t
                        ON t.connector_id = c.id AND LOWER(t.user_id) = :uid
                    WHERE c.enabled = TRUE
                    ORDER BY c.created_at ASC, c.name ASC
                    """
                ),
                {"uid": uid_norm},
            )
        ).fetchall()

        views: list[UserPassthroughConnectorView] = []
        for r in rows:
            has_token = r[6] is not None and str(r[7]).upper() == "ACTIVE"
            views.append(
                UserPassthroughConnectorView(
                    connector_id=str(r[0]),
                    connector_kind=cast(EnterpriseConnectorKind, str(r[1])),
                    connector_name=str(r[2]),
                    base_url=str(r[3]),
                    auth_mode=cast(EnterpriseConnectorAuthMode, str(r[4])),
                    connected=has_token,
                    external_author_login=str(r[5]) if r[5] else None,
                    secret_status=ConnectorSecretStatus(
                        configured=has_token,
                        fingerprint=str(r[6]) if has_token else None,
                        updated_at_iso=r[8].isoformat() if (has_token and r[8]) else None,
                    ),
                )
            )
        return views


async def upsert_user_passthrough_token_on_postgres18(
    engine: AsyncEngine,
    *,
    cipher: PassthroughVaultCipher,
    user_id: str,
    connector_id: str,
    external_author_login: str | None,
    secret_value: str,
    instance: str | None = None,
) -> UserPassthroughConnectorView:
    """Save user personal passthrough token encrypted with AES-256-GCM."""
    plain = secret_value.strip()
    if not plain:
        raise ValidationDomainError(
            detail_override="Passthrough token must not be empty.",
            instance=instance,
        )
    uid_norm = user_id.strip().lower()
    cid_uuid = UUID(connector_id)

    async with engine.begin() as conn:
        await ensure_enterprise_connectors_schema(conn)
        conn_row = (
            await conn.execute(
                sa.text(
                    """
                    SELECT id, connector_kind, name, base_url, auth_mode, enabled
                    FROM enterprise_connectors
                    WHERE id = :cid
                    """
                ),
                {"cid": cid_uuid},
            )
        ).fetchone()
        if conn_row is None:
            raise ResourceNotFoundError(instance=instance)

        kind = str(conn_row[1])
        base_url = str(conn_row[3])
        encrypted = pack_encrypted_secret(
            cipher,
            owner_id=uid_norm,
            plaintext=plain,
            scheme=kind,
            host=extract_url_host(base_url),
        )
        fingerprint = compute_secret_fingerprint(f"{uid_norm}:{connector_id}", plain)
        clean_login = (external_author_login or "").strip() or None
        tok_id = new_uuid7_str()

        row = (
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO user_connector_passthrough_tokens (
                        id, user_id, connector_id, external_author_login,
                        encrypted_token, secret_fingerprint, status, updated_at
                    )
                    VALUES (
                        :id, :uid, :cid, :login,
                        :enc, :fp, 'ACTIVE', NOW()
                    )
                    ON CONFLICT (user_id, connector_id) DO UPDATE SET
                        external_author_login = EXCLUDED.external_author_login,
                        encrypted_token = EXCLUDED.encrypted_token,
                        secret_fingerprint = EXCLUDED.secret_fingerprint,
                        status = 'ACTIVE',
                        updated_at = NOW()
                    RETURNING external_author_login, secret_fingerprint, updated_at
                    """
                ),
                {
                    "id": UUID(tok_id),
                    "uid": uid_norm,
                    "cid": cid_uuid,
                    "login": clean_login,
                    "enc": encrypted,
                    "fp": fingerprint,
                },
            )
        ).fetchone()
        assert row is not None

        return UserPassthroughConnectorView(
            connector_id=str(conn_row[0]),
            connector_kind=cast(EnterpriseConnectorKind, kind),
            connector_name=str(conn_row[2]),
            base_url=base_url,
            auth_mode=cast(EnterpriseConnectorAuthMode, str(conn_row[4])),
            connected=True,
            external_author_login=str(row[0]) if row[0] else None,
            secret_status=ConnectorSecretStatus(
                configured=True,
                fingerprint=str(row[1]),
                updated_at_iso=row[2].isoformat() if row[2] else None,
            ),
        )


async def revoke_user_passthrough_token_on_postgres18(
    engine: AsyncEngine,
    *,
    user_id: str,
    connector_id: str,
    instance: str | None = None,
) -> None:
    """Revoke/delete a user's personal passthrough token for a specific connector."""
    uid_norm = user_id.strip().lower()
    cid_uuid = UUID(connector_id)
    async with engine.begin() as conn:
        await ensure_enterprise_connectors_schema(conn)
        conn_row = (
            await conn.execute(
                sa.text("SELECT id FROM enterprise_connectors WHERE id = :cid"),
                {"cid": cid_uuid},
            )
        ).fetchone()
        if conn_row is None:
            raise ResourceNotFoundError(instance=instance)

        await conn.execute(
            sa.text(
                """
                DELETE FROM user_connector_passthrough_tokens
                WHERE LOWER(user_id) = :uid AND connector_id = :cid
                """
            ),
            {"uid": uid_norm, "cid": cid_uuid},
        )
