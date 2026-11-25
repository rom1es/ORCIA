import * as DialogPrimitive from "@radix-ui/react-dialog";
import React from "react";
import { OrciaIcon } from "../components/icons";
import {
  RgaaDialogFooterActions,
  RgaaUnsavedChangesAlert,
} from "../components/RgaaModalDialog";
import { AssistantGovernanceModeATabs } from "./AssistantGovernanceModeATabs";
import {
  type AssistantGovernanceModalAndStudioLabels,
  type AssistantGovernanceModalAndStudioProps,
  type UiAssembledLayerItem,
  type UiAssistantPromptTelemetryRecord,
  type UiAssistantResponseFormat,
  type UiAssistantResponseTone,
  type UiAssistantSelectOption,
  type UiAssistantStudioNode,
} from "./AssistantGovernanceTypes";
import { OrciaAlertBanner } from "./OrciaAlertBanner";
import { useAssistantGovernanceModalState } from "./useAssistantGovernanceModalState";

export type {
  AssistantGovernanceModalAndStudioLabels,
  AssistantGovernanceModalAndStudioProps,
  UiAssembledLayerItem,
  UiAssistantPromptTelemetryRecord,
  UiAssistantResponseFormat,
  UiAssistantResponseTone,
  UiAssistantSelectOption,
  UiAssistantStudioNode,
};

export function AssistantGovernanceModalAndStudio({
  workspaceId,
  canEditWorkspaceLayer,
  isOpen = true,
  initialUserTone = "BALANCED",
  initialUserFormat = "STRUCTURED_SECTIONS",
  initialDefaultHat = "PM",
  initialPersonalInstructions = "",
  initialWorkspaceInstructions = "",
  initialMcpExposed = true,
  mcpFrozenByUpperLayer = false,
  mcpIdeConfigJson = '{"mcpServers":{"orcia-assistant":{"url":"/api/v1/mcp/spaces/default","tool":"assistant.ask"}}}',
  assembledLayers,
  promptTelemetryLog = [],
  saveError = null,
  labels,
  onSaveUserPreferences,
  onSaveWorkspaceSettings,
  onCopyMcpConfig,
  onClearSaveError,
  onClose,
}: AssistantGovernanceModalAndStudioProps): React.ReactElement | null {
  const state = useAssistantGovernanceModalState({
    isOpen,
    canEditWorkspaceLayer,
    initialUserTone,
    initialUserFormat,
    initialDefaultHat,
    initialPersonalInstructions,
    initialWorkspaceInstructions,
    initialMcpExposed,
    mcpFrozenByUpperLayer,
    saveError,
    labels,
    onSaveUserPreferences,
    onSaveWorkspaceSettings,
    onClearSaveError,
    onClose,
  });

  if (!state.effectiveOpen) return null;

  const cancelCloseLabel = state.isDirty
    ? (labels.cancelButtonLabel ?? labels.cancelCta ?? "")
    : (labels.closeButtonLabel ?? labels.cancelButtonLabel ?? labels.cancelCta ?? "");
  const submitButtonLabel = state.isSaving
    ? (labels.savingChangesLabel ?? labels.saveChangesCta ?? labels.saveUserPrefsCta)
    : (labels.saveChangesCta ?? labels.saveUserPrefsCta);

  return (
    <DialogPrimitive.Root
      open={true}
      modal={false}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) state.guard.requestClose();
      }}
    >
      <DialogPrimitive.Portal>
        <div className="orcia-ds-dialog-overlay" />
        <DialogPrimitive.Content
          asChild
          aria-describedby={undefined}
          onEscapeKeyDown={(e) => {
            e.preventDefault();
          }}
        >
          <div
            aria-label={labels.modalTitle}
            data-testid="assistant-governance-container"
            data-active-mode="MODE_A"
            style={{ overflowY: "auto" }}
            className="orcia-ds-dialog-content orcia-ds-dialog-content-wide rounded-xl border border-surface-border bg-surface-elevated p-4 text-xs text-text-primary space-y-4"
          >
            <DialogPrimitive.Title className="sr-only">
              {labels.modalTitle}
            </DialogPrimitive.Title>
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <div className="flex items-center gap-2.5">
                <span className="font-semibold text-sm">{labels.modalTitle}</span>
                {state.autosavedBadgeVisible && (
                  <span
                    data-testid="assistant-gov-autosaved-badge"
                    style={{
                      color: "var(--color-status-success)",
                      backgroundColor: "var(--color-gate-emerald-bg)",
                    }}
                    className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
                  >
                    <OrciaIcon name="check" /> {labels.savedBadgeLabel}
                  </span>
                )}
              </div>
            </div>

            <RgaaUnsavedChangesAlert
              testIdPrefix="assistant-gov"
              isOpen={state.guard.showUnsavedAlert}
              labels={labels}
              onStay={state.guard.cancelDiscard}
              onConfirmDiscard={state.guard.confirmDiscard}
            />

            {state.displayedError && (
              <OrciaAlertBanner tone="crimson" testId="assistant-gov-error-banner">
                {state.displayedError}
              </OrciaAlertBanner>
            )}

            <AssistantGovernanceModeATabs
              workspaceId={workspaceId}
              activeTab={state.activeTab}
              canEditWorkspaceLayer={canEditWorkspaceLayer}
              mcpFrozenByUpperLayer={mcpFrozenByUpperLayer}
              mcpIdeConfigJson={mcpIdeConfigJson}
              userTone={state.userTone}
              userFormat={state.userFormat}
              defaultHat={state.defaultHat}
              personalInstructions={state.personalInstructions}
              workspaceInstructions={state.workspaceInstructions}
              mcpExposed={state.mcpExposed}
              copiedMcp={state.copiedMcp}
              isDirty={state.isDirty}
              assembledLayers={assembledLayers}
              promptTelemetryLog={promptTelemetryLog}
              labels={labels}
              onSelectTab={state.setActiveTab}
              onChangeTone={(next) => { state.setUserTone(next); state.clearFeedbackOnEdit(); }}
              onChangeFormat={(next) => { state.setUserFormat(next); state.clearFeedbackOnEdit(); }}
              onChangeDefaultHat={(next) => { state.setDefaultHat(next); state.clearFeedbackOnEdit(); }}
              onChangePersonalInstructions={(next) => {
                state.setPersonalInstructions(next);
                state.clearFeedbackOnEdit();
              }}
              onChangeWorkspaceInstructions={(next) => {
                state.setWorkspaceInstructions(next);
                state.clearFeedbackOnEdit();
              }}
              onChangeMcpExposed={(next) => { state.setMcpExposed(next); state.clearFeedbackOnEdit(); }}
              onCopyMcpConfig={() => {
                state.setCopiedMcp(true);
                onCopyMcpConfig?.(mcpIdeConfigJson);
              }}
            />

            <div className="border-t border-surface-border pt-3">
              <RgaaDialogFooterActions
                testIdPrefix="assistant-gov"
                cancelTestId="assistant-gov-cancel-btn"
                submitTestId="assistant-save-user-prefs-btn"
                cancelLabel={cancelCloseLabel}
                submitLabel={submitButtonLabel}
                submitDisabled={!state.isDirty || state.isSaving}
                isSubmitting={state.isSaving}
                onCancel={state.guard.requestClose}
                onSubmit={() => { void state.handleSaveChanges(); }}
              />
            </div>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
