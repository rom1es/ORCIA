import React from "react";
import { formatI18nTemplate } from "../../../i18n";
import type { ProcessVsmExecutionUiDictionary } from "../../../i18n/locales/process_vsm_execution_ui_labels";
import type { UiVsmSpec } from "./mapApiVsmToUiSpec";
import type { VsmComparisonMode } from "./ValueStreamMapHeaderAndDrawer";

export function ValueStreamMapPhaseGrid({
  phases,
  mode,
  selectedStepNum,
  copy,
  onSelectStep,
  onHighlightStep,
  onNavigateStudio,
}: {
  readonly phases: UiVsmSpec["phases"];
  readonly mode: VsmComparisonMode;
  readonly selectedStepNum: string | null;
  readonly copy: ProcessVsmExecutionUiDictionary["vsm"];
  readonly onSelectStep: (stepNum: string) => void;
  readonly onHighlightStep: (stepNum: string | null) => void;
  readonly onNavigateStudio: (workflowId: string) => void;
}): React.JSX.Element {
  return (
    <>
      {phases.map((phase) => (
        <div
          key={phase.num}
          data-testid={`vsm-phase-section-${phase.num}`}
          className="orcia-bento-card"
          style={{ display: "flex", flexDirection: "column", gap: "12px" }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "8px",
              borderBottom: "1px solid var(--color-border-subtle)",
              paddingBottom: "8px",
            }}
          >
            <div>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "11.5px",
                  fontWeight: 700,
                  color: "var(--color-primary-cobalt)",
                }}
              >
                {formatI18nTemplate(copy.phaseHeaderTemplate, {
                  num: phase.num,
                  range: phase.steps_range,
                })}
              </span>
              <h2 style={{ margin: "2px 0 0 0", fontSize: "17px" }}>
                {phase.name} — {phase.goal}
              </h2>
            </div>
            <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
              {phase.deliverables_summary}
            </span>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
              gap: "12px",
            }}
          >
            {phase.steps.map((step) => {
              const isSelected = selectedStepNum === step.num;
              return (
                <article
                  key={step.num}
                  data-testid={`vsm-step-card-${step.num}`}
                  onMouseEnter={() => onHighlightStep(step.num)}
                  onMouseLeave={() => onHighlightStep(null)}
                  className="rounded border p-3.5"
                  style={{
                    backgroundColor: isSelected
                      ? "var(--color-action-primary-subtle)"
                      : "var(--color-bg-elevated)",
                    borderColor: isSelected
                      ? "var(--color-primary-cobalt)"
                      : "var(--color-border-subtle)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                    justifyContent: "space-between",
                  }}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        gap: "6px",
                        flexWrap: "wrap",
                      }}
                    >
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontWeight: 700,
                          fontSize: "12px",
                          color: "var(--color-primary-cobalt)",
                        }}
                      >
                        {formatI18nTemplate(copy.stepBadgeTemplate, { num: step.num })}
                      </span>
                      <span
                        className="rounded px-2 py-0.5 text-xs font-semibold"
                        style={{
                          backgroundColor: "var(--color-gate-emerald-bg)",
                          color: "var(--color-gate-emerald)",
                        }}
                      >
                        {step.actor_label} · {step.status_badge}
                      </span>
                    </div>

                    <h3 style={{ margin: 0, fontSize: "15px" }}>{step.title}</h3>
                    <p style={{ margin: 0, fontSize: "12px", color: "var(--color-text-secondary)" }}>
                      {step.summary}
                    </p>

                    {mode === "today" || mode === "compare" ? (
                      <div
                        data-testid={`vsm-step-${step.num}-today-box`}
                        className="rounded border p-2 text-xs"
                        style={{
                          backgroundColor: "var(--color-surface-card)",
                          borderColor: "var(--color-border-subtle)",
                        }}
                      >
                        <strong style={{ color: "var(--color-arbitration-amber)" }}>
                          {copy.todayPrefix}
                        </strong>{" "}
                        {step.today.activities}
                      </div>
                    ) : null}

                    {mode === "tomorrow" || mode === "compare" ? (
                      <div
                        data-testid={`vsm-step-${step.num}-tomorrow-box`}
                        className="rounded border p-2 text-xs"
                        style={{
                          backgroundColor: "var(--color-gate-emerald-bg)",
                          borderColor: "var(--color-gate-emerald)",
                        }}
                      >
                        <strong style={{ color: "var(--color-gate-emerald)" }}>
                          {copy.tomorrowPrefix}
                        </strong>{" "}
                        {step.tomorrow.activities}
                        <div style={{ marginTop: "3px", fontWeight: 600 }}>
                          ⚡ {step.tomorrow.gains}
                        </div>
                      </div>
                    ) : null}

                    {step.passage_point ? (
                      <div
                        data-testid={`vsm-passage-diamond-${step.num}`}
                        onMouseEnter={() => onHighlightStep(step.num)}
                        className="rounded border px-2.5 py-1.5 text-xs"
                        style={{
                          backgroundColor: "var(--color-arbitration-bg)",
                          borderColor: "var(--color-arbitration-amber)",
                          color: "var(--color-text-primary)",
                        }}
                      >
                        <strong style={{ color: "var(--color-arbitration-amber)" }}>
                          ◆ {step.passage_point.decision}
                        </strong>
                        <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
                          {step.passage_point.question}
                        </div>
                      </div>
                    ) : null}
                  </div>

                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                    <button
                      type="button"
                      data-testid={`open-step-sheet-btn-${step.num}`}
                      onClick={() => onSelectStep(step.num)}
                      className="orcia-ds-btn-secondary"
                    >
                      {copy.openSheetBtn}
                    </button>
                    {step.linked_workflow_id ? (
                      <>
                        <button
                          type="button"
                          data-testid={`vsm-step-studio-btn-${step.num}`}
                          onClick={() => onNavigateStudio(step.linked_workflow_id!)}
                          className="orcia-ds-btn-secondary"
                        >
                          {copy.studioBtn}
                        </button>
                        <button
                          type="button"
                          data-testid={`vsm-step-run-btn-${step.num}`}
                          onClick={() => onNavigateStudio(step.linked_workflow_id!)}
                          className="orcia-ds-btn-primary"
                        >
                          {copy.executeBtn}
                        </button>
                      </>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      ))}
    </>
  );
}
