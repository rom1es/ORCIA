import React, { useEffect, useState } from "react";
import { ContextualInfoTriggerButton } from "../components/ContextualInfoTriggerButton";
import { StatusBadge, type StatusBadgeTone } from "./StatusBadge";

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
}

export interface UiActivityScopeFilterOption {
  readonly id: string;
  readonly label: string;
  readonly scopePath: string;
  readonly level: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
  readonly childScopeIds?: readonly string[];
  readonly childScopePaths?: readonly string[];
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
  readonly timestampPrefix: string;
}

export interface ActivityLogExplorerViewProps {
  readonly events: readonly UiActivityLogEventItem[];
  readonly scopeOptions: readonly UiActivityScopeFilterOption[];
  readonly activeObservationScopeId: string;
  readonly activeObservationScopeLabel: string;
  readonly connectedUserName?: string;
  readonly nowTimestampMs?: number;
  readonly labels: ActivityLogExplorerLabels;
  readonly onOpenHelpSection?: (sectionId: string) => void;
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  fontSize: "12px",
};

function matchesTimeWindow(
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

function matchesScopeSelection(
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
      pathCandidate !== "global" &&
      (evPathLower.includes(pathCandidate) || evLabelLower.includes(pathCandidate))
    ) {
      return true;
    }
  }
  return false;
}

