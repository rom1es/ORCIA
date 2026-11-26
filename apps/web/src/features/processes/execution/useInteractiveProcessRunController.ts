import type { ProcessPendingRunItemResponse } from "@orcia/api-client";
import type { UiAgentTraceEventItem } from "@orcia/ui";
import { useEffect, useRef, useState } from "react";
import { useI18n } from "../../../i18n";
import {
  extractLocalizedApiError,
  resolveLocalizedClientError,
} from "../../../lib/formatRfc9457ErrorToBanner";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";
import { useReflexiveExecutionController } from "../../shared/useReflexiveExecutionController";
import { useSourceLineInspector } from "../../shared/useSourceLineInspector";
import { buildGoalDrivenExecutionPayload } from "./interactiveRunGoalPayload";
import {
  executeAcceptAndSignHitl,
  executeApproveSubStep,
  executeRejectAndLoopHitl,
  executeSuspendSlaHitl,
} from "./interactiveRunHitlActions";
import {
  applySnapshotContentUpdate,
  hydrateOrStartWorkflowRun,
} from "./interactiveRunSyncHelpers";
import {
  buildInitialArtifactMarkdown,
  buildWritePreviewExecutionPayload,
  extractAgentSlugFromRef,
  formatAgentHumanLabel,
  mapBackendRunStatusToDrawerStatus,
  simpleHashHex,
  type InteractiveProcessDrawerStatus,
} from "./interactiveRunFormatters";

export {
  extractAgentSlugFromRef,
  formatAgentHumanLabel,
  type InteractiveProcessDrawerStatus,
};

