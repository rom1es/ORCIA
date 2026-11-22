import React from "react";
import { OrciaIcon } from "../components/icons";
import type { UiSourceLineInspectTarget } from "../components/AgentExecutionTraceTypes";

export type UiAssistantToolCallStatus =
  | "RUNNING"
  | "EXECUTED"
  | "DENIED"
  | "ERROR"
  | "DEDUPLICATED"
  | "APPROVAL_REQUIRED";

export interface UiAssistantToolCallStepItem {
  readonly toolCallId: string;
  readonly toolName: string;
  readonly status: UiAssistantToolCallStatus;
  readonly summary?: string | null;
  readonly durationMs?: number | null;
  readonly targetUri?: string | null;
  readonly startLine?: number | null;
  readonly endLine?: number | null;
}

export interface AssistantToolCallTraceLabels {
  readonly heading: string;
  readonly runningLabel: string;
  readonly executedLabel: string;
  readonly deniedLabel: string;
  readonly errorLabel: string;
  readonly approvalRequiredLabel: string;
  readonly inspectLinesLabel: string;
  readonly durationSuffix: string;
}

export interface AssistantToolCallTraceProps {
  readonly steps: readonly UiAssistantToolCallStepItem[];
  readonly labels: AssistantToolCallTraceLabels;
  readonly onInspectLines?: (target: UiSourceLineInspectTarget) => void;
}

function resolveStatusDisplay(
  status: UiAssistantToolCallStatus,
  labels: AssistantToolCallTraceLabels,
): { readonly label: string; readonly colorVar: string; readonly bgVar: string } {
  switch (status) {
    case "EXECUTED":
    case "DEDUPLICATED":
      return {
        label: labels.executedLabel,
        colorVar: "var(--color-gate-emerald)",
        bgVar: "var(--color-gate-emerald-bg)",
      };
    case "APPROVAL_REQUIRED":
      return {
        label: labels.approvalRequiredLabel,
        colorVar: "var(--color-arbitration-amber)",
        bgVar: "var(--color-arbitration-bg)",
      };
    case "DENIED":
    case "ERROR":
      return {
        label: labels.errorLabel,
        colorVar: "var(--color-stale-crimson)",
        bgVar: "var(--color-stale-bg)",
      };
    default:
      return {
        label: labels.runningLabel,
        colorVar: "var(--color-action-primary)",
        bgVar: "var(--color-action-primary-subtle)",
      };
  }
}

export function AssistantToolCallTrace({
  steps,
  labels,
  onInspectLines,
}: AssistantToolCallTraceProps): React.JSX.Element | null {
  if (steps.length === 0) return null;

  return (
    <section
      data-testid="assistant-tool-call-trace"
      className="rounded-lg border border-border-subtle bg-surface-elevated p-3 text-xs space-y-2"
    >
      <header className="flex items-center justify-between gap-2 font-semibold text-text-primary">
        <span className="inline-flex items-center gap-1.5">
          <OrciaIcon name="tools" />
          <span>{labels.heading}</span>
        </span>
        <span className="font-mono text-[11px] text-text-secondary">{steps.length}</span>
      </header>
      <ul className="space-y-1.5">
        {steps.map((step) => {
          const badge = resolveStatusDisplay(step.status, labels);
          const hasUri = Boolean(step.targetUri);
          const startLine = Math.max(1, step.startLine ?? 1);
          const endLine = Math.max(startLine, step.endLine ?? startLine + 24);
          return (
            <li
              key={step.toolCallId}
              data-testid={`assistant-tool-call-item-${step.toolCallId}`}
              className="flex flex-wrap items-center justify-between gap-2 rounded border border-border-subtle bg-surface-primary px-2.5 py-1.5"
            >
              <div className="min-w-0 flex-1 space-y-0.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-[11px] font-semibold text-text-primary">
                    {step.toolName}
                  </span>
                  <span
                    data-testid={`assistant-tool-call-status-${step.status}`}
                    style={{ color: badge.colorVar, backgroundColor: badge.bgVar }}
                    className="rounded-full px-2 py-0.5 text-[10px] font-semibold"
                  >
                    {badge.label}
                  </span>
                  {step.durationMs !== undefined && step.durationMs !== null ? (
                    <span className="font-mono text-[10px] text-text-secondary">
                      {Math.max(1, Math.round(step.durationMs))} {labels.durationSuffix}
                    </span>
                  ) : null}
                </div>
                {step.summary ? (
                  <p className="m-0 truncate text-[11px] text-text-secondary">{step.summary}</p>
                ) : null}
              </div>
              {hasUri && onInspectLines ? (
                <button
                  type="button"
                  data-testid={`assistant-tool-call-inspect-btn-${step.toolCallId}`}
                  onClick={() =>
                    onInspectLines({
                      uri: step.targetUri!,
                      startLine,
                      endLine,
                    })
                  }
                  className="rounded border border-border-subtle bg-surface-secondary px-2 py-0.5 text-[11px] font-medium text-action-primary hover:bg-surface-elevated"
                >
                  {labels.inspectLinesLabel}
                </button>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
