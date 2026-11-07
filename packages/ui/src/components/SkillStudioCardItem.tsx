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
  readonly testInputValue: string;
  readonly onChangeTestInput: (skillId: string, nextValue: string) => void;
  readonly onExecuteSkill: (skillId: string, inputText: string) => void;
  readonly onDeleteSkill: (skillId: string) => void;
  readonly onUpdateSkillVisibility?: (
    skillId: string,
    nextVisibility: UiAgentSkillVisibilityScope,
  ) => void;
  readonly onUseSkillInAssistant?: (skill: UiManagedSkillItem) => void;
}

export const SkillStudioCardItem: React.FC<SkillStudioCardItemProps> = ({
  skill,
  labels,
  testInputValue,
  onChangeTestInput,
  onExecuteSkill,
  onDeleteSkill,
  onUpdateSkillVisibility,
  onUseSkillInAssistant,
}) => {
  const [copiedCommand, setCopiedCommand] = useState(false);
  const [autosavedBadgeVisible, setAutosavedBadgeVisible] = useState(false);

  const visibilityScope: UiAgentSkillVisibilityScope = skill.visibilityScope ?? "TEAM";
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
    const nextScope: UiAgentSkillVisibilityScope =
      visibilityScope === "PRIVATE" ? "TEAM" : "PRIVATE";
    onUpdateSkillVisibility?.(skill.skillId, nextScope);
    setAutosavedBadgeVisible(true);
  };

  const handleRunSkill = () => {
    const raw = testInputValue.trim();
    const txt = raw || `Exécute la compétence ${skill.name} sur un cas d'exemple concret.`;
    if (!raw) {
      onChangeTestInput(skill.skillId, txt);
    }
    onExecuteSkill(skill.skillId, txt);
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
          <button
            type="button"
            data-testid={`skill-visibility-badge-${skill.skillId}`}
            onClick={handleToggleVisibilityClick}
            title="Cliquer pour basculer la visibilité (Privé / Équipe)"
            className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-medium"
          >
            {visibilityBadgeText}
          </button>
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
            data-testid={`delete-skill-btn-${skill.skillId}`}
            onClick={() => onDeleteSkill(skill.skillId)}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-1 text-[11px]"
          >
            {labels.deleteSkillButtonLabel}
          </button>
        </div>
      </div>

      <p className="text-[var(--orcia-text-secondary)]">{skill.objective}</p>

      <div className="flex flex-wrap gap-2 pt-1">
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid={`skill-test-input-${skill.skillId}`}
          value={testInputValue}
          onChange={(e) => onChangeTestInput(skill.skillId, e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleRunSkill();
            }
          }}
          placeholder={labels.testSkillInputPlaceholder}
          className="flex-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1"
        />
        <button
          type="button"
          data-testid={`run-skill-btn-${skill.skillId}`}
          onClick={handleRunSkill}
          className="rounded bg-[var(--orcia-action-primary)] px-3 py-1 font-semibold text-[var(--orcia-text-on-action)]"
        >
          ⚡ {labels.runSkillButtonLabel}
        </button>
      </div>

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
