export interface MockAutonomousRunRecord {
  run_id: string;
  workspace_id: string;
  workflow_id: string;
  workflow_title: string;
  trigger_id: string | null;
  trigger_label: string;
  trigger_type: string;
  trigger_status: string;
  run_status: string;
  post_hoc_status: string;
  contract_id: string;
  cost_usd: number;
  created_at_iso: string;
  help_resource_id?: string | null;
  previous_version_available?: boolean;
}

export interface MockContextualHelpResolveState {
  route: string;
  active_article: {
    resource_id: string;
    uri: string;
    title: string;
    version: string;
    lang: string;
    layer: "BASE" | "PACK" | "WORKSPACE" | "PERSONAL";
    pack_name?: string | null;
    bound_routes: string[];
    summary_what_for: string;
    step_by_step_items: string[];
    key_terms_items: string[];
    faq_items: string[];
    cas_key: string;
    sha256: string;
    previous_version?: string | null;
  };
  merged_layers: Array<"BASE" | "PACK" | "WORKSPACE" | "PERSONAL">;
  redis_cache_key: string;
  rollback_available: boolean;
  is_autonomous_generated: boolean;
  run_id: string | null;
  contract_label: string | null;
  trigger_label: string | null;
  previous_version_available: boolean;
}

const mockAutonomousRuns: MockAutonomousRunRecord[] = [];
const mockHelpByRoute = new Map<string, MockContextualHelpResolveState>();

export function resetVitestAutonomousSupervisionMockState(): void {
  mockAutonomousRuns.length = 0;
  mockHelpByRoute.clear();
}

export function seedVitestAutonomousSupervisionRuns(
  runs: readonly MockAutonomousRunRecord[],
): void {
  mockAutonomousRuns.length = 0;
  for (const r of runs) {
    mockAutonomousRuns.push({ ...r });
  }
}

export function seedVitestContextualHelpResolve(state: MockContextualHelpResolveState): void {
  mockHelpByRoute.set(state.route, structuredClone(state));
}

export function getVitestAutonomousSupervisionRuns(): MockAutonomousRunRecord[] {
  return mockAutonomousRuns;
}

function restoreHelpRecordsForRunOrResource(
  runId: string,
  helpResourceId: string | null,
): string {
  let restoredVersion = "1.0.0";
  for (const [route, help] of mockHelpByRoute.entries()) {
    const matchesRun = help.run_id === runId;
    const matchesRes =
      helpResourceId !== null && help.active_article.resource_id === helpResourceId;
    if (matchesRun || matchesRes) {
      restoredVersion = help.active_article.previous_version ?? "1.0.0";
      mockHelpByRoute.set(route, {
        ...help,
        active_article: {
          ...help.active_article,
          version: restoredVersion,
          previous_version: null,
        },
        rollback_available: false,
        is_autonomous_generated: false,
        run_id: null,
        contract_label: null,
        trigger_label: null,
        previous_version_available: false,
      });
    }
  }
  return restoredVersion;
}

