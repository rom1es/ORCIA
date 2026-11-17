import React, { useMemo, useState } from "react";
import {
  TraceEventRow,
  TraceWritePreviewCard,
} from "./AgentExecutionTraceItems";
import type {
  AgentExecutionTraceLabels,
  UiAgentTraceEventItem,
  UiReflexivePendingWritePreview,
  UiReflexiveSessionStatus,
  UiSourceLineInspectTarget,
} from "./AgentExecutionTraceTypes";
import { OrciaIcon } from "./icons";

export interface AgentExecutionTraceProps {
  readonly status: UiReflexiveSessionStatus;
  readonly events: readonly UiAgentTraceEventItem[];
  readonly pendingWritePreview?: UiReflexivePendingWritePreview | null;
  readonly labels: AgentExecutionTraceLabels;
  readonly onInspectLines: (target: UiSourceLineInspectTarget) => void;
  readonly onSynthesizeNow: () => void;
  readonly onApproveWrite: (previewId: string) => void;
  readonly onRejectWrite: (previewId: string) => void;
  readonly defaultCollapsedWhenCompleted?: boolean;
}

interface TraceGroupSection {
  readonly key: string;
  readonly title: string;
  readonly items: readonly UiAgentTraceEventItem[];
  readonly delegatedChildrenByParentId: ReadonlyMap<string, readonly UiAgentTraceEventItem[]>;
}

function groupTraceEvents(
  events: readonly UiAgentTraceEventItem[],
  defaultTitle: string,
): readonly TraceGroupSection[] {
  const sorted = [...events].sort((a, b) => a.sequence - b.sequence);
  const groups: Array<{
    key: string;
    title: string;
    items: UiAgentTraceEventItem[];
    delegatedChildrenByParentId: Map<string, UiAgentTraceEventItem[]>;
  }> = [];

  let activeGroup: (typeof groups)[number] | null = null;
  let activeDelegationParent: { eventId: string; agentSlug: string } | null = null;

  for (const ev of sorted) {
    if (ev.kind === "EXECUTION_FINISHED") {
      continue;
    }
    if (ev.kind === "GROUP_HEADER") {
      const key = ev.groupKey || ev.eventId || `group-${groups.length + 1}`;
      activeGroup = {
        key,
        title: ev.label || defaultTitle,
        items: [],
        delegatedChildrenByParentId: new Map(),
      };
      groups.push(activeGroup);
      activeDelegationParent = null;
      continue;
    }

    if (!activeGroup) {
      activeGroup = {
        key: ev.groupKey || "default-group",
        title: defaultTitle,
        items: [],
        delegatedChildrenByParentId: new Map(),
      };
      groups.push(activeGroup);
    }

    if (ev.kind === "AGENT_DELEGATED") {
      activeGroup.items.push(ev);
      const slug = (ev.delegatedAgentSlug || "").replace(/^@/, "");
      activeDelegationParent = slug ? { eventId: ev.eventId, agentSlug: slug } : null;
      continue;
    }

    if (ev.kind === "WRITE_PREVIEW_REQUESTED") {
      continue;
    }

    const cleanActor = (ev.actorSlug || "").replace(/^@/, "");
    if (
      activeDelegationParent &&
      cleanActor &&
      cleanActor === activeDelegationParent.agentSlug
    ) {
      const existing =
        activeGroup.delegatedChildrenByParentId.get(activeDelegationParent.eventId) ?? [];
      activeGroup.delegatedChildrenByParentId.set(activeDelegationParent.eventId, [
        ...existing,
        ev,
      ]);
      continue;
    }

    activeDelegationParent = null;
    activeGroup.items.push(ev);
  }

  return groups;
}

