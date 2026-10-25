"use client";

import {
  AppShell,
  type UiHumanProfileBadge,
  type UiModuleKey,
  type UiScopeNode,
  type UiShellModuleItem,
} from "@orcia/ui";
import { usePathname, useRouter } from "next/navigation";
import React, { useEffect, useState } from "react";
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
};

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
  const [selectedModuleOverride, setSelectedModuleOverride] = useState<UiModuleKey | null>(null);

  useEffect(() => {
    setSelectedModuleOverride(null);
  }, [pathname]);

  const activeModuleKey = selectedModuleOverride ?? resolveModuleFromPathname(pathname);
  const selectedScope =
    DEFAULT_SCOPES.find((s) => s.id === activeScopeId) ?? DEFAULT_SCOPES[3]!;

  const effectiveProfile: UiHumanProfileBadge = {
    ...DEFAULT_HUMAN_PROFILE,
    accessMode: selectedScope.accessMode,
  };

  return (
    <AppShell
      modules={DEFAULT_SHELL_MODULES}
      activeModuleKey={activeModuleKey}
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
  );
}
