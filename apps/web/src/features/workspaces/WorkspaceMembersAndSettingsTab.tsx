import {
  OrciaDataCard,
  OrciaIcon,
  type ControlCenterWorkspaceGovItem,
  type WorkspaceVisibilityMode,
} from "@orcia/ui";
import React, { useState } from "react";
import type { ConfiguredOrgUnit } from "../../components/platformSetupStore";
import { resolveDictionaryForFlag, resolveLocaleForFlag } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import { useAuthSessionStore } from "../../stores/authSessionStore";
import { WorkspaceMembersInstructionsCard } from "./WorkspaceMembersInstructionsCard";
import { WorkspacePacksTabSection } from "./WorkspacePacksTabSection";
import { resolveWorkspaceVisibilityMeta } from "./workspaceDisplayHelpers";
import type { WorkspaceFeedbackInput } from "./workspaceFeedbackTypes";

export interface WorkspaceMembersAndSettingsTabProps {
  readonly isFr: boolean;
  readonly activeWorkspace: ControlCenterWorkspaceGovItem;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly onUpdateWorkspaceVisibility?: (
    workspaceId: string,
    visibilityMode: WorkspaceVisibilityMode,
  ) => void | Promise<void>;
  readonly onMarkAutosaved?: (workspaceId: string) => void;
  readonly onFeedback?: (feedback: WorkspaceFeedbackInput) => void;
}

export function WorkspaceMembersAndSettingsTab({
  isFr,
  activeWorkspace,
  orgUnits,
  onUpdateWorkspaceVisibility,
  onMarkAutosaved,
  onFeedback,
}: WorkspaceMembersAndSettingsTabProps): React.ReactElement {
  const locale = resolveLocaleForFlag(isFr);
  const dict = resolveDictionaryForFlag(isFr, locale);
  const tabsCopy = dict.featureWorkspaces.detailTabs;
  const cardCopy = dict.featureWorkspaces.summaryCard;
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const [isUpdatingVisibility, setIsUpdatingVisibility] = useState(false);

  const wsId = activeWorkspace.workspaceId;
  const visibilityMeta = resolveWorkspaceVisibilityMeta(activeWorkspace.visibilityMode, isFr);
  const isPrivateLocked = activeWorkspace.visibilityMode === "PRIVATE_USER";
  const isVisibilityDisabled =
    isPrivateLocked || readOnlyObserver || isUpdatingVisibility || !onUpdateWorkspaceVisibility;

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

  const activeVisibilityDescription =
    activeWorkspace.visibilityMode === "PRIVATE_USER"
      ? tabsCopy.visibilityModePrivateDesc
      : activeWorkspace.visibilityMode === "CONFIDENTIAL_RESTRICTED"
        ? tabsCopy.visibilityModeConfidentialDesc
        : tabsCopy.visibilityModeStandardDesc;

  const handleVisibilityChange = (nextVis: WorkspaceVisibilityMode) => {
    if (!onUpdateWorkspaceVisibility || isPrivateLocked || readOnlyObserver) return;
    setIsUpdatingVisibility(true);
    void Promise.resolve(onUpdateWorkspaceVisibility(wsId, nextVis))
      .then(() => {
        onMarkAutosaved?.(wsId);
      })
      .catch((err: unknown) => {
        onFeedback?.({
          tone: "crimson",
          message: formatRfc9457ErrorToBanner(err, locale, cardCopy.visibilityErrorContext)
            .fullText,
        });
      })
      .finally(() => {
        setIsUpdatingVisibility(false);
      });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <OrciaDataCard
        testId="workspace-members-roster-card"
        title={tabsCopy.membersRosterTitle}
        icon="team"
      >
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
      </OrciaDataCard>

      <OrciaDataCard
        testId="workspace-settings-summary-card"
        title={tabsCopy.workspaceSettingsTitle}
        icon={isPrivateLocked ? "lock" : "shield"}
        metaBadge={
          <span
            data-testid={`workspace-settings-visibility-badge-${wsId}`}
            className="inline-flex items-center gap-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-0.5 text-[11px] font-semibold"
          >
            <OrciaIcon name={visibilityMeta.iconName} size={12} />
            <span>{`${tabsCopy.workspaceSettingsVisibilityLabel}: ${visibilityMeta.fullLabel}`}</span>
          </span>
        }
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px" }}>
            <label
              className="orcia-ds-label"
              style={{ minWidth: "260px", maxWidth: "360px" }}
            >
              <span>{tabsCopy.workspaceSettingsVisibilityLabel}</span>
              <select
                data-testid={`workspace-card-visibility-select-${wsId}`}
                aria-label={cardCopy.visibilitySelectAriaLabel}
                value={activeWorkspace.visibilityMode}
                disabled={isVisibilityDisabled}
                onChange={(e) => handleVisibilityChange(e.target.value as WorkspaceVisibilityMode)}
                className="orcia-ds-select"
              >
                <option value="STANDARD">{cardCopy.visibilityStandard}</option>
                <option value="CONFIDENTIAL_RESTRICTED">{cardCopy.visibilityConfidential}</option>
                <option value="PRIVATE_USER" disabled={!isPrivateLocked}>
                  {cardCopy.visibilityPrivate}
                </option>
              </select>
            </label>
          </div>

          <p
            data-testid={`workspace-visibility-mode-description-${wsId}`}
            style={{ margin: 0, fontSize: "12px", color: "var(--color-muted-foreground)" }}
          >
            {activeVisibilityDescription}
          </p>

          {isPrivateLocked ? (
            <p
              data-testid={`workspace-visibility-private-locked-hint-${wsId}`}
              className="inline-flex items-center gap-1.5 text-xs"
              style={{ margin: 0, color: "var(--color-muted-foreground)" }}
            >
              <OrciaIcon name="lock" size={12} />
              <span>{tabsCopy.visibilityPrivateLockedHint}</span>
            </p>
          ) : readOnlyObserver ? (
            <p
              data-testid={`workspace-visibility-observer-locked-hint-${wsId}`}
              className="inline-flex items-center gap-1.5 text-xs"
              style={{ margin: 0, color: "var(--color-muted-foreground)" }}
            >
              <OrciaIcon name="eye" size={12} />
              <span>{tabsCopy.visibilityObserverLockedHint}</span>
            </p>
          ) : null}
        </div>
      </OrciaDataCard>

      <OrciaDataCard>
        <WorkspaceMembersInstructionsCard
          isFr={isFr}
          activeWorkspace={activeWorkspace}
          onFeedback={onFeedback}
        />
      </OrciaDataCard>

      <WorkspacePacksTabSection workspaceId={wsId} />
    </div>
  );
}
