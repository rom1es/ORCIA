import { OrciaIcon, type ControlCenterWorkspaceGovItem } from "@orcia/ui";
import React from "react";
import type { ConfiguredOrgUnit } from "../../components/platformSetupStore";
import { resolveDictionaryForFlag, resolveLocaleForFlag } from "../../i18n";
import { WorkspaceMembersInstructionsCard } from "./WorkspaceMembersInstructionsCard";
import {
  resolveWorkspacePhaseLabel,
  resolveWorkspaceVisibilityMeta,
} from "./workspaceDisplayHelpers";
import type { WorkspaceFeedbackInput } from "./workspaceFeedbackTypes";

export interface WorkspaceMembersAndSettingsTabProps {
  readonly isFr: boolean;
  readonly activeWorkspace: ControlCenterWorkspaceGovItem;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly onFeedback?: (feedback: WorkspaceFeedbackInput) => void;
}

export function WorkspaceMembersAndSettingsTab({
  isFr,
  activeWorkspace,
  orgUnits,
  onFeedback,
}: WorkspaceMembersAndSettingsTabProps): React.ReactElement {
  const locale = resolveLocaleForFlag(isFr);
  const dict = resolveDictionaryForFlag(isFr, locale);
  const tabsCopy = dict.featureWorkspaces.detailTabs;
  const wsId = activeWorkspace.workspaceId;
  const phaseLabel = resolveWorkspacePhaseLabel(activeWorkspace.lifecyclePhase, isFr);
  const visibilityMeta = resolveWorkspaceVisibilityMeta(activeWorkspace.visibilityMode, isFr);

  const ownerTeam = orgUnits.find(
    (u) =>
      u.id === activeWorkspace.ownerOrgUnitId ||
      (activeWorkspace.ownerOrgUnitName && u.name === activeWorkspace.ownerOrgUnitName),
  );
  const leadIds = Array.from(
    new Set([
      ...(ownerTeam?.leadUserIds ?? []),
      ...(ownerTeam?.leadUserId ? [ownerTeam.leadUserId] : []),
    ]),
  );
  const memberIds = Array.from(
    new Set((ownerTeam?.memberUserIds ?? []).filter((id) => !leadIds.includes(id))),
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <div
        data-testid="workspace-members-roster-card"
        className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-3"
        style={{ display: "flex", flexDirection: "column", gap: "8px" }}
      >
        <strong style={{ fontSize: "13px" }}>{tabsCopy.membersRosterTitle}</strong>
        {leadIds.length === 0 && memberIds.length === 0 ? (
          <p
            data-testid="workspace-members-empty-hint"
            style={{ margin: 0, fontSize: "12px", color: "var(--color-muted-foreground)" }}
          >
            {tabsCopy.membersEmptyHint}
          </p>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", fontSize: "12px" }}>
            {leadIds.map((id) => (
              <span
                key={`lead-${id}`}
                data-testid={`workspace-member-lead-${id}`}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2 py-0.5"
              >
                {`${tabsCopy.membersLeadsLabel}: ${id}`}
              </span>
            ))}
            {memberIds.map((id) => (
              <span
                key={`member-${id}`}
                data-testid={`workspace-member-item-${id}`}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2 py-0.5"
              >
                {`${tabsCopy.membersListLabel}: ${id}`}
              </span>
            ))}
          </div>
        )}
      </div>

      <div
        data-testid="workspace-settings-summary-card"
        className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-3"
        style={{ display: "flex", flexDirection: "column", gap: "8px" }}
      >
        <strong style={{ fontSize: "13px" }}>{tabsCopy.workspaceSettingsTitle}</strong>
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px", fontSize: "12px" }}>
          <span
            data-testid={`workspace-settings-phase-badge-${wsId}`}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1"
          >
            {`${tabsCopy.workspaceSettingsPhaseLabel}: ${phaseLabel}`}
          </span>
          <span
            data-testid={`workspace-settings-visibility-badge-${wsId}`}
            className="inline-flex items-center gap-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1"
          >
            <OrciaIcon name={visibilityMeta.iconName} />
            <span>{`${tabsCopy.workspaceSettingsVisibilityLabel}: ${visibilityMeta.fullLabel}`}</span>
          </span>
        </div>
      </div>

      <WorkspaceMembersInstructionsCard
        isFr={isFr}
        activeWorkspace={activeWorkspace}
        onFeedback={onFeedback}
      />
    </div>
  );
}
