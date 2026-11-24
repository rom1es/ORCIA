import React from "react";
import { formatI18nTemplate } from "../../../i18n";
import type { ProcessVsmExecutionUiDictionary } from "../../../i18n/locales/process_vsm_execution_ui_labels";
import type { VsmReturnLoopItem } from "./ReturnLoopsSvgOverlay";

export type StepDetailTabKey =
  | "overview"
  | "agent_substeps"
  | "interactions"
  | "controls_gates"
  | "return_loops"
  | "opportunities";

export interface StepDetailData {
  num: string;
  title: string;
  actor_type: string;
  actor_label: string;
  status_badge: string;
  summary: string;
  deliverable: string;
  attention_point?: string | null;
  linked_workflow_id?: string | null;
  today: { actors: string; activities: string; deliverable: string; pain_points: string };
  tomorrow: { actors: string; activities: string; deliverable: string; gains: string };
  passage_point?: {
    decision: string;
    question: string;
    actors: string;
    possible_outcomes: string[];
  } | null;
  detail_tabs: {
    agent_sub_steps: Array<Record<string, unknown>>;
    human_ai_interactions: Record<string, unknown>;
    controls_and_gates: Record<string, unknown>;
    complements_and_missing: string[];
    guardrails: string[];
  };
}

export function StepDetailSheetTabsContent({
  activeTab,
  step,
  outgoingLoops,
  incomingLoops,
  copy,
}: {
  readonly activeTab: StepDetailTabKey;
  readonly step: StepDetailData;
  readonly outgoingLoops: readonly VsmReturnLoopItem[];
  readonly incomingLoops: readonly VsmReturnLoopItem[];
  readonly copy: ProcessVsmExecutionUiDictionary["vsm"];
}): React.JSX.Element | null {
  const interactions = step.detail_tabs.human_ai_interactions ?? {};
  const controls = step.detail_tabs.controls_and_gates ?? {};

  if (activeTab === "overview") {
    return (
      <div
        data-testid="step-sheet-panel-overview"
        style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(290px, 1fr))", gap: "12px" }}
      >
        <div
          className="rounded border p-3"
          style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}
        >
          <div style={{ fontWeight: 700, fontSize: "13px", color: "var(--color-arbitration-amber)" }}>
            {copy.sheetTodayHeading}
          </div>
          <p style={{ fontSize: "12.5px", margin: "6px 0" }}>
            <strong>{copy.sheetActorsLabel}</strong> {step.today.actors}
          </p>
          <p style={{ fontSize: "12.5px", margin: "6px 0" }}>
            <strong>{copy.sheetActivitiesLabel}</strong> {step.today.activities}
          </p>
          <p style={{ fontSize: "12.5px", margin: "6px 0" }}>
            <strong>{copy.sheetDeliverableLabel}</strong> {step.today.deliverable}
          </p>
          <p style={{ fontSize: "12.5px", margin: "6px 0", color: "var(--color-stale-crimson)" }}>
            <strong>{copy.sheetPainPointsLabel}</strong> {step.today.pain_points}
          </p>
        </div>

        <div
          className="rounded border p-3"
          style={{ backgroundColor: "var(--color-gate-emerald-bg)", borderColor: "var(--color-gate-emerald)" }}
        >
          <div style={{ fontWeight: 700, fontSize: "13px", color: "var(--color-gate-emerald)" }}>
            {copy.sheetTomorrowHeading}
          </div>
          <p style={{ fontSize: "12.5px", margin: "6px 0" }}>
            <strong>{copy.sheetActorsLabel}</strong> {step.tomorrow.actors}
          </p>
          <p style={{ fontSize: "12.5px", margin: "6px 0" }}>
            <strong>{copy.sheetActivitiesLabel}</strong> {step.tomorrow.activities}
          </p>
          <p style={{ fontSize: "12.5px", margin: "6px 0" }}>
            <strong>{copy.sheetDeliverableLabel}</strong> {step.tomorrow.deliverable}
          </p>
          <p style={{ fontSize: "12.5px", margin: "6px 0", fontWeight: 600 }}>
            <strong>{copy.sheetExpectedGainsLabel}</strong> {step.tomorrow.gains}
          </p>
        </div>
      </div>
    );
  }

  if (activeTab === "agent_substeps") {
    return (
      <div data-testid="step-sheet-panel-agent_substeps" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {step.detail_tabs.agent_sub_steps.length === 0 ? (
          <div style={{ fontSize: "13px", color: "var(--color-text-secondary)" }}>
            {copy.sheetHumanOrExternalEmpty}
          </div>
        ) : (
          step.detail_tabs.agent_sub_steps.map((sub, idx) => (
            <div
              key={String(sub.id ?? idx)}
              data-testid={`sheet-substep-card-${String(sub.id ?? idx)}`}
              className="rounded border p-3"
              style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong style={{ fontSize: "13.5px", color: "var(--color-primary-cobalt)" }}>
                  {formatI18nTemplate(copy.sheetSubstepPrefixTemplate, {
                    index: idx + 1,
                    name: String(sub.name ?? sub.shortLabel ?? ""),
                  })}
                </strong>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--color-text-secondary)" }}>
                  {String(sub.trigger ?? "")}
                </span>
              </div>
              <div style={{ fontSize: "12.5px", marginTop: "6px" }}>
                <strong>{copy.sheetSubstepRoleLabel}</strong> {String(sub.role ?? "")}
              </div>
              <div style={{ fontSize: "12.5px", marginTop: "4px" }}>
                <strong>{copy.sheetSubstepOutputLabel}</strong> {String(sub.output ?? "")}
              </div>
              {sub.humanCheck ? (
                <div style={{ fontSize: "12px", marginTop: "6px", color: "var(--color-arbitration-amber)", fontWeight: 600 }}>
                  {formatI18nTemplate(copy.sheetSubstepHumanCheckTemplate, { check: String(sub.humanCheck) })}
                </div>
              ) : null}
            </div>
          ))
        )}
      </div>
    );
  }

  if (activeTab === "interactions") {
    return (
      <div data-testid="step-sheet-panel-interactions" style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "13px" }}>
        <div className="rounded border p-3" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}>
          <strong>{copy.sheetInitiativeLabel}</strong>{" "}
          {String(interactions.initiative ?? step.actor_label)}
        </div>
        <div className="rounded border p-3" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}>
          <strong>{copy.sheetHumanValidationLabel}</strong>{" "}
          {String(interactions.humanValidation ?? step.passage_point?.question ?? copy.sheetHumanValidationFallback)}
        </div>
        <div className="rounded border p-3" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}>
          <strong>{copy.sheetOutputDeliverableLabel}</strong> {step.deliverable}
        </div>
      </div>
    );
  }

  if (activeTab === "controls_gates") {
    return (
      <div data-testid="step-sheet-panel-controls_gates" style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "13px" }}>
        <div className="rounded border p-3" style={{ backgroundColor: "var(--color-gate-emerald-bg)", borderColor: "var(--color-gate-emerald)" }}>
          <strong>{copy.sheetControlsPipelineTitle}</strong>
          <div style={{ marginTop: "6px" }}>{JSON.stringify(controls)}</div>
        </div>
        {step.passage_point ? (
          <div className="rounded border p-3" style={{ backgroundColor: "var(--color-arbitration-bg)", borderColor: "var(--color-arbitration-amber)" }}>
            <strong>{formatI18nTemplate(copy.sheetPassagePointTitleTemplate, { decision: step.passage_point.decision })}</strong>
            <div style={{ marginTop: "4px" }}>{step.passage_point.question}</div>
            <div style={{ marginTop: "4px", fontSize: "12px", color: "var(--color-text-secondary)" }}>
              {formatI18nTemplate(copy.sheetPossibleOutcomesTemplate, {
                outcomes: step.passage_point.possible_outcomes.join(" · "),
              })}
            </div>
          </div>
        ) : null}
      </div>
    );
  }

  if (activeTab === "return_loops") {
    return (
      <div data-testid="step-sheet-panel-return_loops" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        <div>
          <strong style={{ fontSize: "13px" }}>{copy.sheetOutgoingLoopsHeading}</strong>
          {outgoingLoops.length === 0 ? (
            <div style={{ fontSize: "12.5px", color: "var(--color-text-secondary)", marginTop: "4px" }}>
              {copy.sheetNoOutgoingLoops}
            </div>
          ) : (
            outgoingLoops.map((loop) => (
              <div
                key={loop.id}
                className="rounded border p-2.5 mt-2 text-xs"
                style={{ backgroundColor: "var(--color-arbitration-bg)", borderColor: "var(--color-arbitration-amber)" }}
              >
                <strong>↩ {loop.from_step_num} → {loop.to_step_num} ({loop.reentry_mode})</strong> — {loop.trigger_condition} : {loop.reason}
              </div>
            ))
          )}
        </div>

        <div>
          <strong style={{ fontSize: "13px" }}>{copy.sheetIncomingLoopsHeading}</strong>
          {incomingLoops.length === 0 ? (
            <div style={{ fontSize: "12.5px", color: "var(--color-text-secondary)", marginTop: "4px" }}>
              {copy.sheetNoIncomingLoops}
            </div>
          ) : (
            incomingLoops.map((loop) => (
              <div
                key={loop.id}
                className="rounded border p-2.5 mt-2 text-xs"
                style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}
              >
                <strong>↩ {copy.sheetIncomingLoopPrefix} {loop.from_step_num} → {loop.to_step_num} ({loop.reentry_mode})</strong> — {loop.reason} ({loop.impact_summary})
              </div>
            ))
          )}
        </div>
      </div>
    );
  }

  return (
    <div data-testid="step-sheet-panel-opportunities" style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "13px" }}>
      <div>
        <strong>{copy.sheetGuardrailsLabel}</strong>
        <ul style={{ margin: "6px 0", paddingLeft: "18px" }}>
          {step.detail_tabs.guardrails.map((g, i) => (
            <li key={i}>{g}</li>
          ))}
        </ul>
      </div>
      {step.detail_tabs.complements_and_missing.length > 0 ? (
        <div>
          <strong>{copy.sheetComplementsLabel}</strong>
          <ul style={{ margin: "6px 0", paddingLeft: "18px" }}>
            {step.detail_tabs.complements_and_missing.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
