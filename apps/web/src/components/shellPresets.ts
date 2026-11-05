import type {
  EightFixedMenuKey,
  UiHumanProfileBadge,
  UiModuleKey,
  UiScopeLevel,
  UiScopeNode,
  UiShellModuleItem,
} from "@orcia/ui";

export const DEFAULT_SHELL_MODULES: UiShellModuleItem[] = [
  { key: "cockpit", order: 1, route: "/cockpit", icon: "message-square", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
  { key: "inbox", order: 2, route: "/inbox", icon: "bell", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
  { key: "catalog", order: 3, route: "/catalog", icon: "package", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
  { key: "ontology", order: 4, route: "/ontology", icon: "dna", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
  { key: "gates", order: 5, route: "/gates", icon: "shield", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
  { key: "finops", order: 6, route: "/finops", icon: "bar-chart", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
  { key: "admin", order: 7, route: "/workspaces", icon: "settings", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
  { key: "bootstrap", order: 8, route: "/settings", icon: "rocket", contributorBadgeCount: 0, hasStaleWarning: false, enabled: true },
];

export const EMPTY_DEFAULT_SCOPES: UiScopeNode[] = [
  { id: "scope-global", level: "GLOBAL", name: "Plateforme Globale ORCIA", accessMode: "CONTRIBUTOR_ACTION_REQUIRED" },
];

export const DEFAULT_HUMAN_PROFILE: UiHumanProfileBadge = {
  archetypeKey: "PLATFORM_ADMIN",
  displayName: "Administrateur de la plateforme",
  accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
  role: "PLATFORM_ADMIN",
  orgUnitName: "",
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
  if (pathname.startsWith("/inbox") || pathname.startsWith("/assistant")) return "inbox";
  if (pathname.startsWith("/catalog") || pathname.startsWith("/agents")) return "catalog";
  if (
    pathname.startsWith("/ontology") ||
    pathname.startsWith("/help") ||
    pathname.startsWith("/showcase")
  ) {
    return "ontology";
  }
  if (pathname.startsWith("/gates") || pathname.startsWith("/processes")) return "gates";
  if (pathname.startsWith("/finops") || pathname.startsWith("/activity")) return "finops";
  if (
    pathname.startsWith("/bootstrap") ||
    pathname.startsWith("/settings") ||
    pathname.startsWith("/configuration") ||
    pathname.startsWith("/wizards")
  ) {
    return "bootstrap";
  }
  if (
    pathname.startsWith("/workspaces") ||
    pathname.startsWith("/spaces") ||
    pathname.startsWith("/admin")
  ) {
    return "admin";
  }
  return "cockpit";
}

export function resolveEightMenuKeyFromModule(
  moduleKey: UiModuleKey,
  pathname: string | null,
): EightFixedMenuKey {
  if (pathname?.startsWith("/help") || pathname?.startsWith("/showcase")) return "help";
  if (pathname?.startsWith("/agents")) return "agents";
  if (pathname?.startsWith("/processes")) return "processes";
  if (pathname?.startsWith("/assistant")) return "assistant";
  if (pathname?.startsWith("/spaces") || pathname?.startsWith("/workspaces")) return "spaces";
  if (pathname?.startsWith("/finops") || pathname?.startsWith("/activity")) return "finops";
  if (pathname?.startsWith("/configuration") || pathname?.startsWith("/settings")) {
    return "configuration";
  }
  switch (moduleKey) {
    case "cockpit":
      return "cockpit";
    case "inbox":
      return "assistant";
    case "catalog":
      return "agents";
    case "ontology":
      return "spaces";
    case "gates":
      return "processes";
    case "finops":
      return "finops";
    case "admin":
      return "spaces";
    case "bootstrap":
      return "configuration";
  }
}

export function mapEightMenuKeyToModule(key: EightFixedMenuKey): {
  moduleKey: UiModuleKey;
  route: string;
} {
  switch (key) {
    case "cockpit":
      return { moduleKey: "cockpit", route: "/cockpit" };
    case "assistant":
      return { moduleKey: "inbox", route: "/assistant" };
    case "processes":
      return { moduleKey: "gates", route: "/processes" };
    case "agents":
      return { moduleKey: "catalog", route: "/agents" };
    case "spaces":
      return { moduleKey: "admin", route: "/workspaces" };
    case "finops":
      return { moduleKey: "finops", route: "/finops" };
    case "configuration":
      return { moduleKey: "bootstrap", route: "/settings" };
    case "help":
      return { moduleKey: "ontology", route: "/help" };
  }
}
