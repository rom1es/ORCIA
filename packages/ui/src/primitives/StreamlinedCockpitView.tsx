import React, { useState } from "react";
import type { EightFixedMenuKey } from "./FourZoneShellTypes";
import {
  CockpitDecisionsCard,
  CockpitFocusWorkshopPanel,
} from "./CockpitDecisionsCard";
import { CockpitOrientationCards } from "./CockpitOrientationCards";

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
  readonly runNumberPrefix?: string;
}

export interface StreamlinedCockpitViewProps {
  readonly decisions: readonly CockpitPendingDecisionItem[];
  readonly currentUserId: string;
  readonly labels: StreamlinedCockpitLabels;
  readonly disabledMenuKeys?: Partial<Record<EightFixedMenuKey, string>>;
  readonly onResolveTieBreak?: (decisionId: string, selectedOption: string) => void;
  readonly onOpenFocusReview?: (lease: FocusReviewWorkshopLeaseInfo) => void;
  readonly onNavigateModule?: (moduleRoute: string) => void;
}

export function StreamlinedCockpitView({
  decisions,
  currentUserId,
  labels,
  disabledMenuKeys,
  onResolveTieBreak,
  onOpenFocusReview,
  onNavigateModule,
}: StreamlinedCockpitViewProps): React.ReactElement {
  const [filterMode, setFilterMode] = useState<"ALL" | "SHORT" | "HEAVY">("ALL");
  const [resolvedTieBreaks, setResolvedTieBreaks] = useState<Record<string, string>>({});
  const [activeFocusWorkshop, setActiveFocusWorkshop] =
    useState<FocusReviewWorkshopLeaseInfo | null>(null);

  const totalDecisions = decisions.length;

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
      <CockpitFocusWorkshopPanel
        activeFocusWorkshop={activeFocusWorkshop}
        labels={labels}
        onClose={() => setActiveFocusWorkshop(null)}
      />
    );
  }

  return (
    <section data-testid="streamlined-cockpit-view" className="flex flex-col gap-5">
      {totalDecisions === 0 ? (
        <CockpitOrientationCards
          labels={labels}
          disabledMenuKeys={disabledMenuKeys}
          onNavigateModule={onNavigateModule}
        />
      ) : (
        <CockpitDecisionsCard
          decisions={decisions}
          filterMode={filterMode}
          onChangeFilterMode={setFilterMode}
          resolvedTieBreaks={resolvedTieBreaks}
          onResolveTieBreakOption={(decisionId, opt) => {
            setResolvedTieBreaks((prev) => ({
              ...prev,
              [decisionId]: opt,
            }));
            onResolveTieBreak?.(decisionId, opt);
          }}
          onOpenFocusWorkshop={handleOpenFocusWorkshop}
          labels={labels}
        />
      )}
    </section>
  );
}
