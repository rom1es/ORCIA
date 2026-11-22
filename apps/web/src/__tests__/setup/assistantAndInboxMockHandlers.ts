import type { UiAssistantSpeedMode, UiInferenceEffort } from "@orcia/ui";
import {
  detectAdaptiveThinkingStepsForQuestion,
  shouldUseProgressiveStepThinking,
} from "../../features/inbox/assistantBackgroundStreamStore";
import { handleAssistantGovernanceAndThreadsRoute } from "./assistantGovernanceMockHandlers";
import { handleInboxAndBrokerRoute } from "./inboxAndBrokerMockHandlers";
import { backendState, buildSseStreamResponse, jsonResponse } from "./mockBackendState";

const vitestPendingTurns = new Map<
  string,
  { body: Record<string, unknown>; createdAt: number }
>();

function inferSupportsToolsFromMockModels(): boolean {
  const activeChat = backendState.aiModelMappings.filter(
    (m) => m.is_active !== false && !m.draining && m.usage !== "embedding",
  );
  if (activeChat.length === 0) return true;
  return activeChat.some((m) => {
    const eff = m.supports_tools_override ?? m.supports_tools;
    return eff === undefined || eff === null ? true : Boolean(eff);
  });
}

function buildSseFrame(idSeq: number, eventName: string, data: Record<string, unknown>): string {
  return `id: ${idSeq}-0\nevent: ${eventName}\ndata: ${JSON.stringify(data)}\n\n`;
}

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
    const requestedSpeed = String(stored.requested_speed ?? "SPEED_1_FAST") as UiAssistantSpeedMode;
    const thinkingEffort = String(stored.thinking_effort ?? "balanced") as UiInferenceEffort;
    const isFr = String(stored.locale ?? "fr") !== "en";
    const fullUserPrompt = String(stored.user_prompt ?? "");
    const cleanPrompt =
      fullUserPrompt.split(/\n\n\[(?:Pièces jointes|User-supplied attachments)/)[0] ??
      fullUserPrompt;
    const replyText = `[${requestedSpeed}] ${cleanPrompt}`;
    const assembledSystemPrompt = `[ROLE=${hat}] [SPEED=${requestedSpeed}] [EFFORT=${thinkingEffort}]`;

    const useSteps = shouldUseProgressiveStepThinking({
      userPrompt: cleanPrompt,
      requestedSpeed,
      deepAuditPillActive: Boolean(stored.deep_audit_pill_active),
      thinkingEffort,
    });
    const plannedSteps = useSteps ? detectAdaptiveThinkingStepsForQuestion(cleanPrompt, isFr) : [];
    const thinkingText = plannedSteps.map((s) => `${s.label}: ${s.intermediateOutput ?? ""}`).join(" · ");

    const mockCitationMap =
      ((globalThis as Record<string, unknown>).__ORCIA_TEST_CITATION_MAP__ as Record<string, unknown> | undefined) ??
      {};
    const emitApproval = Boolean((globalThis as Record<string, unknown>).__ORCIA_TEST_EMIT_APPROVAL__);
    const supportsTools = inferSupportsToolsFromMockModels();

    const numberedFrames: Array<{ seq: number; frame: string }> = [];
    if (useSteps) {
      numberedFrames.push(
        { seq: 1, frame: buildSseFrame(1, "thinking_delta", { turn_id: turnId, seq: 1, thinking_text: thinkingText || "Analyse..." }) },
        { seq: 2, frame: buildSseFrame(2, "tool_call", { turn_id: turnId, tool_call_id: "tc-1", seq: 2, tool_name: "surgical_read_lines", status: "RUNNING", sanitized_args: { uri: "docs/product/capabilities.yaml", start_line: 1, end_line: 25 } }) },
        { seq: 3, frame: buildSseFrame(3, "tool_result", { turn_id: turnId, tool_call_id: "tc-1", seq: 3, tool_name: "surgical_read_lines", status: "EXECUTED", duration_ms: 14, evidence_refs: ["docs/product/capabilities.yaml"], uri: "docs/product/capabilities.yaml", start_line: 1, end_line: 25, summary: "25 lines read" }) },
      );
    }
    if (emitApproval) {
      numberedFrames.push({
        seq: 4,
        frame: buildSseFrame(4, "approval_required", {
          turn_id: turnId,
          proposal_id: "prop-e2e-1",
          action_kind: "PROPOSE_OR_CONTINUE",
          target_uri: "docs/spec.md",
          workflow_ref: "orcia://pack-sdlc/workflows/ticket-to-tech-spec",
          requires_human_anchor: true,
          summary: "Update technical specification after audit.",
        }),
      });
    }
    numberedFrames.push(
      { seq: 5, frame: buildSseFrame(5, "token_delta", { turn_id: turnId, seq: 5, accumulated_text: replyText }) },
      { seq: 6, frame: buildSseFrame(6, "citation_map", { turn_id: turnId, seq: 6, ...mockCitationMap, purged_phantom_count: 0 }) },
      {
        seq: 7,
        frame: buildSseFrame(7, "turn_completed", {
          turn_id: turnId,
          seq: 7,
          response_text: replyText,
          thinking_text: thinkingText,
          assembled_system_prompt: assembledSystemPrompt,
          latency_ms: plannedSteps.length > 0 ? 3000 : 1000,
          low_evidence: !Array.isArray(mockCitationMap.sources) || mockCitationMap.sources.length === 0,
          supports_tools: supportsTools,
          citation_map: mockCitationMap,
        }),
      },
    );

    const afterRaw = parsedUrl.searchParams.get("after");
    const afterSeq = afterRaw ? Number.parseInt(afterRaw.split("-")[0] ?? "0", 10) || 0 : 0;
    const slicedFrames = numberedFrames.filter((f) => f.seq > afterSeq).map((f) => f.frame);

    const threadId = typeof stored.thread_id === "string" ? stored.thread_id : null;
    if (threadId && afterSeq === 0) {
      const wsId = String(stored.workspace_id ?? "0195f000-0000-7000-8000-000000000301");
      const nowIso = new Date().toISOString();
      backendState.assistantThreadMessages = [
        ...backendState.assistantThreadMessages,
        {
          message_id: `msg-u-${turnId}`,
          thread_id: threadId,
          workspace_id: wsId,
          turn_id: turnId,
          parent_turn_id: stored.parent_turn_id ?? null,
          role: "user",
          content: cleanPrompt,
          created_at: nowIso,
        },
        {
          message_id: `msg-a-${turnId}`,
          thread_id: threadId,
          workspace_id: wsId,
          turn_id: turnId,
          parent_turn_id: stored.parent_turn_id ?? null,
          role: "assistant",
          content: replyText,
          citation_map: mockCitationMap,
          created_at: nowIso,
        },
      ];
    }

    return buildSseStreamResponse(slicedFrames);
  }

  if (path === "/api/v1/assistant/turns/active" && method === "GET") {
    return jsonResponse({ workspace_id: parsedUrl.searchParams.get("workspace_id") ?? "", turns: [] });
  }

  const turnActionMatch =
    /^\/api\/v1\/assistant\/turns\/([^/]+)\/(stop|synthesize-now|approve|feedback)$/.exec(path);
  if (turnActionMatch && method === "POST") {
    const turnId = decodeURIComponent(turnActionMatch[1] ?? "");
    const action = turnActionMatch[2];
    if (action === "stop") {
      return jsonResponse({ workspace_id: String(body.workspace_id ?? ""), turn_id: turnId, status: "STOPPED", streamed_text: "", thinking_text: "" });
    }
    if (action === "synthesize-now") {
      return jsonResponse({ turn_id: turnId, workspace_id: String(body.workspace_id ?? ""), status: "SYNTHESIZING", message: "Early synthesis requested." }, 202);
    }
    if (action === "approve") {
      return jsonResponse({
        turn_id: turnId,
        proposal_id: String(body.proposal_id ?? "prop-1"),
        workspace_id: String(body.workspace_id ?? ""),
        approved: Boolean(body.approved ?? true),
        status: body.approved === false ? "REJECTED" : "APPROVED",
        run_id: "0195f000-0000-7000-8000-000000000909",
        run_status: "RUNNING",
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
    return jsonResponse({ folder_id: folderId, workspace_id: folder.workspace_id, visibility_mode: body.visibility_mode, shares: [], has_restricted_sources: folder.has_restricted_sources });
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

  const govOrThreadResp = handleAssistantGovernanceAndThreadsRoute({ path, method, parsedUrl, body });
  if (govOrThreadResp) return govOrThreadResp;

  return handleInboxAndBrokerRoute({ path, method, parsedUrl, body });
}
