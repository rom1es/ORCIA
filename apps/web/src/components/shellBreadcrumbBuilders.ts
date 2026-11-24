import type { FourZoneDirectionCShellLabels, ShellBreadcrumbItem } from "@orcia/ui";
import { DICTIONARIES, resolveDictionaryForFlag } from "../i18n";
import { resolveGlobalScopeLabel } from "./platformSetupWorkspaces";

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
  readonly locale?: "fr" | "en";
  readonly menuEntries: FourZoneDirectionCShellLabels["menuEntries"];
}): readonly ShellBreadcrumbItem[] {
  const { pathname, isFr, locale, menuEntries } = params;
  const copy = resolveDictionaryForFlag(isFr, locale).shellBreadcrumbsAndScope.breadcrumbs;

  if (!pathname || pathname === "/" || pathname.startsWith("/cockpit")) {
    return [{ label: menuEntries.cockpit, route: "/cockpit" }];
  }
  if (pathname.startsWith("/assistant")) {
    return [{ label: menuEntries.assistant, route: "/assistant" }];
  }
  if (pathname.startsWith("/inbox")) {
    return [{ label: copy.inbox, route: "/inbox" }];
  }
  if (pathname.startsWith("/processes/studio")) {
    return [
      { label: menuEntries.processes, route: "/processes" },
      { label: copy.studio },
    ];
  }
  if (pathname.startsWith("/processes/vsm")) {
    return [
      { label: menuEntries.processes, route: "/processes" },
      { label: copy.valueStream },
    ];
  }
  if (pathname.startsWith("/processes")) {
    return [{ label: menuEntries.processes, route: "/processes" }];
  }
  if (pathname.startsWith("/gates")) {
    return [
      { label: menuEntries.processes, route: "/processes" },
      { label: copy.qualityGates, route: "/gates" },
    ];
  }
  if (pathname.startsWith("/agents")) {
    return [{ label: menuEntries.agents, route: "/agents" }];
  }
  if (pathname.startsWith("/catalog")) {
    return [
      { label: menuEntries.agents, route: "/agents" },
      { label: copy.catalog, route: "/catalog" },
    ];
  }
  if (pathname.startsWith("/ontology")) {
    return [
      { label: menuEntries.spaces, route: "/spaces" },
      { label: copy.glossary, route: "/ontology" },
    ];
  }
  if (pathname.includes("/sources") && pathname.startsWith("/workspaces")) {
    return [
      { label: menuEntries.spaces, route: "/spaces" },
      { label: copy.sources },
    ];
  }
  if (pathname.startsWith("/spaces") || pathname.startsWith("/workspaces")) {
    return [{ label: menuEntries.spaces, route: "/spaces" }];
  }
  if (pathname.startsWith("/activity")) {
    return [
      { label: menuEntries.finops, route: "/finops" },
      { label: copy.activityLog, route: "/activity" },
    ];
  }
  if (pathname.startsWith("/finops")) {
    return [{ label: menuEntries.finops, route: "/finops" }];
  }
  if (pathname.startsWith("/organization")) {
    return [{ label: menuEntries.organization ?? copy.organization, route: "/organization" }];
  }
  if (pathname.startsWith("/wizards")) {
    return [
      { label: menuEntries.configuration, route: "/configuration" },
      { label: copy.guidedWizards, route: "/wizards" },
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
    return [{ label: copy.profile, route: "/profile" }];
  }
  if (pathname.startsWith("/showcase")) {
    return [
      { label: menuEntries.help, route: "/help" },
      { label: copy.showcase, route: "/showcase" },
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
  readonly locale?: "fr" | "en";
  readonly menuEntries: FourZoneDirectionCShellLabels["menuEntries"];
  readonly activeTeamLabel?: string | null;
  readonly activeWorkspaceLabel?: string | null;
  readonly canAccessConfiguration?: boolean;
}): readonly ShellBreadcrumbItem[] {
  const {
    pathname,
    isFr,
    locale,
    menuEntries,
    activeTeamLabel,
    activeWorkspaceLabel,
  } = params;
  const globalLabelFr = resolveGlobalScopeLabel(true);
  const globalLabelEn = resolveGlobalScopeLabel(false);
  const redundantAllSpaces = new Set([
    ...DICTIONARIES.fr.shellBreadcrumbsAndScope.breadcrumbs.redundantAllSpacesLabels,
    ...DICTIONARIES.en.shellBreadcrumbsAndScope.breadcrumbs.redundantAllSpacesLabels,
  ]);
  const cleanTeam = (activeTeamLabel ?? "").trim();
  const isRedundantTeam =
    !cleanTeam ||
    cleanTeam === "ORCIA" ||
    cleanTeam === globalLabelFr ||
    cleanTeam === globalLabelEn;

  const cleanWorkspace = (activeWorkspaceLabel ?? "").trim();
  const isRedundantWorkspace =
    !cleanWorkspace ||
    cleanWorkspace === "ORCIA" ||
    cleanWorkspace === cleanTeam ||
    cleanWorkspace === globalLabelFr ||
    cleanWorkspace === globalLabelEn ||
    redundantAllSpaces.has(cleanWorkspace);

  const moduleItems = buildRouteModuleBreadcrumbItems({
    pathname,
    isFr,
    locale,
    menuEntries,
  });
  const prefix: ShellBreadcrumbItem[] = [];
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
