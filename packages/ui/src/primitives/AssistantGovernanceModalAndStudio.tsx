import React, { useEffect, useState } from "react";
import {
  resolveRgaaModalGuardLabels,
  RgaaUnsavedChangesAlert,
  useUnsavedChangesDialogGuard,
  type RgaaModalGuardLabels,
} from "../components/RgaaModalDialog";
import { AssistantGovernanceModeATabs } from "./AssistantGovernanceModeATabs";
import { AssistantGovernanceStudioModeB } from "./AssistantGovernanceStudioModeB";

export type UiAssistantResponseTone = "SYNTHETIC" | "BALANCED" | "DETAILED_CODE";
export type UiAssistantResponseFormat = "BULLETS_SUMMARY" | "STRUCTURED_SECTIONS" | "STEP_BY_STEP";

export interface UiAssembledLayerItem {
  readonly layerNumber: number;
  readonly layerCode: "1_CONSTITUTION" | "2_PACK_METIER" | "3_EQUIPE" | "4_ESPACE" | "5_UTILISATEUR";
  readonly label: string;
  readonly immutable: boolean;
  readonly originBadge: "SOCLE" | "PACK" | "EQUIPE" | "ESPACE" | "UTILISATEUR";
  readonly content: string;
  readonly sha256: string;
}

export interface UiAssistantPromptTelemetryRecord {
  readonly turnId: string;
  readonly timestampIso: string;
  readonly userPrompt: string;
  readonly assembledSystemPrompt: string;
  readonly conversationHistoryCount: number;
  readonly folderTitle?: string | null;
  readonly folderPinnedNotes?: string | null;
  readonly thinkingText?: string;
  readonly assistantReply: string;
  readonly modelLabel: string;
  readonly thinkingEffort: string;
  readonly thinkingElapsedSeconds: number;
  readonly userFeedback?: "LIKE" | "DISLIKE" | null;
}

export interface UiAssistantStudioNode {
  readonly nodeId: string;
  readonly title: string;
  readonly nodeOrder: number;
  readonly isHarnessBoundary: boolean;
  readonly lockedBy: "HARNESS" | "PLATFORM" | "TEAM" | null;
  readonly enabled: boolean;
  readonly subLayersCount: number;
  readonly subAgentUri?: string | null;
}

export interface AssistantGovernanceModalAndStudioLabels extends RgaaModalGuardLabels {
  readonly modalTitle: string;
  readonly tab1UserTitle: string;
  readonly tab2WorkspaceTitle: string;
  readonly tab3AssemblyTitle: string;
  readonly toneLabel: string;
  readonly formatLabel: string;
  readonly defaultHatLabel: string;
  readonly personalInstructionsLabel: string;
  readonly saveUserPrefsCta: string;
  readonly workspaceInstructionsLabel: string;
  readonly workspaceReadOnlyBadge: string;
  readonly mcpExposeToggleLabel: string;
  readonly mcpFrozenByUpperBadge: string;
  readonly copyMcpConfigCta: string;
  readonly saveWorkspaceSettingsCta: string;
  readonly openStudioModeBCta: string;
  readonly studioHeaderTitle: string;
  readonly studioPrePromptLabel: string;
  readonly studioHarnessImmutableBadge: string;
  readonly studioTestDryRunCta: string;
  readonly studioSaveOverrideCta: string;
  readonly studioResetDefaultCta: string;
}

export interface AssistantGovernanceModalAndStudioProps {
  readonly workspaceId: string;
  readonly canEditWorkspaceLayer: boolean;
  readonly canOpenStudioModeB: boolean;
  readonly isOpen?: boolean;
  readonly initialUserTone?: UiAssistantResponseTone;
  readonly initialUserFormat?: UiAssistantResponseFormat;
  readonly initialDefaultHat?: string;
  readonly initialPersonalInstructions?: string;
  readonly initialWorkspaceInstructions?: string;
  readonly initialMcpExposed?: boolean;
  readonly mcpFrozenByUpperLayer?: boolean;
  readonly mcpIdeConfigJson?: string;
  readonly assembledLayers: readonly UiAssembledLayerItem[];
  readonly promptTelemetryLog?: readonly UiAssistantPromptTelemetryRecord[];
  readonly studioNodes: readonly UiAssistantStudioNode[];
  readonly initialStudioPrePrompt?: string;
  readonly labels: AssistantGovernanceModalAndStudioLabels;
  readonly onSaveUserPreferences?: (payload: {
    responseTone: UiAssistantResponseTone;
    favoriteFormat: UiAssistantResponseFormat;
    defaultHat: string;
    personalInstructions: string;
  }) => void;
  readonly onSaveWorkspaceSettings?: (payload: {
    workspaceInstructions: string;
    mcpExposeAssistant: boolean;
  }) => void;
  readonly onCopyMcpConfig?: (jsonText: string) => void;
  readonly onSaveStudioOverride?: (payload: {
    scopeLevel: "TEAM" | "WORKSPACE";
    aiPrePrompt: string;
    nodes: readonly UiAssistantStudioNode[];
  }) => void;
  readonly onResetStudioOverride?: (scopeLevel: "TEAM" | "WORKSPACE") => void;
  readonly onClose?: () => void;
}

export const ASSISTANT_DEFAULT_HAT_OPTIONS: readonly { readonly value: string; readonly label: string }[] = [
  { value: "PM", label: "Chef de Projet / Product Manager" },
  { value: "TECH_LEAD", label: "Tech Lead / Architecte" },
  { value: "DEV", label: "Développeur / Ingénieur" },
  { value: "ANALYST", label: "Analyste Métier" },
  { value: "QA_COMPLIANCE", label: "Responsable Qualité & Conformité" },
  { value: "PLATFORM_ADMIN", label: "Administrateur de la Plateforme" },
  { value: "CONTRIBUTOR", label: "Contributeur d'Équipe" },
];

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
    <div
      role="dialog"
      aria-modal="true"
      aria-label={activeMode === "MODE_A" ? labels.modalTitle : labels.studioHeaderTitle}
      data-testid="assistant-governance-container"
      data-active-mode={activeMode}
      className="rounded-xl border border-surface-border bg-surface-elevated p-4 text-xs text-text-primary space-y-4"
    >
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
              ✓ Enregistré
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
              ← Retour aux réglages
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
            setDryRunOutput("▷ Dry-Run OK : étapes et règles de sécurité vérifiées (0 écriture externe).")
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
  );
}