export function useInteractiveProcessRunController(
  workflow: WorkflowDefinitionV2Item,
  isFr: boolean,
  workspaceId?: string,
  initialPendingRun?: ProcessPendingRunItemResponse | null,
  onRunStateChanged?: () => void,
) {
  const { locale, dictionary } = useI18n();
  const processCopy = dictionary.categoryAControllers.processes;
  const enabledSubSteps = workflow.sub_steps.filter((s) => s.enabled);
  const fallbackStatus: InteractiveProcessDrawerStatus =
    workflow.execution_mode === "external_delegated"
      ? "WAITING_EXTERNAL_GATE"
      : "WAITING_SUBSTEP_HITL";
  const isGoalDriven = workflow.orchestration_type === "non_deterministic";
  const storageKey = `orcia.reflexive_exec.process.${workflow.id}.v1`;
  const actorSlug = extractAgentSlugFromRef(workflow.agent_ref);

  const [runId, setRunId] = useState<string>(
    () => initialPendingRun?.run_id ?? `run-${workflow.id}-01`,
  );
  const [iteration, setIteration] = useState<number>(1);
  const [reentryMode, setReentryMode] = useState<"initial" | "corrections">("initial");
  const [currentSubIndex, setCurrentSubIndex] = useState<number>(0);
  const [status, setStatus] = useState<InteractiveProcessDrawerStatus>(() =>
    initialPendingRun
      ? mapBackendRunStatusToDrawerStatus(initialPendingRun.status, fallbackStatus)
      : fallbackStatus,
  );

  const currentSubStep = enabledSubSteps[currentSubIndex] ?? enabledSubSteps[0];
  const agentLabel = formatAgentHumanLabel(workflow.agent_ref, locale);

  const [artifactMarkdown, setArtifactMarkdown] = useState<string>(() =>
    buildInitialArtifactMarkdown(
      workflow.title,
      currentSubStep?.name ?? processCopy.executionDefaultName,
      agentLabel,
      locale,
    ),
  );
  const [artifactSha256, setArtifactSha256] = useState<string>(() =>
    simpleHashHex(artifactMarkdown),
  );
  const [isEditingDiff, setIsEditingDiff] = useState<boolean>(false);
  const [returnLoopTargetStep, setReturnLoopTargetStep] = useState<string>("02");
  const [returnLoopRemarks, setReturnLoopRemarks] = useState<string>(
    processCopy.defaultReturnRemarks,
  );
  const [signedTokenPreview, setSignedTokenPreview] = useState<string | null>(null);
  const [statusBanner, setStatusBanner] = useState<string | null>(null);
  const [hasError, setHasError] = useState<boolean>(false);
  const [isStartingRun, setIsStartingRun] = useState<boolean>(true);
  const [isSubmittingDecision, setIsSubmittingDecision] = useState<boolean>(false);
  const startRunPromiseRef = useRef<Promise<string | null> | null>(null);
  const hasPersistedServerRunRef = useRef<boolean>(false);
  const onRunStateChangedRef = useRef(onRunStateChanged);
  onRunStateChangedRef.current = onRunStateChanged;
  const [inlineRunTraceEvents, setInlineRunTraceEvents] = useState<
    readonly UiAgentTraceEventItem[]
  >([]);

  const inspector = useSourceLineInspector({ locale, workspaceId, onFeedback: setStatusBanner });
  const reflexive = useReflexiveExecutionController({
    storageKey,
    locale,
    initialExecutionId: initialPendingRun?.reflexive_execution_id ?? null,
    onFeedback: setStatusBanner,
    onSnapshotUpdated: (mapped) => {
      applySnapshotContentUpdate(mapped.finalMarkdown, mapped.artifactSha256, setArtifactMarkdown, setArtifactSha256);
      setStatus((prev) =>
        mapped.status === "WAITING_WRITE_PREVIEW"
          ? "WAITING_WRITE_PREVIEW"
          : mapped.status === "COMPLETED" && prev === "WAITING_WRITE_PREVIEW"
            ? "WAITING_FINAL_ANCHOR"
            : prev,
      );
    },
  });

  useEffect(() => {
    let cancelled = false;
    setIsStartingRun(true);
    setHasError(false);

    const startPromise = (async (): Promise<string | null> => {
      try {
        const resolvedRunId = await hydrateOrStartWorkflowRun({
          locale,
          workflow,
          workspaceId,
          initialPendingRun,
          isCancelled: () => cancelled,
          callbacks: {
            actorSlug,
            fallbackStatus,
            refreshSnapshot: reflexive.refreshSnapshot,
            setRunId,
            setStatus,
            setCurrentSubIndex,
            setIteration,
            setReentryMode,
            setInlineRunTraceEvents,
            setArtifactMarkdown,
            setArtifactSha256,
            markServerRunPersisted: () => { hasPersistedServerRunRef.current = true; },
          },
        });
        if (!cancelled && resolvedRunId && !initialPendingRun) {
          onRunStateChangedRef.current?.();
        }
        return resolvedRunId;
      } catch (err: unknown) {
        if (!cancelled) {
          const extracted = extractLocalizedApiError(err, locale, "ERR_CLIENT_PROCESS_RUN_START");
          setHasError(true);
          setStatusBanner(
            resolveLocalizedClientError("ERR_CLIENT_PROCESS_RUN_START", locale, { detail: extracted.errorMessage }),
          );
        }
        return null;
      } finally {
        if (!cancelled) setIsStartingRun(false);
      }
    })();

    startRunPromiseRef.current = startPromise;
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflow.id, initialPendingRun?.run_id]);

  const handleLaunchLiveInvestigation = () => {
    void reflexive.startExecution(buildGoalDrivenExecutionPayload({
      actorSlug,
      objective: workflow.reflexive_objective || workflow.title,
      workspaceId,
      runInBackground: true,
    }));
  };

  const handleStageExternalWritePreview = () => {
    void reflexive.startExecution(buildWritePreviewExecutionPayload(
      actorSlug, workflow.id, workflow.title, workflow.reflexive_objective, isFr, workspaceId,
    ));
  };

  const handleApproveCurrentSubStep = () => {
    executeApproveSubStep({
      locale, workflowTitle: workflow.title, enabledSubSteps, currentSubIndex, currentSubStep,
      status, artifactSha256, writePreviewPrompt: processCopy.writePreviewPrompt,
      stepApprovedAdvanceTpl: processCopy.stepApprovedAdvance,
      readyForFinalSignoff: processCopy.readyForFinalSignoff,
      setSignedTokenPreview, setCurrentSubIndex, setArtifactMarkdown, setArtifactSha256,
      setStatus, setStatusBanner,
    });
  };

  const handleAction1AcceptAndSign = async (): Promise<void> => {
    if (isStartingRun || isSubmittingDecision) return;
    setIsSubmittingDecision(true);
    setHasError(false);
    try {
      await executeAcceptAndSignHitl({
        locale, runId, actorSlug,
        startRunPromise: startRunPromiseRef.current,
        hasPersistedServerRun: hasPersistedServerRunRef.current,
        deliveredBanner: processCopy.deliverableApprovedBanner,
        setStatus, setHasError, setStatusBanner,
        onRunStateChanged: onRunStateChangedRef.current,
      });
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  const handleAction2SaveAmendedDiff = () => {
    setArtifactSha256(simpleHashHex(artifactMarkdown));
    setIsEditingDiff(false);
    setStatusBanner(processCopy.deliverableDiffSavedBanner);
  };

  const handleAction3RejectAndLoop = async (): Promise<void> => {
    await executeRejectAndLoopHitl({
      locale, runId, actorSlug, iteration,
      targetStepNum: returnLoopTargetStep,
      correctionRemarks: returnLoopRemarks,
      artifactMarkdown,
      loopMarkdownTpl: processCopy.returnLoopMarkdown,
      loopBannerTpl: processCopy.returnLoopBanner,
      hasPersistedServerRun: hasPersistedServerRunRef.current,
      setIteration, setReentryMode, setCurrentSubIndex, setStatus,
      setArtifactMarkdown, setArtifactSha256, setHasError, setStatusBanner,
      onRunStateChanged: onRunStateChangedRef.current,
    });
  };

  const handleAction4SuspendSla = (bannerText: string) => {
    setStatus("SLA_SUSPENDED");
    setStatusBanner(bannerText);
    void executeSuspendSlaHitl({
      locale, runId, actorSlug,
      hasPersistedServerRun: hasPersistedServerRunRef.current,
      setHasError, setStatusBanner,
      onRunStateChanged: onRunStateChangedRef.current,
    });
  };

  const effectiveEvents =
    reflexive.events.length > 0 ? reflexive.events : inlineRunTraceEvents;
  const effectiveTraceStatus =
    reflexive.status ?? (effectiveEvents.length > 0 ? "COMPLETED" : null);

  return {
    dictionary, enabledSubSteps, isGoalDriven, runId, iteration, reentryMode,
    currentSubIndex, currentSubStep, status, setStatus, agentLabel,
    artifactMarkdown, setArtifactMarkdown, artifactSha256, isEditingDiff, setIsEditingDiff,
    returnLoopTargetStep, setReturnLoopTargetStep, returnLoopRemarks, setReturnLoopRemarks,
    signedTokenPreview, statusBanner, hasError, isStartingRun, isSubmittingDecision,
    setStatusBanner, inspector, reflexive, effectiveEvents, effectiveTraceStatus,
    handleLaunchLiveInvestigation, handleStageExternalWritePreview, handleApproveCurrentSubStep,
    handleAction1AcceptAndSign, handleAction2SaveAmendedDiff, handleAction3RejectAndLoop,
    handleAction4SuspendSla,
  };
}
