import React, { useState } from "react";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
  UiManagedSkillItem,
} from "./AgentsAndSkillsManagerView";
import { FormattedMarkdownContent } from "./FormattedMarkdownContent";
import { OrciaIcon } from "./icons";

export interface AgentStudioCardItemProps {
  readonly agent: UiManagedAgentItem;
  readonly skills: readonly UiManagedSkillItem[];
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly testInputValue: string;
  readonly onChangeTestInput: (agentId: string, nextValue: string) => void;
  readonly onToggleAgentSkill: (agentId: string, skillId: string, nextChecked: boolean) => void;
  readonly onExecuteAgent: (agentId: string, prompt: string) => void;
  readonly onDeleteAgent: (agentId: string) => void;
  readonly onUpdateAgentThinkingLevel?: (
    agentId: string,
    nextThinkingLevel: UiAgentThinkingLevel,
  ) => void;
  readonly onUpdateAgentVisibility?: (
    agentId: string,
    nextVisibility: UiAgentSkillVisibilityScope,
  ) => void;
  readonly onUseAgentInAssistant?: (agent: UiManagedAgentItem) => void;
}

export const AgentStudioCardItem: React.FC<AgentStudioCardItemProps> = ({
  agent,
  skills,
  labels,
  testInputValue,
  onChangeTestInput,
  onToggleAgentSkill,
  onExecuteAgent,
  onDeleteAgent,
  onUpdateAgentThinkingLevel,
  onUpdateAgentVisibility,
  onUseAgentInAssistant,
}) => {
  const [copiedHandle, setCopiedHandle] = useState(false);
  const [autosavedBadgeVisible, setAutosavedBadgeVisible] = useState(false);

  const visibilityScope: UiAgentSkillVisibilityScope = agent.visibilityScope ?? "TEAM";
  const visibilityBadgeContent =
    visibilityScope === "PRIVATE" ? (
      <>
        <OrciaIcon name="lock" /> Privé
      </>
    ) : visibilityScope === "PACK" ? (
      <>
        <OrciaIcon name="spaces" /> Pack Métier ({agent.sourcePackKey ?? "orcia-pack-sdlc"})
      </>
    ) : (
      <>
        <OrciaIcon name="team" /> Équipe
      </>
    );

  const triggerAutosavedFeedback = () => {
    setAutosavedBadgeVisible(true);
  };

  const handleCopyHandle = () => {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      void navigator.clipboard.writeText(agent.handle).catch(() => undefined);
    }
    setCopiedHandle(true);
  };

  const handleToggleVisibilityClick = () => {
    const nextScope: UiAgentSkillVisibilityScope =
      visibilityScope === "PRIVATE" ? "TEAM" : "PRIVATE";
    onUpdateAgentVisibility?.(agent.agentId, nextScope);
    triggerAutosavedFeedback();
  };

  const handleRunAgent = () => {
    const raw = testInputValue.trim();
    const prompt =
      raw ||
      `Bonjour ${agent.name}, présente ton rôle (${agent.roleMission}) et confirme que tu es prêt.`;
    if (!raw) {
      onChangeTestInput(agent.agentId, prompt);
    }
    onExecuteAgent(agent.agentId, prompt);
  };

  return (
    <div
      data-testid={`agent-card-${agent.agentId}`}
      className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3.5 text-xs"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <strong className="text-sm text-[var(--orcia-text-primary)]">{agent.name}</strong>
          <code
            data-testid={`agent-handle-${agent.agentId}`}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-1.5 py-0.5 font-mono text-[11px]"
          >
            {agent.handle}
          </code>
          <button
            type="button"
            data-testid={`copy-agent-handle-btn-${agent.agentId}`}
            onClick={handleCopyHandle}
            title="Copier l'identifiant @handle"
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-1.5 py-0.5 text-[10px] font-medium"
          >
            {copiedHandle ? (
              <>
                <OrciaIcon name="check" /> Copié
              </>
            ) : (
              "Copier @"
            )}
          </button>
          <button
            type="button"
            data-testid={`agent-visibility-badge-${agent.agentId}`}
            onClick={handleToggleVisibilityClick}
            title="Cliquer pour basculer la visibilité (Privé / Équipe)"
            className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-medium"
          >
            {visibilityBadgeContent}
          </button>
          {autosavedBadgeVisible && (
            <span
              data-testid={`agent-autosaved-badge-${agent.agentId}`}
              className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-semibold"
              style={{ color: "var(--color-status-success)" }}
            >
              <OrciaIcon name="check" /> Enregistré
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {onUseAgentInAssistant && (
            <button
              type="button"
              data-testid={`use-agent-in-assistant-btn-${agent.agentId}`}
              onClick={() => onUseAgentInAssistant(agent)}
              className="rounded bg-[var(--orcia-action-primary)] px-2.5 py-1 text-[11px] font-semibold text-[var(--orcia-text-on-action)]"
            >
              <OrciaIcon name="assistant" /> Utiliser dans Mon Assistant
            </button>
          )}
          <button
            type="button"
            data-testid={`delete-agent-btn-${agent.agentId}`}
            onClick={() => onDeleteAgent(agent.agentId)}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-1 text-[11px]"
          >
            {labels.deleteAgentButtonLabel}
          </button>
        </div>
      </div>

      <p className="text-[var(--orcia-text-secondary)]">{agent.roleMission}</p>

      <div className="flex flex-wrap items-center gap-3 pt-1">
        <label className="inline-flex items-center gap-1.5">
          <span className="font-medium text-[var(--orcia-text-secondary)]">
            {labels.agentThinkingLevelLabel} :
          </span>
          <select
            data-testid={`agent-card-thinking-select-${agent.agentId}`}
            value={agent.thinkingLevel}
            onChange={(e) => {
              const nextLvl = e.target.value as UiAgentThinkingLevel;
              onUpdateAgentThinkingLevel?.(agent.agentId, nextLvl);
              triggerAutosavedFeedback();
            }}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px]"
          >
            {(["simple", "medium", "complex", "auto"] as const).map((lvl) => (
              <option key={lvl} value={lvl}>
                {labels.thinkingLevels[lvl]}
              </option>
            ))}
          </select>
        </label>

        {skills.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-medium text-[var(--orcia-text-secondary)]">
              {labels.attachedSkillsLabel} :
            </span>
            {skills.map((sk) => {
              const attached = agent.skillIds.includes(sk.skillId);
              return (
                <label
                  key={sk.skillId}
                  className="inline-flex items-center gap-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5"
                >
                  <input
                    type="checkbox"
                    autoComplete="off"
                    data-lpignore="true"
                    data-1p-ignore="true"
                    data-bwignore="true"
                    data-form-type="other"
                    data-testid={`agent-attach-skill-${agent.agentId}-${sk.skillId}`}
                    checked={attached}
                    onChange={(e) => {
                      onToggleAgentSkill(agent.agentId, sk.skillId, e.target.checked);
                      triggerAutosavedFeedback();
                    }}
                  />
                  <span>
                    {sk.name} (<code className="font-mono text-[10px]">{sk.commandHandle}</code>)
                  </span>
                </label>
              );
            })}
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2 pt-1">
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid={`agent-test-input-${agent.agentId}`}
          value={testInputValue}
          onChange={(e) => onChangeTestInput(agent.agentId, e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleRunAgent();
            }
          }}
          placeholder={labels.testAgentInputPlaceholder}
          className="flex-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1"
        />
        <button
          type="button"
          data-testid={`run-agent-btn-${agent.agentId}`}
          onClick={handleRunAgent}
          className="rounded bg-[var(--orcia-action-primary)] px-3 py-1 font-semibold text-[var(--orcia-text-on-action)]"
        >
          <OrciaIcon name="lightning" /> {labels.runAgentButtonLabel}
        </button>
      </div>

      {agent.lastExecutionOutput && (
        <div
          data-testid={`agent-execution-output-${agent.agentId}`}
          className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2.5"
        >
          <FormattedMarkdownContent content={agent.lastExecutionOutput} />
        </div>
      )}
    </div>
  );
};
