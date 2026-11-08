import { createOrciaApiClient } from "@orcia/api-client";
import {
  ContextualHelpColumnAndCenter,
  FourZoneDirectionCShell,
  OrciaIcon,
  TopHeaderSearchCommand,
  UserAccountDropdownAndSettingsModal,
  computeDefaultHelpColumnOpen,
  type EightFixedMenuKey,
  type TopSearchFamilyKey,
  type TopSearchHitItem,
  type TopSearchScopeMode,
  type UiHumanProfileBadge,
  type UiModuleKey,
} from "@orcia/ui";
import React, { createContext, useContext, useEffect, useState } from "react";
import { useI18n } from "../i18n";
import { buildContextualHelpArticle } from "./contextualHelpCatalog";
import { FirstBootAdminSetupModal } from "./FirstBootAdminSetupModal";
import { useOrciaNavigation } from "./navigationAdapter";
import { PlatformSetupProvider, usePlatformSetup } from "./platformSetupStore";
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

function mapBackendSearchFamily(rawFamily: string): TopSearchFamilyKey {
  if (rawFamily === "AGENTS_SKILLS") return "AGENTS_TOOLS";
  if (rawFamily === "GLOSSARY_RULES") return "ONTOLOGY_GLOSSARY";
  if (
    rawFamily === "FOLDERS_DISCUSSIONS" ||
    rawFamily === "PROCESSES_EXECUTIONS" ||
    rawFamily === "AGENTS_TOOLS" ||
    rawFamily === "DELIVERABLES_ARTIFACTS" ||
    rawFamily === "SOURCES_SNIPPETS" ||
    rawFamily === "ONTOLOGY_GLOSSARY" ||
    rawFamily === "HELP_ACTIONS"
  ) {
    return rawFamily;
  }
  return "SOURCES_SNIPPETS";
}

