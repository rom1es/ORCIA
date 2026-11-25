import React from "react";
import { OrciaDataCard } from "../OrciaDataCard";
import { StatusBadge } from "../StatusBadge";

export interface FinopsProcessRowData {
  readonly workflowId: string;
  readonly workflowTitle: string;
  readonly runsCount: number;
  readonly amortizedSetupCostEur: number;
  readonly runCostEur: number;
  readonly humanTimeCostEur: number;
  readonly totalCostEur: number;
  readonly ttmReductionPct: number;
  readonly activeBudgetOverride?: boolean;
  readonly pausedRunsCount?: number;
  readonly pausedReason?: "BUDGET" | "RETRIES" | null;
  readonly samplePausedRunId?: string;
  readonly hasDeclaredBaseline?: boolean;
}

export interface FinopsTierRowData {
  readonly inferenceTier: string;
  readonly effort: string;
  readonly invocationsCount: number;
  readonly inputTokens: number;
  readonly outputTokens: number;
  readonly totalTokens: number;
  readonly costEur: number;
}

export interface FinopsProcessAndTiersTabProps {
  readonly activeSubTab: "processes" | "tiers";
  readonly processes: readonly FinopsProcessRowData[];
  readonly tiers: readonly FinopsTierRowData[];
  readonly labels: {
    processesTable: {
      title: string;
      workflowCol: string;
      runsCol: string;
      setupCostCol: string;
      runCostCol: string;
      humanTimeCol: string;
      totalCostCol: string;
      ttmCol: string;
      statusCol: string;
      actionsCol: string;
      pausedBadgeBudget: string;
      pausedBadgeRetries: string;
      activeBadge: string;
      overrideButton: string;
      emptyProcessesText?: string;
    };
    tiersTable: {
      title: string;
      tierCol: string;
      effortCol: string;
      invocationsCol: string;
      inputTokensCol: string;
      outputTokensCol: string;
      totalTokensCol: string;
      costCol: string;
      emptyTiersText?: string;
      tierLabels?: Readonly<Record<string, string>>;
      effortLabels?: Readonly<Record<string, string>>;
    };
  };
  readonly onOpenOverrideModal?: (runId: string, workflowTitle: string) => void;
}

function formatEur(val: number): string {
  const safeVal = Number.isFinite(val) ? val : 0;
  const isMicro = Math.abs(safeVal) > 0 && Math.abs(safeVal) < 0.01;
  return `${safeVal.toFixed(isMicro ? 3 : 2).replace(".", ",")} €`;
}

