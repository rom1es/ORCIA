import React from "react";
import {
  formatAgentModelPassportSummary,
  type UiAgentHumanPartnerRole,
  type UiAgentOutputContractFormat,
  type UiAgentPosture,
} from "./AgentGovernanceTypesAndDefaults";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
} from "./AgentsAndSkillsTypes";
import { OrciaIcon } from "./icons";

export interface AgentStudioCardBadgesRowProps {
  readonly agent: UiManagedAgentItem;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly visibilityScope: UiAgentSkillVisibilityScope;
  readonly isPack: boolean;
  readonly isEnabled: boolean;
  readonly posture: UiAgentPosture;
  readonly partnerRole: UiAgentHumanPartnerRole;
  readonly testBenchValidated: boolean;
  readonly copiedHandle: boolean;
  readonly autosavedBadgeVisible: boolean;
  readonly onCopyHandle: () => void;
  readonly onToggleVisibility: () => void;
  readonly onUpdateThinkingLevel: (level: UiAgentThinkingLevel) => void;
}

export const AgentStudioCardBadgesRow: React.FC<
  AgentStudioCardBadgesRowProps
> = ({
  agent,
  labels,
  visibilityScope,
  isPack,
  isEnabled,
  posture,
  partnerRole,
  testBenchValidated,
  copiedHandle,
  autosavedBadgeVisible,
  onCopyHandle,
  onToggleVisibility,
  onUpdateThinkingLevel,
}) => {
  const studio = labels.studio;
  const visibilityBadgeContent =
    visibilityScope === "PRIVATE" ? (
      <>
        <OrciaIcon name="lock" /> {studio.visibilityPrivateShort}
      </>
    ) : visibilityScope === "PACK" ? (
      <>
        <OrciaIcon name="spaces" /> {studio.visibilityPackPrefix} (
        {agent.sourcePackKey ?? "orcia-pack-sdlc"})
      </>
    ) : (
      <>
        <OrciaIcon name="team" /> {studio.visibilityTeamShort}
      </>
    );

  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <strong className="text-sm text-[var(--orcia-text-primary)]">
          {agent.name}
        </strong>
        <code
          data-testid={`agent-handle-${agent.agentId}`}
          title={agent.handle}
          className="whitespace-nowrap rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 font-mono text-[11px]"
        >
          {agent.handle}
        </code>
        <button
          type="button"
          data-testid={`copy-agent-handle-btn-${agent.agentId}`}
          onClick={onCopyHandle}
          title={studio.copyHandleTitle}
          className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-1.5 py-0.5 text-[10px] font-medium"
        >
          {copiedHandle ? (
            <>
              <OrciaIcon name="check" /> {studio.copiedShortLabel}
            </>
          ) : (
            studio.copyHandleButton
          )}
        </button>

        <span
          data-testid={`agent-posture-badge-${agent.agentId}`}
          className="inline-flex items-center gap-1 rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-semibold"
        >
          <OrciaIcon name={posture === "EVALUATOR_GATE" ? "shield" : "tools"} size={12} />
          {posture === "EVALUATOR_GATE"
            ? studio.postureEvaluatorBadge
            : studio.postureProducerBadge}
        </span>

        <span
          data-testid={`agent-partner-badge-${agent.agentId}`}
          className="inline-flex items-center gap-1 rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px]"
        >
          <OrciaIcon name="user" size={12} />
          {studio.partnerBadgePrefix}{" "}
          {studio.humanPartnerRoles[partnerRole].split(" (")[0]}
        </span>

        {isPack ? (
          <span
            data-testid={`agent-visibility-badge-${agent.agentId}`}
            className="inline-flex items-center gap-1 rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-medium"
          >
            {visibilityBadgeContent}
          </span>
        ) : (
          <button
            type="button"
            data-testid={`agent-visibility-badge-${agent.agentId}`}
            onClick={onToggleVisibility}
            title={studio.toggleVisibilityTitle}
            className="inline-flex items-center gap-1 rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-medium"
          >
            {visibilityBadgeContent}
          </button>
        )}

        <span
          data-testid={`agent-test-bench-badge-${agent.agentId}`}
          className="inline-flex items-center gap-1 rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-medium"
        >
          <OrciaIcon name={testBenchValidated ? "check" : "clock"} size={12} />
          {testBenchValidated
            ? studio.benchValidatedBadge
            : studio.benchShortToTestBadge}
        </span>

        {!isEnabled && (
          <span
            data-testid={`agent-disabled-badge-${agent.agentId}`}
            className="inline-flex items-center gap-1 rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-medium text-[var(--orcia-text-secondary)]"
          >
            <OrciaIcon name="hourglass" size={12} />
            {studio.disabledWorkspaceBadge}
          </span>
        )}

        {agent.mcpExposed && (
          <span
            data-testid={`agent-mcp-active-badge-${agent.agentId}`}
            className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-semibold"
          >
            <OrciaIcon name="plug" /> {studio.mcpActiveBadge}
          </span>
        )}

        {autosavedBadgeVisible && (
          <span
            data-testid={`agent-autosaved-badge-${agent.agentId}`}
            className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-semibold"
            style={{ color: "var(--color-status-success)" }}
          >
            <OrciaIcon name="check" /> {studio.savedShortBadge}
          </span>
        )}
      </div>

      <label className="inline-flex items-center gap-1.5">
        <span className="font-medium text-[var(--orcia-text-secondary)]">
          {labels.agentThinkingLevelLabel} :
        </span>
        <select
          data-testid={`agent-card-thinking-select-${agent.agentId}`}
          value={agent.thinkingLevel}
          onChange={(e) =>
            onUpdateThinkingLevel(e.target.value as UiAgentThinkingLevel)
          }
          className="orcia-ds-select text-[11px]"
        >
          {(["simple", "medium", "complex", "auto"] as const).map((lvl) => (
            <option key={lvl} value={lvl}>
              {labels.thinkingLevels[lvl]}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
};

export interface AgentStudioGovernancePassportProps {
  readonly agent: UiManagedAgentItem;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly outputFormat: UiAgentOutputContractFormat;
  readonly writePreviewRequired: boolean;
}

export const AgentStudioGovernancePassport: React.FC<
  AgentStudioGovernancePassportProps
> = ({ agent, labels, outputFormat, writePreviewRequired }) => {
  const studio = labels.studio;
  return (
    <div
      data-testid={`agent-governance-passport-${agent.agentId}`}
      className="flex flex-wrap items-center gap-1.5 text-[11px] text-[var(--orcia-text-secondary)]"
    >
      <span className="inline-flex items-center gap-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5">
        <OrciaIcon name="brain" size={12} />
        <span>
          {studio.modelPassportLabel}{" "}
          {formatAgentModelPassportSummary(
            agent.llmModelTier,
            agent.temperature,
            agent.maxTokens,
            studio,
          )}
        </span>
      </span>
      <span className="inline-flex items-center gap-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5">
        <OrciaIcon name="books" size={12} />
        <span>
          {studio.ragShortLabel} (
          {(agent.allowedRagSources ?? ["all_workspace_sources"]).length}
          {") & "}
          {studio.ontologyShortLabel} (
          {(agent.ontologyViews ?? ["glossary"]).length})
        </span>
      </span>
      <span className="inline-flex items-center gap-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5">
        <OrciaIcon name="document" size={12} />
        <span>
          {studio.outputShortLabel}{" "}
          {studio.outputContractFormats[outputFormat].split(" (")[0]}
        </span>
      </span>
      {writePreviewRequired && (
        <span className="inline-flex items-center gap-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5">
          <OrciaIcon name="shield" size={12} />
          <span>{studio.writePreviewBadge}</span>
        </span>
      )}
    </div>
  );
};
