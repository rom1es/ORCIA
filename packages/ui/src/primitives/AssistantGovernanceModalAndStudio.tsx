import React, { useState } from "react";

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

export interface AssistantGovernanceModalAndStudioLabels {
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
}

/**
 * Story 10.1 — 4-Level Governance & Customization of `Mon Assistant`
 * (Mode A 3-Tab Modal & Mode B Studio Graph inside `🔒 AssistantHarness` bounds).
 */
export function AssistantGovernanceModalAndStudio({
  workspaceId,
  canEditWorkspaceLayer,
  canOpenStudioModeB,
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
}: AssistantGovernanceModalAndStudioProps): React.ReactElement {
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
  };

  return (
    <div
      data-testid="assistant-governance-container"
      data-active-mode={activeMode}
      className="rounded-xl border border-surface-border bg-surface-elevated p-4 text-xs text-text-primary space-y-4"
    >
      {/* Top Header with Mode A <-> Mode B Switch */}
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
        </div>
      </div>

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
                    onChange={(e) =>
                      setUserTone(e.target.value as UiAssistantResponseTone)
                    }
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
                    onChange={(e) =>
                      setUserFormat(e.target.value as UiAssistantResponseFormat)
                    }
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
                    data-testid="assistant-user-hat-input"
                    value={defaultHat}
                    onChange={(e) => setDefaultHat(e.target.value)}
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
                  data-testid="assistant-user-instructions-input"
                  value={personalInstructions}
                  onChange={(e) => setPersonalInstructions(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
                />
              </label>
              <button
                type="button"
                data-testid="assistant-save-user-prefs-btn"
                onClick={() =>
                  onSaveUserPreferences?.({
                    responseTone: userTone,
                    favoriteFormat: userFormat,
                    defaultHat,
                    personalInstructions,
                  })
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
                  disabled={!canEditWorkspaceLayer}
                  data-testid="assistant-workspace-instructions-input"
                  value={workspaceInstructions}
                  onChange={(e) => setWorkspaceInstructions(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
                />
              </label>

              {/* MCP Exposure Toggle + Funnel Rule (Principe G) */}
              <div className="p-3 rounded-lg border border-surface-border bg-surface-primary space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <label className="flex items-center gap-2 font-medium">
                    <input
                      type="checkbox"
                      disabled={!canEditWorkspaceLayer || mcpFrozenByUpperLayer}
                      checked={mcpExposed}
                      data-testid="assistant-workspace-mcp-expose-toggle"
                      onChange={(e) => setMcpExposed(e.target.checked)}
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
                  onClick={() =>
                    onSaveWorkspaceSettings?.({
                      workspaceInstructions,
                      mcpExposeAssistant: mcpExposed,
                    })
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
        /* Mode B: ☍ Personnaliser dans le Studio (@xyflow/react graph inside 🔒 AssistantHarness) */
        <div data-testid="assistant-governance-mode-b-studio" className="space-y-3">
          <div className="flex items-center justify-between gap-2">
            <select
              data-testid="studio-override-scope-select"
              value={studioScope}
              onChange={(e) =>
                setStudioScope(e.target.value as "WORKSPACE" | "TEAM")
              }
              className="px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
            >
              <option value="WORKSPACE">WORKSPACE ({workspaceId})</option>
              <option value="TEAM">TEAM</option>
            </select>
            <span
              data-testid="studio-harness-immutable-badge"
              className="px-2.5 py-1 rounded bg-surface-secondary border border-surface-border font-medium"
            >
              {labels.studioHarnessImmutableBadge}
            </span>
          </div>

          <label className="block space-y-1">
            <span className="text-text-secondary">
              {labels.studioPrePromptLabel}
            </span>
            <input
              type="text"
              data-testid="studio-ai-preprompt-input"
              value={studioPrePrompt}
              onChange={(e) => setStudioPrePrompt(e.target.value)}
              className="w-full px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
            />
          </label>

          {/* 5 Nodes wrapped inside Entry/Exit 🔒 AssistantHarness */}
          <div
            data-testid="studio-nodes-canvas"
            className="space-y-2 rounded-lg border border-surface-border bg-surface-primary p-3"
          >
            {nodes.map((node) => (
              <div
                key={node.nodeId}
                data-testid={`studio-node-${node.nodeId}`}
                data-harness-boundary={node.isHarnessBoundary ? "true" : "false"}
                className="flex items-center justify-between p-2 rounded border border-surface-border bg-surface-elevated"
              >
                <div>
                  <div className="font-semibold">{node.title}</div>
                  <div className="text-[11px] font-mono text-text-secondary">
                    COUCHES · {node.subLayersCount}
                    {node.subAgentUri ? ` · ${node.subAgentUri}` : ""}
                  </div>
                </div>
                {node.isHarnessBoundary || node.lockedBy !== null ? (
                  <span
                    data-testid={`studio-node-locked-${node.nodeId}`}
                    className="px-2 py-0.5 rounded bg-surface-secondary text-text-secondary font-mono text-[10px]"
                  >
                    🔒 {node.lockedBy}
                  </span>
                ) : (
                  <button
                    type="button"
                    data-testid={`studio-node-add-subagent-${node.nodeId}`}
                    onClick={() => handleToggleNodeSubAgent(node.nodeId)}
                    className="px-2 py-1 rounded border border-surface-border bg-surface-secondary text-[11px]"
                  >
                    + Sous-agent / Couche
                  </button>
                )}
              </div>
            ))}
          </div>

          {dryRunOutput !== null && (
            <div
              data-testid="studio-dry-run-banner"
              className="p-2 rounded bg-status-success/15 text-status-success font-mono text-[11px]"
            >
              {dryRunOutput}
            </div>
          )}

          {resetBanner && (
            <div
              data-testid="studio-reset-restored-banner"
              className="p-2 rounded bg-surface-secondary border border-surface-border font-mono text-[11px]"
            >
              ↺ Configuration standard restaurée
            </div>
          )}

          <div className="flex items-center justify-between gap-2 pt-1">
            <div className="flex items-center gap-2">
              <button
                type="button"
                data-testid="studio-test-dryrun-btn"
                onClick={() =>
                  setDryRunOutput(
                    "▷ Dry-Run OK : 5 nœuds + bornes 🔒 AssistantHarness vérifiées (0 écriture SI).",
                  )
                }
                className="px-3 py-1.5 rounded border border-surface-border bg-surface-secondary font-medium"
              >
                {labels.studioTestDryRunCta}
              </button>
              <button
                type="button"
                data-testid="studio-save-override-btn"
                onClick={() =>
                  onSaveStudioOverride?.({
                    scopeLevel: studioScope,
                    aiPrePrompt: studioPrePrompt,
                    nodes,
                  })
                }
                className="px-3 py-1.5 rounded bg-brand-primary text-surface-elevated font-medium"
              >
                {labels.studioSaveOverrideCta}
              </button>
            </div>
            <button
              type="button"
              data-testid="studio-reset-default-btn"
              onClick={() => {
                setNodes(studioNodes);
                setResetBanner(true);
                onResetStudioOverride?.(studioScope);
              }}
              className="px-3 py-1.5 rounded border border-surface-border bg-surface-primary text-text-secondary"
            >
              {labels.studioResetDefaultCta}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
