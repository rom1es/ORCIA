import {
  FourZoneDirectionCShell,
  type EightFixedMenuKey,
  type UiHumanProfileBadge,
  type UiModuleKey,
} from "@orcia/ui";
import React from "react";
import { useI18n } from "../i18n";
import {
  canAccessConfigurationSettings,
  canAccessMyOrganization,
  canObserveGlobalAuditScope,
  resolveSessionHatLabel,
  useAuthSessionStore,
} from "../stores/authSessionStore";
import { buildContextualHelpArticle } from "./contextualHelpCatalog";
import { useShellAutonomousSupervision } from "./useShellAutonomousSupervision";
import {
  ShellHydratingLoaderView,
  ShellUnauthenticatedView,
} from "./ShellAuthFallbackView";
import { useOrciaNavigation } from "./navigationAdapter";
import { PlatformSetupProvider, usePlatformSetup } from "./platformSetupStore";
import { ShellContainerModals } from "./ShellContainerModals";
import { ShellContextualHelpColumn } from "./ShellContextualHelpColumn";
import {
  ShellNavigationContext,
  useShellNavigation,
  type ShellNavigationContextValue,
} from "./shellNavigationContext";
import {
  buildShellBreadcrumbItems,
  DEFAULT_HUMAN_PROFILE,
  DEFAULT_SHELL_MODULES,
  EMPTY_DEFAULT_SCOPES,
  evaluateScopeModuleVisibility,
  isDesktopOnlyMobileRoute,
  mapEightMenuKeyToModule,
  resolveEightMenuKeyFromModule,
  resolveModuleFromPathname,
} from "./shellPresets";
import {
  buildDoubleScopeSelectorState,
  buildShellDisabledMenuKeys,
  buildShellNotificationItems,
  buildWorkspaceSwitcherOptions,
} from "./shellScopeOptions";
import { ShellSidebarFooter } from "./ShellSidebarFooter";
import { TemporaryPasswordWarningBanner } from "./TemporaryPasswordWarningBanner";
import { useShellAuthRedirects, useShellContainerState } from "./useShellContainerState";

export {
  DEFAULT_HUMAN_PROFILE,
  DEFAULT_SHELL_MODULES,
  EMPTY_DEFAULT_SCOPES,
  evaluateScopeModuleVisibility,
  mapEightMenuKeyToModule,
  resolveEightMenuKeyFromModule,
  resolveModuleFromPathname,
  useShellNavigation,
  type ShellNavigationContextValue,
};

