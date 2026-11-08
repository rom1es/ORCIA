import {
  DEFAULT_ASSISTANT_AGENT_OPTIONS,
  DEFAULT_ASSISTANT_SKILL_OPTIONS,
  DEFAULT_ORCIA_DOCUMENT_OPTIONS,
  sanitizeAssistantDisplayReply,
  type ControlCenterDatasourceItem,
  type UiAssistantAttachedFileItem,
  type UiAssistantAutocompleteOption,
  type UiAssistantAutocompleteSuggestion,
  type UiAssistantModelOption,
  type UiAssistantOrciaDocumentOption,
  type UiAssistantRagCitationItem,
  type UiCatalogExplorerItemView,
  type UiInferenceEffort,
  type UiInferenceTier,
  type UiThreeSpeedStepProgress,
} from "@orcia/ui";
import {
  consumeAssistantPrefillPrompt,
  readCachedAgentsAndSkills,
} from "../../components/agentsAndSkillsBridgeStore";

export function filterUsedRagSourcesForTurn(params: {
  readonly userPrompt: string;
  readonly assistantReply: string;
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[];
}): readonly UiAssistantRagCitationItem[] {
  const results: UiAssistantRagCitationItem[] = [];
  const seenUris = new Set<string>();

  for (const file of params.attachedFiles ?? []) {
    const uri = file.uri ?? `#local-file-${encodeURIComponent(file.name)}`;
    if (!seenUris.has(uri)) {
      seenUris.add(uri);
      results.push({ title: file.name, uri });
    }
  }

  const combinedLower = `${params.userPrompt} ${params.assistantReply}`.toLowerCase();
  for (const ds of params.datasources) {
    if (seenUris.has(ds.uri)) continue;
    const aliasLower = ds.alias.toLowerCase();
    const significantTokens = aliasLower
      .split(/[^a-zA-Z0-9àâäéèêëîïôöùûüç]+/)
      .filter((tok) => tok.length > 4);
    if (
      combinedLower.includes(aliasLower) ||
      significantTokens.some((tok) => combinedLower.includes(tok))
    ) {
      seenUris.add(ds.uri);
      results.push({ title: ds.alias, uri: ds.uri });
    }
  }
  return results;
}

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
    ...catalogAgents.filter((ca) => !DEFAULT_ASSISTANT_AGENT_OPTIONS.some((d) => d.slug === ca.slug)),
  ];
  const skillOptions: readonly UiAssistantAutocompleteOption[] = [
    ...DEFAULT_ASSISTANT_SKILL_OPTIONS,
    ...catalogSkills.filter((cs) => !DEFAULT_ASSISTANT_SKILL_OPTIONS.some((d) => d.slug === cs.slug)),
  ];
  const orciaDocuments: readonly UiAssistantOrciaDocumentOption[] =
    params.datasources.length > 0
      ? params.datasources.map((ds) => ({ id: ds.id, title: ds.alias, uri: ds.uri }))
      : DEFAULT_ORCIA_DOCUMENT_OPTIONS;
  return { agentOptions, skillOptions, orciaDocuments, ragCitations: [] };
}

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
  if (typeof window !== "undefined" && window.localStorage && typeof window.localStorage.removeItem === "function") {
    try {
      window.localStorage.removeItem(SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY);
    } catch {
      // Ignore storage errors
    }
  }
}

