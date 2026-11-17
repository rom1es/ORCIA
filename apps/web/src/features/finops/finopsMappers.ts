import type {
  CognitiveImpactDashboardResponse,
  FinopsBreakdownResponse,
  RemoteServicesListResponse,
} from "@orcia/api-client";
import type {
  FinopsHumanMasteryTabProps,
  FinopsProcessRowData,
  FinopsTierRowData,
  HumanMasteryLabels,
  RemoteServiceRowData,
} from "@orcia/ui";

export function mapProcessesRows(
  dashboardData: FinopsBreakdownResponse | null,
): readonly FinopsProcessRowData[] {
  if (!dashboardData?.processes) return [];
  return dashboardData.processes.map((p) => ({
    workflowId: p.workflow_id,
    workflowTitle: p.workflow_title,
    runsCount: p.runs_count,
    amortizedSetupCostEur: p.amortized_setup_cost_eur,
    runCostEur: p.run_cost_eur,
    humanTimeCostEur: p.human_time_cost_eur,
    totalCostEur: p.total_cost_eur,
    ttmReductionPct: p.ttm_reduction_pct,
    activeBudgetOverride: p.active_budget_override,
    pausedRunsCount: p.paused_runs_count,
    pausedReason: p.paused_runs_count && p.paused_runs_count > 0 ? "BUDGET" : null,
    samplePausedRunId: undefined,
  }));
}

export function mapTiersRows(
  dashboardData: FinopsBreakdownResponse | null,
): readonly FinopsTierRowData[] {
  if (!dashboardData?.tiers) return [];
  return dashboardData.tiers.map((t) => ({
    inferenceTier: t.inference_tier,
    effort: t.effort,
    invocationsCount: t.invocations_count,
    inputTokens: t.input_tokens,
    outputTokens: t.output_tokens,
    totalTokens: t.total_tokens,
    costEur: t.cost_eur,
  }));
}

export function mapCognitiveTabProps(
  cognitiveData: CognitiveImpactDashboardResponse | null,
  labels: HumanMasteryLabels,
): FinopsHumanMasteryTabProps | null {
  if (!cognitiveData) return null;
  return {
    activeFramingRatio: cognitiveData.active_framing_ratio,
    activeFramingAlert: cognitiveData.active_framing_alert,
    quickPassRate: cognitiveData.quick_pass_rate,
    quickPassAlert: cognitiveData.quick_pass_alert,
    architectureDeviationIndex: cognitiveData.architecture_deviation_index,
    architectureDeviationAlert: cognitiveData.architecture_deviation_alert,
    uncoveredDeviationsCount: cognitiveData.uncovered_deviations_count,
    workflows: (cognitiveData.workflow_breakdowns ?? []).map((w) => ({
      workflowId: w.workflow_id,
      workflowTitle: w.workflow_title,
      criticality: w.criticality,
      humanGatesCount: w.human_gates_count,
      humanPassesCount: w.human_passes_count,
      quickPassesCount: w.quick_passes_count,
      quickPassRate: w.quick_pass_rate,
      medianReviewDurationMs: w.median_review_duration_ms,
      uncoveredDriftCount: w.uncovered_drift_count,
      hasAlert: w.has_alert,
    })),
    recommendations: (cognitiveData.recommendations ?? []).map((r) => ({
      id: r.id,
      workflowId: r.workflow_id,
      workflowTitle: r.workflow_title,
      recommendationType: r.recommendation_type,
      title: r.title,
      description: r.description,
      actionLabel: r.action_label,
      suggestedPolicy: r.suggested_policy,
      status: (r.status as "PROPOSED" | "APPLIED" | "DISMISSED") || "PROPOSED",
      appliedAt: r.applied_at,
    })),
    labels,
  };
}

export function mapRemoteServicesRows(
  remoteData: RemoteServicesListResponse | null,
): readonly RemoteServiceRowData[] {
  if (!remoteData?.services) return [];
  return remoteData.services.map((s) => ({
    connectorKey: s.connector_key,
    displayName: s.display_name,
    serviceKind: s.service_kind,
    scopeType: s.scope_type,
    scopeId: s.scope_id,
    valuationMode: s.valuation_mode,
    maxReportedCostPerCallEur: s.max_reported_cost_per_call_eur ?? 5,
    fixedCostPerCallEur: s.fixed_cost_per_call_eur ?? 0,
    unitTariffEur: s.unit_tariff_eur ?? 0,
    defaultUnitName: s.default_unit_name,
    maxDailyCalls: s.max_daily_calls,
    maxMonthlyCostEur: s.max_monthly_cost_eur,
    dailyCallsCount: s.daily_calls_count ?? 0,
    avgLatencyMs: s.avg_latency_ms ?? 0,
    totalRemoteTokens: s.total_remote_tokens ?? 0,
    totalBusinessUnits: s.total_business_units ?? 0,
    consolidatedCostEur: s.consolidated_cost_eur ?? 0,
    quotaUsedPct: s.quota_used_pct ?? 0,
    circuitState: s.circuit_state ?? "CLOSED",
    anomalyCount: s.anomaly_count ?? 0,
    lastTrippedReason: s.last_tripped_reason,
  }));
}
