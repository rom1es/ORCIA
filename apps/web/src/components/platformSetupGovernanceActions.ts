import { createOrciaApiClient } from "@orcia/api-client";
import type {
  ControlCenterRunItem,
  ControlCenterWorkspaceGovItem,
  UiCatalogExplorerItemView,
  UiOntologyConceptView,
  UiOntologyLevel,
} from "@orcia/ui";
import { resolveWebApiBaseUrl, useAuthSessionStore } from "../stores/authSessionStore";
import {
  applyPromoteOntologyConcept,
  applyRegisterPack,
  applyUpsertWorkflow,
  computeRemoveOrgUnitOutcome,
  formatOntologyLevelLabel,
  type AppendAuditFn,
} from "./platformSetupOrgAndGovernance";
import {
  formatHumanReadableScopePath,
  writeCachedPlatformAdmin,
  writeCachedPlatformSetupState,
  type CachedPlatformSetupState,
  type ConfiguredAuditEvent,
  type ConfiguredLlmTierMapping,
  type ConfiguredOrgUnit,
  type ConfiguredPackItem,
  type ConfiguredPlatformAdmin,
  type ConfiguredRbacGrant,
  type ConfiguredWorkflowItem,
} from "./platformSetupStorageHelpers";

export interface GovernanceActionsDeps {
  readonly platformAdmin: ConfiguredPlatformAdmin | null;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly rbacGrants: readonly ConfiguredRbacGrant[];
  readonly llmTiers: readonly ConfiguredLlmTierMapping[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly packs: readonly ConfiguredPackItem[];
  readonly workflows: readonly ConfiguredWorkflowItem[];
  readonly runs: readonly ControlCenterRunItem[];
  readonly catalogItems: readonly UiCatalogExplorerItemView[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly setPlatformAdmin: (admin: ConfiguredPlatformAdmin | null) => void;
  readonly setOrgUnits: (units: readonly ConfiguredOrgUnit[]) => void;
  readonly setRbacGrants: (grants: readonly ConfiguredRbacGrant[]) => void;
  readonly setLlmTiers: (tiers: readonly ConfiguredLlmTierMapping[]) => void;
  readonly setPacks: (packs: readonly ConfiguredPackItem[]) => void;
  readonly setWorkflows: (workflows: readonly ConfiguredWorkflowItem[]) => void;
  readonly setRuns: (runs: readonly ControlCenterRunItem[]) => void;
  readonly setCatalogItems: (items: readonly UiCatalogExplorerItemView[]) => void;
  readonly setOntologyConcepts: (concepts: readonly UiOntologyConceptView[]) => void;
  readonly setAuditEvents: (events: readonly ConfiguredAuditEvent[]) => void;
  readonly setLastSyncError: (msg: string | null) => void;
  readonly markMutated: () => void;
  readonly appendAudit: AppendAuditFn;
  readonly buildSnapshot: (
    overrides: Partial<CachedPlatformSetupState>,
  ) => CachedPlatformSetupState;
  readonly persistSnapshot: (next: CachedPlatformSetupState) => void;
}

export function createPlatformGovernanceActions(deps: GovernanceActionsDeps) {
  const {
    platformAdmin,
    orgUnits,
    rbacGrants,
    llmTiers,
    workspaces,
    packs,
    workflows,
    runs,
    catalogItems,
    ontologyConcepts,
    setPlatformAdmin,
    setOrgUnits,
    setRbacGrants,
    setLlmTiers,
    setPacks,
    setWorkflows,
    setRuns,
    setCatalogItems,
    setOntologyConcepts,
    setAuditEvents,
    setLastSyncError,
    markMutated,
    appendAudit,
    buildSnapshot,
    persistSnapshot,
  } = deps;

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

    const rawPassword =
      input.password && input.password.trim().length >= 8
        ? input.password.trim()
        : "OrciaInitialAdmin!2026";
    const client = createOrciaApiClient({ baseUrl: resolveWebApiBaseUrl() });
    void client
      .createWelcomeSetupFirstAdmin({
        email: admin.email,
        display_name: admin.displayName,
        password: rawPassword,
        orcia_env: "local",
      })
      .then((res) => {
        if (res && (res.access_token || (res as Record<string, unknown>).accessToken)) {
          useAuthSessionStore.getState().loginWithSession({
            access_token:
              res.access_token ??
              ((res as Record<string, unknown>).accessToken as string | undefined),
            email: admin.email,
            display_name: admin.displayName,
            platform_role: "PLATFORM_ADMIN",
            roles: ["PLATFORM_ADMIN"],
            must_change_password: Boolean(res.must_change_password),
          });
        } else {
          void useAuthSessionStore.getState().hydrateSession({ force: true });
        }
      })
      .catch(async (err: unknown) => {
        setLastSyncError(
          err instanceof Error ? err.message : "Erreur lors de l'initialisation administrateur.",
        );
        const status = await client.getAccostageStatus();
        if (status.first_admin_initialized && status.first_admin_email) {
          const existing: ConfiguredPlatformAdmin = {
            displayName: status.first_admin_display_name ?? status.first_admin_email,
            email: status.first_admin_email,
            role: "PLATFORM_ADMIN",
            memberTeamIds: admin.memberTeamIds ?? [],
          };
          writeCachedPlatformAdmin(existing);
          setPlatformAdmin(existing);
        }
      });
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
    const updatedAdmin: ConfiguredPlatformAdmin = { ...baseAdmin, memberTeamIds: nextTeamIds };
    writeCachedPlatformAdmin(updatedAdmin);
    setPlatformAdmin(updatedAdmin);
    const nextAudit = appendAudit(
      isMember ? "PermissionRevoked" : "PermissionGranted",
      isMember
        ? `Rattachement à l'Équipe "${targetTeam.name}" retiré pour ${updatedAdmin.displayName}`
        : `Compte ${updatedAdmin.displayName} rattaché à l'Équipe de facturation "${targetTeam.name}"`,
      { scopeId: targetTeam.id, scopePath: targetTeam.slug, scopeLabel: `Équipe · ${targetTeam.name}` },
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
      billingEnabled: input.billingEnabled ?? true,
      leadUserId: input.leadUserId ?? null,
      memberUserIds: input.memberUserIds ?? [],
      attachedWorkspacesCount: input.attachedWorkspacesCount ?? 0,
    };
    const nextOrgUnits = [...orgUnits, newUnit];
    if (input.level === "TEAM" && input.attachCurrentAdmin !== false && platformAdmin) {
      const currentTeamIds = platformAdmin.memberTeamIds ?? [];
      if (!currentTeamIds.includes(id)) {
        const updatedAdmin = { ...platformAdmin, memberTeamIds: [...currentTeamIds, id] };
        writeCachedPlatformAdmin(updatedAdmin);
        setPlatformAdmin(updatedAdmin);
      }
    }
    const levelLabel = input.level === "BU" ? "Direction (BU)" : "Équipe";
    const nextAudit = appendAudit(
      "OrgUnitCreated",
      `${levelLabel} "${input.name}" (${input.slug}) créée`,
      { scopeId: id, scopePath: input.slug, scopeLabel: `${levelLabel} · ${input.name}` },
    );
    setOrgUnits(nextOrgUnits);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ orgUnits: nextOrgUnits, auditEvents: nextAudit }));
  };

  const syncOrgUnitsFromServer = (
    units: readonly ConfiguredOrgUnit[],
    auditMeta?: {
      readonly eventType: string;
      readonly summary: string;
      readonly scopeId?: string;
      readonly scopePath?: string;
      readonly scopeLabel?: string;
    },
  ) => {
    setOrgUnits(units);
    if (auditMeta) {
      const nextAudit = appendAudit(auditMeta.eventType, auditMeta.summary, auditMeta);
      setAuditEvents(nextAudit);
      persistSnapshot(buildSnapshot({ orgUnits: units, auditEvents: nextAudit }));
    } else {
      markMutated();
      writeCachedPlatformSetupState(buildSnapshot({ orgUnits: units }));
    }
  };

  const removeOrgUnit = (orgUnitId: string) => {
    const outcome = computeRemoveOrgUnitOutcome({
      orgUnitId,
      orgUnits,
      workspaces,
      rbacGrants,
      platformAdmin,
      appendAudit,
    });
    if (!outcome.deleted || !outcome.nextOrgUnits || !outcome.nextAudit) {
      return { deleted: outcome.deleted, blockedReason: outcome.blockedReason };
    }
    if (outcome.updatedAdmin) {
      writeCachedPlatformAdmin(outcome.updatedAdmin);
      setPlatformAdmin(outcome.updatedAdmin);
    }
    setOrgUnits(outcome.nextOrgUnits);
    setAuditEvents(outcome.nextAudit);
    persistSnapshot(
      buildSnapshot({ orgUnits: outcome.nextOrgUnits, auditEvents: outcome.nextAudit }),
    );
    return { deleted: true, blockedReason: null };
  };

  const addRbacGrant = (input: Omit<ConfiguredRbacGrant, "id">) => {
    const id = rbacGrants.length === 0 ? "grant-1" : `grant-${rbacGrants.length + 1}`;
    const nextRbacGrants = [...rbacGrants, { ...input, id }];
    const readableScope = formatHumanReadableScopePath(input.scopePath);
    const nextAudit = appendAudit(
      "PermissionGranted",
      `${input.subjectType === "ROLE" ? "Rôle" : "Utilisateur"} ${input.subjectId} → ${input.verb} sur ${readableScope}`,
      { scopePath: input.scopePath, scopeLabel: readableScope },
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
      { scopePath: target.scopePath, scopeLabel: readableScope },
    );
    setRbacGrants(nextRbacGrants);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ rbacGrants: nextRbacGrants, auditEvents: nextAudit }));
  };

  const syncRbacGrantsFromServer = (
    grants: readonly ConfiguredRbacGrant[],
    auditMeta?: {
      readonly eventType: string;
      readonly summary: string;
      readonly scopePath?: string;
      readonly scopeLabel?: string;
    },
  ) => {
    setRbacGrants(grants);
    if (auditMeta) {
      const nextAudit = appendAudit(auditMeta.eventType, auditMeta.summary, auditMeta);
      setAuditEvents(nextAudit);
      persistSnapshot(buildSnapshot({ rbacGrants: grants, auditEvents: nextAudit }));
    } else {
      markMutated();
      writeCachedPlatformSetupState(buildSnapshot({ rbacGrants: grants }));
    }
  };

  const upsertLlmTier = (input: ConfiguredLlmTierMapping) => {
    const nextLlmTiers = [...llmTiers.filter((item) => item.tier !== input.tier), input];
    const nextAudit = appendAudit(
      "SettingsChanged",
      `Niveau IA "${input.tier}" associé au modèle ${input.primaryModel} (${input.modelFamily})`,
      { scopeId: "scope-global", scopePath: "GLOBAL", scopeLabel: "Plateforme entière" },
    );
    setLlmTiers(nextLlmTiers);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ llmTiers: nextLlmTiers, auditEvents: nextAudit }));

    const client = createOrciaApiClient({ baseUrl: resolveWebApiBaseUrl() });
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
      .catch((err: unknown) => {
        setLastSyncError(
          err instanceof Error ? err.message : "Erreur d'enregistrement du modèle IA.",
        );
      });
  };

  const registerPack = (input: ConfiguredPackItem) => {
    const { nextPacks, nextCatalogItems, nextAudit } = applyRegisterPack({
      packs,
      catalogItems,
      input,
      appendAudit,
    });
    setPacks(nextPacks);
    setCatalogItems(nextCatalogItems);
    setAuditEvents(nextAudit);
    persistSnapshot(
      buildSnapshot({ packs: nextPacks, catalogItems: nextCatalogItems, auditEvents: nextAudit }),
    );
  };

  const removePack = (packKey: string, scopePath?: string) => {
    const nextPacks = packs.filter(
      (p) => !(p.packKey === packKey && (scopePath === undefined || p.scopePath === scopePath)),
    );
    const stillActiveSomewhere = nextPacks.some((p) => p.packKey === packKey);
    const nextCatalogItems = stillActiveSomewhere
      ? catalogItems
      : catalogItems.filter((item) => item.resourceId !== `pack-${packKey}`);
    const readableScope = formatHumanReadableScopePath(scopePath ?? "GLOBAL");
    const nextAudit = appendAudit(
      "PackDeactivated",
      `Pack "${packKey}" désactivé sur ${readableScope}`,
      { scopePath: scopePath ?? "GLOBAL", scopeLabel: readableScope },
    );
    setPacks(nextPacks);
    setCatalogItems(nextCatalogItems);
    setAuditEvents(nextAudit);
    persistSnapshot(
      buildSnapshot({ packs: nextPacks, catalogItems: nextCatalogItems, auditEvents: nextAudit }),
    );
  };

  const upsertWorkflow = (input: ConfiguredWorkflowItem) => {
    const { nextWorkflows, nextCatalogItems, nextAudit } = applyUpsertWorkflow({
      workflows,
      catalogItems,
      input,
      appendAudit,
    });
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
      `Terme métier "${input.canonicalTerm}" (${formatOntologyLevelLabel(input.level)}) créé`,
      {
        scopeId: input.scopeId || "scope-global",
        scopePath: input.scopeId || "GLOBAL",
        scopeLabel: formatHumanReadableScopePath(input.scopeId || "GLOBAL"),
      },
    );
    setOntologyConcepts(nextConcepts);
    setAuditEvents(nextAudit);
    persistSnapshot(
      buildSnapshot({ ontologyConcepts: nextConcepts, auditEvents: nextAudit }),
    );
  };

  const promoteOntologyConcept = (
    conceptKey: string,
    targetLevel: UiOntologyLevel,
    targetScopeId?: string,
  ) => {
    const outcome = applyPromoteOntologyConcept({
      ontologyConcepts,
      conceptKey,
      targetLevel,
      ...(targetScopeId !== undefined ? { targetScopeId } : {}),
      appendAudit,
    });
    if (!outcome) return;
    setOntologyConcepts(outcome.nextConcepts);
    setAuditEvents(outcome.nextAudit);
    persistSnapshot(
      buildSnapshot({ ontologyConcepts: outcome.nextConcepts, auditEvents: outcome.nextAudit }),
    );
  };

  return {
    createPlatformAdmin,
    toggleAdminTeamMembership,
    addOrgUnit,
    removeOrgUnit,
    syncOrgUnitsFromServer,
    addRbacGrant,
    removeRbacGrant,
    syncRbacGrantsFromServer,
    upsertLlmTier,
    registerPack,
    removePack,
    upsertWorkflow,
    launchRun,
    addOntologyConcept,
    promoteOntologyConcept,
  };
}