export function handleVitestAutonomousSupervisionRoute(
  path: string,
  method: string,
  body: Record<string, unknown>,
  jsonResponse: (data: unknown, status?: number) => Response,
  searchParams?: URLSearchParams,
): Response | null {
  const listMatch = /^\/api\/v1\/workspaces\/([^/]+)\/autonomous-runs$/.exec(path);
  if (listMatch && method === "GET") {
    const wsId = decodeURIComponent(listMatch[1] ?? "");
    return jsonResponse({
      workspace_id: wsId,
      runs: mockAutonomousRuns.filter((r) => r.workspace_id === wsId),
      trace_id: "0195f000000070008000000000007401",
    });
  }

  const stopMatch = /^\/api\/v1\/runs\/([^/]+)\/emergency-stop$/.exec(path);
  if (stopMatch && method === "POST") {
    const runId = decodeURIComponent(stopMatch[1] ?? "");
    const target = mockAutonomousRuns.find((r) => r.run_id === runId);
    if (!target) {
      return jsonResponse({ error_code: "ERR_RESOURCE_NOT_FOUND", detail: "Not found" }, 404);
    }
    target.run_status = "KILL_SWITCH_STOPPED";
    const suspend = body.suspend_trigger !== false && target.trigger_id !== null;
    if (suspend) {
      target.trigger_status = "CIRCUIT_OPEN";
    }
    return jsonResponse({
      run_id: target.run_id,
      workspace_id: target.workspace_id,
      status: "KILL_SWITCH_STOPPED",
      trigger_suspended: suspend,
      sse_dispatch_latency_ms: 4.5,
      trace_id: "0195f000000070008000000000007402",
    });
  }

  const rollbackMatch = /^\/api\/v1\/runs\/([^/]+)\/invalidate-and-restore$/.exec(path);
  if (rollbackMatch && method === "POST") {
    const runId = decodeURIComponent(rollbackMatch[1] ?? "");
    const target = mockAutonomousRuns.find((r) => r.run_id === runId);
    const helpId =
      typeof body.help_resource_id === "string"
        ? body.help_resource_id
        : (target?.help_resource_id ?? null);
    if (!target && !helpId) {
      return jsonResponse({ error_code: "ERR_RESOURCE_NOT_FOUND", detail: "Not found" }, 404);
    }
    if (target) {
      target.run_status = "ROLLED_BACK";
      target.post_hoc_status = "INVALIDATED_ROLLED_BACK";
      target.previous_version_available = false;
    }
    const restoredVersion = restoreHelpRecordsForRunOrResource(runId, helpId);
    return jsonResponse({
      run_id: runId,
      workspace_id: target?.workspace_id ?? "0195f000-0000-7000-8000-000000000301",
      status: "ROLLED_BACK",
      restored_version: restoredVersion,
      help_resource_id: helpId,
      redis_cache_invalidated_ms: 1.2,
      sse_dispatch_latency_ms: 3.4,
      trace_id: "0195f000000070008000000000007403",
    });
  }

  const reviewMatch = /^\/api\/v1\/runs\/([^/]+)\/post-hoc-review$/.exec(path);
  if (reviewMatch && method === "POST") {
    const runId = decodeURIComponent(reviewMatch[1] ?? "");
    const target = mockAutonomousRuns.find((r) => r.run_id === runId);
    if (!target) {
      return jsonResponse({ error_code: "ERR_RESOURCE_NOT_FOUND", detail: "Not found" }, 404);
    }
    const decision = String(body.decision ?? "VALIDATED");
    target.post_hoc_status = decision;
    let restoredVersion: string | null = null;
    if (decision === "INVALIDATED_ROLLED_BACK") {
      target.run_status = "ROLLED_BACK";
      target.previous_version_available = false;
      restoredVersion = restoreHelpRecordsForRunOrResource(runId, target.help_resource_id ?? null);
    }
    return jsonResponse({
      run_id: runId,
      review_status: decision,
      run_status: target.run_status,
      restored_version: restoredVersion,
      trace_id: "0195f000000070008000000000007404",
    });
  }

  if (path === "/api/v1/help/resolve" && method === "GET") {
    const route = searchParams?.get("route") ?? "/cockpit";
    const seeded = mockHelpByRoute.get(route);
    if (seeded) {
      return jsonResponse(seeded);
    }
  }

  if (path === "/api/v1/help/rollback" && method === "POST") {
    const resourceId = String(body.resource_id ?? "");
    const restoredVersion = restoreHelpRecordsForRunOrResource("", resourceId || null);
    return jsonResponse({
      resource_id: resourceId,
      uri: `orcia://system/help/${resourceId}`,
      title: "Aide restaurée",
      version: restoredVersion,
      lang: "fr",
      layer: "WORKSPACE",
      pack_name: "core",
      bound_routes: ["/cockpit"],
      summary_what_for: "Restored",
      step_by_step_items: [],
      key_terms_items: [],
      faq_items: [],
      cas_key: "cas/restored",
      sha256: "a".repeat(64),
      previous_version: null,
      is_autonomous_generated: false,
    });
  }

  const wfV2Match = /^\/api\/v1\/workflows\/v2\/([^/]+)$/.exec(path);
  if (wfV2Match && method === "PUT") {
    return jsonResponse({
      workflow: body.workflow ?? { id: decodeURIComponent(wfV2Match[1] ?? ""), status: "published" },
      forked_as_draft: false,
    });
  }

  return null;
}
