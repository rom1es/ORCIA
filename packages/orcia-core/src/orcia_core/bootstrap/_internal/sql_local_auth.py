"""PostgreSQL 18 persistence adapter for local authentication & password lifecycle (`AD-6`).

Handles credentials upsert, candidate lookup with IAM join, and password rotation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_kernel.ids import new_uuid7_str

_DEFAULT_HUMAN_ROLES: tuple[str, ...] = ("CONTRIBUTOR",)
_VALID_PLATFORM_ROLES = {
    "PLATFORM_ADMIN",
    "BU_DIRECTOR",
    "TEAM_LEAD",
    "CONTRIBUTOR",
    "GATE_REVIEWER",
    "ONTOLOGY_STEWARD_L3",
    "OBSERVER",
}


@dataclass(frozen=True)
class LocalAuthCandidate:
    """Authentication candidate loaded from PostgreSQL 18 `users` + `iam_accounts`."""

    user_id: str
    email: str
    display_name: str
    password_hash_argon2id: str | None
    is_active: bool
    must_change_password: bool
    platform_role: str
    roles: tuple[str, ...]
    iam_status: str | None
    primary_org_unit_id: str
    totp_secret_encrypted: str | None = None
    totp_enabled: bool = False
    human_profile_archetype: str = "CONTRIBUTOR"


def _resolve_platform_role(roles: list[str] | tuple[str, ...]) -> str:
    for r in roles:
        if r == "PLATFORM_ADMIN":
            return "PLATFORM_ADMIN"
        if r in _VALID_PLATFORM_ROLES:
            return r
        if r == "BU_LEAD":
            return "BU_DIRECTOR"
    return "CONTRIBUTOR"


async def _resolve_fallback_primary_org_unit_id(conn: AsyncConnection) -> str:
    res = await conn.execute(
        sa.text(
            """
            SELECT id FROM org_units
            ORDER BY
                CASE
                    WHEN unit_type = 'ENTERPRISE' THEN 0
                    WHEN unit_type = 'BU' THEN 1
                    ELSE 2
                END,
                created_at ASC
            LIMIT 1
            """
        )
    )
    row = res.first()
    if row is not None and row[0] is not None:
        return str(row[0])

    fallback_id = new_uuid7_str()
    await conn.execute(
        sa.text(
            """
            INSERT INTO org_units (id, slug, name, unit_type, billing_enabled, created_at)
            VALUES (:id, 'global', 'Plateforme Globale ORCIA', 'ENTERPRISE', TRUE, NOW())
            ON CONFLICT (slug) DO NOTHING
            """
        ),
        {"id": UUID(fallback_id)},
    )
    return fallback_id


async def upsert_human_user_credentials_on_postgres18(
    conn: AsyncConnection,
    *,
    email: str,
    display_name: str,
    roles: list[str] | tuple[str, ...],
    password_hash_argon2id: str,
    must_change_password: bool,
    primary_org_unit_id: str | None = None,
) -> str:
    """Upsert human credentials in `users` table on PostgreSQL 18."""
    target_org_unit_id = primary_org_unit_id
    if not target_org_unit_id:
        target_org_unit_id = await _resolve_fallback_primary_org_unit_id(conn)

    effective_platform_role = _resolve_platform_role(roles)
    password_changed_at: datetime | None = None if must_change_password else datetime.now(UTC)
    new_user_id = new_uuid7_str()

    res = await conn.execute(
        sa.text(
            """
            INSERT INTO users (
                id, email, display_name, auth_mode, password_hash_argon2id,
                human_profile_archetype, platform_role, primary_org_unit_id,
                is_active, must_change_password, password_changed_at, created_at
            ) VALUES (
                :id, :email, :display_name, 'LOCAL', :password_hash_argon2id,
                'CONTRIBUTOR', :platform_role, :primary_org_unit_id,
                TRUE, :must_change_password, :password_changed_at, NOW()
            )
            ON CONFLICT (email) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                auth_mode = 'LOCAL',
                password_hash_argon2id = EXCLUDED.password_hash_argon2id,
                platform_role = EXCLUDED.platform_role,
                is_active = TRUE,
                must_change_password = EXCLUDED.must_change_password,
                password_changed_at = EXCLUDED.password_changed_at
            RETURNING id;
            """
        ),
        {
            "id": UUID(new_user_id),
            "email": email.strip().lower(),
            "display_name": display_name.strip(),
            "password_hash_argon2id": password_hash_argon2id,
            "platform_role": effective_platform_role,
            "primary_org_unit_id": UUID(target_org_unit_id),
            "must_change_password": bool(must_change_password),
            "password_changed_at": password_changed_at,
        },
    )
    row = res.first()
    return str(row[0]) if row and row[0] else new_user_id


_USER_AUTH_SELECT_SQL = """
            SELECT
                u.id AS user_id,
                u.email,
                u.display_name,
                u.password_hash_argon2id,
                u.totp_secret_encrypted,
                u.totp_enabled,
                u.human_profile_archetype,
                u.platform_role,
                u.primary_org_unit_id,
                u.is_active,
                u.must_change_password,
                i.status AS iam_status,
                i.roles_jsonb AS iam_roles_jsonb
            FROM users u
            LEFT JOIN iam_accounts i ON LOWER(i.email) = LOWER(u.email)
