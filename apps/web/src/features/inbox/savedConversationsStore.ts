import {
  sanitizeAssistantDisplayReply,
  type UiAgentTraceEventItem,
  type UiAssistantAttachedFileItem,
  type UiAssistantModelOption,
  type UiAssistantRagCitationItem,
  type UiInferenceEffort,
  type UiInferenceTier,
  type UiThreeSpeedStepProgress,
} from "@orcia/ui";

export {
  buildAssistantAutocompleteAndRagOptions,
  buildAssistantAutocompleteSuggestions,
  buildAssistantModelOptions,
  consumeAssistantPrefillFromStorage,
  filterUsedRagSourcesForTurn,
} from "./assistantAutocompleteHelpers";

export const SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY =
  "orcia.assistant_saved_conversations.v1";

const fallbackConversationStorage = new Map<string, string>();

export interface SavedConversationTurnItem {
  readonly turnId: string;
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
  readonly stepProgress?: readonly UiThreeSpeedStepProgress[];
  readonly thinkingElapsedSeconds?: number;
  readonly reflexiveExecutionId?: string;
  readonly reflexiveTraceEvents?: readonly UiAgentTraceEventItem[];
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
  fallbackConversationStorage.clear();
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.removeItem === "function"
  ) {
    try {
      window.localStorage.removeItem(SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY);
    } catch {
      // Ignore storage errors
    }
  }
}

export function readSavedAssistantConversations(): readonly SavedAssistantConversation[] {
  let raw: string | null = null;
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.getItem === "function"
  ) {
    try {
      raw = window.localStorage.getItem(
        SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY,
      );
    } catch {
      // Fall back to in-memory map
    }
  }
  if (!raw) {
    raw =
      fallbackConversationStorage.get(
        SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY,
      ) ?? null;
  }
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (item): item is SavedAssistantConversation =>
        typeof item === "object" &&
        item !== null &&
        typeof (item as SavedAssistantConversation).id === "string" &&
        typeof (item as SavedAssistantConversation).title === "string" &&
        Array.isArray((item as SavedAssistantConversation).turns),
    );
  } catch {
    return [];
  }
}

