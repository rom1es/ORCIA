import type {
  UiAssistantAutocompleteSuggestion,
  UiAssistantModelOption,
  UiInferenceEffort,
  UiInferenceTier,
} from "@orcia/ui";
import {
  consumeAssistantPrefillPrompt,
  readCachedAgentsAndSkills,
} from "../../components/agentsAndSkillsBridgeStore";

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
      badge:
        ag.visibilityScope === "PRIVATE"
          ? "🔒 Privé"
          : ag.visibilityScope === "PACK"
            ? `📦 ${ag.sourcePackKey ?? "Pack"}`
            : "👥 Équipe",
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
      badge:
        sk.visibilityScope === "PRIVATE"
          ? "🔒 Privé"
          : sk.visibilityScope === "PACK"
            ? `📦 ${sk.sourcePackKey ?? "Pack"}`
            : "👥 Équipe",
    });
  }

  for (const pack of activePacks) {
    if (pack.packKey === "orcia-pack-sdlc") {
      const sdlcDefaults: readonly UiAssistantAutocompleteSuggestion[] = [
        {
          id: "agent-architecte-solution",
          kind: "agent",
          token: "@architecte-solution",
          name: "Architecte Solution",
          description: "Concevoir et vérifier l'architecture cible",
          badge: "📦 orcia-pack-sdlc",
        },
        {
          id: "agent-analyste-metier",
          kind: "agent",
          token: "@analyste-metier",
          name: "Analyste Métier",
          description: "Clarifier les besoins et rédiger les exigences",
          badge: "📦 orcia-pack-sdlc",
        },
        {
          id: "skill-revue-architecture",
          kind: "skill",
          token: "/revue-architecture",
          name: "Revue d'Architecture",
          description: "Vérifier la cohérence des choix d'architecture",
          badge: "📦 orcia-pack-sdlc",
        },
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
