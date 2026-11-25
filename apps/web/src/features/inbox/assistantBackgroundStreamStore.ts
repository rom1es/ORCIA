import { OrciaProblemError } from "@orcia/api-client";
import type {
  UiAgentTraceEventItem,
  UiAssistantApprovalProposal,
  UiAssistantAttachedFileItem,
  UiAssistantErrorKind,
  UiAssistantSpeedMode,
  UiAssistantToolCallStepItem,
  UiInferenceEffort,
  UiInferenceTier,
  UiReflexivePendingWritePreview,
  UiReflexiveSessionStatus,
  UiThreeSpeedStepProgress,
} from "@orcia/ui";
import { CATEGORY_A_CONTROLLER_BY_LOCALE } from "../../i18n/locales/category_a_controller_labels";
import { resolveLocalizedClientError } from "../../lib/formatRfc9457ErrorToBanner";

export interface CompletedAssistantTurnPayload {
  readonly turnId?: string;
  readonly threadId?: string | null;
  readonly parentTurnId?: string | null;
  readonly userPrompt: string;
  readonly assistantReply: string;
  readonly assembledSystemPrompt?: string;
  readonly thinkingText?: string;
  readonly conversationHistoryCount?: number;
  readonly folderTitle?: string | null;
  readonly folderPinnedNotes?: string | null;
  readonly requestedTier: UiInferenceTier;
  readonly thinkingEffort: UiInferenceEffort;
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[];
  readonly stepProgress?: readonly UiThreeSpeedStepProgress[];
  readonly thinkingElapsedSeconds?: number;
  readonly traceEvents?: readonly UiAgentTraceEventItem[];
  readonly toolCallSteps?: readonly UiAssistantToolCallStepItem[];
  readonly approvalProposal?: UiAssistantApprovalProposal | null;
  readonly citationMap?: Readonly<Record<string, unknown>> | null;
  readonly lowEvidence?: boolean;
  readonly supportsTools?: boolean;
}

export interface BackgroundAssistantStreamSnapshot {
  activeTurnId: string | null;
  activeThreadId: string | null;
  lastEventCursor: string | null;
  streamedText: string;
  activeUserPrompt: string;
  stepProgress: readonly UiThreeSpeedStepProgress[];
  activeTraceStatus: UiReflexiveSessionStatus | null;
  traceEvents: readonly UiAgentTraceEventItem[];
  toolCallSteps: readonly UiAssistantToolCallStepItem[];
  approvalProposal: UiAssistantApprovalProposal | null;
  approvalBusy: boolean;
  pendingWritePreview: UiReflexivePendingWritePreview | null;
  citationMap: Readonly<Record<string, unknown>> | null;
  lowEvidence: boolean;
  supportsTools: boolean;
  purgedPhantomCount: number;
  cacheHit: boolean;
  cacheLookupMs: number;
  nodes1To4Ms: number;
  ttftMs: number;
  isGenerating: boolean;
  thinkingStartedAtMs: number | null;
  generationStopped: boolean;
  errorMessage: string | null;
  errorKind: UiAssistantErrorKind | null;
}

const bgListeners = new Set<() => void>();
let bgAbortController: AbortController | null = null;
let bgTimers: ReturnType<typeof setTimeout>[] = [];
let bgOnTurnCompletedCallback: ((params: CompletedAssistantTurnPayload) => void) | null = null;

export let bgSnapshot: BackgroundAssistantStreamSnapshot = {
  activeTurnId: null,
  activeThreadId: null,
  lastEventCursor: null,
  streamedText: "",
  activeUserPrompt: "",
  stepProgress: [],
  activeTraceStatus: null,
  traceEvents: [],
  toolCallSteps: [],
  approvalProposal: null,
  approvalBusy: false,
  pendingWritePreview: null,
  citationMap: null,
  lowEvidence: false,
  supportsTools: true,
  purgedPhantomCount: 0,
  cacheHit: false,
  cacheLookupMs: 0,
  nodes1To4Ms: 0,
  ttftMs: 0,
  isGenerating: false,
  thinkingStartedAtMs: null,
  generationStopped: false,
  errorMessage: null,
  errorKind: null,
};

export function subscribeBgStream(listener: () => void): () => void {
  bgListeners.add(listener);
  return () => {
    bgListeners.delete(listener);
  };
}

export function setBgOnTurnCompletedCallback(
  cb: ((params: CompletedAssistantTurnPayload) => void) | null,
): void {
  bgOnTurnCompletedCallback = cb;
}

export function invokeBgOnTurnCompleted(params: CompletedAssistantTurnPayload): void {
  bgOnTurnCompletedCallback?.(params);
}

export function getBgAbortController(): AbortController | null {
  return bgAbortController;
}

export function setBgAbortController(controller: AbortController | null): void {
  bgAbortController = controller;
}

export function clearBgTimers(): void {
  for (const t of bgTimers) clearTimeout(t);
  bgTimers = [];
}

