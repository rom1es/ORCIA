import React, { useState } from "react";
import { OrciaDataCard } from "../OrciaDataCard";
import { OrciaPageHeader } from "../OrciaPageHeader";
import { OrciaTabStrip, type OrciaTabStripItem } from "../OrciaTabStrip";
import { FinopsBudgetOverrideModal } from "./FinopsBudgetOverrideModal";
import { FinopsBudgetPolicyModal } from "./FinopsBudgetPolicyModal";
import type {
  FinopsDashboardLabels,
  FinopsTabKey,
  RemoteServiceRowData,
  UpdateConnectorQuotaInput,
} from "./FinopsDashboardTypes";
import { FinopsHumanMasteryTab, type FinopsHumanMasteryTabProps } from "./FinopsHumanMasteryTab";
import { FinopsKpiStrip } from "./FinopsKpiStrip";
import {
  FinopsProcessAndTiersTab,
  type FinopsProcessRowData,
  type FinopsTierRowData,
} from "./FinopsProcessAndTiersTab";
import { FinopsRemoteMcpServicesTab } from "./FinopsRemoteMcpServicesTab";

export type { FinopsDashboardLabels, FinopsTabKey };

export interface FinopsGovernanceDashboardViewProps {
  readonly scopeType: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
  readonly scopeId?: string | null;
  readonly scopeIdsByLevel?: Partial<Record<"BU" | "TEAM" | "WORKSPACE", string | null>>;
  readonly allowedScopes?: readonly ("WORKSPACE" | "TEAM" | "BU" | "GLOBAL")[];
  readonly allowedModalScopes?: readonly ("GLOBAL" | "BU" | "TEAM" | "WORKSPACE")[];
  readonly error?: string | null;
  readonly alertSlot?: React.ReactNode;
  readonly onScopeChange?: (scope: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE") => void;
  readonly totalRuns: number;
  readonly totalCostEur: number;
  readonly verifiedInternalCostEur: number;
  readonly reportedExternalCostEur: number;
  readonly totalLlmTokens: number;
  readonly internalTokens: number;
  readonly remoteTokens: number;
  readonly totalExternalCalls: number;
  readonly externalUnitsBreakdown?: Record<string, number>;
  readonly cacheSavingsEur?: number;
  readonly activeCircuitBreakersCount?: number;
  readonly pausedRunsCount?: number;
  readonly processes: readonly FinopsProcessRowData[];
  readonly tiers: readonly FinopsTierRowData[];
  readonly remoteServices?: readonly RemoteServiceRowData[];
  readonly labels: FinopsDashboardLabels;
  readonly headerActions?: React.ReactNode;
  readonly onOpenHelpSection?: (sectionId: string) => void;
  readonly onSaveBudget?: (
    scopeType: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE",
    scopeId: string | null,
    monthlyBudgetUsd: number,
    warningThresholdPct: number,
    hardStopPct: number,
  ) => void;
  readonly onSubmitOverride?: (runId: string, amountUsd: number, reason: string) => void;
  readonly cognitiveData?: FinopsHumanMasteryTabProps | null;
  readonly onApplyRecommendation?: (recommendationId: string) => void;
  readonly onReviewPostHocSample?: (
    runId: string,
    decision: "VALIDATED" | "INVALIDATED_ROLLED_BACK",
  ) => void;
  readonly onUpdateConnectorQuota?: (input: UpdateConnectorQuotaInput) => void;
  readonly onResetConnectorCircuit?: (connectorKey: string) => void;
}

export function FinopsGovernanceDashboardView({
  scopeType,
  scopeId = null,
  scopeIdsByLevel,
  allowedScopes,
  allowedModalScopes,
  error = null,
  alertSlot,
  onScopeChange,
  totalRuns,
  totalCostEur,
  verifiedInternalCostEur,
  reportedExternalCostEur,
  totalLlmTokens,
  internalTokens,
  remoteTokens,
  totalExternalCalls,
  externalUnitsBreakdown,
  cacheSavingsEur = 0,
  activeCircuitBreakersCount = 0,
  pausedRunsCount = 0,
  processes,
  tiers,
  remoteServices = [],
  labels,
  headerActions,
  onOpenHelpSection,
  onSaveBudget,
  onSubmitOverride,
  cognitiveData,
  onApplyRecommendation,
  onReviewPostHocSample,
  onUpdateConnectorQuota,
  onResetConnectorCircuit,
}: FinopsGovernanceDashboardViewProps): React.ReactElement {
  const [activeTab, setActiveTab] = useState<FinopsTabKey>("processes");
  const [isBudgetModalOpen, setIsBudgetModalOpen] = useState(false);
  const [overrideModalRun, setOverrideModalRun] = useState<{ runId: string; title: string } | null>(null);
  const hasError = error !== null && error !== undefined;
  const effectivePillScope = scopeType === "BU" ? "TEAM" : scopeType;
  const allScopePills = [
    ["WORKSPACE", "finops-scope-workspace", labels.scopeSelector.currentWorkspace],
    ["TEAM", "finops-scope-team", labels.scopeSelector.currentTeam],
    ["GLOBAL", "finops-scope-global", labels.scopeSelector.entirePlatform],
  ] as const;
  const visibleScopePills = allowedScopes
    ? allScopePills.filter(([sKey]) =>
        sKey === "TEAM"
          ? allowedScopes.includes("TEAM") || allowedScopes.includes("BU")
          : allowedScopes.includes(sKey),
      )
    : allScopePills;

  const tabs: readonly OrciaTabStripItem<FinopsTabKey>[] = [
    { key: "processes", label: labels.tabs.processes, testId: "finops-tab-processes" },
    { key: "tiers", label: labels.tabs.tiers, testId: "finops-tab-tiers" },
    { key: "externalServices", label: labels.tabs.externalServices, testId: "finops-tab-external-services" },
    { key: "cognitiveGovernance", label: labels.tabs.cognitiveGovernance, testId: "finops-tab-cognitive-governance" },
  ];

  const scopeSelectorBar = (
    <div
      className="finops-scope-pills flex flex-wrap items-center gap-1.5"
      role="tablist"
      aria-orientation="horizontal"
      aria-label={labels.scopeSelector.currentWorkspace}
      data-testid="finops-scope-pills"
    >
      {visibleScopePills.map(([sKey, testId, label]) => {
        const selected = effectivePillScope === sKey;
        return (
          <button
            key={sKey}
            type="button"
            role="tab"
            aria-selected={selected}
            data-testid={testId}
            className="orcia-ds-filter-pill"
            onClick={() => onScopeChange?.(sKey)}
          >
            {label}
          </button>
        );
      })}
    </div>
  );

  return (
    <div
      className="finops-governance-dashboard orcia-ds-page"
      data-testid="finops-governance-dashboard"
    >
      <OrciaPageHeader
        testId="finops-page"
        icon="finops"
        title={labels.pageTitle}
        subtitle={labels.pageSubtitle}
        secondaryActions={headerActions}
        primaryAction={
          <button
            type="button"
            data-testid="finops-configure-budget-btn"
            className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm orcia-ds-nowrap"
            onClick={() => setIsBudgetModalOpen(true)}
          >
            {labels.configureBudgetButton}
          </button>
        }
        tabs={
          <OrciaTabStrip<FinopsTabKey>
            testId="finops-tab-strip"
            ariaLabel={labels.tabsAriaLabel ?? labels.pageTitle}
            variant="underline"
            tabs={tabs}
            activeTabId={activeTab}
            onSelectTab={setActiveTab}
          />
        }
        scopeBar={scopeSelectorBar}
        alertSlot={alertSlot}
      />

      <FinopsKpiStrip
        totalRuns={totalRuns}
        totalCostEur={totalCostEur}
        verifiedInternalCostEur={verifiedInternalCostEur}
        reportedExternalCostEur={reportedExternalCostEur}
        totalLlmTokens={totalLlmTokens}
        internalTokens={internalTokens}
        remoteTokens={remoteTokens}
        totalExternalCalls={totalExternalCalls}
        externalUnitsBreakdown={externalUnitsBreakdown}
        cacheSavingsEur={cacheSavingsEur}
        activeCircuitBreakersCount={activeCircuitBreakersCount}
        pausedRunsCount={pausedRunsCount}
        suppressEmptyState={hasError}
        emptyStateText={labels.emptyStateText}
        labels={labels.kpis}
      />

      <div className="finops-tabs-container">
        {activeTab === "processes" ? (
          <FinopsProcessAndTiersTab
            activeSubTab="processes"
            processes={processes}
            tiers={tiers}
            labels={labels}
            onOpenOverrideModal={(runId, title) => setOverrideModalRun({ runId, title })}
          />
        ) : activeTab === "tiers" ? (
          <FinopsProcessAndTiersTab
            activeSubTab="tiers"
            processes={processes}
            tiers={tiers}
            labels={labels}
          />
        ) : activeTab === "externalServices" ? (
          labels.remoteServices ? (
            <FinopsRemoteMcpServicesTab
              services={remoteServices}
              labels={labels.remoteServices}
              onUpdateConnectorQuota={onUpdateConnectorQuota}
              onResetConnectorCircuit={onResetConnectorCircuit}
              onOpenHelpSection={onOpenHelpSection}
            />
          ) : hasError ? null : (
            <OrciaDataCard testId="finops-services-placeholder">
              <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "13px" }}>
                {labels.emptyStateText}
              </p>
            </OrciaDataCard>
          )
        ) : cognitiveData ? (
          <FinopsHumanMasteryTab
            {...cognitiveData}
            onApplyRecommendation={onApplyRecommendation}
            onReviewPostHocSample={onReviewPostHocSample}
            onOpenHelpSection={onOpenHelpSection}
          />
        ) : hasError ? null : (
          <OrciaDataCard testId="finops-governance-placeholder">
            <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: "13px" }}>
              {labels.emptyStateText}
            </p>
          </OrciaDataCard>
        )}
      </div>

      <FinopsBudgetPolicyModal
        open={isBudgetModalOpen}
        onOpenChange={setIsBudgetModalOpen}
        currentScopeType={scopeType}
        currentScopeId={scopeId}
        scopeIdsByLevel={scopeIdsByLevel}
        allowedScopes={allowedModalScopes}
        labels={labels.modals}
        onSaveBudget={onSaveBudget}
      />

      <FinopsBudgetOverrideModal
        open={overrideModalRun !== null}
        onOpenChange={(open) => {
          if (!open) setOverrideModalRun(null);
        }}
        runId={overrideModalRun?.runId}
        workflowTitle={overrideModalRun?.title}
        labels={labels.modals}
        onSubmitOverride={onSubmitOverride}
      />
    </div>
  );
}
