import React from "react";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";

export interface StudioWhatIfPanelProps {
  readonly workflow: WorkflowDefinitionV2Item;
  readonly isFr: boolean;
  readonly whatIfResult: {
    readonly subStepsEvaluated: number;
    readonly deterministicGatesPassed: boolean;
    readonly externalWritesExecuted: number;
    readonly estimatedCostUsd: number;
  } | null;
  readonly onRerunWhatIf: () => void;
}

export function StudioWhatIfPanel({
  workflow,
  isFr,
  whatIfResult,
  onRerunWhatIf,
}: StudioWhatIfPanelProps): React.ReactElement {
  return (
    <div
      data-testid="studio-what-if-sandbox-panel"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0, fontSize: "16px" }}>
          {isFr
            ? "Simulation à blanc (sans écriture dans Jira, Confluence ou Git)"
            : "Dry-Run Simulation (zero external writes)"}
        </h3>
        <button
          type="button"
          data-testid="rerun-what-if-simulation-btn"
          onClick={onRerunWhatIf}
          className="orcia-ds-btn-primary"
        >
          {isFr ? "↻ Relancer le test à blanc" : "↻ Re-run simulation"}
        </button>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
          gap: "10px",
        }}
      >
        <div
          className="rounded border p-3"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
          }}
        >
          <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
            Étapes actives testées
          </div>
          <div
            data-testid="what-if-substeps-count"
            style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-primary-cobalt)" }}
          >
            {whatIfResult?.subStepsEvaluated ?? workflow.sub_steps.filter((s) => s.enabled).length}
          </div>
        </div>
        <div
          className="rounded border p-3"
          style={{
            backgroundColor: "var(--color-gate-emerald-bg)",
            borderColor: "var(--color-gate-emerald)",
          }}
        >
          <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
            Modifications externes
          </div>
          <div
            data-testid="what-if-external-writes-count"
            style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-gate-emerald)" }}
          >
            0 (Mode isolé)
          </div>
        </div>
        <div
          className="rounded border p-3"
          style={{
            backgroundColor: "var(--color-gate-emerald-bg)",
            borderColor: "var(--color-gate-emerald)",
          }}
        >
          <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
            Contrôles qualité
          </div>
          <div style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-gate-emerald)" }}>
            Conformes
          </div>
        </div>
        <div
          className="rounded border p-3"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
          }}
        >
          <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
            Coût estimé par dossier
          </div>
          <div style={{ fontSize: "18px", fontWeight: 700 }}>
            {whatIfResult?.estimatedCostUsd ?? 0.045} $
          </div>
        </div>
      </div>
    </div>
  );
}