export function AgentExecutionTrace({
  status,
  events,
  pendingWritePreview = null,
  labels,
  onInspectLines,
  onSynthesizeNow,
  onApproveWrite,
  onRejectWrite,
  defaultCollapsedWhenCompleted = false,
}: AgentExecutionTraceProps): React.JSX.Element | null {
  const [manualOpenByKey, setManualOpenByKey] = useState<Record<string, boolean>>({});

  const groups = useMemo(
    () => groupTraceEvents(events, labels.defaultGroupTitle),
    [events, labels.defaultGroupTitle],
  );

  const visibleStepCount = useMemo(
    () =>
      events.filter(
        (e) =>
          e.kind !== "GROUP_HEADER" &&
          e.kind !== "EXECUTION_FINISHED" &&
          e.kind !== "THOUGHT_DELTA",
      ).length,
    [events],
  );

  const derivedWritePreview: UiReflexivePendingWritePreview | null = useMemo(() => {
    if (pendingWritePreview) return pendingWritePreview;
    const reqEv = [...events].reverse().find((e) => e.kind === "WRITE_PREVIEW_REQUESTED");
    if (!reqEv || status !== "WAITING_WRITE_PREVIEW") return null;
    return {
      previewId: reqEv.eventId,
      targetConnector: reqEv.actorSlug || "workspace",
      actionSummary: reqEv.writePreviewSummary || reqEv.label,
    };
  }, [events, pendingWritePreview, status]);

  if (groups.length === 0 && !derivedWritePreview && status !== "RUNNING" && status !== "SYNTHESIZING") {
    return null;
  }

  const isRunning = status === "RUNNING" || status === "SYNTHESIZING";
  const statusText =
    status === "RUNNING"
      ? labels.runningStatus
      : status === "SYNTHESIZING"
        ? labels.synthesizingStatus
        : status === "WAITING_WRITE_PREVIEW"
          ? labels.pausedWriteStatus
          : status === "CANCELLED"
            ? labels.cancelledStatus
            : status === "FAILED"
              ? labels.failedStatus
              : labels.completedStatus;

  return (
    <section
      data-testid="agent-execution-trace"
      data-trace-status={status}
      aria-label={labels.heading}
      className="orcia-execution-trace"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="inline-flex items-center gap-1.5 font-semibold text-text-primary">
          <OrciaIcon
            name={
              isRunning
                ? "hourglass"
                : status === "WAITING_WRITE_PREVIEW"
                  ? "shield"
                  : status === "FAILED"
                    ? "warning"
                    : "check"
            }
          />
          <span data-testid="trace-status-label">{statusText}</span>
        </div>
        {visibleStepCount > 0 ? (
          <span
            data-testid="trace-steps-counter"
            className="text-[11px] font-medium text-text-secondary"
          >
            {labels.stepsCountLabel(visibleStepCount)}
          </span>
        ) : null}
      </header>

      <div className="space-y-2">
        {groups.map((grp, index) => {
          const isLastGroup = index === groups.length - 1;
          const autoOpen = isRunning
            ? isLastGroup || groups.length === 1
            : !defaultCollapsedWhenCompleted;
          const isOpen = manualOpenByKey[grp.key] ?? autoOpen;

          return (
            <div
              key={grp.key}
              data-testid={`trace-group-${grp.key}`}
              className="space-y-1.5"
            >
              <button
                type="button"
                data-testid="trace-group-header-btn"
                aria-expanded={isOpen}
                aria-label={
                  isOpen
                    ? `${labels.collapseGroupAriaLabel} : ${grp.title}`
                    : `${labels.expandGroupAriaLabel} : ${grp.title}`
                }
                onClick={() =>
                  setManualOpenByKey((prev) => ({
                    ...prev,
                    [grp.key]: !isOpen,
                  }))
                }
                className="flex w-full items-center justify-between gap-2 rounded px-1.5 py-1 text-left text-xs font-semibold text-text-primary hover:bg-surface-secondary transition-colors"
              >
                <span className="inline-flex items-center gap-1.5">
                  <OrciaIcon name={isOpen ? "chevronDown" : "chevronRight"} />
                  <span>{grp.title}</span>
                </span>
                <span className="text-[11px] font-normal text-text-secondary">
                  {grp.items.length}
                </span>
              </button>

              {isOpen && grp.items.length > 0 ? (
                <div
                  data-testid="trace-group-items"
                  className="pl-4 space-y-1.5 border-l"
                  style={{ borderColor: "var(--color-border-subtle)" }}
                >
                  {grp.items.map((item) => (
                    <TraceEventRow
                      key={item.eventId}
                      item={item}
                      childEvents={
                        grp.delegatedChildrenByParentId.get(item.eventId) ?? []
                      }
                      labels={labels}
                      onInspectLines={onInspectLines}
                    />
                  ))}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      {derivedWritePreview ? (
        <TraceWritePreviewCard
          preview={derivedWritePreview}
          labels={labels}
          onApproveWrite={onApproveWrite}
          onRejectWrite={onRejectWrite}
        />
      ) : null}

      {status === "RUNNING" ? (
        <footer
          data-testid="trace-running-footer"
          className="flex flex-wrap items-center justify-between gap-2 border-t pt-2"
          style={{ borderColor: "var(--color-border-subtle)" }}
        >
          <span className="text-[11px] text-text-secondary">
            {labels.synthesizeNowButtonHint}
          </span>
          <button
            type="button"
            data-testid="trace-synthesize-now-btn"
            onClick={onSynthesizeNow}
            className="orcia-ds-btn orcia-ds-btn-secondary text-xs"
          >
            <OrciaIcon name="sparkles" />
            <span>{labels.synthesizeNowButtonLabel}</span>
          </button>
        </footer>
      ) : null}
    </section>
  );
}
