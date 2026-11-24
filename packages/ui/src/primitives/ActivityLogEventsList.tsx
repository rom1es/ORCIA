import React from "react";
import type { ActivityLogExplorerLabels, UiActivityLogEventItem } from "./activityLogHelpers";
import { StatusBadge } from "./StatusBadge";

export interface ActivityLogEventsListProps {
  readonly visibleEvents: readonly UiActivityLogEventItem[];
  readonly selectedRunId?: string;
  readonly labels: ActivityLogExplorerLabels;
  readonly onSelectRunId?: (runId: string) => void;
}

export function ActivityLogEventsList({
  visibleEvents,
  selectedRunId,
  labels,
  onSelectRunId,
}: ActivityLogEventsListProps): React.ReactElement {
  return (
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
                  <StatusBadge label={ev.eventTypeLabel} tone={ev.badgeTone ?? "cobalt"} />
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
                      {labels.runPrefix ?? ""}{" "}
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
  );
}
