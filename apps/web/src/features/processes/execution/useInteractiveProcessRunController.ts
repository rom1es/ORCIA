import type { UiAgentTraceEventItem } from "@orcia/ui";
import { useEffect, useRef, useState } from "react";
import { useI18n } from "../../../i18n";
import {
  extractLocalizedApiError,
  resolveLocalizedClientError,
} from "../../../lib/formatRfc9457ErrorToBanner";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";
import { createProcessesApiClient } from "../studio/studioLabelsAndMappers";
import {
  mapApiTraceEventToUi,
  readPersistedReflexiveId,
} from "../../shared/reflexiveTraceMappers";
import { useReflexiveExecutionController } from "../../shared/useReflexiveExecutionController";
import { useSourceLineInspector } from "../../shared/useSourceLineInspector";
import { buildGoalDrivenExecutionPayload } from "./interactiveRunGoalPayload";
import {
  buildInitialArtifactMarkdown,
  buildSubStepAdvanceMarkdown,
  buildWritePreviewExecutionPayload,
  extractAgentSlugFromRef,
  formatAgentHumanLabel,
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
) {
  const { locale, dictionary } = useI18n();
  const processCopy = dictionary.categoryAControllers.processes;
  const enabledSubSteps = workflow.sub_steps.filter((s) => s.enabled);
  const isExternalGate = workflow.execution_mode === "external_delegated";
  const isGoalDriven = workflow.orchestration_type === "non_deterministic";
  const storageKey = `orcia.reflexive_exec.process.${workflow.id}.v1`;
  const actorSlug = extractAgentSlugFromRef(workflow.agent_ref);

  const [runId, setRunId] = useState<string>(() => `run-${workflow.id}-01`);
  const [iteration, setIteration] = useState<number>(1);
  const [reentryMode, setReentryMode] = useState<"initial" | "corrections">("initial");
  const [currentSubIndex, setCurrentSubIndex] = useState<number>(0);
  const [status, setStatus] = useState<InteractiveProcessDrawerStatus>(
    isExternalGate ? "WAITING_EXTERNAL_GATE" : "WAITING_SUBSTEP_HITL",
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
  const [isStartingRun, setIsStartingRun] = useState<boolean>(
    () => !readPersistedReflexiveId(storageKey),
  );
  const [isSubmittingDecision, setIsSubmittingDecision] = useState<boolean>(false);
  const startRunPromiseRef = useRef<Promise<string | null> | null>(null);
  const hasPersistedServerRunRef = useRef<boolean>(false);
  const [inlineRunTraceEvents, setInlineRunTraceEvents] = useState<
    readonly UiAgentTraceEventItem[]
  >([]);

  const inspector = useSourceLineInspector({ locale, workspaceId, onFeedback: setStatusBanner });
  const reflexive = useReflexiveExecutionController({
    storageKey,
    locale,
    onFeedback: setStatusBanner,
    onSnapshotUpdated: (mapped) => {
      if (mapped.finalMarkdown) {
        setArtifactMarkdown(mapped.finalMarkdown);
        setArtifactSha256(mapped.artifactSha256 || simpleHashHex(mapped.finalMarkdown));
      }
      if (mapped.status === "WAITING_WRITE_PREVIEW") {
        setStatus("WAITING_WRITE_PREVIEW");
      } else if (mapped.status === "COMPLETED" && status === "WAITING_WRITE_PREVIEW") {
        setStatus("WAITING_FINAL_ANCHOR");
      }
    },
  });

  useEffect(() => {
    const existingExecId = readPersistedReflexiveId(storageKey);
    if (existingExecId) {
      setIsStartingRun(false);
      return;
    }
    let cancelled = false;
    setIsStartingRun(true);
    setHasError(false);

    const startPromise = (async (): Promise<string | null> => {
      try {
        const res = await createProcessesApiClient(locale).startWorkflowV2Run(workflow.id, {
          inputs: { objective: workflow.title },
          iteration: 1,
          reentry_mode: "initial",
        });
        if (cancelled || !res?.run) return null;
        const resolvedRunId = res.run.run_id || `run-${workflow.id}-01`;
        setRunId(resolvedRunId);
        hasPersistedServerRunRef.current = Boolean(res.run.run_id);
        if (res.run.reflexive_execution_id) {
          await reflexive.refreshSnapshot(res.run.reflexive_execution_id);
        } else if (Array.isArray(res.run.trace_events) && res.run.trace_events.length > 0) {
          setInlineRunTraceEvents(res.run.trace_events.map((ev) => mapApiTraceEventToUi(ev, actorSlug)));
        } else if (isGoalDriven) {
          await reflexive.startExecution(
            buildGoalDrivenExecutionPayload({
              actorSlug,
              objective: workflow.reflexive_objective || workflow.title,
              workspaceId,
            }),
          );
        }
        return resolvedRunId;
      } catch (err: unknown) {
        if (!cancelled) {
          const extracted = extractLocalizedApiError(err, locale, "ERR_CLIENT_PROCESS_RUN_START");
          setHasError(true);
          setStatusBanner(
            resolveLocalizedClientError("ERR_CLIENT_PROCESS_RUN_START", locale, {
              detail: extracted.errorMessage,
            }),
          );
        }
        return null;
      } finally {
        if (!cancelled) setIsStartingRun(false);
      }
    })();

    startRunPromiseRef.current = startPromise;
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflow.id]);

  const handleLaunchLiveInvestigation = () => {
    void reflexive.startExecution(
      buildGoalDrivenExecutionPayload({
        actorSlug,
        objective: workflow.reflexive_objective || workflow.title,
        runInBackground: true,
      }),
    );
  };

  const handleStageExternalWritePreview = () => {
    void reflexive.startExecution(
      buildWritePreviewExecutionPayload(
        actorSlug,
        workflow.id,
        workflow.title,
        workflow.reflexive_objective,
        isFr,
      ),
    );
  };

  const handleApproveCurrentSubStep = () => {
    if (currentSubStep?.write_preview_required && status !== "WAITING_WRITE_PREVIEW") {
      setStatus("WAITING_WRITE_PREVIEW");
      setStatusBanner(processCopy.writePreviewPrompt);
      return;
    }
    if (status === "WAITING_WRITE_PREVIEW") {
      setSignedTokenPreview(`sat_${artifactSha256.slice(0, 16)}_hmac_ok`);
    }
    if (currentSubIndex + 1 < enabledSubSteps.length) {
      const nextIdx = currentSubIndex + 1;
      const nextSub = enabledSubSteps[nextIdx];
      setCurrentSubIndex(nextIdx);
      const nextMd = buildSubStepAdvanceMarkdown(
        workflow.title,
        nextSub?.name ?? "",
        nextSub?.output_description ?? "",
        locale,
      );
      setArtifactMarkdown(nextMd);
      setArtifactSha256(simpleHashHex(nextMd));
      setStatus(nextSub?.write_preview_required ? "WAITING_WRITE_PREVIEW" : "WAITING_SUBSTEP_HITL");
      setStatusBanner(
        processCopy.stepApprovedAdvance
          .replace("{step}", currentSubStep?.short_label ?? "")
          .replace("{nextStep}", nextSub?.short_label ?? ""),
      );
    } else {
      setStatus("WAITING_FINAL_ANCHOR");
      setStatusBanner(processCopy.readyForFinalSignoff);
    }
  };

  const handleAction1AcceptAndSign = async (): Promise<void> => {
    if (isStartingRun || isSubmittingDecision) return;
    setIsSubmittingDecision(true);
    setHasError(false);
    try {
      let resolvedRunId = runId;
      if (startRunPromiseRef.current) {
        const awaitedRunId = await startRunPromiseRef.current;
        if (awaitedRunId) resolvedRunId = awaitedRunId;
      }
      if (hasPersistedServerRunRef.current) {
        await createProcessesApiClient(locale).sendWorkflowV2HitlSignal(resolvedRunId, {
          action: "APPROVE",
          actor_id: actorSlug,
        });
      }
      setStatus("COMPLETED_APPROVED");
      setStatusBanner(processCopy.deliverableApprovedBanner);
    } catch (err: unknown) {
      const extracted = extractLocalizedApiError(
        err,
        locale,
        "ERR_CLIENT_PROCESS_DELIVERABLE_APPROVE",
      );
      setHasError(true);
      setStatusBanner(
        resolveLocalizedClientError("ERR_CLIENT_PROCESS_DELIVERABLE_APPROVE", locale, {
          detail: extracted.errorMessage,
        }),
      );
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  const handleAction2SaveAmendedDiff = () => {
    setArtifactSha256(simpleHashHex(artifactMarkdown));
    setIsEditingDiff(false);
    setStatusBanner(processCopy.deliverableDiffSavedBanner);
  };

  const handleAction3RejectAndLoop = () => {
    const nextIter = iteration + 1;
    setIteration(nextIter);
    setReentryMode("corrections");
    setCurrentSubIndex(0);
    setStatus("RETURN_LOOP_TRIGGERED");
    const loopSection = processCopy.returnLoopMarkdown
      .replace("{cycle}", String(nextIter))
      .replace("{step}", returnLoopTargetStep)
      .replace("{remarks}", returnLoopRemarks);
    const revisedMd = `${artifactMarkdown}\n\n${loopSection}`;
    setArtifactMarkdown(revisedMd);
    setArtifactSha256(simpleHashHex(revisedMd));
    setStatusBanner(
      processCopy.returnLoopBanner
        .replace("{step}", returnLoopTargetStep)
        .replace("{cycle}", String(nextIter)),
    );
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
  };
}
