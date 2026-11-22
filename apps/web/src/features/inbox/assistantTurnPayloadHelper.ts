import {
  sanitizeAssistantDisplayReply,
  type UiAgentTraceEventItem,
  type UiAssistantApprovalProposal,
  type UiAssistantAttachedFileItem,
  type UiAssistantFolderItem,
  type UiAssistantSpeedMode,
  type UiAssistantToolCallStatus,
  type UiAssistantToolCallStepItem,
  type UiFileBadgeCode,
  type UiInferenceEffort,
  type UiInferenceTier,
} from "@orcia/ui";
import type { SavedAssistantGovernancePrefs } from "./assistantFoldersAndPrefsStore";

export function buildAssistantTurnRequestPayload(params: {
  readonly workspaceIdValue: string;
  readonly activeHat: string;
  readonly userPrompt: string;
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[];
  readonly requestedSpeed: UiAssistantSpeedMode;
  readonly deepAuditPillActive: boolean;
  readonly effectiveTier: UiInferenceTier;
  readonly effectiveEffort: UiInferenceEffort;
  readonly threadId?: string | null;
  readonly activeFolder?: UiAssistantFolderItem | null;
  readonly governancePrefs?: SavedAssistantGovernancePrefs;
  readonly parentTurnId?: string;
  readonly isFr: boolean;
}) {
  const {
    workspaceIdValue,
    activeHat,
    userPrompt,
    attachedFiles,
    requestedSpeed,
    deepAuditPillActive,
    effectiveTier,
    effectiveEffort,
    threadId,
    activeFolder,
    governancePrefs,
    parentTurnId,
    isFr,
  } = params;
  const attachmentHeader = isFr
    ? "\n\n[Pièces jointes fournies par l'utilisateur]\n"
    : "\n\n[User-supplied attachments]\n";
  const attachmentContext =
    attachedFiles && attachedFiles.length > 0
      ? attachmentHeader +
        attachedFiles
          .map(
            (f) =>
              `- ${f.name}${f.uri ? ` (${f.uri})` : ""}${f.contentExcerpt ? ` : ${f.contentExcerpt}` : ""}`,
          )
          .join("\n")
      : "";
  const pinnedNotes = activeFolder?.pinnedNotesMarkdown?.trim() || undefined;
  return {
    workspace_id: workspaceIdValue,
    hat: activeHat,
    user_prompt: `${userPrompt}${attachmentContext}`,
    requested_speed: requestedSpeed,
    deep_audit_pill_active: deepAuditPillActive,
    requested_tier: effectiveTier,
    thinking_effort: (effectiveEffort === "default" ? "balanced" : effectiveEffort) as
      | "fast"
      | "balanced"
      | "deep",
    ...(threadId ? { thread_id: threadId } : {}),
    ...(parentTurnId ? { parent_turn_id: parentTurnId } : {}),
    ...(activeFolder?.folderId ? { folder_id: activeFolder.folderId } : {}),
    ...(pinnedNotes ? { folder_pinned_notes: pinnedNotes } : {}),
    ...(governancePrefs?.responseTone ? { response_tone: governancePrefs.responseTone } : {}),
    ...(governancePrefs?.favoriteFormat ? { response_format: governancePrefs.favoriteFormat } : {}),
    ...(governancePrefs?.personalInstructions
      ? { personal_instructions: governancePrefs.personalInstructions }
      : {}),
    ...(governancePrefs?.workspaceInstructions
      ? { workspace_instructions: governancePrefs.workspaceInstructions }
      : {}),
    locale: isFr ? "fr" : "en",
  };
}

export function upsertToolCallStepFromSse(
  prev: readonly UiAssistantToolCallStepItem[],
  eventName: "tool_call" | "tool_result",
  data: Readonly<Record<string, unknown>>,
): readonly UiAssistantToolCallStepItem[] {
  const toolCallId = String(data.tool_call_id ?? data.call_id ?? `${data.tool_name ?? "tool"}-${prev.length + 1}`);
  const toolName = String(data.tool_name ?? "tool");
  const rawStatus = String(data.status ?? (eventName === "tool_call" ? "RUNNING" : "EXECUTED"));
  const status: UiAssistantToolCallStatus =
    rawStatus === "RUNNING" ||
    rawStatus === "EXECUTED" ||
    rawStatus === "DENIED" ||
    rawStatus === "ERROR" ||
    rawStatus === "DEDUPLICATED" ||
    rawStatus === "APPROVAL_REQUIRED"
      ? rawStatus
      : eventName === "tool_call"
        ? "RUNNING"
        : "EXECUTED";
  const args = (data.sanitized_args ?? {}) as Readonly<Record<string, unknown>>;
  const targetUri =
    String(
      data.uri ??
        args.uri ??
        args.resource_uri ??
        (Array.isArray(data.evidence_refs) ? (data.evidence_refs[0] ?? "") : ""),
    ) || null;
  const startLine = Number(data.start_line ?? args.start_line ?? 0) || null;
  const endLine = Number(data.end_line ?? args.end_line ?? 0) || null;
  const durationMs = typeof data.duration_ms === "number" ? data.duration_ms : null;
  const summary = typeof data.summary === "string" ? data.summary : null;

  const entry: UiAssistantToolCallStepItem = {
    toolCallId,
    toolName,
    status,
    ...(summary ? { summary } : {}),
    ...(durationMs !== null ? { durationMs } : {}),
    ...(targetUri ? { targetUri } : {}),
    ...(startLine ? { startLine } : {}),
    ...(endLine ? { endLine } : {}),
  };
  const existingIdx = prev.findIndex((item) => item.toolCallId === toolCallId);
  if (existingIdx >= 0) {
    return prev.map((item, idx) => (idx === existingIdx ? { ...item, ...entry } : item));
  }
  return [...prev, entry];
}

