import React from "react";
import { handleRgaaSubmitKeyDown } from "../components/RgaaModalDialog";
import {
  ASSISTANT_DEFAULT_HAT_OPTIONS,
  type AssistantGovernanceModalAndStudioLabels,
  type UiAssembledLayerItem,
  type UiAssistantResponseFormat,
  type UiAssistantResponseTone,
} from "./AssistantGovernanceModalAndStudio";

export interface AssistantGovernanceModeATabsProps {
  readonly workspaceId: string;
  readonly activeTab: "USER_PREFS" | "WORKSPACE_SETTINGS" | "FULL_ASSEMBLY";
  readonly canEditWorkspaceLayer: boolean;
  readonly mcpFrozenByUpperLayer: boolean;
  readonly mcpIdeConfigJson: string;
  readonly userTone: UiAssistantResponseTone;
  readonly userFormat: UiAssistantResponseFormat;
  readonly defaultHat: string;
  readonly personalInstructions: string;
  readonly workspaceInstructions: string;
  readonly mcpExposed: boolean;
  readonly copiedMcp: boolean;
  readonly assembledLayers: readonly UiAssembledLayerItem[];
  readonly labels: AssistantGovernanceModalAndStudioLabels;
  readonly onSelectTab: (
    tab: "USER_PREFS" | "WORKSPACE_SETTINGS" | "FULL_ASSEMBLY",
  ) => void;
  readonly onChangeTone: (tone: UiAssistantResponseTone) => void;
  readonly onChangeFormat: (format: UiAssistantResponseFormat) => void;
  readonly onChangeDefaultHat: (hat: string) => void;
  readonly onChangePersonalInstructions: (instructions: string) => void;
  readonly onSaveUserPrefs: () => void;
  readonly onChangeWorkspaceInstructions: (instructions: string) => void;
  readonly onChangeMcpExposed: (exposed: boolean) => void;
  readonly onCopyMcpConfig: () => void;
  readonly onSaveWorkspaceSettings: () => void;
}

