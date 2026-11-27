"""Pack Composer & Scrubbed Export Facade (`Story 31.5`, `<= 195 L`)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.packs._internal._pack_closure_analyzer import (
    analyze_and_optionally_expand_closure_conn,
)
from orcia_core.packs._internal._sql_pack_composer import (
    create_draft_pack_sql,
    update_draft_pack_sql,
)
from orcia_core.packs._internal._sql_pack_composer_members import (
    delete_draft_pack_sql,
    set_draft_pack_members_sql,
)
from orcia_core.packs._internal._sql_pack_composer_reads import (
    get_draft_pack_sql,
    list_draft_packs_sql,
)
from orcia_core.packs._internal._sql_pack_publish_export import (
    export_bundle_tx,
    publish_draft_pack_tx,
)
from orcia_core.packs.composer_models import (
    PackClosureReport,
    PackDraftDetail,
    PackDraftMemberInput,
    PackExportResult,
)
from orcia_core.packs.models import PackQuickActionSpec, PackScopeType, PackSlotSpec
from orcia_core.packs.ports import PackCasStoragePort


class PackComposerService:
    """Composition-Root service for `CUSTOM` draft composition, closure & scrubbed export."""

    def __init__(
        self,
        *,
        engine: AsyncEngine | None = None,
        cas_storage: PackCasStoragePort | None = None,
    ) -> None:
        self._engine = engine
        self._cas_storage = cas_storage

    def set_engine(self, engine: AsyncEngine) -> None:
        self._engine = engine

    def set_cas_storage(self, cas_storage: PackCasStoragePort | None) -> None:
        self._cas_storage = cas_storage

    def _require_engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError(
                "PackComposerService requires a configured PostgreSQL 18 AsyncEngine."
            )
        return self._engine

    async def create_draft(
        self,
        *,
        slug: str,
        name: str,
        version: str = "0.1.0",
        description: str = "",
        author: str = "",
        maintainers: Sequence[str] = (),
        license_name: str = "",
        scope_type: PackScopeType = PackScopeType.WORKSPACE,
        scope_id: str,
        declared_slots: Sequence[PackSlotSpec] = (),
        quick_actions: Sequence[PackQuickActionSpec] = (),
        actor_id: str = "system",
        actor_email: str | None = None,
        trace_id: str | None = None,
        instance: str | None = None,
    ) -> PackDraftDetail:
        return await create_draft_pack_sql(
            self._require_engine(),
            slug=slug,
            name=name,
            version=version,
            description=description,
            author=author,
            maintainers=maintainers,
            license_name=license_name,
            scope_type=scope_type,
            scope_id=scope_id,
            declared_slots=declared_slots,
            quick_actions=quick_actions,
            actor_id=actor_id,
            actor_email=actor_email,
            trace_id=trace_id,
            instance=instance,
        )

    async def list_drafts(
        self,
        *,
        scope_type: PackScopeType | None = None,
        scope_id: str | None = None,
        status_filter: str | None = "DRAFT",
        unrestricted: bool = True,
        allowed_workspace_ids: frozenset[str] = frozenset(),
        allowed_org_ids: frozenset[str] = frozenset(),
        allow_global: bool = False,
    ) -> list[PackDraftDetail]:
        return await list_draft_packs_sql(
            self._require_engine(),
            scope_type=scope_type,
            scope_id=scope_id,
            status_filter=status_filter,
            unrestricted=unrestricted,
            allowed_workspace_ids=allowed_workspace_ids,
            allowed_org_ids=allowed_org_ids,
            allow_global=allow_global,
        )

    async def get_draft(
        self,
        draft_id: str,
        *,
        include_closure: bool = True,
        instance: str | None = None,
    ) -> PackDraftDetail:
        eng = self._require_engine()
        detail = await get_draft_pack_sql(eng, draft_id, instance=instance)
        if not include_closure:
            return detail
        async with eng.connect() as conn:
            closure: PackClosureReport = await analyze_and_optionally_expand_closure_conn(
                conn,
                bundle_id=detail.bundle_id,
                scope_type=detail.scope_type,
                scope_id=detail.scope_id,
                members=detail.members,
                auto_include_dependencies=False,
                can_mutate_draft=False,
                require_active=False,
                fail_on_incomplete=False,
                instance=instance,
            )
        return detail.model_copy(update={"closure": closure})

    async def update_draft(
        self,
        draft_id: str,
        *,
        name: str | None = None,
        version: str | None = None,
        description: str | None = None,
        author: str | None = None,
        maintainers: Sequence[str] | None = None,
        license_name: str | None = None,
        declared_slots: Sequence[PackSlotSpec] | None = None,
        quick_actions: Sequence[PackQuickActionSpec] | None = None,
        instance: str | None = None,
    ) -> PackDraftDetail:
        return await update_draft_pack_sql(
            self._require_engine(),
            draft_id,
            name=name,
            version=version,
            description=description,
            author=author,
            maintainers=maintainers,
            license_name=license_name,
            declared_slots=declared_slots,
            quick_actions=quick_actions,
            instance=instance,
        )

    async def set_members(
        self,
        draft_id: str,
        members: Sequence[PackDraftMemberInput],
        *,
        actor_id: str = "system",
        actor_email: str | None = None,
        trace_id: str | None = None,
        instance: str | None = None,
    ) -> PackDraftDetail:
        return await set_draft_pack_members_sql(
            self._require_engine(),
            draft_id,
            members,
            actor_id=actor_id,
            actor_email=actor_email,
            trace_id=trace_id,
            instance=instance,
        )

    async def delete_draft(
        self,
        draft_id: str,
        *,
        actor_id: str = "system",
        actor_email: str | None = None,
        trace_id: str | None = None,
        instance: str | None = None,
    ) -> dict[str, str]:
        return await delete_draft_pack_sql(
            self._require_engine(),
            draft_id,
            actor_id=actor_id,
            actor_email=actor_email,
            trace_id=trace_id,
            instance=instance,
        )

    async def publish_draft(
        self,
        draft_id: str,
        *,
        auto_include_dependencies: bool = False,
        actor_id: str = "system",
        actor_email: str | None = None,
        trace_id: str | None = None,
        instance: str | None = None,
    ) -> PackDraftDetail:
        return await publish_draft_pack_tx(
            self._require_engine(),
            draft_id=draft_id,
            auto_include_dependencies=auto_include_dependencies,
            cas_storage=self._cas_storage,
            actor_id=actor_id,
            actor_email=actor_email,
            trace_id=trace_id,
            instance=instance,
        )

    async def export_bundle(
        self,
        bundle_id: str,
        *,
        auto_include_dependencies: bool = False,
        require_active: bool = False,
        instance: str | None = None,
    ) -> PackExportResult:
        return await export_bundle_tx(
            self._require_engine(),
            bundle_id=bundle_id,
            auto_include_dependencies=auto_include_dependencies,
            require_active=require_active,
            instance=instance,
        )


__all__ = ["PackComposerService"]
