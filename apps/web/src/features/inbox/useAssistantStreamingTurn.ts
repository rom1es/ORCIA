import { createOrciaApiClient } from "@orcia/api-client";
import {
  sanitizeAssistantDisplayReply,
  type UiAssistantAttachedFileItem,
  type UiAssistantFolderItem,
  type UiAssistantSpeedMode,
  type UiInferenceEffort,
  type UiInferenceTier,
  type UiThreeSpeedStepProgress,
} from "@orcia/ui";
import { useEffect, useRef, useState } from "react";
import type { SavedAssistantGovernancePrefs } from "./assistantFoldersAndPrefsStore";
import type { SavedAssistantConversation } from "./savedConversationsStore";

export interface UseAssistantStreamingTurnOptions {
  readonly activeWorkspaceId: string;
  readonly isFr: boolean;
  readonly isJsdom: boolean;
  readonly initialStreamedText: string;
  readonly activeConversation?: SavedAssistantConversation | null;
  readonly activeFolder?: UiAssistantFolderItem | null;
  readonly governancePrefs?: SavedAssistantGovernancePrefs;
  readonly onTurnCompleted: (params: {
    userPrompt: string;
    assistantReply: string;
    requestedTier: UiInferenceTier;
    thinkingEffort: UiInferenceEffort;
    attachedFiles?: readonly UiAssistantAttachedFileItem[];
    stepProgress?: readonly UiThreeSpeedStepProgress[];
    thinkingElapsedSeconds?: number;
  }) => void;
}

export interface SendAssistantTurnPayload {
  readonly userPrompt: string;
  readonly requestedSpeed: UiAssistantSpeedMode;
  readonly deepAuditPillActive: boolean;
  readonly requestedTier?: UiInferenceTier;
  readonly thinkingEffort?: UiInferenceEffort;
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[];
}

