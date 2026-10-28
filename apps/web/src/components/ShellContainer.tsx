import {
  AppShell,
  type UiHumanProfileBadge,
  type UiModuleKey,
  type UiPermissionBrokerTicketView,
  type UiPersonaKey,
  type UiShellModuleItem,
} from "@orcia/ui";
import React, { createContext, useContext, useEffect, useState } from "react";
import { useI18n } from "../i18n";
import { useOrciaNavigation } from "./navigationAdapter";
import {
  DEFAULT_HUMAN_PROFILE,
  DEFAULT_SCOPES,
  DEFAULT_SHELL_MODULES,
  EMPTY_DEFAULT_SCOPES,
  evaluateScopeModuleVisibility,
  PERSONA_PROFILES,
  resolveModuleFromPathname,
} from "./shellPresets";
import { PERMISSION_BROKER_TICKET_PRESETS } from "./workspaceFixtures";

export {
  DEFAULT_HUMAN_PROFILE,
  DEFAULT_SCOPES,
  DEFAULT_SHELL_MODULES,
  EMPTY_DEFAULT_SCOPES,
  evaluateScopeModuleVisibility,
  PERSONA_PROFILES,
  resolveModuleFromPathname,
};

export interface PersonaContextValue {
  fixtureMode: boolean;
  activeModuleKey: UiModuleKey;
  activePersona: UiPersonaKey;
  setActivePersona: (persona: UiPersonaKey) => void;
  activeBrokerTicket: UiPermissionBrokerTicketView | null;
  brokerActionBanner: string | null;
  triggerPermissionDeniedStep: (presetKey: "git" | "confluence" | "jira") => void;
  triggerConfusedDeputyCheck: () => void;
  pauseBrokerStep: (ticketId: string) => void;
  replayBrokerStep: (ticketId: string) => void;
}

const PersonaContext = createContext<PersonaContextValue>({
  fixtureMode: false,
  activeModuleKey: "cockpit",
  activePersona: "marc",
  setActivePersona: () => undefined,
  activeBrokerTicket: null,
  brokerActionBanner: null,
  triggerPermissionDeniedStep: () => undefined,
  triggerConfusedDeputyCheck: () => undefined,
  pauseBrokerStep: () => undefined,
  replayBrokerStep: () => undefined,
});

export function usePersonaContext(): PersonaContextValue {
  return useContext(PersonaContext);
}

