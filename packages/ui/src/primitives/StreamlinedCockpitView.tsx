import React, { useState } from "react";

export type CockpitDecisionKind = "TIE_BREAK" | "ANCHOR" | "REVIEW_BRIEFING" | "ALERT";

export interface CockpitPendingDecisionItem {
  readonly decisionId: string;
  readonly kind: CockpitDecisionKind;
  readonly runId: string;
  readonly stepExecutionId: string;
  readonly title: string;
  readonly summary: string;
  readonly options?: readonly string[];
}

export interface FocusReviewWorkshopLeaseInfo {
  readonly decisionId: string;
  readonly runId: string;
  readonly stepExecutionId: string;
  readonly redisLockKey: string;
  readonly redisLockTtlSeconds: number;
  readonly claimedByUserId: string;
}

export interface StreamlinedCockpitLabels {
  readonly zeroDecisionsBanner: string;
  readonly quickAssistantTitle: string;
  readonly quickAssistantPlaceholder: string;
  readonly quickAssistantCta: string;
  readonly orientationAssistantTitle: string;
  readonly orientationAssistantDesc: string;
  readonly orientationProcessesTitle: string;
  readonly orientationProcessesDesc: string;
  readonly orientationSpacesTitle: string;
  readonly orientationSpacesDesc: string;
  readonly kpiAnchorsLabel: string;
  readonly kpiArbitrationsLabel: string;
  readonly kpiReviewsLabel: string;
  readonly kpiAlertsLabel: string;
  readonly filterAllLabel: string;
  readonly filterShortLabel: string;
  readonly filterHeavyLabel: string;
  readonly tieBreakInlineBadge: string;
  readonly tieBreakResolvedPrefix: string;
  readonly heavyActionBadge: string;
  readonly openFocusReviewCta: string;
  readonly focusWorkshopBreadcrumbPrefix: string;
  readonly focusWorkshopCloseCta: string;
  readonly redisLockAcquiredPrefix: string;
}

export interface StreamlinedCockpitViewProps {
  readonly decisions: readonly CockpitPendingDecisionItem[];
  readonly currentUserId: string;
  readonly labels: StreamlinedCockpitLabels;
  readonly onResolveTieBreak?: (decisionId: string, selectedOption: string) => void;
  readonly onOpenFocusReview?: (lease: FocusReviewWorkshopLeaseInfo) => void;
  readonly onOpenAssistant?: (initialPrompt: string) => void;
  readonly onNavigateModule?: (moduleRoute: string) => void;
}

