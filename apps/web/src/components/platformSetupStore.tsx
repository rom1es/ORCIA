import { createOrciaApiClient, type PlatformSetupStatePutRequest } from "@orcia/api-client";
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
export const PLATFORM_SETUP_STATE_STORAGE_KEY = "orcia.platform_setup_state.v1";

const fallbackMemoryStorage = new Map<string, string>();

export function clearPlatformSetupStorage(): void {
  fallbackMemoryStorage.clear();
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.removeItem === "function"
  ) {
    try {
      window.localStorage.removeItem(PLATFORM_ADMIN_STORAGE_KEY);
      window.localStorage.removeItem(PLATFORM_SETUP_STATE_STORAGE_KEY);
    } catch {
      // Ignore
    }
  }
}

function readStorageItem(key: string): string | null {
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.getItem === "function"
  ) {
    try {
      return window.localStorage.getItem(key);
    } catch {
      // Fall through to memory storage
    }
  }
  return fallbackMemoryStorage.get(key) ?? null;
}

function writeStorageItem(key: string, value: string | null): void {
  if (value === null) {
    fallbackMemoryStorage.delete(key);
  } else {
    fallbackMemoryStorage.set(key, value);
  }
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.setItem === "function" &&
    typeof window.localStorage.removeItem === "function"
  ) {
    try {
      if (value === null) {
        window.localStorage.removeItem(key);
      } else {
        window.localStorage.setItem(key, value);
      }
    } catch {
      // Ignore storage quota / private mode errors
    }
  }
}

export interface CachedPlatformSetupState {
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
  readonly auditEvents: readonly ConfiguredAuditEvent[];
}

const EMPTY_PLATFORM_SETUP_STATE: CachedPlatformSetupState = {
  orgUnits: [],
  rbacGrants: [],
  llmTiers: [],
  workspaces: [],
  datasources: [],
  packs: [],
  workflows: [],
  runs: [],
  catalogItems: [],
  ontologyConcepts: [],
  auditEvents: [],
};

function readCachedPlatformAdmin(): ConfiguredPlatformAdmin | null {
  try {
    const raw = readStorageItem(PLATFORM_ADMIN_STORAGE_KEY);
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
        memberTeamIds: Array.isArray(parsed.memberTeamIds)
          ? parsed.memberTeamIds.filter((id): id is string => typeof id === "string")
          : [],
      };
    }
  } catch {
    return null;
  }
  return null;
}

function writeCachedPlatformAdmin(admin: ConfiguredPlatformAdmin | null): void {
  writeStorageItem(PLATFORM_ADMIN_STORAGE_KEY, admin === null ? null : JSON.stringify(admin));
}

