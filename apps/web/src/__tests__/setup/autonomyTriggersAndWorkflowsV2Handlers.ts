import type { ApiWorkflowDefinitionV2 } from "@orcia/api-client";
import { listVitestPendingReflexiveRuns } from "../vitestReflexiveBackend";
import { backendState, jsonResponse, problemResponse } from "./mockBackendState";

export function handleAutonomyTriggersAndWorkflowsV2Route(params: {
  path: string;
  method: string;
  body: Record<string, unknown>;
}): Response | null {
  const { path, method, body } = params;

  const autonomyContractMatch = /^\/api\/v1\/workspaces\/([^/]+)\/workflows\/([^/]+)\/autonomy-contract(\/revoke)?$/.exec(path);
  if (autonomyContractMatch) {
    const wsId = decodeURIComponent(autonomyContractMatch[1] ?? "");
    const wfId = decodeURIComponent(autonomyContractMatch[2] ?? "");
    const isRevoke = autonomyContractMatch[3] === "/revoke";
    const defaultSp = {
      id: "0195f000-0000-7000-8000-000000007101",
      principal_id: "sp-docs-automation",
      display_name: "Robot Documentation Espace",
      roles: ["TEAM_LEAD"],
      team_ids: [wsId],
      status: "ACTIVE",
    };
    if (method === "GET" && !isRevoke) {
      const history = backendState.autonomyContracts.filter((c) => c.workspace_id === wsId && c.workflow_id === wfId);
      return jsonResponse({
        workspace_id: wsId,
        workflow_id: wfId,
        active_contract: history.find((c) => c.status === "ACTIVE") ?? null,
        history,
        eligible_service_principals: [defaultSp],
        trace_id: "0195f000000070008000000000000711",
      });
    }
    if (method === "POST" && !isRevoke) {
      if (String(body.criticality ?? "STANDARD") === "HIGH_CRITICAL") {
        return jsonResponse({ error_code: "ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE", detail: "Ce workflow critique exige une Gate Humaine." }, 422);
      }
      for (const existing of backendState.autonomyContracts) {
        if (existing.workspace_id === wsId && existing.workflow_id === wfId && existing.status === "ACTIVE") existing.status = "SUPERSEDED";
      }
      const created = {
        id: `0195f000-0000-7000-8000-00000000720${backendState.autonomyContracts.length + 1}`,
        workspace_id: wsId,
        workflow_id: wfId,
        workflow_version: String(body.workflow_version ?? "1.0.0"),
        workflow_sha256: String(body.workflow_sha256 ?? "sha256-mock"),
        criticality: String(body.criticality ?? "STANDARD"),
        service_principal_id: String(body.service_principal_id ?? defaultSp.id),
        allowed_read_sources: Array.isArray(body.allowed_read_sources) ? body.allowed_read_sources : [],
        allowed_write_actions: Array.isArray(body.allowed_write_actions) ? body.allowed_write_actions : [],
        max_cost_per_run_usd: Number(body.max_cost_per_run_usd ?? 5),
        tie_break_policy: String(body.tie_break_policy ?? "ONTOLOGY_AXIOM_FIRST"),
        post_hoc_sampling_rate: Number(body.post_hoc_sampling_rate ?? 0.15),
        status: "ACTIVE",
        signed_by_user_id: "0195f000-0000-7000-8000-000000000203",
        signed_by_role: "TEAM_LEAD",
        signature_sha256: "a".repeat(64),
        signed_at_iso: "2026-11-17T10:00:00Z",
        revoked_at_iso: null,
        revoked_by_user_id: null,
      };
      backendState.autonomyContracts.unshift(created);
      return jsonResponse(created, 201);
    }
    if (method === "POST" && isRevoke) {
      const active = backendState.autonomyContracts.find((c) => c.workspace_id === wsId && c.workflow_id === wfId && c.status === "ACTIVE");
      if (!active) return jsonResponse({ error_code: "ERR_AUTONOMY_CONTRACT_NOT_FOUND" }, 404);
      active.status = "REVOKED";
      active.revoked_at_iso = "2026-11-17T10:05:00Z";
      active.revoked_by_user_id = "0195f000-0000-7000-8000-000000000203";
      return jsonResponse(active);
    }
  }

  const triggerMatch = path.match(/^\/api\/v1\/workspaces\/([^/]+)\/workflows\/([^/]+)\/triggers(?:\/([^/]+)(?:\/(fire|reset-circuit))?)?$/);
  if (triggerMatch) {
    const wsId = decodeURIComponent(triggerMatch[1] ?? "");
    const wfId = decodeURIComponent(triggerMatch[2] ?? "");
    const trigId = triggerMatch[3] ? decodeURIComponent(triggerMatch[3]) : null;
    const action = triggerMatch[4] ?? null;

    if (method === "GET" && !trigId) {
      const items = backendState.workflowTriggers.filter((t) => t.workspace_id === wsId && t.workflow_id === wfId);
      return jsonResponse({ workspace_id: wsId, workflow_id: wfId, items, trace_id: "0195f000000070008000000000000720" });
    }
    if (method === "POST" && !trigId) {
      const activeContract = backendState.autonomyContracts.find((c) => c.workspace_id === wsId && c.workflow_id === wfId && c.status === "ACTIVE");
      if (!activeContract) return jsonResponse({ error_code: "ERR_AUTONOMY_CONTRACT_REQUIRED" }, 422);
      const nextIdx = backendState.workflowTriggers.length + 1;
      const newId = `0195f000-0000-7000-8000-${String(7300 + nextIdx).padStart(12, "0")}`;
      const explicitKey =
        typeof body.trigger_key === "string" ? body.trigger_key.trim() : "";
      const triggerKey =
        explicitKey ||
        `trg-${String(body.trigger_type ?? "MANUAL_AUTONOMOUS").toLowerCase()}-${String(nextIdx).padStart(12, "0")}`;
      if (
        backendState.workflowTriggers.some(
          (t) =>
            t.workspace_id === wsId &&
            t.workflow_id === wfId &&
            t.trigger_key === triggerKey,
        )
      ) {
        return problemResponse(
          409,
          "ERR_TRIGGER_DUPLICATE_KEY",
          "Clé de déclencheur déjà utilisée",
          `La clé de déclencheur '${triggerKey}' existe déjà sur ce processus.`,
          path,
        );
      }
      const secInput = (body.webhook_secret ?? null) as { action?: string; plaintext_value?: string } | null;
      const hasSecret = Boolean(secInput?.action === "set" && secInput.plaintext_value);
      const created = {
        id: newId,
        trigger_key: triggerKey,
        workspace_id: wsId,
        workflow_id: wfId,
        trigger_type: String(body.trigger_type ?? "MANUAL_AUTONOMOUS"),
        contract_id: String(activeContract.id),
        cron_expr: body.cron_expr ? String(body.cron_expr) : null,
        cooldown_window_seconds: Number(body.cooldown_window_seconds ?? 300),
        service_principal_id: String(activeContract.service_principal_id),
        max_runs_per_hour: Number(body.max_runs_per_hour ?? 10),
        max_daily_cost_usd: Number(body.max_daily_cost_usd ?? 25),
        max_consecutive_failures: 3,
        consecutive_failures: 0,
        status: "ACTIVE",
        auto_help_on_publish: Boolean(body.auto_help_on_publish ?? false),
        last_fired_at_iso: null,
        log_sink_service: body.log_sink_service ? String(body.log_sink_service) : null,
        log_sink_query_text: null,
        outbox_event_filter: null,
        webhook_secret_status: {
          configured: hasSecret,
          fingerprint: hasSecret ? "sha256:mockfp01" : null,
          masked_hint: hasSecret ? "••••••••cret" : null,
          updated_at: hasSecret ? "2026-11-17T10:10:00Z" : "",
          updated_by: hasSecret ? "0195f000-0000-7000-8000-000000000203" : "",
        },
      };
      backendState.workflowTriggers.unshift(created);
      return jsonResponse(created, 201);
    }
    if (method === "PATCH" && trigId) {
      const target = backendState.workflowTriggers.find((t) => t.id === trigId && t.workspace_id === wsId);
      if (!target) return jsonResponse({ error_code: "ERR_TRIGGER_NOT_FOUND" }, 404);
      if (typeof body.status === "string") target.status = body.status;
      if (typeof body.auto_help_on_publish === "boolean") target.auto_help_on_publish = body.auto_help_on_publish;
      const secInput = (body.webhook_secret ?? null) as { action?: string } | null;
      if (secInput?.action === "set") {
        target.webhook_secret_status = { configured: true, fingerprint: "sha256:mockfp02", masked_hint: "••••••••updated", updated_at: "2026-11-17T10:12:00Z", updated_by: "0195f000-0000-7000-8000-000000000203" };
      } else if (secInput?.action === "clear") {
        target.webhook_secret_status = { configured: false, fingerprint: null, masked_hint: null, updated_at: "2026-11-17T10:12:00Z", updated_by: "0195f000-0000-7000-8000-000000000203" };
      }
      return jsonResponse(target);
    }
    if (method === "DELETE" && trigId) {
      backendState.workflowTriggers = backendState.workflowTriggers.filter((t) => !(t.id === trigId && t.workspace_id === wsId));
      return jsonResponse({ deleted_id: trigId, trace_id: "0195f000000070008000000000000721" });
    }
    if (method === "POST" && trigId && action === "fire") {
      const target = backendState.workflowTriggers.find((t) => t.id === trigId && t.workspace_id === wsId);
      if (!target) return jsonResponse({ error_code: "ERR_TRIGGER_NOT_FOUND" }, 404);
      target.last_fired_at_iso = "2026-11-17T10:15:00Z";
      return jsonResponse({
        dispatched: true,
        outcome: "DISPATCHED",
        trigger_id: trigId,
        idempotency_key: "manual:mock",
        dbos_workflow_id: `${trigId}:manual:mock`,
        run_id: "0195f000-0000-7000-8000-000000007401",
        attempts: 1,
        reason: null,
        trace_id: "0195f000000070008000000000000722",
      }, 201);
    }
    if (method === "POST" && trigId && action === "reset-circuit") {
      const target = backendState.workflowTriggers.find((t) => t.id === trigId && t.workspace_id === wsId);
      if (!target) return jsonResponse({ error_code: "ERR_TRIGGER_NOT_FOUND" }, 404);
      target.status = "ACTIVE";
      target.consecutive_failures = 0;
      return jsonResponse(target);
    }
  }

  if (path === "/api/v1/vsm" && method === "GET") {
    return jsonResponse({
      items: [
        {
          id: "vsm-mon-compte-idea-to-prod",
          title: "Chaîne de Valeur Mon Compte",
          subtitle: "Parcours complet en 11 étapes",
        },
      ],
    });
  }
  if (path === "/api/v1/workflows/v2" && method === "GET") {
    return jsonResponse({ items: Array.from(backendState.workflowsV2.values()) });
  }
  if (path === "/api/v1/workflows/v2/runs" && method === "GET") {
    const wfItems = Array.from(backendState.workflowV2Runs.values())
      .reverse()
      .filter((r) => String(r.status ?? "") !== "COMPLETED_APPROVED" && String(r.status ?? "") !== "COMPLETED")
      .map((r) => {
        const wfId = String(r.workflow_id ?? "");
        const wf = backendState.workflowsV2.get(wfId);
        return {
          run_id: String(r.run_id ?? ""),
          workspace_id: r.workspace_id ? String(r.workspace_id) : null,
          workflow_id: wfId,
          workflow_slug: String(r.workflow_slug ?? wfId),
          workflow_title: wf?.title ?? wfId,
          actor_slug: wf?.global_system_prompt_or_ref ?? "assistant",
          status: String(r.status ?? "WAITING_FINAL_ANCHOR"),
          raw_status: String(r.status ?? "WAITING_FINAL_ANCHOR"),
          is_pending: true,
          reflexive_execution_id: r.reflexive_execution_id ? String(r.reflexive_execution_id) : null,
          source: "workflow_v2",
          created_at_iso: "",
          updated_at_iso: "",
        };
      });
    const rxItems = listVitestPendingReflexiveRuns();
    const combined = [...rxItems, ...wfItems];
    return jsonResponse({
      items: combined,
      pending_count: combined.length,
      total_count: combined.length,
      trace_id: "0195f000000070008000000000000303",
    });
  }
  const wfV2WhatIfMatch = /^\/api\/v1\/workflows\/v2\/([^/]+)\/what-if$/.exec(path);
  if (wfV2WhatIfMatch && method === "POST") {
    return jsonResponse({
      workflow_id: decodeURIComponent(wfV2WhatIfMatch[1] ?? ""),
      version: "1.0.0",
      sandbox_isolated: true,
      external_writes_executed: 0,
      sub_steps_evaluated: 2,
      deterministic_gates_passed: true,
      probabilistic_gates_passed: true,
      estimated_tokens: 2900,
      estimated_cost_usd: 0.03,
      findings: [],
    });
  }
  const wfV2RunsMatch = /^\/api\/v1\/workflows\/v2\/([^/]+)\/runs$/.exec(path);
  if (wfV2RunsMatch && method === "POST") {
    const wfId = decodeURIComponent(wfV2RunsMatch[1] ?? "");
    const existing = backendState.workflowsV2.get(wfId);
    const runId = `run-${wfId}-01`;
    const runRecord: Record<string, unknown> = {
      run_id: runId,
      workspace_id: body.workspace_id ? String(body.workspace_id) : null,
      workflow_id: wfId,
      workflow_slug: existing?.slug ?? wfId,
      workflow_version: existing?.version ?? "1.0.0",
      orchestration_type: existing?.orchestration_type ?? "deterministic_dbos",
      execution_mode: existing?.execution_mode ?? "native_orcia",
      status: "WAITING_FINAL_ANCHOR",
      iteration: 1,
      reentry_mode: "initial",
      current_sub_step_index: 0,
      inputs: {},
      mcp_context_bundle: null,
      sub_step_records: [],
      gate_report: null,
      final_artifact_pointer: null,
      reflexive_execution_id: `reflx-${wfId}-01`,
      trace_events: [],
      return_loop_target_step_num: null,
      return_loop_remarks: null,
      audit_trail: [],
    };
    backendState.workflowV2Runs.set(runId, runRecord);
    return jsonResponse({ run: runRecord });
  }
  const wfV2ItemMatch = /^\/api\/v1\/workflows\/v2\/([^/]+)$/.exec(path);
  if (wfV2ItemMatch && method === "GET") {
    const wfId = decodeURIComponent(wfV2ItemMatch[1] ?? "");
    const found = backendState.workflowsV2.get(wfId) ?? Array.from(backendState.workflowsV2.values()).find((w) => w.slug === wfId);
    if (!found) return jsonResponse({ detail: `Workflow '${wfId}' introuvable.` }, 404);
    return jsonResponse(found);
  }
  if (wfV2ItemMatch && method === "PUT") {
    const wfId = decodeURIComponent(wfV2ItemMatch[1] ?? "");
    const incoming = (body.workflow ?? {}) as ApiWorkflowDefinitionV2;
    const saved: ApiWorkflowDefinitionV2 = { ...incoming, id: incoming.id || wfId };
    backendState.workflowsV2.set(saved.id, saved);
    return jsonResponse({ workflow: saved, forked_as_draft: false });
  }

  const runGetMatch = /^\/api\/v1\/runs\/([^/]+)$/.exec(path);
  if (runGetMatch && method === "GET") {
    const runId = decodeURIComponent(runGetMatch[1] ?? "");
    const found = backendState.workflowV2Runs.get(runId);
    if (!found) return jsonResponse({ detail: `Run '${runId}' not found` }, 404);
    return jsonResponse({ run: found });
  }

  const hitlSignalMatch = /^\/api\/v1\/runs\/([^/]+)\/hitl-signal$/.exec(path);
  if (hitlSignalMatch && method === "POST") {
    const runId = decodeURIComponent(hitlSignalMatch[1] ?? "");
    const action = String(body.action ?? "APPROVE");
    const wfId = runId.replace(/^run-/, "").replace(/-\d+$/, "") || "wf-01-qualification-prd";
    const existing = backendState.workflowsV2.get(wfId);
    const nextStatus =
      action === "APPROVE"
        ? "COMPLETED_APPROVED"
        : action === "REJECT_LOOP" || action === "REJECT_AND_LOOP"
          ? "RETURN_LOOP_TRIGGERED"
          : action === "SUSPEND_SLA"
            ? "SLA_SUSPENDED"
            : "WAITING_FINAL_ANCHOR";
    const updatedRun: Record<string, unknown> = {
      ...(backendState.workflowV2Runs.get(runId) ?? {}),
      run_id: runId,
      workflow_id: wfId,
      workflow_slug: existing?.slug ?? wfId,
      workflow_version: existing?.version ?? "1.0.0",
      orchestration_type: existing?.orchestration_type ?? "deterministic_dbos",
      execution_mode: existing?.execution_mode ?? "native_orcia",
      status: nextStatus,
      iteration: 1,
      reentry_mode: "initial",
      current_sub_step_index: 0,
      inputs: {},
      mcp_context_bundle: null,
      sub_step_records: [],
      gate_report: null,
      final_artifact_pointer: null,
      reflexive_execution_id: `reflx-${wfId}-01`,
      trace_events: [],
      return_loop_target_step_num: null,
      return_loop_remarks: null,
      audit_trail: [],
    };
    backendState.workflowV2Runs.set(runId, updatedRun);
    return jsonResponse({ run: updatedRun });
  }

  return null;
}
