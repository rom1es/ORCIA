import type { UiAssistantSpeedMode, UiInferenceEffort } from "@orcia/ui";
import {
  detectAdaptiveThinkingStepsForQuestion,
  shouldUseProgressiveStepThinking,
} from "../../features/inbox/assistantBackgroundStreamStore";
import { backendState, buildSseStreamResponse, jsonResponse, problemResponse } from "./mockBackendState";

export function handleAssistantAndInboxRoute(params: {
  path: string;
  method: string;
  parsedUrl: URL;
  body: Record<string, unknown>;
  init?: RequestInit;
}): Response | Promise<Response> | null {
  const { path, method, parsedUrl, body, init } = params;

  if (path === "/api/v1/assistant/three-speed/stream" && method === "POST") {
    if ((globalThis as Record<string, unknown>).__ORCIA_TEST_KEEP_STREAM_PENDING__) {
      return new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
      });
    }
    const hat = String(body.hat ?? "PM");
    const requestedSpeed = String(body.requested_speed ?? "SPEED_1_FAST") as UiAssistantSpeedMode;
    const thinkingEffort = String(body.thinking_effort ?? "balanced") as UiInferenceEffort;
    const isFr = String(body.locale ?? "fr") !== "en";
    const fullUserPrompt = String(body.user_prompt ?? "");
    const cleanPrompt = fullUserPrompt.split(/\n\n\[(?:Pièces jointes|User-supplied attachments)/)[0] ?? fullUserPrompt;
    const replyText = `[${requestedSpeed}] ${cleanPrompt}`;
    const personalInstructions = body.personal_instructions ? String(body.personal_instructions) : "";
    const folderPinnedNotes = body.folder_pinned_notes ? String(body.folder_pinned_notes) : "";
    const assembledSystemPrompt = [
      `[ROLE=${hat}] [SPEED=${requestedSpeed}] [EFFORT=${thinkingEffort}]`,
      personalInstructions ? `[LAYER_5_USER_PREFERENCES] ${personalInstructions}` : "",
      folderPinnedNotes ? `[LAYER_5_ACTIVE_FOLDER_PINNED_NOTES] ${folderPinnedNotes}` : "",
    ].filter(Boolean).join("\n");

    const useSteps = shouldUseProgressiveStepThinking({
      userPrompt: cleanPrompt,
      requestedSpeed,
      deepAuditPillActive: Boolean(body.deep_audit_pill_active),
      thinkingEffort,
    });
    const plannedSteps = useSteps ? detectAdaptiveThinkingStepsForQuestion(cleanPrompt, isFr) : [];
    const thinkingText = plannedSteps.map((s) => `${s.label}: ${s.intermediateOutput ?? ""}`).join(" · ");

    return buildSseStreamResponse([
      `event: cache_status\ndata: ${JSON.stringify({ cache_hit: false, cache_lookup_ms: 1 })}\n\n`,
      `event: token_delta\ndata: ${JSON.stringify({ accumulated_text: replyText })}\n\n`,
      `event: turn_completed\ndata: ${JSON.stringify({
        turn_id: `turn-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        response_text: replyText,
        thinking_text: thinkingText,
        assembled_system_prompt: assembledSystemPrompt,
        latency_ms: plannedSteps.length > 0 ? 3000 : 1000,
      })}\n\n`,
    ]);
  }

  if (path === "/api/v1/assistant/three-speed/stop" && method === "POST") {
    return jsonResponse({ status: "STOPPED", streamed_text: "", thinking_text: "" });
  }
  if (path === "/api/v1/assistant/three-speed/feedback" && method === "POST") {
    return jsonResponse({ status: "recorded" });
  }

  if (path === "/api/v1/assistant/folders" && method === "POST") {
    const title = String(body.title ?? "Dossier");
    const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, "-");
    const folderId = typeof body.folder_id === "string" && body.folder_id ? body.folder_id : `folder-${slug}-${backendState.recordedCalls.length}`;
    const existing = backendState.assistantFolders.find((f) => f.folder_id === folderId);
    const cleanPinnedNotes = String(body.pinned_notes_markdown ?? "").replace(/\[LAYER_5_[^\]]*\]\s*/g, "").trim();
    const record: Record<string, unknown> = {
      folder_id: folderId,
      workspace_id: String(body.workspace_id ?? ""),
      owner_user_id: "0195f000-0000-7000-8000-000000000001",
      title,
      pinned_notes_markdown: cleanPinnedNotes,
      working_attachments_uris: [],
      consolidated_summary: String(body.consolidated_summary ?? ""),
      evidence_tags: ["S1"],
      has_restricted_sources: Boolean(body.has_restricted_sources ?? false),
      visibility_mode: existing?.visibility_mode ?? "PRIVATE",
      shares: [],
      assembled_layer5_prompt_block: "",
    };
    backendState.assistantFolders = existing
      ? backendState.assistantFolders.map((f) => (f.folder_id === folderId ? record : f))
      : [...backendState.assistantFolders, record];
    return jsonResponse(record);
  }

  const shareMatch = /^\/api\/v1\/assistant\/folders\/([^/]+)\/share$/.exec(path);
  if (shareMatch && method === "POST") {
    const folderId = decodeURIComponent(shareMatch[1] ?? "");
    const folder = backendState.assistantFolders.find((f) => f.folder_id === folderId);
    if (!folder) return jsonResponse({ error_code: "ERR_RESOURCE_NOT_FOUND" }, 404);
    folder.visibility_mode = body.visibility_mode;
    return jsonResponse({
      folder_id: folderId,
      workspace_id: folder.workspace_id,
      visibility_mode: body.visibility_mode,
      shares: [],
      has_restricted_sources: folder.has_restricted_sources,
    });
  }

  const overviewMatch = /^\/api\/v1\/assistant\/workspaces\/([^/]+)\/overview$/.exec(path);
  if (overviewMatch && method === "GET") {
    const workspaceId = decodeURIComponent(overviewMatch[1] ?? "");
    const wsFolders = backendState.assistantFolders.filter((f) => f.workspace_id === workspaceId);
    return jsonResponse({
      workspace_id: workspaceId,
      tabs: ["ACTIVE_DISCUSSION", "FOLDERS", "HISTORY_SEARCH"],
      active_folder_pill_label: null,
      folders_count: wsFolders.length,
      folders: wsFolders,
      threads: [],
      history_hits: [],
    });
  }

  if (path === "/api/v1/assistant/threads" && method === "POST") {
    return jsonResponse({
      thread_id: `thread-${backendState.recordedCalls.length}`,
      workspace_id: String(body.workspace_id ?? "0195f000-0000-7000-8000-000000000301"),
      title: String(body.title ?? "Discussion"),
    });
  }

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
