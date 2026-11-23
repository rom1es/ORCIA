import React from "react";
import { formatI18nTemplate, resolveDictionaryForFlag } from "../../../i18n";
import type { ProcessOrchestrationModesCopy } from "../../../i18n/locales/process_orchestration_modes_labels";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";
import { WorkflowBlock2GoalDrivenSection } from "./WorkflowBlock2GoalDrivenSection";

export interface WorkflowBlock2ExecutionSectionProps {
  readonly workflow: WorkflowDefinitionV2Item;
  readonly goalObjectiveDraft: string;
  readonly goalDelegateAgentsDraft: readonly string[];
  readonly copy: ProcessOrchestrationModesCopy;
  readonly isFr: boolean;
  readonly onChangeGoalObjective: (nextObjective: string) => void;
  readonly onToggleDelegateAgent: (agentSlug: string) => void;
  readonly onToggleSubStepEnabled: (subStepId: string) => void;
  readonly onSwitchExecutionMode: (mode: "native_orcia" | "external_delegated") => void;
}

export function WorkflowBlock2ExecutionSection({
  workflow,
  goalObjectiveDraft,
  goalDelegateAgentsDraft,
  copy,
  isFr,
  onChangeGoalObjective,
  onToggleDelegateAgent,
  onToggleSubStepEnabled,
  onSwitchExecutionMode,
}: WorkflowBlock2ExecutionSectionProps) {
  const studioCopy = resolveDictionaryForFlag(isFr).processStudioUi.studio;

  if (workflow.orchestration_type === "non_deterministic") {
    return (
      <WorkflowBlock2GoalDrivenSection
        goalObjectiveDraft={goalObjectiveDraft}
        goalDelegateAgentsDraft={goalDelegateAgentsDraft}
        copy={copy}
        isFr={isFr}
        onChangeGoalObjective={onChangeGoalObjective}
        onToggleDelegateAgent={onToggleDelegateAgent}
      />
    );
  }

  return (
    <div
      data-testid="studio-block-2-deterministic-substeps"
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
          <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
            {copy.milestoneBlock2Title}
          </strong>
          <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
            {copy.milestoneBlock2Subtitle}
          </div>
        </div>

        <div style={{ display: "flex", gap: "6px" }}>
          <button
            type="button"
            data-testid="mode-switch-native-orcia-btn"
            onClick={() => onSwitchExecutionMode("native_orcia")}
            className={
              workflow.execution_mode === "native_orcia"
                ? "orcia-ds-btn-primary"
                : "orcia-ds-btn-secondary"
            }
          >
            {studioCopy.block2GuidedOrciaBtn}
          </button>
          <button
            type="button"
            data-testid="mode-switch-external-delegated-btn"
            onClick={() => onSwitchExecutionMode("external_delegated")}
            className={
              workflow.execution_mode === "external_delegated"
                ? "orcia-ds-btn-primary"
                : "orcia-ds-btn-secondary"
            }
          >
            {studioCopy.block2ExternalIdeBtn}
          </button>
        </div>
      </div>

      {workflow.execution_mode === "external_delegated" ? (
        <div
          data-testid="studio-external-delegated-banner"
          className="rounded border p-3 text-xs"
          style={{
            backgroundColor: "var(--color-arbitration-bg)",
            borderColor: "var(--color-arbitration-amber)",
          }}
        >
          <strong>{studioCopy.block2ExternalBannerTitle}</strong>{" "}
          {studioCopy.block2ExternalBannerDesc}
        </div>
      ) : null}

      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {workflow.sub_steps.map((sub, idx) => (
          <div
            key={sub.id}
            data-testid={`studio-substep-card-${sub.id}`}
            className="rounded border p-3"
            style={{
              backgroundColor: sub.enabled
                ? "var(--color-bg-elevated)"
                : "var(--color-surface-muted)",
              borderColor: sub.enabled
                ? "var(--color-primary-cobalt)"
                : "var(--color-border-subtle)",
              opacity: sub.enabled ? 1 : 0.65,
            }}
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
              <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                <span
                  style={{
                    fontSize: "12px",
                    fontWeight: 700,
                    color: "var(--color-primary-cobalt)",
                  }}
                >
                  {formatI18nTemplate(studioCopy.block2StepLabelTemplate, { index: idx + 1 })}
                </span>
                <strong style={{ fontSize: "13.5px" }}>{sub.name}</strong>
                {sub.requires_human_checkpoint ? (
                  <span
                    className="rounded px-2 py-0.5 text-xs font-semibold"
                    style={{
                      backgroundColor: "var(--color-arbitration-bg)",
                      color: "var(--color-arbitration-amber)",
                    }}
                  >
                    {studioCopy.block2HumanReviewBadge}
                  </span>
                ) : null}
                {sub.write_preview_required ? (
                  <span
                    className="rounded px-2 py-0.5 text-xs font-semibold"
                    style={{
                      backgroundColor: "var(--color-gate-emerald-bg)",
                      color: "var(--color-gate-emerald)",
                    }}
                  >
                    {studioCopy.block2ConfirmPublishBadge}
                  </span>
                ) : null}
              </div>

              <button
                type="button"
                data-testid={`toggle-substep-enabled-${sub.id}`}
                onClick={() => onToggleSubStepEnabled(sub.id)}
                className="orcia-ds-btn-secondary"
              >
                {sub.enabled ? studioCopy.block2StepEnabledBtn : studioCopy.block2StepSkippedBtn}
              </button>
            </div>

            <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", marginTop: "6px" }}>
              <strong>{studioCopy.block2GoalLabel}</strong> {sub.role_description}
            </div>
            <div style={{ fontSize: "12px", marginTop: "3px" }}>
              <strong>{studioCopy.block2ExpectedOutputLabel}</strong> {sub.output_description}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
