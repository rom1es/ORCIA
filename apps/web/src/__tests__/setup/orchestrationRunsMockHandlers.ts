import { backendState, jsonResponse } from "./mockBackendState";

export function handleOrchestrationRunsRoute(params: {
  path: string;
  method: string;
  body: Record<string, unknown>;
}): Response | null {
  const { path, method, body } = params;

  if (path === "/api/v1/orchestration/state" && method === "GET") {
    return jsonResponse({
      workflows: [],
      runs: backendState.orchestrationRuns.map((r) => ({
        id: r.id,
        run_key: `run-${r.id}`,
        workspace_id: r.workspace_id,
        workflow_def_id: "wf-claims",
        workflow_uri: "orcia://workflows/claims-engineering-delivery",
        parent_run_id: null,
        parent_step_execution_id: null,
        root_run_id: r.id,
        nesting_depth: 0,
        execution_regime: "HUMAN_LED",
        criticality: "HIGH_CRITICAL",
        trigger_id: null,
        trigger_idempotency_key: null,
        status: r.status,
        initiated_by_user_id: "0195f000-0000-7000-8000-000000000001",
        execution_identity_mode: "PASSTHROUGH",
        budget_max_usd: 15,
        run_lock: {
          workflow_uri: "orcia://workflows/claims-engineering-delivery",
          workflow_version: "1.0.0",
          workflow_sha256: "sha256:wf",
          sources: [],
          sub_workflow_locks: [],
          manifest_sha256: "sha256:lock",
        },
      })),
      compiled_default_template: {
        template_key: "tpl-architecture-decision-record",
        uri: "orcia://templates/adr",
        version: "1.0.0",
        human_markdown_view: "",
        cognitive_chunks: [],
        agent_json_schema: {},
        bound_ontology_terms: [],
        sha256: "sha256:tpl",
      },
      trace_id: "0195f000000070008000000000000999",
    });
  }

  if (path === "/api/v1/orchestration/runs/instantiate" && method === "POST") {
    const runId = `0195f000-0000-7000-8000-00000000900${backendState.orchestrationRuns.length + 1}`;
    const wsId = String(body.workspace_id ?? "0192c4e0-0000-7000-8000-000000000201");
    backendState.orchestrationRuns.push({
      id: runId,
      workspace_id: wsId,
      status: "RUNNING",
      step_status: "PENDING",
      draft_artifact: {},
      committed_snapshot_id: null,
    });
    return jsonResponse({
      run: {
        id: runId,
        run_key: `run-${runId}`,
        workspace_id: wsId,
        workflow_def_id: "wf-claims",
        workflow_uri: String(body.workflow_uri ?? "orcia://workflows/claims-engineering-delivery"),
        parent_run_id: null,
        parent_step_execution_id: null,
        root_run_id: runId,
        nesting_depth: 0,
        execution_regime: "HUMAN_LED",
        criticality: "HIGH_CRITICAL",
        trigger_id: null,
        trigger_idempotency_key: null,
        status: "RUNNING",
        initiated_by_user_id: "0195f000-0000-7000-8000-000000000001",
        execution_identity_mode: "PASSTHROUGH",
        budget_max_usd: 15,
        run_lock: {
          workflow_uri: "orcia://workflows/claims-engineering-delivery",
          workflow_version: "1.0.0",
          workflow_sha256: "sha256:wf",
          sources: [],
          sub_workflow_locks: [],
          manifest_sha256: "sha256:lock",
        },
      },
      trace_id: "0195f000000070008000000000000999",
    });
  }

  const bbMatch = /^\/api\/v1\/orchestration\/runs\/([^/]+)\/blackboard$/.exec(path);
  if (bbMatch && method === "GET") {
    const runId = decodeURIComponent(bbMatch[1] ?? "");
    const run = backendState.orchestrationRuns.find((r) => r.id === runId);
    if (!run) return jsonResponse({ error_code: "ERR_RESOURCE_NOT_FOUND" }, 404);
    return jsonResponse({
      run_id: run.id,
      root_run_id: run.id,
      run_status: run.status,
      accumulated_root_cost_usd: 0.02,
      step_executions: [
        {
          id: `step-${run.id}`,
          step_execution_key: `${run.id}:frame-architecture-intent`,
          run_id: run.id,
          step_key: "frame-architecture-intent",
          step_index: 0,
          step_type: "HUMAN_TASK",
          execution_mode: "COACHING",
          status: run.step_status,
          attempt_count: 1,
          max_agent_retries: 2,
          draft_artifact: run.draft_artifact,
          draft_cas_key: null,
          step_memlog: [],
          hydrated_input_uris: [],
          child_run_id: null,
          committed_snapshot_id: run.committed_snapshot_id,
          cost_usd: 0,
        },
      ],
      active_snapshots: run.committed_snapshot_id
        ? [
            {
              id: run.committed_snapshot_id,
              snapshot_key: `snap-${run.id}`,
              run_id: run.id,
              step_execution_id: `step-${run.id}`,
              parent_snapshot_id: null,
              step_key: "frame-architecture-intent",
              branch_status: "ACTIVE",
              artifact_payload: run.draft_artifact,
              artifact_cas_key: "cas://snap",
              artifact_sha256: "a".repeat(64),
              memlog_summary: [],
              superseded_snapshot_ids: [],
            },
          ]
        : [],
      trace_id: "0195f000000070008000000000000999",
    });
  }

  if (path === "/api/v1/orchestration/runs/anchors/sign" && method === "POST") {
    const runId = String(body.run_id ?? "");
    const contentText = String(body.content_text ?? "").trim();
    const authorType = String(body.author_type ?? "HUMAN");
    if (authorType !== "HUMAN" || contentText.length < 30) {
      return jsonResponse({ error_code: "ERR_HUMAN_ANCHOR_REQUIRED" }, 422);
    }
    const run = backendState.orchestrationRuns.find((r) => r.id === runId);
    const sha = "b".repeat(64);
    const sectionKey = String(body.section_key ?? "human_architecture_intent");
    if (run) {
      const prevAnchors = (run.draft_artifact.human_anchors ?? {}) as Record<string, unknown>;
      run.draft_artifact = {
        ...run.draft_artifact,
        human_anchors: {
          ...prevAnchors,
          [sectionKey]: {
            content_text: contentText,
            content_sha256: sha,
            char_length: contentText.length,
            authored_by_user_id: "0195f000-0000-7000-8000-000000000001",
          },
        },
      };
    }
    return jsonResponse({
      signature: {
        id: "sig-1",
        signature_key: `anchor-${sectionKey}`,
        workspace_id: run?.workspace_id ?? "0192c4e0-0000-7000-8000-000000000201",
        run_id: runId,
        step_execution_id: `step-${runId}`,
        step_key: String(body.step_key ?? "frame-architecture-intent"),
        section_key: sectionKey,
        content_text: contentText,
        content_sha256: sha,
        char_length: contentText.length,
        authored_by_user_id: "0195f000-0000-7000-8000-000000000001",
        author_display_name: String(body.signature_text ?? "Admin Test"),
        signature_hash: "c".repeat(64),
      },
      step_execution: {
        id: `step-${runId}`,
        step_execution_key: `${runId}:frame-architecture-intent`,
        run_id: runId,
        step_key: String(body.step_key ?? "frame-architecture-intent"),
        step_index: 0,
        step_type: "HUMAN_TASK",
        execution_mode: "COACHING",
        status: run?.step_status ?? "PENDING",
        attempt_count: 1,
        max_agent_retries: 2,
        draft_artifact: run?.draft_artifact ?? {},
        draft_cas_key: null,
        step_memlog: [],
        hydrated_input_uris: [],
        child_run_id: null,
        committed_snapshot_id: run?.committed_snapshot_id ?? null,
        cost_usd: 0,
      },
      trace_id: "0195f000000070008000000000000999",
    });
  }

  const arbReqMatch = /^\/api\/v1\/orchestration\/runs\/([^/]+)\/steps\/([^/]+)\/arbitration$/.exec(path);
  if (arbReqMatch && method === "POST") {
    const runId = decodeURIComponent(arbReqMatch[1] ?? "");
    const stepKey = decodeURIComponent(arbReqMatch[2] ?? "");
    const arbId = `arb-${runId}`;
    const run = backendState.orchestrationRuns.find((r) => r.id === runId);
    if (run) {
      run.status = "WAITING_FOR_HUMAN_ARBITRATION";
      run.step_status = "WAITING_FOR_HUMAN_ARBITRATION";
      run.draft_artifact = { ...run.draft_artifact, pending_arbitration_id: arbId };
    }
    return jsonResponse({
      arbitration: {
        id: arbId,
        arbitration_key: arbId,
        workspace_id: run?.workspace_id ?? "0192c4e0-0000-7000-8000-000000000201",
        run_id: runId,
        step_execution_id: `step-${runId}`,
        step_key: stepKey,
        tie_break_policy: String(body.tie_break_policy ?? "PAUSE_AND_ESCALATE"),
        status: "PENDING",
        question_title: String(body.question_title ?? ""),
        context_summary: String(body.context_summary ?? ""),
        options_matrix: Array.isArray(body.options_matrix) ? body.options_matrix : [],
        selected_option_key: null,
        human_justification: null,
        resolved_by_user_id: null,
        resolved_by_axiom_key: null,
        outbox_event_id: "evt-arb-1",
      },
      step_execution: {
        id: `step-${runId}`,
        step_execution_key: `${runId}:${stepKey}`,
        run_id: runId,
        step_key: stepKey,
        step_index: 0,
        step_type: "HUMAN_TASK",
        execution_mode: "COACHING",
        status: "WAITING_FOR_HUMAN_ARBITRATION",
        attempt_count: 1,
        max_agent_retries: 2,
        draft_artifact: run?.draft_artifact ?? {},
        draft_cas_key: null,
        step_memlog: [],
        hydrated_input_uris: [],
        child_run_id: null,
        committed_snapshot_id: null,
        cost_usd: 0,
      },
      trace_id: "0195f000000070008000000000000999",
    });
  }

  const arbResMatch = /^\/api\/v1\/orchestration\/runs\/([^/]+)\/steps\/([^/]+)\/arbitration\/resolve$/.exec(path);
  if (arbResMatch && method === "POST") {
    const runId = decodeURIComponent(arbResMatch[1] ?? "");
    const stepKey = decodeURIComponent(arbResMatch[2] ?? "");
    const selectedOptionKey = String(body.selected_option_key ?? "OPT_A_SPOT_15M");
    const humanJustification = String(body.human_justification ?? "");
    const snapId = `snap-committed-${runId}`;
    const run = backendState.orchestrationRuns.find((r) => r.id === runId);
    if (run) {
      run.status = "RUNNING";
      run.step_status = "COMMITTED";
      run.committed_snapshot_id = snapId;
      run.draft_artifact = {
        ...run.draft_artifact,
        arbitration_resolution: {
          arbitration_id: String(body.arbitration_id ?? `arb-${runId}`),
          status: "RESOLVED_BY_HUMAN",
          selected_option_key: selectedOptionKey,
          human_justification: humanJustification,
        },
      };
    }
    return jsonResponse({
      arbitration: {
        id: String(body.arbitration_id ?? `arb-${runId}`),
        arbitration_key: `arb-${runId}`,
        workspace_id: run?.workspace_id ?? "0192c4e0-0000-7000-8000-000000000201",
        run_id: runId,
        step_execution_id: `step-${runId}`,
        step_key: stepKey,
        tie_break_policy: "PAUSE_AND_ESCALATE",
        status: "RESOLVED_BY_HUMAN",
        question_title: "Arbitrage",
        context_summary: "",
        options_matrix: [],
        selected_option_key: selectedOptionKey,
        human_justification: humanJustification,
        resolved_by_user_id: "0195f000-0000-7000-8000-000000000001",
        resolved_by_axiom_key: null,
        outbox_event_id: "evt-arb-1",
      },
      step_execution: {
        id: `step-${runId}`,
        step_execution_key: `${runId}:${stepKey}`,
        run_id: runId,
        step_key: stepKey,
        step_index: 0,
        step_type: "HUMAN_TASK",
        execution_mode: "COACHING",
        status: "COMMITTED",
        attempt_count: 1,
        max_agent_retries: 2,
        draft_artifact: run?.draft_artifact ?? {},
        draft_cas_key: null,
        step_memlog: [],
        hydrated_input_uris: [],
        child_run_id: null,
        committed_snapshot_id: snapId,
        cost_usd: 0,
      },
      committed_snapshot: {
        id: snapId,
        snapshot_key: `snap-${runId}`,
        run_id: runId,
        step_execution_id: `step-${runId}`,
        parent_snapshot_id: null,
        step_key: stepKey,
        branch_status: "ACTIVE",
        artifact_payload: run?.draft_artifact ?? {},
        artifact_cas_key: "cas://snap",
        artifact_sha256: "a".repeat(64),
        memlog_summary: [],
        superseded_snapshot_ids: [],
      },
      trace_id: "0195f000000070008000000000000999",
    });
  }

  return null;
}
