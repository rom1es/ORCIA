import React from "react";
import { OrciaIcon } from "../components/icons";
import { StatusBadge } from "../primitives/StatusBadge";
import type {
  UiOntologyExplorerLabels,
  UiStaleAlertView,
  UiTripartiteEdgeView,
} from "./types";

export interface OntologyTripartiteAndStaleSectionProps {
  readonly ragQuery: string;
  readonly onRagQueryChange: (val: string) => void;
  readonly filteredEdges: readonly UiTripartiteEdgeView[];
  readonly staleAlerts: readonly UiStaleAlertView[];
  readonly labels: UiOntologyExplorerLabels;
  readonly onReplayAlert: (alert: UiStaleAlertView) => void;
}

export function OntologyTripartiteAndStaleSection({
  ragQuery,
  onRagQueryChange,
  filteredEdges,
  staleAlerts,
  labels,
  onReplayAlert,
}: OntologyTripartiteAndStaleSectionProps): React.ReactElement {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
        gap: "12px",
      }}
    >
      <div
        data-testid="tripartite-graph-section"
        style={{
          padding: "10px",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--color-border)",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        <strong>
          {labels.tripartiteTitle} · {labels.hybridRagTitle}
        </strong>
        <input
          type="search"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="hybrid-rag-search-input"
          value={ragQuery}
          onChange={(e) => onRagQueryChange(e.target.value)}
          placeholder={labels.hybridRagSearchPlaceholder}
          style={{
            padding: "6px 8px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-foreground)",
          }}
        />
        {filteredEdges.map((edge) => (
          <div
            key={edge.edgeKey}
            data-testid={`tripartite-edge-${edge.edgeKey}`}
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "var(--font-size-mono)",
              color: "var(--color-muted-foreground)",
            }}
          >
            {edge.sourceUri} —[{edge.relationType}]→ {edge.targetUri}
          </div>
        ))}
      </div>

      <div
        data-testid="stale-alerts-section"
        style={{
          padding: "10px",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--color-stale-crimson)",
          backgroundColor: "var(--color-stale-bg)",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: "8px" }}>
          <strong>{labels.staleAlertsTitle}</strong>
          <StatusBadge label={labels.docObsoleteBadgeLabel} tone="crimson" monospace />
        </div>
        {staleAlerts.map((alert) => (
          <div
            key={alert.alertKey}
            data-testid={`stale-alert-${alert.alertKey}`}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "8px",
              fontFamily: "var(--font-mono)",
              fontSize: "var(--font-size-mono)",
              color: "var(--color-stale-crimson)",
            }}
          >
            <span>
              {alert.diagnosticMarker} {alert.sourceUri} (Jira:{" "}
              {alert.justifyingJiraKey ?? "TTL"}, Runs: {alert.impactedRunIds.join(", ")})
            </span>
            <button
              type="button"
              data-testid={`stale-alert-replay-btn-${alert.alertKey}`}
              onClick={() => onReplayAlert(alert)}
              style={{
                backgroundColor: "var(--color-surface-card)",
                color: "var(--color-stale-crimson)",
                border: "1px solid var(--color-stale-crimson)",
                borderRadius: "var(--radius-sm)",
                padding: "2px 6px",
                fontSize: "10px",
                cursor: "pointer",
              }}
            >
              <OrciaIcon name="regenerate" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
