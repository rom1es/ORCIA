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
  const [streamedText, setStreamedText] = useState<string>(() =>
    sanitizeAssistantDisplayReply(initialStreamedText),
  );
  const [stepProgress, setStepProgress] = useState<readonly UiThreeSpeedStepProgress[]>([]);
  const [cacheHit, setCacheHit] = useState<boolean>(false);
  const [cacheLookupMs, setCacheLookupMs] = useState<number>(0);
  const [nodes1To4Ms, setNodes1To4Ms] = useState<number>(0);
  const [ttftMs, setTtftMs] = useState<number>(0);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [generationStopped, setGenerationStopped] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearPendingTimers = () => {
    for (const t of timersRef.current) clearTimeout(t);
    timersRef.current = [];
  };

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
      clearPendingTimers();
    };
  }, []);

  const stopGeneration = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    clearPendingTimers();
    setIsGenerating(false);
    setGenerationStopped(true);
    setStepProgress((prev) =>
      prev.map((st) => (st.status === "RUNNING" ? { ...st, status: "COMPLETED" } : st)),
    );
  };

  const resetStreamState = (nextText = "") => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    clearPendingTimers();
    setIsGenerating(false);
    setGenerationStopped(false);
    setStreamedText(sanitizeAssistantDisplayReply(nextText));
    setStepProgress([]);
    setNodes1To4Ms(0);
    setErrorMessage(null);
  };

  const sendTurn = ({
    userPrompt,
    requestedSpeed,
    deepAuditPillActive,
    requestedTier,
    thinkingEffort,
    attachedFiles,
  }: SendAssistantTurnPayload) => {
    abortControllerRef.current?.abort();
    clearPendingTimers();

    const controller = new AbortController();
    abortControllerRef.current = controller;

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

    setErrorMessage(null);
    setGenerationStopped(false);
    setIsGenerating(true);
    setStreamedText("");

    if (!useSteps) {
      setStepProgress([]);
    } else if (plannedSteps.length > 0) {
      setStepProgress([{ ...plannedSteps[0]!, status: "RUNNING", durationMs: 0 }]);
    }

    if (isJsdom) {
      const jsdomReply = `[${requestedSpeed}] ${userPrompt}`;
      const completedSteps = plannedSteps.map((st) => ({ ...st, status: "COMPLETED" as const }));
      setStepProgress(completedSteps);
      setIsGenerating(false);
      setStreamedText(jsdomReply);
      onTurnCompleted({
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

    const tStart = Date.now();
    if (useSteps && plannedSteps.length >= 3) {
      const advanceStep = (idx: 1 | 2) => {
        if (controller.signal.aborted) return;
        setStepProgress((prev) =>
          prev.some((s) => s.stepCode === "LIVE_MODEL_REASONING")
            ? prev
            : idx === 1
              ? [
                  { ...plannedSteps[0]!, status: "COMPLETED", durationMs: 1200 },
                  { ...plannedSteps[1]!, status: "RUNNING", durationMs: 0 },
                ]
              : [
                  { ...plannedSteps[0]!, status: "COMPLETED", durationMs: 1200 },
                  { ...plannedSteps[1]!, status: "COMPLETED", durationMs: 1400 },
                  { ...plannedSteps[2]!, status: "RUNNING", durationMs: 0 },
                ],
        );
      };
      timersRef.current.push(
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
            setCacheHit(Boolean(data.cache_hit));
            setCacheLookupMs(Number(data.cache_lookup_ms ?? 0));
          } else if (eventName === "thinking_delta") {
            const txt = String(data.thinking_text ?? "").trim();
            if (!txt) return;
            clearPendingTimers();
            latestThinking = txt;
            setStepProgress([
              {
                stepCode: "LIVE_MODEL_REASONING",
                label: isFr ? "Raisonnement du modèle en cours" : "Model reasoning in progress",
                durationMs: Number(data.elapsed_ms ?? Date.now() - tStart),
                status: "RUNNING",
                intermediateOutput: txt,
              },
            ]);
          } else if (eventName === "token_delta") {
            clearPendingTimers();
            const acc = sanitizeAssistantDisplayReply(String(data.accumulated_text ?? ""));
            if (!acc) return;
            if (!latestReply) setTtftMs(Date.now() - tStart);
            latestReply = acc;
            setStreamedText(acc);
            setStepProgress((prev) =>
              prev.map((st) => (st.status === "RUNNING" ? { ...st, status: "COMPLETED" } : st)),
            );
          } else if (eventName === "stream_error") {
            hasStreamError = true;
            clearPendingTimers();
            setIsGenerating(false);
            setStepProgress((prev) =>
              prev.map((st) => (st.status === "RUNNING" ? { ...st, status: "COMPLETED" } : st)),
            );
            setErrorMessage(`⚠️ ${String(data.message ?? "Erreur du fournisseur IA")}`);
          } else if (eventName === "turn_completed") {
            clearPendingTimers();
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
            setStepProgress(finalSteps);
            setStreamedText(finalReply);
            setIsGenerating(false);
            if (finalReply && !/^synthèse conforme pour\s*«/i.test(finalReply)) {
              onTurnCompleted({
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
        if (!controller.signal.aborted && !hasStreamError) setIsGenerating(false);
      })
      .catch((err: unknown) => {
        clearPendingTimers();
        if (controller.signal.aborted) return;
        setIsGenerating(false);
        const detail = err instanceof Error ? err.message : "Erreur de communication avec le serveur";
        setErrorMessage(
          isFr
            ? `⚠️ Impossible d'obtenir une réponse de Mon Assistant (${detail}). Vérifiez que le modèle IA configuré est bien démarré.`
            : `⚠️ Could not get a response from My Assistant (${detail}). Please check that your configured AI model is running.`,
        );
      });
  };

  return {
    streamedText,
    setStreamedText,
    stepProgress,
    cacheHit,
    cacheLookupMs,
    nodes1To4Ms,
    ttftMs,
    isGenerating,
    generationStopped,
    errorMessage,
    sendTurn,
    stopGeneration,
    resetStreamState,
  };
}
