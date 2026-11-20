import React, { useEffect, useState } from "react";
import { OrciaDialog } from "../primitives/RadixDesignSystemPrimitives";
import type {
  AgentSixBlocksDraftState,
  AgentStudioBlockKey,
} from "./AgentGovernanceTypesAndDefaults";
import {
  computeAgentReadinessChecklist,
  createDefaultAgentSixBlocksDraft,
} from "./AgentGovernanceTypesAndDefaults";
import { AgentIdentityAndSkillsFields } from "./AgentIdentityAndSkillsFields";
import { AgentSixBlocksEditorBody } from "./AgentSixBlocksFormSections";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
  UiManagedSkillItem,
} from "./AgentsAndSkillsTypes";
import {
  AgentDetailModalHeader,
  AgentTestBenchSection,
} from "./AgentTestBenchSection";
import { OrciaIcon } from "./icons";

export interface AgentDetailAndSandboxModalProps {
  readonly agent: UiManagedAgentItem | null;
  readonly skills: readonly UiManagedSkillItem[];
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly testInputValue: string;
  readonly onChangeTestInput: (agentId: string, nextValue: string) => void;
  readonly onToggleAgentSkill: (agentId: string, skillId: string, nextChecked: boolean) => void;
  readonly onExecuteAgent: (agentId: string, prompt: string) => void;
  readonly onUpdateAgentThinkingLevel?: (
    agentId: string,
    nextThinkingLevel: UiAgentThinkingLevel,
  ) => void;
  readonly onUpdateAgentVisibility?: (
    agentId: string,
    nextVisibility: UiAgentSkillVisibilityScope,
  ) => void;
  readonly onToggleAgentMcpExposure?: (agentId: string, nextExposed: boolean) => void;
  readonly onUpdateAgentDetails?: (
    agentId: string,
    patch: Partial<AgentSixBlocksDraftState> & {
      name: string;
      roleMission: string;
      instructions: string;
      thinkingLevel: UiAgentThinkingLevel;
      visibilityScope?: UiAgentSkillVisibilityScope;
      mcpExposed?: boolean;
    },
  ) => void;
  readonly sandboxTraceSlot?: React.ReactNode;
  readonly onClose: () => void;
}

