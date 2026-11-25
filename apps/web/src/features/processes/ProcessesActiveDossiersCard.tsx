import { OrciaDataCard, OrciaIcon, StatusBadge } from "@orcia/ui";
import React from "react";
import { useI18n } from "../../i18n";
import {
  formatAgentHumanLabel,
  InteractiveRunDrawer,
} from "./execution/InteractiveRunDrawer";
import type { WorkflowDefinitionV2Item } from "./processStudioV2Data";

export interface ProcessesActiveDossiersCardProps {
  readonly featuredPendingWorkflow: WorkflowDefinitionV2Item | null;
  readonly activeRunWorkflow: WorkflowDefinitionV2Item | null;
  readonly activeWorkspaceId: string;
  readonly onSelectWorkflowRun: (workflowId: string | null) => void;
}

export function ProcessesActiveDossiersCard({
  featuredPendingWorkflow,
  activeRunWorkflow,
  activeWorkspaceId,
  onSelectWorkflowRun,
}: ProcessesActiveDossiersCardProps): React.JSX.Element {
  const { locale, isFr, dictionary } = useI18n();
  const copy = dictionary.processStudioUi.hub;

  return (
    <OrciaDataCard
      testId="processes-active-dossiers-card"
      title={copy.activeDossiersTitle}
      subtitle={copy.activeDossiersSubtitle}
      metaBadge={<StatusBadge tone="amber" label={copy.pendingValidationBadge} />}
      actions={
        featuredPendingWorkflow && !activeRunWorkflow ? (
          <button
            type="button"
            data-testid="resume-featured-dossier-btn"
            onClick={() => onSelectWorkflowRun(featuredPendingWorkflow.id)}
            className="orcia-ds-btn orcia-ds-btn-cobalt-outline orcia-ds-btn-sm orcia-ds-nowrap"
          >
            <OrciaIcon name="play" />
            <span>{copy.reviewPendingDossierBtn}</span>
          </button>
        ) : null
      }
    >
      {featuredPendingWorkflow && !activeRunWorkflow ? (
        <div
          className="rounded border p-3"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "10px",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
              <strong style={{ fontSize: "14px" }}>
                {copy.featuredDossierPrefix} — {featuredPendingWorkflow.title}
              </strong>
              <span
                className="rounded px-2 py-0.5 text-xs font-semibold"
                style={{
                  backgroundColor: "var(--color-action-primary-subtle)",
                  color: "var(--color-primary-cobalt)",
                }}
              >
                {copy.featuredStepBadge}
              </span>
            </div>
            <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
              {formatAgentHumanLabel(featuredPendingWorkflow.agent_ref, locale)} ·{" "}
              {copy.featuredReadySummary}
            </span>
          </div>

          <button
            type="button"
            onClick={() => onSelectWorkflowRun(featuredPendingWorkflow.id)}
            className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
          >
            {copy.openDeliverableBtn}
          </button>
        </div>
      ) : null}

      {activeRunWorkflow ? (
        <InteractiveRunDrawer
          key={`${activeRunWorkflow.id}-${activeWorkspaceId || "default"}`}
          workflow={activeRunWorkflow}
          workspaceId={activeWorkspaceId || undefined}
          onClose={() => onSelectWorkflowRun(null)}
          isFr={isFr}
        />
      ) : null}
    </OrciaDataCard>
  );
}