export function addBgTimer(timer: ReturnType<typeof setTimeout>): void {
  bgTimers.push(timer);
}

export function updateBgSnapshot(patch: Partial<BackgroundAssistantStreamSnapshot>): void {
  bgSnapshot = { ...bgSnapshot, ...patch };
  for (const listener of bgListeners) listener();
}

export function resetBackgroundAssistantStreamForTests(): void {
  bgAbortController?.abort();
  bgAbortController = null;
  clearBgTimers();
  bgSnapshot = {
    activeTurnId: null,
    activeThreadId: null,
    lastEventCursor: null,
    streamedText: "",
    activeUserPrompt: "",
    stepProgress: [],
    activeTraceStatus: null,
    traceEvents: [],
    toolCallSteps: [],
    approvalProposal: null,
    approvalBusy: false,
    pendingWritePreview: null,
    citationMap: null,
    lowEvidence: false,
    supportsTools: true,
    purgedPhantomCount: 0,
    cacheHit: false,
    cacheLookupMs: 0,
    nodes1To4Ms: 0,
    ttftMs: 0,
    isGenerating: false,
    thinkingStartedAtMs: null,
    generationStopped: false,
    errorMessage: null,
    errorKind: null,
  };
}

export function detectAdaptiveThinkingStepsForQuestion(
  userPrompt: string,
  useFrench = true,
): readonly UiThreeSpeedStepProgress[] {
  const lower = userPrompt.toLowerCase();
  const thinkingDict =
    CATEGORY_A_CONTROLLER_BY_LOCALE[useFrench ? "fr" : "en"].assistantThinking;
  const templates =
    /\b(code|coder|fonction|python|sql|bug|script|algorithme|api|test|typescript|react|classe|boucle|erreur)\b/i.test(
      lower,
    )
      ? thinkingDict.code
      : /\b(explique|expliquer|résume|résumer|document|contrat|texte|synthèse|rapport|note|dossier|extrait)\b/i.test(
            lower,
          )
        ? thinkingDict.explain
        : /\b(choisir|comparer|comparaison|option|options|avantage|avantages|risque|risques|pourquoi|quel|quelle|quels|quelles|arbitrage|versus)\b/i.test(
              lower,
            )
          ? thinkingDict.compare
          : thinkingDict.fallback;

  return templates.map((step) => ({
    stepCode: step.stepCode,
    label: step.label,
    durationMs: step.durationMs,
    status: "COMPLETED",
    intermediateOutput: step.intermediateOutput,
  }));
}

export function shouldUseProgressiveStepThinking(params: {
  readonly userPrompt: string;
  readonly requestedSpeed: UiAssistantSpeedMode;
  readonly deepAuditPillActive: boolean;
  readonly thinkingEffort?: UiInferenceEffort;
}): boolean {
  if (
    params.deepAuditPillActive ||
    params.thinkingEffort === "deep" ||
    params.requestedSpeed === "SPEED_3_DEEP_AUDIT" ||
    params.requestedSpeed === "SPEED_2_AGENT_TOOLS"
  ) {
    return true;
  }
  return /(?:^|\s)(@[a-zA-Z0-9_-]+|\/[a-zA-Z0-9_-]+)/.test(params.userPrompt);
}

export interface AssistantStreamErrorLabels {
  readonly sessionExpiredMessage: string;
  readonly aiUnavailableMessage: (detail?: string) => string;
}

export function extractHttpErrorStatus(err: unknown): number | null {
  if (err instanceof OrciaProblemError) {
    return err.problem.status ?? null;
  }
  if (err && typeof err === "object" && "problem" in err) {
    const prob = (err as { problem?: { status?: unknown } }).problem;
    if (prob && typeof prob.status === "number") {
      return prob.status;
    }
  }
  return null;
}

export function classifyAssistantStreamError(
  err: unknown,
  useFrench: boolean,
  labels?: AssistantStreamErrorLabels,
): { readonly errorKind: UiAssistantErrorKind; readonly errorMessage: string } {
  const activeLocale: "fr" | "en" = useFrench ? "fr" : "en";
  const status = extractHttpErrorStatus(err);
  if (status === 401 || status === 403) {
    return {
      errorKind: "auth_expired",
      errorMessage:
        labels?.sessionExpiredMessage ??
        resolveLocalizedClientError("ERR_CLIENT_SESSION_EXPIRED", activeLocale),
    };
  }
  const detail =
    err instanceof OrciaProblemError
      ? err.problem.detail
      : err instanceof Error
        ? err.message
        : resolveLocalizedClientError("ERR_CLIENT_NETWORK", activeLocale);
  if (status === 502 || status === 503 || status === 504 || status === null) {
    return {
      errorKind: "ai_unavailable",
      errorMessage: labels
        ? labels.aiUnavailableMessage(detail)
        : resolveLocalizedClientError("ERR_CLIENT_AI_UNAVAILABLE", activeLocale, { detail }),
    };
  }
  return {
    errorKind: "stream_error",
    errorMessage: `${detail}`,
  };
}
