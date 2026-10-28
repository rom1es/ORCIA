import type {
  UiHumanProfileBadge,
  UiModuleKey,
  UiPersonaKey,
  UiScopeLevel,
  UiScopeNode,
  UiShellModuleItem,
} from "@orcia/ui";

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
