"""Typed PostgreSQL 18 seed helpers (`seed_org_workspace_admin`, `activate_pack_with_slots`)."""

from __future__ import annotations

from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from uuid_utils import uuid7


@dataclass(frozen=True, slots=True)
class SeededWorkspaceAdmin:
    """Typed PG18 seed result returned by `seed_org_workspace_admin()`."""

    org_unit_id: str
    workspace_id: str
    workspace_slug: str
    admin_user_id: str
    admin_email: str


@dataclass(frozen=True, slots=True)
class ActivatedPackSlotsResult:
    """Typed PG18 result returned by `activate_pack_with_slots()`."""

    activation_id: str
    pack_bundle_id: str
    pack_slug: str
    slot_binding_ids: tuple[str, ...]


async def seed_org_workspace_admin(
    async_database_url: str,
    *,
    org_slug: str = "ent-shared",
    workspace_slug: str = "ws-shared",
    admin_email: str = "admin@orcia.test",
) -> SeededWorkspaceAdmin:
    """Idempotently seed an org root, workspace, and PLATFORM_ADMIN user on PG18."""
    org_id, ws_id, admin_id = str(uuid7()), str(uuid7()), str(uuid7())
    engine = create_async_engine(async_database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "INSERT INTO org_units (id, slug, name, unit_type) "
                    "VALUES (CAST(:id AS uuid), :slug, :name, 'ENTERPRISE') "
                    "ON CONFLICT (slug) DO NOTHING"
                ),
                {"id": org_id, "slug": org_slug, "name": f"Org {org_slug}"},
            )
            org_id = str(
                (
                    await conn.execute(
                        sa.text("SELECT id::text FROM org_units WHERE slug = :slug"),
                        {"slug": org_slug},
                    )
                ).scalar_one()
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO users (id, email, display_name, auth_mode, "
                    "human_profile_archetype, platform_role, primary_org_unit_id) "
                    "VALUES (CAST(:uid AS uuid), :email, 'Shared Admin', 'LOCAL', "
                    "'ARCHITECT', 'PLATFORM_ADMIN', CAST(:org AS uuid)) "
                    "ON CONFLICT (email) DO NOTHING"
                ),
                {"uid": admin_id, "email": admin_email, "org": org_id},
            )
            admin_id = str(
                (
                    await conn.execute(
                        sa.text("SELECT id::text FROM users WHERE email = :email"),
                        {"email": admin_email},
                    )
                ).scalar_one()
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO workspaces (id, slug, name, owner_org_unit_id) "
                    "VALUES (CAST(:ws AS uuid), :slug, :name, CAST(:org AS uuid)) "
                    "ON CONFLICT (slug) DO NOTHING"
                ),
                {
                    "ws": ws_id,
                    "slug": workspace_slug,
                    "name": f"WS {workspace_slug}",
                    "org": org_id,
                },
            )
            ws_id = str(
                (
                    await conn.execute(
                        sa.text("SELECT id::text FROM workspaces WHERE slug = :slug"),
                        {"slug": workspace_slug},
                    )
                ).scalar_one()
            )
    finally:
        await engine.dispose()
    return SeededWorkspaceAdmin(
        org_unit_id=org_id,
        workspace_id=ws_id,
        workspace_slug=workspace_slug,
        admin_user_id=admin_id,
        admin_email=admin_email,
    )


async def activate_pack_with_slots(
    async_database_url: str,
    *,
    workspace_id: str,
    pack_slug: str = "sdlc",
    pack_bundle_id: str | None = None,
    slot_keys: tuple[str, ...] = ("git_repo",),
    priority_order: int = 1,
    activated_by: str = "system",
) -> ActivatedPackSlotsResult:
    """Idempotently ensure a published pack bundle, activate it on workspace, and bind slots."""
    bundle_id = pack_bundle_id or str(uuid7())
    act_id = str(uuid7())
    binding_ids: list[str] = []
    engine = create_async_engine(async_database_url)
    try:
        async with engine.begin() as conn:
            existing_bundle = (
                await conn.execute(
                    sa.text(
                        "SELECT id::text FROM declarative_pack_bundles WHERE slug = :slug LIMIT 1"
                    ),
                    {"slug": pack_slug},
                )
            ).scalar_one_or_none()
            if existing_bundle is not None:
                bundle_id = str(existing_bundle)
            else:
                await conn.execute(
                    sa.text(
                        "INSERT INTO declarative_pack_bundles (id, pack_id, slug, name, version, "
                        "rbac_namespace, bundle_sha256, archive_sha256, bundle_kind, scope_type, "
                        "scope_id, status, source_origin) VALUES (CAST(:id AS uuid), :pid, :slug, "
                        ":name, '1.0.0', :slug, :sha, :sha, 'CUSTOM', 'GLOBAL', 'global', "
                        "'PUBLISHED', 'LOCAL_SYSTEM')"
                    ),
                    {
                        "id": bundle_id,
                        "pid": f"orcia-pack-{pack_slug}",
                        "slug": pack_slug,
                        "name": f"Pack {pack_slug}",
                        "sha": "0" * 64,
                    },
                )
            await conn.execute(
                sa.text(
                    "INSERT INTO workspace_pack_activations (id, workspace_id, pack_bundle_id, "
                    "pack_slug, priority_order, is_active, activated_by) "
                    "VALUES (CAST(:id AS uuid), CAST(:ws AS uuid), CAST(:bid AS uuid), "
                    ":slug, :prio, TRUE, :by) "
                    "ON CONFLICT (workspace_id, pack_slug) DO UPDATE SET is_active = TRUE"
                ),
                {
                    "id": act_id,
                    "ws": workspace_id,
                    "bid": bundle_id,
                    "slug": pack_slug,
                    "prio": priority_order,
                    "by": activated_by,
                },
            )
            for slot_key in slot_keys:
                bid = str(uuid7())
                await conn.execute(
                    sa.text(
                        "INSERT INTO workspace_pack_slot_bindings (id, workspace_id, "
                        "pack_bundle_id, pack_slug, slot_key, target_kind, bound_by) "
                        "VALUES (CAST(:id AS uuid), CAST(:ws AS uuid), CAST(:bid AS uuid), "
                        ":slug, :slot, 'INTERNAL', :by) "
                        "ON CONFLICT (workspace_id, pack_slug, slot_key) DO NOTHING"
                    ),
                    {
                        "id": bid,
                        "ws": workspace_id,
                        "bid": bundle_id,
                        "slug": pack_slug,
                        "slot": slot_key,
                        "by": activated_by,
                    },
                )
                binding_ids.append(bid)
    finally:
        await engine.dispose()
    return ActivatedPackSlotsResult(
        activation_id=act_id,
        pack_bundle_id=bundle_id,
        pack_slug=pack_slug,
        slot_binding_ids=tuple(binding_ids),
    )
