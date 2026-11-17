import React from "react";
import { ContextualInfoTriggerButton } from "../../components/ContextualInfoTriggerButton";
import { CognitiveMetricCard } from "./CognitiveMetricCard";

export interface HumanMasteryWorkflowRow {
  readonly workflowId: string;
  readonly workflowTitle: string;
  readonly criticality: string;
  readonly humanGatesCount: number;
  readonly humanPassesCount: number;
  readonly quickPassesCount: number;
  readonly quickPassRate: number;
  readonly medianReviewDurationMs: number;
  readonly uncoveredDriftCount: number;
  readonly hasAlert: boolean;
}

export interface HumanMasteryRecommendationItem {
  readonly id: string;
  readonly workflowId: string;
  readonly workflowTitle: string;
  readonly recommendationType: string;
  readonly title: string;
  readonly description: string;
  readonly actionLabel: string;
  readonly suggestedPolicy: string;
  readonly status: "PROPOSED" | "APPLIED" | "DISMISSED";
  readonly appliedAt?: string | null;
}

export interface HumanMasteryLabels {
  readonly tabTitle: string;
  readonly tabSubtitle: string;
  readonly infoButtonAriaLabel: string;
  readonly framingGauge: {
    readonly title: string;
    readonly targetLabel: string;
    readonly statusHealthy: string;
    readonly statusAlert: string;
    readonly subtitle: string;
  };
  readonly quickPassGauge: {
    readonly title: string;
    readonly thresholdLabel: string;
    readonly statusHealthy: string;
    readonly statusAlert: string;
    readonly subtitle: string;
  };
  readonly architectureGauge: {
    readonly title: string;
    readonly targetLabel: string;
    readonly statusHealthy: string;
    readonly statusAlert: string;
    readonly subtitle: string;
  };
  readonly recommendationsSectionTitle: string;
  readonly recommendationsEmptyText: string;
  readonly workflowsTable: {
    readonly title: string;
    readonly workflowCol: string;
    readonly criticalityCol: string;
    readonly reviewsCol: string;
    readonly quickPassCol: string;
    readonly medianDurationCol: string;
    readonly deviationsCol: string;
    readonly statusCol: string;
    readonly statusNormal: string;
    readonly statusAlert: string;
    readonly criticalityLabels?: Readonly<Record<string, string>>;
  };
  readonly appliedBadge: string;
}

export interface FinopsHumanMasteryTabProps {
  readonly activeFramingRatio: number;
  readonly activeFramingAlert: boolean;
  readonly quickPassRate: number;
  readonly quickPassAlert: boolean;
  readonly architectureDeviationIndex: number;
  readonly architectureDeviationAlert: boolean;
  readonly uncoveredDeviationsCount?: number;
  readonly workflows: readonly HumanMasteryWorkflowRow[];
  readonly recommendations: readonly HumanMasteryRecommendationItem[];
  readonly labels: HumanMasteryLabels;
  readonly onApplyRecommendation?: (recommendationId: string) => void;
  readonly onOpenHelpSection?: (sectionId: string) => void;
}

