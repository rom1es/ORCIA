import React, { useEffect, useRef, useState } from "react";
import { FormattedMarkdownContent } from "../components/FormattedMarkdownContent";
import { OrciaIcon } from "../components/icons";
import type { UiThreeSpeedStepProgress } from "./AssistantSpeedSelectorAndStreamView";

export interface AssistantThinkingSubWindowProps {
  readonly stepProgress: readonly UiThreeSpeedStepProgress[];
  readonly isGenerating: boolean;
  readonly hasStreamedResponse: boolean;
  readonly elapsedSecondsOverride?: number;
  readonly initialElapsedSeconds?: number;
}

export function formatStepDurationSeconds(
  durationMs: number,
  liveElapsedSeconds: number,
  status: "COMPLETED" | "RUNNING",
): string {
  if (status === "RUNNING") {
    return `${Math.max(0, liveElapsedSeconds)}s`;
  }
  const roundedSeconds = Math.max(0, Math.round(durationMs / 1000));
  if (roundedSeconds > 0) {
    return `${roundedSeconds}s`;
  }
  return "< 1s";
}

export function humanizeStepLabel(rawLabel: string): string {
  if (
    /Nœuds 1–4 déterministes/i.test(rawLabel) ||
    /pgvector/i.test(rawLabel) ||
    /RBAC/i.test(rawLabel)
  ) {
    return "Analyse de la question et préparation du contexte";
  }
  if (
    /Nœud 5\s*—\s*Appel LLM/i.test(rawLabel) ||
    /streaming SSE/i.test(rawLabel)
  ) {
    return "Élaboration de la réponse par Mon Assistant";
  }
  return rawLabel;
}

export function humanizeIntermediateOutput(
  rawOutput: string | null | undefined,
): string | null {
  if (!rawOutput) {
    return null;
  }
  let cleaned = rawOutput.replace(
    /Demande analysée pour l'espace\s*«[^»]*»\s*\(rôle\s*:\s*[^)]+\)\s*:\s*/gi,
    "Analyse de votre demande : ",
  );
  cleaned = cleaned.replace(
    /\s*\(rôle(?:\s+actif)?\s*:\s*PLATFORM_ADMIN\)/gi,
    "",
  );
  cleaned = cleaned.replace(/\bPLATFORM_ADMIN\b/g, "Administrateur");
  return cleaned;
}

