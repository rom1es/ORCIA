import React, { useEffect, useState } from "react";
import { ContextualInfoTriggerButton } from "../components/ContextualInfoTriggerButton";
import { OrciaIcon } from "../components/icons";
import { ActivityLogFiltersBar } from "./ActivityLogFiltersBar";
import {
  matchesScopeSelection,
  matchesTimeWindow,
  type ActivityLogExplorerLabels,
  type ActivityLogProvenanceLabels,
  type ActivityMaxLimitOption,
  type ActivityTimeWindowOption,
  type UiActivityLogEventItem,
  type UiActivityScopeFilterOption,
} from "./activityLogHelpers";
import { ActivityLogProvenanceExportBar } from "./ActivityLogProvenanceExportBar";
import { StatusBadge } from "./StatusBadge";

export type {
  ActivityLogExplorerLabels,
  ActivityLogProvenanceLabels,
  ActivityMaxLimitOption,
  ActivityTimeWindowOption,
  UiActivityLogEventItem,
  UiActivityScopeFilterOption,
};

export interface ActivityLogExplorerViewProps {
  readonly events: readonly UiActivityLogEventItem[];
  readonly scopeOptions: readonly UiActivityScopeFilterOption[];
  readonly activeObservationScopeId: string;
  readonly activeObservationScopeLabel: string;
  readonly allowAllScopesOption?: boolean;
  readonly connectedUserName?: string;
  readonly nowTimestampMs?: number;
  readonly labels: ActivityLogExplorerLabels;
  readonly onOpenHelpSection?: (sectionId: string) => void;
  readonly selectedRunId?: string;
  readonly onSelectRunId?: (runId: string) => void;
  readonly onInspectProvenance?: (runId: string) => void;
  readonly onExportProvenance?: (runId: string, format: "json" | "md") => void;
  readonly isExporting?: boolean;
  readonly provenanceLabels?: ActivityLogProvenanceLabels;
}

