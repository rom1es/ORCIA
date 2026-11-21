import { sanitizeAssistantDisplayReply } from "@orcia/ui";
import type {
  UiAssistantAttachedFileItem,
  UiAssistantFolderItem,
  UiAssistantSpeedMode,
  UiInferenceEffort,
  UiInferenceTier,
} from "@orcia/ui";
import type { SavedAssistantGovernancePrefs } from "./assistantFoldersAndPrefsStore";

export function buildThreeSpeedTurnRequestPayload(params: {
  readonly workspaceIdValue: string;
  readonly activeHat: string;
  readonly userPrompt: string;
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[];
  readonly requestedSpeed: UiAssistantSpeedMode;
  readonly deepAuditPillActive: boolean;
  readonly effectiveTier: UiInferenceTier;
  readonly effectiveEffort: UiInferenceEffort;
  readonly historyPayload: Array<{ role: "user" | "assistant"; content: string }>;
  readonly activeFolder?: UiAssistantFolderItem | null;
  readonly governancePrefs?: SavedAssistantGovernancePrefs;
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
    historyPayload,
    activeFolder,
    governancePrefs,
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
    conversation_history: historyPayload,
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

export async function pollActiveAssistantTurnUntilDone(params: {
  readonly signal: AbortSignal;
  readonly isCompletedHandled: () => boolean;
  readonly fetchStatus: () => Promise<{
    turn_id?: string | null;
    status?: string;
    thinking_text?: string | null;
    streamed_text?: string | null;
    assembled_system_prompt?: string | null;
    elapsed_ms?: number | null;
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
      const snap = await params.fetchStatus();
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
