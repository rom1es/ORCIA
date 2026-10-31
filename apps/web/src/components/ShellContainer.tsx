import {
  ContextualHelpColumnAndCenter,
  FourZoneDirectionCShell,
  TopHeaderSearchCommand,
  UserAccountDropdownAndSettingsModal,
  type EightFixedMenuKey,
  type TopSearchHitItem,
  type UiContextualHelpArticleView,
  type UiHumanProfileBadge,
  type UiModuleKey,
  type UiShellModuleItem,
} from "@orcia/ui";
import React, { createContext, useContext, useEffect, useState } from "react";
import { useI18n } from "../i18n";
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
  readonly navigateToRoute: (href: string) => void;
}

const ShellNavigationContext = createContext<ShellNavigationContextValue>({
  activeModuleKey: "cockpit",
  activeMenuKey: "cockpit",
  activeScopeId: "scope-global",
  navigateToRoute: () => undefined,
});

export function useShellNavigation(): ShellNavigationContextValue {
  return useContext(ShellNavigationContext);
}

const DEFAULT_SEARCH_HITS: readonly TopSearchHitItem[] = [
  {
    itemId: "hit-cockpit",
    family: "HELP_ACTIONS",
    title: "Cockpit & Décisions Prioritaires",
    snippet: "Pilotez vos arbitrages Tie-Break, ancrages humains et revues 4 blocs.",
    workspaceId: "scope-global",
    screenRoute: "/cockpit",
    deepLinkUri: "/cockpit",
    speedTier: 1,
    lockedTop: true,
    score: 0.99,
    badge: null,
    highlightDurationMs: 2000,
    opensContextualHelpColumn: false,
  },
  {
    itemId: "hit-assistant",
    family: "FOLDERS_DISCUSSIONS",
    title: "Mon Assistant (3 Vitesses & Citations [S1])",
    snippet: "Interrogez vos sources avec citations déterministes [S1] / [G1] / [O1].",
    workspaceId: "scope-global",
    screenRoute: "/assistant",
    deepLinkUri: "/assistant",
    speedTier: 1,
    lockedTop: true,
    score: 0.96,
    badge: null,
    highlightDurationMs: 2000,
    opensContextualHelpColumn: false,
  },
  {
    itemId: "hit-spaces",
    family: "ONTOLOGY_GLOSSARY",
    title: "Mes Espaces (5 Sous-Onglets & Chaîne ADN Starlark)",
    snippet: "Gérez vos sources, livrables, dérogations V1 et règles métiers Starlark.",
    workspaceId: "scope-global",
    screenRoute: "/workspaces",
    deepLinkUri: "/workspaces",
    speedTier: 1,
    lockedTop: true,
    score: 0.94,
    badge: null,
    highlightDurationMs: 2000,
    opensContextualHelpColumn: false,
  },
];

