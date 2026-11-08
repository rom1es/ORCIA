import React, { useEffect } from "react";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentSkillVisibilityScope,
} from "./AgentsAndSkillsManagerView";
import { DisabledButtonAlertIndicator } from "./DisabledButtonAlertIndicator";
import { getOrciaIconGlyph } from "./icons";

export interface SkillCreateFormDrawerProps {
  readonly isOpen: boolean;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly skillName: string;
  readonly skillObjective: string;
  readonly skillParamsRaw: string;
  readonly skillInstructions: string;
  readonly skillOutputFormat: string;
  readonly skillVisibility: "PRIVATE" | "TEAM";
  readonly onChangeName: (v: string) => void;
  readonly onChangeObjective: (v: string) => void;
  readonly onChangeParamsRaw: (v: string) => void;
  readonly onChangeInstructions: (v: string) => void;
  readonly onChangeOutputFormat: (v: string) => void;
  readonly onChangeVisibility: (v: "PRIVATE" | "TEAM") => void;
  readonly onSubmit: (e: React.FormEvent) => void;
  readonly onClose?: () => void;
}

export const SkillCreateFormDrawer: React.FC<SkillCreateFormDrawerProps> = ({
  isOpen,
  labels,
  skillName,
  skillObjective,
  skillParamsRaw,
  skillInstructions,
  skillOutputFormat,
  skillVisibility,
  onChangeName,
  onChangeObjective,
  onChangeParamsRaw,
  onChangeInstructions,
  onChangeOutputFormat,
  onChangeVisibility,
  onSubmit,
  onClose,
}) => {
  useEffect(() => {
    if (!isOpen || !onClose) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const isDisabled =
    !skillName.trim() || !skillObjective.trim() || !skillInstructions.trim();

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={labels.createSkillSectionTitle}
      data-testid="create-skill-modal"
      className="fixed inset-0 z-40 flex items-center justify-center p-4"
      style={{ backgroundColor: "var(--color-modal-backdrop)" }}
    >
      <div className="w-[680px] max-h-[600px] flex flex-col rounded-xl border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] text-[var(--orcia-text-primary)] shadow-xl overflow-hidden">
        <header className="flex items-center justify-between border-b border-[var(--orcia-border-subtle)] px-4 py-3">
          <h3 className="text-sm font-semibold">{labels.createSkillSectionTitle}</h3>
          <button
            type="button"
            data-testid="close-create-skill-modal-btn"
            onClick={onClose}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1 text-xs font-medium"
          >
            Annuler
          </button>
        </header>

        <form
          onSubmit={onSubmit}
          autoComplete="off"
          data-lpignore="true"
          data-form-type="other"
          data-testid="create-skill-form"
          className="grid grid-cols-1 gap-3 overflow-y-auto p-4 text-xs md:grid-cols-2"
        >
          <label className="flex flex-col gap-1">
            <span>{labels.skillNameLabel}</span>
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="skill-name-input"
              value={skillName}
              onChange={(e) => onChangeName(e.target.value)}
              placeholder={labels.skillNamePlaceholder}
              className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span>{labels.skillOutputFormatLabel}</span>
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="skill-output-format-input"
              value={skillOutputFormat}
              onChange={(e) => onChangeOutputFormat(e.target.value)}
              placeholder={labels.skillOutputFormatPlaceholder}
              className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5"
            />
          </label>
          <label className="flex flex-col gap-1 md:col-span-2">
            <span>Visibilité &amp; Partage</span>
            <select
              data-testid="skill-visibility-select"
              value={skillVisibility}
              onChange={(e) => onChangeVisibility(e.target.value as "PRIVATE" | "TEAM")}
              className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5"
            >
              <option value="TEAM">{getOrciaIconGlyph("team")} Partagé avec mon Équipe &amp; Espace</option>
              <option value="PRIVATE">{getOrciaIconGlyph("lock")} Privé (Visible uniquement par moi)</option>
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span>{labels.skillObjectiveLabel}</span>
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="skill-objective-input"
              value={skillObjective}
              onChange={(e) => onChangeObjective(e.target.value)}
              placeholder={labels.skillObjectivePlaceholder}
              className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span>{labels.skillParamsLabel}</span>
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="skill-params-input"
              value={skillParamsRaw}
              onChange={(e) => onChangeParamsRaw(e.target.value)}
              placeholder={labels.skillParamsPlaceholder}
              className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5"
            />
          </label>
          <label className="flex flex-col gap-1 md:col-span-2">
            <span>{labels.skillInstructionsLabel}</span>
            <textarea
              rows={2}
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="skill-instructions-input"
              value={skillInstructions}
              onChange={(e) => onChangeInstructions(e.target.value)}
              placeholder={labels.skillInstructionsPlaceholder}
              className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5"
            />
          </label>
          <div className="flex items-center justify-end gap-2 pt-2 md:col-span-2">
            <button
              type="submit"
              data-testid="create-skill-submit-btn"
              disabled={isDisabled}
              title={
                isDisabled
                  ? "Renseignez le nom, l'objectif et les instructions du skill pour activer sa création."
                  : undefined
              }
              className="inline-flex items-center gap-2 rounded bg-[var(--orcia-action-primary)] px-3 py-1.5 text-xs font-semibold text-[var(--orcia-text-on-action)] disabled:opacity-50"
            >
              <span>{labels.createSkillButtonLabel}</span>
              <DisabledButtonAlertIndicator
                disabled={isDisabled}
                reason="Renseignez le nom, l'objectif et les instructions du skill pour activer sa création."
                testIdSuffix="create-skill-submit-btn"
              />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export function matchesAgentQueryAndScope(
  agent: {
    readonly name: string;
    readonly handle: string;
    readonly roleMission: string;
    readonly visibilityScope?: UiAgentSkillVisibilityScope;
  },
  searchQuery: string,
  visibilityFilter: "ALL" | UiAgentSkillVisibilityScope,
): boolean {
  const scope = agent.visibilityScope ?? "TEAM";
  if (visibilityFilter !== "ALL" && scope !== visibilityFilter) return false;
  const q = searchQuery.trim().toLowerCase();
  if (!q) return true;
  return (
    agent.name.toLowerCase().includes(q) ||
    agent.handle.toLowerCase().includes(q) ||
    agent.roleMission.toLowerCase().includes(q)
  );
}

export function matchesSkillQueryAndScope(
  skill: {
    readonly name: string;
    readonly commandHandle: string;
    readonly objective: string;
    readonly visibilityScope?: UiAgentSkillVisibilityScope;
  },
  searchQuery: string,
  visibilityFilter: "ALL" | UiAgentSkillVisibilityScope,
): boolean {
  const scope = skill.visibilityScope ?? "TEAM";
  if (visibilityFilter !== "ALL" && scope !== visibilityFilter) return false;
  const q = searchQuery.trim().toLowerCase();
  if (!q) return true;
  return (
    skill.name.toLowerCase().includes(q) ||
    skill.commandHandle.toLowerCase().includes(q) ||
    skill.objective.toLowerCase().includes(q)
  );
}
