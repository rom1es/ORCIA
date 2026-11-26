import {
  OrciaAlertBanner,
  OrciaPageHeader,
  OrciaTabStrip,
  SourceLineInspectorDrawer,
  StatusBadge,
  useResponsiveBreakpoint,
} from "@orcia/ui";
import React, { useMemo, useState } from "react";
import { useOptionalPlatformSetup } from "../../../components/platformSetupStore";
import { useShellNavigation } from "../../../components/ShellContainer";
import { resolveEffectiveWorkspaceId } from "../../../components/shellScopeOptions";
import { useI18n } from "../../../i18n";
import { useAuthSessionStore } from "../../../stores/authSessionStore";
import {
  loadPersistedWorkflowsV2,
  type WorkflowDefinitionV2Item,
} from "../processStudioV2Data";
import {
  buildFallbackFocusWorkflow,
  buildStatusHumanLabelMap,
} from "./interactiveRunFormatters";
import { ProcessRunActionBanner } from "./ProcessRunActionBanner";
import { ProcessRunArtifactPane } from "./ProcessRunArtifactPane";
import { ProcessRunReasoningRail } from "./ProcessRunReasoningRail";
import { useInteractiveProcessRunController } from "./useInteractiveProcessRunController";

export interface ProcessRunFocusReviewPageProps {
  readonly runId: string;
}

