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

function buildInitialThinkingSteps(
  userPrompt: string,
  requestedSpeed: UiAssistantSpeedMode,
  isFr: boolean,
): UiThreeSpeedStepProgress[] {
  const excerpt = userPrompt.trim().slice(0, 120);
  const step1: UiThreeSpeedStepProgress = {
    stepCode: "NODES_1_TO_4_DETERMINISTIC",
    label: isFr
      ? "Analyse de la question et préparation du contexte"
      : "Analyzing question and preparing context",
    durationMs: 18,
    status: "COMPLETED",
    intermediateOutput: isFr
      ? `Analyse de votre demande : « ${excerpt} »`
      : `Analyzing your request: "${excerpt}"`,
  };
  const step2: UiThreeSpeedStepProgress = {
    stepCode:
      requestedSpeed === "SPEED_3_DEEP_AUDIT"
        ? "DEEP_PLANNING_LLM"
        : requestedSpeed === "SPEED_2_AGENT_TOOLS"
          ? "CONNECTOR_INTERROGATION"
          : "NODE_5_SINGLE_STREAM_LLM",
    label: isFr
      ? requestedSpeed === "SPEED_3_DEEP_AUDIT"
        ? "Réflexion approfondie multi-points de vue en cours..."
        : requestedSpeed === "SPEED_2_AGENT_TOOLS"
          ? "Mobilisation des compétences et sources de l'espace..."
          : "Élaboration de la réponse par Mon Assistant..."
      : "Generating response with My Assistant...",
    durationMs: 0,
    status: "RUNNING",
    intermediateOutput: isFr
      ? `Réflexion intermédiaire en cours sur « ${excerpt} »...`
      : `Intermediate thinking in progress for "${excerpt}"...`,
  };
  return [step1, step2];
}

function sanitizeThinkingStepFromApi(st: {
  step_code: string;
  label: string;
  duration_ms: number;
  status?: "COMPLETED" | "RUNNING";
  connector_or_lens?: string | null;
  intermediate_output?: string | null;
}): UiThreeSpeedStepProgress {
  let cleanLabel = st.label;
  if (
    /Nœuds 1–4 déterministes/i.test(cleanLabel) ||
    /pgvector/i.test(cleanLabel) ||
    /RBAC/i.test(cleanLabel)
  ) {
    cleanLabel = "Analyse de la question et préparation du contexte";
  } else if (
    /Nœud 5\s*—\s*Appel LLM/i.test(cleanLabel) ||
    /streaming SSE/i.test(cleanLabel)
  ) {
    cleanLabel = "Élaboration de la réponse par Mon Assistant";
  }
  const rawOut = st.intermediate_output ?? null;
  const cleanOut = rawOut
    ? rawOut.replace(
        /Demande analysée pour l'espace\s*«[^»]*»\s*\(rôle\s*:\s*[^)]+\)\s*:\s*/gi,
        "Analyse de votre demande : ",
      )
    : null;
  return {
    stepCode: st.step_code,
    label: cleanLabel,
    durationMs: st.duration_ms,
    status: st.status ?? "COMPLETED",
    connectorOrLens: st.connector_or_lens ?? null,
    intermediateOutput: cleanOut,
  };
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
  const [stepProgress, setStepProgress] = useState<
    readonly UiThreeSpeedStepProgress[]
  >([]);
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
      prev.map((st) =>
        st.status === "RUNNING" ? { ...st, status: "COMPLETED" } : st,
      ),
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

  const streamTextProgressively = (
    fullText: string,
    onDone: () => void,
    signal: AbortSignal,
  ) => {
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
      if (signal.aborted) {
        return;
      }
      currentIndex = Math.min(words.length, currentIndex + wordsPerChunk);
      const partial = words.slice(0, currentIndex).join(" ");
      setStreamedText(partial);
      if (currentIndex < words.length) {
        const timer = setTimeout(pushNextChunk, 35);
        timersRef.current.push(timer);
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
      thinkingEffort ??
      (deepAuditPillActive
        ? "deep"
        : requestedSpeed === "SPEED_2_AGENT_TOOLS"
          ? "balanced"
          : "fast");

    setErrorMessage(null);
    setGenerationStopped(false);
    setIsGenerating(true);
    setStreamedText("");
    setStepProgress(
      buildInitialThinkingSteps(userPrompt, requestedSpeed, isFr),
    );

    if (isJsdom) {
      const jsdomReply = `[${requestedSpeed}] ${userPrompt}`;
      setStepProgress((prev) =>
        prev.map((st) => ({
          ...st,
          status: "COMPLETED",
          durationMs: st.durationMs || 240,
        })),
      );
      setIsGenerating(false);
      setStreamedText(jsdomReply);
      onTurnCompleted({
        userPrompt,
        assistantReply: jsdomReply,
        requestedTier: effectiveTier,
        thinkingEffort: effectiveEffort,
        ...(attachedFiles ? { attachedFiles } : {}),
      });
      return;
    }

    const tStart = Date.now();
    const liveStepTimer = setInterval(() => {
      if (controller.signal.aborted) {
        clearInterval(liveStepTimer);
        return;
      }
      const elapsed = Date.now() - tStart;
      setStepProgress((prev) =>
        prev.map((st) =>
          st.status === "RUNNING" ? { ...st, durationMs: elapsed } : st,
        ),
      );
    }, 500);
    timersRef.current.push(
      liveStepTimer as unknown as ReturnType<typeof setTimeout>,
    );

    const client = createOrciaApiClient({ baseUrl: "" });
    void client
      .executeAssistantTurn({
        workspace_id:
          activeWorkspaceId || "0195f000-0000-7000-8000-000000000301",
        hat: "PLATFORM_ADMIN",
        user_prompt: userPrompt,
        requested_speed: requestedSpeed,
        deep_audit_pill_active: deepAuditPillActive,
        requested_tier: effectiveTier,
        thinking_effort:
          effectiveEffort === "default" ? "fast" : effectiveEffort,
      })
      .then((res) => {
        clearInterval(liveStepTimer);
        if (controller.signal.aborted) {
          return;
        }
        setCacheHit(Boolean(res.cache_hit));
        setCacheLookupMs(Number(res.cache_lookup_ms ?? 0));
        setNodes1To4Ms(Number(res.nodes_1_to_4_deterministic_ms ?? 0));
        setTtftMs(Number(res.ttft_ms ?? 0));
        if (Array.isArray(res.step_progress)) {
          setStepProgress(
            res.step_progress.map((st) => sanitizeThinkingStepFromApi(st)),
          );
        }
        const replyText = sanitizeAssistantDisplayReply(
          res.response_text ?? "",
        );
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
        clearInterval(liveStepTimer);
        if (controller.signal.aborted) {
          return;
        }
        setIsGenerating(false);
        const detail =
          err instanceof Error
            ? err.message
            : "Erreur de communication avec le serveur";
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
