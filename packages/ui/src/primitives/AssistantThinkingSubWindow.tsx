import React, { useEffect, useRef, useState } from "react";
import { FormattedMarkdownContent } from "../components/FormattedMarkdownContent";
import type { UiThreeSpeedStepProgress } from "./AssistantSpeedSelectorAndStreamView";

export interface AssistantThinkingSubWindowProps {
  readonly stepProgress: readonly UiThreeSpeedStepProgress[];
  readonly isGenerating: boolean;
  readonly hasStreamedResponse: boolean;
  readonly elapsedSecondsOverride?: number;
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
  if (/Nœud 5\s*—\s*Appel LLM/i.test(rawLabel) || /streaming SSE/i.test(rawLabel)) {
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
  const cleaned = rawOutput.replace(
    /Demande analysée pour l'espace\s*«[^»]*»\s*\(rôle\s*:\s*[^)]+\)\s*:\s*/gi,
    "Analyse de votre demande : ",
  );
  return cleaned;
}

export function AssistantThinkingSubWindow({
  stepProgress,
  isGenerating,
  hasStreamedResponse,
  elapsedSecondsOverride,
}: AssistantThinkingSubWindowProps): React.JSX.Element | null {
  const [expanded, setExpanded] = useState<boolean>(true);
  const [userToggledManually, setUserToggledManually] =
    useState<boolean>(false);
  const [liveSeconds, setLiveSeconds] = useState<number>(0);
  const prevIsGeneratingRef = useRef<boolean>(isGenerating);
  const prevHasStreamedRef = useRef<boolean>(hasStreamedResponse);

  // Automatic open on generation start and automatic collapse when final response starts arriving
  useEffect(() => {
    if (isGenerating && !prevIsGeneratingRef.current) {
      setExpanded(true);
      setUserToggledManually(false);
      setLiveSeconds(0);
    } else if (
      !userToggledManually &&
      ((hasStreamedResponse && !prevHasStreamedRef.current) ||
        (!isGenerating && prevIsGeneratingRef.current && stepProgress.length > 0))
    ) {
      setExpanded(false);
    }
    prevIsGeneratingRef.current = isGenerating;
    prevHasStreamedRef.current = hasStreamedResponse;
  }, [isGenerating, hasStreamedResponse, stepProgress.length, userToggledManually]);

  // Live 1-second counter while generating
  useEffect(() => {
    if (!isGenerating) {
      return;
    }
    const timer = setInterval(() => {
      setLiveSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [isGenerating]);

  if (stepProgress.length === 0 && !isGenerating) {
    return null;
  }

  const totalCompletedSeconds = Math.max(
    liveSeconds,
    Math.round(
      stepProgress.reduce((acc, st) => acc + (st.durationMs || 0), 0) / 1000,
    ),
  );
  const displayHeaderSeconds =
    elapsedSecondsOverride ?? (isGenerating ? liveSeconds : totalCompletedSeconds);

  const headerTitle = isGenerating
    ? `Réflexion en cours · ${displayHeaderSeconds}s`
    : `Réflexion terminée · ${displayHeaderSeconds}s`;

  return (
    <div
      data-testid="assistant-thinking-subwindow"
      data-expanded={expanded ? "true" : "false"}
      className="rounded-lg border border-border-subtle bg-surface-primary text-xs"
    >
      <button
        type="button"
        data-testid="assistant-thinking-subwindow-toggle"
        aria-expanded={expanded}
        onClick={() => {
          setUserToggledManually(true);
          setExpanded((prev) => !prev);
        }}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left font-medium text-text-secondary hover:text-text-primary"
      >
        <span className="inline-flex items-center gap-2">
          <span aria-hidden="true">{isGenerating ? "⏳" : "🧠"}</span>
          <span data-testid="assistant-thinking-subwindow-header-label">
            {headerTitle}
          </span>
        </span>
        <span
          aria-hidden="true"
          data-testid="assistant-thinking-subwindow-chevron"
          className="font-mono text-sm"
        >
          {expanded ? "⌄" : "›"}
        </span>
      </button>

      <ol
        data-testid="assistant-step-progress-list"
        aria-live="polite"
        className={
          expanded
            ? "space-y-2 border-t border-border-subtle px-3 py-2.5"
            : "sr-only"
        }
      >
        {stepProgress.map((st) => {
          const isRunning = st.status === "RUNNING";
          const stepTimerText = formatStepDurationSeconds(
            st.durationMs,
            displayHeaderSeconds,
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
              className="space-y-1 rounded border border-border-subtle/60 bg-surface-secondary/40 p-2"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="inline-flex items-center gap-1.5 font-medium text-text-primary">
                  <span aria-hidden="true">{isRunning ? "⏳" : "✓"}</span>
                  <span>{cleanLabel}</span>
                </span>
                <span
                  data-testid={`assistant-step-live-timer-${st.stepCode}`}
                  className="font-mono text-[11px] text-text-secondary"
                >
                  {stepTimerText}
                </span>
              </div>
              {cleanIntermediate ? (
                <div
                  data-testid={`assistant-step-intermediate-output-${st.stepCode}`}
                  className="rounded border border-border-subtle bg-surface-primary px-2.5 py-1.5 text-[11px] leading-relaxed text-text-secondary"
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
