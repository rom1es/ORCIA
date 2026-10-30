import {
  AppShell,
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
  resolveModuleFromPathname,
} from "./shellPresets";

export {
  DEFAULT_HUMAN_PROFILE,
  DEFAULT_SHELL_MODULES,
  EMPTY_DEFAULT_SCOPES,
  evaluateScopeModuleVisibility,
  resolveModuleFromPathname,
};

export interface ShellNavigationContextValue {
  readonly activeModuleKey: UiModuleKey;
  readonly activeScopeId: string;
  readonly navigateToRoute: (href: string) => void;
}

const ShellNavigationContext = createContext<ShellNavigationContextValue>({
  activeModuleKey: "cockpit",
  activeScopeId: "scope-global",
  navigateToRoute: () => undefined,
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
  const { locale, dictionary, toggleLocale } = useI18n();
  const { pathname, navigateTo } = useOrciaNavigation();
  const { scopes, workspaces } = usePlatformSetup();
  const [activeScopeId, setActiveScopeId] = useState("scope-global");
  const [selectedModuleOverride, setSelectedModuleOverride] = useState<UiModuleKey | null>(null);

  useEffect(() => {
    setSelectedModuleOverride(null);
  }, [pathname]);

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

  const dispatchNavigation = (href: string) => {
    if (onNavigate) {
      onNavigate(href);
    } else {
      navigateTo(href);
    }
  };

  return (
    <ShellNavigationContext.Provider
      value={{
        activeModuleKey: safeModuleKey,
        activeScopeId: selectedScope.id,
        navigateToRoute: dispatchNavigation,
      }}
    >
      <AppShell
        modules={effectiveModules}
        activeModuleKey={safeModuleKey}
        scopes={[...scopes]}
        activeScopeId={selectedScope.id}
        humanProfile={effectiveProfile}
        labels={dictionary.shell}
        currentLocale={locale}
        permissionBrokerTicket={null}
        permissionBrokerLabels={dictionary.permissionBroker}
        onSelectModule={(moduleKey, route) => {
          setSelectedModuleOverride(moduleKey);
          dispatchNavigation(route);
        }}
        onSelectScope={(nextScopeId) => setActiveScopeId(nextScopeId)}
        onToggleLocale={toggleLocale}
      >
        {children}
      </AppShell>
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