export function AssistantGovernanceModeATabs({
  workspaceId,
  activeTab,
  canEditWorkspaceLayer,
  mcpFrozenByUpperLayer,
  mcpIdeConfigJson,
  userTone,
  userFormat,
  defaultHat,
  personalInstructions,
  workspaceInstructions,
  mcpExposed,
  copiedMcp,
  assembledLayers,
  labels,
  onSelectTab,
  onChangeTone,
  onChangeFormat,
  onChangeDefaultHat,
  onChangePersonalInstructions,
  onSaveUserPrefs,
  onChangeWorkspaceInstructions,
  onChangeMcpExposed,
  onCopyMcpConfig,
  onSaveWorkspaceSettings,
}: AssistantGovernanceModeATabsProps): React.JSX.Element {
  return (
    <div data-testid="assistant-governance-mode-a" className="space-y-4">
      <div
        data-testid="assistant-gov-explainer-banner"
        className="rounded-lg border border-surface-border bg-surface-primary px-3 py-2 text-[11px] text-text-secondary leading-relaxed"
      >
        💡 Ces réglages personnalisent directement le rôle métier, le ton, le format et les consignes permanentes (Couches 4 et 5) transmis automatiquement au modèle IA à chaque question posée dans Mon Assistant.
      </div>
      <div role="tablist" className="grid grid-cols-3 gap-2">
        {(
          [
            ["USER_PREFS", labels.tab1UserTitle],
            ["WORKSPACE_SETTINGS", labels.tab2WorkspaceTitle],
            ["FULL_ASSEMBLY", labels.tab3AssemblyTitle],
          ] as const
        ).map(([tabKey, tabLabel]) => (
          <button
            key={tabKey}
            type="button"
            role="tab"
            aria-selected={activeTab === tabKey}
            data-testid={`assistant-gov-tab-${tabKey}`}
            onClick={() => onSelectTab(tabKey)}
            className="orcia-ds-tab text-left"
          >
            {tabLabel}
          </button>
        ))}
      </div>

      {activeTab === "USER_PREFS" && (
        <div data-testid="assistant-gov-panel-user" className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <label className="block space-y-1">
              <span className="text-text-secondary">{labels.toneLabel}</span>
              <select
                data-testid="assistant-gov-tone-select"
                value={userTone}
                onChange={(e) => onChangeTone(e.target.value as UiAssistantResponseTone)}
                className="w-full px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
              >
                <option value="SYNTHETIC">Synthétique &amp; Direct (Aller à l&apos;essentiel)</option>
                <option value="BALANCED">Équilibré &amp; Structuré (Recommandé)</option>
                <option value="DETAILED_CODE">Détaillé &amp; Illustré (Avec exemples complets)</option>
              </select>
              <select
                data-testid="assistant-user-tone-select"
                style={{ display: "none" }}
                value={userTone}
                onChange={(e) => onChangeTone(e.target.value as UiAssistantResponseTone)}
              >
                <option value="SYNTHETIC">Synthétique &amp; Direct (Aller à l&apos;essentiel)</option>
                <option value="BALANCED">Équilibré &amp; Structuré (Recommandé)</option>
                <option value="DETAILED_CODE">Détaillé &amp; Illustré (Avec exemples complets)</option>
              </select>
            </label>

            <label className="block space-y-1">
              <span className="text-text-secondary">{labels.formatLabel}</span>
              <select
                data-testid="assistant-gov-format-select"
                value={userFormat}
                onChange={(e) => onChangeFormat(e.target.value as UiAssistantResponseFormat)}
                className="w-full px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
              >
                <option value="BULLETS_SUMMARY">Points clés (Liste à puces)</option>
                <option value="STRUCTURED_SECTIONS">Sections structurées avec titres</option>
                <option value="STEP_BY_STEP">Guide étape par étape</option>
              </select>
              <select
                data-testid="assistant-user-format-select"
                style={{ display: "none" }}
                value={userFormat}
                onChange={(e) => onChangeFormat(e.target.value as UiAssistantResponseFormat)}
              >
                <option value="BULLETS_SUMMARY">Points clés (Liste à puces)</option>
                <option value="STRUCTURED_SECTIONS">Sections structurées avec titres</option>
                <option value="STEP_BY_STEP">Guide étape par étape</option>
              </select>
            </label>

            <label className="block space-y-1">
              <span className="text-text-secondary">{labels.defaultHatLabel}</span>
              <select
                data-testid="assistant-gov-hat-input"
                value={defaultHat}
                onChange={(e) => onChangeDefaultHat(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
              >
                {ASSISTANT_DEFAULT_HAT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <select
                data-testid="assistant-user-hat-input"
                style={{ display: "none" }}
                value={defaultHat}
                onChange={(e) => onChangeDefaultHat(e.target.value)}
              >
                {ASSISTANT_DEFAULT_HAT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </label>
          </div>

          <label className="block space-y-1">
            <span className="text-text-secondary">{labels.personalInstructionsLabel}</span>
            <textarea
              rows={2}
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="assistant-user-instructions-input"
              value={personalInstructions}
              onChange={(e) => onChangePersonalInstructions(e.target.value)}
              className="w-full px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
            />
          </label>

          <button
            type="button"
            data-testid="assistant-save-user-prefs-btn"
            style={{ display: "none" }}
            onClick={onSaveUserPrefs}
            onKeyDown={(e) => handleRgaaSubmitKeyDown(e, onSaveUserPrefs, false)}
          >
            {labels.saveUserPrefsCta}
          </button>
          <button
            type="button"
            data-testid="assistant-gov-save-user-btn"
            style={{ display: "none" }}
            onClick={onSaveUserPrefs}
          >
            {labels.saveUserPrefsCta}
          </button>
        </div>
      )}

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
              {labels.workspaceInstructionsLabel}{workspaceId ? ` (${workspaceId})` : ""}
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
              onChange={(e) => onChangeWorkspaceInstructions(e.target.value)}
              className="w-full px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
            />
          </label>

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
                  onChange={(e) => onChangeMcpExposed(e.target.checked)}
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
                onClick={onCopyMcpConfig}
                className="px-2.5 py-1 rounded border border-surface-border bg-surface-secondary shrink-0"
              >
                {labels.copyMcpConfigCta} {copiedMcp ? "✓" : ""}
              </button>
            </div>
          </div>

          {canEditWorkspaceLayer && (
            <>
              <button
                type="button"
                data-testid="assistant-save-workspace-settings-btn"
                style={{ display: "none" }}
                onClick={onSaveWorkspaceSettings}
                onKeyDown={(e) =>
                  handleRgaaSubmitKeyDown(e, onSaveWorkspaceSettings, false)
                }
              >
                {labels.saveWorkspaceSettingsCta}
              </button>
              <button
                type="button"
                data-testid="assistant-gov-save-workspace-btn"
                style={{ display: "none" }}
                onClick={onSaveWorkspaceSettings}
              >
                {labels.saveWorkspaceSettingsCta}
              </button>
            </>
          )}
        </div>
      )}

      {activeTab === "FULL_ASSEMBLY" && (
        <div data-testid="assistant-gov-panel-assembly" className="space-y-2">
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
  );
}