function InnerShellContainer({
  children,
  onNavigate,
}: {
  children: React.ReactNode;
  onNavigate?: (href: string) => void;
}) {
  const { locale, dictionary, toggleLocale } = useI18n();
  const { pathname, navigateTo } = useOrciaNavigation();
  const { scopes, workspaces, runs, packs } = usePlatformSetup();
  const [activeScopeId, setActiveScopeId] = useState("scope-global");
  const [selectedModuleOverride, setSelectedModuleOverride] = useState<UiModuleKey | null>(null);
  const [selectedMenuKeyOverride, setSelectedMenuKeyOverride] =
    useState<EightFixedMenuKey | null>(null);
  const [searchModalOpen, setSearchModalOpen] = useState<boolean>(false);
  const [activePackKey, setActivePackKey] = useState<string>("orcia-pack-sdlc@1.0.0");

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
    accessMode: selectedScope.accessMode,
  };

  const hasWorkspaces = workspaces.length > 0;
  const visibilityMap = evaluateScopeModuleVisibility(
    effectiveProfile.role ?? "PLATFORM_ADMIN",
    selectedScope.level,
    hasWorkspaces,
  );

  const effectiveModules: UiShellModuleItem[] = DEFAULT_SHELL_MODULES.map((mod) => ({
    ...mod,
    contributorBadgeCount: 0,
    hasStaleWarning: false,
    enabled: visibilityMap[mod.key],
  }));

  const safeModuleKey: UiModuleKey = !visibilityMap[activeModuleKey]
    ? "cockpit"
    : activeModuleKey;

  const activeMenuKey: EightFixedMenuKey =
    selectedMenuKeyOverride ?? resolveEightMenuKeyFromModule(safeModuleKey, pathname);

  const dispatchNavigation = (href: string) => {
    if (onNavigate) {
      onNavigate(href);
    } else {
      navigateTo(href);
    }
  };

  const activeWorkspaceName =
    workspaces[0]?.name ?? selectedScope.name ?? "Plateforme Globale ORCIA";

  const availablePackKeys = [
    "orcia-pack-sdlc@1.0.0",
    "orcia-pack-builder@1.0.0",
    ...packs.map((p) => `${p.packKey}@${p.version}`),
  ];

  const contextualHelpArticle: UiContextualHelpArticleView = {
    resourceId: `help-${activeMenuKey}`,
    uri: `orcia://packs/core/help/${activeMenuKey}/${locale}`,
    title: dictionary.fourZoneShell.menuEntries[activeMenuKey],
    version: "1.0.0",
    lang: locale,
    layer: "PACK",
    packName: activePackKey,
    boundRoutes: [pathname ?? "/cockpit"],
    summaryWhatFor: dictionary.modulePages[safeModuleKey].description,
    stepByStepItems: [
      "1. Sélectionnez votre Espace actif dans la barre supérieure (52px).",
      "2. Utilisez la recherche fédérée ⌘K ou Mon Assistant pour interroger vos sources.",
      "3. Validez les décisions en attente ou lancez un processus gouverné.",
    ],
    keyTermsItems: ["Ancrage Humain Violet", "Action Staged (AD-3)", "Chaîne Causale ADN"],
    faqItems: ["Comment personnaliser Mon Assistant ? → Cliquez sur ⚙️ Réglages de l'assistant."],
    casKey: "cas/help_ contextual_v1",
    sha256: "sha256_contextual_help_v1",
    previousVersion: "0.9.0",
  };

  const sidebarModuleShortcuts = (
    <div
      className="mt-2 border-t pt-2 flex flex-col gap-1"
      style={{ borderColor: "var(--color-border-subtle)" }}
    >
      {effectiveModules
        .filter((m) => m.enabled)
        .map((mod) => {
          const isCurrent = mod.key === safeModuleKey;
          return (
            <button
              key={mod.key}
              type="button"
              data-testid={`sidebar-nav-item-${mod.key}`}
              aria-current={isCurrent ? "page" : undefined}
              onClick={() => {
                setSelectedModuleOverride(mod.key);
                dispatchNavigation(mod.route);
              }}
              className="flex items-center justify-between rounded px-2 py-1 text-left text-[11px]"
              style={{
                backgroundColor: isCurrent
                  ? "var(--color-action-primary-subtle)"
                  : "transparent",
                color: isCurrent
                  ? "var(--color-action-primary)"
                  : "var(--color-text-secondary)",
              }}
            >
              <span>{dictionary.shell.modules[mod.key]}</span>
            </button>
          );
        })}
    </div>
  );

  return (
    <ShellNavigationContext.Provider
      value={{
        activeModuleKey: safeModuleKey,
        activeMenuKey,
        activeScopeId: selectedScope.id,
        navigateToRoute: dispatchNavigation,
      }}
    >
      <FourZoneDirectionCShell
        activeMenuKey={activeMenuKey}
        activeWorkspaceName={activeWorkspaceName}
        activePackKey={activePackKey}
        availablePacks={Array.from(new Set(availablePackKeys))}
        userDisplayName={effectiveProfile.displayName}
        userHatLabel={effectiveProfile.archetypeKey}
        pendingDecisionsTotal={runs.length}
        labels={dictionary.fourZoneShell}
        onSelectMenu={(menuKey) => {
          const mapped = mapEightMenuKeyToModule(menuKey);
          setSelectedMenuKeyOverride(menuKey);
          setSelectedModuleOverride(mapped.moduleKey);
          dispatchNavigation(mapped.route);
        }}
        onOpenWorkspaceSwitcher={() => {
          const nextIdx =
            (scopes.findIndex((s) => s.id === selectedScope.id) + 1) %
            Math.max(1, scopes.length);
          const nextScope = scopes[nextIdx];
          if (nextScope) {
            setActiveScopeId(nextScope.id);
          }
        }}
        onOpenSearchCommand={() => setSearchModalOpen(true)}
        onSelectPack={(nextPack) => setActivePackKey(nextPack)}
        headerUserControl={
          <div className="flex items-center gap-2">
            <button
              type="button"
              data-testid="shell-locale-toggle"
              onClick={toggleLocale}
              className="rounded border px-2 py-1 text-xs font-medium"
              style={{
                backgroundColor: "var(--color-bg-elevated)",
                borderColor: "var(--color-border-subtle)",
                color: "var(--color-text-primary)",
              }}
            >
              {dictionary.userAccountAndSettings.localeQuickToggleLabel} ({locale.toUpperCase()})
            </button>
            <UserAccountDropdownAndSettingsModal
              userDisplayName={effectiveProfile.displayName}
              userEmail="operateur@orcia.io"
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
          </div>
        }
        sidebarSecondarySlot={sidebarModuleShortcuts}
        helpColumnContent={
          <ContextualHelpColumnAndCenter
            mode="COLUMN_340PX"
            route={pathname ?? "/cockpit"}
            pack={activePackKey}
            redisCacheKey={`help:route:${pathname ?? "/cockpit"}:core:${locale}`}
            mergedLayers={["BASE", "PACK", "WORKSPACE"]}
            article={contextualHelpArticle}
            rollbackAvailable={true}
            isAdmin={true}
            labels={dictionary.contextualHelpHybrid}
            onAskAssistantOnScreen={() => {
              setSelectedMenuKeyOverride("assistant");
              setSelectedModuleOverride("inbox");
              dispatchNavigation("/assistant");
            }}
          />
        }
      >
        {children}
      </FourZoneDirectionCShell>

      {searchModalOpen && (
        <div
          data-testid="cmdk-modal-backdrop"
          className="fixed inset-0 z-40 flex items-center justify-center p-4"
          style={{ backgroundColor: "rgba(15, 23, 42, 0.35)" }}
        >
          <TopHeaderSearchCommand
            labels={dictionary.topHeaderSearch}
            speed1Hits={DEFAULT_SEARCH_HITS}
            onSelectDeepLink={(payload) => {
              setSearchModalOpen(false);
              dispatchNavigation(payload.deepLinkUri);
            }}
            onAskAssistant={() => {
              setSearchModalOpen(false);
              setSelectedMenuKeyOverride("assistant");
              setSelectedModuleOverride("inbox");
              dispatchNavigation("/assistant");
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
