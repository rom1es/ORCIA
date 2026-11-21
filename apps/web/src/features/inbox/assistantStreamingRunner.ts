import { createOrciaApiClient } from "@orcia/api-client";
import {
  sanitizeAssistantDisplayReply,
  type UiAssistantAttachedFileItem,
  type UiInferenceEffort,
  type UiInferenceTier,
  type UiThreeSpeedStepProgress,
} from "@orcia/ui";
import {
  addBgTimer,
  bgSnapshot,
  clearBgTimers,
  extractHttpErrorStatus,
  invokeBgOnTurnCompleted,
  updateBgSnapshot,
  classifyAssistantStreamError,
  type AssistantStreamErrorLabels,
} from "./assistantBackgroundStreamStore";
import { pollActiveAssistantTurnUntilDone } from "./assistantTurnPayloadHelper";

export interface StartAssistantStreamParams {
  readonly controller: AbortController;
  readonly workspaceIdValue: string;
  readonly isFr: boolean;
  readonly tStart: number;
  readonly userPrompt: string;
  readonly effectiveTier: UiInferenceTier;
  readonly effectiveEffort: UiInferenceEffort;
  readonly historyPayload: Array<{ role: "user" | "assistant"; content: string }>;
  readonly folderTitle: string | null;
  readonly pinnedNotes?: string | undefined;
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[] | undefined;
  readonly useSteps: boolean;
  readonly plannedSteps: readonly UiThreeSpeedStepProgress[];
  readonly requestPayload: Parameters<ReturnType<typeof createOrciaApiClient>["streamAssistantTurnSse"]>[0];
  readonly streamErrorLabels?: AssistantStreamErrorLabels | undefined;
}

export function startAssistantStreamingTurnExecution(params: StartAssistantStreamParams): void {
  const {
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
  } = params;

  if (useSteps && plannedSteps.length >= 3) {
    const advanceStep = (idx: 1 | 2) => {
      if (controller.signal.aborted || bgSnapshot.stepProgress.some((s) => s.stepCode === "LIVE_MODEL_REASONING")) {
        return;
      }
      updateBgSnapshot({
        stepProgress:
          idx === 1
            ? [
                { ...plannedSteps[0]!, status: "COMPLETED", durationMs: 1200 },
                { ...plannedSteps[1]!, status: "RUNNING", durationMs: 0 },
              ]
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

  const client = createOrciaApiClient({ baseUrl: "", locale: isFr ? "fr" : "en" });
  let latestThinking = "";
  let latestReply = "";
  let hasStreamError = false;
  let completedHandled = false;

  const finalizeCompletedTurn = (done: {
    turnId?: string;
    replyText: string;
    thinkingText: string;
    assembledSystemPrompt: string;
    latencyMs?: number;
  }) => {
    if (completedHandled || controller.signal.aborted) return;
    completedHandled = true;
    clearBgTimers();
    const finalReply = sanitizeAssistantDisplayReply(done.replyText) || latestReply;
    const elapsedSec = Math.max(1, Math.round((Date.now() - tStart) / 1000));
    const finalSteps: readonly UiThreeSpeedStepProgress[] = done.thinkingText
      ? [
          {
            stepCode: "LIVE_MODEL_REASONING",
            label: isFr ? "Raisonnement du modèle" : "Model reasoning",
            durationMs: Number(done.latencyMs ?? elapsedSec * 1000),
            status: "COMPLETED",
            intermediateOutput: done.thinkingText,
          },
        ]
      : useSteps
        ? plannedSteps.map((st) => ({ ...st, status: "COMPLETED" as const }))
        : [];
    updateBgSnapshot({ stepProgress: finalSteps, streamedText: finalReply, isGenerating: false, thinkingStartedAtMs: null });
    if (finalReply && !/^synthèse conforme pour\s*«/i.test(finalReply)) {
      invokeBgOnTurnCompleted({
        ...(done.turnId ? { turnId: done.turnId } : {}),
        userPrompt,
        assistantReply: finalReply,
        assembledSystemPrompt: done.assembledSystemPrompt,
        thinkingText: done.thinkingText,
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
            stepProgress: [
              {
                stepCode: "LIVE_MODEL_REASONING",
                label: isFr ? "Raisonnement du modèle en cours" : "Model reasoning in progress",
                durationMs: Number(data.elapsed_ms ?? Date.now() - tStart),
                status: "RUNNING",
                intermediateOutput: txt,
              },
            ],
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
            errorMessage: `⚠️ ${String(data.message ?? "AI provider error")}`,
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
}
