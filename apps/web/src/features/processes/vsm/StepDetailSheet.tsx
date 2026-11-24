import React, { useState } from "react";
import { formatI18nTemplate, resolveDictionaryForFlag } from "../../../i18n";
import type { VsmReturnLoopItem } from "./ReturnLoopsSvgOverlay";
import {
  StepDetailSheetTabsContent,
  type StepDetailData,
  type StepDetailTabKey,
} from "./StepDetailSheetTabsContent";

export type { StepDetailTabKey };

export interface StepDetailSheetProps {
  step: StepDetailData;
  allLoops: readonly VsmReturnLoopItem[];
  onClose: () => void;
  onOpenStudio: (workflowId: string) => void;
  onExecuteWorkflow: (workflowId: string) => void;
  isFr: boolean;
}

export function StepDetailSheet({
  step,
  allLoops,
  onClose,
  onOpenStudio,
  onExecuteWorkflow,
  isFr,
}: StepDetailSheetProps) {
  const [activeTab, setActiveTab] = useState<StepDetailTabKey>("overview");
  const copy = resolveDictionaryForFlag(isFr).processVsmExecutionUi.vsm;

  const outgoingLoops = allLoops.filter((l) => l.from_step_num === step.num);
  const incomingLoops = allLoops.filter((l) => l.to_step_num === step.num);

  const tabs: ReadonlyArray<{ key: StepDetailTabKey; label: string }> = [
    { key: "overview", label: copy.sheetTabOverview },
    { key: "agent_substeps", label: copy.sheetTabAgentSubsteps },
    { key: "interactions", label: copy.sheetTabInteractions },
    { key: "controls_gates", label: copy.sheetTabControlsGates },
    {
      key: "return_loops",
      label: formatI18nTemplate(copy.sheetTabReturnLoopsTemplate, {
        count: outgoingLoops.length + incomingLoops.length,
      }),
    },
    { key: "opportunities", label: copy.sheetTabOpportunities },
  ];

  return (
    <div
      data-testid={`vsm-step-detail-sheet-${step.num}`}
      className="orcia-bento-card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "14px",
        border: "2px solid var(--color-primary-cobalt)",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <span
              className="rounded px-2 py-0.5 text-xs font-bold"
              style={{
                backgroundColor: "var(--color-action-primary-subtle)",
                color: "var(--color-primary-cobalt)",
                fontFamily: "var(--font-mono)",
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
          <h3 style={{ margin: "4px 0 0 0", fontSize: "18px" }}>{step.title}</h3>
          <p style={{ margin: "2px 0 0 0", fontSize: "13px", color: "var(--color-text-secondary)" }}>
            {step.summary}
          </p>
        </div>

        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {step.linked_workflow_id ? (
            <>
              <button
                type="button"
                data-testid={`sheet-open-studio-btn-${step.num}`}
                onClick={() => onOpenStudio(step.linked_workflow_id!)}
                className="orcia-ds-btn-secondary"
              >
                {copy.sheetOpenStudioBtn}
              </button>
              <button
                type="button"
                data-testid={`sheet-execute-wf-btn-${step.num}`}
                onClick={() => onExecuteWorkflow(step.linked_workflow_id!)}
                className="orcia-ds-btn-primary"
              >
                {copy.sheetExecuteWorkflowBtn}
              </button>
            </>
          ) : null}
          <button
            type="button"
            data-testid="close-step-detail-sheet-btn"
            onClick={onClose}
            className="orcia-ds-btn-secondary"
          >
            {copy.sheetCloseBtn}
          </button>
        </div>
      </div>

      {/* 6 Tabs Navigation */}
      <div
        role="tablist"
        aria-label={copy.sheetTabsAriaLabel}
        className="orcia-ds-tabs"
      >
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.key}
            data-testid={`step-sheet-tab-${tab.key}`}
            onClick={() => setActiveTab(tab.key)}
            className="orcia-ds-tab"
          >
            {tab.label}
          </button>
        ))}
      </div>

      <StepDetailSheetTabsContent
        activeTab={activeTab}
        step={step}
        outgoingLoops={outgoingLoops}
        incomingLoops={incomingLoops}
        copy={copy}
      />
    </div>
  );
}
