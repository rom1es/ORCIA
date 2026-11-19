import React, { useState } from "react";
import { ContextualInfoTriggerButton } from "../../components/ContextualInfoTriggerButton";
import { OrciaTabBar, type OrciaTabItem } from "../RadixDesignSystemPrimitives";
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

  const tabs: readonly OrciaTabItem<FinopsTabKey>[] = [
    { key: "processes", label: labels.tabs.processes, testId: "finops-tab-processes" },
    { key: "tiers", label: labels.tabs.tiers, testId: "finops-tab-tiers" },
    { key: "externalServices", label: labels.tabs.externalServices, testId: "finops-tab-external-services" },
    { key: "cognitiveGovernance", label: labels.tabs.cognitiveGovernance, testId: "finops-tab-cognitive-governance" },
  ];

  return (
    <div
      className="finops-governance-dashboard"
      data-testid="finops-governance-dashboard"
      style={{ display: "flex", flexDirection: "column", gap: "20px" }}
    >
      <div
        className="finops-dashboard-header"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div style={{ maxWidth: "680px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h1
              data-testid="finops-page-title"
              style={{ fontSize: "20px", fontWeight: 700, margin: 0, color: "var(--color-text-primary)" }}
            >
              {labels.pageTitle}
            </h1>
            <ContextualInfoTriggerButton
              sectionId="finops-overview"
              label={labels.infoButtonAriaLabel}
              onOpenHelpSection={onOpenHelpSection}
            />
          </div>
          <p
            style={{
              fontSize: "13px",
              color: "var(--color-text-muted)",
              margin: "6px 0 0 0",
              lineHeight: "1.5",
            }}
          >
            {labels.pageSubtitle}
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
          <div
            className="finops-scope-pills"
            data-testid="finops-scope-pills"
            style={{ display: "inline-flex", borderRadius: "6px", background: "var(--color-surface-muted)", padding: "2px" }}
          >
            {(
              [
                ["WORKSPACE", "finops-scope-workspace", labels.scopeSelector.currentWorkspace],
                ["TEAM", "finops-scope-team", labels.scopeSelector.currentTeam],
                ["GLOBAL", "finops-scope-global", labels.scopeSelector.entirePlatform],
              ] as const
            ).map(([sKey, testId, label]) => (
              <button
                key={sKey}
                type="button"
                data-testid={testId}
                className={`orcia-ds-tab ${scopeType === sKey ? "active" : ""}`}
                style={{
                  fontSize: "12px",
                  padding: "4px 10px",
                  borderRadius: "4px",
                  background: scopeType === sKey ? "var(--color-surface-card)" : "transparent",
                }}
                onClick={() => onScopeChange?.(sKey)}
              >
                {label}
              </button>
            ))}
          </div>

          <button
            type="button"
            data-testid="finops-configure-budget-btn"
            className="orcia-ds-btn orcia-ds-btn-primary"
            onClick={() => setIsBudgetModalOpen(true)}
          >
            {labels.configureBudgetButton}
          </button>
        </div>
      </div>

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
        emptyStateText={labels.emptyStateText}
        labels={labels.kpis}
      />

      <div className="finops-tabs-container">
        <OrciaTabBar<FinopsTabKey>
          tabs={tabs}
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          ariaLabel="Onglets gouvernance FinOps"
          tabsClassName="flex-nowrap overflow-x-auto"
          panels={{
            processes: (
              <FinopsProcessAndTiersTab
                activeSubTab="processes"
                processes={processes}
                tiers={tiers}
                labels={labels}
                onOpenOverrideModal={(runId, title) => setOverrideModalRun({ runId, title })}
              />
            ),
            tiers: (
              <FinopsProcessAndTiersTab
                activeSubTab="tiers"
                processes={processes}
                tiers={tiers}
                labels={labels}
              />
            ),
            externalServices: labels.remoteServices ? (
              <FinopsRemoteMcpServicesTab
                services={remoteServices}
                labels={labels.remoteServices}
                onUpdateConnectorQuota={onUpdateConnectorQuota}
                onResetConnectorCircuit={onResetConnectorCircuit}
                onOpenHelpSection={onOpenHelpSection}
              />
            ) : (
              <div
                className="orcia-bento-card"
                data-testid="finops-services-placeholder"
                style={{ padding: "24px", color: "var(--color-text-muted)", fontSize: "13px" }}
              >
                <p style={{ margin: 0 }}>{labels.emptyStateText}</p>
              </div>
            ),
            cognitiveGovernance: cognitiveData ? (
              <FinopsHumanMasteryTab
                {...cognitiveData}
                onApplyRecommendation={onApplyRecommendation}
                onReviewPostHocSample={onReviewPostHocSample}
                onOpenHelpSection={onOpenHelpSection}
              />
            ) : (
              <div
                className="orcia-bento-card"
                data-testid="finops-governance-placeholder"
                style={{ padding: "24px", color: "var(--color-text-muted)", fontSize: "13px" }}
              >
                <p style={{ margin: 0 }}>{labels.emptyStateText}</p>
              </div>
            ),
          }}
        />
      </div>

      <FinopsBudgetPolicyModal
        open={isBudgetModalOpen}
        onOpenChange={setIsBudgetModalOpen}
        currentScopeType={scopeType}
        currentScopeId={scopeId}
        scopeIdsByLevel={scopeIdsByLevel}
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
