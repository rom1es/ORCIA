import type { HumanMasteryLabels } from "./FinopsHumanMasteryTab";
import type { FinopsKpiStripLabels } from "./FinopsKpiStrip";

export type FinopsTabKey = "processes" | "tiers" | "externalServices" | "cognitiveGovernance";

export type UiValuationMode = "NATIVE_TELEMETRY" | "FIXED_SCALE" | "VOLUMETRIC_ONLY";
export type UiCircuitState = "CLOSED" | "CIRCUIT_OPEN" | "HALF_OPEN";

export interface RemoteServiceRowData {
  readonly connectorKey: string;
  readonly displayName: string;
  readonly serviceKind: string;
  readonly scopeType: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
  readonly scopeId?: string | null;
  readonly valuationMode: UiValuationMode;
  readonly maxReportedCostPerCallEur: number;
  readonly fixedCostPerCallEur: number;
  readonly unitTariffEur: number;
  readonly defaultUnitName?: string | null;
  readonly maxDailyCalls?: number | null;
  readonly maxMonthlyCostEur?: number | null;
  readonly dailyCallsCount: number;
  readonly avgLatencyMs: number;
  readonly totalRemoteTokens: number;
  readonly totalBusinessUnits: number;
  readonly consolidatedCostEur: number;
  readonly quotaUsedPct: number;
  readonly circuitState: UiCircuitState;
  readonly anomalyCount: number;
  readonly lastTrippedReason?: string | null;
}

export interface UpdateConnectorQuotaInput {
  readonly connectorKey: string;
  readonly valuationMode: UiValuationMode;
  readonly maxReportedCostPerCallEur: number;
  readonly fixedCostPerCallEur: number;
  readonly unitTariffEur: number;
  readonly defaultUnitName: string | null;
  readonly maxDailyCalls: number | null;
  readonly maxMonthlyCostEur: number | null;
}

export interface RemoteServicesModalLabels {
  readonly title: string;
  readonly description: string;
  readonly valuationModeLabel: string;
  readonly maxPerCallLabel: string;
  readonly fixedCallCostLabel: string;
  readonly unitTariffLabel: string;
  readonly unitNameLabel: string;
  readonly maxDailyCallsLabel: string;
  readonly maxMonthlyCostLabel: string;
  readonly saveButton: string;
  readonly cancelButton: string;
}

export interface RemoteServicesTabLabels {
  readonly tabTitle: string;
  readonly tabSubtitle: string;
  readonly infoButtonAriaLabel: string;
  readonly emptyStateText: string;
  readonly columns: {
    readonly serviceCol: string;
    readonly typeCol: string;
    readonly callsAndLatencyCol: string;
    readonly remoteTokensCol: string;
    readonly businessUnitsCol: string;
    readonly valuationModeCol: string;
    readonly consolidatedCostCol: string;
    readonly quotaCol: string;
    readonly circuitStatusCol: string;
    readonly actionsCol: string;
  };
  readonly valuationModes: {
    readonly nativeTelemetry: string;
    readonly fixedScale: string;
    readonly volumetricOnly: string;
  };
  readonly circuitStates: {
    readonly closed: string;
    readonly open: string;
    readonly halfOpen: string;
  };
  readonly serviceKinds: {
    readonly mcpServer: string;
    readonly a2aAgent: string;
    readonly openapiRest: string;
    readonly connector: string;
  };
  readonly editQuotaButton: string;
  readonly resetCircuitButton: string;
  readonly callsSuffix: string;
  readonly unlimitedLabel: string;
  readonly durationMsUnit?: string;
  readonly quotaModal: RemoteServicesModalLabels;
}

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
  tabsAriaLabel?: string;
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
    emptyProcessesText?: string;
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
    emptyTiersText?: string;
    tierLabels?: Readonly<Record<string, string>>;
    effortLabels?: Readonly<Record<string, string>>;
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
  remoteServices?: RemoteServicesTabLabels;
  humanMastery?: HumanMasteryLabels;
}