function InnerShellContainer({
  children,
  onNavigate,
}: {
  children: React.ReactNode;
  onNavigate?: (href: string) => void;
}) {
  const { locale, dictionary, toggleLocale } = useI18n();
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
  const [activeScopeId, setActiveScopeId] = useState("scope-global");
  const [selectedModuleOverride, setSelectedModuleOverride] = useState<UiModuleKey | null>(null);
  const [selectedMenuKeyOverride, setSelectedMenuKeyOverride] =
    useState<EightFixedMenuKey | null>(null);
  const [searchModalOpen, setSearchModalOpen] = useState<boolean>(false);
  const [speed2Hits, setSpeed2Hits] = useState<readonly TopSearchHitItem[]>([]);
  const [speed2Loading, setSpeed2Loading] = useState<boolean>(false);
  const [speed2Executed, setSpeed2Executed] = useState<boolean>(false);
  const [speed2Error, setSpeed2Error] = useState<string | null>(null);
  const [helpColumnOpen, setHelpColumnOpen] = useState<boolean>(() =>
    computeDefaultHelpColumnOpen(1440, runs.length),
  );
  const [activeHelpSectionId, setActiveHelpSectionId] = useState<string | null>(null);
  const [adminModalDismissed, setAdminModalDismissed] = useState<boolean>(false);

  const isFr = locale === "fr";

  const runFederatedSpeed2Search = (
    query: string,
    requestedScope: TopSearchScopeMode = "ALL_WORKSPACES",
  ) => {
    const trimmed = query.trim();
    if (!trimmed) {
      setSpeed2Hits([]);
      setSpeed2Loading(false);
      setSpeed2Executed(false);
      setSpeed2Error(null);
      return;
    }
    setSpeed2Loading(true);
    setSpeed2Executed(false);
    setSpeed2Error(null);
    const activeWsId = workspaces[0]?.workspaceId ?? null;
    const effectiveScope: TopSearchScopeMode =
      activeWsId === null && requestedScope === "WORKSPACE" ? "ALL_WORKSPACES" : requestedScope;
    const client = createOrciaApiClient({ baseUrl: "" });
    void client
      .searchFederated(trimmed, effectiveScope, activeWsId, pathname ?? "/cockpit", true)
      .then((res) => {
        setSpeed2Loading(false);
        setSpeed2Executed(Boolean(res.speed2_executed ?? true));
        const mapped = (res.hits ?? []).map(
          (hit): TopSearchHitItem => ({
            itemId: hit.item_id,
            family: mapBackendSearchFamily(String(hit.family ?? "")),
            title: hit.title,
            snippet: hit.snippet,
            workspaceId: hit.workspace_id,
            screenRoute: hit.screen_route,
            deepLinkUri: hit.deep_link_uri,
            speedTier: 2,
            lockedTop: false,
            score: Number(hit.score ?? 0.85),
            badge: hit.badge ?? "✨ Passage proche",
            highlightDurationMs: Number(hit.highlight_duration_ms ?? 2000),
            opensContextualHelpColumn: Boolean(hit.opens_contextual_help_column),
          }),
        );
        setSpeed2Hits(mapped);
      })
      .catch((err: unknown) => {
        setSpeed2Loading(false);
        setSpeed2Executed(false);
        setSpeed2Hits([]);
        const detail = err instanceof Error ? err.message : String(err);
        setSpeed2Error(
          isFr
            ? `Erreur lors de la recherche fédérée (Vitesse 2) : ${detail}`
            : `Federated search error (Speed 2): ${detail}`,
        );
      });
  };

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
    displayName: platformAdmin?.displayName ?? DEFAULT_HUMAN_PROFILE.displayName,
    accessMode: selectedScope.accessMode,
  };

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
        userHatLabel="Administrateur de la plateforme"
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
        sidebarSecondarySlot={
          pathname?.startsWith("/help") || pathname?.startsWith("/ontology") ? null : (
            <button
              type="button"
              data-testid="open-orcia-showcase-site-btn"
              onClick={() => {
                setSelectedMenuKeyOverride("help");
                setSelectedModuleOverride("ontology");
                dispatchNavigation("/showcase");
              }}
              className="mt-1 flex items-center gap-2 rounded border px-2.5 py-1.5 text-left text-[11px] font-semibold"
              style={{
                backgroundColor: pathname?.startsWith("/showcase")
                  ? "var(--color-action-primary-subtle)"
                  : "var(--color-bg-elevated)",
                borderColor: "var(--color-border-subtle)",
                color: pathname?.startsWith("/showcase")
                  ? "var(--color-action-primary)"
                  : "var(--color-text-primary)",
                cursor: "pointer",
              }}
            >
              <OrciaIcon name="globe" />
              <span>Documentation</span>
            </button>
          )
        }
        headerUserControl={
          <UserAccountDropdownAndSettingsModal
            userDisplayName={effectiveProfile.displayName}
            userEmail={platformAdmin?.email ?? ""}
            userRole={effectiveProfile.role ?? "PLATFORM_ADMIN"}
            initialLocale={locale}
            labels={dictionary.userAccountAndSettings}
            onPreferencesSync={(patch) => {
              if (patch.locale && patch.locale !== locale) {
                toggleLocale();
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

      {searchModalOpen && (
        <div
          data-testid="cmdk-modal-backdrop"
          className="fixed inset-0 z-40 flex items-center justify-center p-4"
          style={{ backgroundColor: "rgba(15, 23, 42, 0.35)" }}
        >
          <TopHeaderSearchCommand
            labels={dictionary.topHeaderSearch}
            speed1Hits={[
              ...workspaces.map((ws): TopSearchHitItem => ({
                itemId: ws.workspaceId,
                family: "FOLDERS_DISCUSSIONS",
                title: ws.name,
                snippet: ws.lifecyclePhase,
                workspaceId: ws.workspaceId,
                screenRoute: "/workspaces",
                deepLinkUri: "/workspaces",
                speedTier: 1,
                lockedTop: true,
                score: 0.99,
                badge: null,
                highlightDurationMs: 2000,
                opensContextualHelpColumn: false,
              })),
              ...catalogItems.map((cat): TopSearchHitItem => ({
                itemId: cat.resourceId,
                family: "PROCESSES_EXECUTIONS",
                title: cat.title,
                snippet: cat.uri,
                workspaceId: activeScopeId,
                screenRoute: "/catalog",
                deepLinkUri: "/catalog",
                speedTier: 1,
                lockedTop: true,
                score: 0.95,
                badge: null,
                highlightDurationMs: 2000,
                opensContextualHelpColumn: false,
              })),
              ...ontologyConcepts.map((c): TopSearchHitItem => ({
                itemId: c.conceptKey,
                family: "ONTOLOGY_GLOSSARY",
                title: c.canonicalTerm,
                snippet: c.definitionText,
                workspaceId: activeScopeId,
                screenRoute: "/workspaces",
                deepLinkUri: "/workspaces",
                speedTier: 1,
                lockedTop: true,
                score: 0.92,
                badge: null,
                highlightDurationMs: 2000,
                opensContextualHelpColumn: false,
              })),
            ]}
            speed2Hits={speed2Hits}
            speed2Loading={speed2Loading}
            speed2Executed={speed2Executed}
            speed2Error={speed2Error}
            onQueryChange={(query) => {
              if (!query.trim()) {
                setSpeed2Hits([]);
                setSpeed2Loading(false);
                setSpeed2Executed(false);
                setSpeed2Error(null);
              }
            }}
            onTriggerSpeed2Now={(query, scope) => runFederatedSpeed2Search(query, scope)}
            onSelectDeepLink={(payload) => {
              setSearchModalOpen(false);
              dispatchNavigation(payload.deepLinkUri);
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
        </div>
      )}
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
