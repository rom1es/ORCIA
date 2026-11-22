import { createOrciaApiClient } from "@orcia/api-client";
import { sanitizeAssistantDisplayReply } from "@orcia/ui";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import {
  bgSnapshot,
  clearBgTimers,
  getBgAbortController,
  setBgAbortController,
  updateBgSnapshot,
  type AssistantStreamErrorLabels,
} from "./assistantBackgroundStreamStore";
import { reattachAssistantTurnStream } from "./assistantStreamingRunner";

export function stopActiveAssistantTurn(isFr: boolean): void {
  const turnId = bgSnapshot.activeTurnId;
  getBgAbortController()?.abort();
  setBgAbortController(null);
  clearBgTimers();
  updateBgSnapshot({
    isGenerating: false,
    thinkingStartedAtMs: null,
    generationStopped: true,
    activeTraceStatus: bgSnapshot.activeTraceStatus ? "CANCELLED" : null,
    stepProgress: bgSnapshot.stepProgress.map((st) =>
      st.status === "RUNNING" ? { ...st, status: "COMPLETED" } : st,
    ),
  });
  if (turnId) {
    const client = createOrciaApiClient({ baseUrl: "", locale: isFr ? "fr" : "en" });
    void client.stopAssistantTurn(turnId).catch((err: unknown) => {
      const detail = err instanceof Error ? err.message : String(err);
      updateBgSnapshot({ generationStopped: true, errorKind: "stream_error", errorMessage: `⚠️ ${detail}` });
    });
  }
}

export async function synthesizeActiveAssistantTurn(isFr: boolean): Promise<void> {
  const turnId = bgSnapshot.activeTurnId;
  if (!turnId) return;
  updateBgSnapshot({ activeTraceStatus: "SYNTHESIZING" });
  const client = createOrciaApiClient({ baseUrl: "", locale: isFr ? "fr" : "en" });
  try {
    await client.synthesizeAssistantTurnNow(turnId);
  } catch (err: unknown) {
    const msg = formatRfc9457ErrorToBanner(err, isFr ? "fr" : "en", "Mon Assistant").fullText;
    updateBgSnapshot({ errorKind: "stream_error", errorMessage: msg });
  }
}

export async function decideAssistantTurnProposal(params: {
  readonly activeWorkspaceId: string;
  readonly isFr: boolean;
  readonly proposalId: string;
  readonly approved: boolean;
  readonly humanAnchorMarkdown?: string | undefined;
  readonly rationale?: string | undefined;
}): Promise<void> {
  const { activeWorkspaceId, isFr, proposalId, approved, humanAnchorMarkdown, rationale } = params;
  const turnId = bgSnapshot.activeTurnId;
  if (!turnId || !activeWorkspaceId) return;
  updateBgSnapshot({ approvalBusy: true, errorMessage: null, errorKind: null });
  const client = createOrciaApiClient({ baseUrl: "", locale: isFr ? "fr" : "en" });
  try {
    const resp = await client.approveAssistantTurnProposal(turnId, {
      workspace_id: activeWorkspaceId,
      proposal_id: proposalId,
      approved,
      human_authored_required: Boolean(bgSnapshot.approvalProposal?.requiresHumanAnchor),
      ...(humanAnchorMarkdown ? { human_anchor_markdown: humanAnchorMarkdown } : {}),
      ...(rationale ? { rationale } : {}),
      continue_in_process: true,
    });
    const prevProposal = bgSnapshot.approvalProposal;
    updateBgSnapshot({
      approvalBusy: false,
      pendingWritePreview: null,
      activeTraceStatus: approved ? "COMPLETED" : "CANCELLED",
      approvalProposal: prevProposal
        ? {
            ...prevProposal,
            status: approved ? "APPROVED" : "REJECTED",
            runId: resp.run_id ?? prevProposal.runId ?? null,
          }
        : null,
    });
  } catch (err: unknown) {
    const msg = formatRfc9457ErrorToBanner(err, isFr ? "fr" : "en", "Validation Assistant").fullText;
    updateBgSnapshot({ approvalBusy: false, errorKind: "stream_error", errorMessage: msg });
  }
}

export async function reattachAssistantRunningTurn(params: {
  readonly activeWorkspaceId: string;
  readonly isFr: boolean;
  readonly streamErrorLabels?: AssistantStreamErrorLabels | undefined;
}): Promise<void> {
  const { activeWorkspaceId, isFr, streamErrorLabels } = params;
  if (!activeWorkspaceId || bgSnapshot.isGenerating) return;
  try {
    const client = createOrciaApiClient({ baseUrl: "", locale: isFr ? "fr" : "en" });
    const activeList = await client.listActiveAssistantTurns(activeWorkspaceId);
    const runningTurn = (activeList.turns ?? []).find((t) => t.status === "RUNNING" && t.turn_id);
    if (!runningTurn?.turn_id) return;
    getBgAbortController()?.abort();
    const controller = new AbortController();
    setBgAbortController(controller);
    updateBgSnapshot({
      activeTurnId: runningTurn.turn_id,
      isGenerating: true,
      activeUserPrompt: runningTurn.user_prompt ?? bgSnapshot.activeUserPrompt,
      streamedText: sanitizeAssistantDisplayReply(runningTurn.streamed_text ?? bgSnapshot.streamedText),
    });
    reattachAssistantTurnStream({
      controller,
      turnId: runningTurn.turn_id,
      afterCursor: bgSnapshot.lastEventCursor ?? "0-0",
      workspaceIdValue: activeWorkspaceId,
      isFr,
      tStart: Date.now(),
      userPrompt: runningTurn.user_prompt ?? bgSnapshot.activeUserPrompt,
      streamErrorLabels,
    });
  } catch (err: unknown) {
    console.warn("[orcia:assistant.reattach]", err instanceof Error ? err.message : String(err));
  }
}