"""


def _row_to_local_auth_candidate(row: sa.RowMapping) -> LocalAuthCandidate:
    roles_list: list[str] = []
    raw_roles = row["iam_roles_jsonb"]
    if isinstance(raw_roles, list):
        roles_list = [str(r) for r in raw_roles if r]
    elif isinstance(raw_roles, str):
        try:
            parsed = json.loads(raw_roles)
            if isinstance(parsed, list):
                roles_list = [str(r) for r in parsed if r]
        except json.JSONDecodeError:
            roles_list = []

    if not roles_list and row["platform_role"]:
        roles_list = [str(row["platform_role"])]

    return LocalAuthCandidate(
        user_id=str(row["user_id"]),
        email=str(row["email"]),
        display_name=str(row["display_name"]),
        password_hash_argon2id=row["password_hash_argon2id"],
        is_active=bool(row["is_active"]),
        must_change_password=bool(row["must_change_password"]),
        platform_role=str(row["platform_role"]),
        roles=tuple(roles_list) if roles_list else _DEFAULT_HUMAN_ROLES,
        iam_status=str(row["iam_status"]) if row["iam_status"] else None,
        primary_org_unit_id=str(row["primary_org_unit_id"]),
        totp_secret_encrypted=row["totp_secret_encrypted"],
        totp_enabled=bool(row["totp_enabled"]),
        human_profile_archetype=str(row["human_profile_archetype"] or "CONTRIBUTOR"),
    )


async def load_local_auth_candidate_from_postgres18(
    conn: AsyncConnection,
    *,
    email: str,
) -> LocalAuthCandidate | None:
    """Query `users` joined with `iam_accounts` by case-insensitive email."""
    res = await conn.execute(
        sa.text(f"{_USER_AUTH_SELECT_SQL} WHERE LOWER(u.email) = LOWER(:email) LIMIT 1;"),
        {"email": email.strip().lower()},
    )
    row = res.mappings().first()
    return _row_to_local_auth_candidate(row) if row is not None else None


async def load_auth_candidate_by_id_from_postgres18(
    conn: AsyncConnection,
    *,
    user_id: str,
) -> LocalAuthCandidate | None:
    """Query `users` joined with `iam_accounts` by canonical UUID `user_id`."""
    try:
        uid = UUID(user_id)
    except ValueError:
        return None
    res = await conn.execute(
        sa.text(f"{_USER_AUTH_SELECT_SQL} WHERE u.id = :user_id LIMIT 1;"),
        {"user_id": uid},
    )
    row = res.mappings().first()
    return _row_to_local_auth_candidate(row) if row is not None else None


async def load_auth_candidate_by_oidc_from_postgres18(
    conn: AsyncConnection,
    *,
    oidc_subject: str,
    email: str | None = None,
) -> LocalAuthCandidate | None:
    """Resolve an enterprise OIDC user by `oidc_subject` (or bind on pre-provisioned email)."""
    clean_sub = oidc_subject.strip()
    clean_email = email.strip().lower() if email and email.strip() else None
    res = await conn.execute(
        sa.text(
            f"""
            {_USER_AUTH_SELECT_SQL}
            WHERE u.oidc_subject = :sub
               OR (:email IS NOT NULL AND LOWER(u.email) = LOWER(:email))
            ORDER BY CASE WHEN u.oidc_subject = :sub THEN 0 ELSE 1 END
            LIMIT 1;
            """
        ),
        {"sub": clean_sub, "email": clean_email},
    )
    row = res.mappings().first()
    if row is None:
        return None
    candidate = _row_to_local_auth_candidate(row)
    if clean_sub:
        await conn.execute(
            sa.text(
                """
                UPDATE users
                SET oidc_subject = :sub
                WHERE id = :uid AND oidc_subject IS NULL;
                """
            ),
            {"sub": clean_sub, "uid": UUID(candidate.user_id)},
        )
    return candidate


async def update_user_password_on_postgres18(
    conn: AsyncConnection,
    *,
    email: str,
    new_password_hash_argon2id: str,
) -> bool:
    """Update user password, set must_change_password=FALSE, and update password_changed_at."""
    res = await conn.execute(
        sa.text(
            """
            UPDATE users
            SET
                password_hash_argon2id = :new_hash,
                must_change_password = FALSE,
                password_changed_at = NOW()
            WHERE LOWER(email) = LOWER(:email);
            """
        ),
        {
            "email": email.strip().lower(),
            "new_hash": new_password_hash_argon2id,
        },
    )
    return bool(res.rowcount and res.rowcount > 0)
