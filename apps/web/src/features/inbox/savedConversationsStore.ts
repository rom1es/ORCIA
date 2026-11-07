import {
  DEFAULT_ASSISTANT_AGENT_OPTIONS,
  DEFAULT_ASSISTANT_SKILL_OPTIONS,
  DEFAULT_ORCIA_DOCUMENT_OPTIONS,
  type ControlCenterDatasourceItem,
  type UiAssistantAutocompleteOption,
  type UiAssistantModelOption,
  type UiAssistantOrciaDocumentOption,
  type UiAssistantRagCitationItem,
  type UiCatalogExplorerItemView,
  type UiInferenceEffort,
  type UiInferenceTier,
} from "@orcia/ui";

export function buildAssistantAutocompleteAndRagOptions(params: {
  readonly catalogItems: readonly UiCatalogExplorerItemView[];
  readonly datasources: readonly ControlCenterDatasourceItem[];
}): {
  readonly agentOptions: readonly UiAssistantAutocompleteOption[];
  readonly skillOptions: readonly UiAssistantAutocompleteOption[];
  readonly orciaDocuments: readonly UiAssistantOrciaDocumentOption[];
  readonly ragCitations: readonly UiAssistantRagCitationItem[];
} {
  const catalogAgents: readonly UiAssistantAutocompleteOption[] = params.catalogItems
    .filter((item) => item.resourceType === "agent")
    .map((item) => ({
      slug: item.uri.split("/").pop() ?? item.resourceId,
      label: item.title,
      description: item.description,
      kind: "agent" as const,
    }));
  const catalogSkills: readonly UiAssistantAutocompleteOption[] = params.catalogItems
    .filter((item) => item.resourceType === "skill")
    .map((item) => ({
      slug: item.uri.split("/").pop() ?? item.resourceId,
      label: item.title,
      description: item.description,
      kind: "skill" as const,
    }));
  const agentOptions: readonly UiAssistantAutocompleteOption[] = [
    ...DEFAULT_ASSISTANT_AGENT_OPTIONS,
    ...catalogAgents.filter(
      (ca) => !DEFAULT_ASSISTANT_AGENT_OPTIONS.some((d) => d.slug === ca.slug),
    ),
  ];
  const skillOptions: readonly UiAssistantAutocompleteOption[] = [
    ...DEFAULT_ASSISTANT_SKILL_OPTIONS,
    ...catalogSkills.filter(
      (cs) => !DEFAULT_ASSISTANT_SKILL_OPTIONS.some((d) => d.slug === cs.slug),
    ),
  ];
  const orciaDocuments: readonly UiAssistantOrciaDocumentOption[] =
    params.datasources.length > 0
      ? params.datasources.map((ds) => ({
          id: ds.id,
          title: ds.alias,
          uri: ds.uri,
        }))
      : DEFAULT_ORCIA_DOCUMENT_OPTIONS;
  const ragCitations: readonly UiAssistantRagCitationItem[] =
    params.datasources.length > 0
      ? params.datasources.map((ds) => ({
          title: ds.alias,
          uri: ds.uri,
        }))
      : DEFAULT_ORCIA_DOCUMENT_OPTIONS.map((d) => ({
          title: d.title,
          uri: d.uri,
        }));
  return { agentOptions, skillOptions, orciaDocuments, ragCitations };
}

export const SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY =
  "orcia.assistant_saved_conversations.v1";

const fallbackConversationStorage = new Map<string, string>();

export interface SavedConversationTurnItem {
  readonly turnId: string;
  readonly userPrompt: string;
  readonly assistantReply: string;
  readonly modelTier: UiInferenceTier;
  readonly modelLabel: string;
  readonly thinkingEffort: UiInferenceEffort;
  readonly effortLabel: string;
  readonly timestampIso: string;
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
      raw = window.localStorage.getItem(SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY);
    } catch {
      // Fall back to in-memory map
    }
  }
  if (!raw) {
    raw = fallbackConversationStorage.get(SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY) ?? null;
  }
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
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
  fallbackConversationStorage.set(SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY, serialized);
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.setItem === "function"
  ) {
    try {
      window.localStorage.setItem(SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY, serialized);
    } catch {
      // Ignore storage quota errors
    }
  }
}

