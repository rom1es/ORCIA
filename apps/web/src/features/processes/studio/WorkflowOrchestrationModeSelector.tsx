import { ContextualInfoTriggerButton, OrciaIcon } from "@orcia/ui";
import React from "react";
import type { ProcessOrchestrationModesCopy } from "../../../i18n/locales/process_orchestration_modes_labels";

export type UiProcessOrchestrationType = "non_deterministic" | "deterministic_dbos";

export interface WorkflowOrchestrationModeSelectorProps {
  readonly orchestrationType: UiProcessOrchestrationType;
  readonly copy: ProcessOrchestrationModesCopy;
  readonly isFr: boolean;
  readonly onSelectOrchestrationType: (next: UiProcessOrchestrationType) => void;
  readonly onOpenHelpSection: (sectionId: string) => void;
}

export function WorkflowOrchestrationModeSelector({
  orchestrationType,
  copy,
  isFr,
  onSelectOrchestrationType,
  onOpenHelpSection,
}: WorkflowOrchestrationModeSelectorProps) {
  const isGoalDriven = orchestrationType === "non_deterministic";
  const isMilestoneDriven = orchestrationType === "deterministic_dbos";

  return (
    <div
      data-testid="workflow-orchestration-mode-selector"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "10px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
              {copy.selectorSectionTitle}
            </strong>
            <ContextualInfoTriggerButton
              sectionId="workflows-instructions"
              label={
                isFr
                  ? "Comprendre la différence entre objectif adaptatif et jalons"
                  : "Understand goal-driven vs milestone-driven modes"
              }
              onOpenHelpSection={onOpenHelpSection}
            />
          </div>
          <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
            {copy.selectorSectionHint}
          </div>
        </div>
      </div>

      <div
        role="radiogroup"
        aria-label={copy.selectorSectionTitle}
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "10px",
        }}
      >
        <button
          type="button"
          role="radio"
          aria-checked={isGoalDriven}
          data-testid="mode-option-goal-driven"
          onClick={() => onSelectOrchestrationType("non_deterministic")}
          className="rounded border p-3 text-left"
          style={{
            backgroundColor: isGoalDriven
              ? "var(--color-ontology-bg)"
              : "var(--color-bg-elevated)",
            borderColor: isGoalDriven
              ? "var(--color-ontology-cyan)"
              : "var(--color-border-subtle)",
            cursor: "pointer",
            display: "flex",
            flexDirection: "column",
            gap: "6px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                fontWeight: 700,
                fontSize: "13.5px",
                color: isGoalDriven
                  ? "var(--color-ontology-cyan)"
                  : "var(--color-text-primary)",
              }}
            >
              <OrciaIcon name="compass" />
              <span>{copy.goalDrivenTitle}</span>
            </span>
            {isGoalDriven ? (
              <span
                className="rounded px-2 py-0.5 text-xs font-semibold"
                style={{
                  backgroundColor: "var(--color-gate-emerald-bg)",
                  color: "var(--color-gate-emerald)",
                }}
              >
                <OrciaIcon name="check" />
              </span>
            ) : null}
          </div>
          <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
            {copy.goalDrivenSubtitle}
          </div>
        </button>

        <button
          type="button"
          role="radio"
          aria-checked={isMilestoneDriven}
          data-testid="mode-option-milestone-driven"
          onClick={() => onSelectOrchestrationType("deterministic_dbos")}
          className="rounded border p-3 text-left"
          style={{
            backgroundColor: isMilestoneDriven
              ? "var(--color-action-primary-subtle)"
              : "var(--color-bg-elevated)",
            borderColor: isMilestoneDriven
              ? "var(--color-primary-cobalt)"
              : "var(--color-border-subtle)",
            cursor: "pointer",
            display: "flex",
            flexDirection: "column",
            gap: "6px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                fontWeight: 700,
                fontSize: "13.5px",
                color: isMilestoneDriven
                  ? "var(--color-primary-cobalt)"
                  : "var(--color-text-primary)",
              }}
            >
              <OrciaIcon name="processes" />
              <span>{copy.milestoneDrivenTitle}</span>
            </span>
            {isMilestoneDriven ? (
              <span
                className="rounded px-2 py-0.5 text-xs font-semibold"
                style={{
                  backgroundColor: "var(--color-gate-emerald-bg)",
                  color: "var(--color-gate-emerald)",
                }}
              >
                <OrciaIcon name="check" />
              </span>
            ) : null}
          </div>
          <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
            {copy.milestoneDrivenSubtitle}
          </div>
        </button>
      </div>
    </div>
  );
}