export function ShellContainer({
  children,
  fixtureMode = false,
  onNavigate,
}: {
  children: React.ReactNode;
  fixtureMode?: boolean;
  onNavigate?: (href: string) => void;
}) {
  const { locale, dictionary, toggleLocale } = useI18n();
  const { pathname, navigateTo } = useOrciaNavigation();
  const [urlFixtureFlag, setUrlFixtureFlag] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("fixture") === "test") {
        setUrlFixtureFlag(true);
      }
    }
  }, [pathname]);

  const isFixtureMode = fixtureMode || urlFixtureFlag;
  const activeScopes = isFixtureMode ? DEFAULT_SCOPES : EMPTY_DEFAULT_SCOPES;
  const [activeScopeId, setActiveScopeId] = useState(
    isFixtureMode ? "scope-ws-orcia" : "scope-global",
  );
  const [activePersona, setActivePersona] = useState<UiPersonaKey>("marc");
  const [selectedModuleOverride, setSelectedModuleOverride] = useState<UiModuleKey | null>(null);
  const [activeBrokerTicket, setActiveBrokerTicket] =
    useState<UiPermissionBrokerTicketView | null>(
      isFixtureMode ? PERMISSION_BROKER_TICKET_PRESETS.git : null,
    );
  const [brokerSequence, setBrokerSequence] = useState(1);
  const [brokerActionBanner, setBrokerActionBanner] = useState<string | null>(null);

  useEffect(() => {
    if (isFixtureMode) {
      setActiveScopeId("scope-ws-orcia");
      setActiveBrokerTicket((prev) => prev ?? PERMISSION_BROKER_TICKET_PRESETS.git);
    }
  }, [isFixtureMode]);

  useEffect(() => {
    setSelectedModuleOverride(null);
  }, [pathname]);

  const activeModuleKey = selectedModuleOverride ?? resolveModuleFromPathname(pathname);
  const selectedScope =
    activeScopes.find((s) => s.id === activeScopeId) ?? activeScopes[activeScopes.length - 1]!;
  const personaMeta = isFixtureMode ? PERSONA_PROFILES[activePersona] : null;

  const effectiveProfile: UiHumanProfileBadge = personaMeta
    ? {
        archetypeKey: personaMeta.archetypeKey,
        displayName: personaMeta.displayName,
        role: personaMeta.role,
        orgUnitName: personaMeta.orgUnitName,
        accessMode:
          personaMeta.accessMode === "READ_ONLY_OBSERVER"
            ? "READ_ONLY_OBSERVER"
            : selectedScope.accessMode,
      }
    : {
        ...DEFAULT_HUMAN_PROFILE,
        accessMode: selectedScope.accessMode,
      };

  const visibilityMap = evaluateScopeModuleVisibility(
    effectiveProfile.role ?? "TEAM_LEAD",
    selectedScope.level,
    isFixtureMode,
  );

  const effectiveModules: UiShellModuleItem[] = DEFAULT_SHELL_MODULES.map((mod) => ({
    ...mod,
    contributorBadgeCount: isFixtureMode ? mod.contributorBadgeCount : 0,
    hasStaleWarning: isFixtureMode ? mod.hasStaleWarning : false,
    enabled: visibilityMap[mod.key],
  }));

  const safeModuleKey: UiModuleKey = !visibilityMap[activeModuleKey]
    ? "cockpit"
    : activeModuleKey;

  function triggerPermissionDeniedStep(presetKey: "git" | "confluence" | "jira") {
    const preset = PERMISSION_BROKER_TICKET_PRESETS[presetKey];
    const nextSeq = brokerSequence + 1;
    setBrokerSequence(nextSeq);
    setActiveBrokerTicket({
      ...preset,
      id: `${preset.id}-evt-${nextSeq}`,
      stepState: "PERMISSION_DENIED_STEP",
      status: "WAITING_FOR_PERMISSION",
    });
    setBrokerActionBanner(
      `HTTP 403 ERR_PERMISSION_BROKER_INTERCEPTED — ${preset.permissionBrokerHint}`,
    );
  }

  function triggerConfusedDeputyCheck() {
    setBrokerActionBanner(dictionary.permissionBroker.confusedDeputyBlockedBanner);
  }

  function pauseBrokerStep(_ticketId: string) {
    if (effectiveProfile.accessMode === "READ_ONLY_OBSERVER") {
      setBrokerActionBanner(dictionary.permissionBroker.observerDeniedBanner);
      return;
    }
    setActiveBrokerTicket((prev) =>
      prev ? { ...prev, stepState: "PAUSED", status: "PAUSED" } : prev,
    );
    setBrokerActionBanner(dictionary.permissionBroker.pausedStateBanner);
  }

  function replayBrokerStep(_ticketId: string) {
    if (effectiveProfile.accessMode === "READ_ONLY_OBSERVER") {
      setBrokerActionBanner(dictionary.permissionBroker.observerDeniedBanner);
      return;
    }
    setActiveBrokerTicket((prev) =>
      prev ? { ...prev, stepState: "REPLAYED", status: "REPLAYED" } : prev,
    );
    setBrokerActionBanner(dictionary.permissionBroker.replayedStateBanner);
  }

  return (
    <PersonaContext.Provider
      value={{
        fixtureMode: isFixtureMode,
        activeModuleKey: safeModuleKey,
        activePersona,
        setActivePersona,
        activeBrokerTicket,
        brokerActionBanner,
        triggerPermissionDeniedStep,
        triggerConfusedDeputyCheck,
        pauseBrokerStep,
        replayBrokerStep,
      }}
    >
      <AppShell
        modules={effectiveModules}
        activeModuleKey={safeModuleKey}
        scopes={activeScopes}
        activeScopeId={selectedScope.id}
        humanProfile={effectiveProfile}
        labels={dictionary.shell}
        currentLocale={locale}
        permissionBrokerTicket={activeBrokerTicket}
        permissionBrokerLabels={dictionary.permissionBroker}
        onSelectModule={(moduleKey, route) => {
          setSelectedModuleOverride(moduleKey);
          const targetHref =
            urlFixtureFlag && !route.includes("?") ? `${route}?fixture=test` : route;
          if (onNavigate) {
            onNavigate(targetHref);
          } else {
            navigateTo(targetHref);
          }
        }}
        onSelectScope={(nextScopeId) => setActiveScopeId(nextScopeId)}
        onToggleLocale={toggleLocale}
        onPausePermissionStep={pauseBrokerStep}
        onReplayPermissionStep={replayBrokerStep}
      >
        {children}
      </AppShell>
    </PersonaContext.Provider>
  );
}
