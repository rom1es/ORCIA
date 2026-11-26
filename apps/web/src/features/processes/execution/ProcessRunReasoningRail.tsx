import {
  AgentExecutionTrace,
  OrciaDataCard,
  OrciaIcon,
  type AgentExecutionTraceLabels,
  type UiAgentTraceEventItem,
  type UiReflexivePendingWritePreview,
  type UiReflexiveSessionStatus,
  type UiSourceLineInspectTarget,
} from "@orcia/ui";
import React from "react";
import { resolveDictionaryForFlag } from "../../../i18n";

export interface ProcessRunReasoningRailProps {
  readonly isFr: boolean;
  readonly isGoalDriven?: boolean;
  readonly traceStatus: UiReflexiveSessionStatus | null;
  readonly events: readonly UiAgentTraceEventItem[];
  readonly pendingWritePreview?: UiReflexivePendingWritePreview | null;
  readonly traceLabels: AgentExecutionTraceLabels;
  readonly onInspectLines: (target: UiSourceLineInspectTarget) => void;
  readonly onSynthesizeNow: () => void;
  readonly onApproveWrite: (previewId: string) => void;
  readonly onRejectWrite: (previewId: string) => void;
  readonly onLaunchLiveInvestigation?: () => void;
  readonly onStageExternalWritePreview?: () => void;
}

export function ProcessRunReasoningRail({
  isFr,
  isGoalDriven = false,
  traceStatus,
  events,
  pendingWritePreview = null,
  traceLabels,
  onInspectLines,
  onSynthesizeNow,
  onApproveWrite,
  onRejectWrite,
  onLaunchLiveInvestigation,
  onStageExternalWritePreview,
}: ProcessRunReasoningRailProps): React.JSX.Element {
  const copy = resolveDictionaryForFlag(isFr).processVsmExecutionUi.execution;
  const hasTrace = Boolean(traceStatus && (events.length > 0 || pendingWritePreview));

  return (
    <OrciaDataCard
      testId="process-run-reasoning-rail"
      icon="assistant"
      title={copy.reasoningRailTitle}
      actions={
        isGoalDriven && (onLaunchLiveInvestigation || onStageExternalWritePreview) ? (
          <div className="flex flex-wrap gap-1.5">
            {onLaunchLiveInvestigation ? (
              <button
                type="button"
                data-testid="process-launch-live-investigation-btn"
                onClick={onLaunchLiveInvestigation}
                className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
              >
                <OrciaIcon name="play" size={12} />
                <span>{copy.launchLiveAnalysisBtn}</span>
              </button>
            ) : null}
            {onStageExternalWritePreview ? (
              <button
                type="button"
                data-testid="process-request-write-preview-btn"
                onClick={onStageExternalWritePreview}
                className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
              >
                {copy.stageExternalPubBtn}
              </button>
            ) : null}
          </div>
        ) : undefined
      }
    >
      {hasTrace && traceStatus ? (
        <AgentExecutionTrace
          status={traceStatus}
          events={events}
          pendingWritePreview={pendingWritePreview}
          labels={traceLabels}
          defaultCollapsedWhenCompleted={true}
          onInspectLines={onInspectLines}
          onSynthesizeNow={onSynthesizeNow}
          onApproveWrite={onApproveWrite}
          onRejectWrite={onRejectWrite}
        />
      ) : (
        <p
          data-testid="focus-reasoning-empty-note"
          className="m-0 text-xs"
          style={{ color: "var(--color-text-secondary)" }}
        >
          {copy.reasoningEmptyNote}
        </p>
      )}
    </OrciaDataCard>
  );
}
