import type {
  ControlCenterDatasourceItem,
  ControlCenterOverrideItem,
  ControlCenterWorkspaceGovItem,
  UiAccostageMilestoneItem,
} from "@orcia/ui";
import {
  canAccessMyOrganization,
  isPlatformAdministratorSession,
} from "../stores/authSessionStore";
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

const SERVER_TO_UI_MILESTONE_KEY: Readonly<Record<string, string>> = {
  "first-admin": "first-admin",
  "first-llm-model": "step-llm",
  "first-org-unit": "step-iam",
  "first-space": "step-workspaces",
  "first-datasource": "step-connectors",
  "pilot-workflow-run": "step-workflows",
};

function isUiMilestoneAccessible(params: {
  readonly uiKey: string;
  readonly roles?: readonly string[];
  readonly readOnlyObserver?: boolean;
  readonly allowedServerKeys?: ReadonlySet<string> | null;
}): boolean {
  const { uiKey, roles, readOnlyObserver, allowedServerKeys } = params;
  if (readOnlyObserver) {
    return false;
  }
  if (roles && roles.length > 0) {
    const normalizedRoles = roles.map((r) => r.trim().toUpperCase());
    if (
      normalizedRoles.includes("OBSERVER") ||
      normalizedRoles.includes("READ_ONLY_OBSERVER")
    ) {
      return false;
    }
    const isAdmin = isPlatformAdministratorSession({ roles, readOnlyObserver });
    const canOrg = canAccessMyOrganization({ roles, readOnlyObserver });
    if (!isAdmin) {
      if (uiKey === "first-admin" || uiKey === "step-llm" || uiKey === "step-connectors") {
        return false;
      }
      if (uiKey === "step-iam" && !canOrg) {
        return false;
      }
    }
  }
  if (allowedServerKeys && allowedServerKeys.size > 0) {
    const allowedUiKeys = new Set(
      Array.from(allowedServerKeys).map((k) => SERVER_TO_UI_MILESTONE_KEY[k] ?? k),
    );
    return allowedUiKeys.has(uiKey);
  }
  return true;
}

export function buildUnifiedAccostageMilestones(params: {
  readonly isFr: boolean;
  readonly summary: AccostageProgressSummary;
  readonly roles?: readonly string[];
  readonly readOnlyObserver?: boolean;
  readonly visibleMilestoneKeys?: readonly string[] | null;
}): readonly UiAccostageMilestoneItem[] {
  const { isFr, summary, roles, readOnlyObserver, visibleMilestoneKeys } = params;
  const allMilestones: readonly UiAccostageMilestoneItem[] = [
    {
      index: 1,
      key: "first-admin",
      title: isFr ? "1. Compte Admin" : "1. Admin Account",
      completed: summary.adminCreated,
      targetRoute: summary.adminCreated ? "/profile" : "/cockpit",
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

  const allowedServerKeys =
    visibleMilestoneKeys && visibleMilestoneKeys.length > 0
      ? new Set(visibleMilestoneKeys)
      : null;

  return allMilestones.filter((m) =>
    isUiMilestoneAccessible({
      uiKey: m.key,
      roles,
      readOnlyObserver,
      allowedServerKeys,
    }),
  );
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