export function summarizePromptAsConversationTitle(prompt: string): string {
  const clean = prompt.replace(/\s+/g, " ").trim();
  if (!clean) {
    return "Nouvelle conversation";
  }
  return clean.length > 64 ? `${clean.slice(0, 61)}...` : clean;
}

export function buildAssistantModelOptions(
  llmTiers: readonly { readonly tier: string; readonly primaryModel?: string }[],
  isFr: boolean,
): readonly UiAssistantModelOption[] {
  const findModel = (tierKey: UiInferenceTier): string | undefined => {
    const exact = llmTiers.find((t) => t.tier === tierKey);
    return exact?.primaryModel || llmTiers[0]?.primaryModel;
  };
  return [
    {
      tier: "simple",
      title: isFr ? "Rapide" : "Fast",
      subtitle: isFr ? "Réponses les plus rapides" : "Fastest answers",
      ...(findModel("simple")
        ? { configuredModelName: findModel("simple") }
        : {}),
    },
    {
      tier: "medium",
      title: isFr ? "Polyvalent" : "Versatile",
      subtitle: isFr
        ? "Aide polyvalente au quotidien"
        : "Everyday versatile assistance",
      ...(findModel("medium")
        ? { configuredModelName: findModel("medium") }
        : {}),
    },
    {
      tier: "complex",
      title: isFr ? "Raisonnement avancé" : "Advanced reasoning",
      subtitle: isFr
        ? "Tâches complexes & analyse critique"
        : "Complex tasks & critical analysis",
      ...(findModel("complex")
        ? { configuredModelName: findModel("complex") }
        : {}),
    },
  ];
}

export function upsertTurnIntoSavedConversations(params: {
  readonly prevConversations: readonly SavedAssistantConversation[];
  readonly activeConversationId: string | null;
  readonly activeWorkspaceId: string;
  readonly activeFolderId: string;
  readonly modelOptions: readonly UiAssistantModelOption[];
  readonly isFr: boolean;
  readonly userPrompt: string;
  readonly assistantReply: string;
  readonly requestedTier: UiInferenceTier;
  readonly thinkingEffort: UiInferenceEffort;
}): {
  readonly nextConversations: readonly SavedAssistantConversation[];
  readonly resolvedConversationId: string;
  readonly isNewConversation: boolean;
  readonly createdTitle: string;
} {
  const modelOpt =
    params.modelOptions.find((m) => m.tier === params.requestedTier) ??
    params.modelOptions[1]!;
  const modelLabel = modelOpt.configuredModelName
    ? `${modelOpt.title} (${modelOpt.configuredModelName})`
    : modelOpt.title;
  const effortLabel =
    params.thinkingEffort === "deep"
      ? params.isFr
        ? "Réflexion Élevée"
        : "High effort"
      : params.thinkingEffort === "balanced"
        ? params.isFr
          ? "Réflexion Moyenne"
          : "Medium effort"
        : params.isFr
          ? "Réflexion Basse"
          : "Low effort";
  const nowIso = new Date().toISOString();
  const newTurn: SavedConversationTurnItem = {
    turnId: `turn-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    userPrompt: params.userPrompt,
    assistantReply: params.assistantReply,
    modelTier: params.requestedTier,
    modelLabel,
    thinkingEffort: params.thinkingEffort,
    effortLabel,
    timestampIso: nowIso,
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
      thinkingEffort: params.thinkingEffort,
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
    thinkingEffort: params.thinkingEffort,
    turns: [newTurn],
  };
  const nextList = [createdConv, ...params.prevConversations];
  writeSavedAssistantConversations(nextList);
  return {
    nextConversations: nextList,
    resolvedConversationId: convId,
    isNewConversation: true,
    createdTitle,
  };
}
