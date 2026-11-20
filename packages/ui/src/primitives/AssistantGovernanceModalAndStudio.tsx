import * as DialogPrimitive from "@radix-ui/react-dialog";
import React, { useEffect, useState } from "react";
import { OrciaIcon } from "../components/icons";
import {
  resolveRgaaModalGuardLabels,
  RgaaUnsavedChangesAlert,
  useUnsavedChangesDialogGuard,
  type RgaaModalGuardLabels,
} from "../components/RgaaModalDialog";
import { AssistantGovernanceModeATabs } from "./AssistantGovernanceModeATabs";
import { AssistantGovernanceStudioModeB } from "./AssistantGovernanceStudioModeB";
import {
  ASSISTANT_DEFAULT_HAT_OPTIONS,
  type AssistantGovernanceModalAndStudioLabels,
  type AssistantGovernanceModalAndStudioProps,
  type UiAssembledLayerItem,
  type UiAssistantPromptTelemetryRecord,
  type UiAssistantResponseFormat,
  type UiAssistantResponseTone,
  type UiAssistantStudioNode,
} from "./AssistantGovernanceTypes";

export {
  ASSISTANT_DEFAULT_HAT_OPTIONS,
  type AssistantGovernanceModalAndStudioLabels,
  type AssistantGovernanceModalAndStudioProps,
  type UiAssembledLayerItem,
  type UiAssistantPromptTelemetryRecord,
  type UiAssistantResponseFormat,
  type UiAssistantResponseTone,
  type UiAssistantStudioNode,
};

