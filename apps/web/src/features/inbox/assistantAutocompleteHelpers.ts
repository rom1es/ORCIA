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
  const resolveCatalogItemSlug = (
    item: UiCatalogExplorerItemView,
    allOfType: readonly UiCatalogExplorerItemView[],
  ): string => {
    const shortSlug = item.uri.split("/").pop()?.split("@")[0] ?? item.resourceId;
    const collisionCount = allOfType.filter(
      (other) =>
        (other.uri.split("/").pop()?.split("@")[0] ?? other.resourceId) === shortSlug,
    ).length;
    if (collisionCount <= 1) return shortSlug;
    const match = /^orcia:\/\/packs\/([^/]+)\//i.exec(item.uri);
    const packSlug = match?.[1]?.toLowerCase() ?? "workspace";
    return `${packSlug}/${shortSlug}`;
  };

  const agentCatalogItems = params.catalogItems.filter(
    (item) => item.resourceType === "agent",
  );
  const skillCatalogItems = params.catalogItems.filter(
    (item) => item.resourceType === "skill",
  );
  const catalogAgents: readonly UiAssistantAutocompleteOption[] =
    agentCatalogItems.map((item) => ({
      slug: resolveCatalogItemSlug(item, agentCatalogItems),
      label: item.title,
      description: item.description,
      kind: "agent" as const,
    }));
  const catalogSkills: readonly UiAssistantAutocompleteOption[] =
    skillCatalogItems.map((item) => ({
      slug: resolveCatalogItemSlug(item, skillCatalogItems),
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

  const resolveScopeBadge = (
    scope: string | undefined,
    packSlug?: string | null,
    sourcePackKey?: string | null,
  ) =>
    scope === "PRIVATE"
      ? autoCopy.badgePrivate
      : scope === "PACK"
        ? (packSlug ?? sourcePackKey ?? autoCopy.badgePackDefault)
        : autoCopy.badgeTeam;

  const activeAgents = (cached.agents ?? []).filter(
    (ag) => ag.lifecycleStatus !== "DRAFT" && ag.enabledOnWorkspace !== false,
  );
  const agentSlugCounts = new Map<string, number>();
  for (const ag of activeAgents) {
    const key = ag.slug.trim().toLowerCase();
    agentSlugCounts.set(key, (agentSlugCounts.get(key) ?? 0) + 1);
  }
  for (const ag of activeAgents) {
    const key = ag.slug.trim().toLowerCase();
    const colliding = (agentSlugCounts.get(key) ?? 0) > 1 || Boolean(ag.isColliding);
    const originPack =
      ag.packSlug ??
      (ag.visibilityScope === "PACK"
        ? (ag.sourcePackKey?.replace(/^orcia-pack-/, "") ?? null)
        : null);
    const token = colliding
      ? ag.qualifiedRef?.trim() ||
        (originPack ? `@${originPack}/${ag.slug}` : `@workspace/${ag.slug}`)
      : ag.handle;
    if (seenTokens.has(token)) continue;
    seenTokens.add(token);
    suggestions.push({
      id: ag.agentId,
      kind: "agent",
      token,
      name: ag.name,
      description: ag.roleMission,
      badge: resolveScopeBadge(ag.visibilityScope, originPack, ag.sourcePackKey),
    });
  }

  const allSkills = cached.skills ?? [];
  const skillSlugCounts = new Map<string, number>();
  for (const sk of allSkills) {
    const key = sk.slug.trim().toLowerCase();
    skillSlugCounts.set(key, (skillSlugCounts.get(key) ?? 0) + 1);
  }
  for (const sk of allSkills) {
    const key = sk.slug.trim().toLowerCase();
    const colliding = (skillSlugCounts.get(key) ?? 0) > 1 || Boolean(sk.isColliding);
    const originPack =
      sk.packSlug ??
      (sk.visibilityScope === "PACK"
        ? (sk.sourcePackKey?.replace(/^orcia-pack-/, "") ?? null)
        : null);
    const token = colliding
      ? sk.qualifiedRef?.trim() ||
        (originPack ? `/${originPack}/${sk.slug}` : `/workspace/${sk.slug}`)
      : sk.commandHandle;
    if (seenTokens.has(token)) continue;
    seenTokens.add(token);
    suggestions.push({
      id: sk.skillId,
      kind: "skill",
      token,
      name: sk.name,
      description: sk.objective,
      badge: resolveScopeBadge(sk.visibilityScope, originPack, sk.sourcePackKey),
    });
  }
  return suggestions;
}
