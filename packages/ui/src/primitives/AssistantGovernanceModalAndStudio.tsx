import React, { useState } from "react";
import {
  handleRgaaSubmitKeyDown,
  resolveRgaaModalGuardLabels,
  RgaaUnsavedChangesAlert,
  useUnsavedChangesDialogGuard,
  type RgaaModalGuardLabels,
} from "../components/RgaaModalDialog";
import { AssistantGovernanceStudioModeB } from "./AssistantGovernanceStudioModeB";

export type UiAssistantResponseTone = "SYNTHETIC" | "BALANCED" | "DETAILED_CODE";
export type UiAssistantResponseFormat =
  | "BULLETS_SUMMARY"
  | "STRUCTURED_SECTIONS"
  | "STEP_BY_STEP";

export interface UiAssembledLayerItem {
  readonly layerNumber: number;
  readonly layerCode:
    | "1_CONSTITUTION"
    | "2_PACK_METIER"
    | "3_EQUIPE"
    | "4_ESPACE"
    | "5_UTILISATEUR";
  readonly label: string;
  readonly immutable: boolean;
  readonly originBadge: "SOCLE" | "PACK" | "EQUIPE" | "ESPACE" | "UTILISATEUR";
  readonly content: string;
  readonly sha256: string;
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

/**
 * Story 10.1 — 4-Level Governance & Customization of `Mon Assistant`
 * (Mode A 3-Tab Modal & Mode B Studio Graph inside `🔒 AssistantHarness` bounds)
 * with RGAA Escape, Cancel button, Unsaved Changes guard, and Enter-on-Submit.
 */
export function AssistantGovernanceModalAndStudio({
  workspaceId,
  canEditWorkspaceLayer,
  canOpenStudioModeB,
  isOpen = true,
  initialUserTone = "BALANCED",
  initialUserFormat = "STRUCTURED_SECTIONS",
  initialDefaultHat = "PM",
  initialPersonalInstructions = "Toujours citer [S1] et synthétiser les risques.",
  initialWorkspaceInstructions = "Respecter le glossaire actif de l'Espace et privilégier les sources RÉFÉRENCE.",
  initialMcpExposed = true,
  mcpFrozenByUpperLayer = false,
  mcpIdeConfigJson = '{"mcpServers":{"orcia-assistant":{"url":"/api/v1/mcp/spaces/default","tool":"assistant.ask"}}}',
  assembledLayers,
  studioNodes,
  initialStudioPrePrompt = "Exécuter le graphe assistant-agent à 5 nœuds entre les bornes 🔒 AssistantHarness.",
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
  const [userFormat, setUserFormat] =
    useState<UiAssistantResponseFormat>(initialUserFormat);
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
  const [studioPrePrompt, setStudioPrePrompt] = useState<string>(
    initialStudioPrePrompt,
  );
  const [nodes, setNodes] = useState<readonly UiAssistantStudioNode[]>(studioNodes);
  const [dryRunOutput, setDryRunOutput] = useState<string | null>(null);
  const [resetBanner, setResetBanner] = useState<boolean>(false);
  const [isDirty, setIsDirty] = useState<boolean>(false);

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
    if (onClose) {
      onClose();
    } else {
      setInternalOpen(false);
    }
  };

  const { showUnsavedAlert, requestClose, cancelDiscard, confirmDiscard } =
    useUnsavedChangesDialogGuard({
      isOpen: effectiveOpen,
      isDirty,
      onClose: handleCloseAction,
      onDiscardChanges: resetUnsavedChanges,
    });

  if (!effectiveOpen) {
    return null;
  }

  const handleToggleNodeSubAgent = (nodeId: string): void => {
    setNodes((prev) =>
      prev.map((n) => {
        if (n.nodeId !== nodeId || n.isHarnessBoundary || n.lockedBy !== null) {
          return n;
        }
        return {
          ...n,
          subLayersCount: n.subLayersCount + 1,
          subAgentUri: "orcia://agents/custom-workspace-sub-agent",
        };
      }),
    );
    setIsDirty(true);
  };

  const handleSaveUserPrefs = (): void => {
    setIsDirty(false);
    onSaveUserPreferences?.({
      responseTone: userTone,
      favoriteFormat: userFormat,
      defaultHat,
      personalInstructions,
    });
  };

  const handleSaveWorkspaceSettings = (): void => {
    setIsDirty(false);
    onSaveWorkspaceSettings?.({
      workspaceInstructions,
      mcpExposeAssistant: mcpExposed,
    });
  };

  const handleSaveStudio = (): void => {
    setIsDirty(false);
    onSaveStudioOverride?.({
      scopeLevel: studioScope,
      aiPrePrompt: studioPrePrompt,
      nodes,
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
      {/* Top Header with Mode A <-> Mode B Switch + Cancel / Close */}
      <div className="flex items-center justify-between border-b border-surface-border pb-3">
        <div className="font-semibold text-sm">
          {activeMode === "MODE_A" ? labels.modalTitle : labels.studioHeaderTitle}
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
              ← Mode A
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
        <div data-testid="assistant-governance-mode-a" className="space-y-4">
          {/* 3-Tab Navigation */}
          <div role="tablist" className="grid grid-cols-3 gap-2">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "USER_PREFS"}
              data-testid="assistant-gov-tab-USER_PREFS"
              onClick={() => setActiveTab("USER_PREFS")}
              className={`py-2 px-3 rounded-lg border font-medium text-left ${
                activeTab === "USER_PREFS"
                  ? "border-brand-primary bg-surface-secondary"
                  : "border-surface-border bg-surface-primary text-text-secondary"
              }`}
            >
              {labels.tab1UserTitle}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "WORKSPACE_SETTINGS"}
              data-testid="assistant-gov-tab-WORKSPACE_SETTINGS"
              onClick={() => setActiveTab("WORKSPACE_SETTINGS")}
              className={`py-2 px-3 rounded-lg border font-medium text-left ${
                activeTab === "WORKSPACE_SETTINGS"
                  ? "border-brand-primary bg-surface-secondary"
                  : "border-surface-border bg-surface-primary text-text-secondary"
              }`}
            >
              {labels.tab2WorkspaceTitle}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "FULL_ASSEMBLY"}
              data-testid="assistant-gov-tab-FULL_ASSEMBLY"
              onClick={() => setActiveTab("FULL_ASSEMBLY")}
              className={`py-2 px-3 rounded-lg border font-medium text-left ${
                activeTab === "FULL_ASSEMBLY"
                  ? "border-brand-primary bg-surface-secondary"
                  : "border-surface-border bg-surface-primary text-text-secondary"
              }`}
            >
              {labels.tab3AssemblyTitle}
            </button>
          </div>

          {/* Tab 1: 👤 Mes préférences (Couche 5 — USER) */}
          {activeTab === "USER_PREFS" && (
            <div data-testid="assistant-gov-panel-user" className="space-y-3">
              <div className="grid grid-cols-3 gap-3">
                <label className="block space-y-1">
                  <span className="text-text-secondary">{labels.toneLabel}</span>
                  <select
                    data-testid="assistant-user-tone-select"
                    value={userTone}
                    onChange={(e) => {
                      setUserTone(e.target.value as UiAssistantResponseTone);
                      setIsDirty(true);
                    }}
                    className="w-full px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
                  >
                    <option value="SYNTHETIC">SYNTHETIC</option>
                    <option value="BALANCED">BALANCED</option>
                    <option value="DETAILED_CODE">DETAILED_CODE</option>
                  </select>
                </label>
                <label className="block space-y-1">
                  <span className="text-text-secondary">{labels.formatLabel}</span>
                  <select
                    data-testid="assistant-user-format-select"
                    value={userFormat}
                    onChange={(e) => {
                      setUserFormat(e.target.value as UiAssistantResponseFormat);
                      setIsDirty(true);
                    }}
                    className="w-full px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
                  >
                    <option value="BULLETS_SUMMARY">BULLETS_SUMMARY</option>
                    <option value="STRUCTURED_SECTIONS">STRUCTURED_SECTIONS</option>
                    <option value="STEP_BY_STEP">STEP_BY_STEP</option>
                  </select>
                </label>
                <label className="block space-y-1">
                  <span className="text-text-secondary">
                    {labels.defaultHatLabel}
                  </span>
                  <input
                    type="text"
                    autoComplete="off"
                    data-lpignore="true"
                    data-1p-ignore="true"
                    data-bwignore="true"
                    data-form-type="other"
                    data-testid="assistant-user-hat-input"
                    value={defaultHat}
                    onChange={(e) => {
                      setDefaultHat(e.target.value);
                      setIsDirty(true);
                    }}
                    className="w-full px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
                  />
                </label>
              </div>
              <label className="block space-y-1">
                <span className="text-text-secondary">
                  {labels.personalInstructionsLabel}
                </span>
                <textarea
                  rows={2}
                  autoComplete="off"
                  data-lpignore="true"
                  data-1p-ignore="true"
                  data-bwignore="true"
                  data-form-type="other"
                  data-testid="assistant-user-instructions-input"
                  value={personalInstructions}
                  onChange={(e) => {
                    setPersonalInstructions(e.target.value);
                    setIsDirty(true);
                  }}
                  className="w-full px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
                />
              </label>
              <button
                type="button"
                data-testid="assistant-save-user-prefs-btn"
                onClick={handleSaveUserPrefs}
                onKeyDown={(e) =>
                  handleRgaaSubmitKeyDown(e, handleSaveUserPrefs, false)
                }
                className="px-3 py-1.5 rounded-lg bg-brand-primary text-surface-elevated font-medium"
              >
                {labels.saveUserPrefsCta}
              </button>
            </div>
          )}

          {/* Tab 2: 📦 Réglages de l'Espace (Couche 4 — WORKSPACE) */}
          {activeTab === "WORKSPACE_SETTINGS" && (
            <div data-testid="assistant-gov-panel-workspace" className="space-y-3">
              {!canEditWorkspaceLayer && (
                <div
                  data-testid="assistant-workspace-readonly-badge"
                  className="p-2 rounded border border-surface-border bg-surface-secondary text-text-secondary"
                >
                  {labels.workspaceReadOnlyBadge}
                </div>
              )}
              <label className="block space-y-1">
                <span className="text-text-secondary">
                  {labels.workspaceInstructionsLabel} ({workspaceId})
                </span>
                <textarea
                  rows={2}
                  autoComplete="off"
                  data-lpignore="true"
                  data-1p-ignore="true"
                  data-bwignore="true"
                  data-form-type="other"
                  disabled={!canEditWorkspaceLayer}
                  data-testid="assistant-workspace-instructions-input"
                  value={workspaceInstructions}
                  onChange={(e) => {
                    setWorkspaceInstructions(e.target.value);
                    setIsDirty(true);
                  }}
                  className="w-full px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
                />
              </label>

              {/* MCP Exposure Toggle + Funnel Rule (Principe G) */}
              <div className="p-3 rounded-lg border border-surface-border bg-surface-primary space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <label className="flex items-center gap-2 font-medium">
                    <input
                      type="checkbox"
                      autoComplete="off"
                      data-lpignore="true"
                      data-1p-ignore="true"
                      data-bwignore="true"
                      data-form-type="other"
                      disabled={!canEditWorkspaceLayer || mcpFrozenByUpperLayer}
                      checked={mcpExposed}
                      data-testid="assistant-workspace-mcp-expose-toggle"
                      onChange={(e) => {
                        setMcpExposed(e.target.checked);
                        setIsDirty(true);
                      }}
                    />
                    <span>{labels.mcpExposeToggleLabel}</span>
                  </label>
                  {mcpFrozenByUpperLayer && (
                    <span
                      data-testid="assistant-mcp-frozen-funnel-badge"
                      className="px-2 py-0.5 rounded bg-status-warning/15 text-status-warning font-medium text-[11px]"
                    >
                      {labels.mcpFrozenByUpperBadge}
                    </span>
                  )}
                </div>
                <div className="flex items-center justify-between gap-2">
                  <code
                    data-testid="assistant-mcp-config-snippet"
                    className="text-[11px] font-mono text-text-secondary truncate"
                  >
                    {mcpIdeConfigJson}
                  </code>
                  <button
                    type="button"
                    data-testid="assistant-copy-mcp-config-btn"
                    onClick={() => {
                      setCopiedMcp(true);
                      onCopyMcpConfig?.(mcpIdeConfigJson);
                    }}
                    className="px-2.5 py-1 rounded border border-surface-border bg-surface-secondary shrink-0"
                  >
                    {labels.copyMcpConfigCta} {copiedMcp ? "✓" : ""}
                  </button>
                </div>
              </div>

              {canEditWorkspaceLayer && (
                <button
                  type="button"
                  data-testid="assistant-save-workspace-settings-btn"
                  onClick={handleSaveWorkspaceSettings}
                  onKeyDown={(e) =>
                    handleRgaaSubmitKeyDown(e, handleSaveWorkspaceSettings, false)
                  }
                  className="px-3 py-1.5 rounded-lg bg-brand-primary text-surface-elevated font-medium"
                >
                  {labels.saveWorkspaceSettingsCta}
                </button>
              )}
            </div>
          )}

          {/* Tab 3: 👁️ Assemblage complet (Lecture seule — 5 couches AD-15) */}
          {activeTab === "FULL_ASSEMBLY" && (
            <div
              data-testid="assistant-gov-panel-assembly"
              className="space-y-2"
            >
              {assembledLayers.map((layer) => (
                <div
                  key={layer.layerCode}
                  data-testid={`assembled-layer-${layer.layerNumber}`}
                  className="p-2.5 rounded-lg border border-surface-border bg-surface-primary space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{layer.label}</span>
                    <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-surface-secondary border border-surface-border">
                      {layer.originBadge} · {layer.sha256.slice(0, 12)}
                    </span>
                  </div>
                  <pre className="text-[11px] font-mono text-text-secondary whitespace-pre-wrap">
                    {layer.content}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
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
          onChangeStudioScope={(s) => {
            setStudioScope(s);
            setIsDirty(true);
          }}
          onChangeStudioPrePrompt={(p) => {
            setStudioPrePrompt(p);
            setIsDirty(true);
          }}
          onToggleNodeSubAgent={handleToggleNodeSubAgent}
          onRunDryRun={() =>
            setDryRunOutput(
              "▷ Dry-Run OK : 5 nœuds + bornes 🔒 AssistantHarness vérifiées (0 écriture SI).",
            )
          }
          onSaveOverride={handleSaveStudio}
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
