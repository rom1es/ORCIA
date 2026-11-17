import { createOrciaApiClient } from "@orcia/api-client";
import type {
  ControlCenterDatasourceItem,
  UiAgentTraceEventItem,
  UiAssistantFolderItem,
  UiAssistantModelOption,
  UiAssistantPromptTelemetryRecord,
} from "@orcia/ui";
import {
  readSavedActiveConversationId,
  updatePromptTelemetryFeedback,
  upsertSavedPromptTelemetryRecord,
} from "./assistantFoldersAndPrefsStore";
import {
  filterUsedRagSourcesForTurn,
  readSavedAssistantConversations,
  updateTurnFeedbackInSavedConversations,
  upsertTurnIntoSavedConversations,
  type SavedAssistantConversation,
} from "./savedConversationsStore";
import type { CompletedAssistantTurnPayload } from "./useAssistantStreamingTurn";

export function persistCompletedInboxTurn(params: {
  readonly completed: CompletedAssistantTurnPayload;
  readonly savedConversations: readonly SavedAssistantConversation[];
  readonly activeConversationId: string | null;
  readonly activeWorkspaceId: string;
  readonly activeFolderId: string;
  readonly activeFolder: UiAssistantFolderItem | null;
  readonly modelOptions: readonly UiAssistantModelOption[];
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly isFr: boolean;
  readonly reflexiveExecutionId: string | null;
  readonly reflexiveEvents: readonly UiAgentTraceEventItem[];
  readonly onFeedbackBanner: (message: string) => void;
}): {
  readonly nextConversations: readonly SavedAssistantConversation[];
  readonly resolvedConversationId: string;
  readonly nextTelemetryLog: readonly UiAssistantPromptTelemetryRecord[];
} {
  const { completed } = params;
  const usedSources = filterUsedRagSourcesForTurn({
    userPrompt: completed.userPrompt,
    assistantReply: completed.assistantReply,
    datasources: params.datasources,
    ...(completed.attachedFiles
      ? { attachedFiles: completed.attachedFiles }
      : {}),
  });
  const latestStored = readSavedAssistantConversations();
  const persistedActiveId =
    readSavedActiveConversationId() ?? params.activeConversationId;
  const outcome = upsertTurnIntoSavedConversations({
    prevConversations:
      latestStored.length >= params.savedConversations.length
        ? latestStored
        : params.savedConversations,
    activeConversationId: persistedActiveId,
    activeWorkspaceId: params.activeWorkspaceId,
    activeFolderId: params.activeFolderId,
    modelOptions: params.modelOptions,
    isFr: params.isFr,
    ...(completed.turnId ? { turnId: completed.turnId } : {}),
    userPrompt: completed.userPrompt,
    assistantReply: completed.assistantReply,
    ...(completed.assembledSystemPrompt
      ? { assembledSystemPrompt: completed.assembledSystemPrompt }
      : {}),
    requestedTier: completed.requestedTier,
    thinkingEffort: completed.thinkingEffort,
    ...(completed.attachedFiles
      ? { attachedFiles: completed.attachedFiles }
      : {}),
    usedSources,
    ...(completed.stepProgress ? { stepProgress: completed.stepProgress } : {}),
    ...(completed.thinkingElapsedSeconds !== undefined
      ? { thinkingElapsedSeconds: completed.thinkingElapsedSeconds }
      : {}),
    ...(params.reflexiveExecutionId && params.reflexiveEvents.length > 0
      ? {
          reflexiveExecutionId: params.reflexiveExecutionId,
          reflexiveTraceEvents: params.reflexiveEvents,
        }
      : {}),
  });

  const nextTelemetryLog = upsertSavedPromptTelemetryRecord({
    turnId: outcome.createdTurn.turnId,
    timestampIso: outcome.createdTurn.timestampIso,
    userPrompt: completed.userPrompt,
    assembledSystemPrompt: completed.assembledSystemPrompt || "",
    conversationHistoryCount: completed.conversationHistoryCount ?? 0,
    folderTitle: completed.folderTitle ?? params.activeFolder?.title ?? null,
    folderPinnedNotes:
      completed.folderPinnedNotes ??
      params.activeFolder?.pinnedNotesMarkdown ??
      null,
    thinkingText: completed.thinkingText || "",
    assistantReply: completed.assistantReply,
    modelLabel: outcome.createdTurn.modelLabel,
    thinkingEffort: completed.thinkingEffort,
    thinkingElapsedSeconds: completed.thinkingElapsedSeconds ?? 1,
    userFeedback: null,
  });

  if (outcome.isNewConversation) {
    const client = createOrciaApiClient({ baseUrl: "" });
    void client
      .createAssistantThread({
        workspace_id:
          params.activeWorkspaceId || "0195f000-0000-7000-8000-000000000301",
        ...(params.activeFolderId ? { folder_id: params.activeFolderId } : {}),
        title: outcome.createdTitle,
        initial_summary: completed.assistantReply.slice(0, 240),
      })
      .catch((err: unknown) => {
        const detail =
          err instanceof Error ? err.message : "Synchronisation différée";
        params.onFeedbackBanner(
          params.isFr
            ? `ℹ️ Conversation sauvegardée localement (${detail}).`
            : `ℹ️ Conversation saved locally (${detail}).`,
        );
      });
  }

  return {
    nextConversations: outcome.nextConversations,
    resolvedConversationId: outcome.resolvedConversationId,
    nextTelemetryLog,
  };
}

export function persistInboxTurnFeedback(params: {
  readonly turnId: string;
  readonly feedback: "LIKE" | "DISLIKE" | null;
  readonly activeWorkspaceId: string;
  readonly isFr: boolean;
  readonly onFeedbackBanner: (message: string) => void;
}): {
  readonly nextConversations: readonly SavedAssistantConversation[];
  readonly nextTelemetryLog: readonly UiAssistantPromptTelemetryRecord[];
} {
  const nextConversations = updateTurnFeedbackInSavedConversations(
    params.turnId,
    params.feedback,
  );
  const nextTelemetryLog = updatePromptTelemetryFeedback(
    params.turnId,
    params.feedback,
  );
  const client = createOrciaApiClient({ baseUrl: "" });
  void client
    .recordAssistantTurnFeedback({
      workspace_id:
        params.activeWorkspaceId || "0195f000-0000-7000-8000-000000000301",
      turn_id: params.turnId,
      user_feedback: params.feedback,
    })
    .catch((err: unknown) => {
      const detail =
        err instanceof Error ? err.message : "Synchronisation locale";
      params.onFeedbackBanner(
        params.isFr
          ? `ℹ️ Avis enregistré localement (${detail}).`
          : `ℹ️ Feedback saved locally (${detail}).`,
      );
    });
  return { nextConversations, nextTelemetryLog };
}
