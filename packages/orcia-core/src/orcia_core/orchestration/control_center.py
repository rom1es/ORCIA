"""Multi-Level Workspace Control Center & `RunAccessGuard` (`Story 5.2`, `AD-4`, `AD-14`)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

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
    ValidationDomainError,
)
from orcia_core.orchestration.notifications_and_claims import (
    UnifiedNotificationAndClaimService,
)
from orcia_core.permissions.errors import ScopeAccessDeniedError
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
        items = (
            SupervisedRunItem(
                run_id="0195f000-0000-7000-8000-000000000701",
                workspace_id="0192c4e0-0000-7000-8000-000000000201",
                workspace_name="Workspace 1 — Paiements & Checkout Web",
                workflow_key="architecture-arbitration-flow",
                title="Run #701 — Arbitrage Topologie Paiements v2",
                status="PAUSED_ARBITRATION",
                current_step_id="0195f000-0000-7000-8000-000000000801",
                current_step_key="architecture-arbitration",
                execution_mode="COACHING",
                access_mode="CONTRIBUTOR_ACTION_REQUIRED",
                claimed_by_user_id=None,
                claimed_by_display_name=None,
                budget_consumed_usd=4.25,
                blackboard_summary="Synthèse d'architecture prête pour arbitrage humain.",
            ),
            SupervisedRunItem(
                run_id="0195f000-0000-7000-8000-000000000702",
                workspace_id="0192c4e0-0000-7000-8000-000000000202",
                workspace_name="Workspace 2 — Core Banking & Ledger",
                workflow_key="migration-readiness-flow",
                title="Run #702 — Audit Bascule Core Ledger",
                status="PAUSED_HUMAN_GATE",
                current_step_id="0195f000-0000-7000-8000-000000000802",
                current_step_key="ledger-human-gate",
                execution_mode="FAST_PATH",
                access_mode="READ_ONLY_OBSERVER",
                claimed_by_user_id=None,
                claimed_by_display_name=None,
                budget_consumed_usd=8.90,
                blackboard_summary="Rapport de conformité Core Ledger généré.",
            ),
            SupervisedRunItem(
                run_id="0195f000-0000-7000-8000-000000000703",
                workspace_id="0192c4e0-0000-7000-8000-000000000203",
                workspace_name="Workspace 3 — Audit Confidentiel SecOps (Restreint)",
                workflow_key="secops-incident-flow",
                title="Run #703 — Investigation SecOps Restreinte",
                status="RUNNING",
                current_step_id="0195f000-0000-7000-8000-000000000803",
                current_step_key="forensic-scan",
                execution_mode="FAST_PATH",
                access_mode="READ_ONLY_OBSERVER",
                claimed_by_user_id=None,
                claimed_by_display_name=None,
                budget_consumed_usd=19.50,
                blackboard_summary="Payload métier confidentiel SecOps.",
            ),
        )
        return {r.run_id: r for r in items}

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
                detail_override=f"Run '{run_id}' introuvable.", instance=instance
            )
        access = self.evaluator.resolve_workspace_access(user, run.workspace_id)
        if access is None or access.access_mode == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(instance=instance)
        active_lock = self.notification_service.presence_lock.get_lock(
            step_execution_id, now_utc=now_utc
        )
        if active_lock is not None and active_lock.holder_user_id != user.id:
            raise StepAlreadyClaimedByPeerError(
                detail_override=(
                    f"Mutation refusée: l'étape '{step_execution_id}' du Run '{run_id}' est "
                    f"verrouillée par '{active_lock.holder_display_name}'."
                ),
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
        if scope_type == "WORKSPACE":
            ws = self.evaluator.get_workspace(scope_id)
            if ws is None:
                raise ResourceNotFoundError(instance=instance)
            acc = self.evaluator.resolve_workspace_access(user, ws.id)
            if acc is not None:
                return (ws.name, [(ws, acc.access_mode, acc.finops_visible, False)])
            if user.platform_role == "PLATFORM_ADMIN":
                return (ws.name, [(ws, "READ_ONLY_OBSERVER", True, True)])
            raise ScopeAccessDeniedError(instance=instance)

        target_org_id = (
            "0192c4e0-0000-7000-8000-000000000101" if scope_type == "GLOBAL" else scope_id
        )
        org_map = {u.id: u for u in self.evaluator.org_units}
        root_node = org_map.get(target_org_id)
        if root_node is None:
            raise ValidationDomainError(
                detail_override=f"Périmètre '{target_org_id}' introuvable.", instance=instance
            )
        allowed_org_ids = {
            target_org_id,
            *self.evaluator.get_descendant_org_unit_ids(target_org_id),
        }
        rows: list[tuple[WorkspaceEntity, AccessMode, bool, bool]] = []
        for ws in self.evaluator.workspaces:
            if ws.owner_org_unit_id not in allowed_org_ids:
                continue
            acc = self.evaluator.resolve_workspace_access(user, ws.id)
            if acc is not None:
                rows.append((ws, acc.access_mode, acc.finops_visible, False))
            elif (
                user.platform_role == "PLATFORM_ADMIN"
                and ws.visibility_mode == "CONFIDENTIAL_RESTRICTED"
            ):
                rows.append((ws, "READ_ONLY_OBSERVER", True, True))
        return (root_node.name, rows)

    def build_overview(
        self,
        user: UserIdentity,
        *,
        scope_type: ScopeType = "GLOBAL",
        scope_id: str = "0192c4e0-0000-7000-8000-000000000101",
        instance: str | None = None,
    ) -> ControlCenterOverview:
        """Consolidate the 4 fractal tabs for `GLOBAL | BU | TEAM | WORKSPACE` in a single pass."""
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
            hydrated = replace(
                run,
                access_mode=effective_mode,
                claimed_by_user_id=lock.holder_user_id if lock else run.claimed_by_user_id,
                claimed_by_display_name=(
                    lock.holder_display_name if lock else run.claimed_by_display_name
                ),
                blackboard_summary=(
                    "[CONFIDENTIAL_RESTRICTED — Payload Métier Masqué]"
                    if masked
                    else run.blackboard_summary
                ),
                blackboard_payload_masked=masked,
            )
            if effective_mode == "CONTRIBUTOR_ACTION_REQUIRED":
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
        observer_banner = (
            "👁️ Mode Consultation Seule — Vous suivez ce périmètre en tant qu'Observateur"
            if viewer_mode == "READ_ONLY_OBSERVER"
            else None
        )
        user_mode = "FAST_PATH" if user.platform_role == "TEAM_LEAD" else "COACHING"
        overrides = (
            DeclarativeOverrideLayer(
                workflow_key="architecture-arbitration-flow",
                title="Arbitrage Topologie & Gates Adaptatives",
                base_layer="v1.0.0 (Socle Plateforme)",
                team_override="seuil_gate_agentique=0.85",
                workspace_override="human_authored_required=true",
                user_override=f"mode_execution={user_mode}",
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
        q = query.strip().lower()
        entries: list[CommandPaletteEntry] = [
            CommandPaletteEntry(
                "nav-cockpit",
                "NAVIGATION",
                "Aller au Cockpit & Flux de Travail",
                "Navigation rapide",
                "g c",
                "/cockpit",
            ),
            CommandPaletteEntry(
                "nav-inbox",
                "NAVIGATION",
                "Aller à la Boîte & Mes Runs",
                "Notifications & Claims",
                "g i",
                "/inbox",
            ),
            CommandPaletteEntry(
                "nav-workspaces",
                "NAVIGATION",
                "Aller au Centre de Pilotage des Workspaces",
                "Supervision 4 onglets",
                "g w",
                "/workspaces",
            ),
            CommandPaletteEntry(
                "nav-catalog",
                "NAVIGATION",
                "Aller au Catalogue Fédéré",
                "Agents, Skills & Workflows",
                "g f",
                "/catalog",
            ),
            CommandPaletteEntry(
                "nav-ontology",
                "NAVIGATION",
                "Aller à l'Ontologie & Graphe",
                "Concepts SKOS & What-If",
                "g o",
                "/ontology",
            ),
            CommandPaletteEntry(
                "nav-governance",
                "NAVIGATION",
                "Aller aux Gates & Permissions",
                "Courtier d'Accès",
                "g g",
                "/governance",
            ),
            CommandPaletteEntry(
                "nav-audit",
                "NAVIGATION",
                "Aller à l'Audit & FinOps",
                "Registre immuable",
                "g a",
                "/audit",
            ),
            CommandPaletteEntry(
                "nav-admin",
                "NAVIGATION",
                "Aller à l'Administration",
                "Topologie & Sécurité",
                "g s",
                "/admin",
            ),
        ]
        overview = self.build_overview(user, scope_type="GLOBAL")
        for run in (*overview.contributor_runs, *overview.observer_runs):
            entries.append(
                CommandPaletteEntry(
                    entry_id=f"run-{run.run_id}",
                    category="RUN",
                    label_fr=run.title,
                    subtitle_fr=f"{run.workspace_name} • {run.current_step_key}",
                    shortcut="Alt + ↑/↓",
                    target_route=f"/cockpit?runId={run.run_id}",
                    access_mode=run.access_mode,
                )
            )
        for ws in overview.workspaces_governance:
            entries.append(
                CommandPaletteEntry(
                    entry_id=f"ws-{ws.workspace_id}",
                    category="WORKSPACE",
                    label_fr=ws.name,
                    subtitle_fr=f"Cycle {ws.lifecycle_phase} • {ws.visibility_mode}",
                    shortcut="⌘W",
                    target_route=f"/workspaces/{ws.workspace_id}",
                    access_mode=ws.access_mode,
                )
            )
        if not q:
            return tuple(entries)
        return tuple(
            e
            for e in entries
            if q in e.label_fr.lower() or q in e.subtitle_fr.lower() or q in e.shortcut.lower()
        )


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