export function writeSavedAssistantConversations(
  conversations: readonly SavedAssistantConversation[],
): void {
  const serialized = JSON.stringify(conversations);
  fallbackConversationStorage.set(
    SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY,
    serialized,
  );
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.setItem === "function"
  ) {
    try {
      window.localStorage.setItem(
        SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY,
        serialized,
      );
    } catch {
      // Ignore storage quota errors
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
  readonly userPrompt: string;
  readonly assistantReply: string;
  readonly assembledSystemPrompt?: string;
  readonly requestedTier: UiInferenceTier;
  readonly thinkingEffort: UiInferenceEffort;
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[];
  readonly usedSources?: readonly UiAssistantRagCitationItem[];
  readonly stepProgress?: readonly UiThreeSpeedStepProgress[];
  readonly thinkingElapsedSeconds?: number;
  readonly reflexiveExecutionId?: string;
  readonly reflexiveTraceEvents?: readonly UiAgentTraceEventItem[];
}): {
  readonly nextConversations: readonly SavedAssistantConversation[];
  readonly resolvedConversationId: string;
  readonly createdTurn: SavedConversationTurnItem;
  readonly isNewConversation: boolean;
  readonly createdTitle: string;
} {
  const modelOpt =
    params.modelOptions.find((m) => m.tier === params.requestedTier) ??
    params.modelOptions[1]!;
  const modelLabel =
    modelOpt.configuredModelName &&
    modelOpt.title !== modelOpt.configuredModelName
      ? `${modelOpt.title} (${modelOpt.configuredModelName})`
      : modelOpt.configuredModelName || modelOpt.title;
  const effortLabel =
    params.thinkingEffort === "deep"
      ? params.isFr
        ? "Approfondi"
        : "In-depth"
      : "Standard";
  const nowIso = new Date().toISOString();
  const cleanReply = sanitizeAssistantDisplayReply(params.assistantReply);
  const normalizedEffort: UiInferenceEffort =
    params.thinkingEffort === "deep" ? "deep" : "balanced";
  const newTurn: SavedConversationTurnItem = {
    turnId:
      params.turnId ||
      `turn-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    userPrompt: params.userPrompt,
    assistantReply: cleanReply,
    ...(params.assembledSystemPrompt
      ? { assembledSystemPrompt: params.assembledSystemPrompt }
      : {}),
    modelTier: params.requestedTier,
    modelLabel,
    thinkingEffort: normalizedEffort,
    effortLabel,
    timestampIso: nowIso,
    ...(params.attachedFiles && params.attachedFiles.length > 0
      ? { attachedFiles: params.attachedFiles }
      : {}),
    ...(params.usedSources && params.usedSources.length > 0
      ? { usedSources: params.usedSources }
      : {}),
    ...(params.stepProgress && params.stepProgress.length > 0
      ? { stepProgress: params.stepProgress }
      : {}),
    ...(params.thinkingElapsedSeconds !== undefined
      ? { thinkingElapsedSeconds: params.thinkingElapsedSeconds }
      : {}),
    ...(params.reflexiveExecutionId
      ? { reflexiveExecutionId: params.reflexiveExecutionId }
      : {}),
    ...(params.reflexiveTraceEvents && params.reflexiveTraceEvents.length > 0
      ? { reflexiveTraceEvents: params.reflexiveTraceEvents }
      : {}),
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
      turns: [...existing.turns, newTurn],
    };
    const nextList = [
      updatedConv,
      ...params.prevConversations.filter((c) => c.id !== existing.id),
    ];
    writeSavedAssistantConversations(nextList);
    return {
      nextConversations: nextList,
      resolvedConversationId: existing.id,
      createdTurn: newTurn,
      isNewConversation: false,
      createdTitle: existing.title,
    };
  }

  const convId = `conv-${params.prevConversations.length + 1}-${Date.now()}`;
  const createdTitle = summarizePromptAsConversationTitle(params.userPrompt);
  const createdConv: SavedAssistantConversation = {
    id: convId,
    workspaceId: params.activeWorkspaceId || "ws-default",
    ...(params.activeFolderId ? { folderId: params.activeFolderId } : {}),
    title: createdTitle,
    createdAtIso: nowIso,
    updatedAtIso: nowIso,
    modelTier: params.requestedTier,
    modelLabel,
    thinkingEffort: normalizedEffort,
    turns: [newTurn],
  };
  const nextList = [createdConv, ...params.prevConversations];
  writeSavedAssistantConversations(nextList);
  return {
    nextConversations: nextList,
    resolvedConversationId: convId,
    createdTurn: newTurn,
    isNewConversation: true,
    createdTitle,
  };
}

export function attachReflexiveTraceToConversationLatestTurn(
  conversationId: string | null,
  executionId: string,
  traceEvents: readonly UiAgentTraceEventItem[],
): readonly SavedAssistantConversation[] {
  const current = readSavedAssistantConversations();
  if (!conversationId || traceEvents.length === 0) return current;
  const next = current.map((conv) => {
    if (conv.id !== conversationId || conv.turns.length === 0) return conv;
    const lastIdx = conv.turns.length - 1;
    const updatedTurns = conv.turns.map((t, idx) =>
      idx === lastIdx
        ? {
            ...t,
            reflexiveExecutionId: executionId,
            reflexiveTraceEvents: traceEvents,
          }
        : t,
    );
    return { ...conv, turns: updatedTurns };
  });
  writeSavedAssistantConversations(next);
  return next;
}

export function updateTurnFeedbackInSavedConversations(
  turnId: string,
  feedback: "LIKE" | "DISLIKE" | null,
): readonly SavedAssistantConversation[] {
  const current = readSavedAssistantConversations();
  const next = current.map((conv) => ({
    ...conv,
    turns: conv.turns.map((t) =>
      t.turnId === turnId ? { ...t, userFeedback: feedback } : t,
    ),
  }));
  writeSavedAssistantConversations(next);
  return next;
}
