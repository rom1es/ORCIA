import { OrciaButton, OrciaIcon } from "@orcia/ui";
import React from "react";
import type { AdminAndStudioDictionarySection } from "../../../i18n/locales/admin_and_studio_labels";

export interface OrgPedagogicalCalloutProps {
  readonly labels: AdminAndStudioDictionarySection["settingsHub"]["organizationTab"];
  readonly onOpenWorkspaces: () => void;
}

export function OrgPedagogicalCallout({
  labels,
  onOpenWorkspaces,
}: OrgPedagogicalCalloutProps): React.ReactElement {
  return (
    <div
      data-testid="organization-pedagogical-callout"
      style={{
        padding: "10px 14px",
        borderRadius: "var(--radius-sm)",
        border: "1px solid var(--color-border)",
        backgroundColor: "var(--color-surface-secondary)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexWrap: "wrap",
        gap: "10px",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12.5px" }}>
        <strong style={{ color: "var(--color-foreground)" }}>{labels.pedagogyTitle}</strong>
        <span style={{ color: "var(--color-muted-foreground)" }}>
          {`${labels.pedagogyBuSummary} · ${labels.pedagogyTeamSummary} · ${labels.pedagogyWorkspaceSummary}`}
        </span>
      </div>
      <OrciaButton
        variant="secondary"
        testId="organization-open-workspaces-btn"
        onClick={onOpenWorkspaces}
      >
        <OrciaIcon name="spaces" size={14} />
        <span>{labels.openWorkspacesCta}</span>
      </OrciaButton>
    </div>
  );
}
