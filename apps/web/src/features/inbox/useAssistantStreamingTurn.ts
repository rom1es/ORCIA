import { createOrciaApiClient } from "@orcia/api-client";
import {
  sanitizeAssistantDisplayReply,
  type UiAssistantAttachedFileItem,
  type UiAssistantSpeedMode,
  type UiInferenceEffort,
  type UiInferenceTier,
  type UiThreeSpeedStepProgress,
} from "@orcia/ui";
import { useEffect, useRef, useState } from "react";

export interface UseAssistantStreamingTurnOptions {
  readonly activeWorkspaceId: string;
  readonly isFr: boolean;
  readonly isJsdom: boolean;
  readonly initialStreamedText: string;
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

export function useAssistantStreamingTurn({
  activeWorkspaceId,
  isFr,
  isJsdom,
  initialStreamedText,
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
    for (const t of timersRef.current) {
      clearTimeout(t);
    }
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
    setErrorMessage(null);
  };

  const streamTextProgressively = (fullText: string, onDone: () => void, signal: AbortSignal) => {
    const words = fullText.split(" ");
    if (words.length <= 2) {
      setStreamedText(fullText);
      onDone();
      return;
    }
    const chunkCount = Math.min(8, Math.max(2, Math.ceil(words.length / 4)));
    const wordsPerChunk = Math.max(1, Math.ceil(words.length / chunkCount));
    let currentIndex = 0;

    const pushNextChunk = () => {
      if (signal.aborted) return;
      currentIndex = Math.min(words.length, currentIndex + wordsPerChunk);
      setStreamedText(words.slice(0, currentIndex).join(" "));
      if (currentIndex < words.length) {
        timersRef.current.push(setTimeout(pushNextChunk, 35));
      } else {
        onDone();
      }
    };
    pushNextChunk();
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
      const tStep2 = setTimeout(() => {
        if (controller.signal.aborted) return;
        setStepProgress([
          { ...plannedSteps[0]!, status: "COMPLETED", durationMs: 1200 },
          { ...plannedSteps[1]!, status: "RUNNING", durationMs: 0 },
        ]);
      }, 1200);
      const tStep3 = setTimeout(() => {
        if (controller.signal.aborted) return;
        setStepProgress([
          { ...plannedSteps[0]!, status: "COMPLETED", durationMs: 1200 },
          { ...plannedSteps[1]!, status: "COMPLETED", durationMs: 1400 },
          { ...plannedSteps[2]!, status: "RUNNING", durationMs: 0 },
        ]);
      }, 2600);
      timersRef.current.push(tStep2, tStep3);
    }

    const client = createOrciaApiClient({ baseUrl: "" });
    void client
      .executeAssistantTurn({
        workspace_id: activeWorkspaceId || "0195f000-0000-7000-8000-000000000301",
        hat: "PLATFORM_ADMIN",
        user_prompt: userPrompt,
        requested_speed: requestedSpeed,
        deep_audit_pill_active: deepAuditPillActive,
        requested_tier: effectiveTier,
        thinking_effort: effectiveEffort === "default" ? "balanced" : effectiveEffort,
      })
      .then((res) => {
        if (controller.signal.aborted) return;
        clearPendingTimers();
        const elapsedSec = Math.max(1, Math.round((Date.now() - tStart) / 1000));
        setCacheHit(Boolean(res.cache_hit));
        setCacheLookupMs(Number(res.cache_lookup_ms ?? 0));
        setNodes1To4Ms(Number(res.nodes_1_to_4_deterministic_ms ?? 0));
        setTtftMs(Number(res.ttft_ms ?? 0));
        const finalSteps = useSteps
          ? plannedSteps.map((st) => ({ ...st, status: "COMPLETED" as const }))
          : [];
        setStepProgress(finalSteps);
        const replyText = sanitizeAssistantDisplayReply(res.response_text ?? "");
        if (replyText) {
          streamTextProgressively(
            replyText,
            () => {
              if (!controller.signal.aborted) {
                setIsGenerating(false);
                onTurnCompleted({
                  userPrompt,
                  assistantReply: replyText,
                  requestedTier: effectiveTier,
                  thinkingEffort: effectiveEffort,
                  ...(attachedFiles ? { attachedFiles } : {}),
                  ...(finalSteps.length > 0 ? { stepProgress: finalSteps } : {}),
                  thinkingElapsedSeconds: elapsedSec,
                });
              }
            },
            controller.signal,
          );
        } else {
          setIsGenerating(false);
        }
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
