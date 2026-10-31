"""PostgreSQL 18 Exclusive Table Lock Guard (`LOCK TABLE users IN EXCLUSIVE MODE`, `Story 9.2`)."""

from __future__ import annotations

import hmac
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.bootstrap.errors import (
    FirstUserAlreadyInitializedError,
    InvalidBootstrapTokenError,
)
from orcia_core.bootstrap.progressive_accostage import (
    EXCLUSIVE_USERS_LOCK_SQL,
    FirstPlatformAdminRecord,
)
from orcia_kernel.ids import new_uuid7_str


async def create_first_platform_admin_on_postgres18(
    engine: AsyncEngine,
    *,
    email: str,
    display_name: str,
    password_hash: str,
    orcia_env: str = "local",
    expected_bootstrap_token: str | None = None,
    provided_bootstrap_token: str | None = None,
    instance: str | None = None,
) -> FirstPlatformAdminRecord:
    """Create the initial `PLATFORM_ADMIN` atomically under `LOCK TABLE users IN EXCLUSIVE MODE`."""
    effective_env = orcia_env.strip().lower() or "local"
    if effective_env != "local":
        expected = (expected_bootstrap_token or "").strip()
        candidate = (provided_bootstrap_token or "").strip()
        if not expected or not candidate or not hmac.compare_digest(expected, candidate):
            raise InvalidBootstrapTokenError(instance=instance)

    async with engine.begin() as conn:
        await conn.execute(sa.text(EXCLUSIVE_USERS_LOCK_SQL))
        count_row = await conn.execute(sa.text("SELECT COUNT(*) FROM users"))
        existing_count = int(count_row.scalar_one())
        if existing_count > 0:
            raise FirstUserAlreadyInitializedError(instance=instance)

        org_id_row = await conn.execute(
            sa.text(
                """
                INSERT INTO org_units (id, slug, name, unit_type, parent_id)
                VALUES (:id, 'orcia-root', 'ORCIA Root Organization', 'ENTERPRISE', NULL)
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """
            ),
            {"id": UUID(new_uuid7_str())},
        )
        root_org_id = org_id_row.scalar_one()

        user_id_str = new_uuid7_str()
        await conn.execute(
            sa.text(
                """
                INSERT INTO users (
                    id, email, display_name, auth_mode, password_hash_argon2id,
                    human_profile_archetype, platform_role, primary_org_unit_id, is_active
                )
                VALUES (
                    :id, :email, :display_name, 'LOCAL', :password_hash,
                    'TECH_LEAD', 'PLATFORM_ADMIN', :org_id, TRUE
                )
                """
            ),
            {
                "id": UUID(user_id_str),
                "email": email.strip().lower(),
                "display_name": display_name.strip(),
                "password_hash": password_hash,
                "org_id": root_org_id,
            },
        )

    return FirstPlatformAdminRecord(
        user_id=user_id_str,
        email=email.strip().lower(),
        display_name=display_name.strip(),
        platform_role="PLATFORM_ADMIN",
        orcia_env=effective_env,
        sql_lock_statement=EXCLUSIVE_USERS_LOCK_SQL,
    )