export function ProcessRunFocusReviewPage({
  runId,
}: ProcessRunFocusReviewPageProps): React.JSX.Element {
  const { locale, isFr, dictionary } = useI18n();
  const { activeScopeId, navigateToRoute } = useShellNavigation();
  const setupCtx = useOptionalPlatformSetup();
  const authEmail = useAuthSessionStore((s) => s.email);
  const authDisplayName = useAuthSessionStore((s) => s.displayName);
  const { isDesktop } = useResponsiveBreakpoint();
  const [compactTab, setCompactTab] = useState<"artifact" | "reasoning">("artifact");
  const [humanAnchorValue, setHumanAnchorValue] = useState<string>("");

  const activeWorkspaceId = resolveEffectiveWorkspaceId(
    activeScopeId,
    setupCtx?.workspaces ?? [],
    authEmail,
  );
  const execCopy = dictionary.processVsmExecutionUi.execution;

  const knownWorkflows = useMemo(() => loadPersistedWorkflowsV2(locale), [locale]);
  const fallbackWorkflow = useMemo<WorkflowDefinitionV2Item>(
    () => knownWorkflows[0] ?? buildFallbackFocusWorkflow(runId, execCopy.focusReviewTitle),
    [knownWorkflows, runId, execCopy.focusReviewTitle],
  );
  const [resolvedWorkflow, setResolvedWorkflow] = useState<WorkflowDefinitionV2Item>(
    fallbackWorkflow,
  );

  const ctrl = useInteractiveProcessRunController(
    resolvedWorkflow,
    isFr,
    activeWorkspaceId || undefined,
    null,
    undefined,
    runId,
    knownWorkflows,
    setResolvedWorkflow,
  );

  const statusHumanLabel = buildStatusHumanLabelMap(execCopy, ctrl.iteration);

  const statusTone =
    ctrl.status === "COMPLETED_APPROVED"
      ? "emerald"
      : ctrl.status === "FAILED_GATES"
        ? "crimson"
        : ctrl.status === "RUNNING" || ctrl.status === "SLA_SUSPENDED"
          ? "cobalt"
          : "amber";

  const isReflexiveRunning =
    ctrl.reflexive.status === "RUNNING" || ctrl.reflexive.status === "SYNTHESIZING";

  const idempotencyKey = `${ctrl.runId}:${ctrl.currentSubStep?.id ?? "step"}:iter-${ctrl.iteration}`;
  const s3Uri = `s3://orcia-artifacts/${ctrl.runId}/${ctrl.currentSubStep?.id ?? "step"}/iter-${ctrl.iteration}/${ctrl.artifactSha256.slice(0, 16)}.md`;

  const alertNode = ctrl.runNotFound ? (
    <OrciaAlertBanner tone="crimson" role="alert" testId="focus-run-not-found-banner">
      {execCopy.runNotFoundBanner}
    </OrciaAlertBanner>
  ) : ctrl.statusBanner ? (
    <OrciaAlertBanner
      tone={ctrl.hasError ? "crimson" : "emerald"}
      role={ctrl.hasError ? "alert" : "status"}
      testId="run-drawer-feedback-banner"
    >
      {ctrl.statusBanner}
    </OrciaAlertBanner>
  ) : null;

  const artifactPane = (
    <ProcessRunArtifactPane
      workflow={resolvedWorkflow}
      isFr={isFr}
      currentSubStep={ctrl.currentSubStep}
      artifactMarkdown={ctrl.artifactMarkdown}
      isEditingDiff={ctrl.isEditingDiff}
      traceEvents={ctrl.effectiveEvents}
      onChangeArtifactMarkdown={ctrl.setArtifactMarkdown}
      onSetIsEditingDiff={ctrl.setIsEditingDiff}
      onSaveAmendedDiff={ctrl.handleAction2SaveAmendedDiff}
      onInspectSourceLines={ctrl.inspector.openInspectTarget}
    />
  );

  const reasoningRail = (
    <ProcessRunReasoningRail
      isFr={isFr}
      isGoalDriven={ctrl.isGoalDriven}
      traceStatus={ctrl.effectiveTraceStatus}
      events={ctrl.effectiveEvents}
      pendingWritePreview={ctrl.reflexive.pendingWritePreview}
      traceLabels={ctrl.dictionary.executionTrace}
      onInspectLines={ctrl.inspector.openInspectTarget}
      onSynthesizeNow={() => {
        void ctrl.reflexive.synthesizeNow();
      }}
      onApproveWrite={(previewId) => {
        void ctrl.reflexive.approveWrite(previewId);
      }}
      onRejectWrite={(previewId) => {
        void ctrl.reflexive.rejectWrite(previewId);
      }}
      onLaunchLiveInvestigation={ctrl.handleLaunchLiveInvestigation}
      onStageExternalWritePreview={ctrl.handleStageExternalWritePreview}
    />
  );

  return (
    <section
      data-testid="process-run-focus-review-page"
      data-run-id={ctrl.runId}
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <div className="sr-only" aria-hidden="true">
        <span data-testid="run-drawer-status-badge">{ctrl.status}</span>
        <span data-testid="run-drawer-idempotency-key">{idempotencyKey}</span>
        <span data-testid="run-drawer-reentry-mode">
          {`mode: ${ctrl.reentryMode} (iter-${ctrl.iteration})`}
        </span>
        <span data-testid="claim-check-s3-uri">{s3Uri}</span>
        <span data-testid="claim-check-sha256">
          {`SHA-256: ${ctrl.artifactSha256.slice(0, 16)}`}
        </span>
      </div>

      <OrciaPageHeader
        testId="process-run-focus-header"
        icon="processes"
        title={resolvedWorkflow.title}
        subtitle={`${ctrl.agentLabel} · ${ctrl.runId}`}
        contextBadge={<StatusBadge tone={statusTone} label={statusHumanLabel[ctrl.status]} />}
        secondaryActions={
          <>
            {isReflexiveRunning ? (
              <button
                type="button"
                data-testid="process-stop-execution-btn"
                onClick={() => {
                  void ctrl.reflexive.cancelExecution();
                }}
                className="orcia-ds-btn orcia-ds-btn-danger orcia-ds-btn-sm orcia-ds-nowrap"
              >
                {execCopy.stopBtn}
              </button>
            ) : null}
            <button
              type="button"
              data-testid="focus-review-back-to-processes-btn"
              onClick={() => navigateToRoute("/processes")}
              className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm orcia-ds-nowrap"
            >
              {execCopy.backToProcessesBtn}
            </button>
          </>
        }
        alertSlot={alertNode}
      />

      {!ctrl.runNotFound ? (
        <>
          <ProcessRunActionBanner
            workflow={resolvedWorkflow}
            isFr={isFr}
            status={ctrl.status}
            statusLabel={statusHumanLabel[ctrl.status]}
            currentSubStep={ctrl.currentSubStep}
            iteration={ctrl.iteration}
            reentryMode={ctrl.reentryMode}
            signedTokenPreview={ctrl.signedTokenPreview}
            returnLoopTargetStep={ctrl.returnLoopTargetStep}
            returnLoopRemarks={ctrl.returnLoopRemarks}
            isStartingRun={ctrl.isStartingRun}
            isSubmittingDecision={ctrl.isSubmittingDecision}
            isSticky={true}
            authorName={authDisplayName ?? authEmail ?? ""}
            humanAnchorValue={humanAnchorValue}
            humanAnchorLabels={ctrl.dictionary.humanAnchor}
            onChangeHumanAnchorValue={setHumanAnchorValue}
            onSimulateExternalWebhook={() => {
              ctrl.setStatus("WAITING_FINAL_ANCHOR");
              ctrl.setStatusBanner(execCopy.externalWorkReceivedBanner);
            }}
            onApproveCurrentSubStep={() => {
              void ctrl.handleApproveCurrentSubStep();
            }}
            onAction1AcceptAndSign={() => {
              void ctrl.handleAction1AcceptAndSign();
            }}
            onAction3RejectAndLoop={() => {
              void ctrl.handleAction3RejectAndLoop();
            }}
            onAction4SuspendSla={() => {
              ctrl.handleAction4SuspendSla(execCopy.processPausedBanner);
            }}
            onChangeReturnLoopTarget={ctrl.setReturnLoopTargetStep}
            onChangeReturnLoopRemarks={ctrl.setReturnLoopRemarks}
          />

          {isDesktop ? (
            <div
              data-testid="focus-review-split-layout"
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1.85fr) minmax(320px, 1fr)",
                gap: "16px",
                alignItems: "start",
              }}
            >
              <div data-testid="focus-review-zone2-artifact">{artifactPane}</div>
              <div data-testid="focus-review-zone3-reasoning">{reasoningRail}</div>
            </div>
          ) : (
            <div data-testid="focus-review-compact-layout" className="flex flex-col gap-3">
              <OrciaTabStrip<"artifact" | "reasoning">
                testId="focus-review-compact-tabs"
                ariaLabel={execCopy.focusMobileTabsAriaLabel}
                variant="underline"
                activeTabId={compactTab}
                onSelectTab={setCompactTab}
                tabs={[
                  {
                    key: "artifact",
                    label: execCopy.mobileTabArtifactLabel,
                    icon: "document",
                    testId: "focus-compact-tab-artifact",
                  },
                  {
                    key: "reasoning",
                    label: execCopy.mobileTabReasoningLabel,
                    icon: "assistant",
                    testId: "focus-compact-tab-reasoning",
                  },
                ]}
              />
              {compactTab === "artifact" ? (
                <div data-testid="focus-review-zone2-artifact">{artifactPane}</div>
              ) : (
                <div data-testid="focus-review-zone3-reasoning">{reasoningRail}</div>
              )}
            </div>
          )}
        </>
      ) : null}

      <SourceLineInspectorDrawer
        open={ctrl.inspector.inspectorState.open}
        onOpenChange={ctrl.inspector.setInspectorOpen}
        resourceUri={ctrl.inspector.inspectorState.resourceUri}
        displayFilename={ctrl.inspector.inspectorState.displayFilename}
        fileBadgeCode={ctrl.inspector.inspectorState.fileBadgeCode}
        startLine={ctrl.inspector.inspectorState.startLine}
        endLine={ctrl.inspector.inspectorState.endLine}
        totalLines={ctrl.inspector.inspectorState.totalLines}
        lines={ctrl.inspector.inspectorState.lines}
        isLoading={ctrl.inspector.inspectorState.isLoading}
        redacted={ctrl.inspector.inspectorState.redacted}
        redactedReason={ctrl.inspector.inspectorState.redactedReason}
        permissionRequestHint={ctrl.inspector.inspectorState.permissionRequestHint}
        errorMessage={ctrl.inspector.inspectorState.errorMessage}
        copiedFeedback={ctrl.inspector.inspectorState.copiedFeedback}
        labels={ctrl.dictionary.sourceLineInspector}
        onCopySlice={ctrl.inspector.copyCurrentSlice}
      />
    </section>
  );
}
