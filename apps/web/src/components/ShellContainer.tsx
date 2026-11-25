import {
  FourZoneDirectionCShell,
  type EightFixedMenuKey,
  type UiModuleKey,
} from "@orcia/ui";
import React from "react";
import { useI18n } from "../i18n";
import {
  canObserveGlobalAuditScope,
  useAuthSessionStore,
} from "../stores/authSessionStore";
import { writeAssistantPrefillPrompt } from "./agentsAndSkillsBridgeStore";
import { useOrciaNavigation } from "./navigationAdapter";
import { PlatformSetupProvider, usePlatformSetup } from "./platformSetupStore";
import {
  ShellCentralWorkspaceBody,
  ShellHydratingLoaderView,
  ShellUnauthenticatedView,
} from "./ShellAuthFallbackView";
import { deriveShellScopeAndBreadcrumbs } from "./shellBreadcrumbAndScope";
import { ShellContainerModals } from "./ShellContainerModals";
import {
  ShellNavigationContext,
  useShellNavigation,
  type ShellNavigationContextValue,
} from "./shellNavigationContext";
import {
  DEFAULT_SHELL_MODULES,
  EMPTY_DEFAULT_SCOPES,
  evaluateScopeModuleVisibility,
  isDesktopOnlyMobileRoute,
  mapEightMenuKeyToModule,
  resolveActiveMobileBottomTab,
  resolveEightMenuKeyFromModule,
  resolveModuleFromPathname,
} from "./shellPresets";
import { renderShellSidebarFooter } from "./ShellSidebarFooter";
import { ShellUserSettingsModal } from "./ShellUserSettingsModal";
import { renderShellZone4HelpColumn } from "./shellZone4HelpWiring";
import { useShellAutonomousSupervision } from "./useShellAutonomousSupervision";
import {
  clearSavedActiveScopeId,
  useShellAuthRedirects,
  useShellContainerState,
} from "./useShellContainerState";

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
  const { locale, isFr, dictionary, setLocale } = useI18n();
  const { pathname, navigateTo } = useOrciaNavigation();
  const setup = usePlatformSetup();
  const {
    isInitialLoading, platformAdmin, scopes, orgUnits, workspaces,
    catalogItems, ontologyConcepts, runs, createPlatformAdmin,
  } = setup;
  const auth = useAuthSessionStore();
  const canObserveGlobal = canObserveGlobalAuditScope({
    roles: auth.roles,
    readOnlyObserver: auth.readOnlyObserver,
  });
  const firstScopedId =
    workspaces[0]?.workspaceId ?? scopes.find((s) => s.id !== "scope-global")?.id ?? orgUnits[0]?.id;
  const validScopeIds = [
    ...workspaces.map((w) => w.workspaceId),
    ...orgUnits.map((u) => u.id),
    ...scopes.map((s) => s.id),
  ];

  const state = useShellContainerState(runs.length, pathname, {
    canObserveGlobalScope: canObserveGlobal,
    defaultScopedId: firstScopedId,
    isAuthHydrating: auth.isHydrating,
    isInitialLoading,
    isAuthenticated: auth.isAuthenticated,
    currentUserEmail: auth.email,
    validScopeIds,
  });
  const dispatchNavigation = (href: string) => (onNavigate ? onNavigate(href) : navigateTo(href));
  const isShowcaseStandalone = Boolean(pathname?.startsWith("/showcase"));
  const isAdminModalOpen = !isShowcaseStandalone && platformAdmin === null && !state.adminModalDismissed;

  useShellAuthRedirects({
    isHydrating: auth.isHydrating,
    isInitialLoading,
    isAuthenticated: auth.isAuthenticated,
    isAdminModalOpen,
    isShowcaseStandalone,
    pathname,
    hydrateSession: auth.hydrateSession,
    dispatchNavigation,
  });

  const preliminaryScope =
    scopes.find((s) => s.id === state.activeScopeId) ?? scopes[0] ?? EMPTY_DEFAULT_SCOPES[0]!;
  const { lastClaimEvent, autonomousRuns, inboxNotifications } = useShellAutonomousSupervision({
    isAuthenticated: auth.isAuthenticated,
    selectedScope: preliminaryScope,
    workspaces,
    currentUserEmail: auth.email,
  });
  const derived = deriveShellScopeAndBreadcrumbs({
    pathname,
    locale,
    auth,
    setup,
    activeScopeId: state.activeScopeId,
    selectedModuleOverride: state.selectedModuleOverride,
    selectedMenuKeyOverride: state.selectedMenuKeyOverride,
    dictionary,
    autonomousRuns,
    inboxNotifications,
    lastClaimEvent,
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

  if (!isShowcaseStandalone && (auth.isHydrating || (isInitialLoading && !auth.isAuthenticated))) {
    return <ShellHydratingLoaderView isFr={isFr} />;
  }
  if (!isShowcaseStandalone && !auth.isAuthenticated && !isAdminModalOpen) {
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
        activeModuleKey: derived.safeModuleKey,
        activeMenuKey: derived.activeMenuKey,
        activeScopeId: derived.selectedScope.id,
        setActiveScopeId: state.setActiveScopeId,
        helpColumnOpen: state.helpColumnOpen,
        activeHelpSectionId: state.activeHelpSectionId,
        disabledMenuKeys: derived.disabledMenuKeys,
        navigateToRoute: dispatchNavigation,
        openHelpSection: (sectionId) => {
          state.setHelpColumnOpen(true);
          state.setActiveHelpSectionId(sectionId);
        },
      }}
    >
      <FourZoneDirectionCShell
        activeMenuKey={derived.activeMenuKey}
        breadcrumbItems={derived.breadcrumbItems}
        onNavigateBreadcrumb={dispatchNavigation}
        activeWorkspaceName={derived.activeWorkspaceName}
        activeScopeId={derived.selectedScope.id}
        workspaceOptions={derived.workspaceOptions}
        unifiedScopeGroups={derived.unifiedScopeState.groups}
        unifiedAllSpacesOption={derived.unifiedScopeState.allSpacesOption}
        unifiedScopeLabel={derived.unifiedScopeState.scopeLabel}
        activeUnifiedScopeId={derived.unifiedScopeState.activeScopeValue}
        onSelectUnifiedScope={state.setActiveScopeId}
        onNavigateHome={() => selectModuleAndNavigate("cockpit", "cockpit", "/cockpit")}
        onSelectWorkspace={state.setActiveScopeId}
        isDesktopOnlyRoute={isDesktopOnlyMobileRoute(pathname)}
        activeMobileBottomTab={resolveActiveMobileBottomTab(pathname)}
        onSelectMobileBottomTab={(tab) => {
          if (tab === "cockpit") selectModuleAndNavigate("cockpit", "cockpit", "/cockpit");
          else if (tab === "assistant" && !derived.disabledMenuKeys.assistant)
            selectModuleAndNavigate("assistant", "inbox", "/assistant");
          else if (tab === "decisions") selectModuleAndNavigate("cockpit", "inbox", "/inbox");
        }}
        activePackKey=""
        availablePacks={[]}
        userDisplayName={derived.effectiveDisplayName}
        userHatLabel={derived.userHatLabel}
        pendingDecisionsTotal={derived.hasAuthenticatedIdentity ? runs.length : 0}
        notifications={derived.notificationItems}
        onSelectNotification={(item) => {
          if (item.targetRoute === "#change-password") auth.openUserSettingsModalAtTab("ACCOUNT_SECURITY");
          else if (item.targetRoute) dispatchNavigation(item.targetRoute);
        }}
        labels={dictionary.fourZoneShell}
        viewportWidth={state.viewportWidth}
        disabledMenuKeys={derived.disabledMenuKeys}
        hiddenMenuKeys={derived.showConfigurationMenu ? [] : ["configuration"]}
        helpColumnOpen={isHelpCenterRoute ? false : state.helpColumnOpen}
        helpColumnToggleDisabled={isHelpCenterRoute}
        mobileDrawerCloseSignal={`${pathname ?? ""}:${String(auth.userSettingsModalOpen)}`}
        onHelpColumnOpenChange={(nextOpen) => !isHelpCenterRoute && state.setHelpColumnOpen(nextOpen)}
        onSelectMenu={(menuKey) => {
          const mapped = mapEightMenuKeyToModule(menuKey);
          selectModuleAndNavigate(menuKey, mapped.moduleKey, mapped.route);
        }}
        onSelectActivityMenu={(route) => selectModuleAndNavigate("finops", "finops", route)}
        onOpenWorkspaceSwitcher={() => undefined}
        onOpenSearchCommand={() => state.setSearchModalOpen(true)}
        renderSidebarFooter={renderShellSidebarFooter({
          hasAuthenticatedIdentity: derived.hasAuthenticatedIdentity,
          hideSidebarShowcaseBtn,
          pathname,
          effectiveDisplayName: derived.effectiveDisplayName,
          effectiveEmail: derived.effectiveEmail,
          userRole: auth.roles[0] ?? "CONTRIBUTOR",
          userHatLabel: derived.userHatLabel,
          locale,
          dictionary,
          onLocaleChange: setLocale,
          onDispatchNavigation: dispatchNavigation,
          onLogout: () => {
            clearSavedActiveScopeId();
            void auth.logoutSession().then(() => dispatchNavigation("/login"));
          },
          onOpenShowcase: () => selectModuleAndNavigate("help", "ontology", "/showcase"),
        })}
        helpColumnContent={renderShellZone4HelpColumn({
          isHelpCenterRoute, pathname, locale,
          activeMenuKey: derived.activeMenuKey,
          safeModuleKey: derived.safeModuleKey,
          activeHelpSectionId: state.activeHelpSectionId,
          assistantDisabled: Boolean(derived.disabledMenuKeys.assistant),
          dictionary, hasOnNavigateProp: Boolean(onNavigate),
          onSelectModuleAndNavigate: selectModuleAndNavigate,
          onDispatchNavigation: dispatchNavigation,
        })}
      >
        <ShellCentralWorkspaceBody
          lastSyncError={setup.lastSyncError}
          mustChangePassword={auth.mustChangePassword}
          isFr={isFr}
          onOpenAccountSecurity={() => auth.openUserSettingsModalAtTab("ACCOUNT_SECURITY")}
        >
          {children}
        </ShellCentralWorkspaceBody>
      </FourZoneDirectionCShell>

      <ShellContainerModals
        isFr={isFr} isAdminModalOpen={isAdminModalOpen} searchModalOpen={state.searchModalOpen}
        pathname={pathname} activeScopeId={derived.selectedScope.id} workspaces={workspaces}
        catalogItems={catalogItems} ontologyConcepts={ontologyConcepts}
        labels={dictionary.topHeaderSearch} disabledMenuKeys={derived.disabledMenuKeys}
        onDismissAdminModal={() => state.setAdminModalDismissed(true)}
        onCreatePlatformAdmin={createPlatformAdmin}
        onCloseSearchModal={() => state.setSearchModalOpen(false)}
        onDispatchNavigation={dispatchNavigation}
        onOpenAssistantFromSearch={(query) => {
          if (query.trim()) writeAssistantPrefillPrompt(query.trim());
          if (onNavigate) selectModuleAndNavigate("assistant", "inbox", "/assistant");
          else dispatchNavigation("/assistant");
        }}
      />
      {auth.isAuthenticated && (
        <ShellUserSettingsModal
          userEmail={derived.effectiveEmail} userRole={auth.roles[0] ?? "CONTRIBUTOR"} locale={locale}
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
