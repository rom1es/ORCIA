import { backendState, buildSseStreamResponse, jsonResponse, problemResponse } from "./mockBackendState";

export function handleInboxAndBrokerRoute(params: {
  path: string;
  method: string;
  parsedUrl: URL;
  body: Record<string, unknown>;
}): Response | Promise<Response> | null {
  const { path, method, parsedUrl, body } = params;

  if (path === "/api/v1/events/stream" && method === "GET") {
    const wsId = parsedUrl.searchParams.get("workspace_id") ?? "0195f000-0000-7000-8000-000000000301";
    return buildSseStreamResponse([
      `event: connected\ndata: ${JSON.stringify({ channel: `channel:workspace:${wsId}` })}\n\n`,
    ]);
  }

  if (path === "/api/v1/inbox/notifications" && method === "GET") {
    const wsId = parsedUrl.searchParams.get("workspace_id");
    const scopeFilter = parsedUrl.searchParams.get("scope_filter") ?? "ALL";
    const items = backendState.inboxNotifications.filter((n) => {
      if (wsId && n.workspace_id && n.workspace_id !== wsId) return false;
      if (scopeFilter === "PERSONAL") return n.scope_kind === "PERSONAL";
      if (scopeFilter === "TEAM") return n.scope_kind === "TEAM";
      return true;
    });
    return jsonResponse({
      workspace_id: wsId ?? "0195f000-0000-7000-8000-000000000301",
      viewer_user_id: "0195f000-0000-7000-8000-000000000001",
      amber_badge_count: items.filter((n) => n.status === "OPEN").length,
      items,
      trace_id: "trace-vitest-inbox",
    });
  }

  const taskClaimMatch = /^\/api\/v1\/tasks\/([^/]+)\/claim$/.exec(path);
  if (taskClaimMatch && method === "POST") {
    const taskId = decodeURIComponent(taskClaimMatch[1] ?? "");
    const target = backendState.inboxNotifications.find((n) => n.id === taskId);
    if (!target) return problemResponse(404, "ERR_RESOURCE_NOT_FOUND", "Ressource introuvable", `Notification ${taskId} introuvable.`, path);
    const force = Boolean(body.force ?? false);
    if (target.status === "CLAIMED" && target.claimed_by_user_id && target.claimed_by_user_id !== "0195f000-0000-7000-8000-000000000001" && !force) {
      return problemResponse(409, "ERR_STEP_ALREADY_CLAIMED_BY_PEER", "Étape déjà prise en charge", "Cette tâche est déjà prise en charge par un pair.", path);
    }
    target.status = "CLAIMED";
    target.claimed_by_user_id = "0195f000-0000-7000-8000-000000000001";
    target.claimed_by_display_name = backendState.firstAdmin?.displayName ?? "Admin Test";
    target.presence_state = "CLAIMED_BY_ME";
    target.claimed_at = new Date().toISOString();
    return jsonResponse({
      notification: target,
      lock_key: `lock:step:${String(target.step_execution_id ?? taskId)}`,
      viewer_presence_state: "CLAIMED_BY_ME",
      peer_presence_state: "CLAIMED_BY_PEER",
      sse_event: {
        event_id: `evt-claim-${backendState.recordedCalls.length}`,
        event_name: "step.claimed",
        channel: `workspace:${String(target.workspace_id ?? "ws")}`,
        workspace_id: String(target.workspace_id ?? ""),
        run_id: String(target.run_id ?? ""),
        step_execution_id: String(target.step_execution_id ?? ""),
        payload: { task_id: taskId },
        published_at_iso: new Date().toISOString(),
        dispatch_latency_ms: 12,
      },
      trace_id: "trace-vitest-claim",
    });
  }

  const taskReleaseMatch = /^\/api\/v1\/tasks\/([^/]+)\/release$/.exec(path);
  if (taskReleaseMatch && method === "POST") {
    const taskId = decodeURIComponent(taskReleaseMatch[1] ?? "");
    const target = backendState.inboxNotifications.find((n) => n.id === taskId);
    if (!target) return problemResponse(404, "ERR_RESOURCE_NOT_FOUND", "Ressource introuvable", `Notification ${taskId} introuvable.`, path);
    target.status = "OPEN";
    target.claimed_by_user_id = null;
    target.claimed_by_display_name = null;
    target.presence_state = "UNCLAIMED";
    return jsonResponse({
      notification: target,
      lock_key: null,
      viewer_presence_state: "UNCLAIMED",
      peer_presence_state: "UNCLAIMED",
      sse_event: {
        event_id: `evt-release-${backendState.recordedCalls.length}`,
        event_name: "step.released",
        channel: `workspace:${String(target.workspace_id ?? "ws")}`,
        workspace_id: String(target.workspace_id ?? ""),
        run_id: String(target.run_id ?? ""),
        step_execution_id: String(target.step_execution_id ?? ""),
        payload: { task_id: taskId },
        published_at_iso: new Date().toISOString(),
        dispatch_latency_ms: 9,
      },
      trace_id: "trace-vitest-release",
    });
  }

  if (path === "/api/v1/permissions/broker/state" && method === "GET") {
    const wsId = parsedUrl.searchParams.get("workspace_id");
    const tickets = backendState.permissionBrokerTickets.filter((t) => !wsId || !t.workspace_id || t.workspace_id === wsId);
    return jsonResponse({ policies: backendState.permissionBrokerPolicies, tickets, trace_id: "trace-vitest-broker" });
  }

  if (path === "/api/v1/permissions/broker/check-access" && method === "POST") {
    const targetUri = String(body.target_uri ?? "git://gitlab.internal/platform/infra-core");
    const scheme = targetUri.includes("://") ? (targetUri.split("://")[0] ?? "git").toLowerCase() : "git";
    const ticketId = `0195f000-0000-7000-8000-${String(backendState.permissionBrokerTickets.length + 1).padStart(12, "0")}`;
    const ticket: Record<string, unknown> = {
      id: ticketId,
      ticket_key: `tkt-vitest-${backendState.permissionBrokerTickets.length + 1}`,
      workspace_id: body.workspace_id ?? null,
      requester_user_id: "0195f000-0000-7000-8000-000000000001",
      policy_id: "0192c4e0-0000-7000-8000-000000001007",
      step_key: String(body.step_key ?? "fetch_repo"),
      step_number: Number(body.step_number ?? 1),
      step_state: "PERMISSION_DENIED_STEP",
      status: "WAITING_FOR_PERMISSION",
      target_uri: targetUri,
      connector_scheme: scheme,
      execution_identity: String(body.execution_identity ?? "passthrough"),
      upstream_http_status: Number(body.simulated_upstream_status ?? 403),
      required_role: "ROLE_GIT_REPOSITORY_READER",
      approver_team: "SecOps & Platform IAM",
      sla_hours: 4,
      request_url: "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa?pid=10420",
      jira_request_url: "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa?pid=10420",
      permission_broker_hint: `jira://IAM/ROLE_GIT_REPOSITORY_READER?target=${encodeURIComponent(targetUri)}`,
      procedure_markdown: "### Procédure d'habilitation Dépôt Git\n1. Ouvrir la demande d'accès IAM pré-remplie.",
    };
    backendState.permissionBrokerTickets = [ticket, ...backendState.permissionBrokerTickets];
    return jsonResponse({
      allowed: false,
      status: "WAITING_FOR_PERMISSION",
      execution_identity: ticket.execution_identity,
      target_uri: targetUri,
      connector_scheme: scheme,
      policy: {
        id: "0192c4e0-0000-7000-8000-000000001007",
        policy_key: "pol-git-default-fallback",
        uri_pattern: `${scheme}://*`,
        connector_scheme: scheme,
        required_role: "ROLE_GIT_REPOSITORY_READER",
        approver_team: "SecOps & Platform IAM",
        request_url_template: "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa?pid=10420",
        sla_hours: 4,
        procedure_markdown: ticket.procedure_markdown,
        service_principal_allowed: false,
        approved_by_admin_id: null,
        human_anchor_author_id: null,
        human_anchor_signature: null,
        freshness_ttl_days: 90,
      },
      ticket,
      permission_broker_hint: ticket.permission_broker_hint,
      trace_id: "trace-vitest-broker-check",
    });
  }

  const brokerActionMatch = /^\/api\/v1\/permissions\/broker\/tickets\/([^/]+)\/action$/.exec(path);
  if (brokerActionMatch && method === "POST") {
    const ticketId = decodeURIComponent(brokerActionMatch[1] ?? "");
    const target = backendState.permissionBrokerTickets.find((t) => t.id === ticketId || t.ticket_key === ticketId);
    if (!target) return problemResponse(404, "ERR_RESOURCE_NOT_FOUND", "Ticket introuvable", `Ticket ${ticketId} introuvable.`, path);
    const action = String(body.action ?? "REPLAY");
    target.step_state = action === "PAUSE" ? "PAUSED" : "REPLAYED";
    target.status = action === "PAUSE" ? "PAUSED" : "REPLAYED";
    return jsonResponse({ ticket: target, trace_id: "trace-vitest-broker-action" });
  }

  return null;
}