export function buildApprovalProposalFromSse(
  data: Readonly<Record<string, unknown>>,
): UiAssistantApprovalProposal {
  return {
    proposalId: String(data.proposal_id ?? "prop-1"),
    actionKind: String(data.action_kind ?? data.tool_name ?? "PROPOSE_OR_CONTINUE"),
    targetUri: String(data.target_uri ?? ""),
    workflowRef: data.workflow_ref ? String(data.workflow_ref) : null,
    rationale: String(data.rationale ?? data.summary ?? ""),
    requiresHumanAnchor: data.requires_human_anchor === undefined ? true : Boolean(data.requires_human_anchor),
    status: "PENDING",
    runId: data.run_id ? String(data.run_id) : null,
  };
}

export function inferBadgeCodeFromUri(uri: string): UiFileBadgeCode {
  const lower = uri.toLowerCase();
  if (lower.endsWith(".py")) return "PY";
  if (lower.endsWith(".ts") || lower.endsWith(".tsx")) return "TS";
  if (lower.endsWith(".yaml") || lower.endsWith(".yml")) return "YML";
  if (lower.endsWith(".json")) return "JSON";
  return "MD";
}

export function buildTraceEventFromToolSse(params: {
  readonly eventName: "tool_call" | "tool_result";
  readonly data: Readonly<Record<string, unknown>>;
  readonly nextSeq: number;
  readonly isFr: boolean;
}): readonly UiAgentTraceEventItem[] {
  const { eventName, data, nextSeq, isFr } = params;
  const toolName = String(data.tool_name ?? "tool");
  const args = (data.sanitized_args ?? {}) as Readonly<Record<string, unknown>>;
  const uri = String(
    data.uri ??
      args.uri ??
      args.resource_uri ??
      (Array.isArray(data.evidence_refs) ? data.evidence_refs[0] ?? "" : ""),
  );
  const startLine = Number(data.start_line ?? args.start_line ?? 1) || 1;
  const endLine = Number(data.end_line ?? args.end_line ?? 25) || 25;
  const isFileRead = Boolean(uri) || /read|inspect|line|file/i.test(toolName);
  const items: UiAgentTraceEventItem[] = [];
  if (nextSeq <= 1) {
    items.push({
      eventId: `evt-grp-${nextSeq}`,
      sequence: nextSeq,
      kind: "GROUP_HEADER",
      label: isFr ? "Exploration et preuves" : "Exploration & evidence",
      actorSlug: "assistant",
      groupKey: "assistant-turn",
    });
  }
  const seq = nextSeq + items.length;
  items.push({
    eventId: `evt-${eventName}-${seq}`,
    sequence: seq,
    kind: eventName === "tool_result" && isFileRead ? "FILE_ANALYZED" : "CHECK_EXECUTED",
    label:
      eventName === "tool_call"
        ? isFr
          ? `Appel outil : ${toolName}`
          : `Calling tool: ${toolName}`
        : isFr
          ? `Résultat : ${toolName}`
          : `Result: ${toolName}`,
    actorSlug: "assistant",
    groupKey: "assistant-turn",
    ...(uri
      ? {
          resourceUri: uri,
          displayFilename: uri.split("/").pop() || uri,
          fileBadgeCode: inferBadgeCodeFromUri(uri),
          startLine,
          endLine,
          redacted: String(data.status ?? "") === "DENIED",
        }
      : {}),
  });
  return items;
}

export async function pollActiveAssistantTurnUntilDone(params: {
  readonly signal: AbortSignal;
  readonly isCompletedHandled: () => boolean;
  readonly getTargetTurnId: () => string | null;
  readonly fetchActiveTurns: () => Promise<{
    turns?: Array<{
      turn_id?: string | null;
      status?: string;
      thinking_text?: string | null;
      streamed_text?: string | null;
      assembled_system_prompt?: string | null;
      elapsed_ms?: number | null;
    }>;
  }>;
  readonly onThinking: (thinking: string) => void;
  readonly onStreamedText: (reply: string) => void;
  readonly onCompleted: (done: {
    turnId?: string;
    replyText: string;
    thinkingText: string;
    assembledSystemPrompt: string;
    latencyMs: number;
  }) => void;
  readonly getLatestThinking: () => string;
}): Promise<void> {
  for (let attempt = 0; attempt < 150; attempt += 1) {
    if (params.signal.aborted || params.isCompletedHandled()) return;
    try {
      const list = await params.fetchActiveTurns();
      const turns = list.turns ?? [];
      const targetId = params.getTargetTurnId();
      const snap =
        (targetId ? turns.find((t) => t.turn_id === targetId) : undefined) ?? turns[0];
      if (!snap) break;
      if (snap.thinking_text) params.onThinking(snap.thinking_text);
      if (snap.streamed_text) {
        params.onStreamedText(sanitizeAssistantDisplayReply(snap.streamed_text));
      }
      if (snap.status === "COMPLETED" && snap.streamed_text) {
        params.onCompleted({
          ...(snap.turn_id ? { turnId: snap.turn_id } : {}),
          replyText: snap.streamed_text,
          thinkingText: snap.thinking_text || params.getLatestThinking(),
          assembledSystemPrompt: snap.assembled_system_prompt || "",
          latencyMs: snap.elapsed_ms ?? 0,
        });
        return;
      }
      if (snap.status === "STOPPED" || snap.status === "ERROR" || snap.status === "IDLE") return;
    } catch (err: unknown) {
      console.warn(
        "[orcia:assistant.active_turn_poll]",
        err instanceof Error ? err.message : String(err),
      );
      break;
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
}
