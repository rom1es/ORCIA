import {
  DEFAULT_ASSISTANT_AGENT_OPTIONS,
  DEFAULT_ASSISTANT_SKILL_OPTIONS,
  DEFAULT_ORCIA_DOCUMENT_OPTIONS,
  type ControlCenterDatasourceItem,
  type UiAssistantAttachedFileItem,
  type UiAssistantAutocompleteOption,
  type UiAssistantAutocompleteSuggestion,
  type UiAssistantModelOption,
  type UiAssistantOrciaDocumentOption,
  type UiAssistantRagCitationItem,
  type UiCatalogExplorerItemView,
  type UiInferenceTier,
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

  const combinedLower =
    `${params.userPrompt} ${params.assistantReply}`.toLowerCase();
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
  const catalogAgents: readonly UiAssistantAutocompleteOption[] =
    params.catalogItems
      .filter((item) => item.resourceType === "agent")
      .map((item) => ({
        slug: item.uri.split("/").pop() ?? item.resourceId,
        label: item.title,
        description: item.description,
        kind: "agent" as const,
      }));
  const catalogSkills: readonly UiAssistantAutocompleteOption[] =
    params.catalogItems
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
  return { agentOptions, skillOptions, orciaDocuments, ragCitations: [] };
}

export function buildAssistantModelOptions(
  llmTiers: readonly { readonly tier: string; readonly primaryModel?: string }[],
  isFr: boolean,
): readonly UiAssistantModelOption[] {
  const configuredTiers = llmTiers.filter((t) => Boolean(t.primaryModel?.trim()));
  const distinctModels = new Set(
    configuredTiers.map((t) => t.primaryModel!.trim()),
  );
  const singleModelOnly =
    distinctModels.size === 1 ? [...distinctModels][0] : undefined;

  if (singleModelOnly) {
    const sub = isFr ? "Modèle IA configuré" : "Configured AI model";
    return [
      {
        tier: "simple",
        title: singleModelOnly,
        subtitle: sub,
        configuredModelName: singleModelOnly,
        hiddenDuplicate: true,
      },
      {
        tier: "medium",
        title: singleModelOnly,
        subtitle: sub,
        configuredModelName: singleModelOnly,
      },
      {
        tier: "complex",
        title: singleModelOnly,
        subtitle: sub,
        configuredModelName: singleModelOnly,
        hiddenDuplicate: true,
      },
    ];
  }

  const seenModels = new Set<string>();
  const buildEntry = (
    tierKey: UiInferenceTier,
    title: string,
    subtitle: string,
  ): UiAssistantModelOption => {
    const modelName = configuredTiers
      .find((t) => t.tier === tierKey)
      ?.primaryModel?.trim();
    const isDuplicate =
      configuredTiers.length > 0 && (!modelName || seenModels.has(modelName));
    if (modelName) seenModels.add(modelName);
    return {
      tier: tierKey,
      title,
      subtitle: modelName ? `${subtitle} · ${modelName}` : subtitle,
      ...(modelName ? { configuredModelName: modelName } : {}),
      ...(isDuplicate ? { hiddenDuplicate: true } : {}),
    };
  };

  return [
    buildEntry(
      "simple",
      isFr ? "Rapide" : "Fast",
      isFr ? "Réponses les plus rapides" : "Fastest answers",
    ),
    buildEntry(
      "medium",
      isFr ? "Polyvalent" : "Versatile",
      isFr ? "Aide polyvalente au quotidien" : "Everyday versatile assistance",
    ),
    buildEntry(
      "complex",
      isFr ? "Raisonnement avancé" : "Advanced reasoning",
      isFr
        ? "Tâches complexes & analyse critique"
        : "Complex tasks & critical analysis",
    ),
  ];
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
