import { createOrciaApiClient } from "@orcia/api-client";
import {
  sanitizeAssistantDisplayReply,
  type UiAssistantAttachedFileItem,
  type UiAssistantFolderItem,
  type UiAssistantSpeedMode,
  type UiInferenceEffort,
  type UiInferenceTier,
} from "@orcia/ui";
import { useEffect, useRef, useState } from "react";
import {
  bgSnapshot,
  buildConversationHistoryPayload,
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
import { buildAssistantTurnRequestPayload } from "./assistantTurnPayloadHelper";
import type { SavedAssistantConversation } from "./savedConversationsStore";

export {
  buildConversationHistoryPayload,
  detectAdaptiveThinkingStepsForQuestion,
  resetBackgroundAssistantStreamForTests,
  shouldUseProgressiveStepThinking,
  type CompletedAssistantTurnPayload,
};

export interface UseAssistantStreamingTurnOptions {
  readonly activeWorkspaceId: string;
  readonly isFr: boolean;
  readonly initialStreamedText: string;
  readonly activeConversation?: SavedAssistantConversation | null;
  readonly activeFolder?: UiAssistantFolderItem | null;
  readonly governancePrefs?: SavedAssistantGovernancePrefs;
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
  activeConversation = null,
  activeFolder = null,
  governancePrefs,
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
    // Intentionally DO NOT abort bgAbortController on unmount so thinking continues across ORCIA screens.
    return subscribeBgStream(() => setTick((n) => n + 1));
  }, []);

  const setStreamedText = (next: string) =>
    updateBgSnapshot({ streamedText: sanitizeAssistantDisplayReply(next) });

  const stopGeneration = () => {
    const turnId = bgSnapshot.activeTurnId;
    getBgAbortController()?.abort();
    setBgAbortController(null);
    clearBgTimers();
    updateBgSnapshot({
      isGenerating: false,
      thinkingStartedAtMs: null,
      generationStopped: true,
      activeTraceStatus: bgSnapshot.activeTraceStatus ? "CANCELLED" : null,
      stepProgress: bgSnapshot.stepProgress.map((st) =>
        st.status === "RUNNING" ? { ...st, status: "COMPLETED" } : st,
      ),
    });
    if (turnId) {
      const client = createOrciaApiClient({ baseUrl: "", locale: isFr ? "fr" : "en" });
      void client.stopAssistantTurn(turnId).catch((err: unknown) => {
        const detail = err instanceof Error ? err.message : String(err);
        console.warn("[orcia:assistant.stopTurn]", detail);
        if (detail) updateBgSnapshot({ generationStopped: true });
      });
    }
  };

  const synthesizeNow = async () => {
    const turnId = bgSnapshot.activeTurnId;
    if (!turnId) return;
    updateBgSnapshot({ activeTraceStatus: "SYNTHESIZING" });
    const client = createOrciaApiClient({ baseUrl: "", locale: isFr ? "fr" : "en" });
    try {
      await client.synthesizeAssistantTurnNow(turnId);
    } catch (err: unknown) {
      console.warn("[orcia:assistant.synthesizeNow]", err instanceof Error ? err.message : String(err));
    }
  };

  const decideProposal = async (proposalId: string, approved: boolean) => {
    const turnId = bgSnapshot.activeTurnId;
    if (!turnId) return;
    const workspaceIdValue = activeWorkspaceId || "0195f000-0000-7000-8000-000000000301";
    const client = createOrciaApiClient({ baseUrl: "", locale: isFr ? "fr" : "en" });
    try {
      await client.approveAssistantTurnProposal(turnId, {
        workspace_id: workspaceIdValue,
        proposal_id: proposalId,
        approved,
        human_authored_required: false,
      });
      updateBgSnapshot({ pendingWritePreview: null, activeTraceStatus: approved ? "COMPLETED" : "CANCELLED" });
    } catch (err: unknown) {
      updateBgSnapshot({
        errorKind: "stream_error",
        errorMessage: `⚠️ ${err instanceof Error ? err.message : String(err)}`,
      });
    }
  };

  const resetStreamState = (nextText = "") => {
    getBgAbortController()?.abort();
    setBgAbortController(null);
    clearBgTimers();
    updateBgSnapshot({
      activeTurnId: null,
      isGenerating: false,
      thinkingStartedAtMs: null,
      generationStopped: false,
      activeUserPrompt: "",
      streamedText: sanitizeAssistantDisplayReply(nextText),
      stepProgress: [],
      activeTraceStatus: null,
      traceEvents: [],
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
      thinkingEffort ?? (deepAuditPillActive ? "deep" : "balanced");
    const useSteps = shouldUseProgressiveStepThinking({
      userPrompt,
      requestedSpeed,
      deepAuditPillActive,
      thinkingEffort: effectiveEffort,
    });
    const plannedSteps = useSteps ? detectAdaptiveThinkingStepsForQuestion(userPrompt, isFr) : [];
    const tStart = Date.now();
    const historyPayload = buildConversationHistoryPayload(activeConversation);
    const activeHat = governancePrefs?.defaultHat || "PM";
    const pinnedNotes = activeFolder?.pinnedNotesMarkdown?.trim() || undefined;
    const folderTitle = activeFolder?.title || null;

    updateBgSnapshot({
      activeTurnId: null,
      errorMessage: null,
      errorKind: null,
      generationStopped: false,
      isGenerating: true,
      thinkingStartedAtMs: tStart,
      activeUserPrompt: userPrompt,
      streamedText: "",
      activeTraceStatus: useSteps || requestedSpeed !== "SPEED_1_FAST" ? "RUNNING" : null,
      traceEvents: [],
      pendingWritePreview: null,
      citationMap: null,
      lowEvidence: false,
      purgedPhantomCount: 0,
      stepProgress:
        useSteps && plannedSteps.length > 0
          ? [{ ...plannedSteps[0]!, status: "RUNNING", durationMs: 0 }]
          : [],
    });

    const workspaceIdValue = activeWorkspaceId || "0195f000-0000-7000-8000-000000000301";
    const requestPayload = buildAssistantTurnRequestPayload({
      workspaceIdValue,
      activeHat,
      userPrompt,
      ...(attachedFiles ? { attachedFiles } : {}),
      requestedSpeed,
      deepAuditPillActive,
      effectiveTier,
      effectiveEffort,
      historyPayload,
      activeFolder,
      ...(parentTurnId ? { parentTurnId } : {}),
      ...(governancePrefs ? { governancePrefs } : {}),
      isFr,
    });

    startAssistantStreamingTurnExecution({
      controller,
      workspaceIdValue,
      isFr,
      tStart,
      userPrompt,
      effectiveTier,
      effectiveEffort,
      historyPayload,
      folderTitle,
      pinnedNotes,
      attachedFiles,
      useSteps,
      plannedSteps,
      requestPayload,
      streamErrorLabels,
    });
  };

  const initialElapsedSeconds =
    bgSnapshot.isGenerating && bgSnapshot.thinkingStartedAtMs !== null
      ? Math.max(0, Math.floor((Date.now() - bgSnapshot.thinkingStartedAtMs) / 1000))
      : 0;

  return {
    activeTurnId: bgSnapshot.activeTurnId,
    streamedText: bgSnapshot.streamedText,
    setStreamedText,
    activeUserPrompt: bgSnapshot.activeUserPrompt,
    stepProgress: bgSnapshot.stepProgress,
    activeTraceStatus: bgSnapshot.activeTraceStatus,
    traceEvents: bgSnapshot.traceEvents,
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
    stopGeneration,
    synthesizeNow,
    approveProposal: (id: string) => decideProposal(id, true),
    rejectProposal: (id: string) => decideProposal(id, false),
    resetStreamState,
  };
}
