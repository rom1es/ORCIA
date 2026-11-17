import { OrciaIcon } from "@orcia/ui";
import React from "react";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";
import type { InteractiveProcessDrawerStatus } from "./useInteractiveProcessRunController";

export interface InteractiveRunDrawerHeaderProps {
  readonly workflow: WorkflowDefinitionV2Item;
  readonly isFr: boolean;
  readonly isGoalDriven: boolean;
  readonly status: InteractiveProcessDrawerStatus;
  readonly statusLabel: string;
  readonly reentryMode: "initial" | "corrections";
  readonly iteration: number;
  readonly agentLabel: string;
  readonly isReflexiveRunning: boolean;
  readonly onLaunchLiveInvestigation: () => void;
  readonly onStageExternalWritePreview: () => void;
  readonly onStopReflexive: () => void;
  readonly onCloseDrawer: () => void;
}

export function InteractiveRunDrawerHeader({
  workflow,
  isFr,
  isGoalDriven,
  status,
  statusLabel,
  reentryMode,
  iteration,
  agentLabel,
  isReflexiveRunning,
  onLaunchLiveInvestigation,
  onStageExternalWritePreview,
  onStopReflexive,
  onCloseDrawer,
}: InteractiveRunDrawerHeaderProps): React.JSX.Element {
  return (
    <div className="flex flex-wrap items-start justify-between gap-2.5">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="rounded px-2.5 py-0.5 text-xs font-semibold"
            style={{
              backgroundColor:
                status === "COMPLETED_APPROVED"
                  ? "var(--color-gate-emerald-bg)"
                  : status === "RETURN_LOOP_TRIGGERED"
                    ? "var(--color-arbitration-bg)"
                    : "var(--color-action-primary-subtle)",
              color:
                status === "COMPLETED_APPROVED"
                  ? "var(--color-gate-emerald)"
                  : status === "RETURN_LOOP_TRIGGERED"
                    ? "var(--color-arbitration-amber)"
                    : "var(--color-primary-cobalt)",
            }}
          >
            {statusLabel}
          </span>
          {reentryMode === "corrections" ? (
            <span
              className="rounded px-2 py-0.5 text-xs font-semibold"
              style={{
                backgroundColor: "var(--color-arbitration-bg)",
                color: "var(--color-arbitration-amber)",
              }}
            >
              {isFr
                ? `Cycle de correction n°${iteration}`
                : `Correction cycle #${iteration}`}
            </span>
          ) : null}
          <span
            style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}
          >
            {agentLabel}
          </span>
        </div>
        <h3 style={{ margin: "6px 0 0 0", fontSize: "17px" }}>
          {workflow.title}
        </h3>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {isGoalDriven ? (
          <>
            <button
              type="button"
              data-testid="process-launch-live-investigation-btn"
              onClick={onLaunchLiveInvestigation}
              className="orcia-ds-btn-secondary text-xs"
            >
              <OrciaIcon name="play" />{" "}
              {isFr ? "Relancer l'analyse en direct" : "Run live analysis"}
            </button>
            <button
              type="button"
              data-testid="process-request-write-preview-btn"
              onClick={onStageExternalWritePreview}
              className="orcia-ds-btn-secondary text-xs"
            >
              {isFr
                ? "Préparer la publication externe"
                : "Stage external publication"}
            </button>
          </>
        ) : null}
        {isReflexiveRunning ? (
          <button
            type="button"
            data-testid="process-stop-execution-btn"
            onClick={onStopReflexive}
            className="orcia-ds-btn-danger text-xs"
          >
            <OrciaIcon name="stopSquare" /> {isFr ? "Arrêter" : "Stop"}
          </button>
        ) : null}
        <button
          type="button"
          data-testid="close-interactive-run-drawer-btn"
          onClick={onCloseDrawer}
          className="orcia-ds-btn-secondary"
        >
          {isFr ? "✕ Refermer le dossier" : "✕ Close"}
        </button>
      </div>
    </div>
  );
}
