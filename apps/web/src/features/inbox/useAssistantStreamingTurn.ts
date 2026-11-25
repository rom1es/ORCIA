import {
  sanitizeAssistantDisplayReply,
  type UiAssistantAttachedFileItem,
  type UiAssistantFolderItem,
  type UiAssistantSpeedMode,
  type UiInferenceEffort,
  type UiInferenceTier,
} from "@orcia/ui";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  bgSnapshot,
  classifyAssistantStreamError,
  clearBgTimers,
  detectAdaptiveThinkingStepsForQuestion,
  getBgAbortController,
  resetBackgroundAssistantStreamForTests,
  setBgAbortController,
  setBgOnTurnCompletedCallback,
  shouldUseProgressiveStepThinking,
  subscribeBgStream,
  updateBgSnapshot,
  type AssistantStreamErrorLabels,
  type CompletedAssistantTurnPayload,
} from "./assistantBackgroundStreamStore";
import type { SavedAssistantGovernancePrefs } from "./assistantFoldersAndPrefsStore";
import { startAssistantStreamingTurnExecution } from "./assistantStreamingRunner";
import {
  decideAssistantTurnProposal,
  reattachAssistantRunningTurn,
  stopActiveAssistantTurn,
  synthesizeActiveAssistantTurn,
} from "./assistantTurnControlsHelper";
import { buildAssistantTurnRequestPayload } from "./assistantTurnPayloadHelper";

export {
  detectAdaptiveThinkingStepsForQuestion,
  resetBackgroundAssistantStreamForTests,
  shouldUseProgressiveStepThinking,
  type CompletedAssistantTurnPayload,
};

export interface UseAssistantStreamingTurnOptions {
  readonly activeWorkspaceId: string;
  readonly isFr: boolean;
  readonly initialStreamedText: string;
  readonly activeThreadId?: string | null;
  readonly ensureThreadForTurn?: (titleSeed: string) => Promise<string>;
  readonly activeFolder?: UiAssistantFolderItem | null;
  readonly governancePrefs?: SavedAssistantGovernancePrefs;
  readonly sessionActiveHat?: string;
  readonly streamErrorLabels?: AssistantStreamErrorLabels;
  readonly onTurnCompleted: (params: CompletedAssistantTurnPayload) => void;
}

export interface SendAssistantTurnPayload {
  readonly userPrompt: string;
  readonly requestedSpeed: UiAssistantSpeedMode;
  readonly deepAuditPillActive: boolean;
  readonly requestedTier?: UiInferenceTier;
  readonly thinkingEffort?: UiInferenceEffort;
  readonly parentTurnId?: string;
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[];
}

