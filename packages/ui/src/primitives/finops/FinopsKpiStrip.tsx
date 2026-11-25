import React from "react";
import { StatusBadge } from "../StatusBadge";

export interface FinopsKpiStripLabels {
  consolidatedCostTitle: string;
  verifiedInternalSubtitle: string;
  reportedExternalSubtitle: string;
  tokensTitle: string;
  internalTokensSubtitle: string;
  remoteTokensSubtitle: string;
  externalCallsTitle: string;
  externalUnitsSubtitle: string;
  savingsTitle: string;
  activeBreakersBadge: string;
  pausedRunsBadge: string;
}

export interface FinopsKpiStripProps {
  readonly totalRuns: number;
  readonly totalCostEur: number;
  readonly verifiedInternalCostEur: number;
  readonly reportedExternalCostEur: number;
  readonly totalLlmTokens: number;
  readonly internalTokens: number;
  readonly remoteTokens: number;
  readonly totalExternalCalls: number;
  readonly externalUnitsBreakdown?: Record<string, number>;
  readonly cacheSavingsEur?: number;
  readonly activeCircuitBreakersCount?: number;
  readonly pausedRunsCount?: number;
  readonly suppressEmptyState?: boolean;
  readonly emptyStateText: string;
  readonly labels: FinopsKpiStripLabels;
}

function formatTokens(count: number): string {
  if (count >= 1_000_000) {
    return `${(count / 1_000_000).toFixed(2).replace(".", ",")} M`;
  }
  if (count >= 1_000) {
    return `${(count / 1_000).toFixed(1).replace(".", ",")} k`;
  }
  return `${count}`;
}

function formatCurrency(amount: number): string {
  const safeAmount = Number.isFinite(amount) ? amount : 0;
  const isMicro = Math.abs(safeAmount) > 0 && Math.abs(safeAmount) < 0.01;
  return `${safeAmount.toFixed(isMicro ? 3 : 2).replace(".", ",")} €`;
}

export function FinopsKpiStrip({
  totalRuns,
  totalCostEur,
  verifiedInternalCostEur,
  reportedExternalCostEur,
  totalLlmTokens,
  internalTokens,
  remoteTokens,
  totalExternalCalls,
  externalUnitsBreakdown,
  cacheSavingsEur = 0,
  activeCircuitBreakersCount = 0,
  pausedRunsCount = 0,
  suppressEmptyState = false,
  emptyStateText,
  labels,
}: FinopsKpiStripProps): React.ReactElement | null {
  const isEmpty =
    totalRuns === 0 &&
    totalCostEur === 0 &&
    totalExternalCalls === 0 &&
    activeCircuitBreakersCount === 0;
  const unitEntries = Object.entries(externalUnitsBreakdown ?? {}).filter(([, val]) => val > 0);

  if (isEmpty) {
    if (suppressEmptyState) {
      return null;
    }
    return (
      <div
        className="orcia-bento-card"
        data-testid="finops-empty-state"
        style={{
          padding: "24px",
          textAlign: "center",
          borderRadius: "8px",
          border: "1px dashed var(--color-border)",
          color: "var(--color-text-muted)",
        }}
      >
        <p style={{ margin: 0, fontSize: "14px", lineHeight: "1.6" }}>
          {emptyStateText}
        </p>
      </div>
    );
  }

  return (
    <div
      className="finops-kpi-grid grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
      data-testid="finops-kpi-strip"
    >
      {/* KPI 1 : Coût consolidé */}
      <div
        className="orcia-bento-card"
        data-testid="finops-kpi-consolidated-cost"
        style={{ padding: "16px", borderRadius: "8px" }}
      >
        <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)", letterSpacing: "0.05em" }}>
          {labels.consolidatedCostTitle}
        </span>
        <div style={{ fontSize: "24px", fontWeight: 700, margin: "6px 0", color: "var(--color-text-primary)" }}>
          {formatCurrency(totalCostEur)}
        </div>
        <div style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
          <span data-testid="finops-kpi-verified-internal-cost">
            {formatCurrency(verifiedInternalCostEur)} {labels.verifiedInternalSubtitle}
          </span>
          {" · "}
          <span data-testid="finops-kpi-reported-external-cost">
            {formatCurrency(reportedExternalCostEur)} {labels.reportedExternalSubtitle}
          </span>
        </div>
      </div>

      {/* KPI 2 : Tokens LLM */}
      <div
        className="orcia-bento-card"
        data-testid="finops-kpi-tokens"
        style={{ padding: "16px", borderRadius: "8px" }}
      >
        <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)", letterSpacing: "0.05em" }}>
          {labels.tokensTitle}
        </span>
        <div style={{ fontSize: "24px", fontWeight: 700, margin: "6px 0", color: "var(--color-text-primary)" }}>
          {formatTokens(totalLlmTokens)}
        </div>
        <div style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
          <span>{formatTokens(internalTokens)} {labels.internalTokensSubtitle}</span>
          {" · "}
          <span>{formatTokens(remoteTokens)} {labels.remoteTokensSubtitle}</span>
        </div>
      </div>

      {/* KPI 3 : Appels et unités externes */}
      <div
        className="orcia-bento-card"
        data-testid="finops-kpi-external-calls"
        style={{ padding: "16px", borderRadius: "8px" }}
      >
        <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)", letterSpacing: "0.05em" }}>
          {labels.externalCallsTitle}
        </span>
        <div style={{ fontSize: "24px", fontWeight: 700, margin: "6px 0", color: "var(--color-text-primary)" }}>
          {totalExternalCalls}
        </div>
        <div
          data-testid="finops-kpi-external-units-summary"
          style={{ fontSize: "12px", color: "var(--color-text-muted)" }}
        >
          {unitEntries.length > 0
            ? unitEntries.map(([unitName, val]) => `${val} ${unitName}`).join(" · ")
            : labels.externalUnitsSubtitle}
        </div>
      </div>

      {/* KPI 4 : Économies & alertes */}
      <div
        className="orcia-bento-card"
        data-testid="finops-kpi-savings"
        style={{ padding: "16px", borderRadius: "8px" }}
      >
        <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-text-muted)", letterSpacing: "0.05em" }}>
          {labels.savingsTitle}
        </span>
        <div style={{ fontSize: "24px", fontWeight: 700, margin: "6px 0", color: "var(--color-text-primary)" }}>
          {formatCurrency(cacheSavingsEur)}
        </div>
        <div style={{ fontSize: "12px", display: "flex", gap: "8px", alignItems: "center" }}>
          {activeCircuitBreakersCount > 0 ? (
            <StatusBadge
              tone="crimson"
              label={`${activeCircuitBreakersCount} ${labels.activeBreakersBadge}`}
            />
          ) : (
            <StatusBadge
              tone="emerald"
              label={`0 ${labels.activeBreakersBadge}`}
            />
          )}
          {pausedRunsCount > 0 && (
            <StatusBadge
              tone="amber"
              label={`${pausedRunsCount} ${labels.pausedRunsBadge}`}
            />
          )}
        </div>
      </div>
    </div>
  );
}
