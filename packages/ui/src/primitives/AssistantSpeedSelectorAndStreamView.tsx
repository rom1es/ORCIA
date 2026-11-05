import React, { useState } from "react";

export type UiAssistantSpeedMode =
  | "SPEED_1_FAST"
  | "SPEED_2_AGENT_TOOLS"
  | "SPEED_3_DEEP_AUDIT";

export interface UiThreeSpeedStepProgress {
  readonly stepCode: string;
  readonly label: string;
  readonly durationMs: number;
  readonly status: "COMPLETED" | "RUNNING";
  readonly connectorOrLens?: string | null;
}

export interface AssistantSpeedSelectorAndStreamViewLabels {
  readonly headerTitle: string;
  readonly speed1PillLabel: string;
  readonly speed2PillLabel: string;
  readonly speed3DeepAuditPillLabel: string;
  readonly cacheHitBadge: string;
  readonly cacheMissBadge: string;
  readonly nodesDeterministicLabel: string;
  readonly ttftBadgePrefix: string;
  readonly inputPlaceholder: string;
  readonly sendPromptCta: string;
}

export interface AssistantSpeedSelectorAndStreamViewProps {
  readonly workspaceId: string;
  readonly userId: string;
  readonly hat: string;
  readonly activeSpeed?: UiAssistantSpeedMode;
  readonly deepAuditPillActive?: boolean;
  readonly cacheHit?: boolean;
  readonly cacheLookupMs?: number;
  readonly nodes1To4DeterministicMs?: number;
  readonly ttftMs?: number;
  readonly stepProgress: readonly UiThreeSpeedStepProgress[];
  readonly streamedText?: string;
  readonly isGenerating?: boolean;
  readonly errorMessage?: string | null;
  readonly labels: AssistantSpeedSelectorAndStreamViewLabels;
  readonly onSendTurn?: (payload: {
    userPrompt: string;
    requestedSpeed: UiAssistantSpeedMode;
    deepAuditPillActive: boolean;
  }) => void;
}

/**
 * Story 10.2 — 3-Speed Conversational Selector (`⚡ Rapide`, `@Agent / /Skill`, `🧠 Approfondi`),
 * Redis 5-Layer Prompt Cache (`TTL 300s`, `< 5 ms`) & Real-Time Step Progress Stream View.
 */