export function useAssistantStreamingTurn({
  activeWorkspaceId,
  isFr,
  initialStreamedText,
  activeThreadId = null,
  ensureThreadForTurn,
  activeFolder = null,
  governancePrefs,
  sessionActiveHat,
  streamErrorLabels,
  onTurnCompleted,
}: UseAssistantStreamingTurnOptions) {
  setBgOnTurnCompletedCallback(onTurnCompleted);
  const initializedRef = useRef(false);
  if (!initializedRef.current) {
    initializedRef.current = true;
    if (!bgSnapshot.isGenerating && !bgSnapshot.streamedText && initialStreamedText) {
      updateBgSnapshot({ streamedText: sanitizeAssistantDisplayReply(initialStreamedText) });
    }
  }

  const [, setTick] = useState(0);
  useEffect(() => {
    return subscribeBgStream(() => setTick((n) => n + 1));
  }, []);

  const reattachToActiveTurn = useCallback(
    () =>
      reattachAssistantRunningTurn({
        activeWorkspaceId,
        isFr,
        streamErrorLabels,
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [activeWorkspaceId, isFr],
  );

  useEffect(() => {
    void reattachToActiveTurn();
  }, [reattachToActiveTurn]);

  const setStreamedText = (next: string) =>
    updateBgSnapshot({ streamedText: sanitizeAssistantDisplayReply(next) });

  const resetStreamState = (nextText = "") => {
    getBgAbortController()?.abort();
    setBgAbortController(null);
    clearBgTimers();
    updateBgSnapshot({
      activeTurnId: null,
      lastEventCursor: null,
      isGenerating: false,
      thinkingStartedAtMs: null,
      generationStopped: false,
      activeUserPrompt: "",
      streamedText: sanitizeAssistantDisplayReply(nextText),
      stepProgress: [],
      activeTraceStatus: null,
      traceEvents: [],
      toolCallSteps: [],
      approvalProposal: null,
      approvalBusy: false,
      pendingWritePreview: null,
      citationMap: null,
      lowEvidence: false,
      supportsTools: true,
      purgedPhantomCount: 0,
      nodes1To4Ms: 0,
      errorMessage: null,
      errorKind: null,
    });
  };

  const sendTurn = ({
    userPrompt,
    requestedSpeed,
    deepAuditPillActive,
    requestedTier,
    thinkingEffort,
    parentTurnId,
    attachedFiles,
  }: SendAssistantTurnPayload) => {
    getBgAbortController()?.abort();
    clearBgTimers();

    const controller = new AbortController();
    setBgAbortController(controller);

    const effectiveTier: UiInferenceTier = requestedTier ?? "medium";
    const effectiveEffort: UiInferenceEffort =
      thinkingEffort ??
      (deepAuditPillActive ? "deep" : requestedSpeed === "SPEED_1_FAST" ? "fast" : "balanced");
    const useSteps = shouldUseProgressiveStepThinking({
      userPrompt,
      requestedSpeed,
      deepAuditPillActive,
      thinkingEffort: effectiveEffort,
    });
    const plannedSteps = useSteps ? detectAdaptiveThinkingStepsForQuestion(userPrompt, isFr) : [];
    const tStart = Date.now();
    const activeHat = governancePrefs?.defaultHat?.trim() || sessionActiveHat?.trim() || "ARCHITECT";
    const pinnedNotes = activeFolder?.pinnedNotesMarkdown?.trim() || undefined;
    const folderTitle = activeFolder?.title || null;

    updateBgSnapshot({
      activeTurnId: null,
      lastEventCursor: null,
      errorMessage: null,
      errorKind: null,
      generationStopped: false,
      isGenerating: true,
      thinkingStartedAtMs: tStart,
      activeUserPrompt: userPrompt,
      streamedText: "",
      activeTraceStatus: useSteps || requestedSpeed !== "SPEED_1_FAST" ? "RUNNING" : null,
      traceEvents: [],
      toolCallSteps: [],
      approvalProposal: null,
      approvalBusy: false,
      pendingWritePreview: null,
      citationMap: null,
      lowEvidence: false,
      purgedPhantomCount: 0,
      stepProgress:
        useSteps && plannedSteps.length > 0
          ? [{ ...plannedSteps[0]!, status: "RUNNING", durationMs: 0 }]
          : [],
    });

    const launchWithThread = (resolvedThreadId: string | null) => {
      if (controller.signal.aborted) return;
      const requestPayload = buildAssistantTurnRequestPayload({
        workspaceIdValue: activeWorkspaceId,
        activeHat,
        userPrompt,
        ...(attachedFiles ? { attachedFiles } : {}),
        requestedSpeed,
        deepAuditPillActive,
        effectiveTier,
        effectiveEffort,
        threadId: resolvedThreadId,
        activeFolder,
        ...(parentTurnId ? { parentTurnId } : {}),
        ...(governancePrefs ? { governancePrefs } : {}),
        isFr,
      });

      startAssistantStreamingTurnExecution({
        controller,
        workspaceIdValue: activeWorkspaceId,
        threadId: resolvedThreadId,
        parentTurnId: parentTurnId ?? null,
        isFr,
        tStart,
        userPrompt,
        effectiveTier,
        effectiveEffort,
        folderTitle,
        pinnedNotes,
        attachedFiles,
        useSteps,
        plannedSteps,
        requestPayload,
        streamErrorLabels,
      });
    };

    if (activeThreadId || !ensureThreadForTurn) {
      launchWithThread(activeThreadId);
    } else {
      void ensureThreadForTurn(userPrompt)
        .then((newThreadId) => launchWithThread(newThreadId))
        .catch((err: unknown) => {
          if (controller.signal.aborted) return;
          const classified = classifyAssistantStreamError(err, isFr, streamErrorLabels);
          updateBgSnapshot({
            isGenerating: false,
            thinkingStartedAtMs: null,
            errorKind: classified.errorKind,
            errorMessage: classified.errorMessage,
          });
        });
    }
  };

  const initialElapsedSeconds =
    bgSnapshot.isGenerating && bgSnapshot.thinkingStartedAtMs !== null
      ? Math.max(0, Math.floor((Date.now() - bgSnapshot.thinkingStartedAtMs) / 1000))
      : 0;

  return {
    activeTurnId: bgSnapshot.activeTurnId,
    activeThreadId: bgSnapshot.activeThreadId,
    lastEventCursor: bgSnapshot.lastEventCursor,
    streamedText: bgSnapshot.streamedText,
    setStreamedText,
    activeUserPrompt: bgSnapshot.activeUserPrompt,
    stepProgress: bgSnapshot.stepProgress,
    activeTraceStatus: bgSnapshot.activeTraceStatus,
    traceEvents: bgSnapshot.traceEvents,
    toolCallSteps: bgSnapshot.toolCallSteps,
    approvalProposal: bgSnapshot.approvalProposal,
    approvalBusy: bgSnapshot.approvalBusy,
    pendingWritePreview: bgSnapshot.pendingWritePreview,
    citationMap: bgSnapshot.citationMap,
    lowEvidence: bgSnapshot.lowEvidence,
    supportsTools: bgSnapshot.supportsTools,
    purgedPhantomCount: bgSnapshot.purgedPhantomCount,
    cacheHit: bgSnapshot.cacheHit,
    cacheLookupMs: bgSnapshot.cacheLookupMs,
    nodes1To4Ms: bgSnapshot.nodes1To4Ms,
    ttftMs: bgSnapshot.ttftMs,
    isGenerating: bgSnapshot.isGenerating,
    initialElapsedSeconds,
    generationStopped: bgSnapshot.generationStopped,
    errorMessage: bgSnapshot.errorMessage,
    errorKind: bgSnapshot.errorKind,
    sendTurn,
    stopGeneration: () => stopActiveAssistantTurn(isFr),
    synthesizeNow: () => synthesizeActiveAssistantTurn(isFr),
    reattachToActiveTurn,
    approveProposal: (id: string, humanAnchorMarkdown?: string) =>
      decideAssistantTurnProposal({ activeWorkspaceId, isFr, proposalId: id, approved: true, humanAnchorMarkdown }),
    rejectProposal: (id: string, rationale?: string) =>
      decideAssistantTurnProposal({ activeWorkspaceId, isFr, proposalId: id, approved: false, rationale }),
    resetStreamState,
  };
}
