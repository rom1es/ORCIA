import {
  OrciaIcon,
  OrciaPageHeader,
  type ControlCenterWorkspaceGovItem,
} from "@orcia/ui";
import React from "react";
import { resolveGlobalScopeLabel } from "../../components/platformSetupWorkspaces";
import { resolveDictionaryForFlag, resolveLocaleForFlag } from "../../i18n";
import { resolveWorkspaceVisibilityMeta } from "./workspaceDisplayHelpers";

export interface WorkspaceCompactHeaderProps {
  readonly isFr: boolean;
  readonly activeWorkspace: ControlCenterWorkspaceGovItem | null;
  readonly isAutosaved: boolean;
  readonly isCreateFormExpanded: boolean;
  readonly alertSlot?: React.ReactNode;
  readonly onToggleCreateForm: () => void;
  readonly onNavigateToGlossary: () => void;
}

export function WorkspaceCompactHeader({
  isFr,
  activeWorkspace,
  isAutosaved,
  isCreateFormExpanded,
  alertSlot,
  onToggleCreateForm,
  onNavigateToGlossary,
}: WorkspaceCompactHeaderProps): React.ReactElement {
  const resolvedLocale = resolveLocaleForFlag(isFr);
  const dict = resolveDictionaryForFlag(isFr, resolvedLocale);
  const studioCopy = dict.featureWorkspaces.studioCards;
  const cardCopy = dict.featureWorkspaces.summaryCard;
  const panelCopy = dict.featureWorkspaces.panel;

  const visibilityMeta = activeWorkspace
    ? resolveWorkspaceVisibilityMeta(activeWorkspace.visibilityMode, isFr)
    : null;

  const contextBadge = activeWorkspace ? (
    <>
      {visibilityMeta ? (
        <span
          data-testid={`workspace-visibility-badge-${activeWorkspace.workspaceId}`}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            fontSize: "11px",
            fontWeight: 600,
            padding: "2px 8px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-bg-elevated)",
            border: "1px solid var(--color-border-subtle)",
          }}
        >
          <OrciaIcon name={visibilityMeta.iconName} size={12} />
          <span>{visibilityMeta.shortLabel}</span>
        </span>
      ) : null}
      {isAutosaved ? (
        <span
          data-testid={`workspace-autosaved-badge-${activeWorkspace.workspaceId}`}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            fontSize: "11px",
            fontWeight: 700,
            padding: "2px 8px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-action-primary-subtle)",
            color: "var(--color-status-success)",
          }}
        >
          <OrciaIcon name="check" size={12} />
          <span>{cardCopy.savedBadge}</span>
        </span>
      ) : null}
    </>
  ) : undefined;

  return (
    <OrciaPageHeader
      testId="workspaces-compact-header"
      titleTestId="workspaces-active-title"
      icon="spaces"
      title={activeWorkspace ? activeWorkspace.name : studioCopy.emptyHeaderTitle}
      subtitle={
        activeWorkspace
          ? `${cardCopy.billingTeamLabel} ${activeWorkspace.ownerOrgUnitName ?? resolveGlobalScopeLabel(isFr)}`
          : undefined
      }
      contextBadge={contextBadge}
      secondaryActions={
        <button
          type="button"
          data-testid="spaces-open-glossary-link"
          onClick={onNavigateToGlossary}
          className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
        >
          {panelCopy.glossaryLinkBtn}
        </button>
      }
      primaryAction={
        <button
          type="button"
          data-testid="toggle-create-workspace-form-btn"
          aria-expanded={isCreateFormExpanded}
          onClick={onToggleCreateForm}
          className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm"
        >
          {studioCopy.newSpaceBtn}
        </button>
      }
      alertSlot={alertSlot}
    />
  );
}
