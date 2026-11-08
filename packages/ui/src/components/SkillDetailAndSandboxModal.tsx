import React, { useEffect } from "react";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentSkillVisibilityScope,
  UiManagedSkillItem,
} from "./AgentsAndSkillsManagerView";
import { FormattedMarkdownContent } from "./FormattedMarkdownContent";

export interface SkillDetailAndSandboxModalProps {
  readonly skill: UiManagedSkillItem | null;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly testInputValue: string;
  readonly onChangeTestInput: (skillId: string, nextValue: string) => void;
  readonly onExecuteSkill: (skillId: string, inputText: string) => void;
  readonly onUpdateSkillVisibility?: (
    skillId: string,
    nextVisibility: UiAgentSkillVisibilityScope,
  ) => void;
  readonly onClose: () => void;
}

export const SkillDetailAndSandboxModal: React.FC<SkillDetailAndSandboxModalProps> = ({
  skill,
  labels,
  testInputValue,
  onChangeTestInput,
  onExecuteSkill,
  onUpdateSkillVisibility,
  onClose,
}) => {
  useEffect(() => {
    if (!skill) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [skill, onClose]);

  if (!skill) return null;

  const isPack = skill.visibilityScope === "PACK";
  const visibilityScope: UiAgentSkillVisibilityScope = skill.visibilityScope ?? "TEAM";

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
      role="dialog"
      aria-modal="true"
      aria-label={`Configuration & Bac à sable — ${skill.name}`}
      data-testid={`skill-detail-modal-${skill.skillId}`}
      className="fixed inset-0 z-40 flex items-center justify-center p-4"
      style={{ backgroundColor: "var(--color-modal-backdrop)" }}
    >
      <div className="w-[720px] max-h-[600px] flex flex-col rounded-xl border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] text-[var(--orcia-text-primary)] shadow-xl overflow-hidden text-xs">
        <header className="flex items-center justify-between border-b border-[var(--orcia-border-subtle)] px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold">🛠️ {skill.name}</h3>
            <code className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-1.5 py-0.5 font-mono text-[11px]">
              {skill.commandHandle}
            </code>
          </div>
          <button
            type="button"
            data-testid={`close-skill-detail-modal-btn-${skill.skillId}`}
            onClick={onClose}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1 text-xs font-medium"
          >
            Fermer (Échap)
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="space-y-2 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3">
            <p>
              <strong>{labels.skillObjectiveLabel} :</strong> {skill.objective}
            </p>
            <p>
              <strong>{labels.skillInstructionsLabel} :</strong> {skill.instructions}
            </p>
            <p>
              <strong>{labels.skillOutputFormatLabel} :</strong> {skill.expectedOutputFormat}
            </p>
            {skill.inputParameters.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                <span className="font-medium">{labels.skillParamsLabel} :</span>
                {skill.inputParameters.map((param) => (
                  <code
                    key={param}
                    className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 font-mono text-[11px]"
                  >
                    {param}
                  </code>
                ))}
              </div>
            )}
            {!isPack && (
              <div className="pt-2">
                <label className="inline-flex items-center gap-2">
                  <span className="font-medium">Visibilité :</span>
                  <select
                    data-testid={`edit-skill-visibility-select-${skill.skillId}`}
                    value={visibilityScope === "PRIVATE" ? "PRIVATE" : "TEAM"}
                    onChange={(e) =>
                      onUpdateSkillVisibility?.(
                        skill.skillId,
                        e.target.value as UiAgentSkillVisibilityScope,
                      )
                    }
                    className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-1"
                  >
                    <option value="TEAM">👥 Équipe / Espace</option>
                    <option value="PRIVATE">🔒 Privé</option>
                  </select>
                </label>
              </div>
            )}
          </div>

          <div className="space-y-2 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3">
            <h4 className="font-semibold">▷ Tester la Compétence / Dry-Run</h4>
            <div className="flex flex-wrap gap-2">
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
                className="flex-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
              />
              <button
                type="button"
                data-testid={`run-skill-btn-${skill.skillId}`}
                onClick={handleRunSkill}
                className="rounded bg-[var(--orcia-action-primary)] px-3 py-1.5 font-semibold text-[var(--orcia-text-on-action)]"
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
        </div>
      </div>
    </div>
  );
};
