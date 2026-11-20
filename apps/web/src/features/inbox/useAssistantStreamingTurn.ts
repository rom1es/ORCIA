import { createOrciaApiClient } from "@orcia/api-client";
import {
  sanitizeAssistantDisplayReply,
  type UiAssistantAttachedFileItem,
  type UiAssistantFolderItem,
  type UiAssistantSpeedMode,
  type UiInferenceEffort,
  type UiInferenceTier,
  type UiThreeSpeedStepProgress,
} from "@orcia/ui";
import { useEffect, useRef, useState } from "react";
import {
  buildThreeSpeedTurnRequestPayload,
  pollActiveAssistantTurnUntilDone,
} from "./assistantTurnPayloadHelper";
import {
  addBgTimer,
  bgSnapshot,
  buildConversationHistoryPayload,
  classifyAssistantStreamError,
  clearBgTimers,
  detectAdaptiveThinkingStepsForQuestion,
  extractHttpErrorStatus,
  getBgAbortController,
  invokeBgOnTurnCompleted,
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
    // Intentionally DO NOT abort bgAbortController on unmount so thinking continues across ORCIA screens!
    return subscribeBgStream(() => setTick((n) => n + 1));
  }, []);

  const setStreamedText = (next: string) => updateBgSnapshot({ streamedText: sanitizeAssistantDisplayReply(next) });

  const stopGeneration = () => {
    getBgAbortController()?.abort();
    setBgAbortController(null);
    clearBgTimers();
    updateBgSnapshot({
      isGenerating: false,
      thinkingStartedAtMs: null,
      generationStopped: true,
      stepProgress: bgSnapshot.stepProgress.map((st) => (st.status === "RUNNING" ? { ...st, status: "COMPLETED" } : st)),
    });
    const client = createOrciaApiClient({ baseUrl: "", locale: isFr ? "fr" : "en" });
    void client
      .stopActiveAssistantTurn({ workspace_id: activeWorkspaceId || "0195f000-0000-7000-8000-000000000301" })
      .catch((err: unknown) => {
        const detail = err instanceof Error ? err.message : String(err);
        console.warn("[orcia:assistant.stopActiveTurn]", detail);
        if (detail) updateBgSnapshot({ generationStopped: true });
      });
  };

  const resetStreamState = (nextText = "") => {
    getBgAbortController()?.abort();
    setBgAbortController(null);
    clearBgTimers();
    updateBgSnapshot({
      isGenerating: false,
      thinkingStartedAtMs: null,
      generationStopped: false,
      activeUserPrompt: "",
      streamedText: sanitizeAssistantDisplayReply(nextText),
      stepProgress: [],
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
    attachedFiles,
  }: SendAssistantTurnPayload) => {
    getBgAbortController()?.abort();
    clearBgTimers();

    const controller = new AbortController();
    setBgAbortController(controller);

    const effectiveTier: UiInferenceTier = requestedTier ?? "medium";
    const effectiveEffort: UiInferenceEffort = thinkingEffort ?? (deepAuditPillActive ? "deep" : "balanced");
    const useSteps = shouldUseProgressiveStepThinking({ userPrompt, requestedSpeed, deepAuditPillActive, thinkingEffort: effectiveEffort });
    const plannedSteps = useSteps ? detectAdaptiveThinkingStepsForQuestion(userPrompt, isFr) : [];
    const tStart = Date.now();
    const historyPayload = buildConversationHistoryPayload(activeConversation);
    const activeHat = governancePrefs?.defaultHat || "PM";
    const pinnedNotes = activeFolder?.pinnedNotesMarkdown?.trim() || undefined;
    const folderTitle = activeFolder?.title || null;

    updateBgSnapshot({
      errorMessage: null,
      errorKind: null,
      generationStopped: false,
      isGenerating: true,
      thinkingStartedAtMs: tStart,
      activeUserPrompt: userPrompt,
      streamedText: "",
      stepProgress: useSteps && plannedSteps.length > 0 ? [{ ...plannedSteps[0]!, status: "RUNNING", durationMs: 0 }] : [],
    });

    if (useSteps && plannedSteps.length >= 3) {
      const advanceStep = (idx: 1 | 2) => {
        if (controller.signal.aborted || bgSnapshot.stepProgress.some((s) => s.stepCode === "LIVE_MODEL_REASONING")) return;
        updateBgSnapshot({
          stepProgress:
            idx === 1
              ? [{ ...plannedSteps[0]!, status: "COMPLETED", durationMs: 1200 }, { ...plannedSteps[1]!, status: "RUNNING", durationMs: 0 }]
              : [
                  { ...plannedSteps[0]!, status: "COMPLETED", durationMs: 1200 },
                  { ...plannedSteps[1]!, status: "COMPLETED", durationMs: 1400 },
                  { ...plannedSteps[2]!, status: "RUNNING", durationMs: 0 },
                ],
        });
      };
      addBgTimer(setTimeout(() => advanceStep(1), 1200));
      addBgTimer(setTimeout(() => advanceStep(2), 2600));
    }

    const workspaceIdValue = activeWorkspaceId || "0195f000-0000-7000-8000-000000000301";
    const requestPayload = buildThreeSpeedTurnRequestPayload({
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
      ...(governancePrefs ? { governancePrefs } : {}),
      isFr,
    });

    const client = createOrciaApiClient({ baseUrl: "", locale: isFr ? "fr" : "en" });
    let latestThinking = "";
    let latestReply = "";
    let hasStreamError = false;
    let completedHandled = false;

    const finalizeCompletedTurn = (params: {
      turnId?: string;
      replyText: string;
      thinkingText: string;
      assembledSystemPrompt: string;
      latencyMs?: number;
    }) => {
      if (completedHandled || controller.signal.aborted) return;
      completedHandled = true;
      clearBgTimers();
      const finalReply = sanitizeAssistantDisplayReply(params.replyText) || latestReply;
      const elapsedSec = Math.max(1, Math.round((Date.now() - tStart) / 1000));
      const finalSteps: readonly UiThreeSpeedStepProgress[] = params.thinkingText
        ? [{ stepCode: "LIVE_MODEL_REASONING", label: isFr ? "Raisonnement du modèle" : "Model reasoning", durationMs: Number(params.latencyMs ?? elapsedSec * 1000), status: "COMPLETED", intermediateOutput: params.thinkingText }]
        : useSteps ? plannedSteps.map((st) => ({ ...st, status: "COMPLETED" as const })) : [];
      updateBgSnapshot({ stepProgress: finalSteps, streamedText: finalReply, isGenerating: false, thinkingStartedAtMs: null });
      if (finalReply && !/^synthèse conforme pour\s*«/i.test(finalReply)) {
        invokeBgOnTurnCompleted({
          ...(params.turnId ? { turnId: params.turnId } : {}),
          userPrompt,
          assistantReply: finalReply,
          assembledSystemPrompt: params.assembledSystemPrompt,
          thinkingText: params.thinkingText,
          conversationHistoryCount: historyPayload.length,
          folderTitle,
          folderPinnedNotes: pinnedNotes ?? null,
          requestedTier: effectiveTier,
          thinkingEffort: effectiveEffort,
          ...(attachedFiles ? { attachedFiles } : {}),
          ...(finalSteps.length > 0 ? { stepProgress: finalSteps } : {}),
          thinkingElapsedSeconds: elapsedSec,
        });
      }
    };

    const runFallbackPolling = () =>
      pollActiveAssistantTurnUntilDone({
        signal: controller.signal,
        isCompletedHandled: () => completedHandled,
        fetchStatus: () => client.getActiveAssistantTurnStatus(workspaceIdValue),
        onThinking: (txt) => {
          latestThinking = txt;
        },
        onStreamedText: (reply) => {
          latestReply = reply;
          updateBgSnapshot({ streamedText: reply });
        },
        onCompleted: (done) => finalizeCompletedTurn(done),
        getLatestThinking: () => latestThinking,
      });

    void client
      .streamAssistantTurnSse(requestPayload, {
        signal: controller.signal,
        onEvent: (eventName, data) => {
          if (controller.signal.aborted) return;
          if (eventName === "cache_status") {
            updateBgSnapshot({ cacheHit: Boolean(data.cache_hit), cacheLookupMs: Number(data.cache_lookup_ms ?? 0) });
          } else if (eventName === "thinking_delta") {
            const txt = String(data.thinking_text ?? "").trim();
            if (!txt) return;
            clearBgTimers();
            latestThinking = txt;
            updateBgSnapshot({
              stepProgress: [{ stepCode: "LIVE_MODEL_REASONING", label: isFr ? "Raisonnement du modèle en cours" : "Model reasoning in progress", durationMs: Number(data.elapsed_ms ?? Date.now() - tStart), status: "RUNNING", intermediateOutput: txt }],
            });
          } else if (eventName === "token_delta") {
            clearBgTimers();
            const acc = sanitizeAssistantDisplayReply(String(data.accumulated_text ?? ""));
            if (!acc) return;
            const nextTtft = !latestReply ? Date.now() - tStart : bgSnapshot.ttftMs;
            latestReply = acc;
            updateBgSnapshot({
              ttftMs: nextTtft,
              streamedText: acc,
              stepProgress: bgSnapshot.stepProgress.map((st) => (st.status === "RUNNING" ? { ...st, status: "COMPLETED" } : st)),
            });
          } else if (eventName === "stream_error") {
            hasStreamError = true;
            clearBgTimers();
            updateBgSnapshot({
              isGenerating: false,
              thinkingStartedAtMs: null,
              stepProgress: bgSnapshot.stepProgress.map((st) => (st.status === "RUNNING" ? { ...st, status: "COMPLETED" } : st)),
              errorKind: "ai_unavailable",
              errorMessage: `⚠️ ${String(data.message ?? "Erreur du fournisseur IA")}`,
            });
          } else if (eventName === "turn_completed") {
            finalizeCompletedTurn({
              ...(typeof data.turn_id === "string" ? { turnId: data.turn_id } : {}),
              replyText: String(data.response_text ?? latestReply),
              thinkingText: String(data.thinking_text ?? latestThinking),
              assembledSystemPrompt: String(data.assembled_system_prompt ?? ""),
              latencyMs: Number(data.latency_ms ?? 0),
            });
          }
        },
      })
      .then(() => {
        if (!controller.signal.aborted && !hasStreamError && !completedHandled) {
          updateBgSnapshot({ isGenerating: false, thinkingStartedAtMs: null });
        }
      })
      .catch(async (err: unknown) => {
        clearBgTimers();
        if (controller.signal.aborted) return;
        const httpStatus = extractHttpErrorStatus(err);
        if (httpStatus !== 401 && httpStatus !== 403) {
          await runFallbackPolling();
        }
        if (completedHandled || controller.signal.aborted) return;
        const classified = classifyAssistantStreamError(err, isFr, streamErrorLabels);
        updateBgSnapshot({
          isGenerating: false,
          thinkingStartedAtMs: null,
          errorKind: classified.errorKind,
          errorMessage: classified.errorMessage,
        });
      });
  };

  const initialElapsedSeconds =
    bgSnapshot.isGenerating && bgSnapshot.thinkingStartedAtMs !== null
      ? Math.max(0, Math.floor((Date.now() - bgSnapshot.thinkingStartedAtMs) / 1000))
      : 0;

  return {
    streamedText: bgSnapshot.streamedText,
    setStreamedText,
    activeUserPrompt: bgSnapshot.activeUserPrompt,
    stepProgress: bgSnapshot.stepProgress,
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
    resetStreamState,
  };
}
