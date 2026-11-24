import {
  getOrciaIconGlyph,
  OrciaIcon,
  type ControlCenterWorkspaceGovItem,
  type ProductLifecyclePhaseType,
  type WorkspaceVisibilityMode,
} from "@orcia/ui";
import React from "react";
import { resolveGlobalScopeLabel } from "../../components/platformSetupWorkspaces";
import {
  formatI18nTemplate,
  resolveDictionaryForFlag,
  resolveLocaleForFlag,
} from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import {
  resolveWorkspacePhaseLabel,
  resolveWorkspaceVisibilityMeta,
} from "./workspaceDisplayHelpers";

export interface WorkspaceCompactHeaderProps {
  readonly isFr: boolean;
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly activeWorkspace: ControlCenterWorkspaceGovItem | null;
  readonly isAutosaved: boolean;
  readonly isCreateFormExpanded: boolean;
  readonly onSelectWorkspace: (workspaceId: string) => void;
  readonly onToggleCreateForm: () => void;
  readonly onNavigateToGlossary: () => void;
  readonly onUpdateWorkspacePhase: (
    workspaceId: string,
    phase: ProductLifecyclePhaseType,
  ) => void | Promise<void>;
  readonly onUpdateWorkspaceVisibility: (
    workspaceId: string,
    visibilityMode: WorkspaceVisibilityMode,
  ) => void | Promise<void>;
  readonly onMarkAutosaved: (workspaceId: string) => void;
  readonly onFeedback: (message: string) => void;
}

const selectStyle: React.CSSProperties = {
  padding: "5px 9px",
  fontSize: "12px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
};

