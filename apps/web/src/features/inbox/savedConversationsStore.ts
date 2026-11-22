import {
  sanitizeAssistantDisplayReply,
  type UiAgentTraceEventItem,
  type UiAssistantApprovalProposal,
  type UiAssistantAttachedFileItem,
  type UiAssistantModelOption,
  type UiAssistantRagCitationItem,
  type UiAssistantToolCallStepItem,
  type UiInferenceEffort,
  type UiInferenceTier,
  type UiThreeSpeedStepProgress,
} from "@orcia/ui";
import { ignoreBenignStorageError } from "../../utils/benignBrowserError";

export {
  buildAssistantAutocompleteAndRagOptions,
  buildAssistantAutocompleteSuggestions,
  buildAssistantModelOptions,
  consumeAssistantPrefillFromStorage,
} from "./assistantAutocompleteHelpers";

export const SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY =
  "orcia.assistant_saved_conversations.v1";

export interface SavedConversationTurnItem {
  readonly turnId: string;
  readonly parentTurnId?: string | null;
  readonly userPrompt: string;
  readonly assistantReply: string;
  readonly assembledSystemPrompt?: string;
  readonly userFeedback?: "LIKE" | "DISLIKE" | null;
  readonly modelTier: UiInferenceTier;
  readonly modelLabel: string;
  readonly thinkingEffort: UiInferenceEffort;
  readonly effortLabel: string;
  readonly timestampIso: string;
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[];
  readonly usedSources?: readonly UiAssistantRagCitationItem[];
  readonly citationMap?: unknown;
  readonly lowEvidence?: boolean;
  readonly stepProgress?: readonly UiThreeSpeedStepProgress[];
  readonly thinkingElapsedSeconds?: number;
  readonly reflexiveExecutionId?: string;
  readonly reflexiveTraceEvents?: readonly UiAgentTraceEventItem[];
  readonly toolCallSteps?: readonly UiAssistantToolCallStepItem[];
  readonly approvalProposal?: UiAssistantApprovalProposal | null;
}

export interface SavedAssistantConversation {
  readonly id: string;
  readonly workspaceId: string;
  readonly folderId?: string;
  readonly title: string;
  readonly createdAtIso: string;
  readonly updatedAtIso: string;
  readonly modelTier: UiInferenceTier;
  readonly modelLabel: string;
  readonly thinkingEffort: UiInferenceEffort;
  readonly turns: readonly SavedConversationTurnItem[];
}

export function clearSavedAssistantConversationsStorage(): void {
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.removeItem === "function"
  ) {
    try {
      window.localStorage.removeItem(SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY);
    } catch (err: unknown) {
      ignoreBenignStorageError("savedConversations.clear", err);
    }
  }
}

export function summarizePromptAsConversationTitle(prompt: string): string {
  const clean = prompt.replace(/\s+/g, " ").trim();
  if (!clean) return "Nouvelle conversation";
  return clean.length > 64 ? `${clean.slice(0, 61)}...` : clean;
}

