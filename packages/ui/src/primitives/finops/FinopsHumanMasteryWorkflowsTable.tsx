import React from "react";
import { OrciaDataCard } from "../OrciaDataCard";
import type { HumanMasteryLabels, HumanMasteryWorkflowRow } from "./FinopsHumanMasteryTab";

export function FinopsHumanMasteryWorkflowsTable({
  workflows,
  labels,
}: {
  readonly workflows: readonly HumanMasteryWorkflowRow[];
  readonly labels: HumanMasteryLabels["workflowsTable"];
}): React.ReactElement | null {
  if (workflows.length === 0) {
    return null;
  }
  return (
    <OrciaDataCard testId="human-mastery-workflows-section" title={labels.title}>
      <div className="orcia-ds-table-wrapper" style={{ overflowX: "auto" }}>
        <table
          data-testid="human-mastery-workflows-table"
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "12px",
            textAlign: "left",
          }}
        >
          <thead>
            <tr
              style={{
                borderBottom: "1px solid var(--color-border-subtle)",
                color: "var(--color-text-muted)",
              }}
            >
              <th style={{ padding: "8px 12px" }}>{labels.workflowCol}</th>
              <th style={{ padding: "8px 12px" }}>{labels.criticalityCol}</th>
              <th style={{ padding: "8px 12px" }}>{labels.reviewsCol}</th>
              <th style={{ padding: "8px 12px" }}>{labels.quickPassCol}</th>
              <th style={{ padding: "8px 12px" }}>{labels.medianDurationCol}</th>
              <th style={{ padding: "8px 12px" }}>{labels.deviationsCol}</th>
              <th style={{ padding: "8px 12px" }}>{labels.statusCol}</th>
            </tr>
          </thead>
          <tbody>
            {workflows.map((wf) => (
              <tr
                key={wf.workflowId}
                data-testid={`human-mastery-row-${wf.workflowId}`}
                style={{ borderBottom: "1px solid var(--color-border-subtle)" }}
              >
                <td style={{ padding: "8px 12px", fontWeight: 600 }}>{wf.workflowTitle}</td>
                <td style={{ padding: "8px 12px" }}>
                  {labels.criticalityLabels?.[wf.criticality] ?? wf.criticality}
                </td>
                <td style={{ padding: "8px 12px" }}>
                  {wf.humanPassesCount} / {wf.humanGatesCount}
                </td>
                <td style={{ padding: "8px 12px" }}>{Math.round(wf.quickPassRate * 100)} %</td>
                <td style={{ padding: "8px 12px" }}>
                  {Math.round(wf.medianReviewDurationMs / 1000)} s
                </td>
                <td style={{ padding: "8px 12px" }}>{wf.uncoveredDriftCount}</td>
                <td style={{ padding: "8px 12px" }}>
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 600,
                      padding: "2px 6px",
                      borderRadius: "4px",
                      color: wf.hasAlert
                        ? "var(--color-arbitration-amber)"
                        : "var(--color-gate-emerald)",
                      background: "var(--color-surface-muted)",
                    }}
                  >
                    {wf.hasAlert ? labels.statusAlert : labels.statusNormal}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </OrciaDataCard>
  );
}
