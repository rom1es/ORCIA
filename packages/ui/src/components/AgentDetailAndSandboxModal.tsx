import React from "react";
import { OrciaAlertBanner } from "../primitives/OrciaAlertBanner";
import { OrciaDialog } from "../primitives/RadixDesignSystemPrimitives";
import {
  computeAgentReadinessChecklist,
  resolveAgentLifecycleAndBenchStatus,
  type AgentSixBlocksDraftState,
} from "./AgentGovernanceTypesAndDefaults";
import { AgentSixBlocksEditorBody } from "./AgentSixBlocksFormSections";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentLifecycleStatus,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
  UiManagedSkillItem,
} from "./AgentsAndSkillsTypes";
import {
  AgentDetailModalHeader,
  AgentTestBenchSection,
} from "./AgentTestBenchSection";
import {
  RgaaDialogFooterActions,
  RgaaUnsavedChangesAlert,
  type RgaaModalGuardLabels,
} from "./RgaaModalDialog";
import { useAgentDetailModalState } from "./useAgentDetailModalState";

export interface AgentDetailAndSandboxModalProps {
  readonly agent: UiManagedAgentItem | null;
  readonly skills: readonly UiManagedSkillItem[];
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly testInputValue: string;
  readonly modalError?: string | null;
  readonly onClearModalError?: () => void;
  readonly onChangeTestInput: (agentId: string, nextValue: string) => void;
  readonly onToggleAgentSkill: (
    agentId: string,
    skillId: string,
    nextChecked: boolean,
  ) => Promise<boolean> | boolean | void;
  readonly onExecuteAgent: (agentId: string, prompt: string) => Promise<boolean> | boolean | void;
  readonly onToggleAgentMcpExposure?: (
    agentId: string,
    nextExposed: boolean,
  ) => Promise<boolean> | boolean | void;
  readonly onUpdateAgentLifecycle?: (
    agentId: string,
    nextLifecycle: UiAgentLifecycleStatus,
  ) => Promise<boolean> | boolean | void;
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
  ) => Promise<boolean> | boolean | void;
  readonly sandboxTraceSlot?: React.ReactNode;
  readonly onClose: () => void;
}

export const AgentDetailAndSandboxModal: React.FC<
  AgentDetailAndSandboxModalProps
