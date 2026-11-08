import React, { useState } from "react";
import { OrciaIcon } from "../components/icons";

export interface SprintContextWidgetLabels {
  readonly widgetTitle: string;
  readonly sprintGoalLabel: string;
  readonly velocityLabel: string;
  readonly openRisksLabel: string;
  readonly auditRisksCta: string;
  readonly auditCompletedMessage: string;
}

export interface SprintContextWidgetProps {
  readonly sprintName: string;
  readonly sprintGoal: string;
  readonly completedStories: number;
  readonly totalStories: number;
  readonly openRisksCount: number;
  readonly labels: SprintContextWidgetLabels;
  readonly onAuditSprintRisks?: (sprintName: string) => void;
}

export function SprintContextWidget({
  sprintName,
  sprintGoal,
  completedStories,
  totalStories,
  openRisksCount,
  labels,
  onAuditSprintRisks,
}: SprintContextWidgetProps) {
  const [audited, setAudited] = useState(false);

  return (
    <article
      data-testid="sprint-context-widget"
      style={{
        padding: "16px",
        borderRadius: "10px",
        border: "1px solid var(--orcia-border-subtle)",
        backgroundColor: "var(--orcia-surface-elevated)",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <strong style={{ fontSize: "0.9375rem" }}>
          <OrciaIcon name="target" /> {labels.widgetTitle} — {sprintName}
        </strong>
        <span
          style={{
            fontSize: "0.75rem",
            fontFamily: "var(--orcia-font-mono)",
            color: "var(--orcia-text-secondary)",
          }}
        >
          {labels.velocityLabel}: {completedStories}/{totalStories} • {labels.openRisksLabel}:{" "}
          {openRisksCount}
        </span>
      </div>

      <p style={{ margin: 0, fontSize: "0.8125rem", color: "var(--orcia-text-secondary)" }}>
        <strong>{labels.sprintGoalLabel} :</strong> {sprintGoal}
      </p>

      <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
        <button
          type="button"
          data-testid="sprint-audit-risks-cta"
          onClick={() => {
            setAudited(true);
            onAuditSprintRisks?.(sprintName);
          }}
          style={{
            padding: "6px 12px",
            borderRadius: "8px",
            fontSize: "0.8125rem",
            fontWeight: 600,
            cursor: "pointer",
            border: "1px solid var(--orcia-action-primary)",
            backgroundColor: "var(--orcia-surface-secondary)",
            color: "var(--orcia-text-primary)",
          }}
        >
          <OrciaIcon name="sparkles" /> {labels.auditRisksCta}
        </button>

        {audited ? (
          <span
            role="status"
            aria-live="polite"
            data-testid="sprint-audit-status"
            style={{ fontSize: "0.75rem", fontWeight: 600 }}
          >
            <OrciaIcon name="checkFilled" /> {labels.auditCompletedMessage}
          </span>
        ) : null}
      </div>
    </article>
  );
}
