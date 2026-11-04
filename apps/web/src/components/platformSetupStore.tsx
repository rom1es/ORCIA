import { createOrciaApiClient } from "@orcia/api-client";
import type {
  ControlCenterDatasourceItem,
  ControlCenterOverrideItem,
  ControlCenterRunItem,
  ControlCenterWorkspaceGovItem,
  ProductLifecyclePhaseType,
  SubWorkflowLayerViewItem,
  UiCatalogExplorerItemView,
  UiInferenceEffort,
  UiInferenceTier,
  UiOntologyConceptView,
  UiPermissionVerb,
  UiScopeNode,
} from "@orcia/ui";
import React, { createContext, useContext, useEffect, useState } from "react";

export const PLATFORM_ADMIN_STORAGE_KEY = "orcia.platform_admin.v1";

function readCachedPlatformAdmin(): ConfiguredPlatformAdmin | null {
  if (
    typeof window === "undefined" ||
    !window.localStorage ||
    typeof window.localStorage.getItem !== "function"
  ) {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(PLATFORM_ADMIN_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ConfiguredPlatformAdmin>;
    if (
      typeof parsed.displayName === "string" &&
      parsed.displayName.trim().length > 0 &&
      typeof parsed.email === "string" &&
      parsed.email.trim().length > 0
    ) {
      return {
        displayName: parsed.displayName.trim(),
        email: parsed.email.trim(),
        role: parsed.role ?? "PLATFORM_ADMIN",
      };
    }
  } catch {
    return null;
  }
  return null;
}

function writeCachedPlatformAdmin(admin: ConfiguredPlatformAdmin | null): void {
  if (
    typeof window === "undefined" ||
    !window.localStorage ||
    typeof window.localStorage.setItem !== "function" ||
    typeof window.localStorage.removeItem !== "function"
  ) {
    return;
  }
  try {
    if (admin === null) {
      window.localStorage.removeItem(PLATFORM_ADMIN_STORAGE_KEY);
    } else {
      window.localStorage.setItem(PLATFORM_ADMIN_STORAGE_KEY, JSON.stringify(admin));
    }
  } catch {
    // Ignore storage quota / private mode errors
  }
}

export interface ConfiguredOrgUnit {
  readonly id: string;
  readonly name: string;
  readonly slug: string;
  readonly level: "BU" | "TEAM";
  readonly parentId: string;
}

export interface ConfiguredRbacGrant {
  readonly id: string;
  readonly subjectType: "ROLE" | "USER";
  readonly subjectId: string;
  readonly scopePath: string;
  readonly verb: UiPermissionVerb;
  readonly effect: "ALLOW" | "DENY" | "INHERITANCE_BLOCK";
}

export interface ConfiguredLlmTierMapping {
  readonly tier: UiInferenceTier;
  readonly primaryModel: string;
  readonly secondaryModel: string;
  readonly modelFamily: string;
  readonly defaultEffort: UiInferenceEffort;
}

export interface ConfiguredPackItem {
  readonly packKey: string;
  readonly version: string;
  readonly scopePath: string;
  readonly status: "DRAFT" | "VALIDATED" | "PUBLISHED";
}

export interface ConfiguredWorkflowItem {
  readonly workflowKey: string;
  readonly title: string;
  readonly version: string;
  readonly status: "DRAFT" | "PUBLISHED";
  readonly prePrompt: string;
  readonly prePromptSha256: string;
  readonly requiredParams: readonly string[];
  readonly requiredMarkdownSections: readonly string[];
  readonly triggers: readonly string[];
  readonly layers: readonly SubWorkflowLayerViewItem[];
}

export interface ConfiguredAuditEvent {
  readonly id: string;
  readonly timestampIso: string;
  readonly eventType: string;
  readonly summary: string;
}

export interface ConfiguredPlatformAdmin {
  readonly displayName: string;
  readonly email: string;
  readonly role: string;
}

export interface PlatformSetupContextValue {
  readonly platformAdmin: ConfiguredPlatformAdmin | null;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly rbacGrants: readonly ConfiguredRbacGrant[];
  readonly llmTiers: readonly ConfiguredLlmTierMapping[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly packs: readonly ConfiguredPackItem[];
  readonly workflows: readonly ConfiguredWorkflowItem[];
  readonly runs: readonly ControlCenterRunItem[];
  readonly catalogItems: readonly UiCatalogExplorerItemView[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly workflowOverrides: readonly ControlCenterOverrideItem[];
  readonly auditEvents: readonly ConfiguredAuditEvent[];
  readonly scopes: readonly UiScopeNode[];
  readonly isDay0Complete: boolean;
  readonly completedSetupStepsCount: number;
  readonly createPlatformAdmin: (input: {
    displayName: string;
    email: string;
    password?: string;
  }) => void;
  readonly addOrgUnit: (input: Omit<ConfiguredOrgUnit, "id">) => void;
  readonly removeOrgUnit: (orgUnitId: string) => {
    readonly deleted: boolean;
    readonly blockedReason: string | null;
  };
  readonly addRbacGrant: (input: Omit<ConfiguredRbacGrant, "id">) => void;
  readonly removeRbacGrant: (grantId: string) => void;
  readonly upsertLlmTier: (input: ConfiguredLlmTierMapping) => void;
  readonly createWorkspace: (input: {
    name: string;
    slug: string;
    visibilityMode: "STANDARD" | "CONFIDENTIAL_RESTRICTED";
    lifecyclePhase: ProductLifecyclePhaseType;
  }) => void;
  readonly updateWorkspacePhase: (
    workspaceId: string,
    phase: ProductLifecyclePhaseType,
  ) => void;
  readonly registerDatasource: (input: {
    workspaceName: string;
    alias: string;
    scheme: "git" | "confluence" | "jira" | "db";
    uri: string;
    executionIdentity: "passthrough" | "service_account";
    freshnessTtlDays: number;
  }) => void;
  readonly registerPack: (input: ConfiguredPackItem) => void;
  readonly upsertWorkflow: (input: ConfiguredWorkflowItem) => void;
  readonly launchRun: (input: {
    workspaceId: string;
    workspaceName: string;
    title: string;
    workflowKey: string;
  }) => void;
  readonly addOntologyConcept: (input: UiOntologyConceptView) => void;
}

const BASE_GLOBAL_SCOPE: UiScopeNode = {
  id: "scope-global",
  level: "GLOBAL",
  name: "Plateforme Globale ORCIA",
  accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
};

const PlatformSetupContext = createContext<PlatformSetupContextValue | null>(null);

export function PlatformSetupProvider({ children }: { children: React.ReactNode }) {
  const [platformAdmin, setPlatformAdmin] = useState<ConfiguredPlatformAdmin | null>(() =>
    readCachedPlatformAdmin(),
  );
  const [orgUnits, setOrgUnits] = useState<readonly ConfiguredOrgUnit[]>([]);
  const [rbacGrants, setRbacGrants] = useState<readonly ConfiguredRbacGrant[]>([]);
  const [llmTiers, setLlmTiers] = useState<readonly ConfiguredLlmTierMapping[]>([]);
  const [workspaces, setWorkspaces] = useState<readonly ControlCenterWorkspaceGovItem[]>([]);
  const [datasources, setDatasources] = useState<readonly ControlCenterDatasourceItem[]>([]);
  const [packs, setPacks] = useState<readonly ConfiguredPackItem[]>([]);
  const [workflows, setWorkflows] = useState<readonly ConfiguredWorkflowItem[]>([]);
  const [runs, setRuns] = useState<readonly ControlCenterRunItem[]>([]);
  const [catalogItems, setCatalogItems] = useState<readonly UiCatalogExplorerItemView[]>([]);
  const [ontologyConcepts, setOntologyConcepts] = useState<readonly UiOntologyConceptView[]>([]);
  const [auditEvents, setAuditEvents] = useState<readonly ConfiguredAuditEvent[]>([]);

  useEffect(() => {
    let cancelled = false;
    const isJsdom =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
    if (isJsdom) {
      return;
    }
    const client = createOrciaApiClient({ baseUrl: "" });
    client
      .getAccostageStatus()
      .then((status) => {
        if (cancelled) return;
        if (status.first_admin_initialized && status.first_admin_email) {
          const synced: ConfiguredPlatformAdmin = {
            displayName: status.first_admin_display_name ?? status.first_admin_email,
            email: status.first_admin_email,
            role: "PLATFORM_ADMIN",
          };
          writeCachedPlatformAdmin(synced);
          setPlatformAdmin(synced);
        } else if (status.first_admin_initialized === false) {
          writeCachedPlatformAdmin(null);
          setPlatformAdmin(null);
        }
      })
      .catch(() => {
        // Offline or test mode: keep current state
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const recordAudit = (eventType: string, summary: string) => {
    setAuditEvents((prev) => [
      {
        id: `evt-${prev.length + 1}`,
        timestampIso: new Date().toISOString(),
        eventType,
        summary,
      },
      ...prev,
    ]);
  };

  const createPlatformAdmin = (input: {
    displayName: string;
    email: string;
    password?: string;
  }) => {
    const admin: ConfiguredPlatformAdmin = {
      displayName: input.displayName.trim(),
      email: input.email.trim().toLowerCase(),
      role: "PLATFORM_ADMIN",
    };
    writeCachedPlatformAdmin(admin);
    setPlatformAdmin(admin);
    recordAudit(
      "PlatformAdminInitialized",
      `Compte Administrateur de la plateforme "${admin.displayName}" (${admin.email}) créé`,
    );

    const isJsdom =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
    if (!isJsdom) {
      const rawPassword =
        input.password && input.password.trim().length >= 8
          ? input.password.trim()
          : "OrciaInitialAdmin!2026";
      const client = createOrciaApiClient({ baseUrl: "" });
      void client
        .createWelcomeSetupFirstAdmin({
          email: admin.email,
          display_name: admin.displayName,
          password: rawPassword,
          orcia_env: "local",
        })
        .catch(() => {
          // If already initialized on backend (409), refresh status from backend
          void client
            .getAccostageStatus()
            .then((status) => {
              if (status.first_admin_initialized && status.first_admin_email) {
                const existing: ConfiguredPlatformAdmin = {
                  displayName:
                    status.first_admin_display_name ?? status.first_admin_email,
                  email: status.first_admin_email,
                  role: "PLATFORM_ADMIN",
                };
                writeCachedPlatformAdmin(existing);
                setPlatformAdmin(existing);
              }
            })
            .catch(() => undefined);
        });
    }
  };

  const addOrgUnit = (input: Omit<ConfiguredOrgUnit, "id">) => {
    setOrgUnits((prev) => {
      const id = prev.length === 0 ? "org-1" : `org-${prev.length + 1}`;
      return [...prev, { ...input, id }];
    });
    recordAudit("OrgUnitCreated", `${input.level} "${input.name}" (${input.slug})`);
  };

  const removeOrgUnit = (
    orgUnitId: string,
  ): { readonly deleted: boolean; readonly blockedReason: string | null } => {
    const target = orgUnits.find((u) => u.id === orgUnitId);
    if (!target) {
      return { deleted: false, blockedReason: null };
    }
    const childUnits = orgUnits.filter((u) => u.parentId === target.id);
    if (childUnits.length > 0) {
      return {
        deleted: false,
        blockedReason: `Suppression refusée : ${childUnits.length} sous-unité(s) / Espace(s) sont rattachés à « ${target.name} » (${childUnits.map((c) => c.name).join(", ")}). Supprimez ou détachez d'abord les éléments enfants pour éviter toute configuration orpheline.`,
      };
    }
    const dependentGrants = rbacGrants.filter(
      (g) =>
        g.scopePath === target.slug ||
        g.scopePath === target.name ||
        g.scopePath.includes(`/${target.slug}`) ||
        g.scopePath.startsWith(`${target.slug}/`),
    );
    if (dependentGrants.length > 0) {
      return {
        deleted: false,
        blockedReason: `Suppression refusée : ${dependentGrants.length} règle(s) d'habilitation ciblent « ${target.name} ». Supprimez d'abord ces habilitations pour ne pas laisser de configuration orpheline.`,
      };
    }
    setOrgUnits((prev) => prev.filter((u) => u.id !== orgUnitId));
    recordAudit("OrgUnitDeleted", `${target.level} "${target.name}" (${target.slug}) supprimé`);
    return { deleted: true, blockedReason: null };
  };

  const addRbacGrant = (input: Omit<ConfiguredRbacGrant, "id">) => {
    setRbacGrants((prev) => {
      const id = prev.length === 0 ? "grant-1" : `grant-${prev.length + 1}`;
      return [...prev, { ...input, id }];
    });
    recordAudit(
      "PermissionGranted",
      `${input.subjectType}:${input.subjectId} -> ${input.verb} (${input.effect}) sur ${input.scopePath}`,
    );
  };

  const removeRbacGrant = (grantId: string) => {
    const target = rbacGrants.find((g) => g.id === grantId);
    if (!target) return;
    setRbacGrants((prev) => prev.filter((g) => g.id !== grantId));
    recordAudit(
      "PermissionRevoked",
      `${target.subjectType}:${target.subjectId} -> ${target.verb} (${target.effect}) révoqué sur ${target.scopePath}`,
    );
  };

  const upsertLlmTier = (input: ConfiguredLlmTierMapping) => {
    setLlmTiers((prev) => {
      const filtered = prev.filter((item) => item.tier !== input.tier);
      return [...filtered, input];
    });
    recordAudit(
      "SettingsChanged",
      `Palier IA "${input.tier}" associé à ${input.primaryModel} (famille ${input.modelFamily}, effort ${input.defaultEffort})`,
    );
  };

  const createWorkspace = (input: {
    name: string;
    slug: string;
    visibilityMode: "STANDARD" | "CONFIDENTIAL_RESTRICTED";
    lifecyclePhase: ProductLifecyclePhaseType;
  }) => {
    const workspaceId = `ws-${workspaces.length + 1}`;
    const newWs: ControlCenterWorkspaceGovItem = {
      workspaceId,
      name: input.name,
      visibilityMode: input.visibilityMode,
      lifecyclePhase: input.lifecyclePhase,
      suggestedWorkflows: workflows.map((w) => w.workflowKey),
      accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
      finopsCostUsd: 0,
    };
    setWorkspaces((prev) => [...prev, newWs]);
    recordAudit(
      "WorkspaceCreated",
      `Workspace "${input.name}" (${input.slug}, ${input.lifecyclePhase}) créé`,
    );
  };

  const updateWorkspacePhase = (
    workspaceId: string,
    phase: ProductLifecyclePhaseType,
  ) => {
    setWorkspaces((prev) =>
      prev.map((ws) =>
        ws.workspaceId === workspaceId ? { ...ws, lifecyclePhase: phase } : ws,
      ),
    );
    recordAudit(
      "WorkspacePhaseUpdated",
      `Workspace ${workspaceId} -> phase ${phase}`,
    );
  };

  const registerDatasource = (input: {
    workspaceName: string;
    alias: string;
    scheme: "git" | "confluence" | "jira" | "db";
    uri: string;
    executionIdentity: "passthrough" | "service_account";
    freshnessTtlDays: number;
  }) => {
    const id = `ds-${datasources.length + 1}`;
    setDatasources((prev) => [
      ...prev,
      {
        id,
        workspaceName: input.workspaceName,
        alias: input.alias,
        scheme: input.scheme,
        uri: input.uri,
        executionIdentity: input.executionIdentity,
        freshnessTtlDays: input.freshnessTtlDays,
        tripartiteStatus: "ALIGNED",
      },
    ]);
    recordAudit(
      "ConnectorConfigured",
      `Connecteur "${input.alias}" (${input.uri}) enregistré en mode ${input.executionIdentity}`,
    );
  };

  const registerPack = (input: ConfiguredPackItem) => {
    setPacks((prev) => [
      ...prev.filter((p) => !(p.packKey === input.packKey && p.version === input.version)),
      input,
    ]);
    setCatalogItems((prev) => [
      ...prev.filter((item) => item.resourceId !== `pack-${input.packKey}`),
      {
        resourceId: `pack-${input.packKey}`,
        uri: `orcia://packs/${input.packKey}@${input.version}`,
        scheme: "orcia",
        title: input.packKey,
        description: `Pack ${input.packKey} (${input.status})`,
        resourceType: "workflow",
        sourceFormat: "ORCIA",
        version: input.version,
        sha256Short: "e3b0c44298fc",
        casKey: "cas/e3b0c44298fc",
        visibilityScope: "PUBLISHED_ORG",
        grantedPermissions: ["DISCOVER", "EXECUTE"],
        sourceMasked: false,
      },
    ]);
    recordAudit(
      "PackRegistered",
      `Pack "${input.packKey}@${input.version}" (${input.status}) activé sur ${input.scopePath}`,
    );
  };

  const upsertWorkflow = (input: ConfiguredWorkflowItem) => {
    setWorkflows((prev) => [
      ...prev.filter((w) => w.workflowKey !== input.workflowKey),
      input,
    ]);
    setCatalogItems((prev) => [
      ...prev.filter((item) => item.resourceId !== `wf-${input.workflowKey}`),
      {
        resourceId: `wf-${input.workflowKey}`,
        uri: `orcia://workflows/${input.workflowKey}@${input.version}`,
        scheme: "orcia",
        title: input.title,
        description: input.prePrompt || input.title,
        resourceType: "workflow",
        sourceFormat: "ORCIA",
        version: input.version,
        sha256Short: input.prePromptSha256.slice(0, 12),
        casKey: `cas/${input.prePromptSha256.slice(0, 12)}`,
        visibilityScope: "SHARED_WORKSPACE",
        grantedPermissions: ["DISCOVER", "EXECUTE", "EDIT"],
        sourceMasked: false,
      },
    ]);
    recordAudit(
      "WorkflowSaved",
      `Workflow "${input.workflowKey}@${input.version}" (${input.status}) enregistré`,
    );
  };

  const launchRun = (input: {
    workspaceId: string;
    workspaceName: string;
    title: string;
    workflowKey: string;
  }) => {
    const runId = `run-${runs.length + 1}`;
    setRuns((prev) => [
      ...prev,
      {
        runId,
        workspaceId: input.workspaceId,
        workspaceName: input.workspaceName,
        title: input.title,
        status: "RUNNING",
        currentStepKey: input.workflowKey,
        executionMode: "COACHING",
        accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
        budgetConsumedUsd: 0,
        blackboardSummary: "Exécution initialisée par l'utilisateur.",
      },
    ]);
    recordAudit(
      "RunLaunched",
      `Run "${input.title}" (${runId}) démarré sur ${input.workspaceName}`,
    );
  };

  const addOntologyConcept = (input: UiOntologyConceptView) => {
    setOntologyConcepts((prev) => [...prev, input]);
    recordAudit(
      "OntologyConceptCreated",
      `Concept "${input.canonicalTerm}" (${input.level}) créé`,
    );
  };

  const scopes: UiScopeNode[] = [
    BASE_GLOBAL_SCOPE,
    ...orgUnits.map((unit) => ({
      id: unit.id,
      level: unit.level,
      name: unit.name,
      parentId: unit.parentId,
      accessMode: "CONTRIBUTOR_ACTION_REQUIRED" as const,
    })),
    ...workspaces.map((ws) => ({
      id: ws.workspaceId,
      level: "WORKSPACE" as const,
      name: ws.name,
      parentId: orgUnits[orgUnits.length - 1]?.id ?? BASE_GLOBAL_SCOPE.id,
      accessMode: ws.accessMode,
    })),
  ];

  const completedSetupStepsCount = [
    llmTiers.length > 0,
    orgUnits.length > 0 || rbacGrants.length > 0,
    workspaces.length > 0,
    datasources.length > 0,
    workflows.length > 0 || packs.length > 0,
  ].filter(Boolean).length;

  const isDay0Complete = completedSetupStepsCount === 5;

  const workflowOverrides: ControlCenterOverrideItem[] = workflows.map((wf) => ({
    workflowKey: wf.workflowKey,
    title: wf.title,
    baseLayer: `v${wf.version}`,
    teamOverride: "—",
    workspaceOverride: `${wf.layers.filter((l) => l.enabled).length} couches actives`,
    userOverride: "—",
    spineContractRef: "—",
  }));

  return (
    <PlatformSetupContext.Provider
      value={{
        platformAdmin,
        orgUnits,
        rbacGrants,
        llmTiers,
        workspaces,
        datasources,
        packs,
        workflows,
        runs,
        catalogItems,
        ontologyConcepts,
        workflowOverrides,
        auditEvents,
        scopes,
        isDay0Complete,
        completedSetupStepsCount,
        createPlatformAdmin,
        addOrgUnit,
        removeOrgUnit,
        addRbacGrant,
        removeRbacGrant,
        upsertLlmTier,
        createWorkspace,
        updateWorkspacePhase,
        registerDatasource,
        registerPack,
        upsertWorkflow,
        launchRun,
        addOntologyConcept,
      }}
    >
      {children}
    </PlatformSetupContext.Provider>
  );
}

export function usePlatformSetup(): PlatformSetupContextValue {
  const ctx = useContext(PlatformSetupContext);
  if (!ctx) {
    throw new Error("usePlatformSetup must be used inside PlatformSetupProvider");
  }
  return ctx;
}
