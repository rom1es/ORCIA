import React, { useState } from "react";
import type {
  UiAgentHumanPartnerRole,
  UiAgentOutputContractFormat,
  UiAgentPosture,
} from "./AgentGovernanceTypesAndDefaults";
import {
  AgentStudioCardBadgesRow,
  AgentStudioGovernancePassport,
} from "./AgentStudioCardBadgesAndPassport";
import type { AgentStudioCardItemProps } from "./AgentStudioCardTypes";
import type { UiAgentSkillVisibilityScope } from "./AgentsAndSkillsTypes";
import { FormattedMarkdownContent } from "./FormattedMarkdownContent";
import { OrciaIcon } from "./icons";

export type { AgentStudioCardItemProps };

export const AgentStudioCardItem: React.FC<AgentStudioCardItemProps> = ({
  agent,
  skills,
  labels,
  onDeleteAgent,
  onDuplicateAgent,
  onToggleAgentEnabled,
  onOpenDetailModal,
  onUpdateAgentThinkingLevel,
  onUpdateAgentVisibility,
  onUseAgentInAssistant,
}) => {
  const [copiedHandle, setCopiedHandle] = useState(false);
  const [autosavedBadgeVisible, setAutosavedBadgeVisible] = useState(false);
  const studio = labels.studio;

  const visibilityScope: UiAgentSkillVisibilityScope = agent.visibilityScope ?? "TEAM";
  const isPack = visibilityScope === "PACK";
  const isEnabled = agent.enabledOnWorkspace !== false;
  const posture: UiAgentPosture = agent.posture ?? "PRODUCER";
  const partnerRole: UiAgentHumanPartnerRole = agent.humanPartnerRole ?? "PO_PM";
  const outputFormat: UiAgentOutputContractFormat =
    agent.outputContractFormat ?? "markdown_structure";
  const writePreviewRequired = agent.writePreviewRequired !== false;
  const testBenchValidated = Boolean(
    agent.testBenchValidated || agent.lastExecutionOutput || isPack,
  );
  const attachedSkills = skills.filter((sk) => agent.skillIds.includes(sk.skillId));

  const handleCopyHandle = () => {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      void navigator.clipboard.writeText(agent.handle).catch((err: unknown) => {
        if (typeof console !== "undefined") {
          console.debug(
            "[orcia:clipboard]",
            err instanceof Error ? err.message : String(err),
          );
        }
      });
    }
    setCopiedHandle(true);
  };

  const handleToggleVisibilityClick = () => {
    if (isPack) return;
    const nextScope: UiAgentSkillVisibilityScope =
      visibilityScope === "PRIVATE" ? "TEAM" : "PRIVATE";
    onUpdateAgentVisibility?.(agent.agentId, nextScope);
    setAutosavedBadgeVisible(true);
  };

  return (
    <div
      data-testid={`agent-card-${agent.agentId}`}
      className="orcia-bento-card space-y-2.5 p-4 text-xs"
    >
      <AgentStudioCardBadgesRow
        agent={agent}
        labels={labels}
        visibilityScope={visibilityScope}
        isPack={isPack}
        isEnabled={isEnabled}
        posture={posture}
        partnerRole={partnerRole}
        testBenchValidated={testBenchValidated}
        copiedHandle={copiedHandle}
        autosavedBadgeVisible={autosavedBadgeVisible}
        onCopyHandle={handleCopyHandle}
        onToggleVisibility={handleToggleVisibilityClick}
        onUpdateThinkingLevel={(lvl) => {
          onUpdateAgentThinkingLevel?.(agent.agentId, lvl);
          setAutosavedBadgeVisible(true);
        }}
      />

      <div className="space-y-1.5">
        <p className="text-[var(--orcia-text-secondary)]">{agent.roleMission}</p>

        <AgentStudioGovernancePassport
          agent={agent}
          labels={labels}
          outputFormat={outputFormat}
          writePreviewRequired={writePreviewRequired}
        />

        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-medium text-[var(--orcia-text-secondary)]">
            {labels.attachedSkillsLabel} :
          </span>
          {attachedSkills.length === 0 ? (
            <span className="text-[11px] text-[var(--orcia-text-secondary)]">
              {studio.noAttachedSkillsLabel}
            </span>
          ) : (
            attachedSkills.map((sk) => (
              <span
                key={sk.skillId}
                className="inline-flex items-center gap-1 rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px]"
              >
                <OrciaIcon name="tools" /> {sk.name} (
                <code className="font-mono text-[10px]">{sk.commandHandle}</code>)
              </span>
            ))
          )}
          <button
            type="button"
            onClick={() => onOpenDetailModal?.(agent)}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-medium"
          >
            {studio.manageBlocksButton}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
        <div className="flex flex-wrap items-center gap-2">
          {onUseAgentInAssistant && (
            <button
              type="button"
              data-testid={`use-agent-in-assistant-btn-${agent.agentId}`}
              onClick={() => onUseAgentInAssistant(agent)}
              className="orcia-ds-btn orcia-ds-btn-cobalt-outline text-[11px]"
            >
              <OrciaIcon name="assistant" /> {studio.useInAssistantButton}
            </button>
          )}
          <button
            type="button"
            data-testid={`open-agent-detail-modal-btn-${agent.agentId}`}
            onClick={() => onOpenDetailModal?.(agent)}
            className="orcia-ds-btn orcia-ds-btn-secondary text-[11px]"
          >
            <OrciaIcon name="configuration" />{" "}
            {studio.configureAndTestSixBlocksButton}
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {isPack ? (
            <>
              <button
                type="button"
                data-testid={`duplicate-agent-btn-${agent.agentId}`}
                onClick={() => onDuplicateAgent?.(agent)}
                className="orcia-ds-btn orcia-ds-btn-secondary text-[11px]"
              >
                <OrciaIcon name="copy" /> {studio.duplicateAndCustomizeButton}
              </button>
              <button
                type="button"
                data-testid={`toggle-agent-enabled-btn-${agent.agentId}`}
                onClick={() => onToggleAgentEnabled?.(agent.agentId, !isEnabled)}
                className="orcia-ds-btn orcia-ds-btn-secondary text-[11px]"
              >
                {isEnabled
                  ? studio.disableOnWorkspaceButton
                  : studio.enableOnWorkspaceButton}
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                data-testid={`duplicate-agent-btn-${agent.agentId}`}
                onClick={() => onDuplicateAgent?.(agent)}
                className="orcia-ds-btn orcia-ds-btn-secondary text-[11px]"
              >
                <OrciaIcon name="copy" /> {studio.duplicateButton}
              </button>
              <button
                type="button"
                data-testid={`delete-agent-btn-${agent.agentId}`}
                onClick={() => onDeleteAgent(agent.agentId)}
                className="orcia-ds-btn orcia-ds-btn-secondary text-[11px]"
              >
                {labels.deleteAgentButtonLabel}
              </button>
            </>
          )}
        </div>
      </div>

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
};