export const AgentDetailAndSandboxModal: React.FC<AgentDetailAndSandboxModalProps> = ({
  agent,
  skills,
  labels,
  testInputValue,
  onChangeTestInput,
  onToggleAgentSkill,
  onExecuteAgent,
  onUpdateAgentThinkingLevel,
  onUpdateAgentVisibility,
  onToggleAgentMcpExposure,
  onUpdateAgentDetails,
  sandboxTraceSlot = null,
  onClose,
}) => {
  const [draft, setDraft] = useState<AgentSixBlocksDraftState>(() =>
    createDefaultAgentSixBlocksDraft(agent),
  );
  const [activeBlock, setActiveBlock] = useState<AgentStudioBlockKey>("A");
  const [showAllBlocks, setShowAllBlocks] = useState<boolean>(true);
  const [savedFeedback, setSavedFeedback] = useState<boolean>(false);

  useEffect(() => {
    if (agent) {
      setDraft(createDefaultAgentSixBlocksDraft(agent));
      setSavedFeedback(false);
    }
  }, [agent]);

  if (!agent) return null;

  const isPack = agent.visibilityScope === "PACK";
  const visibilityScope: UiAgentSkillVisibilityScope = draft.visibilityScope ?? "TEAM";
  const readiness = computeAgentReadinessChecklist(draft);

  const applyDraftPatch = (patch: Partial<AgentSixBlocksDraftState>) => {
    const next: AgentSixBlocksDraftState = { ...draft, ...patch };
    setDraft(next);
    setSavedFeedback(true);
    if (patch.thinkingLevel) onUpdateAgentThinkingLevel?.(agent.agentId, patch.thinkingLevel);
    if (patch.visibilityScope) onUpdateAgentVisibility?.(agent.agentId, patch.visibilityScope);
    onUpdateAgentDetails?.(agent.agentId, {
      ...next,
      name: next.name.trim() || agent.name,
      roleMission: next.roleMission.trim() || agent.roleMission,
      instructions: next.instructions.trim() || agent.instructions,
      thinkingLevel: next.thinkingLevel,
      visibilityScope: next.visibilityScope,
      mcpExposed: next.mcpExposed,
    });
  };

  const handleRunAgent = () => {
    const raw = testInputValue.trim();
    const prompt =
      raw ||
      `Bonjour ${agent.name}, présente ton rôle (${agent.roleMission}) et confirme que tu es prêt.`;
    if (!raw) onChangeTestInput(agent.agentId, prompt);
    setDraft((prev) => ({ ...prev, testBenchValidated: true }));
    onExecuteAgent(agent.agentId, prompt);
  };

  return (
    <OrciaDialog
      open={true}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) onClose();
      }}
      title={agent.name}
      testId={`agent-detail-modal-${agent.agentId}`}
      closeLabel="Fermer (Échap)"
      closeButtonTestId={`close-agent-detail-modal-btn-${agent.agentId}`}
      contentClassName="orcia-ds-dialog-content-wide w-[960px] max-w-[96vw] max-h-[82vh] text-xs"
      headerExtra={
        <AgentDetailModalHeader
          agent={agent}
          testBenchValidated={draft.testBenchValidated}
          savedFeedback={savedFeedback}
          onToggleMcpExposure={(checked) => {
            onToggleAgentMcpExposure?.(agent.agentId, checked);
            setSavedFeedback(true);
          }}
        />
      }
    >
      <div className="orcia-ds-dialog-body pt-3 space-y-4">
        <AgentIdentityAndSkillsFields
          agent={agent}
          draft={draft}
          skills={skills}
          labels={labels}
          isPack={isPack}
          visibilityScope={visibilityScope}
          onChangeDraft={applyDraftPatch}
          onToggleAgentSkill={(agentId, skillId, checked) => {
            onToggleAgentSkill(agentId, skillId, checked);
            setSavedFeedback(true);
          }}
        />

        <AgentSixBlocksEditorBody
          draft={draft}
          labels={labels}
          skills={skills}
          activeBlock={activeBlock}
          showAllBlocks={showAllBlocks}
          readOnlyIdentity={isPack}
          testIdPrefix={`detail-${agent.agentId}`}
          onSelectBlock={(blk) => {
            setActiveBlock(blk);
            setShowAllBlocks(false);
          }}
          onToggleShowAllBlocks={() => setShowAllBlocks((p) => !p)}
          onChangeDraft={applyDraftPatch}
          onToggleSkillId={(skillId, checked) => {
            onToggleAgentSkill(agent.agentId, skillId, checked);
            setSavedFeedback(true);
          }}
        />

        <AgentTestBenchSection
          agent={agent}
          labels={labels}
          satisfiedConditionsCount={readiness.filter((r) => r.satisfied).length}
          testInputValue={testInputValue}
          onChangeTestInput={onChangeTestInput}
          onRunAgent={handleRunAgent}
          sandboxTraceSlot={sandboxTraceSlot}
        />
      </div>

      <div className="orcia-ds-dialog-footer justify-between">
        <span className="text-[11px] text-[var(--orcia-text-secondary)]">
          {savedFeedback ? "Modifications enregistrées" : "Sauvegarde automatique active"}
        </span>
        <button
          type="button"
          data-testid={`save-agent-detail-modal-btn-${agent.agentId}`}
          onClick={() => applyDraftPatch({})}
          className="orcia-ds-btn orcia-ds-btn-primary text-xs"
        >
          <OrciaIcon name="check" /> Enregistrer
        </button>
      </div>
    </OrciaDialog>
  );
};
