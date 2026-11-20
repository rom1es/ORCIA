import type {
  EightFixedMenuKey,
  ShellBreadcrumbItem,
  UiLocalePreference,
  UiModuleKey,
  UiScopeNode,
} from "@orcia/ui";
import type { TranslationDictionary } from "../i18n/types";
import {
  canAccessConfigurationSettings,
  canObserveGlobalAuditScope,
  resolveSessionHatLabel,
  type AuthSessionStoreState,
} from "../stores/authSessionStore";
import type { PlatformSetupContextValue } from "./platformSetupStore";
import {
  buildShellBreadcrumbItems,
  EMPTY_DEFAULT_SCOPES,
  resolveEightMenuKeyFromModule,
  resolveModuleFromPathname,
} from "./shellPresets";
import {
  buildDoubleScopeSelectorState,
  buildShellDisabledMenuKeys,
  buildShellNotificationItems,
  buildUnifiedScopeSelectorState,
  buildWorkspaceSwitcherOptions,
  type DoubleScopeSelectorState,
  type UnifiedScopeSelectorState,
  type WorkspaceSwitcherOptionItem,
} from "./shellScopeOptions";

export interface DerivedShellScopeAndBreadcrumbs {
  readonly showConfigurationMenu: boolean;
  readonly safeModuleKey: UiModuleKey;
  readonly activeMenuKey: EightFixedMenuKey | null;
  readonly selectedScope: UiScopeNode;
  readonly hasAuthenticatedIdentity: boolean;
  readonly effectiveDisplayName: string;
  readonly effectiveEmail: string;
  readonly userHatLabel: string;
  readonly workspaceOptions: readonly WorkspaceSwitcherOptionItem[];
  readonly doubleScopeState: DoubleScopeSelectorState;
  readonly unifiedScopeState: UnifiedScopeSelectorState;
  readonly activeWorkspaceName: string;
  readonly breadcrumbItems: readonly ShellBreadcrumbItem[];
  readonly disabledMenuKeys: Partial<Record<EightFixedMenuKey, string>>;
  readonly notificationItems: ReturnType<typeof buildShellNotificationItems>;
}

function resolveRouteWorkspaceName(
  pathname: string | undefined,
  workspaces: PlatformSetupContextValue["workspaces"],
): string | null {
  if (!pathname) return null;
  const match = pathname.match(/^\/workspaces\/([^/]+)/);
  if (!match || !match[1]) return null;
  const wsIdOrSlug = decodeURIComponent(match[1]);
  const found = workspaces.find(
    (w) => w.workspaceId === wsIdOrSlug || w.slug === wsIdOrSlug,
  );
  return found?.name ?? null;
}

