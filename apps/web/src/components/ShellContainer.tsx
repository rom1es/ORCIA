import {
  ContextualHelpColumnAndCenter,
  FourZoneDirectionCShell,
  OrciaIcon,
  UserAccountDropdownAndSettingsModal,
  computeDefaultHelpColumnOpen,
  type EightFixedMenuKey,
  type UiHumanProfileBadge,
  type UiModuleKey,
} from "@orcia/ui";
import React, { createContext, useContext, useEffect, useState } from "react";
import { useI18n } from "../i18n";
import {
  resolveSessionHatLabel,
  useAuthSessionStore,
} from "../stores/authSessionStore";
import { buildContextualHelpArticle } from "./contextualHelpCatalog";
import { FirstBootAdminSetupModal } from "./FirstBootAdminSetupModal";
import { useOrciaNavigation } from "./navigationAdapter";
import { PlatformSetupProvider, usePlatformSetup } from "./platformSetupStore";
import { ShellFederatedSearchModal } from "./ShellFederatedSearchModal";
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
import { useWorkspaceEventsSse } from "./useWorkspaceEventsSse";

export {
  DEFAULT_HUMAN_PROFILE,
  DEFAULT_SHELL_MODULES,
  EMPTY_DEFAULT_SCOPES,
  evaluateScopeModuleVisibility,
  mapEightMenuKeyToModule,
  resolveEightMenuKeyFromModule,
  resolveModuleFromPathname,
};

export interface ShellNavigationContextValue {
  readonly activeModuleKey: UiModuleKey;
  readonly activeMenuKey: EightFixedMenuKey;
  readonly activeScopeId: string;
  readonly helpColumnOpen: boolean;
  readonly activeHelpSectionId: string | null;
  readonly navigateToRoute: (href: string) => void;
  readonly openHelpSection: (sectionId: string) => void;
}

const ShellNavigationContext = createContext<ShellNavigationContextValue>({
  activeModuleKey: "cockpit",
  activeMenuKey: "cockpit",
  activeScopeId: "scope-global",
  helpColumnOpen: true,
  activeHelpSectionId: null,
  navigateToRoute: () => undefined,
  openHelpSection: () => undefined,
});

