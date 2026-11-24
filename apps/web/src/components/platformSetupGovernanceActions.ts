import { createOrciaApiClient } from "@orcia/api-client";
import type {
  ControlCenterRunItem,
  ControlCenterWorkspaceGovItem,
  UiCatalogExplorerItemView,
  UiOntologyConceptView,
} from "@orcia/ui";
import { DICTIONARIES, formatI18nTemplate, type SupportedWebLocale } from "../i18n";
import { formatRfc9457ErrorToBanner } from "../lib/formatRfc9457ErrorToBanner";
import { resolveWebApiBaseUrl, useAuthSessionStore } from "../stores/authSessionStore";
import { createPlatformCatalogAndRunActions } from "./platformSetupCatalogAndRunActions";
import type { AppendAuditFn } from "./platformSetupOrgAndGovernance";
import { createPlatformOrgAndRbacActions } from "./platformSetupOrgAndRbacActions";
import {
  writeCachedPlatformAdmin,
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
  readonly locale?: SupportedWebLocale;
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
    locale = "fr",
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
  const copy = DICTIONARIES[locale].shellChrome.platformSetupGovernance;

  const orgAndRbacActions = createPlatformOrgAndRbacActions({
    locale,
    platformAdmin,
    orgUnits,
    rbacGrants,
    workspaces,
    setPlatformAdmin,
    setOrgUnits,
    setRbacGrants,
    setAuditEvents,
    markMutated,
    appendAudit,
    buildSnapshot,
    persistSnapshot,
  });

  const catalogAndRunActions = createPlatformCatalogAndRunActions({
    locale,
    packs,
    workflows,
    runs,
    catalogItems,
    ontologyConcepts,
    setPacks,
    setWorkflows,
    setRuns,
    setCatalogItems,
    setOntologyConcepts,
    setAuditEvents,
    appendAudit,
    buildSnapshot,
    persistSnapshot,
  });

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
    const rawPassword =
      input.password && input.password.trim().length >= 8
        ? input.password.trim()
        : "OrciaInitialAdmin!2026";
    const client = createOrciaApiClient({ baseUrl: resolveWebApiBaseUrl(), locale });
    markMutated();
    void client
      .createWelcomeSetupFirstAdmin({
        email: admin.email,
        display_name: admin.displayName,
        password: rawPassword,
        orcia_env: "local",
      })
      .then(async (res) => {
        const token =
          res?.access_token ??
          ((res as Record<string, unknown> | undefined)?.accessToken as string | undefined);
        if (token) {
          useAuthSessionStore.getState().loginWithSession({
            access_token: token,
            email: admin.email,
            display_name: admin.displayName,
            platform_role: "PLATFORM_ADMIN",
            roles: ["PLATFORM_ADMIN"],
            must_change_password: Boolean(res.must_change_password),
          });
        } else {
          await useAuthSessionStore.getState().hydrateSession({ force: true });
        }
        writeCachedPlatformAdmin(admin);
        setPlatformAdmin(admin);
        const nextAudit = appendAudit(
          "PlatformAdminInitialized",
          formatI18nTemplate(copy.adminCreatedTemplate, {
            displayName: admin.displayName,
            email: admin.email,
          }),
          {
            actorName: admin.displayName,
            actorEmail: admin.email,
            scopeId: "scope-global",
            scopePath: "GLOBAL",
            scopeLabel: copy.globalScopeLabel,
          },
        );
        setAuditEvents(nextAudit);
        persistSnapshot(buildSnapshot({ auditEvents: nextAudit }));
      })
      .catch(async (err: unknown) => {
        setLastSyncError(
          formatRfc9457ErrorToBanner(err, locale, copy.adminInitErrorContext).fullText,
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

  const upsertLlmTier = (input: ConfiguredLlmTierMapping) => {
    const nextLlmTiers = [...llmTiers.filter((item) => item.tier !== input.tier), input];
    const nextAudit = appendAudit(
      "SettingsChanged",
      formatI18nTemplate(copy.llmTierConfiguredTemplate, {
        tier: input.tier,
        primaryModel: input.primaryModel,
        modelFamily: input.modelFamily,
      }),
      { scopeId: "scope-global", scopePath: "GLOBAL", scopeLabel: copy.globalScopeLabel },
    );
    setLlmTiers(nextLlmTiers);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ llmTiers: nextLlmTiers, auditEvents: nextAudit }));

    const client = createOrciaApiClient({ baseUrl: resolveWebApiBaseUrl(), locale });
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
          formatRfc9457ErrorToBanner(err, locale, copy.aiModelConfigErrorContext).fullText,
        );
      });
  };

  return {
    ...orgAndRbacActions,
    ...catalogAndRunActions,
    createPlatformAdmin,
    upsertLlmTier,
  };
}
