import { createOrciaApiClient } from "@orcia/api-client";
import type {
  UiAssistantAttachedFileItem,
  UiInferenceEffort,
  UiInferenceTier,
  UiThreeSpeedStepProgress,
} from "@orcia/ui";
import {
  addBgTimer,
  bgSnapshot,
  classifyAssistantStreamError,
  clearBgTimers,
  extractHttpErrorStatus,
  updateBgSnapshot,
  type AssistantStreamErrorLabels,
} from "./assistantBackgroundStreamStore";
import { pollActiveAssistantTurnUntilDone } from "./assistantTurnPayloadHelper";
import { createTurnSseProcessor } from "./assistantTurnSseProcessor";

export interface StartAssistantStreamParams {
  readonly controller: AbortController;
  readonly workspaceIdValue: string;
  readonly threadId?: string | null;
  readonly parentTurnId?: string | null;
  readonly isFr: boolean;
  readonly tStart: number;
  readonly userPrompt: string;
  readonly effectiveTier: UiInferenceTier;
  readonly effectiveEffort: UiInferenceEffort;
  readonly folderTitle: string | null;
  readonly pinnedNotes?: string | undefined;
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[] | undefined;
  readonly useSteps: boolean;
  readonly plannedSteps: readonly UiThreeSpeedStepProgress[];
  readonly requestPayload: Parameters<ReturnType<typeof createOrciaApiClient>["streamAssistantTurnSse"]>[0];
  readonly streamErrorLabels?: AssistantStreamErrorLabels | undefined;
}

export interface ReattachAssistantStreamParams {
  readonly controller: AbortController;
  readonly turnId: string;
  readonly afterCursor?: string | null;
  readonly workspaceIdValue: string;
  readonly isFr: boolean;
  readonly tStart: number;
  readonly userPrompt: string;
  readonly streamErrorLabels?: AssistantStreamErrorLabels | undefined;
}

export function startAssistantStreamingTurnExecution(params: StartAssistantStreamParams): void {
  const {
    controller, workspaceIdValue, threadId, parentTurnId, isFr, tStart, userPrompt,
    effectiveTier, effectiveEffort, folderTitle, pinnedNotes, attachedFiles,
    useSteps, plannedSteps, requestPayload, streamErrorLabels,
  } = params;

  if (useSteps && plannedSteps.length >= 3) {
    const advanceStep = (idx: 1 | 2) => {
      if (controller.signal.aborted || bgSnapshot.stepProgress.some((s) => s.stepCode === "LIVE_MODEL_REASONING")) return;
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
  const proc = createTurnSseProcessor({
    controller, isFr, tStart, userPrompt, threadId, parentTurnId,
    effectiveTier, effectiveEffort, folderTitle, pinnedNotes, attachedFiles, useSteps, plannedSteps,
  });

  void client
    .streamAssistantTurnSse(requestPayload, {
      signal: controller.signal,
      onTurnCreated: (accepted) => {
        proc.setActiveTurnId(accepted.turn_id);
        updateBgSnapshot({
          activeTurnId: accepted.turn_id,
          activeThreadId: threadId ?? null,
          activeTraceStatus: accepted.speed_mode !== "SPEED_1_FAST" || useSteps ? "RUNNING" : null,
        });
      },
      onEvent: proc.onEvent,
    })
    .then(() => {
      if (!controller.signal.aborted && !proc.hasStreamError() && !proc.isCompletedHandled()) {
        updateBgSnapshot({ isGenerating: false, thinkingStartedAtMs: null });
      }
    })
    .catch(async (err: unknown) => {
      clearBgTimers();
      if (controller.signal.aborted) return;
      const httpStatus = extractHttpErrorStatus(err);
      if (httpStatus !== 401 && httpStatus !== 403 && proc.getActiveTurnId()) {
        await pollActiveAssistantTurnUntilDone({
          signal: controller.signal,
          isCompletedHandled: proc.isCompletedHandled,
          getTargetTurnId: proc.getActiveTurnId,
          fetchActiveTurns: () => client.listActiveAssistantTurns(workspaceIdValue),
          onThinking: proc.setLatestThinking,
          onStreamedText: (reply) => { proc.setLatestReply(reply); updateBgSnapshot({ streamedText: reply }); },
          onCompleted: proc.finalizeCompletedTurn,
          getLatestThinking: proc.getLatestThinking,
        });
      }
      if (proc.isCompletedHandled() || controller.signal.aborted) return;
      const classified = classifyAssistantStreamError(err, isFr, streamErrorLabels);
      updateBgSnapshot({
        isGenerating: false, thinkingStartedAtMs: null,
        activeTraceStatus: bgSnapshot.activeTraceStatus ? "FAILED" : null,
        errorKind: classified.errorKind, errorMessage: classified.errorMessage,
      });
    });
}

export function reattachAssistantTurnStream(params: ReattachAssistantStreamParams): void {
  const { controller, turnId, afterCursor, workspaceIdValue, isFr, tStart, userPrompt, streamErrorLabels } = params;
  const client = createOrciaApiClient({ baseUrl: "", locale: isFr ? "fr" : "en" });
  const proc = createTurnSseProcessor({
    controller, isFr, tStart, userPrompt,
    effectiveTier: "medium", effectiveEffort: "balanced",
    folderTitle: null, useSteps: false, plannedSteps: [], initialTurnId: turnId,
  });

  void client
    .streamAssistantTurnByIdSse(turnId, {
      ...(afterCursor ? { after: afterCursor } : {}),
      signal: controller.signal,
      onEvent: proc.onEvent,
    })
    .then(() => {
      if (!controller.signal.aborted && !proc.hasStreamError() && !proc.isCompletedHandled()) {
        updateBgSnapshot({ isGenerating: false, thinkingStartedAtMs: null });
      }
    })
    .catch(async (err: unknown) => {
      if (controller.signal.aborted) return;
      await pollActiveAssistantTurnUntilDone({
        signal: controller.signal,
        isCompletedHandled: proc.isCompletedHandled,
        getTargetTurnId: () => turnId,
        fetchActiveTurns: () => client.listActiveAssistantTurns(workspaceIdValue),
        onThinking: proc.setLatestThinking,
        onStreamedText: (reply) => { proc.setLatestReply(reply); updateBgSnapshot({ streamedText: reply }); },
        onCompleted: proc.finalizeCompletedTurn,
        getLatestThinking: proc.getLatestThinking,
      });
      if (proc.isCompletedHandled() || controller.signal.aborted) return;
      const classified = classifyAssistantStreamError(err, isFr, streamErrorLabels);
      updateBgSnapshot({ isGenerating: false, thinkingStartedAtMs: null, errorKind: classified.errorKind, errorMessage: classified.errorMessage });
    });
}