export function AssistantGovernanceModalAndStudio({
  workspaceId,
  canEditWorkspaceLayer,
  canOpenStudioModeB,
  isOpen = true,
  initialUserTone = "BALANCED",
  initialUserFormat = "STRUCTURED_SECTIONS",
  initialDefaultHat = "PM",
  initialPersonalInstructions = "Privilégier des réponses claires, citer les documents utilisés et mettre en évidence les points d'attention.",
  initialWorkspaceInstructions = "Respecter le vocabulaire métier de l'équipe et s'appuyer en priorité sur les documents de référence de l'espace.",
  initialMcpExposed = true,
  mcpFrozenByUpperLayer = false,
  mcpIdeConfigJson = '{"mcpServers":{"orcia-assistant":{"url":"/api/v1/mcp/spaces/default","tool":"assistant.ask"}}}',
  assembledLayers,
  promptTelemetryLog = [],
  studioNodes,
  initialStudioPrePrompt = "Coordonner les étapes d'analyse, de recherche documentaire et de vérification avant de rédiger la réponse.",
  labels,
  onSaveUserPreferences,
  onSaveWorkspaceSettings,
  onCopyMcpConfig,
  onSaveStudioOverride,
  onResetStudioOverride,
  onClose,
}: AssistantGovernanceModalAndStudioProps): React.ReactElement | null {
  const [internalOpen, setInternalOpen] = useState<boolean>(true);
  const [activeMode, setActiveMode] = useState<"MODE_A" | "MODE_B">("MODE_A");
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
  const [studioScope, setStudioScope] = useState<"WORKSPACE" | "TEAM">("WORKSPACE");
  const [studioPrePrompt, setStudioPrePrompt] = useState<string>(initialStudioPrePrompt);
  const [nodes, setNodes] = useState<readonly UiAssistantStudioNode[]>(studioNodes);
  const [dryRunOutput, setDryRunOutput] = useState<string | null>(null);
  const [resetBanner, setResetBanner] = useState<boolean>(false);
  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [autosavedBadgeVisible, setAutosavedBadgeVisible] = useState<boolean>(false);

  useEffect(() => {
    if (!autosavedBadgeVisible) return;
    const timer = setTimeout(() => setAutosavedBadgeVisible(false), 3000);
    return () => clearTimeout(timer);
  }, [autosavedBadgeVisible]);

  const effectiveOpen = isOpen && internalOpen;
  const guardLabels = resolveRgaaModalGuardLabels(labels);

  const resetUnsavedChanges = (): void => {
    setUserTone(initialUserTone);
    setUserFormat(initialUserFormat);
    setDefaultHat(initialDefaultHat);
    setPersonalInstructions(initialPersonalInstructions);
    setWorkspaceInstructions(initialWorkspaceInstructions);
    setMcpExposed(mcpFrozenByUpperLayer ? false : initialMcpExposed);
    setStudioPrePrompt(initialStudioPrePrompt);
    setNodes(studioNodes);
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
            aria-label={activeMode === "MODE_A" ? labels.modalTitle : labels.studioHeaderTitle}
            data-testid="assistant-governance-container"
            data-active-mode={activeMode}
            style={{ overflowY: "auto" }}
            className="orcia-ds-dialog-content orcia-ds-dialog-content-wide rounded-xl border border-surface-border bg-surface-elevated p-4 text-xs text-text-primary space-y-4"
          >
            <DialogPrimitive.Title className="sr-only">
              {activeMode === "MODE_A" ? labels.modalTitle : labels.studioHeaderTitle}
            </DialogPrimitive.Title>
      <div className="flex items-center justify-between border-b border-surface-border pb-3">
        <div className="flex items-center gap-2.5">
          <span className="font-semibold text-sm">
            {activeMode === "MODE_A" ? labels.modalTitle : labels.studioHeaderTitle}
          </span>
          {autosavedBadgeVisible && (
            <span
              data-testid="assistant-gov-autosaved-badge"
              style={{
                color: "var(--color-status-success)",
                backgroundColor: "rgba(22, 163, 74, 0.12)",
              }}
              className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
            >
              <OrciaIcon name="check" /> Enregistré
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {activeMode === "MODE_A" && canOpenStudioModeB && (
            <button
              type="button"
              data-testid="assistant-open-studio-mode-b-btn"
              onClick={() => setActiveMode("MODE_B")}
              className="px-3 py-1.5 rounded-lg border border-brand-primary bg-surface-secondary font-medium text-brand-primary"
            >
              {labels.openStudioModeBCta}
            </button>
          )}
          {activeMode === "MODE_B" && (
            <button
              type="button"
              data-testid="assistant-back-to-mode-a-btn"
              onClick={() => setActiveMode("MODE_A")}
              className="px-3 py-1.5 rounded-lg border border-surface-border bg-surface-secondary"
            >
              <OrciaIcon name="arrowLeft" /> Retour aux réglages
            </button>
          )}
          <button
            type="button"
            data-testid="assistant-gov-cancel-btn"
            onClick={requestClose}
            className="px-3 py-1.5 rounded-lg border border-surface-border bg-surface-secondary text-text-primary"
          >
            {guardLabels.cancelButtonLabel}
          </button>
        </div>
      </div>

      <RgaaUnsavedChangesAlert
        testIdPrefix="assistant-gov"
        isOpen={showUnsavedAlert}
        labels={guardLabels}
        onStay={cancelDiscard}
        onConfirmDiscard={confirmDiscard}
      />

      {activeMode === "MODE_A" ? (
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
      ) : (
        <AssistantGovernanceStudioModeB
          workspaceId={workspaceId}
          studioScope={studioScope}
          studioPrePrompt={studioPrePrompt}
          nodes={nodes}
          dryRunOutput={dryRunOutput}
          resetBanner={resetBanner}
          cancelLabel={guardLabels.cancelButtonLabel}
          showCancelButton={false}
          labels={labels}
          onChangeStudioScope={(s) => { setStudioScope(s); setIsDirty(true); }}
          onChangeStudioPrePrompt={(p) => { setStudioPrePrompt(p); setIsDirty(true); }}
          onToggleNodeSubAgent={(nodeId) => {
            setNodes((prev) =>
              prev.map((n) =>
                n.nodeId !== nodeId || n.isHarnessBoundary || n.lockedBy !== null
                  ? n
                  : { ...n, subLayersCount: n.subLayersCount + 1, subAgentUri: "orcia://agents/custom-workspace-sub-agent" },
              ),
            );
            setIsDirty(true);
          }}
          onRunDryRun={() =>
            setDryRunOutput("▷ Simulation vérifiée : étapes et règles de sécurité validées (0 écriture externe).")
          }
          onSaveOverride={() => {
            setIsDirty(false);
            setAutosavedBadgeVisible(true);
            onSaveStudioOverride?.({ scopeLevel: studioScope, aiPrePrompt: studioPrePrompt, nodes });
          }}
          onResetDefault={() => {
            setNodes(studioNodes);
            setStudioPrePrompt(initialStudioPrePrompt);
            setIsDirty(false);
            setResetBanner(true);
            onResetStudioOverride?.(studioScope);
          }}
          onCancel={requestClose}
        />
      )}
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