export function readSavedAssistantConversations(): readonly SavedAssistantConversation[] {
  let raw: string | null = null;
  if (typeof window !== "undefined" && window.localStorage && typeof window.localStorage.getItem === "function") {
    try {
      raw = window.localStorage.getItem(SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY);
    } catch {
      // Fall back to in-memory map
    }
  }
  if (!raw) {
    raw = fallbackConversationStorage.get(SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY) ?? null;
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

export function writeSavedAssistantConversations(conversations: readonly SavedAssistantConversation[]): void {
  const serialized = JSON.stringify(conversations);
  fallbackConversationStorage.set(SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY, serialized);
  if (typeof window !== "undefined" && window.localStorage && typeof window.localStorage.setItem === "function") {
    try {
      window.localStorage.setItem(SAVED_ASSISTANT_CONVERSATIONS_STORAGE_KEY, serialized);
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

export function buildAssistantModelOptions(
  llmTiers: readonly { readonly tier: string; readonly primaryModel?: string }[],
  isFr: boolean,
): readonly UiAssistantModelOption[] {
  const configuredTiers = llmTiers.filter((t) => Boolean(t.primaryModel?.trim()));
  const distinctModels = new Set(configuredTiers.map((t) => t.primaryModel!.trim()));
  const singleModelOnly = distinctModels.size === 1 ? [...distinctModels][0] : undefined;

  if (singleModelOnly) {
    return [
      { tier: "simple", title: singleModelOnly, subtitle: isFr ? "Modèle IA configuré" : "Configured AI model", configuredModelName: singleModelOnly, hiddenDuplicate: true },
      { tier: "medium", title: singleModelOnly, subtitle: isFr ? "Modèle IA configuré" : "Configured AI model", configuredModelName: singleModelOnly },
      { tier: "complex", title: singleModelOnly, subtitle: isFr ? "Modèle IA configuré" : "Configured AI model", configuredModelName: singleModelOnly, hiddenDuplicate: true },
    ];
  }

  const seenModels = new Set<string>();
  const buildEntry = (tierKey: UiInferenceTier, title: string, subtitle: string): UiAssistantModelOption => {
    const modelName = configuredTiers.find((t) => t.tier === tierKey)?.primaryModel?.trim();
    const isDuplicate = configuredTiers.length > 0 && (!modelName || seenModels.has(modelName));
    if (modelName) seenModels.add(modelName);
    const enrichedSubtitle = modelName ? `${subtitle} · ${modelName}` : subtitle;
    return {
      tier: tierKey,
      title,
      subtitle: enrichedSubtitle,
      ...(modelName ? { configuredModelName: modelName } : {}),
      ...(isDuplicate ? { hiddenDuplicate: true } : {}),
    };
  };

  return [
    buildEntry("simple", isFr ? "Rapide" : "Fast", isFr ? "Réponses les plus rapides" : "Fastest answers"),
    buildEntry("medium", isFr ? "Polyvalent" : "Versatile", isFr ? "Aide polyvalente au quotidien" : "Everyday versatile assistance"),
    buildEntry("complex", isFr ? "Raisonnement avancé" : "Advanced reasoning", isFr ? "Tâches complexes & analyse critique" : "Complex tasks & critical analysis"),
  ];
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
}): {
  readonly nextConversations: readonly SavedAssistantConversation[];
  readonly resolvedConversationId: string;
  readonly createdTurn: SavedConversationTurnItem;
  readonly isNewConversation: boolean;
  readonly createdTitle: string;
} {
  const modelOpt = params.modelOptions.find((m) => m.tier === params.requestedTier) ?? params.modelOptions[1]!;
  const modelLabel =
    modelOpt.configuredModelName && modelOpt.title !== modelOpt.configuredModelName
      ? `${modelOpt.title} (${modelOpt.configuredModelName})`
      : modelOpt.configuredModelName || modelOpt.title;
  const effortLabel = params.thinkingEffort === "deep" ? (params.isFr ? "Approfondi" : "In-depth") : "Standard";
  const nowIso = new Date().toISOString();
  const cleanReply = sanitizeAssistantDisplayReply(params.assistantReply);
  const normalizedEffort: UiInferenceEffort = params.thinkingEffort === "deep" ? "deep" : "balanced";
  const newTurn: SavedConversationTurnItem = {
    turnId: params.turnId || `turn-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
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
    ...(params.stepProgress && params.stepProgress.length > 0 ? { stepProgress: params.stepProgress } : {}),
    ...(params.thinkingElapsedSeconds !== undefined ? { thinkingElapsedSeconds: params.thinkingElapsedSeconds } : {}),
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
    const nextList = [updatedConv, ...params.prevConversations.filter((c) => c.id !== existing.id)];
    writeSavedAssistantConversations(nextList);
    return { nextConversations: nextList, resolvedConversationId: existing.id, createdTurn: newTurn, isNewConversation: false, createdTitle: existing.title };
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
  return { nextConversations: nextList, resolvedConversationId: convId, createdTurn: newTurn, isNewConversation: true, createdTitle };
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

export function consumeAssistantPrefillFromStorage(): string | null {
  return consumeAssistantPrefillPrompt();
}

export function buildAssistantAutocompleteSuggestions(
  activePacks: readonly { readonly packKey: string }[] = [],
): readonly UiAssistantAutocompleteSuggestion[] {
  const suggestions: UiAssistantAutocompleteSuggestion[] = [];
  const seenTokens = new Set<string>();
  const cached = readCachedAgentsAndSkills();

  for (const ag of cached.agents ?? []) {
    if (seenTokens.has(ag.handle)) continue;
    seenTokens.add(ag.handle);
    suggestions.push({
      id: ag.agentId,
      kind: "agent",
      token: ag.handle,
      name: ag.name,
      description: ag.roleMission,
      badge: ag.visibilityScope === "PRIVATE" ? "🔒 Privé" : ag.visibilityScope === "PACK" ? `📦 ${ag.sourcePackKey ?? "Pack"}` : "👥 Équipe",
    });
  }
  for (const sk of cached.skills ?? []) {
    if (seenTokens.has(sk.commandHandle)) continue;
    seenTokens.add(sk.commandHandle);
    suggestions.push({
      id: sk.skillId,
      kind: "skill",
      token: sk.commandHandle,
      name: sk.name,
      description: sk.objective,
      badge: sk.visibilityScope === "PRIVATE" ? "🔒 Privé" : sk.visibilityScope === "PACK" ? `📦 ${sk.sourcePackKey ?? "Pack"}` : "👥 Équipe",
    });
  }
  for (const pack of activePacks) {
    if (pack.packKey === "orcia-pack-sdlc") {
      const sdlcDefaults: readonly UiAssistantAutocompleteSuggestion[] = [
        { id: "agent-architecte-solution", kind: "agent", token: "@architecte-solution", name: "Architecte Solution", description: "Concevoir et vérifier l'architecture cible", badge: "📦 orcia-pack-sdlc" },
        { id: "agent-analyste-metier", kind: "agent", token: "@analyste-metier", name: "Analyste Métier", description: "Clarifier les besoins et rédiger les exigences", badge: "📦 orcia-pack-sdlc" },
        { id: "skill-revue-architecture", kind: "skill", token: "/revue-architecture", name: "Revue d'Architecture", description: "Vérifier la cohérence des choix d'architecture", badge: "📦 orcia-pack-sdlc" },
      ];
      for (const item of sdlcDefaults) {
        if (!seenTokens.has(item.token)) {
          seenTokens.add(item.token);
          suggestions.push(item);
        }
      }
    }
  }
  return suggestions;
}
