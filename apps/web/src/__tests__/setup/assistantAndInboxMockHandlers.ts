import type { UiAssistantSpeedMode, UiInferenceEffort } from "@orcia/ui";
import {
  detectAdaptiveThinkingStepsForQuestion,
  shouldUseProgressiveStepThinking,
} from "../../features/inbox/assistantBackgroundStreamStore";
import { backendState, buildSseStreamResponse, jsonResponse } from "./mockBackendState";
import { handleInboxAndBrokerRoute } from "./inboxAndBrokerMockHandlers";

const vitestPendingTurns = new Map<
  string,
  {
    body: Record<string, unknown>;
    createdAt: number;
  }
>();

export function handleAssistantAndInboxRoute(params: {
  path: string;
  method: string;
  parsedUrl: URL;
  body: Record<string, unknown>;
  init?: RequestInit;
}): Response | Promise<Response> | null {
  const { path, method, parsedUrl, body, init } = params;

  if (path === "/api/v1/assistant/turns" && method === "POST") {
    if ((globalThis as Record<string, unknown>).__ORCIA_TEST_KEEP_STREAM_PENDING__) {
      return new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () =>
          reject(new DOMException("Aborted", "AbortError")),
        );
      });
    }
    const turnId = `turn-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    const requestedSpeed = String(body.requested_speed ?? "SPEED_1_FAST") as UiAssistantSpeedMode;
    vitestPendingTurns.set(turnId, { body: { ...body }, createdAt: Date.now() });
    return jsonResponse(
      {
        turn_id: turnId,
        workspace_id: String(body.workspace_id ?? ""),
        thread_id: body.thread_id ?? null,
        parent_turn_id: body.parent_turn_id ?? null,
        speed_mode: requestedSpeed,
        status: "RUNNING",
        stream_url: `/api/v1/assistant/turns/${turnId}/stream`,
        trace_id: "0195f000000070008000000000000001",
      },
      202,
    );
  }

  const streamMatch = /^\/api\/v1\/assistant\/turns\/([^/]+)\/stream$/.exec(path);
  if (streamMatch && method === "GET") {
    const turnId = decodeURIComponent(streamMatch[1] ?? "");
    const stored = vitestPendingTurns.get(turnId)?.body ?? {};
    const hat = String(stored.hat ?? "PM");
    const requestedSpeed = String(
      stored.requested_speed ?? "SPEED_1_FAST",
    ) as UiAssistantSpeedMode;
    const thinkingEffort = String(stored.thinking_effort ?? "balanced") as UiInferenceEffort;
    const isFr = String(stored.locale ?? "fr") !== "en";
    const fullUserPrompt = String(stored.user_prompt ?? "");
    const cleanPrompt =
      fullUserPrompt.split(/\n\n\[(?:Pièces jointes|User-supplied attachments)/)[0] ??
      fullUserPrompt;
    const replyText = `[${requestedSpeed}] ${cleanPrompt}`;
    const personalInstructions = stored.personal_instructions
      ? String(stored.personal_instructions)
      : "";
    const folderPinnedNotes = stored.folder_pinned_notes
      ? String(stored.folder_pinned_notes)
      : "";
    const assembledSystemPrompt = [
      `[ROLE=${hat}] [SPEED=${requestedSpeed}] [EFFORT=${thinkingEffort}]`,
      personalInstructions ? `[LAYER_5_USER_PREFERENCES] ${personalInstructions}` : "",
      folderPinnedNotes ? `[LAYER_5_ACTIVE_FOLDER_PINNED_NOTES] ${folderPinnedNotes}` : "",
    ]
      .filter(Boolean)
      .join("\n");

    const useSteps = shouldUseProgressiveStepThinking({
      userPrompt: cleanPrompt,
      requestedSpeed,
      deepAuditPillActive: Boolean(stored.deep_audit_pill_active),
      thinkingEffort,
    });
    const plannedSteps = useSteps
      ? detectAdaptiveThinkingStepsForQuestion(cleanPrompt, isFr)
      : [];
    const thinkingText = plannedSteps
      .map((s) => `${s.label}: ${s.intermediateOutput ?? ""}`)
      .join(" · ");

    const frames: string[] = [];
    if (useSteps) {
      frames.push(
        `event: thinking_delta\ndata: ${JSON.stringify({ turn_id: turnId, seq: 1, thinking_text: thinkingText || "Analyse..." })}\n\n`,
        `event: tool_call\ndata: ${JSON.stringify({ turn_id: turnId, seq: 2, tool_name: "surgical_read_lines", sanitized_args: { uri: "docs/product/capabilities.yaml", start_line: 1, end_line: 25 } })}\n\n`,
        `event: tool_result\ndata: ${JSON.stringify({ turn_id: turnId, seq: 3, tool_name: "surgical_read_lines", status: "EXECUTED", evidence_refs: ["docs/product/capabilities.yaml"], uri: "docs/product/capabilities.yaml", start_line: 1, end_line: 25 })}\n\n`,
      );
    }
    frames.push(
      `event: token_delta\ndata: ${JSON.stringify({ turn_id: turnId, seq: 4, accumulated_text: replyText })}\n\n`,
      `event: citation_map\ndata: ${JSON.stringify({ turn_id: turnId, seq: 5, citations: {}, purged_phantom_count: 0 })}\n\n`,
      `event: turn_completed\ndata: ${JSON.stringify({
        turn_id: turnId,
        seq: 6,
        response_text: replyText,
        thinking_text: thinkingText,
        assembled_system_prompt: assembledSystemPrompt,
        latency_ms: plannedSteps.length > 0 ? 3000 : 1000,
        low_evidence: true,
        supports_tools: true,
        citation_map: {},
      })}\n\n`,
    );
    return buildSseStreamResponse(frames);
  }

  if (path === "/api/v1/assistant/turns/active" && method === "GET") {
    return jsonResponse({
      workspace_id: parsedUrl.searchParams.get("workspace_id") ?? "",
      turns: [],
    });
  }

  const turnActionMatch =
    /^\/api\/v1\/assistant\/turns\/([^/]+)\/(stop|synthesize-now|approve|feedback)$/.exec(
      path,
    );
  if (turnActionMatch && method === "POST") {
    const turnId = decodeURIComponent(turnActionMatch[1] ?? "");
    const action = turnActionMatch[2];
    if (action === "stop") {
      return jsonResponse({
        workspace_id: String(body.workspace_id ?? ""),
        turn_id: turnId,
        status: "STOPPED",
        streamed_text: "",
        thinking_text: "",
      });
    }
    if (action === "synthesize-now") {
      return jsonResponse(
        {
          turn_id: turnId,
          workspace_id: String(body.workspace_id ?? ""),
          status: "SYNTHESIZING",
          message: "Early synthesis requested.",
        },
        202,
      );
    }
    if (action === "approve") {
      return jsonResponse({
        turn_id: turnId,
        proposal_id: String(body.proposal_id ?? "prop-1"),
        workspace_id: String(body.workspace_id ?? ""),
        approved: Boolean(body.approved ?? true),
        status: body.approved === false ? "REJECTED" : "APPROVED",
      });
    }
    return jsonResponse({
      feedback_id: `fb-${turnId}`,
      turn_id: turnId,
      workspace_id: String(body.workspace_id ?? ""),
      user_id: "0195f000-0000-7000-8000-000000000001",
      rating: body.rating === "down" ? "down" : "up",
      reason_code: body.reason_code ?? null,
      comment: body.comment ?? null,
    });
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

  const launchMatch = /^\/api\/v1\/assistant\/folders\/([^/]+)\/launch-process$/.exec(path);
  if (launchMatch && method === "POST") {
    const folderId = decodeURIComponent(launchMatch[1] ?? "");
    return jsonResponse({
      folder_id: folderId,
      workspace_id: String(body.workspace_id ?? ""),
      workflow_uri: String(body.target_workflow_uri ?? "orcia://pack-sdlc/workflows/ticket-to-tech-spec"),
      initiated_by_user_id: "0195f000-0000-7000-8000-000000000001",
      passthrough_identity: "marc@orcia.io",
      prefilled_contract_inputs: { source_folder_id: folderId },
      run_id: `0195f000-0000-7000-8000-${String(backendState.recordedCalls.length).padStart(12, "0")}`,
      run_status: "WAITING_FOR_HUMAN_ARBITRATION",
      dbos_workflow_id: null,
      waiting_step_keys: ["frame-spec-human-anchor"],
      executed_step_keys: [],
      snapshot_count: 0,
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

  return handleInboxAndBrokerRoute({ path, method, parsedUrl, body });
}
