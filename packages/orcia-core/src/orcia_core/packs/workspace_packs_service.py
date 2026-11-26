"""Composition-Root Service for Workspace Pack Activation, Slots & Run Pinning (`Story 31.4`)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.packs._internal._sql_run_lock_pinning import (
    pin_workflow_v2_run_lock_sql,
    validate_and_snapshot_workspace_packs_sql,
)
from orcia_core.packs._internal._sql_run_lock_reads import (
    attach_pinned_packs_to_run_lock_sql,
    get_run_lock_manifest_sql,
    sync_workflow_v2_run_status_sql,
)
from orcia_core.packs._internal._sql_workspace_pack_mutations import (
    activate_workspace_pack_sql,
    deactivate_workspace_pack_sql,
)
from orcia_core.packs._internal._sql_workspace_pack_reorder import reorder_workspace_packs_sql
from orcia_core.packs._internal._sql_workspace_pack_views import list_workspace_packs_sql
from orcia_core.packs._internal._sql_workspace_slot_bindings import (
    bind_workspace_pack_slots_sql,
)
from orcia_core.packs.slot_guard import (
    EffectiveSlotBindingView,
    PinnedPackManifestEntry,
    SlotBindingInput,
    WorkspacePackView,
)


class WorkspacePacksService:
    """Orchestrates workspace pack activation, slot binding, reorder, and run-lock pinning."""

    def __init__(self, *, engine: AsyncEngine | None = None) -> None:
        self._engine = engine

    def set_engine(self, engine: AsyncEngine | None) -> None:
        self._engine = engine

    def has_engine(self) -> bool:
        return self._engine is not None

    def _require_engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("WorkspacePacksService requires a configured PG18 AsyncEngine.")
        return self._engine

    async def list_workspace_packs(
        self,
        workspace_id: str,
        *,
        instance: str | None = None,
    ) -> list[WorkspacePackView]:
        """List visible packs for `workspace_id` with activation & slot readiness state."""
        if self._engine is None:
            return []
        return await list_workspace_packs_sql(self._engine, workspace_id, instance=instance)

    async def bind_pack_slots(
        self,
        *,
        workspace_id: str,
        pack_slug: str,
        bindings: Sequence[SlotBindingInput],
        bundle_id: str | None = None,
        actor_id: str,
        actor_email: str | None = None,
        trace_id: str | None = None,
        instance: str | None = None,
    ) -> list[EffectiveSlotBindingView]:
        """Persist explicit slot bindings and emit `audit_ledger` `PACK_SLOTS_BOUND`."""
        return await bind_workspace_pack_slots_sql(
            self._require_engine(),
            workspace_id=workspace_id,
            pack_slug=pack_slug,
            bindings=bindings,
            bundle_id=bundle_id,
            actor_id=actor_id,
            actor_email=actor_email,
            trace_id=trace_id,
            instance=instance,
        )

    async def activate_pack(
        self,
        *,
        workspace_id: str,
        pack_slug: str,
        bundle_id: str | None = None,
        version: str | None = None,
        priority_order: int | None = None,
        slot_bindings: Sequence[SlotBindingInput] = (),
        actor_id: str,
        actor_email: str | None = None,
        trace_id: str | None = None,
        instance: str | None = None,
    ) -> dict[str, Any]:
        """Activate a pack in `workspace_id` after verifying all required slots are bound."""
        return await activate_workspace_pack_sql(
            self._require_engine(),
            workspace_id=workspace_id,
            pack_slug=pack_slug,
            bundle_id=bundle_id,
            version=version,
            priority_order=priority_order,
            slot_bindings=slot_bindings,
            actor_id=actor_id,
            actor_email=actor_email,
            trace_id=trace_id,
            instance=instance,
        )

    async def deactivate_pack(
        self,
        *,
        workspace_id: str,
        pack_slug: str,
        actor_id: str,
        actor_email: str | None = None,
        trace_id: str | None = None,
        instance: str | None = None,
    ) -> dict[str, Any]:
        """Deactivate a workspace pack (`is_active=FALSE, priority_order=NULL`)."""
        return await deactivate_workspace_pack_sql(
            self._require_engine(),
            workspace_id=workspace_id,
            pack_slug=pack_slug,
            actor_id=actor_id,
            actor_email=actor_email,
            trace_id=trace_id,
            instance=instance,
        )

    async def reorder_packs(
        self,
        *,
        workspace_id: str,
        ordered_pack_slugs: Sequence[str],
        actor_id: str,
        actor_email: str | None = None,
        trace_id: str | None = None,
        instance: str | None = None,
    ) -> list[dict[str, Any]]:
        """Atomically reorder active workspace packs via `DEFERRABLE` priority constraint."""
        return await reorder_workspace_packs_sql(
            self._require_engine(),
            workspace_id=workspace_id,
            ordered_pack_slugs=ordered_pack_slugs,
            actor_id=actor_id,
            actor_email=actor_email,
            trace_id=trace_id,
            instance=instance,
        )

    async def enforce_run_start_readiness(
        self,
        *,
        workspace_id: str | None,
        workflow_pack_id: str | None = None,
        instance: str | None = None,
    ) -> list[PinnedPackManifestEntry]:
        """Fail closed (`422 ERR_PACK_SLOT_UNBOUND`) or return pinned packs for `run_lock`."""
        if self._engine is None:
            return []
        if not workspace_id and not workflow_pack_id:
            return []
        return await validate_and_snapshot_workspace_packs_sql(
            self._engine,
            workspace_id=workspace_id,
            workflow_pack_id=workflow_pack_id,
            instance=instance,
        )

    async def pin_run_lock(
        self,
        *,
        run_id: str,
        workspace_id: str | None,
        workflow_id: str,
        workflow_slug: str,
        workflow_version: str,
        workflow_sha256: str,
        status: str,
        actor_user_id: str | None,
        pinned_packs: list[PinnedPackManifestEntry],
        v2_run_payload: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], str] | None:
        """Persist `workflow_runs` + immutable `run_lock_manifests` snapshot in PG18."""
        if self._engine is None or not workspace_id:
            return None
        return await pin_workflow_v2_run_lock_sql(
            self._engine,
            run_id=run_id,
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            workflow_slug=workflow_slug,
            workflow_version=workflow_version,
            workflow_sha256=workflow_sha256,
            status=status,
            actor_user_id=actor_user_id,
            pinned_packs=pinned_packs,
            v2_run_payload=v2_run_payload,
        )

    async def sync_run_status(self, *, run_id: str, status: str) -> None:
        """Sync terminal/HITL status onto `workflow_runs` without altering `run_lock_manifests`."""
        if self._engine is None:
            return
        await sync_workflow_v2_run_status_sql(self._engine, run_id=run_id, status=status)

    async def attach_pinned_packs_to_run_lock(
        self,
        *,
        run_id: str,
        pinned_packs: list[PinnedPackManifestEntry],
    ) -> None:
        """Merge pinned workspace packs into an existing `run_lock_manifests` row."""
        if self._engine is None or not pinned_packs:
            return
        await attach_pinned_packs_to_run_lock_sql(
            self._engine, run_id=run_id, pinned_packs=pinned_packs
        )

    async def get_run_lock(self, *, run_id: str) -> dict[str, Any] | None:
        """Read immutable `run_lock_manifests` snapshot by `run_id`."""
        if self._engine is None:
            return None
        return await get_run_lock_manifest_sql(self._engine, run_id=run_id)


__all__ = ["WorkspacePacksService"]