export function AssistantThinkingSubWindow({
  stepProgress,
  isGenerating,
  hasStreamedResponse,
  elapsedSecondsOverride,
  initialElapsedSeconds = 0,
}: AssistantThinkingSubWindowProps): React.JSX.Element | null {
  const hasSteps = stepProgress.length > 0;
  const isLiveReasoningOnly =
    stepProgress.length === 1 &&
    stepProgress[0]?.stepCode === "LIVE_MODEL_REASONING";
  const [expanded, setExpanded] = useState<boolean>(
    isGenerating && !hasStreamedResponse && !isLiveReasoningOnly,
  );
  const [userToggledManually, setUserToggledManually] =
    useState<boolean>(false);
  const [userExpandedSteps, setUserExpandedSteps] = useState<
    Readonly<Record<string, boolean>>
  >({});
  const [liveSeconds, setLiveSeconds] = useState<number>(() =>
    Math.max(0, Math.floor(initialElapsedSeconds)),
  );
  const [stepLiveTimers, setStepLiveTimers] = useState<
    Readonly<Record<string, number>>
  >({});
  const prevIsGeneratingRef = useRef<boolean>(isGenerating);
  const prevHasStreamedRef = useRef<boolean>(hasStreamedResponse);

  useEffect(() => {
    if (initialElapsedSeconds > liveSeconds && isGenerating) {
      setLiveSeconds(Math.floor(initialElapsedSeconds));
    }
  }, [initialElapsedSeconds, isGenerating, liveSeconds]);

  // Automatic open on generation start (except LIVE_MODEL_REASONING which stays collapse hide by default)
  // and automatic collapse when final response starts arriving
  useEffect(() => {
    if (isGenerating && !prevIsGeneratingRef.current) {
      setExpanded(!isLiveReasoningOnly);
      setUserToggledManually(false);
      setUserExpandedSteps({});
      setLiveSeconds(Math.max(0, Math.floor(initialElapsedSeconds)));
      setStepLiveTimers({});
    } else if (isGenerating && isLiveReasoningOnly && !userToggledManually) {
      setExpanded(false);
    } else if (
      !userToggledManually &&
      ((hasStreamedResponse && !prevHasStreamedRef.current) ||
        (!isGenerating && prevIsGeneratingRef.current))
    ) {
      setExpanded(false);
    }
    prevIsGeneratingRef.current = isGenerating;
    prevHasStreamedRef.current = hasStreamedResponse;
  }, [
    isGenerating,
    hasStreamedResponse,
    userToggledManually,
    isLiveReasoningOnly,
    initialElapsedSeconds,
  ]);

  // Live 1-second counter while generating (overall + per RUNNING step)
  useEffect(() => {
    if (!isGenerating) {
      return;
    }
    const timer = setInterval(() => {
      setLiveSeconds((prev) => prev + 1);
      setStepLiveTimers((prev) => {
        const next: Record<string, number> = { ...prev };
        for (const st of stepProgress) {
          if (st.status === "RUNNING") {
            next[st.stepCode] = (next[st.stepCode] ?? 0) + 1;
          }
        }
        return next;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [isGenerating, stepProgress]);

  if (!hasSteps && !isGenerating && elapsedSecondsOverride === undefined) {
    return null;
  }

  const totalCompletedSeconds = Math.max(
    liveSeconds,
    Math.round(
      stepProgress.reduce((acc, st) => acc + (st.durationMs || 0), 0) / 1000,
    ),
  );
  const displayHeaderSeconds =
    elapsedSecondsOverride ??
    (isGenerating ? liveSeconds : totalCompletedSeconds);

  const headerTitle = isGenerating
    ? `Réflexion en cours · ${displayHeaderSeconds}s`
    : `Réflexion pendant ${displayHeaderSeconds}s`;

  // Rule A — No structured steps: static non-collapsible line once finished, or simple header while generating
  if (!hasSteps) {
    return (
      <div
        data-testid="assistant-thinking-subwindow"
        data-expanded="false"
        className="text-xs text-text-secondary py-0.5"
      >
        <span data-testid="assistant-thinking-subwindow-header-label">
          {headerTitle}
        </span>
      </div>
    );
  }

  const toggleIndividualStep = (stepCode: string, currentlyOpen: boolean) => {
    setUserToggledManually(true);
    setUserExpandedSteps((prev) => ({
      ...prev,
      [stepCode]: !currentlyOpen,
    }));
    if (!expanded) {
      setExpanded(true);
    }
  };

  return (
    <div
      data-testid="assistant-thinking-subwindow"
      data-expanded={expanded ? "true" : "false"}
      className="text-xs"
    >
      <button
        type="button"
        data-testid="assistant-thinking-subwindow-toggle"
        aria-expanded={expanded}
        onClick={() => {
          setUserToggledManually(true);
          const nextExpanded = !expanded;
          setExpanded(nextExpanded);
          if (isLiveReasoningOnly && stepProgress[0]) {
            setUserExpandedSteps((prev) => ({
              ...prev,
              [stepProgress[0]!.stepCode]: nextExpanded,
            }));
          }
        }}
        className="inline-flex items-center gap-1.5 py-0.5 text-xs font-normal text-text-secondary hover:text-text-primary transition-colors"
      >
        <span data-testid="assistant-thinking-subwindow-header-label">
          {headerTitle}
        </span>
        <OrciaIcon
          name={expanded ? "chevronDown" : "chevronRight"}
          testId="assistant-thinking-subwindow-chevron"
          className="text-xs leading-none"
        />
      </button>

      <ol
        data-testid="assistant-step-progress-list"
        aria-live="polite"
        style={expanded ? undefined : { display: "none" }}
        className={
          expanded
            ? "pl-3 border-l border-border-subtle/60 space-y-1 mt-1 text-[11px] text-text-secondary"
            : "sr-only"
        }
      >
        {stepProgress.map((st) => {
          const isRunning = st.status === "RUNNING";
          const manualState = userExpandedSteps[st.stepCode];
          // Progressive collapse rule:
          // - LIVE_MODEL_REASONING (delta.reasoning) starts in collapse hide (false) by default unless manually expanded by user
          // - Other RUNNING steps are automatically in collapse show (true) unless manually collapsed
          // - COMPLETED steps automatically transition to collapse hide (false) unless manually expanded by user
          const defaultStepExpanded =
            st.stepCode === "LIVE_MODEL_REASONING" ? false : isRunning;
          const isStepExpanded =
            manualState !== undefined ? manualState : defaultStepExpanded;
          const stepElapsed =
            stepLiveTimers[st.stepCode] ?? displayHeaderSeconds;
          const stepTimerText = formatStepDurationSeconds(
            st.durationMs,
            stepElapsed,
            st.status,
          );
          const cleanLabel = humanizeStepLabel(st.label);
          const cleanIntermediate = humanizeIntermediateOutput(
            st.intermediateOutput,
          );
          return (
            <li
              key={st.stepCode}
              data-testid={`assistant-step-item-${st.stepCode}`}
              data-step-expanded={isStepExpanded ? "true" : "false"}
              data-step-status={st.status}
              className="space-y-0.5 py-0.5"
            >
              <button
                type="button"
                data-testid={`assistant-step-toggle-${st.stepCode}`}
                aria-expanded={isStepExpanded}
                onClick={() => toggleIndividualStep(st.stepCode, isStepExpanded)}
                className="flex w-full items-center gap-1.5 text-left hover:text-text-primary transition-colors"
              >
                <OrciaIcon name={isRunning ? "hourglass" : "check"} />
                <span className="text-text-secondary">{cleanLabel}</span>
                <span
                  data-testid={`assistant-step-live-timer-${st.stepCode}`}
                  className="font-mono text-[11px] text-text-secondary/80"
                >
                  {stepTimerText}
                </span>
                <OrciaIcon
                  name={isStepExpanded ? "chevronDown" : "chevronRight"}
                  testId={`assistant-step-chevron-${st.stepCode}`}
                  className="text-[11px] leading-none text-text-secondary/70"
                />
              </button>
              {cleanIntermediate ? (
                <div
                  data-testid={`assistant-step-intermediate-output-${st.stepCode}`}
                  style={isStepExpanded ? undefined : { display: "none" }}
                  className={
                    isStepExpanded
                      ? "pl-4 text-[11px] leading-relaxed text-text-secondary/80"
                      : "sr-only"
                  }
                >
                  <FormattedMarkdownContent
                    content={cleanIntermediate}
                    testId={`formatted-markdown-step-${st.stepCode}`}
                  />
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
