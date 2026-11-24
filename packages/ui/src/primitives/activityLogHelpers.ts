import type { StatusBadgeTone } from "./StatusBadge";

export type ActivityTimeWindowOption = "ALL" | "1H" | "24H" | "7D" | "30D";
export type ActivityMaxLimitOption = 50 | 100 | 200 | 500;

export interface UiActivityLogEventItem {
  readonly id: string;
  readonly timestampIso: string;
  readonly formattedTimestamp: string;
  readonly eventType: string;
  readonly eventTypeLabel: string;
  readonly summary: string;
  readonly actorName: string;
  readonly actorEmail?: string;
  readonly scopeId?: string;
  readonly scopePath: string;
  readonly scopeLabel: string;
  readonly badgeTone?: StatusBadgeTone;
  readonly runId?: string;
}

export interface UiActivityScopeFilterOption {
  readonly id: string;
  readonly label: string;
  readonly scopePath: string;
  readonly level: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
  readonly childScopeIds?: readonly string[];
  readonly childScopePaths?: readonly string[];
}

export interface ActivityLogProvenanceLabels {
  readonly selectedRunPrefix: string;
  readonly inspectProvenanceAction: string;
  readonly exportJsonAction: string;
  readonly exportMdAction: string;
}

export interface ActivityLogExplorerLabels {
  readonly pageTitle: string;
  readonly pageSubtitle: string;
  readonly infoButtonLabel: string;
  readonly observationScopeBannerPrefix: string;
  readonly resetToObservationScopeCta: string;
  readonly scopeFilterLabel: string;
  readonly allScopesOptionLabel: string;
  readonly userFilterLabel: string;
  readonly allUsersOptionLabel: string;
  readonly userSearchPlaceholder: string;
  readonly maxLimitFilterLabel: string;
  readonly limit50Label: string;
  readonly limit100Label: string;
  readonly limit200Label: string;
  readonly limit500Label: string;
  readonly timeWindowFilterLabel: string;
  readonly windowAllLabel: string;
  readonly window1hLabel: string;
  readonly window24hLabel: string;
  readonly window7dLabel: string;
  readonly window30dLabel: string;
  readonly customDateFromLabel: string;
  readonly customDateToLabel: string;
  readonly resultsCounterPrefix: string;
  readonly emptyStateMessage: string;
  readonly actorPrefix: string;
  readonly scopePrefix: string;
  readonly runPrefix?: string;
  readonly timestampPrefix: string;
  readonly provenanceLabels?: ActivityLogProvenanceLabels;
}

export function matchesTimeWindow(
  timestampIso: string,
  windowMode: ActivityTimeWindowOption,
  dateFrom: string,
  dateTo: string,
  nowMs: number,
): boolean {
  const parsed = Date.parse(timestampIso);
  if (Number.isNaN(parsed)) {
    return true;
  }
  if (windowMode !== "ALL") {
    const windowMsMap: Record<Exclude<ActivityTimeWindowOption, "ALL">, number> = {
      "1H": 60 * 60 * 1000,
      "24H": 24 * 60 * 60 * 1000,
      "7D": 7 * 24 * 60 * 60 * 1000,
      "30D": 30 * 24 * 60 * 60 * 1000,
    };
    const delta = nowMs - parsed;
    if (delta > windowMsMap[windowMode]) {
      return false;
    }
  }
  if (dateFrom.trim()) {
    const fromMs = Date.parse(dateFrom.trim());
    if (!Number.isNaN(fromMs) && parsed < fromMs) {
      return false;
    }
  }
  if (dateTo.trim()) {
    const toRaw = dateTo.trim();
    const toMs = Date.parse(toRaw.length <= 10 ? `${toRaw}T23:59:59.999Z` : toRaw);
    if (!Number.isNaN(toMs) && parsed > toMs) {
      return false;
    }
  }
  return true;
}

export function matchesScopeSelection(
  event: UiActivityLogEventItem,
  selectedScopeId: string,
  scopeOptions: readonly UiActivityScopeFilterOption[],
): boolean {
  if (selectedScopeId === "ALL" || selectedScopeId === "scope-global") {
    return true;
  }
  const option = scopeOptions.find((opt) => opt.id === selectedScopeId);
  if (!option || option.level === "GLOBAL") {
    return true;
  }
  const allowedIds = new Set<string>([option.id, ...(option.childScopeIds ?? [])]);
  const allowedPaths = new Set<string>(
    [option.scopePath, option.label, ...(option.childScopePaths ?? [])].map((v) =>
      v.toLowerCase(),
    ),
  );
  if (event.scopeId && allowedIds.has(event.scopeId)) {
    return true;
  }
  const evPathLower = event.scopePath.toLowerCase();
  const evLabelLower = event.scopeLabel.toLowerCase();
  if (allowedPaths.has(evPathLower) || allowedPaths.has(evLabelLower)) {
    return true;
  }
  for (const pathCandidate of allowedPaths) {
    if (
      pathCandidate &&
      (evPathLower.includes(pathCandidate) || pathCandidate.includes(evPathLower))
    ) {
      return true;
    }
  }
  return false;
}
