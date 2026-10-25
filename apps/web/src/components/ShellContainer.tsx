"use client";

import {
  AppShell,
  type UiHumanProfileBadge,
  type UiModuleKey,
  type UiPermissionBrokerTicketView,
  type UiPersonaKey,
  type UiScopeLevel,
  type UiScopeNode,
  type UiShellModuleItem,
} from "@orcia/ui";
import { usePathname, useRouter } from "next/navigation";
import React, { createContext, useContext, useEffect, useState } from "react";
import { useI18n } from "../i18n";
import { PERMISSION_BROKER_TICKET_PRESETS } from "./workspaceFixtures";

export const DEFAULT_SHELL_MODULES: UiShellModuleItem[] = [
  { key: "cockpit", order: 1, route: "/cockpit", icon: "message-square", contributorBadgeCount: 1, hasStaleWarning: false, enabled: true },
  { key: "inbox", order: 2, route: "/inbox", icon: "bell", contributorBadgeCount: 2, hasStaleWarning: false, enabled: true },
  { key: "catalog", order: 3, route: "/catalog", icon: "package", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
  { key: "ontology", order: 4, route: "/ontology", icon: "dna", contributorBadgeCount: 0, hasStaleWarning: true, enabled: true },
  { key: "gates", order: 5, route: "/gates", icon: "shield", contributorBadgeCount: 1, hasStaleWarning: false, enabled: true },
  { key: "finops", order: 6, route: "/finops", icon: "bar-chart", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
  { key: "admin", order: 7, route: "/workspaces", icon: "settings", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
  { key: "bootstrap", order: 8, route: "/bootstrap", icon: "rocket", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
];

export const EMPTY_DEFAULT_SCOPES: UiScopeNode[] = [
  { id: "scope-global", level: "GLOBAL", name: "Plateforme Globale ORCIA", accessMode: "CONTRIBUTOR_ACTION_REQUIRED" },
];

export const DEFAULT_SCOPES: UiScopeNode[] = [
  { id: "scope-global", level: "GLOBAL", name: "Plateforme Globale ORCIA", accessMode: "READ_ONLY_OBSERVER" },
  { id: "scope-bu-digital", level: "BU", name: "BU Produits & Plateformes", parentId: "scope-global", accessMode: "READ_ONLY_OBSERVER" },
  { id: "scope-team-core", level: "TEAM", name: "Équipe Architecture & Agentique", parentId: "scope-bu-digital", accessMode: "CONTRIBUTOR_ACTION_REQUIRED" },
  { id: "scope-ws-orcia", level: "WORKSPACE", name: "Workspace Solution ORCIA Core", parentId: "scope-team-core", accessMode: "CONTRIBUTOR_ACTION_REQUIRED" },
];

export const DEFAULT_HUMAN_PROFILE: UiHumanProfileBadge = {
  archetypeKey: "TECH_LEAD",
  displayName: "Tech Lead / Architecte",
  accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
  role: "TEAM_LEAD",
  orgUnitName: "",
};

export const PERSONA_PROFILES: Record<
  UiPersonaKey,
  UiHumanProfileBadge & { adminEnabled: boolean }
> = {
  karim: {
    archetypeKey: "SECOPS",
    displayName: "Karim (Ingénieur Plateforme)",
    accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
    role: "PLATFORM_ADMIN",
    orgUnitName: "Entreprise ORCIA Group",
    adminEnabled: true,
  },
  claire: {
    archetypeKey: "EXECUTIVE",
    displayName: "Claire (Directrice BU / Équipe Parente)",
    accessMode: "READ_ONLY_OBSERVER",
    role: "BU_DIRECTOR",
    orgUnitName: "BU Digital & Paiements",
    adminEnabled: true,
  },
  marc: {
    archetypeKey: "TECH_LEAD",
    displayName: "Tech Lead / Architecte",
    accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
    role: "TEAM_LEAD",
    orgUnitName: "Sous-Équipe Checkout & Core Solutions",
    adminEnabled: true,
  },
  nadia: {
    archetypeKey: "DEVELOPER",
    displayName: "Nadia (Développeuse Senior)",
    accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
    role: "CONTRIBUTOR",
    orgUnitName: "Sous-Équipe Checkout & Core Solutions",
    adminEnabled: false,
  },
  partenaire: {
    archetypeKey: "DEVELOPER",
    displayName: "Partenaire Externe (Invité Workspace 1)",
    accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
    role: "CONTRIBUTOR",
    orgUnitName: "Équipe Partenaire Intégration",
    adminEnabled: false,
  },
};

export function evaluateScopeModuleVisibility(
  role: string,
  scopeLevel: UiScopeLevel,
  hasWorkspaces: boolean,
): Record<UiModuleKey, boolean> {
  const isSupervisorOrAdmin =
    role === "PLATFORM_ADMIN" || role === "BU_DIRECTOR" || role === "TEAM_LEAD";
  return {
    cockpit: true,
    inbox: hasWorkspaces,
    catalog: true,
    ontology:
      hasWorkspaces &&
      (scopeLevel === "WORKSPACE" || scopeLevel === "TEAM" || isSupervisorOrAdmin),
    gates: hasWorkspaces,
    finops: hasWorkspaces && isSupervisorOrAdmin,
    admin: isSupervisorOrAdmin,
    bootstrap: isSupervisorOrAdmin,
  };
}

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

export function resolveModuleFromPathname(pathname: string | null): UiModuleKey {
  if (!pathname || pathname === "/" || pathname.startsWith("/cockpit")) {
    return "cockpit";
  }
  if (pathname.startsWith("/inbox")) return "inbox";
  if (pathname.startsWith("/catalog")) return "catalog";
  if (pathname.startsWith("/ontology")) return "ontology";
  if (pathname.startsWith("/gates")) return "gates";
  if (pathname.startsWith("/finops")) return "finops";
  if (pathname.startsWith("/bootstrap")) return "bootstrap";
  if (pathname.startsWith("/workspaces") || pathname.startsWith("/admin")) return "admin";
  return "cockpit";
}

export function ShellContainer({
  children,
  fixtureMode = false,
}: {
  children: React.ReactNode;
  fixtureMode?: boolean;
}) {
  const { locale, dictionary, toggleLocale } = useI18n();
  const pathname = usePathname();
  const router = useRouter();
  const [urlFixtureFlag, setUrlFixtureFlag] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("fixture") === "test") {
        setUrlFixtureFlag(true);
      }
    }
  }, []);

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
          router.push(route);
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
