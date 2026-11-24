import React from "react";
import type {
  CockpitPendingDecisionItem,
  FocusReviewWorkshopLeaseInfo,
  StreamlinedCockpitLabels,
} from "./StreamlinedCockpitView";

export interface CockpitFocusWorkshopPanelProps {
  readonly activeFocusWorkshop: FocusReviewWorkshopLeaseInfo;
  readonly labels: StreamlinedCockpitLabels;
  readonly onClose: () => void;
}

export function CockpitFocusWorkshopPanel({
  activeFocusWorkshop,
  labels,
  onClose,
}: CockpitFocusWorkshopPanelProps): React.ReactElement {
  return (
    <section
      data-testid="focus-review-workshop-view"
      className="flex flex-col gap-4 rounded border p-5"
      style={{
        backgroundColor: "var(--color-bg-surface)",
        borderColor: "var(--color-border-subtle)",
      }}
    >
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold">
          {labels.focusWorkshopBreadcrumbPrefix}{" "}
          <span className="font-mono">
            {`${labels.runNumberPrefix ?? "#"}${activeFocusWorkshop.runId}`}
          </span>
        </div>
        <button
          type="button"
          data-testid="focus-review-workshop-close-btn"
          onClick={onClose}
          className="rounded border px-3 py-1 text-xs font-medium"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
          }}
        >
          {labels.focusWorkshopCloseCta}
        </button>
      </div>

      <div
        data-testid="focus-review-redis-lock-badge"
        className="rounded border px-3 py-2 font-mono text-xs"
        style={{
          backgroundColor: "var(--color-action-primary-subtle)",
          borderColor: "var(--color-border-subtle)",
          color: "var(--color-action-primary)",
        }}
      >
        {`${labels.redisLockAcquiredPrefix} SET ${activeFocusWorkshop.redisLockKey} ${activeFocusWorkshop.claimedByUserId} NX EX ${activeFocusWorkshop.redisLockTtlSeconds}`}
      </div>
    </section>
  );
}

export interface CockpitDecisionsCardProps {
  readonly decisions: readonly CockpitPendingDecisionItem[];
  readonly filterMode: "ALL" | "SHORT" | "HEAVY";
  readonly onChangeFilterMode: (mode: "ALL" | "SHORT" | "HEAVY") => void;
  readonly resolvedTieBreaks: Readonly<Record<string, string>>;
  readonly onResolveTieBreakOption: (decisionId: string, option: string) => void;
  readonly onOpenFocusWorkshop: (item: CockpitPendingDecisionItem) => void;
  readonly labels: StreamlinedCockpitLabels;
}

export function CockpitDecisionsCard({
  decisions,
  filterMode,
  onChangeFilterMode,
  resolvedTieBreaks,
  onResolveTieBreakOption,
  onOpenFocusWorkshop,
  labels,
}: CockpitDecisionsCardProps): React.ReactElement {
  const countAnchors = decisions.filter((d) => d.kind === "ANCHOR").length;
  const countTieBreaks = decisions.filter((d) => d.kind === "TIE_BREAK").length;
  const countReviews = decisions.filter((d) => d.kind === "REVIEW_BRIEFING").length;
  const countAlerts = decisions.filter((d) => d.kind === "ALERT").length;

  const filteredDecisions = decisions.filter((d) => {
    if (filterMode === "SHORT") return d.kind === "TIE_BREAK";
    if (filterMode === "HEAVY") return d.kind !== "TIE_BREAK";
    return true;
  });

  const kpiCells = [
    { label: labels.kpiAnchorsLabel, value: countAnchors },
    { label: labels.kpiArbitrationsLabel, value: countTieBreaks },
    { label: labels.kpiReviewsLabel, value: countReviews },
    { label: labels.kpiAlertsLabel, value: countAlerts },
  ] as const;

  return (
    <div className="flex flex-col gap-4">
      <div
        data-testid="cockpit-kpi-counters-grid"
        className="grid grid-cols-2 gap-3 md:grid-cols-4"
      >
        {kpiCells.map((cell) => (
          <div
            key={cell.label}
            className="rounded border p-3"
            style={{
              backgroundColor: "var(--color-bg-surface)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>
              {cell.label}
            </div>
            <div className="mt-1 font-mono text-lg font-bold">{cell.value}</div>
          </div>
        ))}
      </div>

      <div data-testid="cockpit-decisions-filter-bar" className="flex items-center gap-2">
        {(
          [
            { key: "ALL", label: labels.filterAllLabel },
            { key: "SHORT", label: labels.filterShortLabel },
            { key: "HEAVY", label: labels.filterHeavyLabel },
          ] as const
        ).map((f) => (
          <button
            key={f.key}
            type="button"
            data-testid={`cockpit-filter-${f.key.toLowerCase()}`}
            onClick={() => onChangeFilterMode(f.key)}
            className="rounded border px-2.5 py-1 text-xs font-medium"
            style={{
              backgroundColor:
                filterMode === f.key
                  ? "var(--color-action-primary-subtle)"
                  : "var(--color-bg-surface)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-3">
        {filteredDecisions.map((item) => {
          const isShortTieBreak = item.kind === "TIE_BREAK";
          const resolvedChoice = resolvedTieBreaks[item.decisionId];
          return (
            <article
              key={item.decisionId}
              data-testid={`cockpit-decision-card-${item.decisionId}`}
              className="flex flex-col gap-2 rounded border p-4"
              style={{
                backgroundColor: "var(--color-bg-surface)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold">{item.title}</span>
                <span className="font-mono text-[11px]">
                  {isShortTieBreak ? labels.tieBreakInlineBadge : labels.heavyActionBadge}
                </span>
              </div>
              <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>
                {item.summary}
              </p>

              {isShortTieBreak ? (
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  {(item.options ?? []).map((opt, idx) => (
                    <button
                      key={opt}
                      type="button"
                      data-testid={`cockpit-tiebreak-option-${item.decisionId}-${idx}`}
                      onClick={() => onResolveTieBreakOption(item.decisionId, opt)}
                      className="rounded border px-2.5 py-1 text-xs font-medium"
                      style={{
                        backgroundColor: "var(--color-bg-elevated)",
                        borderColor: "var(--color-border-subtle)",
                      }}
                    >
                      {opt}
                    </button>
                  ))}
                  {resolvedChoice !== undefined && (
                    <span
                      data-testid={`cockpit-tiebreak-resolved-${item.decisionId}`}
                      className="text-xs font-semibold"
                      style={{ color: "var(--color-state-verified)" }}
                    >
                      {labels.tieBreakResolvedPrefix} {resolvedChoice}
                    </span>
                  )}
                </div>
              ) : (
                <div className="mt-1 flex justify-end">
                  <button
                    type="button"
                    data-testid={`cockpit-open-focus-review-btn-${item.decisionId}`}
                    onClick={() => onOpenFocusWorkshop(item)}
                    className="rounded px-3 py-1.5 text-xs font-semibold"
                    style={{
                      backgroundColor: "var(--color-action-primary)",
                      color: "var(--color-bg-surface)",
                    }}
                  >
                    {labels.openFocusReviewCta}
                  </button>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}