export function FinopsProcessAndTiersTab({
  activeSubTab,
  processes,
  tiers,
  labels,
  onOpenOverrideModal,
}: FinopsProcessAndTiersTabProps): React.ReactElement {
  if (activeSubTab === "tiers") {
    return (
      <OrciaDataCard testId="finops-tiers-card" title={labels.tiersTable.title}>
        <div className="finops-tiers-tab" data-testid="finops-tiers-tab" style={{ overflowX: "auto" }}>
        <table className="orcia-table" style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left", color: "var(--color-text-muted)" }}>
              <th style={{ padding: "10px 12px" }}>{labels.tiersTable.tierCol}</th>
              <th style={{ padding: "10px 12px" }}>{labels.tiersTable.effortCol}</th>
              <th style={{ padding: "10px 12px" }}>{labels.tiersTable.invocationsCol}</th>
              <th style={{ padding: "10px 12px" }}>{labels.tiersTable.inputTokensCol}</th>
              <th style={{ padding: "10px 12px" }}>{labels.tiersTable.outputTokensCol}</th>
              <th style={{ padding: "10px 12px" }}>{labels.tiersTable.totalTokensCol}</th>
              <th style={{ padding: "10px 12px" }}>{labels.tiersTable.costCol}</th>
            </tr>
          </thead>
          <tbody>
            {tiers.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: "20px", textAlign: "center", color: "var(--color-text-muted)" }}>
                  {labels.tiersTable.emptyTiersText ?? ""}
                </td>
              </tr>
            ) : (
              tiers.map((t, idx) => (
                <tr key={`${t.inferenceTier}-${t.effort}-${idx}`} style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <td style={{ padding: "10px 12px", fontWeight: 600 }}>
                    {labels.tiersTable.tierLabels?.[t.inferenceTier] ?? t.inferenceTier}
                  </td>
                  <td style={{ padding: "10px 12px" }}>
                    {labels.tiersTable.effortLabels?.[t.effort] ?? t.effort}
                  </td>
                  <td style={{ padding: "10px 12px" }}>{t.invocationsCount}</td>
                  <td style={{ padding: "10px 12px" }}>{t.inputTokens.toLocaleString()}</td>
                  <td style={{ padding: "10px 12px" }}>{t.outputTokens.toLocaleString()}</td>
                  <td style={{ padding: "10px 12px" }}>{t.totalTokens.toLocaleString()}</td>
                  <td style={{ padding: "10px 12px", fontWeight: 600 }}>{formatEur(t.costEur)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        </div>
      </OrciaDataCard>
    );
  }

  return (
    <OrciaDataCard testId="finops-processes-card" title={labels.processesTable.title}>
      <div className="finops-processes-tab" data-testid="finops-processes-tab" style={{ overflowX: "auto" }}>
      <table className="orcia-table" style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left", color: "var(--color-text-muted)" }}>
            <th style={{ padding: "10px 12px" }}>{labels.processesTable.workflowCol}</th>
            <th style={{ padding: "10px 12px" }}>{labels.processesTable.runsCol}</th>
            <th style={{ padding: "10px 12px" }}>{labels.processesTable.setupCostCol}</th>
            <th style={{ padding: "10px 12px" }}>{labels.processesTable.runCostCol}</th>
            <th style={{ padding: "10px 12px" }}>{labels.processesTable.humanTimeCol}</th>
            <th style={{ padding: "10px 12px" }}>{labels.processesTable.totalCostCol}</th>
            <th style={{ padding: "10px 12px" }}>{labels.processesTable.ttmCol}</th>
            <th style={{ padding: "10px 12px" }}>{labels.processesTable.statusCol}</th>
            <th style={{ padding: "10px 12px" }}>{labels.processesTable.actionsCol}</th>
          </tr>
        </thead>
        <tbody>
          {processes.length === 0 ? (
            <tr>
              <td colSpan={9} style={{ padding: "20px", textAlign: "center", color: "var(--color-text-muted)" }}>
                {labels.processesTable.emptyProcessesText ?? ""}
              </td>
            </tr>
          ) : (
            processes.map((p) => {
              const hasPaused = (p.pausedRunsCount ?? 0) > 0;
              const isRetries = p.pausedReason === "RETRIES";
              const targetRunId = p.samplePausedRunId ?? null;

              return (
                <tr
                  key={p.workflowId}
                  data-testid={`finops-process-row-${p.workflowId}`}
                  style={{ borderBottom: "1px solid var(--color-border)" }}
                >
                  <td style={{ padding: "10px 12px", fontWeight: 600 }}>{p.workflowTitle}</td>
                  <td style={{ padding: "10px 12px" }}>{p.runsCount}</td>
                  <td style={{ padding: "10px 12px" }}>{formatEur(p.amortizedSetupCostEur)}</td>
                  <td style={{ padding: "10px 12px" }}>{formatEur(p.runCostEur)}</td>
                  <td style={{ padding: "10px 12px" }}>{formatEur(p.humanTimeCostEur)}</td>
                  <td style={{ padding: "10px 12px", fontWeight: 700 }}>{formatEur(p.totalCostEur)}</td>
                  <td style={{ padding: "10px 12px", color: "var(--color-status-success)" }}>
                    {p.hasDeclaredBaseline === false
                      ? "—"
                      : p.ttmReductionPct > 0
                        ? `-${p.ttmReductionPct}%`
                        : "0%"}
                  </td>
                  <td style={{ padding: "10px 12px" }}>
                    {hasPaused ? (
                      <StatusBadge
                        tone="crimson"
                        label={
                          isRetries
                            ? labels.processesTable.pausedBadgeRetries
                            : labels.processesTable.pausedBadgeBudget
                        }
                      />
                    ) : (
                      <StatusBadge
                        tone="emerald"
                        label={labels.processesTable.activeBadge}
                      />
                    )}
                  </td>
                  <td style={{ padding: "10px 12px" }}>
                    {hasPaused && targetRunId ? (
                      <button
                        type="button"
                        data-testid={`finops-override-btn-${p.workflowId}`}
                        className="orcia-ds-btn orcia-ds-btn-secondary"
                        style={{ fontSize: "12px", padding: "4px 8px" }}
                        onClick={() => onOpenOverrideModal?.(targetRunId, p.workflowTitle)}
                      >
                        {labels.processesTable.overrideButton} →
                      </button>
                    ) : null}
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
      </div>
    </OrciaDataCard>
  );
}
