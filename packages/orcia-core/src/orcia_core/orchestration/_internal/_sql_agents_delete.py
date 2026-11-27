"""Guarded PG18 delete helpers for `catalog_items` assets (`Story 31.5`)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.kernel.errors import ResourceNotFoundError, ScopeAccessDeniedError
from orcia_core.orchestration.agents_and_skills_models import ManagedAgentRecord
from orcia_core.storage.pack_draft_guard import (
    DraftAuthCallback,
    guard_or_unlink_pack_drafts_conn,
)

CatalogAuthCallback = Callable[[str, str], None]

_ITEM_ENTITY_TYPE: dict[str, str] = {
    "USER_AGENT": "AGENT",
    "USER_SKILL": "SKILL",
    "INSTRUCTION": "INSTRUCTION",
    "HELP_ARTICLE": "HELP_ARTICLE",
}


def _extract_catalog_row(row: Any) -> tuple[str, str, str | None, str]:
    if isinstance(row, Mapping):
        return (
            str(row["uid"]),
            str(row.get("ws_id") or ""),
            str(row["bid"]) if row.get("bid") is not None else None,
            str(row.get("visibility_scope") or "").upper(),
        )
    uid, ws_id, bid, vis = row[0], row[1], row[2], row[3]
    return (
        str(uid),
        str(ws_id or ""),
        str(bid) if bid is not None else None,
        str(vis or "").upper(),
    )


async def delete_catalog_item_guarded(
    engine: AsyncEngine,
    resource_id: str,
    item_type: str,
    *,
    unlink_from_draft_packs: bool = False,
    authorize_target_cb: CatalogAuthCallback | None = None,
    authorize_draft_cb: DraftAuthCallback | None = None,
    raise_if_missing: bool = False,
    actor_id: str = "system",
    actor_email: str | None = None,
    trace_id: str | None = None,
    instance: str | None = None,
) -> tuple[str, list[dict[str, str]]]:
    """Delete standalone `catalog_items` row with pack-immutability, RBAC & anti-hostage guard."""
    entity_type = _ITEM_ENTITY_TYPE.get(item_type, "AGENT")
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                sa.text(
                    "SELECT id::text AS uid, COALESCE(owner_workspace_id::text, '') AS ws_id, "
                    "pack_bundle_id::text AS bid, visibility_scope "
                    "FROM catalog_items "
                    "WHERE (resource_id = :rid OR id::text = :rid) "
                    "AND item_type = :item_type "
                    "ORDER BY (pack_bundle_id IS NULL) DESC LIMIT 1 FOR UPDATE"
                ),
                {"rid": resource_id, "item_type": item_type},
            )
        ).first()
        if row is None:
            if raise_if_missing:
                raise ResourceNotFoundError(
                    detail_override=f"{entity_type} {resource_id!r} not found.",
                    instance=instance,
                )
            await conn.execute(
                sa.text(
                    "DELETE FROM catalog_items "
                    "WHERE resource_id = :resource_id AND item_type = :item_type"
                ),
                {"resource_id": resource_id, "item_type": item_type},
            )
            return "", []
        target_uuid, ws_id, bid, vis = _extract_catalog_row(row)
        if bid is not None or vis == "PACK":
            raise ScopeAccessDeniedError(
                detail_override="Pack-owned catalog assets cannot be deleted individually.",
                instance=instance,
            )
        if authorize_target_cb is not None:
            authorize_target_cb(ws_id, vis)
        unlinked = await guard_or_unlink_pack_drafts_conn(
            conn,
            fk_column="catalog_item_id",
            target_uuid=target_uuid,
            entity_type=entity_type,
            entity_label=resource_id,
            unlink_from_draft_packs=unlink_from_draft_packs,
            authorize_draft_cb=authorize_draft_cb,
            actor_id=actor_id,
            actor_email=actor_email,
            trace_id=trace_id,
            scope_path=f"WORKSPACE:{ws_id}" if ws_id else "GLOBAL",
            instance=instance,
        )
        await conn.execute(
            sa.text("DELETE FROM catalog_items WHERE id = CAST(:uid AS uuid)"),
            {"uid": target_uuid},
        )
        return target_uuid, unlinked


async def delete_skill_with_agent_sync(
    engine: AsyncEngine,
    skill_id: str,
    updated_agents: tuple[ManagedAgentRecord, ...],
    *,
    unlink_from_draft_packs: bool = False,
    authorize_target_cb: CatalogAuthCallback | None = None,
    authorize_draft_cb: DraftAuthCallback | None = None,
    actor_id: str = "system",
    actor_email: str | None = None,
    trace_id: str | None = None,
    instance: str | None = None,
) -> tuple[bool, list[dict[str, str]]]:
    """Atomically guard, unlink, delete a Skill & detach from non-PACK PG18 Agents in 1 tx."""
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                sa.text(
                    "SELECT id::text AS uid, COALESCE(owner_workspace_id::text, '') AS ws_id, "
                    "pack_bundle_id::text AS bid, visibility_scope "
                    "FROM catalog_items "
                    "WHERE (resource_id = :rid OR id::text = :rid) "
                    "AND item_type = 'USER_SKILL' "
                    "ORDER BY (pack_bundle_id IS NULL) DESC LIMIT 1 FOR UPDATE"
                ),
                {"rid": skill_id},
            )
        ).first()
        if row is None:
            await conn.execute(
                sa.text(
                    "DELETE FROM catalog_items "
                    "WHERE resource_id = :resource_id AND item_type = 'USER_SKILL'"
                ),
                {"resource_id": skill_id},
            )
            return False, []
        target_uuid, ws_id, bid, vis = _extract_catalog_row(row)
        if bid is not None or vis == "PACK":
            raise ScopeAccessDeniedError(
                detail_override="Pack-owned skills cannot be deleted individually.",
                instance=instance,
            )
        if authorize_target_cb is not None:
            authorize_target_cb(ws_id, vis)
        unlinked = await guard_or_unlink_pack_drafts_conn(
            conn,
            fk_column="catalog_item_id",
            target_uuid=target_uuid,
            entity_type="SKILL",
            entity_label=skill_id,
            unlink_from_draft_packs=unlink_from_draft_packs,
            authorize_draft_cb=authorize_draft_cb,
            actor_id=actor_id,
            actor_email=actor_email,
            trace_id=trace_id,
            scope_path=f"WORKSPACE:{ws_id}" if ws_id else "GLOBAL",
            instance=instance,
        )
        await conn.execute(
            sa.text("DELETE FROM catalog_items WHERE id = CAST(:uid AS uuid)"),
            {"uid": target_uuid},
        )
        detach_ids = [
            a.agent_id for a in updated_agents if str(a.visibility_scope).upper() != "PACK"
        ]
        if detach_ids:
            await conn.execute(
                sa.text(
                    "UPDATE catalog_items SET metadata_jsonb = jsonb_set("
                    "COALESCE(metadata_jsonb, '{}'::jsonb), '{skill_ids}', "
                    "COALESCE((SELECT jsonb_agg(elem) FROM jsonb_array_elements_text("
                    "COALESCE(metadata_jsonb->'skill_ids', '[]'::jsonb)) elem "
                    "WHERE elem <> :sid), '[]'::jsonb)) "
                    "WHERE item_type = 'USER_AGENT' AND pack_bundle_id IS NULL "
                    "AND visibility_scope <> 'PACK' AND resource_id = ANY(:aids)"
                ),
                {"sid": skill_id, "aids": detach_ids},
            )
        return True, unlinked


async def delete_agent_from_postgres18(
    engine: AsyncEngine,
    agent_id: str,
    *,
    unlink_from_draft_packs: bool = False,
    authorize_target_cb: CatalogAuthCallback | None = None,
    authorize_draft_cb: DraftAuthCallback | None = None,
    actor_id: str = "system",
    actor_email: str | None = None,
    trace_id: str | None = None,
    instance: str | None = None,
) -> list[dict[str, str]]:
    """Delete a standalone Agent from PG18 `catalog_items` with draft & scope guard."""
    _, unlinked = await delete_catalog_item_guarded(
        engine,
        agent_id,
        "USER_AGENT",
        unlink_from_draft_packs=unlink_from_draft_packs,
        authorize_target_cb=authorize_target_cb,
        authorize_draft_cb=authorize_draft_cb,
        actor_id=actor_id,
        actor_email=actor_email,
        trace_id=trace_id,
        instance=instance,
    )
    return unlinked


__all__ = [
    "CatalogAuthCallback",
    "delete_agent_from_postgres18",
    "delete_catalog_item_guarded",
    "delete_skill_with_agent_sync",
]
