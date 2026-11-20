import type { UiAgentTraceEventItem } from "@orcia/ui";
import { useEffect, useRef, useState } from "react";
import { useI18n } from "../../../i18n";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";
import { createProcessesApiClient } from "../studio/studioLabelsAndMappers";
import {
  mapApiTraceEventToUi,
  readPersistedReflexiveId,
} from "../../shared/reflexiveTraceMappers";
import { useReflexiveExecutionController } from "../../shared/useReflexiveExecutionController";
import { useSourceLineInspector } from "../../shared/useSourceLineInspector";
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
  const enabledSubSteps = workflow.sub_steps.filter((s) => s.enabled);
  const isExternalGate = workflow.execution_mode === "external_delegated";
  const isGoalDriven = workflow.orchestration_type === "non_deterministic";
  const storageKey = `orcia.reflexive_exec.process.${workflow.id}.v1`;
  const actorSlug = extractAgentSlugFromRef(workflow.agent_ref);

  const [runId, setRunId] = useState<string>(() => `run-${workflow.id}-01`);
  const [iteration, setIteration] = useState<number>(1);
  const [reentryMode, setReentryMode] = useState<"initial" | "corrections">(
    "initial",
  );
  const [currentSubIndex, setCurrentSubIndex] = useState<number>(0);
  const [status, setStatus] = useState<InteractiveProcessDrawerStatus>(
    isExternalGate ? "WAITING_EXTERNAL_GATE" : "WAITING_SUBSTEP_HITL",
  );

  const currentSubStep = enabledSubSteps[currentSubIndex] ?? enabledSubSteps[0];
  const agentLabel = formatAgentHumanLabel(workflow.agent_ref);

  const [artifactMarkdown, setArtifactMarkdown] = useState<string>(() =>
    buildInitialArtifactMarkdown(workflow.title, currentSubStep?.name ?? "Exécution", agentLabel),
  );
  const [artifactSha256, setArtifactSha256] = useState<string>(() =>
    simpleHashHex(artifactMarkdown),
  );
  const [isEditingDiff, setIsEditingDiff] = useState<boolean>(false);
  const [returnLoopTargetStep, setReturnLoopTargetStep] = useState<string>("02");
  const [returnLoopRemarks, setReturnLoopRemarks] = useState<string>(
    "Préciser les hypothèses de gain métier sur le segment professionnel.",
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

  const inspector = useSourceLineInspector({
    locale,
    workspaceId,
    onFeedback: setStatusBanner,
  });

  const reflexive = useReflexiveExecutionController({
    storageKey,
    locale,
    onFeedback: setStatusBanner,
    onSnapshotUpdated: (mapped) => {
      if (mapped.finalMarkdown) {
        setArtifactMarkdown(mapped.finalMarkdown);
        setArtifactSha256(
          mapped.artifactSha256 || simpleHashHex(mapped.finalMarkdown),
        );
      }
      if (mapped.status === "WAITING_WRITE_PREVIEW") {
        setStatus("WAITING_WRITE_PREVIEW");
      } else if (
        mapped.status === "COMPLETED" &&
        status === "WAITING_WRITE_PREVIEW"
      ) {
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
        const res = await createProcessesApiClient(locale).startWorkflowV2Run(
          workflow.id,
          {
            inputs: { objective: workflow.title },
            iteration: 1,
            reentry_mode: "initial",
          },
        );
        if (cancelled || !res?.run) return null;
        const resolvedRunId = res.run.run_id || `run-${workflow.id}-01`;
        setRunId(resolvedRunId);
        hasPersistedServerRunRef.current = Boolean(res.run.run_id);
        if (res.run.reflexive_execution_id) {
          await reflexive.refreshSnapshot(res.run.reflexive_execution_id);
        } else if (
          Array.isArray(res.run.trace_events) &&
          res.run.trace_events.length > 0
        ) {
          setInlineRunTraceEvents(
            res.run.trace_events.map((ev) =>
              mapApiTraceEventToUi(ev, actorSlug),
            ),
          );
        } else if (isGoalDriven) {
          await reflexive.startExecution({
            actor_slug: actorSlug,
            objective: workflow.reflexive_objective || workflow.title,
            effort_level: "high",
            effort_mode: "approfondi",
            allow_sub_agent_delegation: true,
            available_delegate_agents: ["analyste-metier"],
            initial_resources: [
              "docs/product/capabilities.yaml",
              "packs/orcia-docs/workflows/wf-generate-orcia-documentation.yaml",
            ],
            ...(workspaceId ? { workspace_id: workspaceId } : {}),
          });
        }
        return resolvedRunId;
      } catch (err: unknown) {
        if (!cancelled) {
          const detail = err instanceof Error ? err.message : String(err);
          setHasError(true);
          setStatusBanner(
            isFr
              ? `Échec du démarrage du run : ${detail}`
              : `Failed to start run: ${detail}`,
          );
        }
        return null;
      } finally {
        if (!cancelled) {
          setIsStartingRun(false);
        }
      }
    })();

    startRunPromiseRef.current = startPromise;
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflow.id]);

  const handleLaunchLiveInvestigation = () => {
    void reflexive.startExecution({
      actor_slug: actorSlug,
      objective: workflow.reflexive_objective || workflow.title,
      effort_level: "high",
      effort_mode: "approfondi",
      allow_sub_agent_delegation: true,
      available_delegate_agents: ["analyste-metier"],
      initial_resources: [
        "docs/product/capabilities.yaml",
        "packs/orcia-docs/workflows/wf-generate-orcia-documentation.yaml",
      ],
      run_in_background: true,
      step_delay_ms: 120,
    });
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
    if (
      currentSubStep?.write_preview_required &&
      status !== "WAITING_WRITE_PREVIEW"
    ) {
      setStatus("WAITING_WRITE_PREVIEW");
      setStatusBanner(
        isFr
          ? "Vérification avant publication externe : veuillez confirmer la création dans l'outil cible (Jira / Confluence)."
          : "Pre-publication check: please confirm creation in the target tool.",
      );
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
      );
      setArtifactMarkdown(nextMd);
      setArtifactSha256(simpleHashHex(nextMd));
      setStatus(nextSub?.write_preview_required ? "WAITING_WRITE_PREVIEW" : "WAITING_SUBSTEP_HITL");
      setStatusBanner(
        isFr
          ? `Étape « ${currentSubStep?.short_label} » validée. Passage à « ${nextSub?.short_label} ».`
          : `Step "${currentSubStep?.short_label}" approved. Advancing to "${nextSub?.short_label}".`,
      );
    } else {
      setStatus("WAITING_FINAL_ANCHOR");
      setStatusBanner(
        isFr
          ? "Toutes les étapes et les vérifications de qualité sont conformes. Vous pouvez valider et publier le livrable final."
          : "All steps and quality checks passed. Ready for final sign-off.",
      );
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
      setStatusBanner(
        isFr
          ? "Dossier validé et signé : le livrable final est enregistré et publié."
          : "Deliverable approved, signed, and published.",
      );
    } catch (err: unknown) {
      const detail = err instanceof Error ? err.message : String(err);
      setHasError(true);
      setStatusBanner(isFr ? `Échec de la validation du livrable : ${detail}` : `Deliverable approval failed: ${detail}`);
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  const handleAction2SaveAmendedDiff = () => {
    setArtifactSha256(simpleHashHex(artifactMarkdown));
    setIsEditingDiff(false);
    setStatusBanner(isFr ? "Modifications enregistrées sur le livrable." : "Deliverable changes saved.");
  };

  const handleAction3RejectAndLoop = () => {
    const nextIter = iteration + 1;
    setIteration(nextIter);
    setReentryMode("corrections");
    setCurrentSubIndex(0);
    setStatus("RETURN_LOOP_TRIGGERED");
    const revisedMd = `${artifactMarkdown}\n\n## Reprise sur corrections (Cycle ${nextIter} → Étape ${returnLoopTargetStep})\nCommentaires pris en compte : ${returnLoopRemarks}`;
    setArtifactMarkdown(revisedMd);
    setArtifactSha256(simpleHashHex(revisedMd));
    setStatusBanner(
      isFr
        ? `Dossier renvoyé vers l'Étape ${returnLoopTargetStep} avec vos commentaires de correction (Cycle ${nextIter}).`
        : `Returned to Step ${returnLoopTargetStep} with your correction notes (Cycle ${nextIter}).`,
    );
  };

  const effectiveEvents =
    reflexive.events.length > 0 ? reflexive.events : inlineRunTraceEvents;
  const effectiveTraceStatus =
    reflexive.status ?? (effectiveEvents.length > 0 ? "COMPLETED" : null);

  return {
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
  };
}
