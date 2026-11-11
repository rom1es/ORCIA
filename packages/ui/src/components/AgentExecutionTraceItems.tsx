import React, { useState } from "react";
import type {
  AgentExecutionTraceLabels,
  UiAgentTraceEventItem,
  UiReflexivePendingWritePreview,
  UiSourceLineInspectTarget,
} from "./AgentExecutionTraceTypes";
import { OrciaIcon } from "./icons";

export interface TraceEventRowProps {
  readonly item: UiAgentTraceEventItem;
  readonly childEvents?: readonly UiAgentTraceEventItem[];
  readonly labels: AgentExecutionTraceLabels;
  readonly onInspectLines: (target: UiSourceLineInspectTarget) => void;
}

export function TraceEventRow({
  item,
  childEvents = [],
  labels,
  onInspectLines,
}: TraceEventRowProps): React.JSX.Element | null {
  const [thoughtOpen, setThoughtOpen] = useState<boolean>(false);
  const [delegationOpen, setDelegationOpen] = useState<boolean>(true);

  if (item.kind === "THOUGHT_COMPLETED" || item.kind === "THOUGHT_DELTA") {
    const secs = Math.max(1, Math.round(item.durationSeconds ?? 1));
    const summaryText =
      item.kind === "THOUGHT_DELTA"
        ? labels.thoughtInProgressLabel
        : labels.thoughtSummaryLabel(secs);
    const bodyText = (item.thoughtContent ?? item.label ?? "").trim();

    return (
      <div className="space-y-1 text-xs" data-testid={`trace-event-thought-${item.eventId}`}>
        <button
          type="button"
          data-testid="trace-thought-toggle-btn"
          aria-expanded={thoughtOpen}
          onClick={() => setThoughtOpen((prev) => !prev)}
          className="inline-flex items-center gap-1.5 rounded px-1.5 py-0.5 text-left text-[11.5px] font-medium text-text-secondary hover:bg-surface-secondary hover:text-text-primary transition-colors"
        >
          <OrciaIcon name="brain" />
          <span>{summaryText}</span>
          <OrciaIcon name={thoughtOpen ? "chevronDown" : "chevronRight"} />
        </button>
        {thoughtOpen && bodyText.length > 0 ? (
          <pre
            data-testid="trace-thought-content"
            style={{
              margin: 0,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              borderLeft: "2px solid var(--color-border-strong)",
              paddingLeft: "10px",
              color: "var(--color-text-secondary)",
              fontFamily: "var(--font-sans)",
              fontSize: "11.5px",
              lineHeight: 1.5,
            }}
          >
            {bodyText}
          </pre>
        ) : null}
      </div>
    );
  }

  if (item.kind === "FILE_ANALYZED") {
    const uri = item.resourceUri ?? "";
    const startLine = Math.max(1, item.startLine ?? 1);
    const endLine = Math.max(startLine, item.endLine ?? startLine);
    const filename =
      item.displayFilename ||
      uri.split("/").pop() ||
      uri ||
      "source";
    const badgeCode = item.fileBadgeCode || "DOC";

    return (
      <div
        className="flex flex-wrap items-center gap-1.5 text-xs"
        data-testid={`trace-event-file-${item.eventId}`}
      >
        <span className="text-[11.5px] text-text-secondary">{labels.analyzedPrefix}</span>
        <button
          type="button"
          data-testid="trace-file-analyzed-pill"
          data-resource-uri={uri}
          data-start-line={startLine}
          data-end-line={endLine}
          onClick={() =>
            onInspectLines({
              uri,
              startLine,
              endLine,
              filename,
              badgeCode,
            })
          }
          className="orcia-execution-trace-pill"
        >
          <span className="orcia-execution-trace-badge">{badgeCode}</span>
          <span className="truncate max-w-[220px] font-medium">{filename}</span>
          <code
            className="font-mono text-[11px]"
            style={{ color: "var(--color-action-primary)" }}
          >
            {labels.linesRangeShort(startLine, endLine)}
          </code>
          {item.redacted ? (
            <span
              className="inline-flex items-center gap-1 text-[10.5px] font-semibold"
              style={{ color: "var(--color-arbitration-amber)" }}
            >
              <OrciaIcon name="lock" />
              <span>{labels.redactedPillSuffix}</span>
            </span>
          ) : null}
        </button>
      </div>
    );
  }

  if (item.kind === "AGENT_DELEGATED") {
    const rawAgent = item.delegatedAgentSlug || item.actorSlug || "agent";
    const agentHandle = rawAgent.startsWith("@") ? rawAgent : `@${rawAgent}`;

    return (
      <div
        data-testid="trace-delegated-agent-block"
        className="rounded border px-2.5 py-1.5 space-y-1.5"
        style={{
          borderColor: "var(--color-border-subtle)",
          backgroundColor: "var(--color-surface-card)",
        }}
      >
        <button
          type="button"
          data-testid="trace-delegation-toggle-btn"
          aria-expanded={delegationOpen}
          onClick={() => setDelegationOpen((prev) => !prev)}
          className="flex w-full items-center justify-between gap-2 text-left text-xs font-semibold text-text-primary"
        >
          <span className="inline-flex items-center gap-1.5 flex-wrap">
            <OrciaIcon name="agents" />
            <span>{labels.delegatedPrefix(agentHandle)}</span>
            {item.label ? (
              <span className="font-normal text-text-secondary">— {item.label}</span>
            ) : null}
          </span>
          <OrciaIcon name={delegationOpen ? "chevronDown" : "chevronRight"} />
        </button>
        {delegationOpen && childEvents.length > 0 ? (
          <div className="pl-3 space-y-1.5 border-l" style={{ borderColor: "var(--color-border-subtle)" }}>
            {childEvents.map((sub) => (
              <TraceEventRow
                key={sub.eventId}
                item={sub}
                labels={labels}
                onInspectLines={onInspectLines}
              />
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  if (item.kind === "CHECK_EXECUTED" || item.kind === "SYNTHESIS_READY") {
    return (
      <div
        data-testid={`trace-event-check-${item.eventId}`}
        className="flex items-start gap-1.5 text-[11.5px] text-text-secondary"
      >
        <OrciaIcon
          name={item.kind === "SYNTHESIS_READY" ? "sparkles" : "search"}
          className="mt-0.5 shrink-0"
        />
        <span>{item.label}</span>
      </div>
    );
  }

  return null;
}

export interface TraceWritePreviewCardProps {
  readonly preview: UiReflexivePendingWritePreview;
  readonly labels: AgentExecutionTraceLabels;
  readonly onApproveWrite: (previewId: string) => void;
  readonly onRejectWrite: (previewId: string) => void;
}

export function TraceWritePreviewCard({
  preview,
  labels,
  onApproveWrite,
  onRejectWrite,
}: TraceWritePreviewCardProps): React.JSX.Element {
  return (
    <div
      data-testid="trace-write-preview-card"
      className="rounded border p-3 space-y-2 text-xs"
      style={{
        backgroundColor: "var(--color-arbitration-bg)",
        borderColor: "var(--color-arbitration-amber)",
        color: "var(--color-text-primary)",
      }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <strong className="inline-flex items-center gap-1.5 text-xs">
          <OrciaIcon name="shield" />
          <span>{labels.writePreviewHeading}</span>
        </strong>
        <span className="rounded px-2 py-0.5 font-mono text-[11px]" style={{ backgroundColor: "var(--color-surface-card)" }}>
          {labels.writePreviewTargetPrefix} {preview.targetConnector}
        </span>
      </div>
      <p className="m-0 text-xs">{preview.actionSummary}</p>
      <div className="flex flex-wrap items-center gap-2 pt-0.5">
        <button
          type="button"
          data-testid="trace-approve-write-btn"
          onClick={() => onApproveWrite(preview.previewId)}
          className="orcia-ds-btn orcia-ds-btn-primary text-xs"
        >
          <OrciaIcon name="check" />
          <span>{labels.approveWriteButtonLabel}</span>
        </button>
        <button
          type="button"
          data-testid="trace-reject-write-btn"
          onClick={() => onRejectWrite(preview.previewId)}
          className="orcia-ds-btn orcia-ds-btn-secondary text-xs"
        >
          <OrciaIcon name="cross" />
          <span>{labels.rejectWriteButtonLabel}</span>
        </button>
      </div>
    </div>
  );
}
