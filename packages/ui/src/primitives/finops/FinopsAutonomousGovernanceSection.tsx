import React from "react";
import { ContextualInfoTriggerButton } from "../../components/ContextualInfoTriggerButton";
import { OrciaIcon } from "../../components/icons";
import { CognitiveMetricCard } from "./CognitiveMetricCard";

export interface FinopsPostHocSampleRow {
  readonly id: string;
  readonly runId: string;
  readonly workflowTitle: string;
  readonly triggerLabel: string;
  readonly reviewStatus: "PENDING_SAMPLE" | "VALIDATED" | "INVALIDATED_ROLLED_BACK";
  readonly runStatus: string;
  readonly sampledAt: string;
}

export interface FinopsAutonomousGovernanceData {
  readonly totalAutonomousRuns: number;
  readonly escalatedRunsCount: number;
  readonly killedRunsCount: number;
  readonly sampledRunsCount: number;
  readonly pendingSamplesCount: number;
  readonly invalidatedSamplesCount: number;
  readonly autonomousEscalationRate: number;
  readonly postHocInvalidationRate: number;
  readonly invalidationAlert: boolean;
  readonly avgAutonomousCostUsd: number;
  readonly avgTtmGainMinutes: number;
  readonly pendingSamples: readonly FinopsPostHocSampleRow[];
}

export interface FinopsAutonomousGovernanceLabels {
  readonly sectionTitle: string;
  readonly sectionSubtitle: string;
  readonly infoButtonAriaLabel: string;
  readonly escalationGauge: {
    readonly title: string;
    readonly targetLabel: string;
    readonly statusHealthy: string;
    readonly statusAlert: string;
    readonly subtitle: string;
  };
  readonly invalidationGauge: {
    readonly title: string;
    readonly thresholdLabel: string;
    readonly statusHealthy: string;
    readonly statusAlert: string;
    readonly subtitle: string;
  };
  readonly efficiencyGauge: {
    readonly title: string;
    readonly targetLabel: string;
    readonly statusHealthy: string;
    readonly costPrefix: string;
    readonly gainPrefix: string;
    readonly minutesUnit: string;
  };
  readonly invalidationAlertBanner: string;
  readonly samplesTitle: string;
  readonly samplesEmptyText: string;
  readonly validateSampleButton: string;
  readonly invalidateAndRestoreButton: string;
  readonly sampleStatusLabels: Readonly<Record<string, string>>;
}

export interface FinopsAutonomousGovernanceSectionProps {
  readonly data: FinopsAutonomousGovernanceData;
  readonly labels: FinopsAutonomousGovernanceLabels;
  readonly onReviewSample?: (
    runId: string,
    decision: "VALIDATED" | "INVALIDATED_ROLLED_BACK",
  ) => void;
  readonly onOpenHelpSection?: (sectionId: string) => void;
}

/**
 * Autonomous Governance & Post-Hoc Quality Sampling section mounted INSIDE
 * the existing "Maîtrise humaine et qualité" tab of `/finops` (`Story 7.4`, zero extra tab).
 * Hidden cleanly whenever `totalAutonomousRuns === 0`.
 */