export function WorkspaceCompactHeader({
  isFr,
  workspaces,
  activeWorkspace,
  isAutosaved,
  isCreateFormExpanded,
  onSelectWorkspace,
  onToggleCreateForm,
  onNavigateToGlossary,
  onUpdateWorkspacePhase,
  onUpdateWorkspaceVisibility,
  onMarkAutosaved,
  onFeedback,
}: WorkspaceCompactHeaderProps): React.ReactElement {
  const resolvedLocale = resolveLocaleForFlag(isFr);
  const dict = resolveDictionaryForFlag(isFr, resolvedLocale);
  const studioCopy = dict.featureWorkspaces.studioCards;
  const cardCopy = dict.featureWorkspaces.summaryCard;
  const panelCopy = dict.featureWorkspaces.panel;

  const privateSpaces = workspaces.filter((w) => w.visibilityMode === "PRIVATE_USER");
  const teamSpaces = workspaces.filter((w) => w.visibilityMode !== "PRIVATE_USER");
  const visibilityMeta = activeWorkspace
    ? resolveWorkspaceVisibilityMeta(activeWorkspace.visibilityMode, isFr)
    : null;
  const phaseLabel = activeWorkspace
    ? resolveWorkspacePhaseLabel(activeWorkspace.lifecyclePhase, isFr)
    : null;

  const handlePhaseChange = (nextPhase: ProductLifecyclePhaseType) => {
    if (!activeWorkspace) return;
    void Promise.resolve(onUpdateWorkspacePhase(activeWorkspace.workspaceId, nextPhase))
      .then(() => onMarkAutosaved(activeWorkspace.workspaceId))
      .catch((err: unknown) => {
        onFeedback(
          `⚠️ ${formatRfc9457ErrorToBanner(err, resolvedLocale, cardCopy.phaseErrorContext).fullText}`,
        );
      });
  };

  const handleVisibilityChange = (
    nextVis: WorkspaceVisibilityMode,
    successTemplate?: string,
  ) => {
    if (!activeWorkspace) return;
    void Promise.resolve(onUpdateWorkspaceVisibility(activeWorkspace.workspaceId, nextVis))
      .then(() => {
        onMarkAutosaved(activeWorkspace.workspaceId);
        if (successTemplate) {
          onFeedback(formatI18nTemplate(successTemplate, { name: activeWorkspace.name }));
        }
      })
      .catch((err: unknown) => {
        const ctx = successTemplate ? cardCopy.shareErrorContext : cardCopy.visibilityErrorContext;
        onFeedback(`⚠️ ${formatRfc9457ErrorToBanner(err, resolvedLocale, ctx).fullText}`);
      });
  };

  return (
    <header
      data-testid="workspaces-compact-header"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "10px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
            <h1
              data-testid="workspaces-active-title"
              style={{ margin: 0, fontSize: "18px", fontWeight: 700 }}
            >
              {activeWorkspace ? activeWorkspace.name : studioCopy.emptyHeaderTitle}
            </h1>
            {activeWorkspace && phaseLabel && (
              <span
                data-testid={`workspace-phase-badge-${activeWorkspace.workspaceId}`}
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--color-action-primary-subtle)",
                  color: "var(--color-action-primary)",
                }}
              >
                {phaseLabel}
              </span>
            )}
            {activeWorkspace && visibilityMeta && (
              <span
                data-testid={`workspace-visibility-badge-${activeWorkspace.workspaceId}`}
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--color-bg-elevated)",
                  border: "1px solid var(--color-border-subtle)",
                }}
              >
                <OrciaIcon name={visibilityMeta.iconName} /> {visibilityMeta.shortLabel}
              </span>
            )}
            {activeWorkspace && isAutosaved && (
              <span
                data-testid={`workspace-autosaved-badge-${activeWorkspace.workspaceId}`}
                style={{
                  fontSize: "11px",
                  fontWeight: 700,
                  padding: "2px 8px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--color-action-primary-subtle)",
                  color: "var(--color-status-success)",
                }}
              >
                <OrciaIcon name="check" /> {cardCopy.savedBadge}
              </span>
            )}
          </div>
          {activeWorkspace && (
            <div style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>
              {cardCopy.billingTeamLabel}{" "}
              <strong>
                {activeWorkspace.ownerOrgUnitName ?? resolveGlobalScopeLabel(isFr)}
              </strong>
            </div>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
          {activeWorkspace && workspaces.length > 0 && (
            <select
              data-testid="workspaces-active-switcher-select"
              aria-label={studioCopy.switcherAriaLabel}
              value={activeWorkspace.workspaceId}
              onChange={(e) => onSelectWorkspace(e.target.value)}
              style={{ ...selectStyle, minWidth: "200px", fontWeight: 600 }}
            >
              {privateSpaces.length > 0 && (
                <optgroup label={studioCopy.switcherPersonalGroup}>
                  {privateSpaces.map((ws) => (
                    <option key={ws.workspaceId} value={ws.workspaceId}>
                      {`${getOrciaIconGlyph("lock")} ${ws.name}`}
                    </option>
                  ))}
                </optgroup>
              )}
              {teamSpaces.length > 0 && (
                <optgroup label={studioCopy.switcherTeamGroup}>
                  {teamSpaces.map((ws) => (
                    <option key={ws.workspaceId} value={ws.workspaceId}>
                      {`${getOrciaIconGlyph("team")} ${ws.name}`}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          )}
          <button
            type="button"
            data-testid="toggle-create-workspace-form-btn"
            aria-expanded={isCreateFormExpanded}
            onClick={onToggleCreateForm}
            className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm"
          >
            {studioCopy.newSpaceBtn}
          </button>
          <button
            type="button"
            data-testid="spaces-open-glossary-link"
            onClick={onNavigateToGlossary}
            className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
          >
            {panelCopy.glossaryLinkBtn}
          </button>
        </div>
      </div>

      {activeWorkspace && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "8px",
            borderTop: "1px solid var(--color-border-subtle)",
            paddingTop: "8px",
          }}
        >
          <select
            data-testid={`workspace-card-phase-select-${activeWorkspace.workspaceId}`}
            aria-label={cardCopy.phaseSelectAriaLabel}
            value={activeWorkspace.lifecyclePhase}
            onChange={(e) => handlePhaseChange(e.target.value as ProductLifecyclePhaseType)}
            style={{ ...selectStyle, fontSize: "11px", padding: "4px 8px" }}
          >
            <option value="BUILD">{cardCopy.phaseBuildOption}</option>
            <option value="RUN">{cardCopy.phaseRunOption}</option>
            <option value="MIGRATION">{cardCopy.phaseMigrationOption}</option>
          </select>

          <select
            data-testid={`workspace-card-visibility-select-${activeWorkspace.workspaceId}`}
            aria-label={cardCopy.visibilitySelectAriaLabel}
            value={activeWorkspace.visibilityMode}
            onChange={(e) => handleVisibilityChange(e.target.value as WorkspaceVisibilityMode)}
            style={{ ...selectStyle, fontSize: "11px", padding: "4px 8px" }}
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

          {activeWorkspace.visibilityMode === "PRIVATE_USER" && (
            <button
              type="button"
              data-testid={`share-private-workspace-btn-${activeWorkspace.workspaceId}`}
              onClick={() => handleVisibilityChange("STANDARD", cardCopy.shareSuccessTemplate)}
              className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
            >
              <OrciaIcon name="team" /> {cardCopy.shareWithTeamBtn}
            </button>
          )}
        </div>
      )}
    </header>
  );
}