export function ActivityLogExplorerView({
  events,
  scopeOptions,
  activeObservationScopeId,
  activeObservationScopeLabel,
  connectedUserName,
  nowTimestampMs,
  labels,
  onOpenHelpSection,
}: ActivityLogExplorerViewProps): React.ReactElement {
  const [selectedScopeId, setSelectedScopeId] = useState<string>(activeObservationScopeId);
  const [selectedActor, setSelectedActor] = useState<string>("ALL");
  const [actorSearchQuery, setActorSearchQuery] = useState<string>("");
  const [maxLimit, setMaxLimit] = useState<ActivityMaxLimitOption>(100);
  const [timeWindow, setTimeWindow] = useState<ActivityTimeWindowOption>("ALL");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");

  useEffect(() => {
    setSelectedScopeId(activeObservationScopeId);
  }, [activeObservationScopeId]);

  const distinctActors = Array.from(
    new Set(
      [
        ...(connectedUserName && connectedUserName.trim() ? [connectedUserName.trim()] : []),
        ...events.map((ev) => ev.actorName.trim()).filter(Boolean),
      ],
    ),
  );

  const effectiveNowMs = nowTimestampMs ?? Date.now();
  const normalizedActorQuery = actorSearchQuery.trim().toLowerCase();

  const matchingEvents = events.filter((ev) => {
    if (!matchesScopeSelection(ev, selectedScopeId, scopeOptions)) {
      return false;
    }
    if (selectedActor !== "ALL" && ev.actorName !== selectedActor) {
      return false;
    }
    if (normalizedActorQuery.length > 0) {
      const actorTarget = `${ev.actorName} ${ev.actorEmail ?? ""}`.toLowerCase();
      if (!actorTarget.includes(normalizedActorQuery)) {
        return false;
      }
    }
    if (!matchesTimeWindow(ev.timestampIso, timeWindow, dateFrom, dateTo, effectiveNowMs)) {
      return false;
    }
    return true;
  });

  const visibleEvents = matchingEvents.slice(0, maxLimit);
  const activeScopeOption = scopeOptions.find((o) => o.id === selectedScopeId);
  const displayedScopeLabel =
    selectedScopeId === "ALL"
      ? labels.allScopesOptionLabel
      : (activeScopeOption?.label ?? activeObservationScopeLabel);

  return (
    <div
      data-testid="activity-log-explorer-page"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <header
        className="orcia-bento-card"
        style={{ display: "flex", flexDirection: "column", gap: "10px" }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "8px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <h1 style={{ margin: 0, fontSize: "var(--font-size-h2)" }}>
              {labels.pageTitle}
            </h1>
            <ContextualInfoTriggerButton
              sectionId="audit-overview"
              label={labels.infoButtonLabel}
              onOpenHelpSection={onOpenHelpSection}
            />
          </div>

          <div
            data-testid="activity-observation-scope-badge"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "4px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-bg-elevated)",
              fontSize: "12px",
            }}
          >
            <span>
              <strong>{labels.observationScopeBannerPrefix}</strong> {displayedScopeLabel}
            </span>
            {selectedScopeId !== activeObservationScopeId && (
              <button
                type="button"
                data-testid="activity-reset-observation-scope-btn"
                onClick={() => setSelectedScopeId(activeObservationScopeId)}
                style={{
                  padding: "2px 8px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor: "var(--color-surface-card)",
                  color: "var(--color-primary-cobalt)",
                  fontSize: "11px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {labels.resetToObservationScopeCta}
              </button>
            )}
          </div>
        </div>

        <p
          style={{
            margin: 0,
            fontSize: "var(--font-size-body)",
            color: "var(--color-muted-foreground)",
          }}
        >
          {labels.pageSubtitle}
        </p>

        {/* Filters Bar */}
        <div
          data-testid="activity-filters-bar"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "10px",
            marginTop: "4px",
          }}
        >
          {/* 1. Observation Scope Filter */}
          <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>{labels.scopeFilterLabel}</span>
            <select
              data-testid="activity-scope-filter-select"
              value={selectedScopeId}
              onChange={(e) => setSelectedScopeId(e.target.value)}
              style={inputStyle}
            >
              {scopeOptions.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
              {!scopeOptions.some((o) => o.id === "ALL") && (
                <option value="ALL">{labels.allScopesOptionLabel}</option>
              )}
            </select>
          </label>

          {/* 2. User / Author Filter + Search */}
          <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>{labels.userFilterLabel}</span>
            <div style={{ display: "flex", gap: "6px" }}>
              <select
                data-testid="activity-user-filter-select"
                value={selectedActor}
                onChange={(e) => setSelectedActor(e.target.value)}
                style={{ ...inputStyle, flex: 1 }}
              >
                <option value="ALL">{labels.allUsersOptionLabel}</option>
                {distinctActors.map((actor) => (
                  <option key={actor} value={actor}>
                    {actor}
                  </option>
                ))}
              </select>
              <input
                type="text"
                spellCheck={false}
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="activity-user-search-input"
                value={actorSearchQuery}
                onChange={(e) => setActorSearchQuery(e.target.value)}
                placeholder={labels.userSearchPlaceholder}
                style={{ ...inputStyle, flex: 1, minWidth: "110px" }}
              />
            </div>
          </label>

          {/* 3. Max Recent Limit Filter (50, 100, 200, 500) */}
          <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>{labels.maxLimitFilterLabel}</span>
            <select
              data-testid="activity-max-limit-select"
              value={String(maxLimit)}
              onChange={(e) => setMaxLimit(Number(e.target.value) as ActivityMaxLimitOption)}
              style={inputStyle}
            >
              <option value="50">{labels.limit50Label}</option>
              <option value="100">{labels.limit100Label}</option>
              <option value="200">{labels.limit200Label}</option>
              <option value="500">{labels.limit500Label}</option>
            </select>
          </label>

          {/* 4. Time Window Filter + Optional Custom Date Range */}
          <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>{labels.timeWindowFilterLabel}</span>
            <select
              data-testid="activity-time-window-select"
              value={timeWindow}
              onChange={(e) => setTimeWindow(e.target.value as ActivityTimeWindowOption)}
              style={inputStyle}
            >
              <option value="ALL">{labels.windowAllLabel}</option>
              <option value="1H">{labels.window1hLabel}</option>
              <option value="24H">{labels.window24hLabel}</option>
              <option value="7D">{labels.window7dLabel}</option>
              <option value="30D">{labels.window30dLabel}</option>
            </select>
          </label>
        </div>

        {/* Optional Custom Date Bounds */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "10px",
            paddingTop: "4px",
          }}
        >
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px", fontSize: "12px" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ color: "var(--color-muted-foreground)" }}>{labels.customDateFromLabel}</span>
              <input
                type="date"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="activity-date-from-input"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                style={inputStyle}
              />
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ color: "var(--color-muted-foreground)" }}>{labels.customDateToLabel}</span>
              <input
                type="date"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="activity-date-to-input"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                style={inputStyle}
              />
            </label>
          </div>

          <span
            data-testid="activity-results-counter"
            style={{ fontSize: "12px", fontWeight: 600, color: "var(--color-muted-foreground)" }}
          >
            {labels.resultsCounterPrefix} {visibleEvents.length} / {matchingEvents.length}
          </span>
        </div>
      </header>

      <section
        data-testid="settings-audit-section"
        className="orcia-bento-card"
        style={{ display: "flex", flexDirection: "column", gap: "10px" }}
      >
        {visibleEvents.length === 0 ? (
          <p
            data-testid="audit-events-empty-state"
            style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}
          >
            {labels.emptyStateMessage}
          </p>
        ) : (
          <div style={{ display: "grid", gap: "8px" }}>
            {visibleEvents.map((ev) => (
              <div
                key={ev.id}
                data-testid={`audit-event-row-${ev.id}`}
                style={{
                  padding: "10px 12px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor: "var(--color-surface-card)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                  <span
                    data-testid={`activity-event-summary-${ev.id}`}
                    style={{ fontWeight: 600, fontSize: "13px" }}
                  >
                    {ev.summary}
                  </span>
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      alignItems: "center",
                      gap: "12px",
                      fontSize: "12px",
                      color: "var(--color-muted-foreground)",
                    }}
                  >
                    <span
                      data-testid={`activity-event-timestamp-${ev.id}`}
                      style={{ fontFamily: "var(--font-mono)" }}
                    >
                      🕒 {labels.timestampPrefix} : {ev.formattedTimestamp}
                    </span>
                    <span data-testid={`activity-event-actor-${ev.id}`}>
                      👤 {labels.actorPrefix} : <strong>{ev.actorName}</strong>
                      {ev.actorEmail ? ` (${ev.actorEmail})` : ""}
                    </span>
                    <span data-testid={`activity-event-scope-${ev.id}`}>
                      📍 {labels.scopePrefix} : <strong>{ev.scopeLabel}</strong>
                    </span>
                  </div>
                </div>

                <div data-testid={`activity-event-type-${ev.id}`}>
                  <StatusBadge
                    label={ev.eventTypeLabel}
                    tone={ev.badgeTone ?? "cobalt"}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