export function FinopsHumanMasteryTab({
  activeFramingRatio,
  activeFramingAlert,
  quickPassRate,
  quickPassAlert,
  architectureDeviationIndex,
  architectureDeviationAlert,
  uncoveredDeviationsCount = 0,
  workflows,
  recommendations,
  labels,
  onApplyRecommendation,
  onOpenHelpSection,
}: FinopsHumanMasteryTabProps): React.ReactElement {
  const framingPct = Math.round(activeFramingRatio * 100);
  const quickPassPct = Math.round(quickPassRate * 100);
  const archDeviationPct = Math.round(architectureDeviationIndex * 100);

  return (
    <div
      className="finops-human-mastery-tab"
      data-testid="finops-human-mastery-tab"
      style={{ display: "flex", flexDirection: "column", gap: "20px" }}
    >
      {/* 1. Header with title and help button */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <h2
              data-testid="human-mastery-title"
              style={{ fontSize: "16px", fontWeight: 700, margin: 0, color: "var(--color-text-primary)" }}
            >
              {labels.tabTitle}
            </h2>
            <ContextualInfoTriggerButton
              sectionId="finops-human-mastery"
              label={labels.infoButtonAriaLabel}
              onOpenHelpSection={onOpenHelpSection}
            />
          </div>
          <p style={{ fontSize: "13px", color: "var(--color-text-muted)", margin: "4px 0 0 0" }}>
            {labels.tabSubtitle}
          </p>
        </div>
      </div>

      {/* 2. Three Counter-Metric Gauges */}
      <div
        className="human-mastery-gauges-grid"
        data-testid="human-mastery-gauges-grid"
        style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}
      >
        <CognitiveMetricCard
          title={labels.framingGauge.title}
          valueFormatted={`${framingPct} %`}
          percentage={framingPct}
          targetLabel={labels.framingGauge.targetLabel}
          statusLabel={activeFramingAlert ? labels.framingGauge.statusAlert : labels.framingGauge.statusHealthy}
          tone={activeFramingAlert ? "amber" : "emerald"}
          testId="human-mastery-gauge-framing"
          subtitle={labels.framingGauge.subtitle}
        />
        <CognitiveMetricCard
          title={labels.quickPassGauge.title}
          valueFormatted={`${quickPassPct} %`}
          percentage={Math.min(100, quickPassPct * 5)}
          targetLabel={labels.quickPassGauge.thresholdLabel}
          statusLabel={quickPassAlert ? labels.quickPassGauge.statusAlert : labels.quickPassGauge.statusHealthy}
          tone={quickPassAlert ? "crimson" : "emerald"}
          testId="human-mastery-gauge-quick-pass"
          subtitle={labels.quickPassGauge.subtitle}
        />
        <CognitiveMetricCard
          title={labels.architectureGauge.title}
          valueFormatted={uncoveredDeviationsCount > 0 ? `${uncoveredDeviationsCount}` : `${archDeviationPct} %`}
          percentage={uncoveredDeviationsCount > 0 ? 100 : 0}
          targetLabel={labels.architectureGauge.targetLabel}
          statusLabel={
            architectureDeviationAlert
              ? labels.architectureGauge.statusAlert
              : labels.architectureGauge.statusHealthy
          }
          tone={architectureDeviationAlert ? "crimson" : "emerald"}
          testId="human-mastery-gauge-architecture"
          subtitle={labels.architectureGauge.subtitle}
        />
      </div>

      {/* 3. Gate Policy Recommendations Section */}
      <div data-testid="human-mastery-recommendations-section" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        <h3 style={{ fontSize: "14px", fontWeight: 600, margin: 0, color: "var(--color-text-primary)" }}>
          {labels.recommendationsSectionTitle}
        </h3>

        {recommendations.length === 0 ? (
          <div
            data-testid="human-mastery-recommendations-empty"
            style={{
              padding: "16px 20px",
              background: "var(--color-surface-card)",
              border: "1px solid var(--color-border-subtle)",
              borderRadius: "8px",
              color: "var(--color-text-muted)",
              fontSize: "13px",
            }}
          >
            {labels.recommendationsEmptyText}
          </div>
        ) : (
          recommendations.map((rec) => (
            <div
              key={rec.id}
              data-testid={`human-mastery-rec-card-${rec.id}`}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "14px 18px",
                background: "var(--color-surface-card)",
                border: "1px solid var(--color-border-subtle)",
                borderRadius: "8px",
                flexWrap: "wrap",
                gap: "12px",
              }}
            >
              <div style={{ maxWidth: "620px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)" }}>
                    {rec.title}
                  </span>
                  <span
                    style={{
                      fontSize: "11px",
                      padding: "1px 6px",
                      borderRadius: "4px",
                      background: "var(--color-surface-muted)",
                      color: "var(--color-text-muted)",
                    }}
                  >
                    {rec.workflowTitle}
                  </span>
                </div>
                <p style={{ fontSize: "12px", color: "var(--color-text-muted)", margin: "4px 0 0 0" }}>
                  {rec.description}
                </p>
              </div>

              <div>
                {rec.status === "APPLIED" ? (
                  <span
                    data-testid={`human-mastery-rec-applied-${rec.id}`}
                    style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      color: "var(--color-gate-emerald)",
                      padding: "4px 10px",
                      borderRadius: "4px",
                      background: "var(--color-surface-muted)",
                    }}
                  >
                    {labels.appliedBadge}
                  </span>
                ) : (
                  <button
                    type="button"
                    data-testid={`human-mastery-apply-btn-${rec.id}`}
                    className="orcia-ds-btn orcia-ds-btn-primary"
                    style={{ fontSize: "12px", padding: "6px 14px" }}
                    onClick={() => onApplyRecommendation?.(rec.id)}
                  >
                    {rec.actionLabel}
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* 4. Workflow Cognitive Breakdown Table */}
      {workflows.length > 0 && (
        <div data-testid="human-mastery-workflows-section" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <h3 style={{ fontSize: "14px", fontWeight: 600, margin: 0, color: "var(--color-text-primary)" }}>
            {labels.workflowsTable.title}
          </h3>

          <div
            className="orcia-ds-table-wrapper"
            style={{
              overflowX: "auto",
              background: "var(--color-surface-card)",
              border: "1px solid var(--color-border-subtle)",
              borderRadius: "8px",
            }}
          >
            <table
              data-testid="human-mastery-workflows-table"
              style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px", textAlign: "left" }}
            >
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border-subtle)", color: "var(--color-text-muted)" }}>
                  <th style={{ padding: "8px 12px" }}>{labels.workflowsTable.workflowCol}</th>
                  <th style={{ padding: "8px 12px" }}>{labels.workflowsTable.criticalityCol}</th>
                  <th style={{ padding: "8px 12px" }}>{labels.workflowsTable.reviewsCol}</th>
                  <th style={{ padding: "8px 12px" }}>{labels.workflowsTable.quickPassCol}</th>
                  <th style={{ padding: "8px 12px" }}>{labels.workflowsTable.medianDurationCol}</th>
                  <th style={{ padding: "8px 12px" }}>{labels.workflowsTable.deviationsCol}</th>
                  <th style={{ padding: "8px 12px" }}>{labels.workflowsTable.statusCol}</th>
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
                      {labels.workflowsTable.criticalityLabels?.[wf.criticality] ?? wf.criticality}
                    </td>
                    <td style={{ padding: "8px 12px" }}>{wf.humanPassesCount} / {wf.humanGatesCount}</td>
                    <td style={{ padding: "8px 12px" }}>{Math.round(wf.quickPassRate * 100)} %</td>
                    <td style={{ padding: "8px 12px" }}>{Math.round(wf.medianReviewDurationMs / 1000)} s</td>
                    <td style={{ padding: "8px 12px" }}>{wf.uncoveredDriftCount}</td>
                    <td style={{ padding: "8px 12px" }}>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: 600,
                          padding: "2px 6px",
                          borderRadius: "4px",
                          color: wf.hasAlert ? "var(--color-arbitration-amber)" : "var(--color-gate-emerald)",
                          background: "var(--color-surface-muted)",
                        }}
                      >
                        {wf.hasAlert ? labels.workflowsTable.statusAlert : labels.workflowsTable.statusNormal}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
