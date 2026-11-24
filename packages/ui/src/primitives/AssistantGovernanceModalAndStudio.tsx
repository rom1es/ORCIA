import * as DialogPrimitive from "@radix-ui/react-dialog";
import React, { useEffect, useState } from "react";
import { OrciaIcon } from "../components/icons";
import {
  RgaaUnsavedChangesAlert,
  useUnsavedChangesDialogGuard,
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
  labels,
  onSaveUserPreferences,
  onSaveWorkspaceSettings,
  onCopyMcpConfig,
  onClose,
}: AssistantGovernanceModalAndStudioProps): React.ReactElement | null {
  const [internalOpen, setInternalOpen] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<
    "USER_PREFS" | "WORKSPACE_SETTINGS" | "FULL_ASSEMBLY"
  >("USER_PREFS");

  const [userTone, setUserTone] = useState<UiAssistantResponseTone>(initialUserTone);
  const [userFormat, setUserFormat] = useState<UiAssistantResponseFormat>(initialUserFormat);
  const [defaultHat, setDefaultHat] = useState<string>(initialDefaultHat);
  const [personalInstructions, setPersonalInstructions] = useState<string>(
    initialPersonalInstructions,
  );
  const [workspaceInstructions, setWorkspaceInstructions] = useState<string>(
    initialWorkspaceInstructions,
  );
  const [mcpExposed, setMcpExposed] = useState<boolean>(
    mcpFrozenByUpperLayer ? false : initialMcpExposed,
  );
  const [copiedMcp, setCopiedMcp] = useState<boolean>(false);
  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [autosavedBadgeVisible, setAutosavedBadgeVisible] = useState<boolean>(false);

  useEffect(() => {
    setUserTone(initialUserTone);
    setUserFormat(initialUserFormat);
    setDefaultHat(initialDefaultHat);
    setPersonalInstructions(initialPersonalInstructions);
    setWorkspaceInstructions(initialWorkspaceInstructions);
    setMcpExposed(mcpFrozenByUpperLayer ? false : initialMcpExposed);
  }, [
    initialUserTone,
    initialUserFormat,
    initialDefaultHat,
    initialPersonalInstructions,
    initialWorkspaceInstructions,
    initialMcpExposed,
    mcpFrozenByUpperLayer,
  ]);

  useEffect(() => {
    if (!autosavedBadgeVisible) return;
    const timer = setTimeout(() => setAutosavedBadgeVisible(false), 3000);
    return () => clearTimeout(timer);
  }, [autosavedBadgeVisible]);

  const effectiveOpen = isOpen && internalOpen;

  const resetUnsavedChanges = (): void => {
    setUserTone(initialUserTone);
    setUserFormat(initialUserFormat);
    setDefaultHat(initialDefaultHat);
    setPersonalInstructions(initialPersonalInstructions);
    setWorkspaceInstructions(initialWorkspaceInstructions);
    setMcpExposed(mcpFrozenByUpperLayer ? false : initialMcpExposed);
    setIsDirty(false);
  };

  const handleCloseAction = (): void => {
    if (onClose) onClose();
    else setInternalOpen(false);
  };

  const { showUnsavedAlert, requestClose, cancelDiscard, confirmDiscard } =
    useUnsavedChangesDialogGuard({
      isOpen: effectiveOpen,
      isDirty,
      onClose: handleCloseAction,
      onDiscardChanges: resetUnsavedChanges,
    });

  if (!effectiveOpen) return null;

  const triggerAutoSaveUserPrefs = (patch: {
    responseTone?: UiAssistantResponseTone;
    favoriteFormat?: UiAssistantResponseFormat;
    defaultHat?: string;
    personalInstructions?: string;
  }) => {
    setAutosavedBadgeVisible(true);
    onSaveUserPreferences?.({
      responseTone: patch.responseTone ?? userTone,
      favoriteFormat: patch.favoriteFormat ?? userFormat,
      defaultHat: patch.defaultHat ?? defaultHat,
      personalInstructions: patch.personalInstructions ?? personalInstructions,
    });
  };

  const triggerAutoSaveWorkspace = (patch: {
    workspaceInstructions?: string;
    mcpExposeAssistant?: boolean;
  }) => {
    setAutosavedBadgeVisible(true);
    onSaveWorkspaceSettings?.({
      workspaceInstructions: patch.workspaceInstructions ?? workspaceInstructions,
      mcpExposeAssistant: patch.mcpExposeAssistant ?? mcpExposed,
    });
  };

  return (
    <DialogPrimitive.Root
      open={true}
      modal={false}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) requestClose();
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
          <span className="font-semibold text-sm">
            {labels.modalTitle}
          </span>
          {autosavedBadgeVisible && (
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
        <div className="flex items-center gap-2">
          <button
            type="button"
            data-testid="assistant-gov-cancel-btn"
            onClick={requestClose}
            className="px-3 py-1.5 rounded-lg border border-surface-border bg-surface-secondary text-text-primary"
          >
            {labels.cancelButtonLabel ?? labels.cancelCta ?? ""}
          </button>
        </div>
      </div>

      <RgaaUnsavedChangesAlert
        testIdPrefix="assistant-gov"
        isOpen={showUnsavedAlert}
        labels={labels}
        onStay={cancelDiscard}
        onConfirmDiscard={confirmDiscard}
      />

      <AssistantGovernanceModeATabs
        workspaceId={workspaceId}
        activeTab={activeTab}
        canEditWorkspaceLayer={canEditWorkspaceLayer}
        mcpFrozenByUpperLayer={mcpFrozenByUpperLayer}
        mcpIdeConfigJson={mcpIdeConfigJson}
        userTone={userTone}
        userFormat={userFormat}
        defaultHat={defaultHat}
        personalInstructions={personalInstructions}
        workspaceInstructions={workspaceInstructions}
        mcpExposed={mcpExposed}
        copiedMcp={copiedMcp}
        assembledLayers={assembledLayers}
        promptTelemetryLog={promptTelemetryLog}
        labels={labels}
        onSelectTab={setActiveTab}
        onChangeTone={(next) => { setUserTone(next); setIsDirty(true); triggerAutoSaveUserPrefs({ responseTone: next }); }}
        onChangeFormat={(next) => { setUserFormat(next); setIsDirty(true); triggerAutoSaveUserPrefs({ favoriteFormat: next }); }}
        onChangeDefaultHat={(next) => { setDefaultHat(next); setIsDirty(true); triggerAutoSaveUserPrefs({ defaultHat: next }); }}
        onChangePersonalInstructions={(next) => { setPersonalInstructions(next); setIsDirty(true); triggerAutoSaveUserPrefs({ personalInstructions: next }); }}
        onSaveUserPrefs={() => { setIsDirty(false); triggerAutoSaveUserPrefs({}); }}
        onChangeWorkspaceInstructions={(next) => { setWorkspaceInstructions(next); setIsDirty(true); triggerAutoSaveWorkspace({ workspaceInstructions: next }); }}
        onChangeMcpExposed={(next) => { setMcpExposed(next); setIsDirty(true); triggerAutoSaveWorkspace({ mcpExposeAssistant: next }); }}
        onCopyMcpConfig={() => { setCopiedMcp(true); onCopyMcpConfig?.(mcpIdeConfigJson); }}
        onSaveWorkspaceSettings={() => { setIsDirty(false); triggerAutoSaveWorkspace({}); }}
      />
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
