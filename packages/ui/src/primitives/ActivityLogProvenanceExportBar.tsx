import React from "react";
import { OrciaIcon } from "../components/icons";
import type { ActivityLogProvenanceLabels } from "./activityLogHelpers";

export interface ActivityLogProvenanceExportBarProps {
  readonly selectedRunId?: string;
  readonly onInspectProvenance?: (runId: string) => void;
  readonly onExportProvenance?: (runId: string, format: "json" | "md") => void;
  readonly isExporting?: boolean;
  readonly labels?: ActivityLogProvenanceLabels;
}

export function ActivityLogProvenanceExportBar({
  selectedRunId,
  onInspectProvenance,
  onExportProvenance,
  isExporting = false,
  labels,
}: ActivityLogProvenanceExportBarProps): React.ReactElement | null {
  if (!selectedRunId || !labels) {
    return null;
  }

  return (
    <div
      data-testid="activity-provenance-export-bar"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "10px",
        padding: "8px 12px",
        borderRadius: "var(--radius-sm)",
        border: "1px solid var(--color-border)",
        backgroundColor: "var(--color-bg-elevated)",
        fontSize: "12px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <OrciaIcon name="lock" />
        <span>
          {labels.selectedRunPrefix}{" "}
          <code style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>{selectedRunId}</code>
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        {onInspectProvenance && (
          <button
            type="button"
            data-testid="activity-inspect-provenance-btn"
            onClick={() => onInspectProvenance(selectedRunId)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "4px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-surface-card)",
              color: "var(--color-foreground)",
              fontSize: "12px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            <OrciaIcon name="search" />
            {labels.inspectProvenanceAction}
          </button>
        )}

        {onExportProvenance && (
          <>
            <button
              type="button"
              data-testid="activity-export-json-btn"
              disabled={isExporting}
              onClick={() => onExportProvenance(selectedRunId, "json")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "4px 10px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                backgroundColor: "var(--color-surface-card)",
                color: "var(--color-primary-cobalt)",
                fontSize: "12px",
                fontWeight: 600,
                cursor: isExporting ? "wait" : "pointer",
              }}
            >
              <OrciaIcon name="arrowDown" />
              {labels.exportJsonAction}
            </button>

            <button
              type="button"
              data-testid="activity-export-md-btn"
              disabled={isExporting}
              onClick={() => onExportProvenance(selectedRunId, "md")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "4px 10px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                backgroundColor: "var(--color-surface-card)",
                color: "var(--color-foreground)",
                fontSize: "12px",
                fontWeight: 500,
                cursor: isExporting ? "wait" : "pointer",
              }}
            >
              <OrciaIcon name="document" />
              {labels.exportMdAction}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