> = ({
  agent,
  skills,
  labels,
  testInputValue,
  modalError = null,
  onClearModalError,
  onChangeTestInput,
  onToggleAgentSkill,
  onExecuteAgent,
  onToggleAgentMcpExposure,
  onUpdateAgentLifecycle,
  onUpdateAgentDetails,
  sandboxTraceSlot = null,
  onClose,
}) => {
  const state = useAgentDetailModalState({
    agent,
    labels,
    modalError,
    testInputValue,
    onChangeTestInput,
    onToggleAgentSkill,
    onExecuteAgent,
    onToggleAgentMcpExposure,
    onUpdateAgentLifecycle,
    onUpdateAgentDetails,
    onClearModalError,
    onClose,
  });

  if (!agent) return null;

  const studio = labels.studio;
  const isPack = agent.visibilityScope === "PACK";
  const { lifecycleStatus, testBenchStatus } = resolveAgentLifecycleAndBenchStatus(agent);
  const readiness = computeAgentReadinessChecklist(state.draft, studio);
  const guardLabels: RgaaModalGuardLabels = {
    unsavedAlertTitle: studio.unsavedAlertTitle,
    unsavedAlertMessage: studio.unsavedAlertMessage,
    unsavedStayCta: studio.unsavedAlertStayCta,
    unsavedDiscardCta: studio.unsavedAlertDiscardCta,
    cancelButtonLabel: studio.cancelButton,
    submitButtonLabel: studio.saveButtonLabel,
  };
  const footerHint = state.savedFeedback
    ? studio.savedFeedbackLabel
    : state.isDirty
      ? (studio.unsavedChangesHintLabel ?? studio.escapeCancelHint)
      : (studio.explicitSaveHintLabel ?? studio.escapeCancelHint);

  return (
    <OrciaDialog
      open={true}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) state.guard.requestClose();
      }}
      onEscapeKeyDown={(e) => {
        e.preventDefault();
      }}
      title={agent.name}
      testId={`agent-detail-modal-${agent.agentId}`}
      closeLabel={studio.closeEscapeLabel}
      closeButtonTestId={`close-agent-detail-modal-btn-${agent.agentId}`}
      contentClassName="orcia-ds-dialog-content-wide w-[960px] max-w-[96vw] max-h-[82vh] text-xs"
      headerExtra={
        <AgentDetailModalHeader
          agent={agent}
          labels={labels}
          isPack={isPack}
          lifecycleStatus={lifecycleStatus}
          testBenchStatus={testBenchStatus}
          mcpExposed={state.mcpExposed}
          isUpdatingMcp={state.isUpdatingMcp}
          isUpdatingLifecycle={state.isUpdatingLifecycle}
          savedFeedback={state.savedFeedback}
          onToggleMcpExposure={(checked) => {
            void state.handleToggleMcp(checked);
          }}
          onToggleLifecycle={
            onUpdateAgentLifecycle
              ? (nextLifecycle) => {
                  void state.handleToggleLifecycle(nextLifecycle);
                }
              : undefined
          }
        />
      }
    >
      <div className="orcia-ds-dialog-body pt-3 space-y-4">
        <RgaaUnsavedChangesAlert
          testIdPrefix={`agent-detail-${agent.agentId}`}
          isOpen={state.guard.showUnsavedAlert}
          labels={guardLabels}
          onStay={state.guard.cancelDiscard}
          onConfirmDiscard={state.guard.confirmDiscard}
        />

        {state.displayedError ? (
          <OrciaAlertBanner
            tone="crimson"
            role="alert"
            testId={`agent-detail-modal-error-${agent.agentId}`}
          >
            {state.displayedError}
          </OrciaAlertBanner>
        ) : null}

        <AgentSixBlocksEditorBody
          draft={state.draft}
          labels={labels}
          skills={skills}
          activeBlock={state.activeBlock}
          showAllBlocks={state.showAllBlocks}
          readOnlyIdentity={isPack}
          testIdPrefix={`detail-${agent.agentId}`}
          onSelectBlock={(blk) => {
            state.setActiveBlock(blk);
            state.setShowAllBlocks(false);
          }}
          onToggleShowAllBlocks={() => state.setShowAllBlocks((p) => !p)}
          onChangeDraft={state.handleChangeDraft}
          onToggleSkillId={(skillId, checked) => {
            void state.handleToggleSkill(skillId, checked);
          }}
        />

        <AgentTestBenchSection
          agent={agent}
          labels={labels}
          satisfiedConditionsCount={readiness.filter((r) => r.satisfied).length}
          testInputValue={testInputValue}
          readOnlyPack={isPack}
          onChangeTestInput={onChangeTestInput}
          onRunAgent={state.handleRunAgent}
          sandboxTraceSlot={sandboxTraceSlot}
        />
      </div>

      <div className="orcia-ds-dialog-footer justify-between">
        <span
          data-testid={`agent-detail-footer-status-${agent.agentId}`}
          className="text-[11px] text-[var(--orcia-text-secondary)]"
          style={state.savedFeedback ? { color: "var(--color-status-success)" } : undefined}
        >
          {isPack ? studio.mcpPackPresetReadOnlyHint : footerHint}
        </span>
        <RgaaDialogFooterActions
          testIdPrefix={`agent-detail-${agent.agentId}`}
          cancelTestId={`cancel-agent-detail-modal-btn-${agent.agentId}`}
          submitTestId={`save-agent-detail-modal-btn-${agent.agentId}`}
          cancelLabel={state.isDirty ? studio.cancelButton : studio.closeEscapeLabel}
          submitLabel={
            state.isSaving
              ? (studio.savingChangesLabel ?? studio.saveButtonLabel)
              : studio.saveButtonLabel
          }
          submitDisabled={isPack || !state.isDirty || state.isSaving}
          isSubmitting={state.isSaving}
          onCancel={state.guard.requestClose}
          onSubmit={() => {
            void state.handleSaveDetails();
          }}
        />
      </div>
    </OrciaDialog>
  );
};
