import React from "react";
import type { ActivityProvenanceModalLabels } from "../i18n/locales/activity_labels";
import type { AuditProvenanceSummaryResponse } from "./activityApiBridge";

export interface ActivityProvenanceModalProps {
  readonly summary: AuditProvenanceSummaryResponse;
  readonly labels: ActivityProvenanceModalLabels;
  readonly onClose: () => void;
}

export function ActivityProvenanceModal({
  summary,
  labels,
  onClose,
}: ActivityProvenanceModalProps): React.ReactElement {
  return (
    <div
      data-testid="activity-provenance-modal"
      style={{
        marginBottom: "16px",
        padding: "14px 16px",
        borderRadius: "var(--radius-sm)",
        border: "1px solid var(--color-border)",
        backgroundColor: "var(--color-bg-elevated)",
        display: "flex",
        flexDirection: "column",
        gap: "8px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0, fontSize: "14px" }}>
          {labels.provenanceTitlePrefix} <code>{summary.run_id}</code>
        </h3>
        <button
          type="button"
          onClick={onClose}
          aria-label={labels.closeModalAriaLabel}
          style={{
            border: "none",
            background: "transparent",
            cursor: "pointer",
            fontSize: "16px",
            color: "var(--color-muted-foreground)",
          }}
        >
          ✕
        </button>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "10px",
          fontSize: "12px",
        }}
      >
        <div>
          <strong>{labels.alignmentStatusLabel}</strong>{" "}
          {summary.is_run_lock_aligned ? labels.conformingBadge : labels.divergenceBadge}
        </div>
        <div>
          <strong>{labels.eventsCountLabel}</strong> {summary.total_events}
        </div>
        <div>
          <strong>{labels.totalTokensLabel}</strong>{" "}
          {summary.total_input_tokens + summary.total_output_tokens}
        </div>
        <div>
          <strong>{labels.consolidatedCostLabel}</strong> ${summary.total_cost_usd} USD
        </div>
      </div>
    </div>
  );
}
