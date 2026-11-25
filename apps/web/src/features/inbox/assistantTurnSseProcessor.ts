import {
  sanitizeAssistantDisplayReply,
  type UiAgentTraceEventItem,
  type UiAssistantAttachedFileItem,
  type UiInferenceEffort,
  type UiInferenceTier,
  type UiThreeSpeedStepProgress,
} from "@orcia/ui";
import { resolveDictionaryForFlag, resolveLocaleForFlag } from "../../i18n";
import { resolveLocalizedClientError } from "../../lib/formatRfc9457ErrorToBanner";
import {
  bgSnapshot,
  clearBgTimers,
  invokeBgOnTurnCompleted,
  updateBgSnapshot,
} from "./assistantBackgroundStreamStore";
import {
  buildApprovalProposalFromSse,
  buildTraceEventFromToolSse,
  upsertToolCallStepFromSse,
} from "./assistantTurnPayloadHelper";

export function createTurnSseProcessor(cfg: {
  readonly controller: AbortController;
  readonly isFr: boolean;
  readonly tStart: number;
  readonly userPrompt: string;
  readonly threadId?: string | null;
  readonly parentTurnId?: string | null;
  readonly effectiveTier: UiInferenceTier;
  readonly effectiveEffort: UiInferenceEffort;
  readonly folderTitle: string | null;
  readonly pinnedNotes?: string | undefined;
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[] | undefined;
  readonly useSteps: boolean;
  readonly plannedSteps: readonly UiThreeSpeedStepProgress[];
  readonly initialTurnId?: string | null;
}) {
  let latestThinking = "";
  let latestReply = "";
  let latestCitationMap: Readonly<Record<string, unknown>> | null = null;
  let activeTurnId: string | null = cfg.initialTurnId ?? null;
  let hasStreamError = false;
  let completedHandled = false;
  const flowCopy = resolveDictionaryForFlag(cfg.isFr).featureInboxAssistant.assistantFlow;

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
    if (completedHandled || cfg.controller.signal.aborted) return;
    completedHandled = true;
    clearBgTimers();
    const finalReply = sanitizeAssistantDisplayReply(done.replyText) || latestReply;
    const elapsedSec = Math.max(1, Math.round((Date.now() - cfg.tStart) / 1000));
    const finalSteps: readonly UiThreeSpeedStepProgress[] = done.thinkingText
      ? [{
          stepCode: "LIVE_MODEL_REASONING",
          label: flowCopy.modelReasoningLabel,
          durationMs: Number(done.latencyMs ?? elapsedSec * 1000),
          status: "COMPLETED",
          intermediateOutput: done.thinkingText,
        }]
      : cfg.useSteps
        ? cfg.plannedSteps.map((st) => ({ ...st, status: "COMPLETED" as const }))
        : [];
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
        ...(cfg.threadId ? { threadId: cfg.threadId } : {}),
        ...(cfg.parentTurnId ? { parentTurnId: cfg.parentTurnId } : {}),
        userPrompt: cfg.userPrompt,
        assistantReply: finalReply,
        assembledSystemPrompt: done.assembledSystemPrompt,
        thinkingText: done.thinkingText,
        conversationHistoryCount: 0,
        folderTitle: cfg.folderTitle,
        folderPinnedNotes: cfg.pinnedNotes ?? null,
        requestedTier: cfg.effectiveTier,
        thinkingEffort: cfg.effectiveEffort,
        ...(cfg.attachedFiles ? { attachedFiles: cfg.attachedFiles } : {}),
        ...(finalSteps.length > 0 ? { stepProgress: finalSteps } : {}),
        thinkingElapsedSeconds: elapsedSec,
        ...(bgSnapshot.traceEvents.length > 0 ? { traceEvents: bgSnapshot.traceEvents } : {}),
        ...(bgSnapshot.toolCallSteps.length > 0 ? { toolCallSteps: bgSnapshot.toolCallSteps } : {}),
        ...(bgSnapshot.approvalProposal ? { approvalProposal: bgSnapshot.approvalProposal } : {}),
        ...(done.citationMap ?? latestCitationMap ? { citationMap: done.citationMap ?? latestCitationMap } : {}),
        ...(done.lowEvidence !== undefined ? { lowEvidence: done.lowEvidence } : {}),
        ...(done.supportsTools !== undefined ? { supportsTools: done.supportsTools } : {}),
      });
    }
  };

  const onEvent = (eventName: string, data: Readonly<Record<string, unknown>>, eventId?: string) => {
    if (cfg.controller.signal.aborted) return;
    if (eventId) updateBgSnapshot({ lastEventCursor: eventId });

    if (eventName === "thinking_delta") {
      const txt = String(data.thinking_text ?? data.delta_text ?? "").trim();
      if (!txt) return;
      clearBgTimers();
      latestThinking = txt;
      const seq = bgSnapshot.traceEvents.length + 1;
      const thoughtEvt: UiAgentTraceEventItem = {
        eventId: `evt-thought-${seq}`, sequence: seq, kind: "THOUGHT_DELTA",
        label: flowCopy.explorationGroupLabel, actorSlug: "assistant",
        groupKey: "assistant-turn", thoughtContent: txt,
      };
      updateBgSnapshot({
        ...(bgSnapshot.activeTraceStatus ? { traceEvents: [...bgSnapshot.traceEvents, thoughtEvt] } : {}),
        stepProgress: [{
          stepCode: "LIVE_MODEL_REASONING",
          label: flowCopy.modelReasoningInProgressLabel,
          durationMs: Number(data.elapsed_ms ?? Date.now() - cfg.tStart),
          status: "RUNNING",
          intermediateOutput: txt,
        }],
      });
    } else if (eventName === "tool_call" || eventName === "tool_result") {
      clearBgTimers();
      const newEvts = buildTraceEventFromToolSse({ eventName, data, nextSeq: bgSnapshot.traceEvents.length + 1, isFr: cfg.isFr });
      const nextSteps = upsertToolCallStepFromSse(bgSnapshot.toolCallSteps, eventName, data);
      updateBgSnapshot({ activeTraceStatus: "RUNNING", traceEvents: [...bgSnapshot.traceEvents, ...newEvts], toolCallSteps: nextSteps });
    } else if (eventName === "approval_required") {
      const proposal = buildApprovalProposalFromSse(data);
      updateBgSnapshot({
        activeTraceStatus: "WAITING_WRITE_PREVIEW",
        approvalProposal: proposal,
        pendingWritePreview: {
          previewId: proposal.proposalId,
          targetConnector: proposal.targetUri || proposal.actionKind || "ORCIA",
          actionSummary: proposal.rationale || flowCopy.actionPendingApprovalLabel,
          payloadPreview: data,
        },
      });
    } else if (eventName === "token_delta") {
      clearBgTimers();
      const acc = sanitizeAssistantDisplayReply(String(data.accumulated_text ?? ""));
      if (!acc) return;
      const nextTtft = !latestReply ? Date.now() - cfg.tStart : bgSnapshot.ttftMs;
      latestReply = acc;
      updateBgSnapshot({
        ttftMs: nextTtft, streamedText: acc,
        stepProgress: bgSnapshot.stepProgress.map((st) => (st.status === "RUNNING" ? { ...st, status: "COMPLETED" } : st)),
      });
    } else if (eventName === "citation_map") {
      latestCitationMap = data;
      updateBgSnapshot({ citationMap: data, purgedPhantomCount: Number(data.purged_phantom_count ?? 0) });
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
        errorMessage: `${String(data.detail ?? data.message ?? resolveLocalizedClientError("ERR_CLIENT_AI_UNAVAILABLE", resolveLocaleForFlag(cfg.isFr), { detail: flowCopy.turnErrorContext }))}`,
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
  };

  return {
    getActiveTurnId: () => activeTurnId,
    setActiveTurnId: (id: string) => { activeTurnId = id; },
    isCompletedHandled: () => completedHandled,
    hasStreamError: () => hasStreamError,
    getLatestThinking: () => latestThinking,
    setLatestReply: (reply: string) => { latestReply = reply; },
    setLatestThinking: (txt: string) => { latestThinking = txt; },
    finalizeCompletedTurn,
    onEvent,
  };
}
