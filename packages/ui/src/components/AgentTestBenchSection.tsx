import React from "react";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentLifecycleStatus,
  UiAgentTestBenchStatus,
  UiManagedAgentItem,
} from "./AgentsAndSkillsTypes";
import { FormattedMarkdownContent } from "./FormattedMarkdownContent";
import { OrciaIcon } from "./icons";

export interface AgentDetailModalHeaderProps {
  readonly agent: UiManagedAgentItem;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly isPack: boolean;
  readonly lifecycleStatus: UiAgentLifecycleStatus;
  readonly testBenchStatus: UiAgentTestBenchStatus;
  readonly mcpExposed: boolean;
  readonly isUpdatingMcp?: boolean;
  readonly isUpdatingLifecycle?: boolean;
  readonly savedFeedback: boolean;
  readonly onToggleMcpExposure: (checked: boolean) => void;
  readonly onToggleLifecycle?: (nextLifecycle: UiAgentLifecycleStatus) => void;
  readonly onClose?: () => void;
}

export function AgentDetailModalHeader({
  agent,
  labels,
  isPack,
  lifecycleStatus,
  testBenchStatus,
  mcpExposed,
  isUpdatingMcp = false,
  isUpdatingLifecycle = false,
  savedFeedback,
  onToggleMcpExposure,
  onToggleLifecycle,
}: AgentDetailModalHeaderProps): React.JSX.Element {
  const studio = labels.studio;
  const isDraft = lifecycleStatus === "DRAFT";
  const mcpDisabled = isPack || isDraft || isUpdatingMcp;
  const mcpDisabledHint = isPack
    ? studio.mcpPackPresetReadOnlyHint
    : isDraft
      ? studio.mcpDraftBlockedHint
      : undefined;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <code
        data-testid={`agent-modal-handle-${agent.agentId}`}
        className="whitespace-nowrap rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-1.5 py-0.5 font-mono text-[11px]"
      >
        {agent.handle}
      </code>
      <span
        data-testid={`agent-modal-lifecycle-badge-${agent.agentId}`}
        className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2 py-0.5 text-[11px] font-semibold"
        style={{
          color:
            lifecycleStatus === "ACTIVE"
              ? "var(--color-status-success)"
              : "var(--color-arbitration-amber)",
        }}
      >
        {lifecycleStatus === "ACTIVE"
          ? studio.lifecycleActiveBadge
          : studio.lifecycleDraftBadge}
      </span>
      <span
        data-testid={`agent-bench-status-badge-${agent.agentId}`}
        className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2 py-0.5 text-[11px] font-semibold"
        style={
          testBenchStatus === "FAILED"
            ? { color: "var(--color-status-danger)" }
            : undefined
        }
      >
        {testBenchStatus === "PASSED"
          ? studio.benchValidatedBadge
          : testBenchStatus === "FAILED"
            ? studio.benchFailedBadge
            : studio.benchToTestBadge}
      </span>
      {!isPack && onToggleLifecycle && (
        <button
          type="button"
          data-testid={`agent-toggle-lifecycle-btn-${agent.agentId}`}
          disabled={isUpdatingLifecycle}
          onClick={() => onToggleLifecycle(isDraft ? "ACTIVE" : "DRAFT")}
          className="orcia-ds-btn orcia-ds-btn-secondary text-[11px]"
        >
          {isDraft ? studio.activateAgentButton : studio.setDraftAgentButton}
        </button>
      )}
      {savedFeedback && (
        <span
          data-testid={`agent-modal-saved-badge-${agent.agentId}`}
          className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2 py-0.5 text-[11px] font-semibold"
          style={{ color: "var(--color-status-success)" }}
        >
          <OrciaIcon name="check" /> {studio.savedShortBadge}
        </span>
      )}
      <label
        title={mcpDisabledHint || undefined}
        className={`inline-flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1 text-xs font-medium ${
          mcpDisabled ? "opacity-60 cursor-not-allowed" : ""
        }`}
      >
        <input
          type="checkbox"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid={`agent-mcp-expose-checkbox-${agent.agentId}`}
          disabled={mcpDisabled}
          checked={mcpExposed}
          onChange={(e) => onToggleMcpExposure(e.target.checked)}
        />
        <span>
          <OrciaIcon name="plug" /> {studio.exposeMcpLabel}
        </span>
      </label>
      {mcpDisabledHint ? (
        <span
          data-testid={`agent-mcp-disabled-hint-${agent.agentId}`}
          className="text-[11px] text-[var(--orcia-text-secondary)]"
        >
          {mcpDisabledHint}
        </span>
      ) : null}
    </div>
  );
}

export interface AgentTestBenchSectionProps {
  readonly agent: UiManagedAgentItem;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly satisfiedConditionsCount: number;
  readonly testInputValue: string;
  readonly readOnlyPack?: boolean;
  readonly onChangeTestInput: (agentId: string, nextValue: string) => void;
  readonly onRunAgent: () => void;
  readonly sandboxTraceSlot?: React.ReactNode;
}

export function AgentTestBenchSection({
  agent,
  labels,
  satisfiedConditionsCount,
  testInputValue,
  readOnlyPack = false,
  onChangeTestInput,
  onRunAgent,
  sandboxTraceSlot = null,
}: AgentTestBenchSectionProps): React.JSX.Element {
  const studio = labels.studio;
  return (
    <div className="space-y-2 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="font-semibold">
          <OrciaIcon name="playOutline" /> {studio.testBenchHeading}
        </h4>
        <span className="text-[11px] text-[var(--orcia-text-secondary)]">
          {studio.conditionsMetPrefix} {satisfiedConditionsCount}/6
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid={`agent-test-input-${agent.agentId}`}
          disabled={readOnlyPack}
          value={testInputValue}
          onChange={(e) => onChangeTestInput(agent.agentId, e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !readOnlyPack) {
              e.preventDefault();
              onRunAgent();
            }
          }}
          placeholder={labels.testAgentInputPlaceholder}
          className="orcia-ds-input flex-1 disabled:opacity-60"
        />
        <button
          type="button"
          data-testid={`run-agent-btn-${agent.agentId}`}
          disabled={readOnlyPack}
          title={readOnlyPack ? studio.mcpPackPresetReadOnlyHint : undefined}
          onClick={() => {
            if (!readOnlyPack) onRunAgent();
          }}
          className="orcia-ds-btn orcia-ds-btn-primary text-xs disabled:opacity-60 disabled:cursor-not-allowed"
        >
          <OrciaIcon name="lightning" /> {labels.runAgentButtonLabel}
        </button>
      </div>
      {readOnlyPack && (
        <p
          data-testid={`agent-bench-pack-readonly-hint-${agent.agentId}`}
          className="text-[11px] text-[var(--orcia-text-secondary)]"
        >
          {studio.mcpPackPresetReadOnlyHint}
        </p>
      )}
      {sandboxTraceSlot ? (
        <div data-testid="agent-sandbox-trace-slot">{sandboxTraceSlot}</div>
      ) : null}
      {agent.lastExecutionOutput && (
        <div
          data-testid={`agent-execution-output-${agent.agentId}`}
          className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2.5"
        >
          <FormattedMarkdownContent
            content={agent.lastExecutionOutput}
            copyLabel={studio.copyCodeLabel}
            copiedLabel={studio.copiedShortLabel}
          />
        </div>
      )}
    </div>
  );
}
