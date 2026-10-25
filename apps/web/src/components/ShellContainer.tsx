"use client";

import {
  AppShell,
  type UiHumanProfileBadge,
  type UiModuleKey,
  type UiPersonaKey,
  type UiScopeNode,
  type UiShellModuleItem,
} from "@orcia/ui";
import { usePathname, useRouter } from "next/navigation";
import React, { createContext, useContext, useEffect, useState } from "react";
import { useI18n } from "../i18n";

export const DEFAULT_SHELL_MODULES: UiShellModuleItem[] = [
  { key: "cockpit", order: 1, route: "/cockpit", icon: "message-square", contributorBadgeCount: 1, hasStaleWarning: false, enabled: true },
  { key: "inbox", order: 2, route: "/inbox", icon: "bell", contributorBadgeCount: 2, hasStaleWarning: false, enabled: true },
  { key: "catalog", order: 3, route: "/catalog", icon: "package", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
  { key: "ontology", order: 4, route: "/ontology", icon: "dna", contributorBadgeCount: 0, hasStaleWarning: true, enabled: true },
  { key: "gates", order: 5, route: "/gates", icon: "shield", contributorBadgeCount: 1, hasStaleWarning: false, enabled: true },
  { key: "finops", order: 6, route: "/finops", icon: "bar-chart", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
  { key: "admin", order: 7, route: "/workspaces", icon: "settings", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
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
  orgUnitName: "Sous-Équipe Checkout & Core Solutions",
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

interface PersonaContextValue {
  activePersona: UiPersonaKey;
  setActivePersona: (persona: UiPersonaKey) => void;
}

const PersonaContext = createContext<PersonaContextValue>({
  activePersona: "marc",
  setActivePersona: () => undefined,
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
  if (pathname.startsWith("/workspaces") || pathname.startsWith("/admin")) return "admin";
  return "cockpit";
}

export function ShellContainer({ children }: { children: React.ReactNode }) {
  const { locale, dictionary, toggleLocale } = useI18n();
  const pathname = usePathname();
  const router = useRouter();
  const [activeScopeId, setActiveScopeId] = useState("scope-ws-orcia");
  const [activePersona, setActivePersona] = useState<UiPersonaKey>("marc");
  const [selectedModuleOverride, setSelectedModuleOverride] = useState<UiModuleKey | null>(null);

  useEffect(() => {
    setSelectedModuleOverride(null);
  }, [pathname]);

  const activeModuleKey = selectedModuleOverride ?? resolveModuleFromPathname(pathname);
  const selectedScope =
    DEFAULT_SCOPES.find((s) => s.id === activeScopeId) ?? DEFAULT_SCOPES[3]!;
  const personaMeta = PERSONA_PROFILES[activePersona];

  const effectiveProfile: UiHumanProfileBadge = {
    archetypeKey: personaMeta.archetypeKey,
    displayName: personaMeta.displayName,
    role: personaMeta.role,
    orgUnitName: personaMeta.orgUnitName,
    accessMode:
      personaMeta.accessMode === "READ_ONLY_OBSERVER"
        ? "READ_ONLY_OBSERVER"
        : selectedScope.accessMode,
  };

  const effectiveModules: UiShellModuleItem[] = DEFAULT_SHELL_MODULES.map((mod) =>
    mod.key === "admin" ? { ...mod, enabled: personaMeta.adminEnabled } : mod,
  );
  const safeModuleKey: UiModuleKey =
    !personaMeta.adminEnabled && activeModuleKey === "admin" ? "cockpit" : activeModuleKey;

  return (
    <PersonaContext.Provider value={{ activePersona, setActivePersona }}>
      <AppShell
        modules={effectiveModules}
        activeModuleKey={safeModuleKey}
        scopes={DEFAULT_SCOPES}
        activeScopeId={activeScopeId}
        humanProfile={effectiveProfile}
        labels={dictionary.shell}
        currentLocale={locale}
        onSelectModule={(moduleKey, route) => {
          setSelectedModuleOverride(moduleKey);
          router.push(route);
        }}
        onSelectScope={(nextScopeId) => setActiveScopeId(nextScopeId)}
        onToggleLocale={toggleLocale}
      >
        {children}
      </AppShell>
    </PersonaContext.Provider>
  );
}