function InnerShellContainer({
  children,
  onNavigate,
}: {
  children: React.ReactNode;
  onNavigate?: (href: string) => void;
}) {
  const { locale, dictionary, setLocale } = useI18n();
  const { pathname, navigateTo } = useOrciaNavigation();
  const setup = usePlatformSetup();
  const {
    isInitialLoading, platformAdmin, scopes, orgUnits, workspaces,
    catalogItems, ontologyConcepts, llmTiers, runs, createPlatformAdmin,
  } = setup;

  const {
    isAuthenticated, isHydrating, mustChangePassword, roles,
    readOnlyObserver, email: sessionEmail, displayName: sessionDisplayName,
    openUserSettingsModalAtTab, logoutSession, hydrateSession,
  } = useAuthSessionStore();

  const canObserveGlobal = canObserveGlobalAuditScope({ roles, readOnlyObserver });
  const showOrganizationMenu = canAccessMyOrganization({ roles, readOnlyObserver });
  const firstScopedId =
    workspaces[0]?.workspaceId ?? scopes.find((s) => s.id !== "scope-global")?.id ?? orgUnits[0]?.id;

  const state = useShellContainerState(runs.length, pathname, {
    canObserveGlobalScope: canObserveGlobal,
    defaultScopedId: firstScopedId,
  });
  const isFr = locale === "fr";
  const dispatchNavigation = (href: string) => (onNavigate ? onNavigate(href) : navigateTo(href));

  const isAdminModalOpen = platformAdmin === null && !state.adminModalDismissed;
  const isShowcaseStandalone = Boolean(pathname?.startsWith("/showcase"));

  useShellAuthRedirects({
    isHydrating,
    isInitialLoading,
    isAuthenticated,
    isAdminModalOpen,
    isShowcaseStandalone,
    pathname,
    hydrateSession,
    dispatchNavigation,
  });

  const showConfigurationMenu = canAccessConfigurationSettings({ roles, readOnlyObserver });

  const activeModuleKey = state.selectedModuleOverride ?? resolveModuleFromPathname(pathname);
  const selectedScope =
    scopes.find((s) => s.id === state.activeScopeId) ?? scopes[0] ?? EMPTY_DEFAULT_SCOPES[0]!;

  const effectiveProfile: UiHumanProfileBadge = {
    ...DEFAULT_HUMAN_PROFILE,
    displayName: sessionDisplayName ?? (isAuthenticated ? platformAdmin?.displayName : DEFAULT_HUMAN_PROFILE.displayName) ?? DEFAULT_HUMAN_PROFILE.displayName,
    role: roles[0] || "CONTRIBUTOR",
    accessMode: selectedScope.accessMode,
  };
  const userHatLabel = resolveSessionHatLabel({ roles, readOnlyObserver }, locale);

  const safeModuleKey: UiModuleKey = activeModuleKey;
  const activeMenuKey: EightFixedMenuKey | null =
    state.selectedMenuKeyOverride ?? resolveEightMenuKeyFromModule(safeModuleKey, pathname);
  const openHelpSection = (sectionId: string) => {
    state.setHelpColumnOpen(true);
    state.setActiveHelpSectionId(sectionId);
  };

  const activeWorkspaceName =
    selectedScope.name ?? workspaces[0]?.name ?? "Plateforme Globale ORCIA";
  const { lastClaimEvent, autonomousRuns, inboxNotifications } = useShellAutonomousSupervision({
    isAuthenticated, selectedScope, workspaces,
  });

  const visibleScopes = canObserveGlobal ? scopes : scopes.filter((s) => s.id !== "scope-global");
  const effectiveScopes = visibleScopes.length > 0 ? visibleScopes : scopes;
  const workspaceOptions = buildWorkspaceSwitcherOptions({
    isFr, orgUnits, workspaces, scopes: effectiveScopes,
  });
  const doubleScopeState = buildDoubleScopeSelectorState({
    isFr,
    orgUnits,
    workspaces,
    scopes: effectiveScopes,
    activeScopeId: selectedScope.id,
  });
  const breadcrumbItems = buildShellBreadcrumbItems({
    pathname,
    isFr,
    menuEntries: dictionary.fourZoneShell.menuEntries,
  });
  const isDesktopOnlyRoute = isDesktopOnlyMobileRoute(pathname);
  const disabledMenuKeys = buildShellDisabledMenuKeys({ isFr, llmTiers, workspaces });
  const notificationItems = buildShellNotificationItems({
    isFr, platformAdmin, orgUnits, workspaces, llmTiers, runs, autonomousRuns, inboxNotifications, lastClaimEvent, mustChangePassword,
  });

  const helpTitleFallback = activeMenuKey
    ? dictionary.fourZoneShell.menuEntries[activeMenuKey]
    : dictionary.modulePages[safeModuleKey].subtitle;

  const contextualHelpArticle = buildContextualHelpArticle({
    activeMenuKey: activeMenuKey ?? "cockpit",
    pathname,
    locale,
    title: helpTitleFallback,
    defaultSummary: dictionary.modulePages[safeModuleKey].description,
  });

  const isHelpCenterRoute = Boolean(pathname?.startsWith("/help"));
  const hideSidebarShowcaseBtn =
    isHelpCenterRoute || Boolean(pathname?.startsWith("/ontology"));

  if (!isShowcaseStandalone && (isHydrating || (isInitialLoading && !isAuthenticated))) {
    return <ShellHydratingLoaderView isFr={isFr} />;
  }

  if (!isShowcaseStandalone && !isAuthenticated && !isAdminModalOpen) {
    return <ShellUnauthenticatedView />;
  }

  return (
    <ShellNavigationContext.Provider
      value={{
        activeModuleKey: safeModuleKey,
        activeMenuKey,
        activeScopeId: selectedScope.id,
        helpColumnOpen: state.helpColumnOpen,
        activeHelpSectionId: state.activeHelpSectionId,
        navigateToRoute: dispatchNavigation,
        openHelpSection,
      }}
    >
      <FourZoneDirectionCShell
        activeMenuKey={activeMenuKey}
        showOrganizationMenu={showOrganizationMenu}
        organizationMenuActive={Boolean(pathname?.startsWith("/organization"))}
        activityMenuActive={Boolean(pathname?.startsWith("/activity"))}
        breadcrumbItems={breadcrumbItems}
        onNavigateBreadcrumb={(route) => dispatchNavigation(route)}
        activeWorkspaceName={activeWorkspaceName}
        activeScopeId={selectedScope.id}
        workspaceOptions={workspaceOptions}
        teamBuOptions={doubleScopeState.teamBuOptions}
        activeTeamBuId={doubleScopeState.activeTeamBuId}
        onSelectTeamBu={(scopeId) => state.setActiveScopeId(scopeId)}
        workspaceSelectorOptions={doubleScopeState.workspaceSelectorOptions}
        activeWorkspaceSelectorId={doubleScopeState.activeWorkspaceSelectorId}
        onSelectWorkspaceFromSidebar={(scopeId) =>
          state.setActiveScopeId(scopeId || doubleScopeState.activeTeamBuId)
        }
        onSelectWorkspace={(scopeId) => state.setActiveScopeId(scopeId)}
        isDesktopOnlyRoute={isDesktopOnlyRoute}
        activeMobileBottomTab={
          pathname?.startsWith("/inbox")
            ? "decisions"
            : pathname?.startsWith("/assistant")
              ? "assistant"
              : pathname === "/" || pathname?.startsWith("/cockpit")
                ? "cockpit"
                : null
        }
        onSelectMobileBottomTab={(tab) => {
          if (tab === "cockpit") {
            state.setSelectedMenuKeyOverride("cockpit");
            state.setSelectedModuleOverride("cockpit");
            dispatchNavigation("/cockpit");
          } else if (tab === "assistant") {
            if (!disabledMenuKeys.assistant) {
              state.setSelectedMenuKeyOverride("assistant");
              state.setSelectedModuleOverride("inbox");
              dispatchNavigation("/assistant");
            }
          } else {
            state.setSelectedMenuKeyOverride("assistant");
            state.setSelectedModuleOverride("inbox");
            dispatchNavigation("/inbox");
          }
        }}
        activePackKey=""
        availablePacks={[]}
        userDisplayName={effectiveProfile.displayName}
        userHatLabel={userHatLabel}
        pendingDecisionsTotal={runs.length}
        notifications={notificationItems}
        onSelectNotification={(item) => {
          if (item.targetRoute === "#change-password") {
            openUserSettingsModalAtTab("ACCOUNT_SECURITY");
            return;
          }
          if (item.targetRoute) {
            dispatchNavigation(item.targetRoute);
          }
        }}
        labels={dictionary.fourZoneShell}
        viewportWidth={state.viewportWidth}
        disabledMenuKeys={disabledMenuKeys}
        hiddenMenuKeys={showConfigurationMenu ? [] : ["configuration"]}
        helpColumnOpen={isHelpCenterRoute ? false : state.helpColumnOpen}
        onHelpColumnOpenChange={(nextOpen) => {
          if (!isHelpCenterRoute) {
            state.setHelpColumnOpen(nextOpen);
          }
        }}
        onSelectMenu={(menuKey) => {
          const mapped = mapEightMenuKeyToModule(menuKey);
          state.setSelectedMenuKeyOverride(menuKey);
          state.setSelectedModuleOverride(mapped.moduleKey);
          dispatchNavigation(mapped.route);
        }}
        onSelectOrganizationMenu={(route) => {
          state.setSelectedMenuKeyOverride("spaces");
          state.setSelectedModuleOverride("admin");
          dispatchNavigation(route);
        }}
        onSelectActivityMenu={(route) => {
          state.setSelectedMenuKeyOverride("finops");
          state.setSelectedModuleOverride("finops");
          dispatchNavigation(route);
        }}
        onOpenWorkspaceSwitcher={() => undefined}
        onOpenSearchCommand={() => state.setSearchModalOpen(true)}
        renderSidebarFooter={(railCollapsed) => (
          <ShellSidebarFooter
            railCollapsed={railCollapsed}
            hideSidebarShowcaseBtn={hideSidebarShowcaseBtn}
            pathname={pathname}
            userDisplayName={effectiveProfile.displayName}
            userEmail={sessionEmail ?? (isAuthenticated ? platformAdmin?.email : "") ?? ""}
            userRole={roles[0] ?? "CONTRIBUTOR"}
            userRoleLabel={userHatLabel}
            locale={locale}
            footerLabels={dictionary.sidebarFooter}
            accountLabels={dictionary.userAccountAndSettings}
            onLocaleChange={(nextLocale) => setLocale(nextLocale)}
            onNavigate={(href) => dispatchNavigation(href)}
            onLogout={() => {
              void logoutSession().then(() => dispatchNavigation("/login"));
            }}
            onOpenShowcase={() => {
              state.setSelectedMenuKeyOverride(null);
              state.setSelectedModuleOverride("ontology");
              dispatchNavigation("/showcase");
            }}
          />
        )}
        helpColumnContent={
          isHelpCenterRoute ? undefined : (
            <ShellContextualHelpColumn
              pathname={pathname}
              locale={locale}
              contextualHelpArticle={contextualHelpArticle}
              activeHelpSectionId={state.activeHelpSectionId}
              labels={dictionary.contextualHelpHybrid}
              autonomousBadgeLabels={dictionary.autonomousSupervision.badge}
              onAskAssistant={() => {
                if (!disabledMenuKeys.assistant) {
                  state.setSelectedMenuKeyOverride("assistant");
                  state.setSelectedModuleOverride("inbox");
                  dispatchNavigation("/assistant");
                }
              }}
            />
          )
        }
      >
        <div className="flex h-full flex-col">
          {mustChangePassword && (
            <TemporaryPasswordWarningBanner
              isFr={isFr}
              onOpenSettings={() => {
                openUserSettingsModalAtTab("ACCOUNT_SECURITY");
              }}
            />
          )}
          <div className="flex-1">{children}</div>
        </div>
      </FourZoneDirectionCShell>

      <ShellContainerModals
        isFr={isFr}
        isAdminModalOpen={isAdminModalOpen}
        searchModalOpen={state.searchModalOpen}
        pathname={pathname}
        activeScopeId={selectedScope.id}
        workspaces={workspaces}
        catalogItems={catalogItems}
        ontologyConcepts={ontologyConcepts}
        labels={dictionary.topHeaderSearch}
        disabledMenuKeys={disabledMenuKeys}
        onDismissAdminModal={() => state.setAdminModalDismissed(true)}
        onCreatePlatformAdmin={createPlatformAdmin}
        onCloseSearchModal={() => state.setSearchModalOpen(false)}
        onDispatchNavigation={dispatchNavigation}
        onOpenAssistantFromSearch={() => {
          state.setSelectedMenuKeyOverride("assistant");
          state.setSelectedModuleOverride("inbox");
          dispatchNavigation("/assistant");
        }}
      />
    </ShellNavigationContext.Provider>
  );
}

export function ShellContainer({
  children,
  onNavigate,
}: {
  children: React.ReactNode;
  onNavigate?: (href: string) => void;
}) {
  return (
    <PlatformSetupProvider>
      <InnerShellContainer onNavigate={onNavigate}>{children}</InnerShellContainer>
    </PlatformSetupProvider>
  );
}
