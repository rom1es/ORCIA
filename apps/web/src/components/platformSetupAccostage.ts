import type {
  ControlCenterDatasourceItem,
  ControlCenterOverrideItem,
  ControlCenterWorkspaceGovItem,
  UiAccostageMilestoneItem,
} from "@orcia/ui";
import type { AccostagePg18CountsView } from "./platformSetupHydration";
import type {
  ConfiguredLlmTierMapping,
  ConfiguredOrgUnit,
  ConfiguredPackItem,
  ConfiguredPlatformAdmin,
  ConfiguredWorkflowItem,
} from "./platformSetupStorageHelpers";

export interface AccostageProgressSummary {
  readonly adminCreated: boolean;
  readonly hasModels: boolean;
  readonly hasOrgUnits: boolean;
  readonly hasWorkspaces: boolean;
  readonly hasSources: boolean;
  readonly hasWorkflows: boolean;
  readonly completedCount: number;
  readonly totalCount: 6;
  readonly isDay0Complete: boolean;
}

export function computeAccostageProgressSummary(params: {
  readonly accostageCounts: AccostagePg18CountsView | null;
  readonly platformAdmin: ConfiguredPlatformAdmin | null;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly llmTiers: readonly ConfiguredLlmTierMapping[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly workflows: readonly ConfiguredWorkflowItem[];
  readonly packs: readonly ConfiguredPackItem[];
}): AccostageProgressSummary {
  const {
    accostageCounts,
    platformAdmin,
    orgUnits,
    llmTiers,
    workspaces,
    datasources,
    workflows,
    packs,
  } = params;

  const adminCreated = Boolean(accostageCounts?.adminCreated || platformAdmin !== null);
  const hasModels = llmTiers.length > 0 || (accostageCounts?.modelsCount ?? 0) > 0;
  const hasOrgUnits =
    orgUnits.some((u) => u.level === "BU" || u.level === "TEAM") ||
    (accostageCounts?.orgUnitsCount ?? 0) > 0;
  const hasWorkspaces =
    workspaces.length > 0 || (accostageCounts?.workspacesCount ?? 0) > 0;
  const hasSources =
    datasources.length > 0 || (accostageCounts?.sourcesCount ?? 0) > 0;
  const hasWorkflows =
    workflows.length > 0 ||
    packs.length > 0 ||
    (accostageCounts?.workflowsCount ?? 0) > 0;

  const completedCount = [
    adminCreated,
    hasModels,
    hasOrgUnits,
    hasWorkspaces,
    hasSources,
    hasWorkflows,
  ].filter(Boolean).length;

  return {
    adminCreated,
    hasModels,
    hasOrgUnits,
    hasWorkspaces,
    hasSources,
    hasWorkflows,
    completedCount,
    totalCount: 6,
    isDay0Complete: completedCount === 6,
  };
}

export function buildUnifiedAccostageMilestones(params: {
  readonly isFr: boolean;
  readonly summary: AccostageProgressSummary;
}): readonly UiAccostageMilestoneItem[] {
  const { isFr, summary } = params;
  return [
    {
      index: 1,
      key: "first-admin",
      title: isFr ? "1. Compte Admin" : "1. Admin Account",
      completed: summary.adminCreated,
      targetRoute: "/welcome-setup",
    },
    {
      index: 2,
      key: "step-llm",
      title: isFr ? "2. Modèles IA" : "2. AI Models",
      completed: summary.hasModels,
      targetRoute: "/configuration",
    },
    {
      index: 3,
      key: "step-iam",
      title: isFr ? "3. Organisation" : "3. Organization",
      completed: summary.hasOrgUnits,
      targetRoute: "/organization",
    },
    {
      index: 4,
      key: "step-workspaces",
      title: isFr ? "4. Premier Espace" : "4. First Space",
      completed: summary.hasWorkspaces,
      targetRoute: "/spaces",
    },
    {
      index: 5,
      key: "step-connectors",
      title: isFr ? "5. Première Source" : "5. First Source",
      completed: summary.hasSources,
      targetRoute: "/configuration",
    },
    {
      index: 6,
      key: "step-workflows",
      title: isFr ? "6. Premier Processus" : "6. First Process",
      completed: summary.hasWorkflows,
      targetRoute: "/processes",
    },
  ];
}

export function buildWorkflowOverridesFromWorkflows(
  workflows: readonly ConfiguredWorkflowItem[],
): ControlCenterOverrideItem[] {
  return workflows.map((wf) => ({
    workflowKey: wf.workflowKey,
    title: wf.title,
    baseLayer: `v${wf.version}`,
    teamOverride: "—",
    workspaceOverride: `${wf.layers.filter((l) => l.enabled).length} couches actives`,
    userOverride: "—",
    spineContractRef: "—",
  }));
}
