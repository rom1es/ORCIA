import {
  FourZoneDirectionCShell,
  type EightFixedMenuKey,
  type UiModuleKey,
} from "@orcia/ui";
import React from "react";
import { useI18n } from "../i18n";
import {
  canAccessConfigurationSettings,
  canObserveGlobalAuditScope,
  resolveSessionHatLabel,
  useAuthSessionStore,
} from "../stores/authSessionStore";
import { buildContextualHelpArticle } from "./contextualHelpCatalog";
import { writeAssistantPrefillPrompt } from "./agentsAndSkillsBridgeStore";
import { useShellAutonomousSupervision } from "./useShellAutonomousSupervision";
import {
  ShellCentralWorkspaceBody,
  ShellHydratingLoaderView,
  ShellUnauthenticatedView,
} from "./ShellAuthFallbackView";
import { useOrciaNavigation } from "./navigationAdapter";
import { PlatformSetupProvider, usePlatformSetup } from "./platformSetupStore";
import { ShellContainerModals } from "./ShellContainerModals";
import { ShellUserSettingsModal } from "./ShellUserSettingsModal";
import { ShellContextualHelpColumn } from "./ShellContextualHelpColumn";
import {
  ShellNavigationContext,
  useShellNavigation,
  type ShellNavigationContextValue,
} from "./shellNavigationContext";
import {
  buildShellBreadcrumbItems,
  DEFAULT_SHELL_MODULES,
  EMPTY_DEFAULT_SCOPES,
  evaluateScopeModuleVisibility,
  isDesktopOnlyMobileRoute,
  mapEightMenuKeyToModule,
  resolveActiveMobileBottomTab,
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
import { useShellAuthRedirects, useShellContainerState } from "./useShellContainerState";

export {
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
    catalogItems, ontologyConcepts, llmTiers, runs, accostageSummary, createPlatformAdmin,
  } = setup;

  const {
    isAuthenticated, isHydrating, mustChangePassword, roles,
    readOnlyObserver, email: sessionEmail, displayName: sessionDisplayName,
    userSettingsModalOpen, openUserSettingsModalAtTab, logoutSession, hydrateSession,
  } = useAuthSessionStore();

  const canObserveGlobal = canObserveGlobalAuditScope({ roles, readOnlyObserver });
  const firstScopedId =
    workspaces[0]?.workspaceId ?? scopes.find((s) => s.id !== "scope-global")?.id ?? orgUnits[0]?.id;

  const state = useShellContainerState(runs.length, pathname, {
    canObserveGlobalScope: canObserveGlobal,
    defaultScopedId: firstScopedId,
  });
  const isFr = locale === "fr";
  const dispatchNavigation = (href: string) => (onNavigate ? onNavigate(href) : navigateTo(href));
  const isShowcaseStandalone = Boolean(pathname?.startsWith("/showcase"));
  const isAdminModalOpen = !isShowcaseStandalone && platformAdmin === null && !state.adminModalDismissed;

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
  const activeOrgUnitLabel =
    orgUnits.find((u) => u.id === doubleScopeState.activeTeamBuId)?.name ?? null;
  const breadcrumbItems = buildShellBreadcrumbItems({
    pathname,
    isFr,
    menuEntries: dictionary.fourZoneShell.menuEntries,
    activeTeamLabel: activeOrgUnitLabel,
  });
  const isDesktopOnlyRoute = isDesktopOnlyMobileRoute(pathname);
  const disabledMenuKeys = buildShellDisabledMenuKeys({
    isFr,
    adminCreated: accostageSummary.adminCreated,
    day0AdminMissingReason: dictionary.firstBootAdminModal.day0DisabledAdminMissingReason,
    llmTiers,
    workspaces,
    hasModels: accostageSummary.hasModels,
    hasWorkspaces: accostageSummary.hasWorkspaces,
  });
  const notificationItems = buildShellNotificationItems({
    isFr,
    platformAdmin,
    orgUnits,
    workspaces,
    llmTiers,
    hasModels: accostageSummary.hasModels,
    hasOrgUnits: accostageSummary.hasOrgUnits,
    hasWorkspaces: accostageSummary.hasWorkspaces,
    runs,
    autonomousRuns,
    inboxNotifications,
    lastClaimEvent,
    mustChangePassword,
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
  const hideSidebarShowcaseBtn = isHelpCenterRoute || Boolean(pathname?.startsWith("/ontology"));

  const selectModuleAndNavigate = (
    menuKey: EightFixedMenuKey | null, moduleKey: UiModuleKey, route: string,
  ) => {
    state.setSelectedMenuKeyOverride(menuKey);
    state.setSelectedModuleOverride(moduleKey);
    dispatchNavigation(route);
  };

  if (!isShowcaseStandalone && (isHydrating || (isInitialLoading && !isAuthenticated))) {
    return <ShellHydratingLoaderView isFr={isFr} />;
  }

  if (!isShowcaseStandalone && !isAuthenticated && !isAdminModalOpen) {
    return (
      <ShellUnauthenticatedView
        onReopenDay0Setup={platformAdmin === null ? () => state.setAdminModalDismissed(false) : undefined}
        reopenDay0SetupLabel={dictionary.firstBootAdminModal.reopenSetupCta}
      />
    );
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
        breadcrumbItems={breadcrumbItems}
        onNavigateBreadcrumb={dispatchNavigation}
        activeWorkspaceName={activeWorkspaceName}
        activeScopeId={selectedScope.id}
        workspaceOptions={workspaceOptions}
        teamBuOptions={doubleScopeState.teamBuOptions}
        activeTeamBuId={doubleScopeState.activeTeamBuId}
        onSelectTeamBu={state.setActiveScopeId}
        workspaceSelectorOptions={doubleScopeState.workspaceSelectorOptions}
        activeWorkspaceSelectorId={doubleScopeState.activeWorkspaceSelectorId}
        onSelectWorkspaceFromSidebar={(scopeId) =>
          state.setActiveScopeId(scopeId || doubleScopeState.activeTeamBuId)
        }
        onSelectWorkspace={state.setActiveScopeId}
        isDesktopOnlyRoute={isDesktopOnlyRoute}
        activeMobileBottomTab={resolveActiveMobileBottomTab(pathname)}
        onSelectMobileBottomTab={(tab) => {
          if (tab === "cockpit") selectModuleAndNavigate("cockpit", "cockpit", "/cockpit");
          else if (tab === "assistant" && !disabledMenuKeys.assistant)
            selectModuleAndNavigate("assistant", "inbox", "/assistant");
          else if (tab === "decisions") selectModuleAndNavigate("assistant", "inbox", "/inbox");
        }}
        activePackKey=""
        availablePacks={[]}
        userDisplayName={effectiveDisplayName}
        userHatLabel={userHatLabel}
        pendingDecisionsTotal={hasAuthenticatedIdentity ? runs.length : 0}
        notifications={notificationItems}
        onSelectNotification={(item) => {
          if (item.targetRoute === "#change-password") {
            openUserSettingsModalAtTab("ACCOUNT_SECURITY");
          } else if (item.targetRoute) {
            dispatchNavigation(item.targetRoute);
          }
        }}
        labels={dictionary.fourZoneShell}
        viewportWidth={state.viewportWidth}
        disabledMenuKeys={disabledMenuKeys}
        hiddenMenuKeys={showConfigurationMenu ? [] : ["configuration"]}
        helpColumnOpen={isHelpCenterRoute ? false : state.helpColumnOpen}
        mobileDrawerCloseSignal={`${pathname ?? ""}:${String(userSettingsModalOpen)}`}
        onHelpColumnOpenChange={(nextOpen) => !isHelpCenterRoute && state.setHelpColumnOpen(nextOpen)}
        onSelectMenu={(menuKey) => {
          const mapped = mapEightMenuKeyToModule(menuKey);
          selectModuleAndNavigate(menuKey, mapped.moduleKey, mapped.route);
        }}
        onSelectActivityMenu={(route) => selectModuleAndNavigate("finops", "finops", route)}
        onOpenWorkspaceSwitcher={() => undefined}
        onOpenSearchCommand={() => state.setSearchModalOpen(true)}
        renderSidebarFooter={
          hasAuthenticatedIdentity
            ? (railCollapsed) => (
                <ShellSidebarFooter
                  railCollapsed={railCollapsed}
                  hideSidebarShowcaseBtn={hideSidebarShowcaseBtn}
                  pathname={pathname}
                  userDisplayName={effectiveDisplayName}
                  userEmail={effectiveEmail}
                  userRole={roles[0] ?? "CONTRIBUTOR"}
                  userRoleLabel={userHatLabel}
                  locale={locale}
                  footerLabels={dictionary.sidebarFooter}
                  accountLabels={dictionary.userAccountAndSettings}
                  onLocaleChange={setLocale}
                  onNavigate={dispatchNavigation}
                  onLogout={() => void logoutSession().then(() => dispatchNavigation("/login"))}
                  onOpenShowcase={() => selectModuleAndNavigate(null, "ontology", "/showcase")}
                />
              )
            : undefined
        }
        helpColumnContent={
          isHelpCenterRoute ? undefined : (
            <ShellContextualHelpColumn
              pathname={pathname}
              locale={locale}
              contextualHelpArticle={contextualHelpArticle}
              activeHelpSectionId={state.activeHelpSectionId}
              labels={dictionary.contextualHelpHybrid}
              autonomousBadgeLabels={dictionary.autonomousSupervision.badge}
              onAskAssistant={(_route, prefillPrompt) => {
                if (disabledMenuKeys.assistant) return;
                if (prefillPrompt?.trim()) {
                  writeAssistantPrefillPrompt(prefillPrompt.trim());
                }
                if (onNavigate) {
                  selectModuleAndNavigate("assistant", "inbox", "/assistant");
                } else {
                  dispatchNavigation("/assistant");
                }
              }}
            />
          )
        }
      >
        <ShellCentralWorkspaceBody
          lastSyncError={setup.lastSyncError}
          mustChangePassword={mustChangePassword}
          isFr={isFr}
          onOpenAccountSecurity={() => openUserSettingsModalAtTab("ACCOUNT_SECURITY")}
        >
          {children}
        </ShellCentralWorkspaceBody>
      </FourZoneDirectionCShell>

      <ShellContainerModals
        isFr={isFr} isAdminModalOpen={isAdminModalOpen} searchModalOpen={state.searchModalOpen}
        pathname={pathname} activeScopeId={selectedScope.id} workspaces={workspaces}
        catalogItems={catalogItems} ontologyConcepts={ontologyConcepts}
        labels={dictionary.topHeaderSearch} disabledMenuKeys={disabledMenuKeys}
        onDismissAdminModal={() => state.setAdminModalDismissed(true)}
        onCreatePlatformAdmin={createPlatformAdmin}
        onCloseSearchModal={() => state.setSearchModalOpen(false)}
        onDispatchNavigation={dispatchNavigation}
        onOpenAssistantFromSearch={(query) => {
          if (query.trim()) {
            writeAssistantPrefillPrompt(query.trim());
          }
          if (onNavigate) {
            selectModuleAndNavigate("assistant", "inbox", "/assistant");
          } else {
            dispatchNavigation("/assistant");
          }
        }}
      />
      {isAuthenticated && (
        <ShellUserSettingsModal
          userEmail={effectiveEmail} userRole={roles[0] ?? "CONTRIBUTOR"} locale={locale}
          labels={dictionary.userAccountAndSettings} onLocaleChange={setLocale} onNavigate={dispatchNavigation}
        />
      )}
    </ShellNavigationContext.Provider>
  );
}

export function ShellContainer({ children, onNavigate }: { children: React.ReactNode; onNavigate?: (href: string) => void }) {
  return (
    <PlatformSetupProvider>
      <InnerShellContainer onNavigate={onNavigate}>{children}</InnerShellContainer>
    </PlatformSetupProvider>
  );
}
