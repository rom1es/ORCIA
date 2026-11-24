import React from "react";
import type {
  ExceptionWaiverItem,
  WorkspaceFiveTabsLabels,
} from "./WorkspaceFiveTabsAndExternalRebaseView";
import {
  WaiversAndRebasePanel,
  type WaiversAndRebasePanelProps,
} from "./WorkspaceFiveTabsPanels";

export interface OverviewStatItem {
  readonly key: string;
  readonly title: string;
  readonly value: string | number;
}

export interface OverviewTabPanelProps {
  readonly sourcesCount: number;
  readonly pendingGlossaryCandidatesCount: number;
  readonly activeWaivers: readonly ExceptionWaiverItem[];
  readonly overviewStats: readonly OverviewStatItem[];
  readonly labels: WorkspaceFiveTabsLabels;
  readonly workspaceName?: string;
  readonly safeSlug: string;
  readonly sharedWaiverProps: WaiversAndRebasePanelProps;
}

export const OverviewTabPanel: React.FC<OverviewTabPanelProps> = ({
  sourcesCount,
  pendingGlossaryCandidatesCount,
  activeWaivers,
  overviewStats,
  labels,
  workspaceName,
  safeSlug,
  sharedWaiverProps,
}) => {
  const hasAnyOverviewActivity =
    sourcesCount > 0 || pendingGlossaryCandidatesCount > 0 || activeWaivers.length > 0;

  return (
    <div
      role="tabpanel"
      aria-labelledby="workspace-tab-OVERVIEW"
      className="grid grid-cols-1 gap-4 md:grid-cols-2"
    >
      <div
        data-testid="workspace-overview-panel"
        className="space-y-3 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
      >
        <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
          {labels.tabOverview}
        </h3>
        {hasAnyOverviewActivity ? (
          <>
            <p className="text-xs text-[var(--orcia-text-secondary)]">
              {labels.overviewSummaryText ?? workspaceName ?? safeSlug}
            </p>
            <div data-testid="workspace-overview-kpi-grid" className="grid grid-cols-2 gap-2 text-xs">
              {overviewStats.map((stat) => (
                <div
                  key={stat.key}
                  data-testid={`workspace-overview-kpi-${stat.key}`}
                  className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2"
                >
                  <div className="text-[11px] text-[var(--orcia-text-secondary)]">{stat.title}</div>
                  <strong className="text-sm">{stat.value}</strong>
                </div>
              ))}
            </div>
          </>
        ) : (
          <p
            data-testid="workspace-overview-empty-hint"
            className="text-xs text-[var(--orcia-text-secondary)]"
          >
            {labels.overviewEmptyStateHint ?? labels.overviewSummaryText ?? workspaceName ?? safeSlug}
          </p>
        )}
      </div>
      <WaiversAndRebasePanel {...sharedWaiverProps} />
    </div>
  );
};

export interface GlossaryRulesTabPanelProps {
  readonly pendingGlossaryCandidatesCount: number;
  readonly activeWaiversCount: number;
  readonly labels: WorkspaceFiveTabsLabels;
  readonly glossaryTabSlot?: React.ReactNode;
  readonly sharedWaiverProps: WaiversAndRebasePanelProps;
}

export const GlossaryRulesTabPanel: React.FC<GlossaryRulesTabPanelProps> = ({
  pendingGlossaryCandidatesCount,
  activeWaiversCount,
  labels,
  glossaryTabSlot,
  sharedWaiverProps,
}) => (
  <div
    role="tabpanel"
    aria-labelledby="workspace-tab-GLOSSARY_RULES"
    data-testid="workspace-glossary-rules-panel"
    className="space-y-3 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
  >
    {glossaryTabSlot ? (
      glossaryTabSlot
    ) : (
      <>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
            {labels.tabGlossaryRules}
          </h3>
          <span className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 font-mono text-[11px]">
            {pendingGlossaryCandidatesCount}
          </span>
        </div>
        <p className="text-xs text-[var(--orcia-text-secondary)]">
          {labels.inviolableEnterpriseLockNotice}
        </p>
        {activeWaiversCount === 0 && (
          <p className="text-xs text-[var(--orcia-text-secondary)]">
            {labels.emptyGlossaryRulesText ?? labels.waiverSectionTitle}
          </p>
        )}
        <WaiversAndRebasePanel {...sharedWaiverProps} />
      </>
    )}
  </div>
);
