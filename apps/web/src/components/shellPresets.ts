import type {
  EightFixedMenuKey,
  ShellBreadcrumbItem,
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

export function evaluateScopeModuleVisibility(
  role: string,
  scopeLevel: UiScopeLevel,
  hasWorkspaces: boolean,
): Record<UiModuleKey, boolean> {
  const isSupervisorOrAdmin =
    role === "PLATFORM_ADMIN" ||
    role === "BU_DIRECTOR" ||
    role === "BU_LEAD" ||
    role === "TEAM_LEAD";
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
    bootstrap: role === "PLATFORM_ADMIN" || role === "SECOPS",
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
    pathname.startsWith("/organization") ||
    pathname.startsWith("/admin")
  ) {
    return "admin";
  }
  return "cockpit";
}

export function resolveEightMenuKeyFromModule(
  moduleKey: UiModuleKey,
  pathname: string | null,
): EightFixedMenuKey | null {
  if (pathname) {
    if (pathname === "/" || pathname.startsWith("/cockpit")) return "cockpit";
    if (pathname.startsWith("/assistant") || pathname.startsWith("/inbox")) return "assistant";
    if (pathname.startsWith("/processes") || pathname.startsWith("/gates")) return "processes";
    if (pathname.startsWith("/agents") || pathname.startsWith("/catalog")) return "agents";
    if (
      pathname.startsWith("/spaces") ||
      pathname.startsWith("/workspaces") ||
      pathname.startsWith("/ontology")
    ) {
      return "spaces";
    }
    if (pathname.startsWith("/finops") || pathname.startsWith("/activity")) return "finops";
    if (
      pathname.startsWith("/configuration") ||
      pathname.startsWith("/settings") ||
      pathname.startsWith("/organization") ||
      pathname.startsWith("/wizards") ||
      pathname.startsWith("/bootstrap")
    ) {
      return "configuration";
    }
    if (pathname.startsWith("/help")) return "help";
    if (pathname.startsWith("/profile") || pathname.startsWith("/showcase")) return null;
    return null;
  }

  switch (moduleKey) {
    case "cockpit":
      return "cockpit";
    case "inbox":
      return "assistant";
    case "catalog":
      return "agents";
    case "ontology":
      return "help";
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
      return { moduleKey: "admin", route: "/spaces" };
    case "finops":
      return { moduleKey: "finops", route: "/finops" };
    case "configuration":
      return { moduleKey: "bootstrap", route: "/configuration" };
    case "help":
      return { moduleKey: "ontology", route: "/help" };
  }
}

export function resolveActiveMobileBottomTab(
  pathname: string | null | undefined,
): "cockpit" | "assistant" | "decisions" | null {
  if (pathname?.startsWith("/inbox")) {
    return "decisions";
  }
  if (pathname?.startsWith("/assistant")) {
    return "assistant";
  }
  if (pathname === "/" || pathname?.startsWith("/cockpit")) {
    return "cockpit";
  }
  return null;
}

export function isDesktopOnlyMobileRoute(pathname: string | null | undefined): boolean {
  if (!pathname) return false;
  return (
    pathname.startsWith("/settings") ||
    pathname.startsWith("/configuration") ||
    pathname.startsWith("/organization") ||
    pathname.startsWith("/processes/studio") ||
    pathname.startsWith("/processes/vsm")
  );
}

export function buildShellBreadcrumbItems(params: {
  readonly pathname: string | null | undefined;
  readonly isFr: boolean;
  readonly menuEntries: Record<EightFixedMenuKey, string>;
}): readonly ShellBreadcrumbItem[] {
  const { pathname, isFr, menuEntries } = params;
  if (!pathname || pathname === "/" || pathname.startsWith("/cockpit")) {
    return [{ label: menuEntries.cockpit, route: "/cockpit" }];
  }
  if (pathname.startsWith("/assistant")) {
    return [{ label: menuEntries.assistant, route: "/assistant" }];
  }
  if (pathname.startsWith("/inbox")) {
    return [
      { label: menuEntries.assistant, route: "/assistant" },
      { label: isFr ? "Décisions" : "Decisions", route: "/inbox" },
    ];
  }
  if (pathname.startsWith("/processes/studio")) {
    return [
      { label: menuEntries.processes, route: "/processes" },
      { label: "Studio" },
    ];
  }
  if (pathname.startsWith("/processes/vsm")) {
    return [
      { label: menuEntries.processes, route: "/processes" },
      { label: isFr ? "Chaîne de valeur" : "Value Stream" },
    ];
  }
  if (pathname.startsWith("/processes")) {
    return [{ label: menuEntries.processes, route: "/processes" }];
  }
  if (pathname.startsWith("/gates")) {
    return [
      { label: menuEntries.processes, route: "/processes" },
      { label: isFr ? "Validations" : "Quality Gates", route: "/gates" },
    ];
  }
  if (pathname.startsWith("/agents")) {
    return [{ label: menuEntries.agents, route: "/agents" }];
  }
  if (pathname.startsWith("/catalog")) {
    return [
      { label: menuEntries.agents, route: "/agents" },
      { label: isFr ? "Catalogue" : "Catalog", route: "/catalog" },
    ];
  }
  if (pathname.startsWith("/ontology")) {
    return [
      { label: menuEntries.spaces, route: "/spaces" },
      { label: isFr ? "Glossaire" : "Glossary", route: "/ontology" },
    ];
  }
  if (pathname.includes("/sources") && pathname.startsWith("/workspaces")) {
    return [
      { label: menuEntries.spaces, route: "/spaces" },
      { label: "Sources" },
    ];
  }
  if (pathname.startsWith("/spaces") || pathname.startsWith("/workspaces")) {
    return [{ label: menuEntries.spaces, route: "/spaces" }];
  }
  if (pathname.startsWith("/activity")) {
    return [
      { label: menuEntries.finops, route: "/finops" },
      { label: isFr ? "Journal d'Activité" : "Activity Log", route: "/activity" },
    ];
  }
  if (pathname.startsWith("/finops")) {
    return [{ label: menuEntries.finops, route: "/finops" }];
  }
  if (pathname.startsWith("/organization")) {
    return [
      { label: menuEntries.configuration, route: "/configuration" },
      { label: isFr ? "Mon Organisation" : "My Organization", route: "/organization" },
    ];
  }
  if (pathname.startsWith("/wizards")) {
    return [
      { label: menuEntries.configuration, route: "/configuration" },
      { label: isFr ? "Assistants Guidés" : "Guided Wizards", route: "/wizards" },
    ];
  }
  if (
    pathname.startsWith("/configuration") ||
    pathname.startsWith("/settings") ||
    pathname.startsWith("/bootstrap")
  ) {
    return [{ label: menuEntries.configuration, route: "/configuration" }];
  }
  if (pathname.startsWith("/profile")) {
    return [{ label: isFr ? "Profil" : "Profile", route: "/profile" }];
  }
  if (pathname.startsWith("/showcase")) {
    return [
      { label: menuEntries.help, route: "/help" },
      { label: isFr ? "Présentation ORCIA" : "ORCIA Showcase", route: "/showcase" },
    ];
  }
  if (pathname.startsWith("/help")) {
    return [{ label: menuEntries.help, route: "/help" }];
  }
  return [];
}
