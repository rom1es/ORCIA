import React, { useState } from "react";
import { ContextualInfoTriggerButton } from "../../components/ContextualInfoTriggerButton";
import { OrciaTabBar, type OrciaTabItem } from "../RadixDesignSystemPrimitives";
import { FinopsBudgetOverrideModal } from "./FinopsBudgetOverrideModal";
import { FinopsBudgetPolicyModal } from "./FinopsBudgetPolicyModal";
import { FinopsKpiStrip, type FinopsKpiStripLabels } from "./FinopsKpiStrip";
import {
  FinopsProcessAndTiersTab,
  type FinopsProcessRowData,
  type FinopsTierRowData,
} from "./FinopsProcessAndTiersTab";

export type FinopsTabKey = "processes" | "tiers" | "externalServices" | "cognitiveGovernance";

export interface FinopsDashboardLabels {
  pageTitle: string;
  pageSubtitle: string;
  infoButtonAriaLabel: string;
  scopeSelector: {
    currentWorkspace: string;
    currentTeam: string;
    entirePlatform: string;
  };
  configureBudgetButton: string;
  emptyStateText: string;
  kpis: FinopsKpiStripLabels;
  tabs: {
    processes: string;
    tiers: string;
    externalServices: string;
    cognitiveGovernance: string;
  };
  processesTable: {
    title: string;
    workflowCol: string;
    runsCol: string;
    setupCostCol: string;
    runCostCol: string;
    humanTimeCol: string;
    totalCostCol: string;
    ttmCol: string;
    statusCol: string;
    actionsCol: string;
    pausedBadgeBudget: string;
    pausedBadgeRetries: string;
    activeBadge: string;
    overrideButton: string;
  };
  tiersTable: {
    title: string;
    tierCol: string;
    effortCol: string;
    invocationsCol: string;
    inputTokensCol: string;
    outputTokensCol: string;
    totalTokensCol: string;
    costCol: string;
  };
  modals: {
    budgetTitle: string;
    budgetDescription: string;
    monthlyLimitLabel: string;
    warningThresholdLabel: string;
    hardStopLabel: string;
    scopeLabel: string;
    scopeGlobalLabel?: string;
    scopeBuLabel?: string;
    scopeTeamLabel?: string;
    scopeWorkspaceLabel?: string;
    saveButton: string;
    cancelButton: string;
    overrideTitle: string;
    overrideDescription: string;
    overrideAmountLabel: string;
    overrideReasonLabel: string;
    overrideSubmitButton: string;
  };
}