export function deriveShellScopeAndBreadcrumbs(params: {
  readonly pathname: string | undefined;
  readonly locale: UiLocalePreference;
  readonly auth: Pick<
    AuthSessionStoreState,
    "isAuthenticated" | "roles" | "readOnlyObserver" | "email" | "displayName" | "mustChangePassword"
  >;
  readonly setup: Pick<
    PlatformSetupContextValue,
    "scopes" | "orgUnits" | "workspaces" | "llmTiers" | "runs" | "platformAdmin" | "accostageSummary"
  >;
  readonly activeScopeId: string;
  readonly selectedModuleOverride: UiModuleKey | null;
  readonly selectedMenuKeyOverride: EightFixedMenuKey | null;
  readonly dictionary: TranslationDictionary;
  readonly autonomousRuns: Parameters<typeof buildShellNotificationItems>[0]["autonomousRuns"];
  readonly inboxNotifications: Parameters<typeof buildShellNotificationItems>[0]["inboxNotifications"];
  readonly lastClaimEvent: Parameters<typeof buildShellNotificationItems>[0]["lastClaimEvent"];
}): DerivedShellScopeAndBreadcrumbs {
  const {
    pathname,
    locale,
    auth,
    setup,
    activeScopeId,
    selectedModuleOverride,
    selectedMenuKeyOverride,
    dictionary,
    autonomousRuns,
    inboxNotifications,
    lastClaimEvent,
  } = params;
  const { isAuthenticated, roles, readOnlyObserver, email: sessionEmail, displayName: sessionDisplayName, mustChangePassword } = auth;
  const { scopes, orgUnits, workspaces, llmTiers, runs, platformAdmin, accostageSummary } = setup;
  const { adminCreated, hasModels, hasOrgUnits, hasWorkspaces } = accostageSummary;

  const isFr = locale === "fr";
  const canObserveGlobal = canObserveGlobalAuditScope({ roles, readOnlyObserver });
  const showConfigurationMenu = canAccessConfigurationSettings({ roles, readOnlyObserver });
  const safeModuleKey: UiModuleKey = selectedModuleOverride ?? resolveModuleFromPathname(pathname ?? null);
  const activeMenuKey: EightFixedMenuKey | null =
    selectedMenuKeyOverride ??
    resolveEightMenuKeyFromModule(safeModuleKey, pathname ?? null, {
      canAccessConfiguration: showConfigurationMenu,
    });
  const selectedScope =
    scopes.find((s) => s.id === activeScopeId) ?? scopes[0] ?? EMPTY_DEFAULT_SCOPES[0]!;
  const hasAuthenticatedIdentity =
    isAuthenticated &&
    (platformAdmin !== null || Boolean(sessionDisplayName?.trim() || sessionEmail?.trim()));
  const effectiveDisplayName = hasAuthenticatedIdentity
    ? (sessionDisplayName ?? platformAdmin?.displayName ?? "")
    : "";
  const effectiveEmail = hasAuthenticatedIdentity
    ? (sessionEmail ?? platformAdmin?.email ?? "")
    : "";
  const userHatLabel = hasAuthenticatedIdentity
    ? resolveSessionHatLabel({ roles, readOnlyObserver }, locale)
    : "";

  const visibleScopes = canObserveGlobal ? scopes : scopes.filter((s) => s.id !== "scope-global");
  const effectiveScopes = visibleScopes.length > 0 ? visibleScopes : scopes;
  const workspaceOptions = buildWorkspaceSwitcherOptions({
    isFr,
    orgUnits,
    workspaces,
    scopes: effectiveScopes,
  });
  const doubleScopeState = buildDoubleScopeSelectorState({
    isFr,
    orgUnits,
    workspaces,
    scopes: effectiveScopes,
    activeScopeId: selectedScope.id,
  });
  const unifiedScopeState = buildUnifiedScopeSelectorState({
    isFr,
    orgUnits,
    workspaces,
    activeScopeId: selectedScope.id,
    labels: dictionary.fourZoneShell.doubleSelector,
  });

  const activeOrgUnitLabel =
    orgUnits.find((u) => u.id === doubleScopeState.activeTeamBuId)?.name ?? null;
  const activeWorkspaceLabel =
    workspaces.find((w) => w.workspaceId === doubleScopeState.activeWorkspaceSelectorId)?.name ??
    resolveRouteWorkspaceName(pathname, workspaces) ??
    (selectedScope.level === "WORKSPACE" ? selectedScope.name : null);

  const breadcrumbItems = buildShellBreadcrumbItems({
    pathname,
    isFr,
    menuEntries: dictionary.fourZoneShell.menuEntries,
    activeTeamLabel: activeOrgUnitLabel,
    activeWorkspaceLabel,
    canAccessConfiguration: showConfigurationMenu,
  });

  const activeWorkspaceName =
    selectedScope.name ??
    workspaces[0]?.name ??
    dictionary.fourZoneShell.doubleSelector?.globalPlatformLabel ??
    "ORCIA";

  const disabledMenuKeys = buildShellDisabledMenuKeys({
    isFr,
    adminCreated,
    day0AdminMissingReason: dictionary.firstBootAdminModal.day0DisabledAdminMissingReason,
    llmTiers,
    workspaces,
    hasModels,
    hasWorkspaces,
  });

  const notificationItems = buildShellNotificationItems({
    isFr,
    platformAdmin,
    orgUnits,
    workspaces,
    llmTiers,
    hasModels,
    hasOrgUnits,
    hasWorkspaces,
    runs,
    autonomousRuns,
    inboxNotifications,
    lastClaimEvent,
    mustChangePassword,
  });

  return {
    showConfigurationMenu,
    safeModuleKey,
    activeMenuKey,
    selectedScope,
    hasAuthenticatedIdentity,
    effectiveDisplayName,
    effectiveEmail,
    userHatLabel,
    workspaceOptions,
    doubleScopeState,
    unifiedScopeState,
    activeWorkspaceName,
    breadcrumbItems,
    disabledMenuKeys,
    notificationItems,
  };
}