export function ActivityLogExplorerView({
  events,
  scopeOptions,
  activeObservationScopeId,
  activeObservationScopeLabel,
  allowAllScopesOption = true,
  connectedUserName,
  nowTimestampMs,
  labels,
  provenanceLabels,
  onOpenHelpSection,
  selectedRunId,
  onSelectRunId,
  onInspectProvenance,
  onExportProvenance,
  isExporting = false,
}: ActivityLogExplorerViewProps): React.ReactElement {
  const resolvedDefaultScopeId =
    !allowAllScopesOption &&
    (activeObservationScopeId === "ALL" || activeObservationScopeId === "scope-global")
      ? (scopeOptions.find((o) => o.id !== "ALL" && o.id !== "scope-global")?.id ??
        activeObservationScopeId)
      : activeObservationScopeId;

  const [selectedScopeId, setSelectedScopeId] = useState<string>(resolvedDefaultScopeId);
  const [selectedActor, setSelectedActor] = useState<string>("ALL");
  const [actorSearchQuery, setActorSearchQuery] = useState<string>("");
  const [maxLimit, setMaxLimit] = useState<ActivityMaxLimitOption>(100);
  const [timeWindow, setTimeWindow] = useState<ActivityTimeWindowOption>("ALL");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");

  useEffect(() => {
    setSelectedScopeId(resolvedDefaultScopeId);
  }, [resolvedDefaultScopeId]);

  const distinctActors = Array.from(
    new Set(events.map((e) => e.actorName).filter(Boolean)),
  ).sort();

  const nowMs = nowTimestampMs ?? Date.now();

  const matchingEvents = events
    .filter((event) => matchesScopeSelection(event, selectedScopeId, scopeOptions))
    .filter((event) => {
      if (selectedActor !== "ALL" && event.actorName !== selectedActor) {
        return false;
      }
      if (actorSearchQuery.trim()) {
        const queryLower = actorSearchQuery.trim().toLowerCase();
        const matchName = event.actorName.toLowerCase().includes(queryLower);
        const matchEmail = (event.actorEmail ?? "").toLowerCase().includes(queryLower);
        if (!matchName && !matchEmail) {
          return false;
        }
      }
      return true;
    })
    .filter((event) =>
      matchesTimeWindow(event.timestampIso, timeWindow, dateFrom, dateTo, nowMs),
    );

  const visibleEvents = matchingEvents.slice(0, maxLimit);

  const isScopeBroadened = selectedScopeId !== activeObservationScopeId;

  return (
    <div
      data-testid="activity-log-explorer-page"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "16px",
        padding: "20px",
        maxWidth: "1400px",
        margin: "0 auto",
        width: "100%",
      }}
    >
      {/* Scope Observation Top Banner */}
      <div
        data-testid="activity-observation-scope-banner"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "8px",
          padding: "10px 14px",
          borderRadius: "var(--radius-sm)",
          backgroundColor: "var(--color-surface-card)",
          border: "1px solid var(--color-border)",
          fontSize: "13px",
        }}
      >
        <div
          data-testid="activity-observation-scope-badge"
          style={{ display: "flex", alignItems: "center", gap: "8px" }}
        >
          <span style={{ color: "var(--color-muted-foreground)" }}>
            {labels.observationScopeBannerPrefix}
          </span>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--color-action-primary-subtle)",
              color: "var(--color-primary-cobalt)",
              fontWeight: 600,
              fontSize: "12px",
            }}
          >
            <OrciaIcon name="spaces" />
            {activeObservationScopeLabel}
          </span>
        </div>

        {isScopeBroadened && (
          <button
            type="button"
            data-testid="activity-reset-observation-scope-btn"
            onClick={() => setSelectedScopeId(activeObservationScopeId)}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--color-primary-cobalt)",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: 500,
              textDecoration: "underline",
              padding: 0,
            }}
          >
            {labels.resetToObservationScopeCta}
          </button>
        )}
      </div>

      {/* Header with Title and Filters */}
      <header
        className="orcia-bento-card"
        style={{
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <h1 style={{ margin: 0, fontSize: "18px", fontWeight: 700 }}>{labels.pageTitle}</h1>
            {onOpenHelpSection && (
              <ContextualInfoTriggerButton
                testId="contextual-info-trigger-audit-overview"
                sectionId="audit-overview"
                label={labels.infoButtonLabel}
                onOpenHelpSection={onOpenHelpSection}
              />
            )}
          </div>
        </div>

        <p style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>
          {labels.pageSubtitle}
        </p>

        {/* Filters Bar Component */}
        <ActivityLogFiltersBar
          labels={labels}
          scopeOptions={scopeOptions}
          selectedScopeId={selectedScopeId}
          onScopeChange={setSelectedScopeId}
          allowAllScopesOption={allowAllScopesOption}
          distinctActors={distinctActors}
          selectedActor={selectedActor}
          onActorChange={setSelectedActor}
          actorSearchQuery={actorSearchQuery}
          onActorSearchChange={setActorSearchQuery}
          maxLimit={maxLimit}
          onMaxLimitChange={setMaxLimit}
          timeWindow={timeWindow}
          onTimeWindowChange={setTimeWindow}
          dateFrom={dateFrom}
          onDateFromChange={setDateFrom}
          dateTo={dateTo}
          onDateToChange={setDateTo}
        />

        {/* Results Counter */}
        <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: "4px" }}>
          <span
            data-testid="activity-results-counter"
            style={{ fontSize: "12px", fontWeight: 600, color: "var(--color-muted-foreground)" }}
          >
            {labels.resultsCounterPrefix} {visibleEvents.length} / {matchingEvents.length}
          </span>
        </div>
      </header>

      {/* Provenance and Export Bar */}
      {selectedRunId && (
        <ActivityLogProvenanceExportBar
          selectedRunId={selectedRunId}
          onInspectProvenance={onInspectProvenance}
          onExportProvenance={onExportProvenance}
          isExporting={isExporting}
          labels={provenanceLabels ?? labels.provenanceLabels}
        />
      )}

      {/* Activity Log Events Section */}
      <section
        data-testid="settings-audit-section"
        className="orcia-bento-card"
        style={{ padding: "16px" }}
      >
        {visibleEvents.length === 0 ? (
          <p
            data-testid="audit-events-empty-state"
            style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}
          >
            {labels.emptyStateMessage}
          </p>
        ) : (
          <div data-testid="activity-log-table" style={{ display: "grid", gap: "8px" }}>
            {visibleEvents.map((ev) => (
              <div
                key={ev.id}
                data-testid={`audit-event-row-${ev.id}`}
                onClick={() => ev.runId && onSelectRunId?.(ev.runId)}
                style={{
                  padding: "10px 12px",
                  borderRadius: "var(--radius-sm)",
                  border:
                    ev.runId && ev.runId === selectedRunId
                      ? "1px solid var(--color-primary-cobalt)"
                      : "1px solid var(--color-border)",
                  backgroundColor: "var(--color-surface-card)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "10px",
                  cursor: ev.runId ? "pointer" : "default",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                    <StatusBadge
                      label={ev.eventTypeLabel}
                      tone={ev.badgeTone ?? "cobalt"}
                    />
                    <span style={{ fontSize: "13px", fontWeight: 600 }}>{ev.summary}</span>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      gap: "12px",
                      fontSize: "12px",
                      color: "var(--color-muted-foreground)",
                      flexWrap: "wrap",
                    }}
                  >
                    <span data-testid={`activity-event-actor-${ev.id}`}>
                      {labels.actorPrefix}{" "}
                      <strong>
                        {ev.actorName}
                        {ev.actorEmail && !ev.actorName.includes(ev.actorEmail)
                          ? ` (${ev.actorEmail})`
                          : ""}
                      </strong>
                    </span>
                    <span data-testid={`activity-event-scope-${ev.id}`}>
                      {labels.scopePrefix} <strong>{ev.scopeLabel}</strong>
                    </span>
                    {ev.runId && (
                      <span>
                        {labels.runPrefix ?? "Exécution :"}{" "}
                        <code style={{ fontFamily: "var(--font-mono)" }}>
                          {ev.runId.slice(0, 8)}...
                        </code>
                      </span>
                    )}
                  </div>
                </div>

                <span
                  data-testid={`activity-event-timestamp-${ev.id}`}
                  style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}
                >
                  {labels.timestampPrefix} {ev.formattedTimestamp}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
