import React from "react";
import { OrciaDialog } from "./RadixDesignSystemPrimitives";

export interface ActivityProvenanceModalLabels {
  readonly provenanceTitlePrefix: string;
  readonly alignmentStatusLabel: string;
  readonly conformingBadge: string;
  readonly divergenceBadge: string;
  readonly eventsCountLabel: string;
  readonly totalTokensLabel: string;
  readonly consolidatedCostLabel: string;
  readonly closeModalAriaLabel: string;
}

export interface ActivityProvenanceSummaryView {
  readonly run_id: string;
  readonly total_events: number;
  readonly total_input_tokens: number;
  readonly total_output_tokens: number;
  readonly total_cost_usd: number;
  readonly is_run_lock_aligned: boolean;
}

export interface ActivityProvenanceModalProps {
  readonly summary: ActivityProvenanceSummaryView | null;
  readonly labels: ActivityProvenanceModalLabels;
  readonly onClose: () => void;
}

export function ActivityProvenanceModal({
  summary,
  labels,
  onClose,
}: ActivityProvenanceModalProps): React.ReactElement | null {
  if (!summary) {
    return null;
  }

  return (
    <OrciaDialog
      open={Boolean(summary)}
      onOpenChange={(isOpen) => {
        if (!isOpen) {
          onClose();
        }
      }}
      title={`${labels.provenanceTitlePrefix} ${summary.run_id}`}
      testId="activity-provenance-modal"
      closeLabel={labels.closeModalAriaLabel}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "10px",
          fontSize: "12px",
          paddingTop: "6px",
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
          <strong>{labels.consolidatedCostLabel}</strong>{" "}
          {new Intl.NumberFormat("fr-FR", {
            style: "currency",
            currency: "EUR",
            minimumFractionDigits: 2,
          }).format(Number(summary.total_cost_usd) || 0)}
        </div>
      </div>
    </OrciaDialog>
  );
}
