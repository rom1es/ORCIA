import type { EightFixedMenuKey, ShellBreadcrumbItem } from "@orcia/ui";

function isWorkspaceScopedBreadcrumbRoute(pathname: string | null | undefined): boolean {
  if (!pathname || pathname === "/") return true;
  return (
    pathname.startsWith("/cockpit") ||
    pathname.startsWith("/assistant") ||
    pathname.startsWith("/inbox") ||
    pathname.startsWith("/processes") ||
    pathname.startsWith("/gates") ||
    pathname.startsWith("/agents") ||
    pathname.startsWith("/catalog") ||
    pathname.startsWith("/spaces") ||
    pathname.startsWith("/workspaces") ||
    pathname.startsWith("/ontology") ||
    pathname.startsWith("/finops") ||
    pathname.startsWith("/activity")
  );
}

function buildRouteModuleBreadcrumbItems(params: {
  readonly pathname: string | null | undefined;
  readonly isFr: boolean;
  readonly menuEntries: Record<EightFixedMenuKey, string>;
  readonly canAccessConfiguration?: boolean;
}): readonly ShellBreadcrumbItem[] {
  const { pathname, isFr, menuEntries, canAccessConfiguration = true } = params;
  if (!pathname || pathname === "/" || pathname.startsWith("/cockpit")) {
    return [{ label: menuEntries.cockpit, route: "/cockpit" }];
  }
  if (pathname.startsWith("/assistant")) {
    return [{ label: menuEntries.assistant, route: "/assistant" }];
  }
  if (pathname.startsWith("/inbox")) {
    return [{ label: isFr ? "Boîte de Réception" : "Inbox", route: "/inbox" }];
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
    if (!canAccessConfiguration) {
      return [{ label: isFr ? "Mon Organisation" : "My Organization", route: "/organization" }];
    }
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

export function buildShellBreadcrumbItems(params: {
  readonly pathname: string | null | undefined;
  readonly isFr: boolean;
  readonly menuEntries: Record<EightFixedMenuKey, string>;
  readonly activeTeamLabel?: string | null;
  readonly activeWorkspaceLabel?: string | null;
  readonly canAccessConfiguration?: boolean;
}): readonly ShellBreadcrumbItem[] {
  const {
    pathname,
    isFr,
    menuEntries,
    activeTeamLabel,
    activeWorkspaceLabel,
    canAccessConfiguration = true,
  } = params;
  const cleanTeam = (activeTeamLabel ?? "").trim();
  const isRedundantTeam =
    !cleanTeam ||
    cleanTeam === "ORCIA" ||
    cleanTeam === "Plateforme Globale ORCIA" ||
    cleanTeam === "Global Platform ORCIA";

  const cleanWorkspace = (activeWorkspaceLabel ?? "").trim();
  const isRedundantWorkspace =
    !cleanWorkspace ||
    cleanWorkspace === "ORCIA" ||
    cleanWorkspace === cleanTeam ||
    cleanWorkspace === "Plateforme Globale ORCIA" ||
    cleanWorkspace === "Global Platform ORCIA" ||
    cleanWorkspace === "Tous les espaces" ||
    cleanWorkspace === "All spaces";

  const moduleItems = buildRouteModuleBreadcrumbItems({
    pathname,
    isFr,
    menuEntries,
    canAccessConfiguration,
  });
  const prefix: ShellBreadcrumbItem[] = [{ label: "ORCIA", route: "/cockpit" }];
  if (!isRedundantTeam && !moduleItems.some((item) => item.label === cleanTeam)) {
    prefix.push({ label: cleanTeam });
  }
  if (
    isWorkspaceScopedBreadcrumbRoute(pathname) &&
    !isRedundantWorkspace &&
    !moduleItems.some((item) => item.label === cleanWorkspace)
  ) {
    prefix.push({ label: cleanWorkspace });
  }
  return [...prefix, ...moduleItems];
}
