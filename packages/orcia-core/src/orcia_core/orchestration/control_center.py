"""Multi-Level Workspace Control Center & `RunAccessGuard` (`Story 5.2`, `AD-4`, `AD-14`)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from orcia_core.orchestration._control_center_helpers import (
    build_command_palette_entries,
    resolve_scope_workspaces_helper,
    seed_default_control_center_runs,
)
from orcia_core.orchestration._orchestration_cc_notif_locales import get_cc_copy
from orcia_core.orchestration.control_center_models import (
    DEFAULT_GUIDANCE_DRAWER_STEPS,
    LIFECYCLE_SUGGESTED_WORKFLOWS,
    CommandPaletteEntry,
    ControlCenterOverview,
    DeclarativeOverrideLayer,
    GuidanceStepSpec,
    ProductLifecyclePhase,
    ScopeType,
    SupervisedDatasourceItem,
    SupervisedRunItem,
    WorkspaceGovernanceItem,
)
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    StepAlreadyClaimedByPeerError,
)
from orcia_core.orchestration.notifications_and_claims import (
    UnifiedNotificationAndClaimService,
)
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import AccessMode, UserIdentity, WorkspaceEntity


class ControlCenterOverviewService:
    """Multi-level supervision service (`GLOBAL|BU|TEAM|WORKSPACE`) & O(1) `RunAccessGuard`."""

    def __init__(
        self,
        *,
        evaluator: MatrixPermissionEvaluator,
        notification_service: UnifiedNotificationAndClaimService,
    ) -> None:
        self.evaluator = evaluator
        self.notification_service = notification_service
        self._lifecycle_by_ws: dict[str, ProductLifecyclePhase] = {
            "0192c4e0-0000-7000-8000-000000000201": "BUILD",
            "0192c4e0-0000-7000-8000-000000000202": "MIGRATION",
            "0192c4e0-0000-7000-8000-000000000203": "RUN",
        }
        self._runs: dict[str, SupervisedRunItem] = self._seed_default_runs()

    def _seed_default_runs(self) -> dict[str, SupervisedRunItem]:
        return seed_default_control_center_runs()

    def enforce_run_mutation_guard(
        self,
        user: UserIdentity,
        *,
        run_id: str,
        step_execution_id: str,
        now_utc: datetime | None = None,
        instance: str | None = None,
    ) -> SupervisedRunItem:
        """`RunAccessGuard` ($O(1)$): reject `READ_ONLY_OBSERVER` (`403`) or peer lock (`409`)."""
        if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
            raise ObserverModeReadOnlyError(instance=instance)
        run = self._runs.get(run_id)
        if run is None:
            raise ResourceNotFoundError(
                detail_code="ERR_RUN_NOT_FOUND",
                detail_params={"run_id": run_id},
                instance=instance,
            )
        access = self.evaluator.resolve_workspace_access(user, run.workspace_id)
        if access is None or access.access_mode == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        active_lock = self.notification_service.presence_lock.get_lock(
            step_execution_id, now_utc=now_utc
        )
        if active_lock is not None and active_lock.holder_user_id != user.id:
            raise StepAlreadyClaimedByPeerError(
                detail_code="ERR_CONTROL_CENTER_STEP_LOCKED",
                detail_params={
                    "step_id": step_execution_id,
                    "run_id": run_id,
                    "holder": active_lock.holder_display_name,
                },
                instance=instance,
            )
        return run

    def set_workspace_lifecycle_phase(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        lifecycle_phase: ProductLifecyclePhase,
        instance: str | None = None,
    ) -> WorkspaceGovernanceItem:
        """Update `RUN | BUILD | MIGRATION` lifecycle phase on a Workspace (`Story 5.2`)."""
        access = self.evaluator.enforce_scope_mutation_guard(user, workspace_id, instance=instance)
        ws = access.workspace
        self._lifecycle_by_ws[ws.id] = lifecycle_phase
        return WorkspaceGovernanceItem(
            workspace_id=ws.id,
            slug=ws.slug,
            name=ws.name,
            owner_org_unit_id=ws.owner_org_unit_id,
            visibility_mode=ws.visibility_mode,
            lifecycle_phase=lifecycle_phase,
            suggested_workflows=LIFECYCLE_SUGGESTED_WORKFLOWS[lifecycle_phase],
            access_mode=access.access_mode,
            finops_cost_usd=ws.finops_cost_usd if access.finops_visible else None,
            blackboard_payload_masked=False,
        )

    def _resolve_scope_workspaces(
        self, user: UserIdentity, scope_type: ScopeType, scope_id: str, instance: str | None
    ) -> tuple[str, list[tuple[WorkspaceEntity, AccessMode, bool, bool]]]:
        """Return `(scope_label, [(workspace, access_mode, finops_visible, payload_masked)])`."""
        return resolve_scope_workspaces_helper(self.evaluator, user, scope_type, scope_id, instance)

    def build_overview(
        self,
        user: UserIdentity,
        *,
        scope_type: ScopeType = "GLOBAL",
        scope_id: str = "0192c4e0-0000-7000-8000-000000000101",
        instance: str | None = None,
    ) -> ControlCenterOverview:
        """Consolidate the 4 fractal tabs for `GLOBAL | BU | TEAM | WORKSPACE` in a single pass."""
        cc = get_cc_copy()
        scope_label, ws_rows = self._resolve_scope_workspaces(user, scope_type, scope_id, instance)
        ws_meta = {ws.id: (mode, finops_ok, masked) for ws, mode, finops_ok, masked in ws_rows}

        contributor_runs: list[SupervisedRunItem] = []
        observer_runs: list[SupervisedRunItem] = []
        for run in self._runs.values():
            if run.workspace_id not in ws_meta:
                continue
            mode, _fin_ok, masked = ws_meta[run.workspace_id]
            lock = self.notification_service.presence_lock.get_lock(run.current_step_id)
            effective_mode: AccessMode = (
                "READ_ONLY_OBSERVER"
                if mode == "READ_ONLY_OBSERVER" or user.platform_role in ("OBSERVER", "BU_DIRECTOR")
                else "CONTRIBUTOR_ACTION_REQUIRED"
            )
            hydrated = (
                replace(
                    run,
                    workspace_name="[CONFIDENTIAL_RESTRICTED]",
                    workflow_key="masked",
                    title=cc["masked_summary"],
                    current_step_key="masked",
                    access_mode="READ_ONLY_OBSERVER",
                    claimed_by_user_id=None,
                    claimed_by_display_name=None,
                    blackboard_summary=cc["masked_summary"],
                    blackboard_payload_masked=True,
                )
                if masked
                else replace(
                    run,
                    access_mode=effective_mode,
                    claimed_by_user_id=lock.holder_user_id if lock else run.claimed_by_user_id,
                    claimed_by_display_name=(
                        lock.holder_display_name if lock else run.claimed_by_display_name
                    ),
                    blackboard_summary=run.blackboard_summary,
                    blackboard_payload_masked=False,
                )
            )
            if not masked and effective_mode == "CONTRIBUTOR_ACTION_REQUIRED":
                contributor_runs.append(hydrated)
            else:
                observer_runs.append(hydrated)

        datasources: list[SupervisedDatasourceItem] = []
        gov_items: list[WorkspaceGovernanceItem] = []
        total_finops = 0.0
        for ws, mode, finops_ok, masked in ws_rows:
            if finops_ok:
                total_finops += ws.finops_cost_usd
            phase = self._lifecycle_by_ws.get(ws.id, "BUILD")
            gov_items.append(
                WorkspaceGovernanceItem(
                    workspace_id=ws.id,
                    slug=ws.slug,
                    name=ws.name,
                    owner_org_unit_id=ws.owner_org_unit_id,
                    visibility_mode=ws.visibility_mode,
                    lifecycle_phase=phase,
                    suggested_workflows=LIFECYCLE_SUGGESTED_WORKFLOWS[phase],
                    access_mode=mode,
                    finops_cost_usd=ws.finops_cost_usd if finops_ok else None,
                    blackboard_payload_masked=masked,
                )
            )
            if not masked:
                for ds in ws.datasources:
                    datasources.append(
                        SupervisedDatasourceItem(
                            id=ds.id,
                            workspace_id=ws.id,
                            workspace_name=ws.name,
                            alias=ds.alias,
                            scheme=ds.scheme,
                            uri=ds.uri,
                            role=ds.role,
                            execution_identity=ds.execution_identity,
                            freshness_ttl_days=ds.freshness_ttl_days,
                            tripartite_status=(
                                "STALE_WARNING" if ds.freshness_ttl_days <= 30 else "ALIGNED"
                            ),
                        )
                    )

        viewer_mode: AccessMode = (
            "CONTRIBUTOR_ACTION_REQUIRED"
            if any(m == "CONTRIBUTOR_ACTION_REQUIRED" for _w, m, _f, _k in ws_rows)
            and user.platform_role not in ("OBSERVER", "BU_DIRECTOR")
            else "READ_ONLY_OBSERVER"
        )
        observer_banner = cc["observer_banner"] if viewer_mode == "READ_ONLY_OBSERVER" else None
        user_mode = "FAST_PATH" if user.platform_role == "TEAM_LEAD" else "COACHING"
        overrides = (
            DeclarativeOverrideLayer(
                workflow_key="architecture-arbitration-flow",
                title=cc["override_title"],
                base_layer=cc["override_base"],
                team_override=cc["override_team"],
                workspace_override="human_authored_required=true",
                user_override=cc["override_user_tpl"].format(user_mode=user_mode),
                spine_contract_ref="ARCHITECTURE-SPINE.md#AD-2",
            ),
        )
        return ControlCenterOverview(
            scope_type=scope_type,
            scope_id=scope_id,
            scope_label=scope_label,
            viewer_access_mode=viewer_mode,
            observer_banner_fr=observer_banner,
            consolidated_finops_usd=round(total_finops, 4),
            contributor_runs=tuple(contributor_runs),
            observer_runs=tuple(observer_runs),
            datasources=tuple(datasources),
            guidance_steps=DEFAULT_GUIDANCE_DRAWER_STEPS,
            workflow_overrides=overrides,
            org_units=self.evaluator.org_units,
            workspaces_governance=tuple(gov_items),
        )

    def search_command_palette(
        self, user: UserIdentity, query: str = ""
    ) -> tuple[CommandPaletteEntry, ...]:
        """Return `< 1 s` Command Palette (`⌘K`) entries filtered by `query` (`UX-DR13`)."""
        overview = self.build_overview(user, scope_type="GLOBAL")
        return build_command_palette_entries(overview, query=query)


__all__ = [
    "CommandPaletteEntry",
    "ControlCenterOverview",
    "ControlCenterOverviewService",
    "DEFAULT_GUIDANCE_DRAWER_STEPS",
    "DeclarativeOverrideLayer",
    "GuidanceStepSpec",
    "LIFECYCLE_SUGGESTED_WORKFLOWS",
    "ProductLifecyclePhase",
    "ScopeType",
    "SupervisedDatasourceItem",
    "SupervisedRunItem",
    "WorkspaceGovernanceItem",
]
