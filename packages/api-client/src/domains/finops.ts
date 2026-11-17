import type { components } from "../generated/schema";
import { buildPersonaQuery, type createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export type FinopsBreakdownResponse = components["schemas"]["FinopsBreakdownResponse"];
export type UpdateScopeBudgetRequest = components["schemas"]["UpdateScopeBudgetRequest"];
export type ScopeBudgetResponse = components["schemas"]["ScopeBudgetResponse"];
export type SetWorkflowBaselineRequest = components["schemas"]["SetWorkflowBaselineRequest"];
export type WorkflowBaselineResponse = components["schemas"]["WorkflowBaselineResponse"];
export type BudgetOverrideRequest = components["schemas"]["BudgetOverrideRequest"];
export type BudgetOverrideResponse = components["schemas"]["BudgetOverrideResponse"];
export type CognitiveImpactDashboardResponse =
  components["schemas"]["CognitiveImpactDashboardResponse"];
export type ApplyRecommendationResponse =
  components["schemas"]["ApplyRecommendationResponse"];

export function createFinopsDomainClient(requestJson: RequestJsonFn) {
  return {
    getFinopsDashboard(options?: {
      scopeType?: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
      scopeId?: string | null;
      personaKey?: string;
    }): Promise<FinopsBreakdownResponse> {
      const params = new URLSearchParams();
      if (options?.scopeType) params.set("scope_type", options.scopeType);
      if (options?.scopeId) params.set("scope_id", options.scopeId);
      if (options?.personaKey) params.set("persona_key", options.personaKey);
      const qs = params.toString();
      return requestJson<FinopsBreakdownResponse>(
        `/api/v1/finops/dashboard${qs ? `?${qs}` : ""}`,
      );
    },

    updateScopeBudget(
      payload: UpdateScopeBudgetRequest,
      personaKey?: string,
    ): Promise<ScopeBudgetResponse> {
      return requestJson<ScopeBudgetResponse>(
        `/api/v1/finops/budgets${buildPersonaQuery(personaKey)}`,
        "PUT",
        payload,
      );
    },

    setWorkflowBaseline(
      payload: SetWorkflowBaselineRequest,
      personaKey?: string,
    ): Promise<WorkflowBaselineResponse> {
      return requestJson<WorkflowBaselineResponse>(
        `/api/v1/finops/baselines${buildPersonaQuery(personaKey)}`,
        "PUT",
        payload,
      );
    },

    applyBudgetOverride(
      runId: string,
      payload: BudgetOverrideRequest,
      personaKey?: string,
    ): Promise<BudgetOverrideResponse> {
      return requestJson<BudgetOverrideResponse>(
        `/api/v1/runs/${encodeURIComponent(runId)}/budget-override${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },

    getCognitiveImpact(options?: {
      scopeType?: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
      scopeId?: string | null;
      timeWindow?: "7D" | "30D" | "90D" | "ALL";
      personaKey?: string;
    }): Promise<CognitiveImpactDashboardResponse> {
      const params = new URLSearchParams();
      if (options?.scopeType) params.set("scope_type", options.scopeType);
      if (options?.scopeId) params.set("scope_id", options.scopeId);
      if (options?.timeWindow) params.set("time_window", options.timeWindow);
      if (options?.personaKey) params.set("persona_key", options.personaKey);
      const qs = params.toString();
      return requestJson<CognitiveImpactDashboardResponse>(
        `/api/v1/finops/cognitive-impact${qs ? `?${qs}` : ""}`,
      );
    },

    applyGatePolicyRecommendation(
      recommendationId: string,
      personaKey?: string,
    ): Promise<ApplyRecommendationResponse> {
      return requestJson<ApplyRecommendationResponse>(
        `/api/v1/finops/gates/policy-recommendation/${encodeURIComponent(recommendationId)}/apply${buildPersonaQuery(personaKey)}`,
        "POST",
      );
    },
  };
}
