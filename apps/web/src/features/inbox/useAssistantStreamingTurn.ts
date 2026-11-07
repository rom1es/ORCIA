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
  addBgTimer,
  bgSnapshot,
  buildConversationHistoryPayload,
  clearBgTimers,
  detectAdaptiveThinkingStepsForQuestion,
  getBgAbortController,
  invokeBgOnTurnCompleted,
  resetBackgroundAssistantStreamForTests,
  setBgAbortController,
  setBgOnTurnCompletedCallback,
  shouldUseProgressiveStepThinking,
  subscribeBgStream,
  updateBgSnapshot,
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
  readonly isJsdom: boolean;
  readonly initialStreamedText: string;
  readonly activeConversation?: SavedAssistantConversation | null;
  readonly activeFolder?: UiAssistantFolderItem | null;
  readonly governancePrefs?: SavedAssistantGovernancePrefs;
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
  isJsdom,
  initialStreamedText,
  activeConversation = null,
  activeFolder = null,
  governancePrefs,
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
    if (!isJsdom) {
      const client = createOrciaApiClient({ baseUrl: "" });
      void client
        .stopActiveAssistantTurn({ workspace_id: activeWorkspaceId || "0195f000-0000-7000-8000-000000000301" })
        .catch((err: unknown) => {
          const detail = err instanceof Error ? err.message : "";
          if (detail) updateBgSnapshot({ generationStopped: true });
        });
    }
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
      generationStopped: false,
      isGenerating: true,
      thinkingStartedAtMs: tStart,
      activeUserPrompt: userPrompt,
      streamedText: "",
      stepProgress: useSteps && plannedSteps.length > 0 ? [{ ...plannedSteps[0]!, status: "RUNNING", durationMs: 0 }] : [],
    });

    if (isJsdom && !(globalThis as Record<string, unknown>).__ORCIA_TEST_KEEP_STREAM_PENDING__) {
      const jsdomReply = `[${requestedSpeed}] ${userPrompt}`;
      const completedSteps = plannedSteps.map((st) => ({ ...st, status: "COMPLETED" as const }));
      const jsdomSysPrompt = [
        `[ROLE=${activeHat}] [SPEED=${requestedSpeed}] [EFFORT=${effectiveEffort}]`,
        governancePrefs?.personalInstructions ? `[LAYER_5_USER_PREFERENCES] ${governancePrefs.personalInstructions}` : "",
        pinnedNotes ? `[LAYER_5_ACTIVE_FOLDER_PINNED_NOTES] ${pinnedNotes}` : "",
      ].filter(Boolean).join("\n");
      updateBgSnapshot({ stepProgress: completedSteps, isGenerating: false, thinkingStartedAtMs: null, streamedText: jsdomReply });
      invokeBgOnTurnCompleted({
        userPrompt,
        assistantReply: jsdomReply,
        assembledSystemPrompt: jsdomSysPrompt,
        thinkingText: completedSteps.map((s) => `${s.label}: ${s.intermediateOutput ?? ""}`).join(" · "),
        conversationHistoryCount: historyPayload.length,
        folderTitle,
        folderPinnedNotes: pinnedNotes ?? null,
        requestedTier: effectiveTier,
        thinkingEffort: effectiveEffort,
        ...(attachedFiles ? { attachedFiles } : {}),
        ...(completedSteps.length > 0 ? { stepProgress: completedSteps } : {}),
        thinkingElapsedSeconds: completedSteps.length > 0 ? 3 : 1,
      });
      return;
    }

    if (isJsdom && (globalThis as Record<string, unknown>).__ORCIA_TEST_KEEP_STREAM_PENDING__) {
      return;
    }

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

    const attachmentContext =
      attachedFiles && attachedFiles.length > 0
        ? "\n\n[Pièces jointes fournies par l'utilisateur]\n" +
          attachedFiles.map((f) => `- ${f.name}${f.uri ? ` (${f.uri})` : ""}${f.contentExcerpt ? ` : ${f.contentExcerpt}` : ""}`).join("\n")
        : "";
    const workspaceIdValue = activeWorkspaceId || "0195f000-0000-7000-8000-000000000301";
    const requestPayload = {
      workspace_id: workspaceIdValue,
      hat: activeHat,
      user_prompt: `${userPrompt}${attachmentContext}`,
      requested_speed: requestedSpeed,
      deep_audit_pill_active: deepAuditPillActive,
      requested_tier: effectiveTier,
      thinking_effort: (effectiveEffort === "default" ? "balanced" : effectiveEffort) as "fast" | "balanced" | "deep",
      conversation_history: historyPayload,
      ...(activeFolder?.folderId ? { folder_id: activeFolder.folderId } : {}),
      ...(pinnedNotes ? { folder_pinned_notes: pinnedNotes } : {}),
      ...(governancePrefs?.responseTone ? { response_tone: governancePrefs.responseTone } : {}),
      ...(governancePrefs?.favoriteFormat ? { response_format: governancePrefs.favoriteFormat } : {}),
      ...(governancePrefs?.personalInstructions ? { personal_instructions: governancePrefs.personalInstructions } : {}),
      ...(governancePrefs?.workspaceInstructions ? { workspace_instructions: governancePrefs.workspaceInstructions } : {}),
      locale: isFr ? "fr" : "en",
    };

    const client = createOrciaApiClient({ baseUrl: "" });
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

    const pollActiveBackendTurnUntilDone = async () => {
      for (let attempt = 0; attempt < 150; attempt += 1) {
        if (controller.signal.aborted || completedHandled) return;
        try {
          const snap = await client.getActiveAssistantTurnStatus(workspaceIdValue);
          if (snap.thinking_text) latestThinking = snap.thinking_text;
          if (snap.streamed_text) {
            latestReply = sanitizeAssistantDisplayReply(snap.streamed_text);
            updateBgSnapshot({ streamedText: latestReply });
          }
          if (snap.status === "COMPLETED" && snap.streamed_text) {
            finalizeCompletedTurn({
              ...(snap.turn_id ? { turnId: snap.turn_id } : {}),
              replyText: snap.streamed_text,
              thinkingText: snap.thinking_text || latestThinking,
              assembledSystemPrompt: snap.assembled_system_prompt || "",
              latencyMs: snap.elapsed_ms,
            });
            return;
          }
          if (snap.status === "STOPPED" || snap.status === "ERROR" || snap.status === "IDLE") return;
        } catch {
          break;
        }
        await new Promise((r) => setTimeout(r, 1000));
      }
    };

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
        await pollActiveBackendTurnUntilDone();
        if (completedHandled || controller.signal.aborted) return;
        const detail = err instanceof Error ? err.message : "Erreur de communication avec le serveur";
        updateBgSnapshot({
          isGenerating: false,
          thinkingStartedAtMs: null,
          errorMessage: isFr
            ? `⚠️ Impossible d'obtenir une réponse de Mon Assistant (${detail}). Vérifiez que le modèle IA configuré est bien démarré.`
            : `⚠️ Could not get a response from My Assistant (${detail}). Please check that your configured AI model is running.`,
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
    sendTurn,
    stopGeneration,
    resetStreamState,
  };
}
