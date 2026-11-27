import { buildOpenApiMockResponse } from "./generatedOpenApiMocks";

export function handleFinopsAndGatesRoute(params: {
  path: string;
  method: string;
  body: Record<string, unknown>;
}): Response | null {
  const { path, method, body } = params;

  if (path === "/api/v1/finops/dashboard" && method === "GET") {
    return buildOpenApiMockResponse("GET /api/v1/finops/dashboard", {
      trace_id: "0195f000000070008000000000000601",
    });
  }

  if (path === "/api/v1/finops/remote-services" && method === "GET") {
    return buildOpenApiMockResponse("GET /api/v1/finops/remote-services", {
      trace_id: "0195f000000070008000000000000602",
    });
  }

  if (path === "/api/v1/finops/cognitive-impact" && method === "GET") {
    return buildOpenApiMockResponse("GET /api/v1/finops/cognitive-impact", {
      scope_type: "GLOBAL",
      scope_id: null,
      active_framing_ratio: 0.85,
      active_framing_target: 0.4,
      quick_pass_rate: 0.02,
      quick_pass_threshold: 0.05,
      total_human_hours: 1,
      active_framing_hours: 0.8,
      review_hours: 0.2,
      autonomous_governance: null,
      trace_id: "0195f000000070008000000000000603",
    });
  }

  if (path === "/api/v1/jira/actions/stage" && method === "POST") {
    return buildOpenApiMockResponse("POST /api/v1/jira/actions/stage", {
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