export function StreamlinedCockpitView({
  decisions,
  currentUserId,
  labels,
  onResolveTieBreak,
  onOpenFocusReview,
  onOpenAssistant,
  onNavigateModule,
}: StreamlinedCockpitViewProps): React.ReactElement {
  const [quickPrompt, setQuickPrompt] = useState<string>("");
  const [filterMode, setFilterMode] = useState<"ALL" | "SHORT" | "HEAVY">("ALL");
  const [resolvedTieBreaks, setResolvedTieBreaks] = useState<Record<string, string>>({});
  const [activeFocusWorkshop, setActiveFocusWorkshop] =
    useState<FocusReviewWorkshopLeaseInfo | null>(null);

  const totalDecisions = decisions.length;
  const countAnchors = decisions.filter((d) => d.kind === "ANCHOR").length;
  const countTieBreaks = decisions.filter((d) => d.kind === "TIE_BREAK").length;
  const countReviews = decisions.filter((d) => d.kind === "REVIEW_BRIEFING").length;
  const countAlerts = decisions.filter((d) => d.kind === "ALERT").length;

  const filteredDecisions = decisions.filter((d) => {
    if (filterMode === "SHORT") {
      return d.kind === "TIE_BREAK";
    }
    if (filterMode === "HEAVY") {
      return d.kind !== "TIE_BREAK";
    }
    return true;
  });

  const handleOpenFocusWorkshop = (item: CockpitPendingDecisionItem): void => {
    const lease: FocusReviewWorkshopLeaseInfo = {
      decisionId: item.decisionId,
      runId: item.runId,
      stepExecutionId: item.stepExecutionId,
      redisLockKey: `lock:step:${item.stepExecutionId}`,
      redisLockTtlSeconds: 900,
      claimedByUserId: currentUserId,
    };
    setActiveFocusWorkshop(lease);
    onOpenFocusReview?.(lease);
  };

  if (activeFocusWorkshop !== null) {
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
            <span className="font-mono">Run #{activeFocusWorkshop.runId}</span>
          </div>
          <button
            type="button"
            data-testid="focus-review-workshop-close-btn"
            onClick={() => setActiveFocusWorkshop(null)}
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
          {labels.redisLockAcquiredPrefix} SET {activeFocusWorkshop.redisLockKey}{" "}
          {activeFocusWorkshop.claimedByUserId} NX EX {activeFocusWorkshop.redisLockTtlSeconds}
        </div>
      </section>
    );
  }

  return (
    <section data-testid="streamlined-cockpit-view" className="flex flex-col gap-5">
      {/* When total == 0: Hide 0/0/0/0 KPI counters and filter bar; show calm banner + Quick Assistant + 3 Orientation Cards */}
      {totalDecisions === 0 ? (
        <div className="flex flex-col gap-4">
          <div
            data-testid="cockpit-zero-decisions-banner"
            className="rounded border px-4 py-3 text-sm font-semibold"
            style={{
              backgroundColor: "var(--color-bg-surface)",
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-state-verified)",
            }}
          >
            {labels.zeroDecisionsBanner}
          </div>

          <div
            data-testid="cockpit-quick-assistant-box"
            className="flex flex-col gap-2 rounded border p-4"
            style={{
              backgroundColor: "var(--color-bg-surface)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <h3 className="text-xs font-semibold">{labels.quickAssistantTitle}</h3>
            <div className="flex gap-2">
              <input
                type="text"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="cockpit-quick-assistant-input"
                value={quickPrompt}
                onChange={(e) => setQuickPrompt(e.target.value)}
                placeholder={labels.quickAssistantPlaceholder}
                className="flex-1 rounded border px-3 py-1.5 text-xs"
                style={{
                  backgroundColor: "var(--color-bg-canvas)",
                  borderColor: "var(--color-border-subtle)",
                }}
              />
              <button
                type="button"
                data-testid="cockpit-quick-assistant-submit"
                onClick={() => onOpenAssistant?.(quickPrompt)}
                className="rounded px-3 py-1.5 text-xs font-semibold"
                style={{
                  backgroundColor: "var(--color-action-primary)",
                  color: "var(--color-bg-surface)",
                }}
              >
                {labels.quickAssistantCta}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <button
              type="button"
              data-testid="cockpit-orientation-card-assistant"
              onClick={() => onNavigateModule?.("/assistant")}
              className="rounded border p-4 text-left"
              style={{
                backgroundColor: "var(--color-bg-surface)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <div className="text-xs font-semibold">{labels.orientationAssistantTitle}</div>
              <p className="mt-1 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                {labels.orientationAssistantDesc}
              </p>
            </button>

            <button
              type="button"
              data-testid="cockpit-orientation-card-processes"
              onClick={() => onNavigateModule?.("/processes")}
              className="rounded border p-4 text-left"
              style={{
                backgroundColor: "var(--color-bg-surface)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <div className="text-xs font-semibold">{labels.orientationProcessesTitle}</div>
              <p className="mt-1 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                {labels.orientationProcessesDesc}
              </p>
            </button>

            <button
              type="button"
              data-testid="cockpit-orientation-card-spaces"
              onClick={() => onNavigateModule?.("/spaces")}
              className="rounded border p-4 text-left"
              style={{
                backgroundColor: "var(--color-bg-surface)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <div className="text-xs font-semibold">{labels.orientationSpacesTitle}</div>
              <p className="mt-1 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                {labels.orientationSpacesDesc}
              </p>
            </button>
          </div>
        </div>
      ) : (
        /* When total >= 1: Show KPI counters, filter bar, and separate short Tie-Breaks from heavy Focus Review */
        <div className="flex flex-col gap-4">
          <div
            data-testid="cockpit-kpi-counters-grid"
            className="grid grid-cols-2 gap-3 md:grid-cols-4"
          >
            <div
              className="rounded border p-3"
              style={{
                backgroundColor: "var(--color-bg-surface)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <div className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>
                {labels.kpiAnchorsLabel}
              </div>
              <div className="mt-1 font-mono text-lg font-bold">{countAnchors}</div>
            </div>
            <div
              className="rounded border p-3"
              style={{
                backgroundColor: "var(--color-bg-surface)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <div className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>
                {labels.kpiArbitrationsLabel}
              </div>
              <div className="mt-1 font-mono text-lg font-bold">{countTieBreaks}</div>
            </div>
            <div
              className="rounded border p-3"
              style={{
                backgroundColor: "var(--color-bg-surface)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <div className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>
                {labels.kpiReviewsLabel}
              </div>
              <div className="mt-1 font-mono text-lg font-bold">{countReviews}</div>
            </div>
            <div
              className="rounded border p-3"
              style={{
                backgroundColor: "var(--color-bg-surface)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <div className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>
                {labels.kpiAlertsLabel}
              </div>
              <div className="mt-1 font-mono text-lg font-bold">{countAlerts}</div>
            </div>
          </div>

          <div
            data-testid="cockpit-decisions-filter-bar"
            className="flex items-center gap-2"
          >
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
                onClick={() => setFilterMode(f.key)}
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
                          onClick={() => {
                            setResolvedTieBreaks((prev) => ({
                              ...prev,
                              [item.decisionId]: opt,
                            }));
                            onResolveTieBreak?.(item.decisionId, opt);
                          }}
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
                        onClick={() => handleOpenFocusWorkshop(item)}
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
      )}
    </section>
  );
}
