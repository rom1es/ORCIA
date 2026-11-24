import { createOrciaApiClient } from "@orcia/api-client";
import type {
  UiAgentTraceEventItem,
  UiAssistantFolderItem,
  UiAssistantModelOption,
} from "@orcia/ui";
import { resolveDictionaryForFlag, resolveLocaleForFlag } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import { citationMapToRagItems } from "./inboxCitationHelpers";
import {
  updateTurnFeedbackInConversations,
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
  readonly isFr: boolean;
  readonly reflexiveExecutionId: string | null;
  readonly reflexiveEvents: readonly UiAgentTraceEventItem[];
}): {
  readonly nextConversations: readonly SavedAssistantConversation[];
  readonly resolvedConversationId: string;
} {
  const { completed } = params;
  const usedSources = citationMapToRagItems(completed.citationMap);
  const resolvedConvIdInput = completed.threadId ?? params.activeConversationId;
  const outcome = upsertTurnIntoSavedConversations({
    prevConversations: params.savedConversations,
    activeConversationId: resolvedConvIdInput,
    activeWorkspaceId: params.activeWorkspaceId,
    activeFolderId: params.activeFolderId,
    modelOptions: params.modelOptions,
    isFr: params.isFr,
    ...(completed.turnId ? { turnId: completed.turnId } : {}),
    ...(completed.parentTurnId ? { parentTurnId: completed.parentTurnId } : {}),
    userPrompt: completed.userPrompt,
    assistantReply: completed.assistantReply,
    ...(completed.assembledSystemPrompt
      ? { assembledSystemPrompt: completed.assembledSystemPrompt }
      : {}),
    requestedTier: completed.requestedTier,
    thinkingEffort: completed.thinkingEffort,
    ...(completed.attachedFiles ? { attachedFiles: completed.attachedFiles } : {}),
    usedSources,
    ...(completed.citationMap !== undefined ? { citationMap: completed.citationMap } : {}),
    ...(completed.lowEvidence !== undefined ? { lowEvidence: completed.lowEvidence } : {}),
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
    ...(completed.toolCallSteps && completed.toolCallSteps.length > 0
      ? { toolCallSteps: completed.toolCallSteps }
      : {}),
    ...(completed.approvalProposal ? { approvalProposal: completed.approvalProposal } : {}),
  });

  return {
    nextConversations: outcome.nextConversations,
    resolvedConversationId: outcome.resolvedConversationId,
  };
}

export function persistInboxTurnFeedback(params: {
  readonly conversations: readonly SavedAssistantConversation[];
  readonly turnId: string;
  readonly feedback: "LIKE" | "DISLIKE" | null;
  readonly activeWorkspaceId: string;
  readonly isFr: boolean;
  readonly onFeedbackBanner: (message: string) => void;
}): {
  readonly nextConversations: readonly SavedAssistantConversation[];
} {
  const nextConversations = updateTurnFeedbackInConversations(
    params.conversations,
    params.turnId,
    params.feedback,
  );
  const client = createOrciaApiClient({ baseUrl: "" });
  if (params.feedback === "LIKE" || params.feedback === "DISLIKE") {
    void client
      .recordAssistantTurnFeedback(params.turnId, {
        workspace_id: params.activeWorkspaceId,
        rating: params.feedback === "LIKE" ? "up" : "down",
      })
      .catch((err: unknown) => {
        const resolvedLocale = resolveLocaleForFlag(params.isFr);
        const context = resolveDictionaryForFlag(params.isFr, resolvedLocale).featureInboxAssistant.assistantFlow.feedbackErrorContext;
        params.onFeedbackBanner(
          formatRfc9457ErrorToBanner(err, resolvedLocale, context).fullText,
        );
      });
  }
  return { nextConversations };
}
