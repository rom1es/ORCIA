import { OrciaIcon } from "@orcia/ui";
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
    <div
      data-testid="processes-active-dossiers-card"
      className="orcia-bento-card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        borderLeft: "4px solid var(--color-primary-cobalt)",
      }}
    >
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
              className="rounded px-2.5 py-0.5 text-xs font-semibold"
              style={{
                backgroundColor: "var(--color-arbitration-bg)",
                color: "var(--color-arbitration-amber)",
              }}
            >
              {copy.pendingValidationBadge}
            </span>
          </div>
          <h2 style={{ margin: "6px 0 0 0", fontSize: "var(--font-size-h2)" }}>
            {copy.activeDossiersTitle}
          </h2>
          <p style={{ margin: "2px 0 0 0", fontSize: "13px", color: "var(--color-text-secondary)" }}>
            {copy.activeDossiersSubtitle}
          </p>
        </div>

        {featuredPendingWorkflow && !activeRunWorkflow ? (
          <button
            type="button"
            data-testid="resume-featured-dossier-btn"
            onClick={() => onSelectWorkflowRun(featuredPendingWorkflow.id)}
            className="orcia-ds-btn-primary"
            style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
          >
            <OrciaIcon name="play" />
            <span>{copy.reviewPendingDossierBtn}</span>
          </button>
        ) : null}
      </div>

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
            className="orcia-ds-btn-secondary"
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
    </div>
  );
}