export function upsertTurnIntoSavedConversations(params: {
  readonly prevConversations: readonly SavedAssistantConversation[];
  readonly activeConversationId: string | null;
  readonly activeWorkspaceId: string;
  readonly activeFolderId: string;
  readonly modelOptions: readonly UiAssistantModelOption[];
  readonly isFr: boolean;
  readonly turnId?: string;
  readonly parentTurnId?: string | null;
  readonly userPrompt: string;
  readonly assistantReply: string;
  readonly assembledSystemPrompt?: string;
  readonly requestedTier: UiInferenceTier;
  readonly thinkingEffort: UiInferenceEffort;
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[];
  readonly usedSources?: readonly UiAssistantRagCitationItem[];
  readonly citationMap?: unknown;
  readonly lowEvidence?: boolean;
  readonly stepProgress?: readonly UiThreeSpeedStepProgress[];
  readonly thinkingElapsedSeconds?: number;
  readonly reflexiveExecutionId?: string;
  readonly reflexiveTraceEvents?: readonly UiAgentTraceEventItem[];
  readonly toolCallSteps?: readonly UiAssistantToolCallStepItem[];
  readonly approvalProposal?: UiAssistantApprovalProposal | null;
}): {
  readonly nextConversations: readonly SavedAssistantConversation[];
  readonly resolvedConversationId: string;
  readonly createdTurn: SavedConversationTurnItem;
  readonly createdTitle: string;
} {
  const modelOpt =
    params.modelOptions.find((m) => m.tier === params.requestedTier) ?? params.modelOptions[1]!;
  const modelLabel =
    modelOpt.configuredModelName && modelOpt.title !== modelOpt.configuredModelName
      ? `${modelOpt.title} (${modelOpt.configuredModelName})`
      : modelOpt.configuredModelName || modelOpt.title;
  const effortLabel =
    params.thinkingEffort === "deep" ? (params.isFr ? "Approfondi" : "In-depth") : "Standard";
  const nowIso = new Date().toISOString();
  const cleanReply = sanitizeAssistantDisplayReply(params.assistantReply);
  const normalizedEffort: UiInferenceEffort =
    params.thinkingEffort === "deep" ? "deep" : "balanced";
  const newTurn: SavedConversationTurnItem = {
    turnId: params.turnId || `turn-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    ...(params.parentTurnId ? { parentTurnId: params.parentTurnId } : {}),
    userPrompt: params.userPrompt,
    assistantReply: cleanReply,
    ...(params.assembledSystemPrompt ? { assembledSystemPrompt: params.assembledSystemPrompt } : {}),
    modelTier: params.requestedTier,
    modelLabel,
    thinkingEffort: normalizedEffort,
    effortLabel,
    timestampIso: nowIso,
    ...(params.attachedFiles && params.attachedFiles.length > 0 ? { attachedFiles: params.attachedFiles } : {}),
    ...(params.usedSources && params.usedSources.length > 0 ? { usedSources: params.usedSources } : {}),
    ...(params.citationMap !== undefined ? { citationMap: params.citationMap } : {}),
    ...(params.lowEvidence !== undefined ? { lowEvidence: params.lowEvidence } : {}),
    ...(params.stepProgress && params.stepProgress.length > 0 ? { stepProgress: params.stepProgress } : {}),
    ...(params.thinkingElapsedSeconds !== undefined ? { thinkingElapsedSeconds: params.thinkingElapsedSeconds } : {}),
    ...(params.reflexiveExecutionId ? { reflexiveExecutionId: params.reflexiveExecutionId } : {}),
    ...(params.reflexiveTraceEvents && params.reflexiveTraceEvents.length > 0
      ? { reflexiveTraceEvents: params.reflexiveTraceEvents }
      : {}),
    ...(params.toolCallSteps && params.toolCallSteps.length > 0 ? { toolCallSteps: params.toolCallSteps } : {}),
    ...(params.approvalProposal ? { approvalProposal: params.approvalProposal } : {}),
  };

  const existing = params.activeConversationId
    ? params.prevConversations.find((c) => c.id === params.activeConversationId)
    : undefined;
  if (existing) {
    const updatedConv: SavedAssistantConversation = {
      ...existing,
      updatedAtIso: nowIso,
      modelTier: params.requestedTier,
      modelLabel,
      thinkingEffort: normalizedEffort,
      turns: [...existing.turns.filter((t) => t.turnId !== newTurn.turnId), newTurn],
    };
    const nextList = [updatedConv, ...params.prevConversations.filter((c) => c.id !== existing.id)];
    return {
      nextConversations: nextList,
      resolvedConversationId: existing.id,
      createdTurn: newTurn,
      createdTitle: existing.title,
    };
  }

  const convId = params.activeConversationId ?? `thread-${Date.now()}`;
  const createdTitle = summarizePromptAsConversationTitle(params.userPrompt);
  const createdConv: SavedAssistantConversation = {
    id: convId,
    workspaceId: params.activeWorkspaceId,
    ...(params.activeFolderId ? { folderId: params.activeFolderId } : {}),
    title: createdTitle,
    createdAtIso: nowIso,
    updatedAtIso: nowIso,
    modelTier: params.requestedTier,
    modelLabel,
    thinkingEffort: normalizedEffort,
    turns: [newTurn],
  };
  return {
    nextConversations: [createdConv, ...params.prevConversations],
    resolvedConversationId: convId,
    createdTurn: newTurn,
    createdTitle,
  };
}

export function updateTurnFeedbackInConversations(
  conversations: readonly SavedAssistantConversation[],
  turnId: string,
  feedback: "LIKE" | "DISLIKE" | null,
): readonly SavedAssistantConversation[] {
  return conversations.map((conv) => ({
    ...conv,
    turns: conv.turns.map((t) => (t.turnId === turnId ? { ...t, userFeedback: feedback } : t)),
  }));
}
