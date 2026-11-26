import type {
  ControlCenterDatasourceItem,
  UiAssistantAutocompleteOption,
  UiAssistantAutocompleteSuggestion,
  UiAssistantModelOption,
  UiAssistantOrciaDocumentOption,
  UiAssistantRagCitationItem,
  UiCatalogExplorerItemView,
  UiInferenceTier,
} from "@orcia/ui";
import {
  consumeAssistantPrefillPrompt,
  readCachedAgentsAndSkills,
} from "../../components/agentsAndSkillsBridgeStore";
import { resolveDictionaryForFlag } from "../../i18n";

export function buildAssistantAutocompleteAndRagOptions(params: {
  readonly catalogItems: readonly UiCatalogExplorerItemView[];
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly isFr?: boolean;
}): {
  readonly agentOptions: readonly UiAssistantAutocompleteOption[];
  readonly skillOptions: readonly UiAssistantAutocompleteOption[];
  readonly orciaDocuments: readonly UiAssistantOrciaDocumentOption[];
  readonly ragCitations: readonly UiAssistantRagCitationItem[];
} {
  const autoCopy = resolveDictionaryForFlag(params.isFr ?? true).featureInboxAssistant.autocomplete;
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
    ...autoCopy.defaultAgents,
    ...catalogAgents.filter(
      (ca) => !autoCopy.defaultAgents.some((d) => d.slug === ca.slug),
    ),
  ];
  const skillOptions: readonly UiAssistantAutocompleteOption[] = [
    ...autoCopy.defaultSkills,
    ...catalogSkills.filter(
      (cs) => !autoCopy.defaultSkills.some((d) => d.slug === cs.slug),
    ),
  ];
  const orciaDocuments: readonly UiAssistantOrciaDocumentOption[] =
    params.datasources.map((ds) => ({
      id: ds.id,
      title: ds.alias,
      uri: ds.uri,
    }));
  return { agentOptions, skillOptions, orciaDocuments, ragCitations: [] };
}

export function buildAssistantModelOptions(
  llmTiers: readonly { readonly tier: string; readonly primaryModel?: string }[],
  isFr: boolean,
): readonly UiAssistantModelOption[] {
  const autoCopy = resolveDictionaryForFlag(isFr).featureInboxAssistant.autocomplete;
  const configuredTiers = llmTiers.filter((t) => Boolean(t.primaryModel?.trim()));
  const distinctModels = new Set(
    configuredTiers.map((t) => t.primaryModel!.trim()),
  );
  const singleModelOnly =
    distinctModels.size === 1 ? [...distinctModels][0] : undefined;

  if (singleModelOnly) {
    const sub = autoCopy.configuredModelSubtitle;
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
    buildEntry("simple", autoCopy.tierSimpleTitle, autoCopy.tierSimpleSubtitle),
    buildEntry("medium", autoCopy.tierMediumTitle, autoCopy.tierMediumSubtitle),
    buildEntry("complex", autoCopy.tierComplexTitle, autoCopy.tierComplexSubtitle),
  ];
}

export function consumeAssistantPrefillFromStorage(): string | null {
  return consumeAssistantPrefillPrompt();
}

export function buildAssistantAutocompleteSuggestions(
  _activePacks: readonly { readonly packKey: string }[] = [],
  isFr = true,
): readonly UiAssistantAutocompleteSuggestion[] {
  const autoCopy = resolveDictionaryForFlag(isFr).featureInboxAssistant.autocomplete;
  const suggestions: UiAssistantAutocompleteSuggestion[] = [];
  const seenTokens = new Set<string>();
  const cached = readCachedAgentsAndSkills();

  const resolveScopeBadge = (scope: string | undefined, sourcePackKey?: string | null) =>
    scope === "PRIVATE"
      ? autoCopy.badgePrivate
      : scope === "PACK"
        ? (sourcePackKey ?? autoCopy.badgePackDefault)
        : autoCopy.badgeTeam;

  for (const ag of cached.agents ?? []) {
    if (ag.lifecycleStatus === "DRAFT" || ag.enabledOnWorkspace === false) continue;
    if (seenTokens.has(ag.handle)) continue;
    seenTokens.add(ag.handle);
    suggestions.push({
      id: ag.agentId,
      kind: "agent",
      token: ag.handle,
      name: ag.name,
      description: ag.roleMission,
      badge: resolveScopeBadge(ag.visibilityScope, ag.sourcePackKey),
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
      badge: resolveScopeBadge(sk.visibilityScope, sk.sourcePackKey),
    });
  }
  return suggestions;
}