export function AssistantSpeedSelectorAndStreamView({
  workspaceId,
  userId,
  hat,
  activeSpeed: initialSpeed = "SPEED_1_FAST",
  deepAuditPillActive: initialDeepAudit = false,
  cacheHit = true,
  cacheLookupMs = 1.4,
  nodes1To4DeterministicMs = 18.2,
  ttftMs = 398.2,
  stepProgress,
  streamedText = "",
  isGenerating = false,
  errorMessage = null,
  labels,
  onSendTurn,
}: AssistantSpeedSelectorAndStreamViewProps): React.JSX.Element {
  const [speed, setSpeed] = useState<UiAssistantSpeedMode>(
    initialDeepAudit ? "SPEED_3_DEEP_AUDIT" : initialSpeed,
  );
  const [deepAuditActive, setDeepAuditActive] =
    useState<boolean>(initialDeepAudit);
  const [promptText, setPromptText] = useState<string>("");

  const cacheKey = `assistant:prompt:${workspaceId}:${userId}:${hat}`;

  const handleToggleDeepAudit = () => {
    const next = !deepAuditActive;
    setDeepAuditActive(next);
    setSpeed(next ? "SPEED_3_DEEP_AUDIT" : "SPEED_1_FAST");
  };

  const handlePromptChange = (val: string) => {
    setPromptText(val);
    if (!deepAuditActive) {
      if (/(?:^|\s)(@[a-zA-Z0-9_-]+|\/[a-zA-Z0-9_-]+)/.test(val)) {
        setSpeed("SPEED_2_AGENT_TOOLS");
      } else {
        setSpeed("SPEED_1_FAST");
      }
    }
  };

  const triggerSendTurn = () => {
    const trimmed = promptText.trim();
    const effectivePrompt =
      trimmed ||
      (labels.sendPromptCta.toLowerCase().includes("envoyer")
        ? "Bonjour, peux-tu te présenter brièvement et confirmer que tu es opérationnel ?"
        : "Hello, can you briefly introduce yourself and confirm you are operational?");
    if (!trimmed) {
      setPromptText(effectivePrompt);
    }
    onSendTurn?.({
      userPrompt: effectivePrompt,
      requestedSpeed: speed,
      deepAuditPillActive: deepAuditActive,
    });
  };

  return (
    <section
      data-testid="assistant-speed-selector-and-stream"
      className="rounded-lg border border-border-subtle bg-surface-elevated p-4 text-text-primary space-y-3"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle pb-2">
        <h3 className="text-sm font-semibold">{labels.headerTitle}</h3>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span
            data-testid="assistant-prompt-cache-badge"
            className="rounded border border-border-subtle bg-surface-secondary px-2 py-0.5 font-mono text-[11px]"
          >
            {cacheHit ? labels.cacheHitBadge : labels.cacheMissBadge} ·{" "}
            {cacheLookupMs} ms · {cacheKey}
          </span>
          <span
            data-testid="assistant-nodes-deterministic-badge"
            className="rounded bg-surface-secondary px-2 py-0.5 font-mono text-[11px] text-text-secondary"
          >
            {labels.nodesDeterministicLabel}: {nodes1To4DeterministicMs} ms
          </span>
          <span
            data-testid="assistant-ttft-badge"
            className="rounded bg-action-primary/15 px-2 py-0.5 font-mono text-[11px] font-semibold text-action-primary"
          >
            {labels.ttftBadgePrefix}: {ttftMs} ms
          </span>
        </div>
      </header>

      {/* Speed selector bar + 🧠 Approfondi pill */}
      <div
        role="group"
        aria-label={labels.headerTitle}
        className="flex flex-wrap items-center gap-2"
      >
        <button
          type="button"
          data-testid="assistant-speed-pill-SPEED_1_FAST"
          aria-pressed={speed === "SPEED_1_FAST"}
          onClick={() => {
            setDeepAuditActive(false);
            setSpeed("SPEED_1_FAST");
          }}
          className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            speed === "SPEED_1_FAST"
              ? "bg-action-primary text-white"
              : "bg-surface-secondary text-text-secondary"
          }`}
        >
          {labels.speed1PillLabel}
        </button>

        <button
          type="button"
          data-testid="assistant-speed-pill-SPEED_2_AGENT_TOOLS"
          aria-pressed={speed === "SPEED_2_AGENT_TOOLS"}
          onClick={() => {
            setDeepAuditActive(false);
            setSpeed("SPEED_2_AGENT_TOOLS");
          }}
          className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            speed === "SPEED_2_AGENT_TOOLS"
              ? "bg-action-primary text-white"
              : "bg-surface-secondary text-text-secondary"
          }`}
        >
          {labels.speed2PillLabel}
        </button>

        <button
          type="button"
          data-testid="assistant-deep-audit-pill-toggle"
          aria-pressed={deepAuditActive}
          onClick={handleToggleDeepAudit}
          className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
            deepAuditActive
              ? "bg-action-primary text-white"
              : "border border-border-subtle bg-surface-secondary text-text-secondary"
          }`}
        >
          {labels.speed3DeepAuditPillLabel}
        </button>
      </div>

      {/* Real-time step progress stream */}
      {stepProgress.length > 0 && (
        <ol
          data-testid="assistant-step-progress-list"
          aria-live="polite"
          className="space-y-1 rounded border border-border-subtle bg-surface-primary p-2.5 text-xs"
        >
          {stepProgress.map((st) => (
            <li
              key={st.stepCode}
              data-testid={`assistant-step-item-${st.stepCode}`}
              className="flex items-center justify-between gap-2"
            >
              <span>{st.label}</span>
              <span className="font-mono text-[11px] text-text-secondary">
                {st.durationMs} ms
              </span>
            </li>
          ))}
        </ol>
      )}

      {/* Error banner if LLM invocation failed */}
      {errorMessage && (
        <div
          role="alert"
          data-testid="assistant-error-banner"
          className="rounded border border-status-warning/40 bg-status-warning/10 p-2.5 text-xs font-medium text-status-warning"
        >
          {errorMessage}
        </div>
      )}

      {/* Streamed answer preview */}
      {streamedText && (
        <div
          data-testid="assistant-streamed-response-box"
          aria-live="polite"
          className="rounded border border-border-subtle bg-surface-primary p-3 text-xs leading-relaxed whitespace-pre-wrap"
        >
          {streamedText}
        </div>
      )}

      {/* Conversational input bar */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="assistant-three-speed-input"
          value={promptText}
          placeholder={labels.inputPlaceholder}
          onChange={(e) => handlePromptChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              triggerSendTurn();
            }
          }}
          className="flex-1 rounded border border-border-subtle bg-surface-primary px-3 py-1.5 text-xs text-text-primary"
        />
        <button
          type="button"
          data-testid="assistant-three-speed-send-btn"
          disabled={isGenerating}
          onClick={triggerSendTurn}
          className="rounded bg-action-primary px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
        >
          {isGenerating ? "⏳ ..." : labels.sendPromptCta}
        </button>
      </div>
    </section>
  );
}
