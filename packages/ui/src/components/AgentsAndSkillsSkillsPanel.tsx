import React, { useState } from "react";
import type {
  AgentsAndSkillsManagerLabels,
  CreateSkillInput,
  UiAgentSkillVisibilityScope,
  UiManagedSkillItem,
} from "./AgentsAndSkillsTypes";
import { SkillCreateFormDrawer } from "./SkillCreateFormDrawer";
import { SkillDetailAndSandboxModal } from "./SkillDetailAndSandboxModal";
import { SkillStudioCardItem } from "./SkillStudioCardItem";

export interface AgentsAndSkillsSkillsPanelProps {
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly filteredSkills: readonly UiManagedSkillItem[];
  readonly isCreateSkillOpen: boolean;
  readonly activeDetailSkill: UiManagedSkillItem | null;
  readonly onCloseCreateSkill: () => void;
  readonly onOpenDetailModal: (item: UiManagedSkillItem) => void;
  readonly onCloseDetailModal: () => void;
  readonly onCreateSkill: (input: CreateSkillInput) => void;
  readonly onExecuteSkill: (skillId: string, testInput: string) => void;
  readonly onDeleteSkill: (skillId: string) => void;
  readonly onUpdateSkillVisibility?: (
    skillId: string,
    visibilityScope: UiAgentSkillVisibilityScope,
  ) => void;
  readonly onUseSkillInAssistant?: (skill: UiManagedSkillItem) => void;
}

export const AgentsAndSkillsSkillsPanel: React.FC<
  AgentsAndSkillsSkillsPanelProps
> = ({
  labels,
  filteredSkills,
  isCreateSkillOpen,
  activeDetailSkill,
  onCloseCreateSkill,
  onOpenDetailModal,
  onCloseDetailModal,
  onCreateSkill,
  onExecuteSkill,
  onDeleteSkill,
  onUpdateSkillVisibility,
  onUseSkillInAssistant,
}) => {
  const [skillName, setSkillName] = useState("");
  const [skillObjective, setSkillObjective] = useState("");
  const [skillParamsRaw, setSkillParamsRaw] = useState("");
  const [skillInstructions, setSkillInstructions] = useState("");
  const [skillOutputFormat, setSkillOutputFormat] = useState("");
  const [skillVisibility, setSkillVisibility] = useState<"PRIVATE" | "TEAM">(
    "TEAM",
  );
  const [skillTestInputs, setSkillTestInputs] = useState<Record<string, string>>(
    {},
  );

  const handleSubmitSkill = (e: React.FormEvent) => {
    e.preventDefault();
    if (!skillName.trim() || !skillObjective.trim() || !skillInstructions.trim()) {
      return;
    }
    const parsedParams = skillParamsRaw
      .split(",")
      .map((p) => p.trim())
      .filter(Boolean);
    onCreateSkill({
      name: skillName.trim(),
      objective: skillObjective.trim(),
      inputParameters: parsedParams,
      instructions: skillInstructions.trim(),
      expectedOutputFormat:
        skillOutputFormat.trim() || labels.studio.defaultSkillOutputFormat,
      visibilityScope: skillVisibility,
    });
    setSkillName("");
    setSkillObjective("");
    setSkillParamsRaw("");
    setSkillInstructions("");
    setSkillOutputFormat("");
    onCloseCreateSkill();
  };

  return (
    <div data-testid="skills-subview-panel" className="space-y-4">
      <div
        data-testid="skills-usage-guidance-banner"
        className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-2.5 text-xs text-[var(--orcia-text-secondary)]"
      >
        {labels.skillUsageBanner}
      </div>
      <SkillCreateFormDrawer
        isOpen={isCreateSkillOpen}
        labels={labels}
        skillName={skillName}
        skillObjective={skillObjective}
        skillParamsRaw={skillParamsRaw}
        skillInstructions={skillInstructions}
        skillOutputFormat={skillOutputFormat}
        skillVisibility={skillVisibility}
        onChangeName={setSkillName}
        onChangeObjective={setSkillObjective}
        onChangeParamsRaw={setSkillParamsRaw}
        onChangeInstructions={setSkillInstructions}
        onChangeOutputFormat={setSkillOutputFormat}
        onChangeVisibility={setSkillVisibility}
        onSubmit={handleSubmitSkill}
        onClose={onCloseCreateSkill}
      />
      {filteredSkills.length === 0 ? (
        <div
          data-testid="skills-empty-state"
          className="orcia-bento-card orcia-ds-data-card border-dashed p-4 text-center text-xs text-[var(--orcia-text-secondary)]"
        >
          <strong className="block text-[var(--orcia-text-primary)]">
            {labels.emptySkillsTitle}
          </strong>
          <span>{labels.emptySkillsDescription}</span>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredSkills.map((sk) => (
            <SkillStudioCardItem
              key={sk.skillId}
              skill={sk}
              labels={labels}
              onDeleteSkill={onDeleteSkill}
              onOpenDetailModal={onOpenDetailModal}
              onUpdateSkillVisibility={onUpdateSkillVisibility}
              onUseSkillInAssistant={onUseSkillInAssistant}
            />
          ))}
        </div>
      )}
      <SkillDetailAndSandboxModal
        skill={activeDetailSkill}
        labels={labels}
        testInputValue={
          activeDetailSkill ? (skillTestInputs[activeDetailSkill.skillId] ?? "") : ""
        }
        onChangeTestInput={(skillId, val) =>
          setSkillTestInputs((p) => ({ ...p, [skillId]: val }))
        }
        onExecuteSkill={onExecuteSkill}
        onUpdateSkillVisibility={onUpdateSkillVisibility}
        onClose={onCloseDetailModal}
      />
    </div>
  );
};