export function detectAdaptiveThinkingStepsForQuestion(
  userPrompt: string,
  isFr = true,
): readonly UiThreeSpeedStepProgress[] {
  const lower = userPrompt.toLowerCase();
  const buildStep = (
    stepCode: string,
    label: string,
    durationMs: number,
    intermediateOutput: string,
  ): UiThreeSpeedStepProgress => ({
    stepCode,
    label,
    durationMs,
    status: "COMPLETED",
    intermediateOutput,
  });

  if (/\b(code|coder|fonction|python|sql|bug|script|algorithme|api|test|typescript|react|classe|boucle|erreur)\b/i.test(lower)) {
    return [
      buildStep("STEP_1_SPEC_EDGE_CASES", isFr ? "Spécification et cas limites" : "Specification and edge cases", 1100, isFr ? "Cadrage des entrées/sorties, complexité et cas particuliers pour la demande." : "Framing inputs/outputs, complexity, and edge cases for the request."),
      buildStep("STEP_2_IMPLEMENTATION_DESIGN", isFr ? "Conception de l'implémentation" : "Implementation design", 1400, isFr ? "Structuration du code et choix techniques adaptés." : "Code structuring and technical choices."),
      buildStep("STEP_3_VERIFICATION_EXAMPLE", isFr ? "Vérification et exemple d'usage" : "Verification and usage example", 900, isFr ? "Contrôle de validité et préparation d'un cas de test." : "Validity check and test case preparation."),
    ];
  }
  if (/\b(explique|expliquer|résume|résumer|document|contrat|texte|synthèse|rapport|note|dossier|extrait)\b/i.test(lower)) {
    return [
      buildStep("STEP_1_KEY_POINTS_EXTRACTION", isFr ? "Extraction des points clés" : "Extracting key points", 1100, isFr ? "Repérage des idées principales et de la structure." : "Identifying main ideas and structure."),
      buildStep("STEP_2_WORKSPACE_CONTEXT_CROSS", isFr ? "Croisement avec le contexte de l'espace" : "Cross-referencing workspace context", 1300, isFr ? "Mise en regard avec le glossaire et les règles métiers." : "Aligning with glossary and business rules."),
      buildStep("STEP_3_PEDAGOGICAL_STRUCTURING", isFr ? "Structuration pédagogique" : "Pedagogical structuring", 900, isFr ? "Organisation claire de l'explication." : "Clear organization of the explanation."),
    ];
  }
  if (/\b(choisir|comparer|comparaison|option|options|avantage|avantages|risque|risques|pourquoi|quel|quelle|quels|quelles|arbitrage|versus)\b/i.test(lower)) {
    return [
      buildStep("STEP_1_EVALUATION_CRITERIA", isFr ? "Critères d'évaluation" : "Evaluation criteria", 1000, isFr ? "Définition des axes de comparaison pertinents." : "Defining relevant comparison axes."),
      buildStep("STEP_2_OPTIONS_AND_RISKS", isFr ? "Analyse des options et points de vigilance" : "Analyzing options and watchpoints", 1400, isFr ? "Pesée des avantages et limites de chaque piste." : "Weighing pros and limitations of each option."),
      buildStep("STEP_3_ARGUED_RECOMMENDATION", isFr ? "Recommandation argumentée" : "Reasoned recommendation", 900, isFr ? "Synthèse décisionnelle structurée." : "Structured decision summary."),
    ];
  }
  return [
    buildStep("STEP_1_REQUEST_FRAMING", isFr ? "Cadrage de la demande" : "Framing the request", 1000, isFr ? "Identification des objectifs et du périmètre de la question." : "Identifying objectives and scope of the question."),
    buildStep("STEP_2_DEEP_ANALYSIS_SOURCES", isFr ? "Analyse approfondie et sources" : "In-depth analysis and sources", 1400, isFr ? "Exploration détaillée des éléments de réponse et références." : "Detailed exploration of answer elements and references."),
    buildStep("STEP_3_RESPONSE_CONSOLIDATION", isFr ? "Consolidation de la réponse" : "Response consolidation", 900, isFr ? "Mise en forme structurée et synthétique." : "Structured and concise formatting."),
  ];
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

export function buildConversationHistoryPayload(
  conversation?: SavedAssistantConversation | null,
): Array<{ role: "user" | "assistant"; content: string }> {
  if (!conversation || !conversation.turns.length) return [];
  const history: Array<{ role: "user" | "assistant"; content: string }> = [];
  for (const turn of conversation.turns) {
    if (turn.userPrompt.trim()) history.push({ role: "user", content: turn.userPrompt.trim() });
    if (turn.assistantReply.trim()) {
      history.push({ role: "assistant", content: turn.assistantReply.trim() });
    }
  }
  return history;
}

interface BackgroundAssistantStreamSnapshot {
  streamedText: string;
  activeUserPrompt: string;
  stepProgress: readonly UiThreeSpeedStepProgress[];
  cacheHit: boolean;
  cacheLookupMs: number;
  nodes1To4Ms: number;
  ttftMs: number;
  isGenerating: boolean;
  thinkingStartedAtMs: number | null;
  generationStopped: boolean;
  errorMessage: string | null;
}

const bgListeners = new Set<() => void>();
let bgAbortController: AbortController | null = null;
let bgTimers: ReturnType<typeof setTimeout>[] = [];
let bgOnTurnCompletedCallback: UseAssistantStreamingTurnOptions["onTurnCompleted"] | null = null;

let bgSnapshot: BackgroundAssistantStreamSnapshot = {
  streamedText: "",
  activeUserPrompt: "",
  stepProgress: [],
  cacheHit: false,
  cacheLookupMs: 0,
  nodes1To4Ms: 0,
  ttftMs: 0,
  isGenerating: false,
  thinkingStartedAtMs: null,
  generationStopped: false,
  errorMessage: null,
};

function clearBgTimers() {
  for (const t of bgTimers) clearTimeout(t);
  bgTimers = [];
}

function updateBgSnapshot(patch: Partial<BackgroundAssistantStreamSnapshot>) {
  bgSnapshot = { ...bgSnapshot, ...patch };
  for (const listener of bgListeners) listener();
}

export function resetBackgroundAssistantStreamForTests() {
  bgAbortController?.abort();
  bgAbortController = null;
  clearBgTimers();
  bgSnapshot = {
    streamedText: "",
    activeUserPrompt: "",
    stepProgress: [],
    cacheHit: false,
    cacheLookupMs: 0,
    nodes1To4Ms: 0,
    ttftMs: 0,
    isGenerating: false,
    thinkingStartedAtMs: null,
    generationStopped: false,
    errorMessage: null,
  };
}

export function useAssistantStreamingTurn({
  activeWorkspaceId,
  isFr,
  isJsdom,
  initialStreamedText,
  activeConversation = null,
  activeFolder = null,
  governancePrefs,
  onTurnCompleted,
}: UseAssistantStreamingTurnOptions) {
  bgOnTurnCompletedCallback = onTurnCompleted;
  const initializedRef = useRef(false);
  if (!initializedRef.current) {
    initializedRef.current = true;
    if (!bgSnapshot.isGenerating && !bgSnapshot.streamedText && initialStreamedText) {
      bgSnapshot = {
        ...bgSnapshot,
        streamedText: sanitizeAssistantDisplayReply(initialStreamedText),
      };
    }
  }

  const [, setTick] = useState(0);
  useEffect(() => {
    const listener = () => setTick((n) => n + 1);
    bgListeners.add(listener);
    // Intentionally DO NOT abort bgAbortController on unmount so thinking continues across ORCIA screens!
    return () => {
      bgListeners.delete(listener);
    };
  }, []);

  const setStreamedText = (next: string) => {
    updateBgSnapshot({ streamedText: sanitizeAssistantDisplayReply(next) });
  };

  const stopGeneration = () => {
    bgAbortController?.abort();
    bgAbortController = null;
    clearBgTimers();
    updateBgSnapshot({
      isGenerating: false,
      thinkingStartedAtMs: null,
      generationStopped: true,
      stepProgress: bgSnapshot.stepProgress.map((st) =>
        st.status === "RUNNING" ? { ...st, status: "COMPLETED" } : st,
      ),
    });
  };

  const resetStreamState = (nextText = "") => {
    bgAbortController?.abort();
    bgAbortController = null;
    clearBgTimers();
    updateBgSnapshot({
      isGenerating: false,
      thinkingStartedAtMs: null,
      generationStopped: false,
      activeUserPrompt: "",
      streamedText: sanitizeAssistantDisplayReply(nextText),
      stepProgress: [],
      nodes1To4Ms: 0,
      errorMessage: null,
    });
  };

  const sendTurn = ({
    userPrompt,
    requestedSpeed,
    deepAuditPillActive,
    requestedTier,
    thinkingEffort,
    attachedFiles,
  }: SendAssistantTurnPayload) => {
    bgAbortController?.abort();
    clearBgTimers();

    const controller = new AbortController();
    bgAbortController = controller;

    const effectiveTier: UiInferenceTier = requestedTier ?? "medium";
    const effectiveEffort: UiInferenceEffort =
      thinkingEffort ?? (deepAuditPillActive ? "deep" : "balanced");
    const useSteps = shouldUseProgressiveStepThinking({
      userPrompt,
      requestedSpeed,
      deepAuditPillActive,
      thinkingEffort: effectiveEffort,
    });
    const plannedSteps = useSteps ? detectAdaptiveThinkingStepsForQuestion(userPrompt, isFr) : [];
    const tStart = Date.now();

    updateBgSnapshot({
      errorMessage: null,
      generationStopped: false,
      isGenerating: true,
      thinkingStartedAtMs: tStart,
      activeUserPrompt: userPrompt,
      streamedText: "",
      stepProgress:
        useSteps && plannedSteps.length > 0
          ? [{ ...plannedSteps[0]!, status: "RUNNING", durationMs: 0 }]
          : [],
    });

    if (isJsdom && !(globalThis as Record<string, unknown>).__ORCIA_TEST_KEEP_STREAM_PENDING__) {
      const jsdomReply = `[${requestedSpeed}] ${userPrompt}`;
      const completedSteps = plannedSteps.map((st) => ({ ...st, status: "COMPLETED" as const }));
      updateBgSnapshot({
        stepProgress: completedSteps,
        isGenerating: false,
        thinkingStartedAtMs: null,
        streamedText: jsdomReply,
      });
      bgOnTurnCompletedCallback?.({
        userPrompt,
        assistantReply: jsdomReply,
        requestedTier: effectiveTier,
        thinkingEffort: effectiveEffort,
        ...(attachedFiles ? { attachedFiles } : {}),
        ...(completedSteps.length > 0 ? { stepProgress: completedSteps } : {}),
        thinkingElapsedSeconds: completedSteps.length > 0 ? 3 : 1,
      });
      return;
    }

    if (isJsdom && (globalThis as Record<string, unknown>).__ORCIA_TEST_KEEP_STREAM_PENDING__) {
      return;
    }

    if (useSteps && plannedSteps.length >= 3) {
      const advanceStep = (idx: 1 | 2) => {
        if (controller.signal.aborted) return;
        if (bgSnapshot.stepProgress.some((s) => s.stepCode === "LIVE_MODEL_REASONING")) return;
        updateBgSnapshot({
          stepProgress:
            idx === 1
              ? [
                  { ...plannedSteps[0]!, status: "COMPLETED", durationMs: 1200 },
                  { ...plannedSteps[1]!, status: "RUNNING", durationMs: 0 },
                ]
              : [
                  { ...plannedSteps[0]!, status: "COMPLETED", durationMs: 1200 },
                  { ...plannedSteps[1]!, status: "COMPLETED", durationMs: 1400 },
                  { ...plannedSteps[2]!, status: "RUNNING", durationMs: 0 },
                ],
        });
      };
      bgTimers.push(
        setTimeout(() => advanceStep(1), 1200),
        setTimeout(() => advanceStep(2), 2600),
      );
    }

    const attachmentContext =
      attachedFiles && attachedFiles.length > 0
        ? "\n\n[Pièces jointes fournies par l'utilisateur]\n" +
          attachedFiles
            .map((f) => `- ${f.name}${f.uri ? ` (${f.uri})` : ""}${f.contentExcerpt ? ` : ${f.contentExcerpt}` : ""}`)
            .join("\n")
        : "";
    const enrichedPrompt = `${userPrompt}${attachmentContext}`;
    const historyPayload = buildConversationHistoryPayload(activeConversation);
    const activeHat = governancePrefs?.defaultHat || "PM";
    const pinnedNotes = activeFolder?.pinnedNotesMarkdown?.trim() || undefined;
    const requestPayload = {
      workspace_id: activeWorkspaceId || "0195f000-0000-7000-8000-000000000301",
      hat: activeHat,
      user_prompt: enrichedPrompt,
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

    const client = createOrciaApiClient({ baseUrl: "" });
    let latestThinking = "";
    let latestReply = "";
    let hasStreamError = false;

    void client
      .streamAssistantTurnSse(requestPayload, {
        signal: controller.signal,
        onEvent: (eventName, data) => {
          if (controller.signal.aborted) return;
          if (eventName === "cache_status") {
            updateBgSnapshot({
              cacheHit: Boolean(data.cache_hit),
              cacheLookupMs: Number(data.cache_lookup_ms ?? 0),
            });
          } else if (eventName === "thinking_delta") {
            const txt = String(data.thinking_text ?? "").trim();
            if (!txt) return;
            clearBgTimers();
            latestThinking = txt;
            updateBgSnapshot({
              stepProgress: [
                {
                  stepCode: "LIVE_MODEL_REASONING",
                  label: isFr ? "Raisonnement du modèle en cours" : "Model reasoning in progress",
                  durationMs: Number(data.elapsed_ms ?? Date.now() - tStart),
                  status: "RUNNING",
                  intermediateOutput: txt,
                },
              ],
            });
          } else if (eventName === "token_delta") {
            clearBgTimers();
            const acc = sanitizeAssistantDisplayReply(String(data.accumulated_text ?? ""));
            if (!acc) return;
            const nextTtft = !latestReply ? Date.now() - tStart : bgSnapshot.ttftMs;
            latestReply = acc;
            updateBgSnapshot({
              ttftMs: nextTtft,
              streamedText: acc,
              stepProgress: bgSnapshot.stepProgress.map((st) =>
                st.status === "RUNNING" ? { ...st, status: "COMPLETED" } : st,
              ),
            });
          } else if (eventName === "stream_error") {
            hasStreamError = true;
            clearBgTimers();
            updateBgSnapshot({
              isGenerating: false,
              thinkingStartedAtMs: null,
              stepProgress: bgSnapshot.stepProgress.map((st) =>
                st.status === "RUNNING" ? { ...st, status: "COMPLETED" } : st,
              ),
              errorMessage: `⚠️ ${String(data.message ?? "Erreur du fournisseur IA")}`,
            });
          } else if (eventName === "turn_completed") {
            clearBgTimers();
            const finalRaw = sanitizeAssistantDisplayReply(
              String(data.response_text ?? latestReply),
            );
            const finalReply = finalRaw || latestReply;
            const elapsedSec = Math.max(1, Math.round((Date.now() - tStart) / 1000));
            const finalSteps: readonly UiThreeSpeedStepProgress[] = latestThinking
              ? [
                  {
                    stepCode: "LIVE_MODEL_REASONING",
                    label: isFr ? "Raisonnement du modèle" : "Model reasoning",
                    durationMs: Number(data.latency_ms ?? elapsedSec * 1000),
                    status: "COMPLETED",
                    intermediateOutput: latestThinking,
                  },
                ]
              : useSteps
                ? plannedSteps.map((st) => ({ ...st, status: "COMPLETED" as const }))
                : [];
            updateBgSnapshot({
              stepProgress: finalSteps,
              streamedText: finalReply,
              isGenerating: false,
              thinkingStartedAtMs: null,
            });
            if (finalReply && !/^synthèse conforme pour\s*«/i.test(finalReply)) {
              bgOnTurnCompletedCallback?.({
                userPrompt,
                assistantReply: finalReply,
                requestedTier: effectiveTier,
                thinkingEffort: effectiveEffort,
                ...(attachedFiles ? { attachedFiles } : {}),
                ...(finalSteps.length > 0 ? { stepProgress: finalSteps } : {}),
                thinkingElapsedSeconds: elapsedSec,
              });
            }
          }
        },
      })
      .then(() => {
        if (!controller.signal.aborted && !hasStreamError) {
          updateBgSnapshot({ isGenerating: false, thinkingStartedAtMs: null });
        }
      })
      .catch((err: unknown) => {
        clearBgTimers();
        if (controller.signal.aborted) return;
        const detail = err instanceof Error ? err.message : "Erreur de communication avec le serveur";
        updateBgSnapshot({
          isGenerating: false,
          thinkingStartedAtMs: null,
          errorMessage: isFr
            ? `⚠️ Impossible d'obtenir une réponse de Mon Assistant (${detail}). Vérifiez que le modèle IA configuré est bien démarré.`
            : `⚠️ Could not get a response from My Assistant (${detail}). Please check that your configured AI model is running.`,
        });
      });
  };

  const initialElapsedSeconds =
    bgSnapshot.isGenerating && bgSnapshot.thinkingStartedAtMs !== null
      ? Math.max(0, Math.floor((Date.now() - bgSnapshot.thinkingStartedAtMs) / 1000))
      : 0;

  return {
    streamedText: bgSnapshot.streamedText,
    setStreamedText,
    activeUserPrompt: bgSnapshot.activeUserPrompt,
    stepProgress: bgSnapshot.stepProgress,
    cacheHit: bgSnapshot.cacheHit,
    cacheLookupMs: bgSnapshot.cacheLookupMs,
    nodes1To4Ms: bgSnapshot.nodes1To4Ms,
    ttftMs: bgSnapshot.ttftMs,
    isGenerating: bgSnapshot.isGenerating,
    initialElapsedSeconds,
    generationStopped: bgSnapshot.generationStopped,
    errorMessage: bgSnapshot.errorMessage,
    sendTurn,
    stopGeneration,
    resetStreamState,
  };
}
