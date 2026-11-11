import { AgentExecutionTrace, SourceLineInspectorDrawer } from "@orcia/ui";
import React from "react";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";
import { InteractiveRunDeliverableAndHitlPanels } from "./InteractiveRunDeliverableAndHitlPanels";
import { InteractiveRunDrawerHeader } from "./InteractiveRunDrawerHeader";
import {
  formatAgentHumanLabel,
  useInteractiveProcessRunController,
  type InteractiveProcessDrawerStatus,
} from "./useInteractiveProcessRunController";

export { formatAgentHumanLabel };

export interface InteractiveRunDrawerProps {
  workflow: WorkflowDefinitionV2Item;
  onClose: () => void;
  isFr: boolean;
}

export function InteractiveRunDrawer({
  workflow,
  onClose,
  isFr,
}: InteractiveRunDrawerProps) {
  const ctrl = useInteractiveProcessRunController(workflow, isFr);
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
    setStatusBanner,
    inspector,
    reflexive,
    effectiveEvents,
    effectiveTraceStatus,
    handleLaunchLiveInvestigation,
    handleStageExternalWritePreview,
    handleApproveCurrentSubStep,
    handleAction2SaveAmendedDiff,
    handleAction3RejectAndLoop,
  } = ctrl;

  const idempotencyKey = `${runId}:${currentSubStep?.id ?? "step"}:iter-${iteration}`;
  const s3Uri = `s3://orcia-artifacts/${runId}/${currentSubStep?.id ?? "step"}/iter-${iteration}/${artifactSha256.slice(0, 16)}.md`;

  const statusHumanLabel: Record<InteractiveProcessDrawerStatus, string> = {
    WAITING_EXTERNAL_GATE: isFr
      ? "En attente de réalisation (IDE / Git)"
      : "Waiting for external IDE/Git",
    WAITING_SUBSTEP_HITL: isFr
      ? "En attente de votre validation"
      : "Waiting for your review",
    WAITING_WRITE_PREVIEW: isFr
      ? "Confirmation avant publication externe"
      : "Confirm external publication",
    WAITING_FINAL_ANCHOR: isFr
      ? "Prêt pour validation finale du dossier"
      : "Ready for final approval",
    COMPLETED_APPROVED: isFr
      ? "Dossier validé et publié"
      : "Approved and published",
    RETURN_LOOP_TRIGGERED: isFr
      ? `Renvoyé pour corrections (Cycle ${iteration})`
      : `Returned for corrections (Cycle ${iteration})`,
    SLA_SUSPENDED: isFr ? "Dossier mis en pause" : "On hold",
  };

  return (
    <section
      data-testid="interactive-run-hitl-drawer"
      className="orcia-bento-card flex flex-col gap-3.5"
      style={{ borderLeft: "4px solid var(--color-primary-cobalt)" }}
    >
      <div className="sr-only" aria-hidden="true">
        <span data-testid="run-drawer-status-badge">{status}</span>
        <span data-testid="run-drawer-idempotency-key">{idempotencyKey}</span>
        <span data-testid="run-drawer-reentry-mode">
          mode: {reentryMode} (iter-{iteration})
        </span>
        <span data-testid="claim-check-s3-uri">{s3Uri}</span>
        <span data-testid="claim-check-sha256">
          SHA-256: {artifactSha256.slice(0, 16)}
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
                  {isFr ? `Étape ${idx + 1}` : `Step ${idx + 1}`}
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
          role="status"
          data-testid="run-drawer-feedback-banner"
          className="rounded border px-3 py-2 text-xs font-medium"
          style={{
            backgroundColor: "var(--color-gate-emerald-bg)",
            borderColor: "var(--color-gate-emerald)",
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
          setStatusBanner(
            isFr
              ? "Travaux externes reçus (Pull Request détectée) : les contrôles automatiques de conformité sont validés."
              : "External work received: automated quality checks passed.",
          );
        }}
        onApproveCurrentSubStep={handleApproveCurrentSubStep}
        onAction1AcceptAndSign={() => {
          setStatus("COMPLETED_APPROVED");
          setStatusBanner(
            isFr
              ? "Dossier validé et signé : le livrable final est enregistré et publié."
              : "Deliverable approved, signed, and published.",
          );
        }}
        onAction2SaveAmendedDiff={handleAction2SaveAmendedDiff}
        onAction3RejectAndLoop={handleAction3RejectAndLoop}
        onAction4SuspendSla={() => {
          setStatus("SLA_SUSPENDED");
          setStatusBanner(
            isFr
              ? "Dossier mis en pause : le suivi de délai est suspendu jusqu'à votre reprise."
              : "Process paused: SLA timer suspended until resumed.",
          );
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