export function FinopsAutonomousGovernanceSection({
  data,
  labels,
  onReviewSample,
  onOpenHelpSection,
}: FinopsAutonomousGovernanceSectionProps): React.ReactElement | null {
  if (data.totalAutonomousRuns === 0) {
    return null;
  }

  const escPct = Math.round(data.autonomousEscalationRate * 1000) / 10;
  const invPct = Math.round(data.postHocInvalidationRate * 1000) / 10;
  const costFormatted = `${data.avgAutonomousCostUsd.toFixed(2)} $`;
  const ttmFormatted = `${Math.round(data.avgTtmGainMinutes)} ${labels.efficiencyGauge.minutesUnit}`;

  return (
    <div
      data-testid="finops-autonomous-governance-section"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "16px",
        paddingTop: "12px",
        borderTop: "1px solid var(--color-border-subtle)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <h3
              data-testid="finops-autonomous-section-title"
              style={{ fontSize: "15px", fontWeight: 700, margin: 0, color: "var(--color-text-primary)" }}
            >
              {labels.sectionTitle}
            </h3>
            <ContextualInfoTriggerButton
              sectionId="autonomous-supervision"
              label={labels.infoButtonAriaLabel}
              onOpenHelpSection={onOpenHelpSection}
            />
          </div>
          <p style={{ fontSize: "12.5px", color: "var(--color-text-muted)", margin: "4px 0 0 0" }}>
            {labels.sectionSubtitle}
          </p>
        </div>
      </div>

      {data.invalidationAlert && (
        <div
          role="alert"
          data-testid="finops-autonomous-invalidation-alert"
          className="rounded-lg border px-3 py-2.5 text-xs font-medium"
          style={{
            backgroundColor: "var(--color-stale-bg)",
            borderColor: "var(--color-stale-crimson)",
            color: "var(--color-stale-crimson)",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <OrciaIcon name="warning" size={14} />
          <span>{labels.invalidationAlertBanner}</span>
        </div>
      )}

      <div
        data-testid="finops-autonomous-gauges-grid"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "14px",
        }}
      >
        <CognitiveMetricCard
          title={labels.escalationGauge.title}
          valueFormatted={`${escPct} %`}
          percentage={Math.min(100, escPct)}
          targetLabel={labels.escalationGauge.targetLabel}
          statusLabel={
            escPct >= 20 ? labels.escalationGauge.statusAlert : labels.escalationGauge.statusHealthy
          }
          tone={escPct >= 20 ? "amber" : "emerald"}
          testId="finops-autonomous-gauge-escalation"
          subtitle={labels.escalationGauge.subtitle}
        />
        <CognitiveMetricCard
          title={labels.invalidationGauge.title}
          valueFormatted={`${invPct} %`}
          percentage={Math.min(100, invPct * 10)}
          targetLabel={labels.invalidationGauge.thresholdLabel}
          statusLabel={
            data.invalidationAlert
              ? labels.invalidationGauge.statusAlert
              : labels.invalidationGauge.statusHealthy
          }
          tone={data.invalidationAlert ? "crimson" : "emerald"}
          testId="finops-autonomous-gauge-invalidation"
          subtitle={labels.invalidationGauge.subtitle}
        />
        <CognitiveMetricCard
          title={labels.efficiencyGauge.title}
          valueFormatted={`${costFormatted} · -${ttmFormatted}`}
          percentage={100}
          targetLabel={labels.efficiencyGauge.targetLabel}
          statusLabel={labels.efficiencyGauge.statusHealthy}
          tone="emerald"
          testId="finops-autonomous-gauge-efficiency"
          subtitle={`${labels.efficiencyGauge.costPrefix} ${costFormatted} · ${labels.efficiencyGauge.gainPrefix} ${ttmFormatted}`}
        />
      </div>

      <div data-testid="finops-autonomous-samples-list" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        <h4 style={{ fontSize: "13.5px", fontWeight: 600, margin: 0, color: "var(--color-text-primary)" }}>
          {labels.samplesTitle} ({data.pendingSamples.length})
        </h4>

        {data.pendingSamples.length === 0 ? (
          <div
            data-testid="finops-autonomous-samples-empty"
            style={{
              padding: "12px 16px",
              borderRadius: "8px",
              border: "1px solid var(--color-border-subtle)",
              backgroundColor: "var(--color-surface-card)",
              fontSize: "12.5px",
              color: "var(--color-text-muted)",
            }}
          >
            {labels.samplesEmptyText}
          </div>
        ) : (
          data.pendingSamples.map((sample) => (
            <div
              key={sample.id}
              data-testid={`finops-post-hoc-sample-${sample.runId}`}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "10px",
                padding: "12px 16px",
                borderRadius: "8px",
                border: "1px solid var(--color-autonomous-badge-border)",
                backgroundColor: "var(--color-autonomous-badge-bg)",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  <strong style={{ fontSize: "13px", color: "var(--color-text-primary)" }}>
                    {sample.workflowTitle}
                  </strong>
                  <span
                    className="rounded px-2 py-0.5 text-[11px] font-semibold"
                    style={{
                      backgroundColor: "var(--color-surface-card)",
                      color:
                        sample.reviewStatus === "INVALIDATED_ROLLED_BACK"
                          ? "var(--color-stale-crimson)"
                          : sample.reviewStatus === "VALIDATED"
                            ? "var(--color-gate-emerald)"
                            : "var(--color-autonomous-badge-fg)",
                    }}
                  >
                    {labels.sampleStatusLabels[sample.reviewStatus] ?? sample.reviewStatus}
                  </span>
                </div>
                <span style={{ fontSize: "11.5px", color: "var(--color-text-secondary)" }}>
                  {sample.triggerLabel}
                </span>
              </div>

              {sample.reviewStatus === "PENDING_SAMPLE" && onReviewSample && (
                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    data-testid={`finops-sample-validate-btn-${sample.runId}`}
                    className="orcia-ds-btn orcia-ds-btn-primary text-xs px-3 py-1"
                    onClick={() => onReviewSample(sample.runId, "VALIDATED")}
                  >
                    {labels.validateSampleButton}
                  </button>
                  <button
                    type="button"
                    data-testid={`finops-sample-restore-btn-${sample.runId}`}
                    className="orcia-ds-btn orcia-ds-btn-danger text-xs px-3 py-1"
                    onClick={() => onReviewSample(sample.runId, "INVALIDATED_ROLLED_BACK")}
                  >
                    {labels.invalidateAndRestoreButton}
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
