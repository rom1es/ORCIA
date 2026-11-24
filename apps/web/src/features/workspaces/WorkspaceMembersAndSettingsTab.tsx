import {
  getOrciaIconGlyph,
  OrciaIcon,
  type ControlCenterWorkspaceGovItem,
  type ProductLifecyclePhaseType,
  type WorkspaceVisibilityMode,
} from "@orcia/ui";
import React, { useState } from "react";
import type { ConfiguredOrgUnit } from "../../components/platformSetupStore";
import {
  formatI18nTemplate,
  resolveDictionaryForFlag,
  resolveLocaleForFlag,
} from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import { WorkspaceMembersInstructionsCard } from "./WorkspaceMembersInstructionsCard";

export interface WorkspaceMembersAndSettingsTabProps {
  readonly isFr: boolean;
  readonly activeWorkspace: ControlCenterWorkspaceGovItem;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly onUpdateWorkspacePhase?: (
    workspaceId: string,
    phase: ProductLifecyclePhaseType,
  ) => void | Promise<void>;
  readonly onUpdateWorkspaceVisibility?: (
    workspaceId: string,
    visibilityMode: WorkspaceVisibilityMode,
  ) => void | Promise<void>;
  readonly onFeedback?: (message: string | null) => void;
}

const selectStyle: React.CSSProperties = {
  padding: "5px 9px",
  fontSize: "12px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
};

export function WorkspaceMembersAndSettingsTab({
  isFr,
  activeWorkspace,
  orgUnits,
  onUpdateWorkspacePhase,
  onUpdateWorkspaceVisibility,
  onFeedback,
}: WorkspaceMembersAndSettingsTabProps): React.ReactElement {
  const locale = resolveLocaleForFlag(isFr);
  const dict = resolveDictionaryForFlag(isFr, locale);
  const tabsCopy = dict.featureWorkspaces.detailTabs;
  const cardCopy = dict.featureWorkspaces.summaryCard;
  const wsId = activeWorkspace.workspaceId;
  const isObserver = activeWorkspace.accessMode === "READ_ONLY_OBSERVER";

  const [savedSettingsWsId, setSavedSettingsWsId] = useState<string | null>(null);
  const [updatingSettings, setUpdatingSettings] = useState<boolean>(false);

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

  const handlePhaseChange = async (nextPhase: ProductLifecyclePhaseType) => {
    if (!onUpdateWorkspacePhase || isObserver) return;
    setUpdatingSettings(true);
    try {
      await Promise.resolve(onUpdateWorkspacePhase(wsId, nextPhase));
      setSavedSettingsWsId(wsId);
    } catch (err: unknown) {
      onFeedback?.(
        `⚠️ ${formatRfc9457ErrorToBanner(err, locale, cardCopy.phaseErrorContext).fullText}`,
      );
    } finally {
      setUpdatingSettings(false);
    }
  };

  const handleVisibilityChange = async (
    nextVis: WorkspaceVisibilityMode,
    shareTemplate?: string,
  ) => {
    if (!onUpdateWorkspaceVisibility || isObserver) return;
    setUpdatingSettings(true);
    try {
      await Promise.resolve(onUpdateWorkspaceVisibility(wsId, nextVis));
      setSavedSettingsWsId(wsId);
      if (shareTemplate) {
        onFeedback?.(formatI18nTemplate(shareTemplate, { name: activeWorkspace.name }));
      }
    } catch (err: unknown) {
      const ctx = shareTemplate ? cardCopy.shareErrorContext : cardCopy.visibilityErrorContext;
      onFeedback?.(`⚠️ ${formatRfc9457ErrorToBanner(err, locale, ctx).fullText}`);
    } finally {
      setUpdatingSettings(false);
    }
  };

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
        data-testid="workspace-settings-controls-card"
        className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-3"
        style={{ display: "flex", flexDirection: "column", gap: "8px" }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "8px" }}>
          <strong style={{ fontSize: "13px" }}>{tabsCopy.workspaceSettingsTitle}</strong>
          {savedSettingsWsId === wsId && (
            <span
              data-testid={`workspace-settings-saved-badge-${wsId}`}
              style={{
                fontSize: "11px",
                fontWeight: 700,
                padding: "2px 8px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-action-primary-subtle)",
                color: "var(--color-status-success)",
              }}
            >
              {tabsCopy.savedBadge}
            </span>
          )}
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}>
            <span>{tabsCopy.workspaceSettingsPhaseLabel}</span>
            <select
              data-testid={`workspace-settings-phase-select-${wsId}`}
              aria-label={tabsCopy.workspaceSettingsPhaseLabel}
              disabled={isObserver || updatingSettings || !onUpdateWorkspacePhase}
              value={activeWorkspace.lifecyclePhase}
              onChange={(e) => void handlePhaseChange(e.target.value as ProductLifecyclePhaseType)}
              style={selectStyle}
            >
              <option value="BUILD">{cardCopy.phaseBuildOption}</option>
              <option value="RUN">{cardCopy.phaseRunOption}</option>
              <option value="MIGRATION">{cardCopy.phaseMigrationOption}</option>
            </select>
          </label>

          <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px" }}>
            <span>{tabsCopy.workspaceSettingsVisibilityLabel}</span>
            <select
              data-testid={`workspace-settings-visibility-select-${wsId}`}
              aria-label={tabsCopy.workspaceSettingsVisibilityLabel}
              disabled={isObserver || updatingSettings || !onUpdateWorkspaceVisibility}
              value={activeWorkspace.visibilityMode}
              onChange={(e) => void handleVisibilityChange(e.target.value as WorkspaceVisibilityMode)}
              style={selectStyle}
            >
              <option value="STANDARD">
                {`${getOrciaIconGlyph("team")} ${cardCopy.visibilityStandard}`}
              </option>
              <option value="PRIVATE_USER">
                {`${getOrciaIconGlyph("lock")} ${cardCopy.visibilityPrivate}`}
              </option>
              <option value="CONFIDENTIAL_RESTRICTED">
                {`${getOrciaIconGlyph("shield")} ${cardCopy.visibilityConfidential}`}
              </option>
            </select>
          </label>

          {activeWorkspace.visibilityMode === "PRIVATE_USER" && onUpdateWorkspaceVisibility && (
            <button
              type="button"
              data-testid={`workspace-settings-share-btn-${wsId}`}
              disabled={isObserver || updatingSettings}
              onClick={() => void handleVisibilityChange("STANDARD", cardCopy.shareSuccessTemplate)}
              className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
            >
              <OrciaIcon name="team" /> {cardCopy.shareWithTeamBtn}
            </button>
          )}
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
