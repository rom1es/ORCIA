import type { ProcessPendingRunItemResponse } from "@orcia/api-client";
import { AgentExecutionTrace, SourceLineInspectorDrawer } from "@orcia/ui";
import React from "react";
import { formatI18nTemplate, resolveDictionaryForFlag } from "../../../i18n";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";
import { InteractiveRunDeliverableAndHitlPanels } from "./InteractiveRunDeliverableAndHitlPanels";
import { InteractiveRunDrawerHeader } from "./InteractiveRunDrawerHeader";
import {
  extractAgentSlugFromRef,
  formatAgentHumanLabel,
  useInteractiveProcessRunController,
  type InteractiveProcessDrawerStatus,
} from "./useInteractiveProcessRunController";

export { extractAgentSlugFromRef, formatAgentHumanLabel };

export interface InteractiveRunDrawerProps {
  workflow: WorkflowDefinitionV2Item;
  workspaceId?: string;
  initialPendingRun?: ProcessPendingRunItemResponse | null;
  onRunStateChanged?: () => void;
  onClose: () => void;
  isFr: boolean;
}

export function InteractiveRunDrawer({
  workflow,
  workspaceId,
  initialPendingRun = null,
  onRunStateChanged,
  onClose,
  isFr,
}: InteractiveRunDrawerProps) {
  const execCopy = resolveDictionaryForFlag(isFr).processVsmExecutionUi.execution;
  const ctrl = useInteractiveProcessRunController(
    workflow,
    isFr,
    workspaceId,
    initialPendingRun,
    onRunStateChanged,
  );
  const {
    dictionary,
    enabledSubSteps,
    isGoalDriven,
    runId,
    iteration,
    reentryMode,
    currentSubIndex,
    currentSubStep,
    status,
    setStatus,
    agentLabel,
    artifactMarkdown,
    setArtifactMarkdown,
    artifactSha256,
    isEditingDiff,
    setIsEditingDiff,
    returnLoopTargetStep,
    setReturnLoopTargetStep,
    returnLoopRemarks,
    setReturnLoopRemarks,
    signedTokenPreview,
    statusBanner,
    hasError,
    isStartingRun,
    isSubmittingDecision,
    setStatusBanner,
    inspector,
    reflexive,
    effectiveEvents,
    effectiveTraceStatus,
    handleLaunchLiveInvestigation,
    handleStageExternalWritePreview,
    handleApproveCurrentSubStep,
    handleAction1AcceptAndSign,
    handleAction2SaveAmendedDiff,
    handleAction3RejectAndLoop,
    handleAction4SuspendSla,
  } = ctrl;

  const idempotencyKey = `${runId}:${currentSubStep?.id ?? "step"}:iter-${iteration}`;
  const s3Uri = `s3://orcia-artifacts/${runId}/${currentSubStep?.id ?? "step"}/iter-${iteration}/${artifactSha256.slice(0, 16)}.md`;

  const statusHumanLabel: Record<InteractiveProcessDrawerStatus, string> = {
    RUNNING: execCopy.statusRunning,
    WAITING_EXTERNAL_GATE: execCopy.statusWaitingExternal,
    WAITING_SUBSTEP_HITL: execCopy.statusWaitingSubstepHitl,
    WAITING_WRITE_PREVIEW: execCopy.statusWaitingWritePreview,
    WAITING_FINAL_ANCHOR: execCopy.statusWaitingFinalAnchor,
    COMPLETED_APPROVED: execCopy.statusCompletedApproved,
    RETURN_LOOP_TRIGGERED: formatI18nTemplate(execCopy.statusReturnLoopTemplate, { iteration }),
    SLA_SUSPENDED: execCopy.statusSlaSuspended,
    FAILED_GATES: execCopy.statusFailedGates,
  };

  return (
    <section
      data-testid="interactive-run-hitl-drawer"
      className="orcia-bento-card flex flex-col gap-3.5"
    >
      <div className="sr-only" aria-hidden="true">
        <span data-testid="run-drawer-status-badge">{status}</span>
        <span data-testid="run-drawer-idempotency-key">{idempotencyKey}</span>
        <span data-testid="run-drawer-reentry-mode">
          {`mode: ${reentryMode} (iter-${iteration})`}
        </span>
        <span data-testid="claim-check-s3-uri">{s3Uri}</span>
        <span data-testid="claim-check-sha256">
          {`SHA-256: ${artifactSha256.slice(0, 16)}`}
        </span>
      </div>

      <InteractiveRunDrawerHeader
        workflow={workflow}
        isFr={isFr}
        isGoalDriven={isGoalDriven}
        status={status}
        statusLabel={statusHumanLabel[status]}
        reentryMode={reentryMode}
        iteration={iteration}
        agentLabel={agentLabel}
        isReflexiveRunning={
          reflexive.status === "RUNNING" || reflexive.status === "SYNTHESIZING"
        }
        onLaunchLiveInvestigation={handleLaunchLiveInvestigation}
        onStageExternalWritePreview={handleStageExternalWritePreview}
        onStopReflexive={() => {
          void reflexive.cancelExecution();
        }}
        onCloseDrawer={() => {
          reflexive.clearExecution();
          onClose();
        }}
      />

      {enabledSubSteps.length > 0 ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(${Math.max(enabledSubSteps.length, 1)}, minmax(140px, 1fr))`,
            gap: "8px",
          }}
        >
          {enabledSubSteps.map((sub, idx) => {
            const isDone =
              status === "COMPLETED_APPROVED" || idx < currentSubIndex;
            const isCurrent =
              idx === currentSubIndex && status !== "COMPLETED_APPROVED";
            return (
              <div
                key={sub.id}
                className="rounded border px-3 py-2"
                style={{
                  backgroundColor: isCurrent
                    ? "var(--color-action-primary-subtle)"
                    : isDone
                      ? "var(--color-gate-emerald-bg)"
                      : "var(--color-bg-elevated)",
                  borderColor: isCurrent
                    ? "var(--color-primary-cobalt)"
                    : isDone
                      ? "var(--color-gate-emerald)"
                      : "var(--color-border-subtle)",
                }}
              >
                <div
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    color: "var(--color-text-secondary)",
                  }}
                >
                  {isDone ? "✓ " : isCurrent ? "● " : ""}
                  {formatI18nTemplate(execCopy.stepBadgeTemplate, { index: idx + 1 })}
                </div>
                <div style={{ fontSize: "13px", fontWeight: 600 }}>
                  {sub.name}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}

      {statusBanner ? (
        <div
          role={hasError ? "alert" : "status"}
          data-testid="run-drawer-feedback-banner"
          className="rounded border px-3 py-2 text-xs font-medium"
          style={{
            backgroundColor: hasError
              ? "var(--color-arbitration-bg)"
              : "var(--color-gate-emerald-bg)",
            borderColor: hasError
              ? "var(--color-status-error)"
              : "var(--color-gate-emerald)",
            color: "var(--color-text-primary)",
          }}
        >
          {statusBanner}
        </div>
      ) : null}

      {effectiveTraceStatus &&
      (effectiveEvents.length > 0 || reflexive.pendingWritePreview) ? (
        <AgentExecutionTrace
          status={effectiveTraceStatus}
          events={effectiveEvents}
          pendingWritePreview={reflexive.pendingWritePreview}
          labels={dictionary.executionTrace}
          defaultCollapsedWhenCompleted={false}
          onInspectLines={inspector.openInspectTarget}
          onSynthesizeNow={() => {
            void reflexive.synthesizeNow();
          }}
          onApproveWrite={(previewId) => {
            void reflexive.approveWrite(previewId);
          }}
          onRejectWrite={(previewId) => {
            void reflexive.rejectWrite(previewId);
          }}
        />
      ) : null}

      <InteractiveRunDeliverableAndHitlPanels
        workflow={workflow}
        isFr={isFr}
        status={status}
        currentSubStep={currentSubStep}
        artifactMarkdown={artifactMarkdown}
        isEditingDiff={isEditingDiff}
        signedTokenPreview={signedTokenPreview}
        returnLoopTargetStep={returnLoopTargetStep}
        returnLoopRemarks={returnLoopRemarks}
        onChangeArtifactMarkdown={setArtifactMarkdown}
        onSetIsEditingDiff={setIsEditingDiff}
        onSimulateExternalWebhook={() => {
          setStatus("WAITING_FINAL_ANCHOR");
          setStatusBanner(execCopy.externalWorkReceivedBanner);
        }}
        isStartingRun={isStartingRun}
        isSubmittingDecision={isSubmittingDecision}
        onApproveCurrentSubStep={handleApproveCurrentSubStep}
        onAction1AcceptAndSign={handleAction1AcceptAndSign}
        onAction2SaveAmendedDiff={handleAction2SaveAmendedDiff}
        onAction3RejectAndLoop={() => {
          void handleAction3RejectAndLoop();
        }}
        onAction4SuspendSla={() => {
          handleAction4SuspendSla(execCopy.processPausedBanner);
        }}
        onChangeReturnLoopTarget={setReturnLoopTargetStep}
        onChangeReturnLoopRemarks={setReturnLoopRemarks}
      />

      <SourceLineInspectorDrawer
        open={inspector.inspectorState.open}
        onOpenChange={inspector.setInspectorOpen}
        resourceUri={inspector.inspectorState.resourceUri}
        displayFilename={inspector.inspectorState.displayFilename}
        fileBadgeCode={inspector.inspectorState.fileBadgeCode}
        startLine={inspector.inspectorState.startLine}
        endLine={inspector.inspectorState.endLine}
        totalLines={inspector.inspectorState.totalLines}
        lines={inspector.inspectorState.lines}
        isLoading={inspector.inspectorState.isLoading}
        redacted={inspector.inspectorState.redacted}
        redactedReason={inspector.inspectorState.redactedReason}
        permissionRequestHint={inspector.inspectorState.permissionRequestHint}
        errorMessage={inspector.inspectorState.errorMessage}
        copiedFeedback={inspector.inspectorState.copiedFeedback}
        labels={dictionary.sourceLineInspector}
        onCopySlice={inspector.copyCurrentSlice}
      />
    </section>
  );
}
