import { createOrciaApiClient } from "@orcia/api-client";
import {
  sanitizeAssistantDisplayReply,
  type UiAgentTraceEventItem,
  type UiAssistantAttachedFileItem,
  type UiInferenceEffort,
  type UiInferenceTier,
  type UiThreeSpeedStepProgress,
} from "@orcia/ui";
import {
  addBgTimer,
  bgSnapshot,
  classifyAssistantStreamError,
  clearBgTimers,
  extractHttpErrorStatus,
  invokeBgOnTurnCompleted,
  updateBgSnapshot,
  type AssistantStreamErrorLabels,
} from "./assistantBackgroundStreamStore";
import {
  buildTraceEventFromToolSse,
  pollActiveAssistantTurnUntilDone,
} from "./assistantTurnPayloadHelper";

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
    controller, workspaceIdValue, isFr, tStart, userPrompt, effectiveTier, effectiveEffort,
    historyPayload, folderTitle, pinnedNotes, attachedFiles, useSteps, plannedSteps,
    requestPayload, streamErrorLabels,
  } = params;

  if (useSteps && plannedSteps.length >= 3) {
    const advanceStep = (idx: 1 | 2) => {
      if (controller.signal.aborted || bgSnapshot.stepProgress.some((s) => s.stepCode === "LIVE_MODEL_REASONING")) {
        return;
      }
      updateBgSnapshot({
        stepProgress:
          idx === 1
            ? [{ ...plannedSteps[0]!, status: "COMPLETED", durationMs: 1200 }, { ...plannedSteps[1]!, status: "RUNNING", durationMs: 0 }]
            : [{ ...plannedSteps[0]!, status: "COMPLETED", durationMs: 1200 }, { ...plannedSteps[1]!, status: "COMPLETED", durationMs: 1400 }, { ...plannedSteps[2]!, status: "RUNNING", durationMs: 0 }],
      });
    };
    addBgTimer(setTimeout(() => advanceStep(1), 1200));
    addBgTimer(setTimeout(() => advanceStep(2), 2600));
  }

  const client = createOrciaApiClient({ baseUrl: "", locale: isFr ? "fr" : "en" });
  let latestThinking = "";
  let latestReply = "";
  let latestCitationMap: Readonly<Record<string, unknown>> | null = null;
  let activeTurnId: string | null = null;
  let hasStreamError = false;
  let completedHandled = false;

  const finalizeCompletedTurn = (done: {
    turnId?: string;
    replyText: string;
    thinkingText: string;
    assembledSystemPrompt: string;
    latencyMs?: number;
    lowEvidence?: boolean;
    supportsTools?: boolean;
    citationMap?: Readonly<Record<string, unknown>> | null;
  }) => {
    if (completedHandled || controller.signal.aborted) return;
    completedHandled = true;
    clearBgTimers();
    const finalReply = sanitizeAssistantDisplayReply(done.replyText) || latestReply;
    const elapsedSec = Math.max(1, Math.round((Date.now() - tStart) / 1000));
    const finalSteps: readonly UiThreeSpeedStepProgress[] = done.thinkingText
      ? [{ stepCode: "LIVE_MODEL_REASONING", label: isFr ? "Raisonnement du modèle" : "Model reasoning", durationMs: Number(done.latencyMs ?? elapsedSec * 1000), status: "COMPLETED", intermediateOutput: done.thinkingText }]
      : useSteps ? plannedSteps.map((st) => ({ ...st, status: "COMPLETED" as const })) : [];
    const nextTraceStatus = bgSnapshot.activeTraceStatus ? "COMPLETED" : null;
    updateBgSnapshot({
      stepProgress: finalSteps,
      streamedText: finalReply,
      isGenerating: false,
      thinkingStartedAtMs: null,
      activeTraceStatus: nextTraceStatus,
      ...(done.lowEvidence !== undefined ? { lowEvidence: done.lowEvidence } : {}),
      ...(done.supportsTools !== undefined ? { supportsTools: done.supportsTools } : {}),
      ...(done.citationMap !== undefined ? { citationMap: done.citationMap } : {}),
    });
    if (finalReply && !/^synthèse conforme pour\s*«/i.test(finalReply)) {
      invokeBgOnTurnCompleted({
        ...(done.turnId ?? activeTurnId ? { turnId: done.turnId ?? activeTurnId ?? undefined } : {}),
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
        ...(bgSnapshot.traceEvents.length > 0 ? { traceEvents: bgSnapshot.traceEvents } : {}),
        ...(done.citationMap ?? latestCitationMap ? { citationMap: done.citationMap ?? latestCitationMap } : {}),
        ...(done.lowEvidence !== undefined ? { lowEvidence: done.lowEvidence } : {}),
        ...(done.supportsTools !== undefined ? { supportsTools: done.supportsTools } : {}),
      });
    }
  };

  const runFallbackPolling = () =>
    pollActiveAssistantTurnUntilDone({
      signal: controller.signal,
      isCompletedHandled: () => completedHandled,
      getTargetTurnId: () => activeTurnId,
      fetchActiveTurns: () => client.listActiveAssistantTurns(workspaceIdValue),
      onThinking: (txt) => { latestThinking = txt; },
      onStreamedText: (reply) => { latestReply = reply; updateBgSnapshot({ streamedText: reply }); },
      onCompleted: (done) => finalizeCompletedTurn(done),
      getLatestThinking: () => latestThinking,
    });

  void client
    .streamAssistantTurnSse(requestPayload, {
      signal: controller.signal,
      onTurnCreated: (accepted) => {
        activeTurnId = accepted.turn_id;
        updateBgSnapshot({
          activeTurnId: accepted.turn_id,
          activeTraceStatus: accepted.speed_mode !== "SPEED_1_FAST" || useSteps ? "RUNNING" : null,
        });
      },
      onEvent: (eventName, data) => {
        if (controller.signal.aborted) return;
        if (eventName === "thinking_delta") {
          const txt = String(data.thinking_text ?? data.delta_text ?? "").trim();
          if (!txt) return;
          clearBgTimers();
          latestThinking = txt;
          const seq = bgSnapshot.traceEvents.length + 1;
          const thoughtEvt: UiAgentTraceEventItem = {
            eventId: `evt-thought-${seq}`, sequence: seq, kind: "THOUGHT_DELTA",
            label: isFr ? "Raisonnement" : "Reasoning", actorSlug: "assistant",
            groupKey: "assistant-turn", thoughtContent: txt,
          };
          updateBgSnapshot({
            ...(bgSnapshot.activeTraceStatus ? { traceEvents: [...bgSnapshot.traceEvents, thoughtEvt] } : {}),
            stepProgress: [{ stepCode: "LIVE_MODEL_REASONING", label: isFr ? "Raisonnement du modèle en cours" : "Model reasoning in progress", durationMs: Number(data.elapsed_ms ?? Date.now() - tStart), status: "RUNNING", intermediateOutput: txt }],
          });
        } else if (eventName === "tool_call" || eventName === "tool_result") {
          clearBgTimers();
          const newEvts = buildTraceEventFromToolSse({ eventName, data, nextSeq: bgSnapshot.traceEvents.length + 1, isFr });
          updateBgSnapshot({ activeTraceStatus: "RUNNING", traceEvents: [...bgSnapshot.traceEvents, ...newEvts] });
        } else if (eventName === "approval_required") {
          const proposalId = String(data.proposal_id ?? `prop-${Date.now()}`);
          updateBgSnapshot({
            activeTraceStatus: "WAITING_WRITE_PREVIEW",
            pendingWritePreview: {
              previewId: proposalId,
              targetConnector: String(data.target_uri ?? data.action_kind ?? "ORCIA"),
              actionSummary: String(data.summary ?? data.action_kind ?? (isFr ? "Action soumise à approbation humaine" : "Action pending human approval")),
              payloadPreview: data,
            },
          });
        } else if (eventName === "token_delta") {
          clearBgTimers();
          const acc = sanitizeAssistantDisplayReply(String(data.accumulated_text ?? ""));
          if (!acc) return;
          const nextTtft = !latestReply ? Date.now() - tStart : bgSnapshot.ttftMs;
          latestReply = acc;
          updateBgSnapshot({
            ttftMs: nextTtft, streamedText: acc,
            stepProgress: bgSnapshot.stepProgress.map((st) => (st.status === "RUNNING" ? { ...st, status: "COMPLETED" } : st)),
          });
        } else if (eventName === "citation_map") {
          const citationsObj = (data.citations as Readonly<Record<string, unknown>> | undefined) ?? null;
          latestCitationMap = citationsObj;
          updateBgSnapshot({ citationMap: citationsObj, purgedPhantomCount: Number(data.purged_phantom_count ?? 0) });
        } else if (eventName === "turn_stopped") {
          clearBgTimers();
          updateBgSnapshot({
            isGenerating: false, thinkingStartedAtMs: null, generationStopped: true,
            activeTraceStatus: bgSnapshot.activeTraceStatus ? "CANCELLED" : null,
          });
        } else if (eventName === "stream_error") {
          hasStreamError = true;
          clearBgTimers();
          updateBgSnapshot({
            isGenerating: false, thinkingStartedAtMs: null,
            activeTraceStatus: bgSnapshot.activeTraceStatus ? "FAILED" : null,
            stepProgress: bgSnapshot.stepProgress.map((st) => (st.status === "RUNNING" ? { ...st, status: "COMPLETED" } : st)),
            errorKind: "ai_unavailable",
            errorMessage: `⚠️ ${String(data.detail ?? data.message ?? "AI provider error")}`,
          });
        } else if (eventName === "turn_completed") {
          const cMap = (data.citation_map as Readonly<Record<string, unknown>> | undefined) ?? latestCitationMap;
          finalizeCompletedTurn({
            ...(typeof data.turn_id === "string" ? { turnId: data.turn_id } : {}),
            replyText: String(data.response_text ?? latestReply),
            thinkingText: String(data.thinking_text ?? latestThinking),
            assembledSystemPrompt: String(data.assembled_system_prompt ?? ""),
            latencyMs: Number(data.latency_ms ?? 0),
            ...(typeof data.low_evidence === "boolean" ? { lowEvidence: data.low_evidence } : {}),
            ...(typeof data.supports_tools === "boolean" ? { supportsTools: data.supports_tools } : {}),
            citationMap: cMap,
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
      if (httpStatus !== 401 && httpStatus !== 403 && activeTurnId) {
        await runFallbackPolling();
      }
      if (completedHandled || controller.signal.aborted) return;
      const classified = classifyAssistantStreamError(err, isFr, streamErrorLabels);
      updateBgSnapshot({
        isGenerating: false, thinkingStartedAtMs: null,
        activeTraceStatus: bgSnapshot.activeTraceStatus ? "FAILED" : null,
        errorKind: classified.errorKind, errorMessage: classified.errorMessage,
      });
    });
}
