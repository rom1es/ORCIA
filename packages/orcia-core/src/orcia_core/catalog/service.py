"""FederatedCatalogService orchestrating Catalog RBAC, Promotion, CAS, 4-Layer Merge & BMAD.

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from dataclasses import replace

from orcia_core.catalog.bmad_adapter import BmadSkillPackAdapter
from orcia_core.catalog.cas_resolver import FederatedUriResolver
from orcia_core.catalog.models import (
    CATALOG_PROMOTION_ORDER,
    BmadSkillPackInput,
    CatalogItemEntity,
    CustomizationOverrideEntity,
    FederatedScheme,
    WorkflowDefinitionEntity,
)
from orcia_core.catalog.override_merger import (
    EffectiveWorkflowMergeResult,
    FourLayerOverrideMerger,
)
from orcia_core.domain.exceptions import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)
from orcia_core.domain.identifiers import new_uuid7_str
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import (
    CatalogAclEntry,
    CatalogVisibilityScope,
    EffectiveResourcePermissions,
    UserIdentity,
)


class FederatedCatalogService:
    """Domain service for Bounded Context 3: Federated Catalog (`FR-20`, `FR-21`, `AD-5`)."""

    def __init__(
        self,
        *,
        evaluator: MatrixPermissionEvaluator,
        resolver: FederatedUriResolver | None = None,
        catalog_items: tuple[CatalogItemEntity, ...] = (),
        workflows: tuple[WorkflowDefinitionEntity, ...] = (),
        overrides: tuple[CustomizationOverrideEntity, ...] = (),
        extra_acls: tuple[CatalogAclEntry, ...] = (),
    ) -> None:
        self.evaluator = evaluator
        self.resolver = resolver or FederatedUriResolver()
        self._items_by_id = {item.resource_id: item for item in catalog_items}
        self._workflows_by_uri = {wf.uri: wf for wf in workflows}
        self._overrides = list(overrides)

        for acl in extra_acls:
            self.evaluator.upsert_catalog_acl(acl)
        for item in catalog_items:
            if item.content_payload:
                self.resolver.register_upstream_payload(
                    item.uri, item.content_payload, resolved_version=item.version, prewarm_cas=False
                )

    @property
    def catalog_items(self) -> tuple[CatalogItemEntity, ...]:
        return tuple(self._items_by_id.values())

    @property
    def workflows(self) -> tuple[WorkflowDefinitionEntity, ...]:
        return tuple(self._workflows_by_uri.values())

    @property
    def overrides(self) -> tuple[CustomizationOverrideEntity, ...]:
        return tuple(self._overrides)

    def get_catalog_item(
        self, resource_id: str, *, instance: str | None = None
    ) -> CatalogItemEntity:
        if (item := self._items_by_id.get(resource_id)) is None:
            raise ResourceNotFoundError(instance=instance)
        return item

    def upsert_catalog_item(
        self, item: CatalogItemEntity, acl: CatalogAclEntry
    ) -> CatalogItemEntity:
        self._items_by_id[item.resource_id] = item
        self.evaluator.upsert_catalog_acl(acl)
        if item.content_payload:
            self.resolver.register_upstream_payload(
                item.uri, item.content_payload, resolved_version=item.version, prewarm_cas=False
            )
        return item

    def list_catalog_items(
        self,
        user: UserIdentity,
        *,
        workspace_id: str | None = None,
        scheme: FederatedScheme | None = None,
        visibility_scope: CatalogVisibilityScope | None = None,
    ) -> list[tuple[CatalogItemEntity, EffectiveResourcePermissions]]:
        """Return catalog items discoverable by `user` with their 5 dissociated permissions."""
        results: list[tuple[CatalogItemEntity, EffectiveResourcePermissions]] = []
        for item in self._items_by_id.values():
            if (scheme and item.scheme != scheme) or (
                visibility_scope and item.visibility_scope != visibility_scope
            ):
                continue
            target_ws = workspace_id or item.owner_workspace_id
            try:
                effective, _ = self.evaluator.evaluate_catalog_resource(
                    user, item.resource_id, workspace_id=target_ws, require_read_source=False
                )
                results.append((item, effective))
            except (ScopeAccessDeniedError, ResourceNotFoundError):
                continue
        return results

    def _enforce_workspace_or_role_mutation(
        self, user: UserIdentity, workspace_id: str | None, *, instance: str | None = None
    ) -> None:
        if user.platform_role == "OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        if workspace_id is not None:
            self.evaluator.enforce_scope_mutation_guard(user, workspace_id, instance=instance)
        elif user.platform_role == "BU_DIRECTOR":
            raise ObserverModeReadOnlyError(instance=instance)

    def promote_catalog_item(
        self,
        user: UserIdentity,
        resource_id: str,
        target_scope: CatalogVisibilityScope,
        *,
        workspace_id: str | None = None,
        instance: str | None = None,
    ) -> tuple[CatalogItemEntity, EffectiveResourcePermissions]:
        """Promote a catalog item along `DRAFT -> ... -> PUBLISHED_ORG` (`FR-21`)."""
        if user.platform_role == "OBSERVER" or (
            user.platform_role == "BU_DIRECTOR" and target_scope != "PUBLISHED_ORG"
        ):
            raise ObserverModeReadOnlyError(instance=instance)

        item = self.get_catalog_item(resource_id, instance=instance)
        effective_ws_id = workspace_id or item.owner_workspace_id
        is_gov_admin = user.platform_role in ("PLATFORM_ADMIN", "BU_DIRECTOR")

        if effective_ws_id is not None:
            ws_access = self.evaluator.resolve_workspace_access(user, effective_ws_id)
            if (
                ws_access is not None
                and ws_access.access_mode == "READ_ONLY_OBSERVER"
                and not (target_scope == "PUBLISHED_ORG" and is_gov_admin)
            ):
                raise ObserverModeReadOnlyError(instance=instance)

        effective, secret = self.evaluator.evaluate_catalog_resource(
            user,
            resource_id,
            workspace_id=effective_ws_id,
            require_read_source=False,
            instance=instance,
        )
        if not (effective.can_edit or effective.can_admin) and not is_gov_admin:
            raise ScopeAccessDeniedError(instance=instance)
        if target_scope == "PUBLISHED_ORG" and not is_gov_admin:
            raise ScopeAccessDeniedError(instance=instance)
        if CATALOG_PROMOTION_ORDER.index(target_scope) <= CATALOG_PROMOTION_ORDER.index(
            item.visibility_scope
        ):
            raise ValidationDomainError(
                detail_override=f"Invalid promotion from {item.visibility_scope} to {target_scope}",
                instance=instance,
            )

        updated_item = replace(item, visibility_scope=target_scope)
        self._items_by_id[resource_id] = updated_item
        existing_acl = self.evaluator.get_primary_catalog_acl(resource_id)
        updated_acl = (
            replace(existing_acl, visibility_scope=target_scope)
            if existing_acl is not None
            else CatalogAclEntry(
                id=new_uuid7_str(),
                resource_id=updated_item.resource_id,
                resource_uri=updated_item.uri,
                title=updated_item.title,
                visibility_scope=target_scope,
                owner_org_unit_id=updated_item.owner_org_unit_id,
                owner_workspace_id=updated_item.owner_workspace_id,
                can_discover=True,
                can_execute=effective.can_execute,
                can_read_source=effective.can_read_source,
                can_edit=effective.can_edit,
                can_admin=effective.can_admin,
                system_prompt_secret=secret or "",
            )
        )
        self.evaluator.upsert_catalog_acl(updated_acl)
        new_effective, _ = self.evaluator.evaluate_catalog_resource(
            user,
            resource_id,
            workspace_id=effective_ws_id,
            require_read_source=False,
            instance=instance,
        )
        return updated_item, new_effective

    def resolve_effective_workflow(
        self,
        user: UserIdentity,
        *,
        workflow_uri: str,
        workspace_id: str,
        instance: str | None = None,
    ) -> EffectiveWorkflowMergeResult:
        """Merge 4 layers (`Base -> Team -> Workspace -> User`) and generate `run-lock.json`."""
        workspace = self.evaluator.get_workspace(workspace_id)
        if workspace is None:
            raise ResourceNotFoundError(instance=instance)
        if self.evaluator.resolve_workspace_access(user, workspace.id) is None:
            raise ScopeAccessDeniedError(instance=instance)
        base_wf = self._workflows_by_uri.get(workflow_uri.strip())
        if base_wf is None:
            raise ResourceNotFoundError(instance=instance)
        return FourLayerOverrideMerger.merge_and_lock(
            base_workflow=base_wf,
            org_units=self.evaluator.org_units,
            workspace=workspace,
            user_id=user.id,
            overrides=tuple(self._overrides),
            resolver=self.resolver,
        )

    def register_customization_override(
        self,
        user: UserIdentity,
        override: CustomizationOverrideEntity,
        *,
        instance: str | None = None,
    ) -> CustomizationOverrideEntity:
        """Register or replace a declarative override layer (`ScopeAccessGuard` enforced)."""
        self._enforce_workspace_or_role_mutation(user, override.workspace_id, instance=instance)
        if override.override_layer == "USER" and override.user_id != user.id:
            raise ScopeAccessDeniedError(instance=instance)
        if (
            override.override_layer == "TEAM"
            and override.org_unit_id != user.primary_org_unit_id
            and user.platform_role != "PLATFORM_ADMIN"
        ):
            raise ScopeAccessDeniedError(instance=instance)
        self._overrides = [o for o in self._overrides if o.override_key != override.override_key]
        self._overrides.append(override)
        return override

    def import_bmad_skill_pack(
        self,
        user: UserIdentity,
        pack_input: BmadSkillPackInput,
        *,
        instance: str | None = None,
    ) -> tuple[CatalogItemEntity, WorkflowDefinitionEntity, EffectiveResourcePermissions]:
        """Import a BMAD Skill Pack (`SKILL.md` + `customize.toml`) into the Catalog."""
        self._enforce_workspace_or_role_mutation(user, pack_input.workspace_id, instance=instance)
        item, wf_def = BmadSkillPackAdapter.import_pack(pack_input, resolver=self.resolver)
        self._workflows_by_uri[wf_def.uri] = wf_def
        acl = CatalogAclEntry(
            id=new_uuid7_str(),
            resource_id=item.resource_id,
            resource_uri=item.uri,
            title=item.title,
            visibility_scope=item.visibility_scope,
            owner_org_unit_id=item.owner_org_unit_id,
            owner_workspace_id=item.owner_workspace_id,
            grantee_transverse_group="architecture-board",
            can_discover=True,
            can_execute=True,
            can_read_source=True,
            can_edit=True,
            can_admin=True,
            system_prompt_secret=pack_input.skill_markdown,
        )
        self.upsert_catalog_item(item, acl)
        effective, _ = self.evaluator.evaluate_catalog_resource(
            user, item.resource_id, workspace_id=item.owner_workspace_id, instance=instance
        )
        return item, wf_def, effective
