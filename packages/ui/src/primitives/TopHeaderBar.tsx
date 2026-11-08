import React from "react";
import { OrciaIcon } from "../components/icons";

export interface TopHeaderBarLabels {
  readonly workspacePackSelectorLabel: string;
  readonly sprintSelectorLabel: string;
  readonly dbosPg18HealthLabel: string;
  readonly outboxHealthLabel: string;
}

export interface TopHeaderBarProps {
  readonly activeWorkspaceName: string;
  readonly activePackKey: string;
  readonly activeSprintName: string;
  readonly dbosPg18Healthy?: boolean;
  readonly outboxDlqCount?: number;
  readonly labels: TopHeaderBarLabels;
}

export function TopHeaderBar({
  activeWorkspaceName,
  activePackKey,
  activeSprintName,
  dbosPg18Healthy = true,
  outboxDlqCount = 0,
  labels,
}: TopHeaderBarProps) {
  return (
    <header
      data-testid="top-header-bar"
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexWrap: "wrap",
        gap: "10px",
        padding: "10px 14px",
        borderRadius: "10px",
        border: "1px solid var(--orcia-border-subtle)",
        backgroundColor: "var(--orcia-surface-elevated)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
        <span
          data-testid="header-workspace-pack-pill"
          style={{
            padding: "4px 10px",
            borderRadius: "9999px",
            fontSize: "0.75rem",
            fontWeight: 600,
            border: "1px solid var(--orcia-border-subtle)",
            backgroundColor: "var(--orcia-surface-secondary)",
          }}
        >
          <OrciaIcon name="workspaceFolder" /> {labels.workspacePackSelectorLabel}: {activeWorkspaceName} (
          <code style={{ fontFamily: "var(--orcia-font-mono)" }}>{activePackKey}</code>)
        </span>

        <span
          data-testid="header-sprint-selector-pill"
          style={{
            padding: "4px 10px",
            borderRadius: "9999px",
            fontSize: "0.75rem",
            fontWeight: 600,
            border: "1px solid var(--orcia-border-subtle)",
            backgroundColor: "var(--orcia-surface-primary)",
          }}
        >
          <OrciaIcon name="target" /> {labels.sprintSelectorLabel}: {activeSprintName}
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <span
          data-testid="header-health-dbos-pg18"
          style={{
            padding: "3px 8px",
            borderRadius: "9999px",
            fontSize: "0.75rem",
            fontFamily: "var(--orcia-font-mono)",
            border: "1px solid var(--orcia-border-subtle)",
            backgroundColor: "var(--orcia-surface-secondary)",
          }}
        >
          <OrciaIcon name={dbosPg18Healthy ? "statusHealthy" : "statusError"} /> {labels.dbosPg18HealthLabel}
        </span>

        <span
          data-testid="header-health-outbox"
          style={{
            padding: "3px 8px",
            borderRadius: "9999px",
            fontSize: "0.75rem",
            fontFamily: "var(--orcia-font-mono)",
            border: "1px solid var(--orcia-border-subtle)",
            backgroundColor: "var(--orcia-surface-secondary)",
          }}
        >
          <OrciaIcon name={outboxDlqCount === 0 ? "statusHealthy" : "statusWarning"} /> {labels.outboxHealthLabel} (DLQ={outboxDlqCount})
        </span>
      </div>
    </header>
  );
}
