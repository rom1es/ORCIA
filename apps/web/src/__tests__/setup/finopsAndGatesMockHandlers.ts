import { jsonResponse } from "./mockBackendState";

export function handleFinopsAndGatesRoute(params: {
  path: string;
  method: string;
  body: Record<string, unknown>;
}): Response | null {
  const { path, method, body } = params;

  if (path === "/api/v1/finops/dashboard" && method === "GET") {
    return jsonResponse({
      overview: {
        total_setup_cost_eur: 0,
        total_run_cost_eur: 0,
        total_human_cost_eur: 0,
        total_cost_eur: 0,
        avg_ttm_reduction_pct: 0,
        total_runs_count: 0,
        paused_runs_count: 0,
      },
      processes: [],
      tiers: [],
      scope_budgets: [],
      baselines: [],
      trace_id: "0195f000000070008000000000000601",
    });
  }

  if (path === "/api/v1/finops/remote-services" && method === "GET") {
    return jsonResponse({
      services: [],
      total_external_calls: 0,
      total_remote_tokens: 0,
      open_circuits_count: 0,
      trace_id: "0195f000000070008000000000000602",
    });
  }

  if (path === "/api/v1/finops/cognitive-impact" && method === "GET") {
    return jsonResponse({
      scope_type: "GLOBAL",
      scope_id: null,
      active_framing_ratio: 0.85,
      active_framing_target: 0.4,
      active_framing_alert: false,
      quick_pass_rate: 0.02,
      quick_pass_threshold: 0.05,
      quick_pass_alert: false,
      architecture_deviation_index: 0,
      architecture_deviation_target: 0,
      architecture_deviation_alert: false,
      pattern_drift_index: 0,
      pattern_drift_alert: false,
      total_human_hours: 1,
      active_framing_hours: 0.8,
      review_hours: 0.2,
      uncovered_deviations_count: 0,
      workflow_breakdowns: [],
      recommendations: [],
      autonomous_governance: null,
      trace_id: "0195f000000070008000000000000603",
    });
  }

  if (path === "/api/v1/jira/actions/stage" && method === "POST") {
    return jsonResponse({
      staged_action: {
        action_id: "jira-stage-1",
        workspace_id: String(body.workspace_id ?? "0192c4e0-0000-7000-8000-000000000201"),
        run_id: String(body.run_id ?? "0195f000-0000-7000-8000-000000000701"),
        step_execution_id: String(body.step_execution_id ?? "0195f000-0000-7000-8000-000000000801"),
        project_alias: String(body.project_alias ?? "jira:product"),
        action_type: String(body.action_type ?? "transition_issue"),
        issue_key: String(body.issue_key ?? "PAYBUILD-101"),
        target_transition: String(body.target_transition ?? "Submit for Review"),
        summary: String(body.summary ?? ""),
        status: "STAGED",
        available_transitions: ["Submit for Review", "Approve"],
      },
      draft_artifact_jsonb: {},
      trace_id: "0195f000000070008000000000000604",
    });
  }

  return null;
}