export function useShellNavigation(): ShellNavigationContextValue {
  return useContext(ShellNavigationContext);
}

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

  const roles = useAuthSessionStore((s) => s.roles);
  const activeHat = useAuthSessionStore((s) => s.activeHat);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const sessionEmail = useAuthSessionStore((s) => s.email);
  const sessionDisplayName = useAuthSessionStore((s) => s.displayName);
  const userSettingsModalOpen = useAuthSessionStore((s) => s.userSettingsModalOpen);
  const setActiveHat = useAuthSessionStore((s) => s.setActiveHat);
  const setUserSettingsModalOpen = useAuthSessionStore((s) => s.setUserSettingsModalOpen);

  const [activeScopeId, setActiveScopeId] = useState("scope-global");
  const [selectedModuleOverride, setSelectedModuleOverride] = useState<UiModuleKey | null>(null);
  const [selectedMenuKeyOverride, setSelectedMenuKeyOverride] =
    useState<EightFixedMenuKey | null>(null);
  const [searchModalOpen, setSearchModalOpen] = useState<boolean>(false);
  const [helpColumnOpen, setHelpColumnOpen] = useState<boolean>(() =>
    computeDefaultHelpColumnOpen(1440, runs.length),
  );
  const [activeHelpSectionId, setActiveHelpSectionId] = useState<string | null>(null);
  const [adminModalDismissed, setAdminModalDismissed] = useState<boolean>(false);

  const isFr = locale === "fr";

  useEffect(() => {
    setSelectedModuleOverride(null);
    setSelectedMenuKeyOverride(null);
  }, [pathname]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchModalOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const activeModuleKey = selectedModuleOverride ?? resolveModuleFromPathname(pathname);
  const selectedScope =
    scopes.find((s) => s.id === activeScopeId) ?? scopes[0] ?? EMPTY_DEFAULT_SCOPES[0]!;

  const effectiveProfile: UiHumanProfileBadge = {
    ...DEFAULT_HUMAN_PROFILE,
    displayName:
      sessionDisplayName ?? platformAdmin?.displayName ?? DEFAULT_HUMAN_PROFILE.displayName,
    role: activeHat || roles[0] || "PLATFORM_ADMIN",
    accessMode: selectedScope.accessMode,
  };

  const userHatLabel = resolveSessionHatLabel(
    { roles, activeHat, readOnlyObserver },
    locale,
  );

  const safeModuleKey: UiModuleKey = activeModuleKey;
  const activeMenuKey: EightFixedMenuKey =
    selectedMenuKeyOverride ?? resolveEightMenuKeyFromModule(safeModuleKey, pathname);

  const dispatchNavigation = (href: string) => {
    if (onNavigate) {
      onNavigate(href);
    } else {
      navigateTo(href);
    }
  };

  const openHelpSection = (sectionId: string) => {
    setHelpColumnOpen(true);
    setActiveHelpSectionId(sectionId);
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
  });

  const contextualHelpArticle = buildContextualHelpArticle({
    activeMenuKey,
    pathname,
    locale,
    title: dictionary.fourZoneShell.menuEntries[activeMenuKey],
    defaultSummary: dictionary.modulePages[safeModuleKey].description,
  });

  const isAdminModalOpen = platformAdmin === null && !adminModalDismissed;
  const hideSidebarShowcaseBtn =
    Boolean(pathname?.startsWith("/help")) || Boolean(pathname?.startsWith("/ontology"));

  return (
    <ShellNavigationContext.Provider
      value={{
        activeModuleKey: safeModuleKey,
        activeMenuKey,
        activeScopeId: selectedScope.id,
        helpColumnOpen,
        activeHelpSectionId,
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
        onSelectWorkspace={(scopeId) => setActiveScopeId(scopeId)}
        activePackKey=""
        availablePacks={[]}
        userDisplayName={effectiveProfile.displayName}
        userHatLabel={userHatLabel}
        pendingDecisionsTotal={runs.length}
        notifications={notificationItems}
        onSelectNotification={(item) => {
          if (item.targetRoute) {
            dispatchNavigation(item.targetRoute);
          }
        }}
        labels={dictionary.fourZoneShell}
        disabledMenuKeys={disabledMenuKeys}
        helpColumnOpen={helpColumnOpen}
        onHelpColumnOpenChange={setHelpColumnOpen}
        onSelectMenu={(menuKey) => {
          const mapped = mapEightMenuKeyToModule(menuKey);
          setSelectedMenuKeyOverride(menuKey);
          setSelectedModuleOverride(mapped.moduleKey);
          dispatchNavigation(mapped.route);
        }}
        onSelectActivityMenu={(route) => {
          setSelectedMenuKeyOverride("finops");
          setSelectedModuleOverride("finops");
          dispatchNavigation(route);
        }}
        onOpenWorkspaceSwitcher={() => undefined}
        onOpenSearchCommand={() => setSearchModalOpen(true)}
        renderSidebarFooter={(railCollapsed) => (
          <>
            <button
              type="button"
              data-testid="sidebar-open-my-account-btn"
              data-active={userSettingsModalOpen ? "true" : "false"}
              aria-label={railCollapsed ? dictionary.sidebarFooter.myAccountLabel : undefined}
              title={railCollapsed ? dictionary.sidebarFooter.myAccountLabel : undefined}
              onClick={() => setUserSettingsModalOpen(true)}
              className={`orcia-sidebar-nav-btn ${railCollapsed ? "justify-center px-0 py-2" : "gap-2.5 px-2.5 py-2"}`}
            >
              <OrciaIcon name="nav.account" />
              {!railCollapsed && (
                <span className="flex-1">{dictionary.sidebarFooter.myAccountLabel}</span>
              )}
            </button>

            {!hideSidebarShowcaseBtn && (
              <button
                type="button"
                data-testid="open-orcia-showcase-site-btn"
                data-active={pathname?.startsWith("/showcase") ? "true" : "false"}
                aria-label={
                  railCollapsed ? dictionary.sidebarFooter.documentationLabel : undefined
                }
                title={railCollapsed ? dictionary.sidebarFooter.documentationLabel : undefined}
                onClick={() => {
                  setSelectedMenuKeyOverride("help");
                  setSelectedModuleOverride("ontology");
                  dispatchNavigation("/showcase");
                }}
                className={`orcia-sidebar-nav-btn ${railCollapsed ? "justify-center px-0 py-2" : "gap-2.5 px-2.5 py-2"}`}
              >
                <OrciaIcon name="bookOpen" />
                {!railCollapsed && (
                  <span className="flex-1">{dictionary.sidebarFooter.documentationLabel}</span>
                )}
              </button>
            )}
          </>
        )}
        headerUserControl={
          <UserAccountDropdownAndSettingsModal
            userDisplayName={effectiveProfile.displayName}
            userEmail={sessionEmail ?? platformAdmin?.email ?? ""}
            userRole={roles[0] ?? "PLATFORM_ADMIN"}
            initialHat={activeHat}
            initialLocale={locale}
            modalOpen={userSettingsModalOpen}
            onModalOpenChange={setUserSettingsModalOpen}
            labels={dictionary.userAccountAndSettings}
            onPreferencesSync={(patch) => {
              if (patch.locale && patch.locale !== locale) {
                setLocale(patch.locale);
              }
              if (patch.defaultHat) {
                setActiveHat(patch.defaultHat);
              }
            }}
            onNavigateAssistantBehavior={(uri) => dispatchNavigation(uri)}
          />
        }
        helpColumnContent={
          <ContextualHelpColumnAndCenter
            mode="COLUMN_340PX"
            route={pathname ?? "/cockpit"}
            pack="orcia-core"
            redisCacheKey={`help:route:${pathname ?? "/cockpit"}:core:${locale}`}
            mergedLayers={["BASE", "PACK", "WORKSPACE"]}
            article={contextualHelpArticle}
            activeSectionId={activeHelpSectionId}
            rollbackAvailable={true}
            isAdmin={true}
            labels={dictionary.contextualHelpHybrid}
            onAskAssistantOnScreen={() => {
              if (!disabledMenuKeys.assistant) {
                setSelectedMenuKeyOverride("assistant");
                setSelectedModuleOverride("inbox");
                dispatchNavigation("/assistant");
              }
            }}
          />
        }
      >
        {children}
      </FourZoneDirectionCShell>

      <FirstBootAdminSetupModal
        isOpen={isAdminModalOpen}
        isFr={isFr}
        onClose={() => setAdminModalDismissed(true)}
        onCreatePlatformAdmin={createPlatformAdmin}
      />

      <ShellFederatedSearchModal
        isOpen={searchModalOpen}
        isFr={isFr}
        pathname={pathname}
        activeScopeId={selectedScope.id}
        workspaces={workspaces}
        catalogItems={catalogItems}
        ontologyConcepts={ontologyConcepts}
        labels={dictionary.topHeaderSearch}
        onSelectDeepLink={(deepLinkUri) => {
          setSearchModalOpen(false);
          dispatchNavigation(deepLinkUri);
        }}
        onAskAssistant={() => {
          setSearchModalOpen(false);
          if (!disabledMenuKeys.assistant) {
            setSelectedMenuKeyOverride("assistant");
            setSelectedModuleOverride("inbox");
            dispatchNavigation("/assistant");
          }
        }}
        onClose={() => setSearchModalOpen(false)}
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