export function deduplicateConfiguredPacks(
  items: readonly ConfiguredPackItem[],
): readonly ConfiguredPackItem[] {
  const globalPackKeys = new Set(
    items.filter((p) => p.scopePath === "GLOBAL").map((p) => p.packKey),
  );
  const seen = new Set<string>();
  const result: ConfiguredPackItem[] = [];
  for (const item of items) {
    if (globalPackKeys.has(item.packKey) && item.scopePath !== "GLOBAL") {
      continue;
    }
    const key = `${item.packKey}::${item.scopePath}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    result.push(item);
  }
  return result;
}

export function formatHumanReadableScopePath(rawScopePath: string | undefined): string {
  const trimmed = (rawScopePath ?? "").trim();
  if (!trimmed || trimmed === "GLOBAL" || trimmed === "scope-global") {
    return "Plateforme entière";
  }
  return trimmed;
}

export function cleanAuditSummaryJargon(rawSummary: string): string {
  return rawSummary
    .replace(/\bsur GLOBAL\b/g, "sur Plateforme entière")
    .replace(/\(PUBLISHED\)/g, "(Publié)")
    .replace(/\(DRAFT\)/g, "(Brouillon)")
    .replace(/\(VALIDATED\)/g, "(Validé)")
    .replace(/\bmode passthrough\b/gi, "mode Identité personnelle")
    .replace(/\bmode service_account\b/gi, "mode Compte technique partagé");
}

export function normalizeConfiguredAuditEvent(
  raw: Partial<ConfiguredAuditEvent> & Record<string, unknown>,
  fallbackActor?: ConfiguredPlatformAdmin | null,
): ConfiguredAuditEvent {
  const id = typeof raw.id === "string" && raw.id.trim() ? raw.id.trim() : "evt-1";
  const timestampIso =
    typeof raw.timestampIso === "string" && raw.timestampIso.trim()
      ? raw.timestampIso.trim()
      : new Date().toISOString();
  const eventType =
    typeof raw.eventType === "string" && raw.eventType.trim()
      ? raw.eventType.trim()
      : "SettingsChanged";
  const summary = cleanAuditSummaryJargon(
    typeof raw.summary === "string" ? raw.summary : "",
  );
  const actorName =
    typeof raw.actorName === "string" && raw.actorName.trim()
      ? raw.actorName.trim()
      : (fallbackActor?.displayName ?? "Administrateur de la plateforme");
  const actorEmail =
    typeof raw.actorEmail === "string" && raw.actorEmail.trim()
      ? raw.actorEmail.trim()
      : fallbackActor?.email;
  const rawScopePath =
    typeof raw.scopePath === "string" && raw.scopePath.trim()
      ? raw.scopePath.trim()
      : "GLOBAL";
  const scopeLabel =
    typeof raw.scopeLabel === "string" && raw.scopeLabel.trim()
      ? formatHumanReadableScopePath(raw.scopeLabel)
      : formatHumanReadableScopePath(rawScopePath);
  const scopeId =
    typeof raw.scopeId === "string" && raw.scopeId.trim()
      ? raw.scopeId.trim()
      : rawScopePath === "GLOBAL"
        ? "scope-global"
        : undefined;

  return {
    id,
    timestampIso,
    eventType,
    summary,
    actorName,
    ...(actorEmail ? { actorEmail } : {}),
    ...(scopeId ? { scopeId } : {}),
    scopePath: rawScopePath,
    scopeLabel,
  };
}

function readCachedPlatformSetupState(): CachedPlatformSetupState {
  try {
    const raw = readStorageItem(PLATFORM_SETUP_STATE_STORAGE_KEY);
    if (!raw) return EMPTY_PLATFORM_SETUP_STATE;
    const parsed = JSON.parse(raw) as Partial<CachedPlatformSetupState>;
    const cachedAdmin = readCachedPlatformAdmin();
    return {
      orgUnits: Array.isArray(parsed.orgUnits) ? parsed.orgUnits : [],
      rbacGrants: Array.isArray(parsed.rbacGrants) ? parsed.rbacGrants : [],
      llmTiers: Array.isArray(parsed.llmTiers) ? parsed.llmTiers : [],
      workspaces: Array.isArray(parsed.workspaces) ? parsed.workspaces : [],
      datasources: Array.isArray(parsed.datasources) ? parsed.datasources : [],
      packs: Array.isArray(parsed.packs) ? deduplicateConfiguredPacks(parsed.packs) : [],
      workflows: Array.isArray(parsed.workflows) ? parsed.workflows : [],
      runs: Array.isArray(parsed.runs) ? parsed.runs : [],
      catalogItems: Array.isArray(parsed.catalogItems) ? parsed.catalogItems : [],
      ontologyConcepts: Array.isArray(parsed.ontologyConcepts) ? parsed.ontologyConcepts : [],
      auditEvents: Array.isArray(parsed.auditEvents)
        ? parsed.auditEvents.map((ev) =>
            normalizeConfiguredAuditEvent(
              ev as Partial<ConfiguredAuditEvent> & Record<string, unknown>,
              cachedAdmin,
            ),
          )
        : [],
    };
  } catch {
    return EMPTY_PLATFORM_SETUP_STATE;
  }
}

function writeCachedPlatformSetupState(state: CachedPlatformSetupState | null): void {
  writeStorageItem(
    PLATFORM_SETUP_STATE_STORAGE_KEY,
    state === null ? null : JSON.stringify(state),
  );
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

export type LlmAuthMode = "api_key" | "env_var" | "none_local";

export interface ConfiguredLlmTierMapping {
  readonly tier: UiInferenceTier;
  readonly primaryModel: string;
  readonly secondaryModel: string;
  readonly modelFamily: string;
  readonly defaultEffort: UiInferenceEffort;
  readonly endpointUrl?: string;
  readonly authMode?: LlmAuthMode;
  readonly apiKeyConfigured?: boolean;
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
  readonly actorName?: string;
  readonly actorEmail?: string;
  readonly scopeId?: string;
  readonly scopePath?: string;
  readonly scopeLabel?: string;
}

export interface ConfiguredPlatformAdmin {
  readonly displayName: string;
  readonly email: string;
  readonly role: string;
  readonly memberTeamIds?: readonly string[];
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
  readonly toggleAdminTeamMembership: (teamId: string) => void;
  readonly addOrgUnit: (
    input: Omit<ConfiguredOrgUnit, "id"> & { readonly attachCurrentAdmin?: boolean },
  ) => void;
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
    visibilityMode: "STANDARD" | "CONFIDENTIAL_RESTRICTED" | "PRIVATE_USER";
    lifecyclePhase: ProductLifecyclePhaseType;
    ownerOrgUnitId?: string;
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
  readonly removePack: (packKey: string, scopePath?: string) => void;
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
  const [initialCache] = useState<CachedPlatformSetupState>(() => readCachedPlatformSetupState());
  const [orgUnits, setOrgUnits] = useState<readonly ConfiguredOrgUnit[]>(initialCache.orgUnits);
  const [rbacGrants, setRbacGrants] = useState<readonly ConfiguredRbacGrant[]>(
    initialCache.rbacGrants,
  );
  const [llmTiers, setLlmTiers] = useState<readonly ConfiguredLlmTierMapping[]>(
    initialCache.llmTiers,
  );
  const [workspaces, setWorkspaces] = useState<readonly ControlCenterWorkspaceGovItem[]>(
    initialCache.workspaces,
  );
  const [datasources, setDatasources] = useState<readonly ControlCenterDatasourceItem[]>(
    initialCache.datasources,
  );
  const [packs, setPacks] = useState<readonly ConfiguredPackItem[]>(initialCache.packs);
  const [workflows, setWorkflows] = useState<readonly ConfiguredWorkflowItem[]>(
    initialCache.workflows,
  );
  const [runs, setRuns] = useState<readonly ControlCenterRunItem[]>(initialCache.runs);
  const [catalogItems, setCatalogItems] = useState<readonly UiCatalogExplorerItemView[]>(
    initialCache.catalogItems,
  );
  const [ontologyConcepts, setOntologyConcepts] = useState<readonly UiOntologyConceptView[]>(
    initialCache.ontologyConcepts,
  );
  const [auditEvents, setAuditEvents] = useState<readonly ConfiguredAuditEvent[]>(
    initialCache.auditEvents,
  );

  const persistSnapshot = (next: CachedPlatformSetupState) => {
    writeCachedPlatformSetupState(next);
    const isJsdom =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
    if (isJsdom) {
      return;
    }
    const client = createOrciaApiClient({ baseUrl: "" });
    const payload: PlatformSetupStatePutRequest = {
      org_units: next.orgUnits as unknown as Record<string, unknown>[],
      rbac_grants: next.rbacGrants as unknown as Record<string, unknown>[],
      llm_tiers: next.llmTiers.map((t) => ({
        tier: t.tier,
        tierKey: t.tier,
        primaryModel: t.primaryModel,
        secondaryModel: t.secondaryModel,
        modelFamily: t.modelFamily,
        defaultEffort: t.defaultEffort,
        provider: t.modelFamily,
        model: t.primaryModel,
        endpointUrl: t.endpointUrl ?? "",
        authMode: t.authMode ?? "api_key",
        apiKeyConfigured: Boolean(t.apiKeyConfigured),
      })),
      workspaces: next.workspaces as unknown as Record<string, unknown>[],
      datasources: next.datasources as unknown as Record<string, unknown>[],
      packs: next.packs as unknown as Record<string, unknown>[],
      workflows: next.workflows as unknown as Record<string, unknown>[],
      runs: next.runs as unknown as Record<string, unknown>[],
      catalog_items: next.catalogItems as unknown as Record<string, unknown>[],
      ontology_concepts: next.ontologyConcepts as unknown as Record<string, unknown>[],
      audit_events: next.auditEvents as unknown as Record<string, unknown>[],
    };
    void client.savePlatformSetupState(payload).catch(() => undefined);
  };

  useEffect(() => {
    let cancelled = false;
    const isJsdom =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
    if (isJsdom) {
      return;
    }
    const client = createOrciaApiClient({ baseUrl: "" });
    Promise.all([
      client.getAccostageStatus(),
      client.getPlatformSetupState().catch(() => null),
    ])
      .then(([status, remoteState]) => {
        if (cancelled) return;
        if (status.first_admin_initialized === false) {
          writeCachedPlatformAdmin(null);
          writeCachedPlatformSetupState(null);
          setPlatformAdmin(null);
          setOrgUnits([]);
          setRbacGrants([]);
          setLlmTiers([]);
          setWorkspaces([]);
          setDatasources([]);
          setPacks([]);
          setWorkflows([]);
          setRuns([]);
          setCatalogItems([]);
          setOntologyConcepts([]);
          setAuditEvents([]);
          return;
        }
        if (status.first_admin_initialized && status.first_admin_email) {
          const synced: ConfiguredPlatformAdmin = {
            displayName: status.first_admin_display_name ?? status.first_admin_email,
            email: status.first_admin_email,
            role: "PLATFORM_ADMIN",
          };
          writeCachedPlatformAdmin(synced);
          setPlatformAdmin(synced);
        }
        if (remoteState) {
          const rOrgUnits = remoteState.org_units ?? [];
          const rRbacGrants = remoteState.rbac_grants ?? [];
          const rLlmTiers = remoteState.llm_tiers ?? [];
          const rWorkspaces = remoteState.workspaces ?? [];
          const rDatasources = remoteState.datasources ?? [];
          const rPacks = remoteState.packs ?? [];
          const rWorkflows = remoteState.workflows ?? [];
          const rRuns = remoteState.runs ?? [];
          const rCatalogItems = remoteState.catalog_items ?? [];
          const rOntologyConcepts = remoteState.ontology_concepts ?? [];
          const rAuditEvents = remoteState.audit_events ?? [];
          const hasRemoteEntities =
            rOrgUnits.length > 0 ||
            rRbacGrants.length > 0 ||
            rLlmTiers.length > 0 ||
            rWorkspaces.length > 0 ||
            rDatasources.length > 0 ||
            rPacks.length > 0 ||
            rWorkflows.length > 0 ||
            rRuns.length > 0 ||
            rCatalogItems.length > 0 ||
            rOntologyConcepts.length > 0;
          if (hasRemoteEntities) {
            const hydrated: CachedPlatformSetupState = {
              orgUnits: rOrgUnits as unknown as ConfiguredOrgUnit[],
              rbacGrants: rRbacGrants as unknown as ConfiguredRbacGrant[],
              llmTiers: rLlmTiers.map((raw) => ({
                tier: (raw.tier ?? raw.tierKey ?? "medium") as UiInferenceTier,
                primaryModel: String(raw.primaryModel ?? raw.model ?? "claude-3-7-sonnet"),
                secondaryModel: String(raw.secondaryModel ?? ""),
                modelFamily: String(raw.modelFamily ?? raw.provider ?? "Anthropic"),
                defaultEffort: (raw.defaultEffort ?? "balanced") as UiInferenceEffort,
                endpointUrl: raw.endpointUrl ? String(raw.endpointUrl) : undefined,
                authMode: (raw.authMode ?? "api_key") as LlmAuthMode,
                apiKeyConfigured: Boolean(raw.apiKeyConfigured),
              })),
              workspaces: rWorkspaces as unknown as ControlCenterWorkspaceGovItem[],
              datasources: rDatasources as unknown as ControlCenterDatasourceItem[],
              packs: deduplicateConfiguredPacks(
                rPacks as unknown as ConfiguredPackItem[],
              ),
              workflows: rWorkflows as unknown as ConfiguredWorkflowItem[],
              runs: rRuns as unknown as ControlCenterRunItem[],
              catalogItems: rCatalogItems as unknown as UiCatalogExplorerItemView[],
              ontologyConcepts: rOntologyConcepts as unknown as UiOntologyConceptView[],
              auditEvents: (rAuditEvents as unknown as Array<Partial<ConfiguredAuditEvent> & Record<string, unknown>>).map(
                (ev) => normalizeConfiguredAuditEvent(ev, platformAdmin),
              ),
            };
            writeCachedPlatformSetupState(hydrated);
            setOrgUnits(hydrated.orgUnits);
            setRbacGrants(hydrated.rbacGrants);
            setLlmTiers(hydrated.llmTiers);
            setWorkspaces(hydrated.workspaces);
            setDatasources(hydrated.datasources);
            setPacks(hydrated.packs);
            setWorkflows(hydrated.workflows);
            setRuns(hydrated.runs);
            setCatalogItems(hydrated.catalogItems);
            setOntologyConcepts(hydrated.ontologyConcepts);
            setAuditEvents(hydrated.auditEvents);
          }
        }
      })
      .catch(() => {
        // Offline or test mode: keep current state
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const buildSnapshot = (
    overrides: Partial<CachedPlatformSetupState>,
  ): CachedPlatformSetupState => ({
    orgUnits: overrides.orgUnits ?? orgUnits,
    rbacGrants: overrides.rbacGrants ?? rbacGrants,
    llmTiers: overrides.llmTiers ?? llmTiers,
    workspaces: overrides.workspaces ?? workspaces,
    datasources: overrides.datasources ?? datasources,
    packs: overrides.packs ?? packs,
    workflows: overrides.workflows ?? workflows,
    runs: overrides.runs ?? runs,
    catalogItems: overrides.catalogItems ?? catalogItems,
    ontologyConcepts: overrides.ontologyConcepts ?? ontologyConcepts,
    auditEvents: overrides.auditEvents ?? auditEvents,
  });

  const appendAudit = (
    eventType: string,
    summary: string,
    meta?: {
      readonly actorName?: string;
      readonly actorEmail?: string;
      readonly scopeId?: string;
      readonly scopePath?: string;
      readonly scopeLabel?: string;
    },
  ): readonly ConfiguredAuditEvent[] => [
    normalizeConfiguredAuditEvent(
      {
        id: `evt-${auditEvents.length + 1}`,
        timestampIso: new Date().toISOString(),
        eventType,
        summary,
        actorName: meta?.actorName ?? platformAdmin?.displayName ?? "Administrateur de la plateforme",
        actorEmail: meta?.actorEmail ?? platformAdmin?.email,
        scopeId: meta?.scopeId,
        scopePath: meta?.scopePath ?? "GLOBAL",
        scopeLabel: meta?.scopeLabel ?? formatHumanReadableScopePath(meta?.scopePath ?? "GLOBAL"),
      },
      platformAdmin,
    ),
    ...auditEvents,
  ];

  const createPlatformAdmin = (input: {
    displayName: string;
    email: string;
    password?: string;
  }) => {
    const admin: ConfiguredPlatformAdmin = {
      displayName: input.displayName.trim(),
      email: input.email.trim().toLowerCase(),
      role: "PLATFORM_ADMIN",
      memberTeamIds: [],
    };
    writeCachedPlatformAdmin(admin);
    setPlatformAdmin(admin);
    const nextAudit = appendAudit(
      "PlatformAdminInitialized",
      `Compte Administrateur de la plateforme "${admin.displayName}" (${admin.email}) créé`,
      {
        actorName: admin.displayName,
        actorEmail: admin.email,
        scopeId: "scope-global",
        scopePath: "GLOBAL",
        scopeLabel: "Plateforme entière",
      },
    );
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ auditEvents: nextAudit }));

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
          void client
            .getAccostageStatus()
            .then((status) => {
              if (status.first_admin_initialized && status.first_admin_email) {
                const existing: ConfiguredPlatformAdmin = {
                  displayName:
                    status.first_admin_display_name ?? status.first_admin_email,
                  email: status.first_admin_email,
                  role: "PLATFORM_ADMIN",
                  memberTeamIds: admin.memberTeamIds ?? [],
                };
                writeCachedPlatformAdmin(existing);
                setPlatformAdmin(existing);
              }
            })
            .catch(() => undefined);
        });
    }
  };

  const toggleAdminTeamMembership = (teamId: string) => {
    const targetTeam = orgUnits.find((u) => u.id === teamId && u.level === "TEAM");
    if (!targetTeam) return;
    const baseAdmin: ConfiguredPlatformAdmin = platformAdmin ?? {
      displayName: "Administrateur de la plateforme",
      email: "admin@orcia.local",
      role: "PLATFORM_ADMIN",
      memberTeamIds: [],
    };
    const currentTeamIds = baseAdmin.memberTeamIds ?? [];
    const isMember = currentTeamIds.includes(teamId);
    const nextTeamIds = isMember
      ? currentTeamIds.filter((id) => id !== teamId)
      : [...currentTeamIds, teamId];
    const updatedAdmin: ConfiguredPlatformAdmin = {
      ...baseAdmin,
      memberTeamIds: nextTeamIds,
    };
    writeCachedPlatformAdmin(updatedAdmin);
    setPlatformAdmin(updatedAdmin);
    const nextAudit = appendAudit(
      isMember ? "PermissionRevoked" : "PermissionGranted",
      isMember
        ? `Rattachement à l'Équipe "${targetTeam.name}" retiré pour ${updatedAdmin.displayName}`
        : `Compte ${updatedAdmin.displayName} rattaché à l'Équipe de facturation "${targetTeam.name}"`,
      {
        scopeId: targetTeam.id,
        scopePath: targetTeam.slug,
        scopeLabel: `Équipe · ${targetTeam.name}`,
      },
    );
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ auditEvents: nextAudit }));
  };

  const addOrgUnit = (
    input: Omit<ConfiguredOrgUnit, "id"> & { readonly attachCurrentAdmin?: boolean },
  ) => {
    const id = orgUnits.length === 0 ? "org-1" : `org-${orgUnits.length + 1}`;
    const newUnit: ConfiguredOrgUnit = {
      id,
      name: input.name,
      slug: input.slug,
      level: input.level,
      parentId: input.parentId,
    };
    const nextOrgUnits = [...orgUnits, newUnit];
    const shouldAttachAdmin =
      input.level === "TEAM" && input.attachCurrentAdmin !== false;
    if (shouldAttachAdmin && platformAdmin) {
      const currentTeamIds = platformAdmin.memberTeamIds ?? [];
      if (!currentTeamIds.includes(id)) {
        const updatedAdmin: ConfiguredPlatformAdmin = {
          ...platformAdmin,
          memberTeamIds: [...currentTeamIds, id],
        };
        writeCachedPlatformAdmin(updatedAdmin);
        setPlatformAdmin(updatedAdmin);
      }
    }
    const levelLabel = input.level === "BU" ? "Direction (BU)" : "Équipe";
    const nextAudit = appendAudit(
      "OrgUnitCreated",
      `${levelLabel} "${input.name}" (${input.slug}) créée`,
      {
        scopeId: id,
        scopePath: input.slug,
        scopeLabel: `${levelLabel} · ${input.name}`,
      },
    );
    setOrgUnits(nextOrgUnits);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ orgUnits: nextOrgUnits, auditEvents: nextAudit }));
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
        blockedReason: `Suppression refusée : ${childUnits.length} sous-unité(s) / Équipe(s) sont rattachées à « ${target.name} » (${childUnits.map((c) => c.name).join(", ")}). Supprimez ou détachez d'abord les éléments enfants pour éviter toute configuration orpheline.`,
      };
    }
    const attachedWorkspaces = workspaces.filter((w) => w.ownerOrgUnitId === target.id);
    if (attachedWorkspaces.length > 0) {
      return {
        deleted: false,
        blockedReason: `Suppression refusée : ${attachedWorkspaces.length} Espace(s) de Travail sont rattachés à « ${target.name} » (${attachedWorkspaces.map((w) => w.name).join(", ")}). Supprimez ou réattribuez d'abord ces espaces.`,
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
    const nextOrgUnits = orgUnits.filter((u) => u.id !== orgUnitId);
    if (platformAdmin?.memberTeamIds?.includes(orgUnitId)) {
      const updatedAdmin: ConfiguredPlatformAdmin = {
        ...platformAdmin,
        memberTeamIds: platformAdmin.memberTeamIds.filter((id) => id !== orgUnitId),
      };
      writeCachedPlatformAdmin(updatedAdmin);
      setPlatformAdmin(updatedAdmin);
    }
    const levelLabel = target.level === "BU" ? "Direction (BU)" : "Équipe";
    const nextAudit = appendAudit(
      "OrgUnitDeleted",
      `${levelLabel} "${target.name}" (${target.slug}) supprimée`,
      {
        scopeId: target.id,
        scopePath: target.slug,
        scopeLabel: `${levelLabel} · ${target.name}`,
      },
    );
    setOrgUnits(nextOrgUnits);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ orgUnits: nextOrgUnits, auditEvents: nextAudit }));
    return { deleted: true, blockedReason: null };
  };

  const addRbacGrant = (input: Omit<ConfiguredRbacGrant, "id">) => {
    const id = rbacGrants.length === 0 ? "grant-1" : `grant-${rbacGrants.length + 1}`;
    const nextRbacGrants = [...rbacGrants, { ...input, id }];
    const readableScope = formatHumanReadableScopePath(input.scopePath);
    const nextAudit = appendAudit(
      "PermissionGranted",
      `${input.subjectType === "ROLE" ? "Rôle" : "Utilisateur"} ${input.subjectId} → ${input.verb} sur ${readableScope}`,
      {
        scopePath: input.scopePath,
        scopeLabel: readableScope,
      },
    );
    setRbacGrants(nextRbacGrants);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ rbacGrants: nextRbacGrants, auditEvents: nextAudit }));
  };

  const removeRbacGrant = (grantId: string) => {
    const target = rbacGrants.find((g) => g.id === grantId);
    if (!target) return;
    const nextRbacGrants = rbacGrants.filter((g) => g.id !== grantId);
    const readableScope = formatHumanReadableScopePath(target.scopePath);
    const nextAudit = appendAudit(
      "PermissionRevoked",
      `${target.subjectType === "ROLE" ? "Rôle" : "Utilisateur"} ${target.subjectId} → ${target.verb} révoqué sur ${readableScope}`,
      {
        scopePath: target.scopePath,
        scopeLabel: readableScope,
      },
    );
    setRbacGrants(nextRbacGrants);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ rbacGrants: nextRbacGrants, auditEvents: nextAudit }));
  };

  const upsertLlmTier = (input: ConfiguredLlmTierMapping) => {
    const nextLlmTiers = [...llmTiers.filter((item) => item.tier !== input.tier), input];
    const nextAudit = appendAudit(
      "SettingsChanged",
      `Niveau IA "${input.tier}" associé au modèle ${input.primaryModel} (${input.modelFamily})`,
      {
        scopeId: "scope-global",
        scopePath: "GLOBAL",
        scopeLabel: "Plateforme entière",
      },
    );
    setLlmTiers(nextLlmTiers);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ llmTiers: nextLlmTiers, auditEvents: nextAudit }));

    const isJsdom =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
    if (!isJsdom) {
      const client = createOrciaApiClient({ baseUrl: "" });
      const resolvedUri =
        input.endpointUrl &&
        (input.endpointUrl.startsWith("http://") || input.endpointUrl.startsWith("https://"))
          ? input.endpointUrl
          : `https://api.${input.modelFamily.toLowerCase().replace(/[^a-z0-9-]+/g, "-")}.local/v1`;
      void client
        .registerProgressiveLlmEndpoint({
          endpoint_key: input.tier,
          provider_slug: input.modelFamily,
          model_family: input.modelFamily,
          model_name: input.primaryModel,
          endpoint_uri: resolvedUri,
        })
        .catch(() => undefined);
    }
  };

  const createWorkspace = (input: {
    name: string;
    slug: string;
    visibilityMode: "STANDARD" | "CONFIDENTIAL_RESTRICTED" | "PRIVATE_USER";
    lifecyclePhase: ProductLifecyclePhaseType;
    ownerOrgUnitId?: string;
  }) => {
    const workspaceId = `ws-${workspaces.length + 1}`;
    const teamUnits = orgUnits.filter((u) => u.level === "TEAM");
    const resolvedOwnerUnit =
      orgUnits.find((u) => u.id === input.ownerOrgUnitId) ??
      teamUnits[0] ??
      orgUnits[orgUnits.length - 1];
    const ownerOrgUnitId = resolvedOwnerUnit?.id;
    const ownerOrgUnitName =
      resolvedOwnerUnit?.name ?? "Plateforme Globale ORCIA";
    const newWs: ControlCenterWorkspaceGovItem = {
      workspaceId,
      name: input.name,
      visibilityMode: input.visibilityMode,
      ...(ownerOrgUnitId ? { ownerOrgUnitId } : {}),
      ownerOrgUnitName,
      ...(input.visibilityMode === "PRIVATE_USER"
        ? { ownerUserId: platformAdmin?.email ?? "local-operator" }
        : {}),
      lifecyclePhase: input.lifecyclePhase,
      suggestedWorkflows: workflows.map((w) => w.workflowKey),
      accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
      finopsCostUsd: 0,
    };
    const nextWorkspaces = [...workspaces, newWs];
    const modeLabel =
      input.visibilityMode === "PRIVATE_USER"
        ? "Privé personnel"
        : input.visibilityMode === "CONFIDENTIAL_RESTRICTED"
          ? "Confidentiel"
          : "Collectif d'équipe";
    const nextAudit = appendAudit(
      "WorkspaceCreated",
      `Espace de travail "${input.name}" (${input.slug}, ${modeLabel}, facturé à ${ownerOrgUnitName}) créé`,
      {
        scopeId: workspaceId,
        scopePath: input.slug,
        scopeLabel: `Espace · ${input.name}`,
      },
    );
    setWorkspaces(nextWorkspaces);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ workspaces: nextWorkspaces, auditEvents: nextAudit }));
  };

  const updateWorkspacePhase = (
    workspaceId: string,
    phase: ProductLifecyclePhaseType,
  ) => {
    const targetWs = workspaces.find((w) => w.workspaceId === workspaceId);
    const nextWorkspaces = workspaces.map((ws) =>
      ws.workspaceId === workspaceId ? { ...ws, lifecyclePhase: phase } : ws,
    );
    const nextAudit = appendAudit(
      "WorkspacePhaseUpdated",
      `Espace "${targetWs?.name ?? workspaceId}" passé en phase ${phase}`,
      {
        scopeId: workspaceId,
        scopePath: targetWs?.name ?? workspaceId,
        scopeLabel: `Espace · ${targetWs?.name ?? workspaceId}`,
      },
    );
    setWorkspaces(nextWorkspaces);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ workspaces: nextWorkspaces, auditEvents: nextAudit }));
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
    const nextDatasources: readonly ControlCenterDatasourceItem[] = [
      ...datasources,
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
    ];
    const identityLabel =
      input.executionIdentity === "passthrough"
        ? "Identité personnelle"
        : "Compte technique partagé";
    const nextAudit = appendAudit(
      "ConnectorConfigured",
      `Connecteur "${input.alias}" (${input.uri}) enregistré (${identityLabel})`,
      {
        scopePath: input.workspaceName,
        scopeLabel: formatHumanReadableScopePath(input.workspaceName),
      },
    );
    setDatasources(nextDatasources);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ datasources: nextDatasources, auditEvents: nextAudit }));
  };

  const registerPack = (input: ConfiguredPackItem) => {
    const nextPacks = deduplicateConfiguredPacks([
      ...packs.filter(
        (p) =>
          !(
            p.packKey === input.packKey &&
            (p.scopePath === input.scopePath || input.scopePath === "GLOBAL")
          ),
      ),
      input,
    ]);
    const nextCatalogItems: readonly UiCatalogExplorerItemView[] = [
      ...catalogItems.filter((item) => item.resourceId !== `pack-${input.packKey}`),
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
    ];
    const readableScope = formatHumanReadableScopePath(input.scopePath);
    const nextAudit = appendAudit(
      "PackRegistered",
      `Pack "${input.packKey}@${input.version}" activé sur ${readableScope}`,
      {
        scopePath: input.scopePath,
        scopeLabel: readableScope,
      },
    );
    setPacks(nextPacks);
    setCatalogItems(nextCatalogItems);
    setAuditEvents(nextAudit);
    persistSnapshot(
      buildSnapshot({
        packs: nextPacks,
        catalogItems: nextCatalogItems,
        auditEvents: nextAudit,
      }),
    );
  };

  const removePack = (packKey: string, scopePath?: string) => {
    const nextPacks = packs.filter(
      (p) =>
        !(
          p.packKey === packKey &&
          (scopePath === undefined || p.scopePath === scopePath)
        ),
    );
    const stillActiveSomewhere = nextPacks.some((p) => p.packKey === packKey);
    const nextCatalogItems = stillActiveSomewhere
      ? catalogItems
      : catalogItems.filter((item) => item.resourceId !== `pack-${packKey}`);
    const readableScope = formatHumanReadableScopePath(scopePath ?? "GLOBAL");
    const nextAudit = appendAudit(
      "PackDeactivated",
      `Pack "${packKey}" désactivé sur ${readableScope}`,
      {
        scopePath: scopePath ?? "GLOBAL",
        scopeLabel: readableScope,
      },
    );
    setPacks(nextPacks);
    setCatalogItems(nextCatalogItems);
    setAuditEvents(nextAudit);
    persistSnapshot(
      buildSnapshot({
        packs: nextPacks,
        catalogItems: nextCatalogItems,
        auditEvents: nextAudit,
      }),
    );
  };

  const upsertWorkflow = (input: ConfiguredWorkflowItem) => {
    const nextWorkflows = [
      ...workflows.filter((w) => w.workflowKey !== input.workflowKey),
      input,
    ];
    const nextCatalogItems: readonly UiCatalogExplorerItemView[] = [
      ...catalogItems.filter((item) => item.resourceId !== `wf-${input.workflowKey}`),
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
    ];
    const statusLabel = input.status === "PUBLISHED" ? "Publié" : "Brouillon";
    const nextAudit = appendAudit(
      "WorkflowSaved",
      `Processus "${input.title || input.workflowKey}" (${statusLabel}) enregistré`,
      {
        scopeId: "scope-global",
        scopePath: "GLOBAL",
        scopeLabel: "Plateforme entière",
      },
    );
    setWorkflows(nextWorkflows);
    setCatalogItems(nextCatalogItems);
    setAuditEvents(nextAudit);
    persistSnapshot(
      buildSnapshot({
        workflows: nextWorkflows,
        catalogItems: nextCatalogItems,
        auditEvents: nextAudit,
      }),
    );
  };

  const launchRun = (input: {
    workspaceId: string;
    workspaceName: string;
    title: string;
    workflowKey: string;
  }) => {
    const runId = `run-${runs.length + 1}`;
    const nextRuns: readonly ControlCenterRunItem[] = [
      ...runs,
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
    ];
    const nextAudit = appendAudit(
      "RunLaunched",
      `Exécution "${input.title}" (${runId}) démarrée sur ${input.workspaceName}`,
      {
        scopeId: input.workspaceId,
        scopePath: input.workspaceName,
        scopeLabel: `Espace · ${input.workspaceName}`,
      },
    );
    setRuns(nextRuns);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ runs: nextRuns, auditEvents: nextAudit }));
  };

  const addOntologyConcept = (input: UiOntologyConceptView) => {
    const nextConcepts = [...ontologyConcepts, input];
    const nextAudit = appendAudit(
      "OntologyConceptCreated",
      `Terme métier "${input.canonicalTerm}" (${input.level}) créé`,
      {
        scopeId: "scope-global",
        scopePath: "GLOBAL",
        scopeLabel: "Plateforme entière",
      },
    );
    setOntologyConcepts(nextConcepts);
    setAuditEvents(nextAudit);
    persistSnapshot(
      buildSnapshot({ ontologyConcepts: nextConcepts, auditEvents: nextAudit }),
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
      parentId: ws.ownerOrgUnitId ?? orgUnits[orgUnits.length - 1]?.id ?? BASE_GLOBAL_SCOPE.id,
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
        toggleAdminTeamMembership,
        addOrgUnit,
        removeOrgUnit,
        addRbacGrant,
        removeRbacGrant,
        upsertLlmTier,
        createWorkspace,
        updateWorkspacePhase,
        registerDatasource,
        registerPack,
        removePack,
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
