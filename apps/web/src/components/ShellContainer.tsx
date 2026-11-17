import {
  FourZoneDirectionCShell,
  type EightFixedMenuKey,
  type UiHumanProfileBadge,
  type UiModuleKey,
} from "@orcia/ui";
import React, { useEffect, useState } from "react";
import { useI18n } from "../i18n";
import {
  isPlatformAdministratorSession,
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
import { ShellHeaderAccountControl } from "./ShellHeaderAccountControl";
import {
  ShellNavigationContext,
  useShellNavigation,
  type ShellNavigationContextValue,
} from "./shellNavigationContext";
import {
  DEFAULT_HUMAN_PROFILE,
  DEFAULT_SHELL_MODULES,
  EMPTY_DEFAULT_SCOPES,
  evaluateScopeModuleVisibility,
  mapEightMenuKeyToModule,
  resolveEightMenuKeyFromModule,
  resolveModuleFromPathname,
} from "./shellPresets";
import {
  buildShellDisabledMenuKeys,
  buildShellNotificationItems,
  buildWorkspaceSwitcherOptions,
} from "./shellScopeOptions";
import { ShellSidebarFooter } from "./ShellSidebarFooter";
import { TemporaryPasswordWarningBanner } from "./TemporaryPasswordWarningBanner";
import { useShellContainerState } from "./useShellContainerState";

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
    isInitialLoading,
    platformAdmin,
    scopes,
    orgUnits,
    workspaces,
    catalogItems,
    ontologyConcepts,
    llmTiers,
    runs,
    createPlatformAdmin,
  } = setup;

  const {
    isAuthenticated, isHydrating, mustChangePassword, roles, activeHat,
    readOnlyObserver, email: sessionEmail, displayName: sessionDisplayName,
    userSettingsModalOpen, setActiveHat, setUserSettingsModalOpen,
    openUserSettingsModalAtTab, logoutSession, hydrateSession,
  } = useAuthSessionStore();

  const state = useShellContainerState(runs.length, pathname);
  const isFr = locale === "fr";

  const dispatchNavigation = (href: string) => {
    if (onNavigate) {
      onNavigate(href);
    } else {
      navigateTo(href);
    }
  };

  useEffect(() => {
    if (isHydrating) {
      void hydrateSession();
    }
  }, [isHydrating, hydrateSession]);

  const isAdminModalOpen = platformAdmin === null && !state.adminModalDismissed;
  const isShowcaseStandalone = Boolean(pathname?.startsWith("/showcase"));

  useEffect(() => {
    if (
      !isHydrating &&
      !(isInitialLoading && !isAuthenticated) &&
      !isAuthenticated &&
      !isAdminModalOpen &&
      !isShowcaseStandalone &&
      pathname !== "/login"
    ) {
      dispatchNavigation("/login");
    }
  }, [
    isHydrating,
    isInitialLoading,
    isAuthenticated,
    isAdminModalOpen,
    isShowcaseStandalone,
    pathname,
  ]);

  useEffect(() => {
    if (isAuthenticated && pathname === "/login") {
      dispatchNavigation("/");
    }
  }, [isAuthenticated, pathname]);

  const isPlatformAdmin = isPlatformAdministratorSession({
    roles,
    activeHat,
    readOnlyObserver,
  });

  const activeModuleKey = state.selectedModuleOverride ?? resolveModuleFromPathname(pathname);
  const selectedScope =
    scopes.find((s) => s.id === state.activeScopeId) ?? scopes[0] ?? EMPTY_DEFAULT_SCOPES[0]!;

  const effectiveProfile: UiHumanProfileBadge = {
    ...DEFAULT_HUMAN_PROFILE,
    displayName: sessionDisplayName ?? (isAuthenticated ? platformAdmin?.displayName : DEFAULT_HUMAN_PROFILE.displayName) ?? DEFAULT_HUMAN_PROFILE.displayName,
    role: activeHat || roles[0] || "CONTRIBUTOR",
    accessMode: selectedScope.accessMode,
  };

  const userHatLabel = resolveSessionHatLabel(
    { roles, activeHat, readOnlyObserver },
    locale,
  );

  const safeModuleKey: UiModuleKey = activeModuleKey;
  const activeMenuKey: EightFixedMenuKey =
    state.selectedMenuKeyOverride ?? resolveEightMenuKeyFromModule(safeModuleKey, pathname);

  const openHelpSection = (sectionId: string) => {
    state.setHelpColumnOpen(true);
    state.setActiveHelpSectionId(sectionId);
  };

  const activeWorkspaceName =
    selectedScope.name ?? workspaces[0]?.name ?? "Plateforme Globale ORCIA";
  const { lastClaimEvent, autonomousRuns } = useShellAutonomousSupervision({
    isAuthenticated,
    selectedScope,
    workspaces,
  });

  const workspaceOptions = buildWorkspaceSwitcherOptions({
    isFr,
    orgUnits,
    workspaces,
    scopes,
  });

  const disabledMenuKeys = buildShellDisabledMenuKeys({
    isFr,
    llmTiers,
    workspaces,
  });

  const notificationItems = buildShellNotificationItems({
    isFr,
    platformAdmin,
    orgUnits,
    workspaces,
    llmTiers,
    runs,
    autonomousRuns,
    lastClaimEvent,
    mustChangePassword,
  });

  const contextualHelpArticle = buildContextualHelpArticle({
    activeMenuKey,
    pathname,
    locale,
    title: dictionary.fourZoneShell.menuEntries[activeMenuKey],
    defaultSummary: dictionary.modulePages[safeModuleKey].description,
  });

  const hideSidebarShowcaseBtn =
    Boolean(pathname?.startsWith("/help")) || Boolean(pathname?.startsWith("/ontology"));

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
        activityMenuActive={Boolean(pathname?.startsWith("/activity"))}
        activeWorkspaceName={activeWorkspaceName}
        activeScopeId={selectedScope.id}
        workspaceOptions={workspaceOptions}
        onSelectWorkspace={(scopeId) => state.setActiveScopeId(scopeId)}
        activePackKey=""
        availablePacks={[]}
        userDisplayName={effectiveProfile.displayName}
        userHatLabel={userHatLabel}
        pendingDecisionsTotal={runs.length}
        notifications={notificationItems}
        onSelectNotification={(item) => {
          if (item.targetRoute === "#change-password") {
            openUserSettingsModalAtTab("PROFILE_SECURITY");
            return;
          }
          if (item.targetRoute) {
            dispatchNavigation(item.targetRoute);
          }
        }}
        labels={dictionary.fourZoneShell}
        viewportWidth={state.viewportWidth}
        disabledMenuKeys={disabledMenuKeys}
        hiddenMenuKeys={isPlatformAdmin ? [] : ["configuration"]}
        helpColumnOpen={state.helpColumnOpen}
        onHelpColumnOpenChange={state.setHelpColumnOpen}
        onSelectMenu={(menuKey) => {
          const mapped = mapEightMenuKeyToModule(menuKey);
          state.setSelectedMenuKeyOverride(menuKey);
          state.setSelectedModuleOverride(mapped.moduleKey);
          dispatchNavigation(mapped.route);
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
            userSettingsModalOpen={userSettingsModalOpen}
            hideSidebarShowcaseBtn={hideSidebarShowcaseBtn}
            pathname={pathname}
            labels={dictionary.sidebarFooter}
            onOpenMyAccount={() => setUserSettingsModalOpen(true)}
            onOpenShowcase={() => {
              state.setSelectedMenuKeyOverride("help");
              state.setSelectedModuleOverride("ontology");
              dispatchNavigation("/showcase");
            }}
          />
        )}
        headerUserControl={
          <ShellHeaderAccountControl
            userDisplayName={effectiveProfile.displayName}
            userEmail={sessionEmail ?? (isAuthenticated ? platformAdmin?.email : "") ?? ""}
            userRole={roles[0] ?? "CONTRIBUTOR"}
            activeHat={activeHat}
            locale={locale}
            labels={dictionary.userAccountAndSettings}
            onLocaleChange={(nextLocale) => setLocale(nextLocale)}
            onActiveHatChange={(nextHat) => setActiveHat(nextHat)}
            onNavigateAssistantBehavior={(uri) => dispatchNavigation(uri)}
            onLogout={() => {
              void logoutSession();
              dispatchNavigation("/login");
            }}
          />
        }
        helpColumnContent={
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
        }
      >
        <div className="flex h-full flex-col">
          {mustChangePassword && (
            <TemporaryPasswordWarningBanner
              isFr={isFr}
              onOpenSettings={() => {
                openUserSettingsModalAtTab("PROFILE_SECURITY");
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
