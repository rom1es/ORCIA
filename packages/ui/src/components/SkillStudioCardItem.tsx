import React, { useState } from "react";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentSkillVisibilityScope,
  UiManagedSkillItem,
} from "./AgentsAndSkillsManagerView";
import { FormattedMarkdownContent } from "./FormattedMarkdownContent";

export interface SkillStudioCardItemProps {
  readonly skill: UiManagedSkillItem;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly testInputValue?: string;
  readonly onChangeTestInput?: (skillId: string, nextValue: string) => void;
  readonly onExecuteSkill?: (skillId: string, inputText: string) => void;
  readonly onDeleteSkill: (skillId: string) => void;
  readonly onOpenDetailModal?: (skill: UiManagedSkillItem) => void;
  readonly onUpdateSkillVisibility?: (
    skillId: string,
    nextVisibility: UiAgentSkillVisibilityScope,
  ) => void;
  readonly onUseSkillInAssistant?: (skill: UiManagedSkillItem) => void;
}

export const SkillStudioCardItem: React.FC<SkillStudioCardItemProps> = ({
  skill,
  labels,
  onDeleteSkill,
  onOpenDetailModal,
  onUpdateSkillVisibility,
  onUseSkillInAssistant,
}) => {
  const [copiedCommand, setCopiedCommand] = useState(false);
  const [autosavedBadgeVisible, setAutosavedBadgeVisible] = useState(false);

  const visibilityScope: UiAgentSkillVisibilityScope = skill.visibilityScope ?? "TEAM";
  const isPack = visibilityScope === "PACK";
  const visibilityBadgeText =
    visibilityScope === "PRIVATE"
      ? "🔒 Privé"
      : visibilityScope === "PACK"
        ? `📦 Pack Métier (${skill.sourcePackKey ?? "orcia-pack-sdlc"})`
        : "👥 Équipe";

  const handleCopyCommand = () => {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      void navigator.clipboard.writeText(skill.commandHandle).catch(() => undefined);
    }
    setCopiedCommand(true);
  };

  const handleToggleVisibilityClick = () => {
    if (isPack) return;
    const nextScope: UiAgentSkillVisibilityScope =
      visibilityScope === "PRIVATE" ? "TEAM" : "PRIVATE";
    onUpdateSkillVisibility?.(skill.skillId, nextScope);
    setAutosavedBadgeVisible(true);
  };

  return (
    <div
      data-testid={`skill-card-${skill.skillId}`}
      className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3.5 text-xs"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <strong className="text-sm text-[var(--orcia-text-primary)]">{skill.name}</strong>
          <code
            data-testid={`skill-command-handle-${skill.skillId}`}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-1.5 py-0.5 font-mono text-[11px]"
          >
            {skill.commandHandle}
          </code>
          <button
            type="button"
            data-testid={`copy-skill-handle-btn-${skill.skillId}`}
            onClick={handleCopyCommand}
            title="Copier la commande /skill"
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-1.5 py-0.5 text-[10px] font-medium"
          >
            {copiedCommand ? "✓ Copié" : "Copier /"}
          </button>
          {isPack ? (
            <span
              data-testid={`skill-visibility-badge-${skill.skillId}`}
              className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-medium"
            >
              {visibilityBadgeText}
            </span>
          ) : (
            <button
              type="button"
              data-testid={`skill-visibility-badge-${skill.skillId}`}
              onClick={handleToggleVisibilityClick}
              title="Cliquer pour basculer la visibilité (Privé / Équipe)"
              className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-medium"
            >
              {visibilityBadgeText}
            </button>
          )}
          {autosavedBadgeVisible && (
            <span
              data-testid={`skill-autosaved-badge-${skill.skillId}`}
              className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-semibold"
              style={{ color: "var(--color-status-success)" }}
            >
              ✓ Enregistré
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {onUseSkillInAssistant && (
            <button
              type="button"
              data-testid={`use-skill-in-assistant-btn-${skill.skillId}`}
              onClick={() => onUseSkillInAssistant(skill)}
              className="rounded bg-[var(--orcia-action-primary)] px-2.5 py-1 text-[11px] font-semibold text-[var(--orcia-text-on-action)]"
            >
              💬 Utiliser dans Mon Assistant
            </button>
          )}
          <button
            type="button"
            data-testid={`open-skill-detail-modal-btn-${skill.skillId}`}
            onClick={() => onOpenDetailModal?.(skill)}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1 text-[11px] font-semibold"
          >
            ⚙️ Configurer &amp; Tester
          </button>
          {!isPack && (
            <button
              type="button"
              data-testid={`delete-skill-btn-${skill.skillId}`}
              onClick={() => onDeleteSkill(skill.skillId)}
              className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-1 text-[11px]"
            >
              {labels.deleteSkillButtonLabel}
            </button>
          )}
        </div>
      </div>

      <p className="text-[var(--orcia-text-secondary)]">{skill.objective}</p>

      {skill.inputParameters.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] font-medium text-[var(--orcia-text-secondary)]">
            Paramètres :
          </span>
          {skill.inputParameters.map((param) => (
            <code
              key={param}
              className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 font-mono text-[10px]"
            >
              {param}
            </code>
          ))}
        </div>
      )}

      {skill.lastExecutionOutput && (
        <div
          data-testid={`skill-execution-output-${skill.skillId}`}
          className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2.5"
        >
          <FormattedMarkdownContent content={skill.lastExecutionOutput} />
        </div>
      )}
    </div>
  );
};
