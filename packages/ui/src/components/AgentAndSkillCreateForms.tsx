import React, { useEffect, useState } from "react";
import type {
  AgentSixBlocksDraftState,
  AgentStudioBlockKey,
} from "./AgentGovernanceTypesAndDefaults";
import { computeAgentReadinessChecklist } from "./AgentGovernanceTypesAndDefaults";
import { AgentSixBlocksEditorBody } from "./AgentSixBlocksFormSections";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentThinkingLevel,
  UiManagedSkillItem,
} from "./AgentsAndSkillsTypes";
import { AgentsAndSkillsHeaderAndToolbar } from "./AgentsAndSkillsHeaderAndToolbar";
import { DisabledButtonAlertIndicator } from "./DisabledButtonAlertIndicator";
import { OrciaIcon } from "./icons";

export { AgentsAndSkillsHeaderAndToolbar };

export interface AgentCreateFormDrawerProps {
  readonly isOpen: boolean;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly skills: readonly UiManagedSkillItem[];
  readonly draft: AgentSixBlocksDraftState;
  readonly onChangeDraft: (patch: Partial<AgentSixBlocksDraftState>) => void;
  readonly onToggleSkillId: (skillId: string, checked: boolean) => void;
  readonly onSubmit: (e: React.FormEvent) => void;
  readonly onClose?: () => void;
  readonly agentName?: string;
  readonly agentRole?: string;
  readonly agentInstructions?: string;
  readonly agentThinking?: UiAgentThinkingLevel;
  readonly agentVisibility?: "PRIVATE" | "TEAM";
  readonly selectedSkillIds?: readonly string[];
  readonly onChangeName?: (v: string) => void;
  readonly onChangeRole?: (v: string) => void;
  readonly onChangeInstructions?: (v: string) => void;
  readonly onChangeThinking?: (v: UiAgentThinkingLevel) => void;
  readonly onChangeVisibility?: (v: "PRIVATE" | "TEAM") => void;
}

export const AgentCreateFormDrawer: React.FC<AgentCreateFormDrawerProps> = ({
  isOpen,
  labels,
  skills,
  draft,
  onChangeDraft,
  onToggleSkillId,
  onSubmit,
  onClose,
}) => {
  const [activeBlock, setActiveBlock] = useState<AgentStudioBlockKey>("A");
  const [showAllBlocks, setShowAllBlocks] = useState<boolean>(true);
  const studio = labels.studio;

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
    !draft.name.trim() ||
    !draft.roleMission.trim() ||
    (!draft.instructions.trim() && !draft.promptRef.trim());
  const disabledReason = studio.createAgentDisabledReason;
  const readiness = computeAgentReadinessChecklist(draft, studio);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={labels.createAgentSectionTitle}
      data-testid="create-agent-modal"
      className="fixed inset-0 z-40 flex items-center justify-center p-4"
      style={{ backgroundColor: "var(--color-modal-backdrop)" }}
    >
      <div
        className="w-[960px] max-h-[680px] flex flex-col rounded-xl border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] text-[var(--orcia-text-primary)] shadow-xl overflow-hidden"
        style={{
          backgroundColor: "var(--color-surface-card)",
          borderColor: "var(--color-border)",
          color: "var(--color-foreground)",
        }}
      >
        <header className="flex items-center justify-between border-b border-[var(--orcia-border-subtle)] px-4 py-3">
          <div>
            <h3 className="text-sm font-semibold">{labels.createAgentSectionTitle}</h3>
            <p className="text-[11px] text-[var(--orcia-text-secondary)]">
              {studio.createAgentSubtitle}
            </p>
          </div>
        </header>

        <form
          onSubmit={onSubmit}
          autoComplete="off"
          data-lpignore="true"
          data-form-type="other"
          data-testid="create-agent-form"
          className="flex flex-1 flex-col overflow-hidden"
        >
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            <AgentSixBlocksEditorBody
              draft={draft}
              labels={labels}
              skills={skills}
              activeBlock={activeBlock}
              showAllBlocks={showAllBlocks}
              testIdPrefix="create"
              onSelectBlock={(blk) => {
                setActiveBlock(blk);
                setShowAllBlocks(false);
              }}
              onToggleShowAllBlocks={() => setShowAllBlocks((p) => !p)}
              onChangeDraft={onChangeDraft}
              onToggleSkillId={onToggleSkillId}
            />

            <div
              data-testid="create-agent-readiness-checklist"
              className="rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3 text-xs"
            >
              <strong className="block mb-1.5 font-semibold">
                {studio.readinessChecklistTitle}
              </strong>
              <div className="grid grid-cols-1 gap-1.5 md:grid-cols-3">
                {readiness.map((item) => (
                  <div
                    key={item.code}
                    data-testid={`readiness-condition-${item.index}`}
                    className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
                  >
                    <div className="inline-flex items-center gap-1 font-semibold">
                      <OrciaIcon
                        name={item.satisfied ? "check" : "hourglass"}
                        size={12}
                      />
                      <span>
                        {item.index}. {item.label}
                      </span>
                    </div>
                    <div className="text-[11px] text-[var(--orcia-text-secondary)]">
                      {item.detail}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <footer className="flex items-center justify-between border-t border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-4 py-3">
            <span className="text-[11px] text-[var(--orcia-text-secondary)]">
              {studio.escapeCancelHint}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                data-testid="close-create-agent-modal-btn"
                onClick={onClose}
                className="orcia-ds-btn orcia-ds-btn-secondary text-xs"
              >
                {studio.cancelButton}
              </button>
              <button
                type="submit"
                data-testid="create-agent-submit-btn"
                disabled={isDisabled}
                title={isDisabled ? disabledReason : undefined}
                className="orcia-ds-btn orcia-ds-btn-primary text-xs"
              >
                <span>{labels.createAgentButtonLabel}</span>
                <DisabledButtonAlertIndicator
                  disabled={isDisabled}
                  reason={disabledReason}
                  testIdSuffix="create-agent-submit-btn"
                />
              </button>
            </div>
          </footer>
        </form>
      </div>
    </div>
  );
};
