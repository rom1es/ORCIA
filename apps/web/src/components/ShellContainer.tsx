import {
  BiModeLoginView,
  FourZoneDirectionCShell,
  type EightFixedMenuKey,
  type UiHumanProfileBadge,
  type UiModuleKey,
} from "@orcia/ui";
import React from "react";
import { useI18n } from "../i18n";
import {
  resolveSessionHatLabel,
  useAuthSessionStore,
} from "../stores/authSessionStore";
import { buildContextualHelpArticle } from "./contextualHelpCatalog";
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
import { useWorkspaceEventsSse } from "./useWorkspaceEventsSse";

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
  const {
    platformAdmin,
    scopes,
    orgUnits,
    workspaces,
    catalogItems,
    ontologyConcepts,
    llmTiers,
    runs,
    createPlatformAdmin,
  } = usePlatformSetup();

  const isAuthenticated = useAuthSessionStore((s) => s.isAuthenticated);
  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const mustChangePassword = useAuthSessionStore((s) => s.mustChangePassword);
  const roles = useAuthSessionStore((s) => s.roles);
  const activeHat = useAuthSessionStore((s) => s.activeHat);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const sessionEmail = useAuthSessionStore((s) => s.email);
  const sessionDisplayName = useAuthSessionStore((s) => s.displayName);
  const userSettingsModalOpen = useAuthSessionStore((s) => s.userSettingsModalOpen);
  const setActiveHat = useAuthSessionStore((s) => s.setActiveHat);
  const setUserSettingsModalOpen = useAuthSessionStore((s) => s.setUserSettingsModalOpen);
  const openUserSettingsModalAtTab = useAuthSessionStore((s) => s.openUserSettingsModalAtTab);
  const logoutSession = useAuthSessionStore((s) => s.logoutSession);

  const state = useShellContainerState(runs.length, pathname);
  const isFr = locale === "fr";

  const activeModuleKey = state.selectedModuleOverride ?? resolveModuleFromPathname(pathname);
  const selectedScope =
    scopes.find((s) => s.id === state.activeScopeId) ?? scopes[0] ?? EMPTY_DEFAULT_SCOPES[0]!;

  const effectiveProfile: UiHumanProfileBadge = {
    ...DEFAULT_HUMAN_PROFILE,
    displayName:
      sessionDisplayName ??
      (isAuthenticated ? platformAdmin?.displayName : DEFAULT_HUMAN_PROFILE.displayName) ??
      DEFAULT_HUMAN_PROFILE.displayName,
    role: activeHat || roles[0] || "PLATFORM_ADMIN",
    accessMode: selectedScope.accessMode,
  };

  const userHatLabel = resolveSessionHatLabel(
    { roles, activeHat, readOnlyObserver },
    locale,
  );

  const safeModuleKey: UiModuleKey = activeModuleKey;
  const activeMenuKey: EightFixedMenuKey =
    state.selectedMenuKeyOverride ?? resolveEightMenuKeyFromModule(safeModuleKey, pathname);

  const dispatchNavigation = (href: string) => {
    if (onNavigate) {
      onNavigate(href);
    } else {
      navigateTo(href);
    }
  };

  const openHelpSection = (sectionId: string) => {
    state.setHelpColumnOpen(true);
    state.setActiveHelpSectionId(sectionId);
  };

  const activeWorkspaceName =
    selectedScope.name ?? workspaces[0]?.name ?? "Plateforme Globale ORCIA";
  const { lastClaimEvent } = useWorkspaceEventsSse(workspaces[0]?.workspaceId);

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

  const isAdminModalOpen = platformAdmin === null && !state.adminModalDismissed;
  const hideSidebarShowcaseBtn =
    Boolean(pathname?.startsWith("/help")) || Boolean(pathname?.startsWith("/ontology"));

  if (isHydrating) {
    return (
      <div
        data-testid="auth-hydrating-loader"
        className="flex min-h-screen items-center justify-center bg-[var(--color-bg-canvas)] text-[var(--color-text-secondary)]"
      >
        <span className="text-sm font-medium">
          {isFr ? "Chargement de la session..." : "Loading session..."}
        </span>
      </div>
    );
  }

  if (!isAuthenticated && !isAdminModalOpen && pathname !== "/login") {
    return (
      <div
        data-testid="unauthenticated-shell-fallback"
        className="flex min-h-screen flex-col items-center justify-center bg-[var(--color-bg-canvas)] p-6"
      >
        <BiModeLoginView
          labels={dictionary.biModeLogin}
          onTriggerOidcSso={() => dispatchNavigation("/login")}
          onSubmitLocalLogin={() => dispatchNavigation("/login")}
        />
      </div>
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
        disabledMenuKeys={disabledMenuKeys}
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
            userRole={roles[0] ?? "PLATFORM_ADMIN"}
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
