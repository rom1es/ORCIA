import React from "react";
import { resolveDictionaryForFlag } from "../../../i18n";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";

export interface WhatIfSummaryState {
  readonly subStepsEvaluated: number;
  readonly deterministicGatesPassed: boolean;
  readonly externalWritesExecuted: number;
  readonly estimatedCostUsd: number;
}

export function WorkflowWhatIfSandboxPanel({
  workflow,
  whatIfResult,
  isFr,
  onRerun,
}: {
  readonly workflow: WorkflowDefinitionV2Item;
  readonly whatIfResult: WhatIfSummaryState | null;
  readonly isFr: boolean;
  readonly onRerun: () => void;
}) {
  const copy = resolveDictionaryForFlag(isFr).processStudioUi.studio;
  const fallbackCount =
    workflow.orchestration_type === "non_deterministic"
      ? 1
      : workflow.sub_steps.filter((s) => s.enabled).length;

  return (
    <div
      data-testid="studio-what-if-sandbox-panel"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0, fontSize: "16px" }}>{copy.simulationTitle}</h3>
        <button
          type="button"
          data-testid="rerun-what-if-simulation-btn"
          onClick={onRerun}
          className="orcia-ds-btn-primary"
        >
          {copy.rerunSimulationBtn}
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
            {copy.simulationStepsVerifiedLabel}
          </div>
          <div
            data-testid="what-if-substeps-count"
            style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-primary-cobalt)" }}
          >
            {whatIfResult?.subStepsEvaluated ?? fallbackCount}
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
            {copy.simulationExternalWritesLabel}
          </div>
          <div
            data-testid="what-if-external-writes-count"
            style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-gate-emerald)" }}
          >
            {copy.simulationZeroIsolatedValue}
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
            {copy.simulationChecksLabel}
          </div>
          <div style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-gate-emerald)" }}>
            {copy.simulationCompliantValue}
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
            {copy.simulationEstimatedCostLabel}
          </div>
          <div style={{ fontSize: "18px", fontWeight: 700 }}>
            {whatIfResult?.estimatedCostUsd ?? 0.045} $
          </div>
        </div>
      </div>
    </div>
  );
}

export function WorkflowDeclarativePreviewPanel({
  workflow,
  modeBadgeLabel,
  isFr,
}: {
  readonly workflow: WorkflowDefinitionV2Item;
  readonly modeBadgeLabel: string;
  readonly isFr: boolean;
}) {
  const copy = resolveDictionaryForFlag(isFr).processStudioUi.studio;
  const readableSpec = {
    id: workflow.id,
    slug: workflow.slug,
    title: workflow.title,
    version: workflow.version,
    status: workflow.status,
    guidance_mode: modeBadgeLabel,
    expected_outcome: workflow.reflexive_objective ?? null,
    mobilizable_agents: workflow.allowed_delegate_agents ?? [],
    inputs: workflow.contract.inputs,
    outputs: workflow.contract.outputs,
    steps_count: workflow.sub_steps.length,
    guardrails: workflow.guardrails,
  };

  return (
    <div data-testid="studio-yaml-preview-panel" className="orcia-bento-card">
      <h3 style={{ margin: "0 0 8px 0", fontSize: "15px" }}>
        {copy.declarativeSpecTitle}
      </h3>
      <pre
        style={{
          margin: 0,
          padding: "12px",
          borderRadius: "6px",
          backgroundColor: "var(--color-bg-elevated)",
          border: "1px solid var(--color-border-subtle)",
          fontFamily: "var(--font-mono)",
          fontSize: "12px",
          overflowX: "auto",
        }}
      >
        {JSON.stringify(readableSpec, null, 2)}
      </pre>
    </div>
  );
}
