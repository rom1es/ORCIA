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
  readonly testInputValue?: string;
  readonly onChangeTestInput?: (agentId: string, nextValue: string) => void;
  readonly onToggleAgentSkill?: (agentId: string, skillId: string, nextChecked: boolean) => void;
  readonly onExecuteAgent?: (agentId: string, prompt: string) => void;
  readonly onDeleteAgent: (agentId: string) => void;
  readonly onDuplicateAgent?: (agent: UiManagedAgentItem) => void;
  readonly onToggleAgentEnabled?: (agentId: string, nextEnabled: boolean) => void;
  readonly onOpenDetailModal?: (agent: UiManagedAgentItem) => void;
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

  const visibilityScope: UiAgentSkillVisibilityScope = agent.visibilityScope ?? "TEAM";
  const isPack = visibilityScope === "PACK";
  const isEnabled = agent.enabledOnWorkspace !== false;
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

  const attachedSkills = skills.filter((sk) => agent.skillIds.includes(sk.skillId));

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
    if (isPack) return;
    const nextScope: UiAgentSkillVisibilityScope =
      visibilityScope === "PRIVATE" ? "TEAM" : "PRIVATE";
    onUpdateAgentVisibility?.(agent.agentId, nextScope);
    triggerAutosavedFeedback();
  };

  return (
    <div
      data-testid={`agent-card-${agent.agentId}`}
      className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3.5 text-xs"
    >
      {/* Row 1: Identity & Governance Badges */}
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

          {isPack ? (
            <span
              data-testid={`agent-visibility-badge-${agent.agentId}`}
              className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-medium"
            >
              {visibilityBadgeContent}
            </span>
          ) : (
            <button
              type="button"
              data-testid={`agent-visibility-badge-${agent.agentId}`}
              onClick={handleToggleVisibilityClick}
              title="Cliquer pour basculer la visibilité (Privé / Équipe)"
              className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-medium"
            >
              {visibilityBadgeContent}
            </button>
          )}

          {!isEnabled && (
            <span
              data-testid={`agent-disabled-badge-${agent.agentId}`}
              className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-medium text-[var(--orcia-text-secondary)]"
            >
              ⏸️ Désactivé sur cet espace
            </span>
          )}

          {agent.mcpExposed && (
            <span
              data-testid={`agent-mcp-active-badge-${agent.agentId}`}
              className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-semibold"
            >
              <OrciaIcon name="plug" /> MCP Actif
            </span>
          )}

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
      </div>

      {/* Row 2: Mission & Attached Skills Pills */}
      <div className="space-y-1.5">
        <p className="text-[var(--orcia-text-secondary)]">{agent.roleMission}</p>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-medium text-[var(--orcia-text-secondary)]">
            {labels.attachedSkillsLabel} :
          </span>
          {attachedSkills.length === 0 ? (
            <span className="text-[11px] text-[var(--orcia-text-secondary)]">
              Aucune compétence rattachée
            </span>
          ) : (
            attachedSkills.map((sk) => (
              <span
                key={sk.skillId}
                className="inline-flex items-center gap-1 rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px]"
              >
                <OrciaIcon name="tools" /> {sk.name} (<code className="font-mono text-[10px]">{sk.commandHandle}</code>)
              </span>
            ))
          )}
          <button
            type="button"
            onClick={() => onOpenDetailModal?.(agent)}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-medium"
          >
            + Rattacher / Gérer
          </button>
        </div>
      </div>

      {/* Row 3: Clear Actions by Origin */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
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
            data-testid={`open-agent-detail-modal-btn-${agent.agentId}`}
            onClick={() => onOpenDetailModal?.(agent)}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1 text-[11px] font-semibold"
          >
            <OrciaIcon name="configuration" /> Configurer &amp; Tester
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {isPack ? (
            <>
              <button
                type="button"
                data-testid={`duplicate-agent-btn-${agent.agentId}`}
                onClick={() => onDuplicateAgent?.(agent)}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1 text-[11px] font-medium"
              >
                <OrciaIcon name="copy" /> Dupliquer &amp; Personnaliser
              </button>
              <button
                type="button"
                data-testid={`toggle-agent-enabled-btn-${agent.agentId}`}
                onClick={() => onToggleAgentEnabled?.(agent.agentId, !isEnabled)}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1 text-[11px] font-medium"
              >
                {isEnabled ? "⏸️ Désactiver sur l'espace" : "▶️ Activer sur l'espace"}
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                data-testid={`duplicate-agent-btn-${agent.agentId}`}
                onClick={() => onDuplicateAgent?.(agent)}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-1 text-[11px] font-medium"
              >
                <OrciaIcon name="copy" /> Dupliquer
              </button>
              <button
                type="button"
                data-testid={`delete-agent-btn-${agent.agentId}`}
                onClick={() => onDeleteAgent(agent.agentId)}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-1 text-[11px]"
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
          <FormattedMarkdownContent content={agent.lastExecutionOutput} />
        </div>
      )}
    </div>
  );
};
