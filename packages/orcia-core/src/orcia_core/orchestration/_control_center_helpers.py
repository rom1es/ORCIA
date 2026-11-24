"""Seed & Command Palette builders for `ControlCenterOverviewService` (`Story 5.2`)."""

from __future__ import annotations

from orcia_core.orchestration._orchestration_cc_notif_locales import get_cc_copy
from orcia_core.orchestration.control_center_models import (
    CommandPaletteEntry,
    ControlCenterOverview,
    ScopeType,
    SupervisedRunItem,
)
from orcia_core.orchestration.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.permissions.errors import ScopeAccessDeniedError
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import AccessMode, UserIdentity, WorkspaceEntity
from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale


def resolve_scope_workspaces_helper(
    evaluator: MatrixPermissionEvaluator,
    user: UserIdentity,
    scope_type: ScopeType,
    scope_id: str,
    instance: str | None,
) -> tuple[str, list[tuple[WorkspaceEntity, AccessMode, bool, bool]]]:
    """Return `(scope_label, [(workspace, access_mode, finops_visible, payload_masked)])`."""
    if scope_type == "WORKSPACE":
        ws = evaluator.get_workspace(scope_id)
        if ws is None:
            raise ResourceNotFoundError(instance=instance)
        acc = evaluator.resolve_workspace_access(user, ws.id)
        if acc is not None:
            return (ws.name, [(ws, acc.access_mode, acc.finops_visible, False)])
        if user.platform_role == "PLATFORM_ADMIN":
            return (ws.name, [(ws, "READ_ONLY_OBSERVER", True, True)])
        raise ScopeAccessDeniedError(instance=instance)

    target_org_id = "0192c4e0-0000-7000-8000-000000000101" if scope_type == "GLOBAL" else scope_id
    root_node = {u.id: u for u in evaluator.org_units}.get(target_org_id)
    if root_node is None:
        raise ValidationDomainError(
            detail_code="ERR_CONTROL_CENTER_SCOPE_NOT_FOUND",
            detail_params={"scope_id": target_org_id},
            instance=instance,
        )
    allowed_org_ids = {target_org_id, *evaluator.get_descendant_org_unit_ids(target_org_id)}
    rows: list[tuple[WorkspaceEntity, AccessMode, bool, bool]] = []
    for ws in evaluator.workspaces:
        if ws.owner_org_unit_id not in allowed_org_ids:
            continue
        acc = evaluator.resolve_workspace_access(user, ws.id)
        if acc is not None:
            rows.append((ws, acc.access_mode, acc.finops_visible, False))
        elif (
            user.platform_role == "PLATFORM_ADMIN"
            and ws.visibility_mode == "CONFIDENTIAL_RESTRICTED"
        ):
            rows.append((ws, "READ_ONLY_OBSERVER", True, True))
    return (root_node.name, rows)


def seed_default_control_center_runs(
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> dict[str, SupervisedRunItem]:
    """Return initial default supervised runs seeded in the Control Center."""
    cc = get_cc_copy(locale)
    items = (
        SupervisedRunItem(
            run_id="0195f000-0000-7000-8000-000000000701",
            workspace_id="0192c4e0-0000-7000-8000-000000000201",
            workspace_name=cc["ws_1_name"],
            workflow_key="architecture-arbitration-flow",
            title=cc["run_1_title"],
            status="PAUSED_ARBITRATION",
            current_step_id="0195f000-0000-7000-8000-000000000801",
            current_step_key="architecture-arbitration",
            execution_mode="COACHING",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
            claimed_by_user_id=None,
            claimed_by_display_name=None,
            budget_consumed_usd=4.25,
            blackboard_summary=cc["run_1_summary"],
        ),
        SupervisedRunItem(
            run_id="0195f000-0000-7000-8000-000000000702",
            workspace_id="0192c4e0-0000-7000-8000-000000000202",
            workspace_name=cc["ws_2_name"],
            workflow_key="migration-readiness-flow",
            title=cc["run_2_title"],
            status="PAUSED_HUMAN_GATE",
            current_step_id="0195f000-0000-7000-8000-000000000802",
            current_step_key="ledger-human-gate",
            execution_mode="FAST_PATH",
            access_mode="READ_ONLY_OBSERVER",
            claimed_by_user_id=None,
            claimed_by_display_name=None,
            budget_consumed_usd=8.90,
            blackboard_summary=cc["run_2_summary"],
        ),
        SupervisedRunItem(
            run_id="0195f000-0000-7000-8000-000000000703",
            workspace_id="0192c4e0-0000-7000-8000-000000000203",
            workspace_name=cc["ws_3_name"],
            workflow_key="secops-incident-flow",
            title=cc["run_3_title"],
            status="RUNNING",
            current_step_id="0195f000-0000-7000-8000-000000000803",
            current_step_key="forensic-scan",
            execution_mode="FAST_PATH",
            access_mode="READ_ONLY_OBSERVER",
            claimed_by_user_id=None,
            claimed_by_display_name=None,
            budget_consumed_usd=19.50,
            blackboard_summary=cc["run_3_summary"],
        ),
    )
    return {r.run_id: r for r in items}


def build_command_palette_entries(
    overview: ControlCenterOverview,
    query: str = "",
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> tuple[CommandPaletteEntry, ...]:
    """Build `< 1 s` Command Palette (`⌘K`) navigation & workspace/run entries."""
    cc = get_cc_copy(locale)
    q = query.strip().lower()
    entries: list[CommandPaletteEntry] = [
        CommandPaletteEntry(
            "nav-cockpit", "NAVIGATION", cc["nav_cockpit"], cc["nav_cockpit_sub"], "g c", "/cockpit"
        ),
        CommandPaletteEntry(
            "nav-inbox", "NAVIGATION", cc["nav_inbox"], cc["nav_inbox_sub"], "g i", "/inbox"
        ),
        CommandPaletteEntry(
            "nav-workspaces",
            "NAVIGATION",
            cc["nav_workspaces"],
            cc["nav_workspaces_sub"],
            "g w",
            "/workspaces",
        ),
        CommandPaletteEntry(
            "nav-catalog", "NAVIGATION", cc["nav_catalog"], cc["nav_catalog_sub"], "g f", "/catalog"
        ),
        CommandPaletteEntry(
            "nav-ontology",
            "NAVIGATION",
            cc["nav_ontology"],
            cc["nav_ontology_sub"],
            "g o",
            "/ontology",
        ),
        CommandPaletteEntry(
            "nav-governance",
            "NAVIGATION",
            cc["nav_governance"],
            cc["nav_governance_sub"],
            "g g",
            "/governance",
        ),
        CommandPaletteEntry(
            "nav-audit", "NAVIGATION", cc["nav_audit"], cc["nav_audit_sub"], "g a", "/audit"
        ),
        CommandPaletteEntry(
            "nav-admin", "NAVIGATION", cc["nav_admin"], cc["nav_admin_sub"], "g s", "/admin"
        ),
    ]
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
                subtitle_fr=cc["ws_subtitle_tpl"].format(
                    phase=ws.lifecycle_phase, visibility=ws.visibility_mode
                ),
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


__all__ = ["build_command_palette_entries", "seed_default_control_center_runs"]