export interface FinopsGovernanceDashboardViewProps {
  readonly scopeType: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
  readonly onScopeChange?: (scope: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE") => void;
  readonly totalRuns: number;
  readonly totalCostEur: number;
  readonly verifiedInternalCostEur: number;
  readonly reportedExternalCostEur: number;
  readonly totalLlmTokens: number;
  readonly internalTokens: number;
  readonly remoteTokens: number;
  readonly totalExternalCalls: number;
  readonly cacheSavingsEur?: number;
  readonly activeCircuitBreakersCount?: number;
  readonly pausedRunsCount?: number;
  readonly processes: readonly FinopsProcessRowData[];
  readonly tiers: readonly FinopsTierRowData[];
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
}

export function FinopsGovernanceDashboardView({
  scopeType,
  onScopeChange,
  totalRuns,
  totalCostEur,
  verifiedInternalCostEur,
  reportedExternalCostEur,
  totalLlmTokens,
  internalTokens,
  remoteTokens,
  totalExternalCalls,
  cacheSavingsEur = 0,
  activeCircuitBreakersCount = 0,
  pausedRunsCount = 0,
  processes,
  tiers,
  labels,
  onOpenHelpSection,
  onSaveBudget,
  onSubmitOverride,
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
      {/* 1. En-tête sobre Direction C */}
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
          {/* Sélecteur de portée en 3 pilules */}
          <div
            className="finops-scope-pills"
            data-testid="finops-scope-pills"
            style={{
              display: "inline-flex",
              borderRadius: "6px",
              background: "var(--color-surface-muted)",
              padding: "2px",
            }}
          >
            <button
              type="button"
              data-testid="finops-scope-workspace"
              className={`orcia-ds-tab ${scopeType === "WORKSPACE" ? "active" : ""}`}
              style={{
                fontSize: "12px",
                padding: "4px 10px",
                borderRadius: "4px",
                background: scopeType === "WORKSPACE" ? "var(--color-surface-card)" : "transparent",
              }}
              onClick={() => onScopeChange?.("WORKSPACE")}
            >
              {labels.scopeSelector.currentWorkspace}
            </button>
            <button
              type="button"
              data-testid="finops-scope-team"
              className={`orcia-ds-tab ${scopeType === "TEAM" ? "active" : ""}`}
              style={{
                fontSize: "12px",
                padding: "4px 10px",
                borderRadius: "4px",
                background: scopeType === "TEAM" ? "var(--color-surface-card)" : "transparent",
              }}
              onClick={() => onScopeChange?.("TEAM")}
            >
              {labels.scopeSelector.currentTeam}
            </button>
            <button
              type="button"
              data-testid="finops-scope-global"
              className={`orcia-ds-tab ${scopeType === "GLOBAL" ? "active" : ""}`}
              style={{
                fontSize: "12px",
                padding: "4px 10px",
                borderRadius: "4px",
                background: scopeType === "GLOBAL" ? "var(--color-surface-card)" : "transparent",
              }}
              onClick={() => onScopeChange?.("GLOBAL")}
            >
              {labels.scopeSelector.entirePlatform}
            </button>
          </div>

          {/* Bouton de configuration de plafond */}
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

      {/* 2. Barre KPI ou État vide */}
      <FinopsKpiStrip
        totalRuns={totalRuns}
        totalCostEur={totalCostEur}
        verifiedInternalCostEur={verifiedInternalCostEur}
        reportedExternalCostEur={reportedExternalCostEur}
        totalLlmTokens={totalLlmTokens}
        internalTokens={internalTokens}
        remoteTokens={remoteTokens}
        totalExternalCalls={totalExternalCalls}
        cacheSavingsEur={cacheSavingsEur}
        activeCircuitBreakersCount={activeCircuitBreakersCount}
        pausedRunsCount={pausedRunsCount}
        emptyStateText={labels.emptyStateText}
        labels={labels.kpis}
      />

      {/* 3. Onglets de gouvernance */}
      <div className="finops-tabs-container">
        <OrciaTabBar<FinopsTabKey>
          tabs={tabs}
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          ariaLabel="Onglets gouvernance FinOps"
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
            externalServices: (
              <div
                className="orcia-bento-card"
                data-testid="finops-services-placeholder"
                style={{ padding: "24px", color: "var(--color-text-muted)", fontSize: "13px" }}
              >
                <p style={{ margin: 0 }}>
                  La télémétrie multi-métriques des services et serveurs distants sera activée lors de la prochaine étape de livraison.
                </p>
              </div>
            ),
            cognitiveGovernance: (
              <div
                className="orcia-bento-card"
                data-testid="finops-governance-placeholder"
                style={{ padding: "24px", color: "var(--color-text-muted)", fontSize: "13px" }}
              >
                <p style={{ margin: 0 }}>
                  Le tableau de bord d'impact cognitif et de réversibilité humaine sera connecté lors de la prochaine étape de livraison.
                </p>
              </div>
            ),
          }}
        />
      </div>

      {/* Modale de réglage des plafonds */}
      <FinopsBudgetPolicyModal
        open={isBudgetModalOpen}
        onOpenChange={setIsBudgetModalOpen}
        currentScopeType={scopeType}
        labels={labels.modals}
        onSaveBudget={onSaveBudget}
      />

      {/* Modale de rallonge budgétaire */}
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
