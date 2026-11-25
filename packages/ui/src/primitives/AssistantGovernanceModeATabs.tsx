import React from "react";
import { OrciaIcon } from "../components/icons";
import type {
  AssistantGovernanceModalAndStudioLabels,
  UiAssembledLayerItem,
  UiAssistantPromptTelemetryRecord,
  UiAssistantResponseFormat,
  UiAssistantResponseTone,
} from "./AssistantGovernanceTypes";
import { AssistantPromptTelemetrySection } from "./AssistantPromptTelemetrySection";

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
  readonly isDirty?: boolean;
  readonly assembledLayers: readonly UiAssembledLayerItem[];
  readonly promptTelemetryLog?: readonly UiAssistantPromptTelemetryRecord[];
  readonly labels: AssistantGovernanceModalAndStudioLabels;
  readonly onSelectTab: (tab: "USER_PREFS" | "WORKSPACE_SETTINGS" | "FULL_ASSEMBLY") => void;
  readonly onChangeTone: (tone: UiAssistantResponseTone) => void;
  readonly onChangeFormat: (format: UiAssistantResponseFormat) => void;
  readonly onChangeDefaultHat: (hat: string) => void;
  readonly onChangePersonalInstructions: (instructions: string) => void;
  readonly onChangeWorkspaceInstructions: (instructions: string) => void;
  readonly onChangeMcpExposed: (exposed: boolean) => void;
  readonly onCopyMcpConfig: () => void;
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
  isDirty = false,
  assembledLayers,
  promptTelemetryLog = [],
  labels,
  onSelectTab,
  onChangeTone,
  onChangeFormat,
  onChangeDefaultHat,
  onChangePersonalInstructions,
  onChangeWorkspaceInstructions,
  onChangeMcpExposed,
  onCopyMcpConfig,
}: AssistantGovernanceModeATabsProps): React.JSX.Element {
  return (
    <div data-testid="assistant-governance-mode-a" className="space-y-4">
      <div
        data-testid="assistant-gov-explainer-banner"
        className="rounded-lg border border-surface-border bg-surface-primary px-3 py-2 text-[11px] text-text-secondary leading-relaxed"
      >
        <OrciaIcon name="lightbulb" /> {labels.infoBannerText}
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <label className="block min-w-0 space-y-1">
              <span className="text-text-secondary">{labels.toneLabel}</span>
              <select
                data-testid="assistant-gov-tone-select"
                value={userTone}
                onChange={(e) => onChangeTone(e.target.value as UiAssistantResponseTone)}
                className="w-full min-w-0 px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
              >
                {labels.toneOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </label>

            <label className="block min-w-0 space-y-1">
              <span className="text-text-secondary">{labels.formatLabel}</span>
              <select
                data-testid="assistant-gov-format-select"
                value={userFormat}
                onChange={(e) => onChangeFormat(e.target.value as UiAssistantResponseFormat)}
                className="w-full min-w-0 px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
              >
                <option value="BULLETS_SUMMARY">{labels.formatLabels.bulletsSummary}</option>
                <option value="STRUCTURED_SECTIONS">{labels.formatLabels.structuredSections}</option>
                <option value="STEP_BY_STEP">{labels.formatLabels.stepByStep}</option>
              </select>
            </label>

            <label className="block min-w-0 space-y-1">
              <span className="text-text-secondary">{labels.defaultHatLabel}</span>
              <select
                data-testid="assistant-gov-hat-input"
                value={defaultHat}
                onChange={(e) => onChangeDefaultHat(e.target.value)}
                className="w-full min-w-0 px-2.5 py-1.5 rounded border border-surface-border bg-surface-primary"
              >
                {labels.hatOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </label>
          </div>

          <label className="block space-y-1">
            <span className="text-text-secondary">{labels.personalInstructionsLabel}</span>
            <textarea
              rows={3}
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
        </div>
      )}

      {activeTab === "WORKSPACE_SETTINGS" && (
        <div data-testid="assistant-gov-panel-workspace" className="space-y-3">
          {!canEditWorkspaceLayer && (
            <div data-testid="assistant-workspace-readonly-badge" className="p-2 rounded border border-surface-border bg-surface-secondary text-text-secondary">
              {labels.workspaceReadOnlyBadge}
            </div>
          )}
          <label className="block space-y-1">
            <span className="text-text-secondary">{labels.workspaceInstructionsLabel}{workspaceId ? ` (${workspaceId})` : ""}</span>
            <textarea
              rows={3}
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
                <span data-testid="assistant-mcp-frozen-funnel-badge" className="px-2 py-0.5 rounded bg-status-warning/15 text-status-warning font-medium text-[11px]">
                  {labels.mcpFrozenByUpperBadge}
                </span>
              )}
            </div>
            <div className="flex items-center justify-between gap-2">
              <code data-testid="assistant-mcp-config-snippet" className="text-[11px] font-mono text-text-secondary truncate">{mcpIdeConfigJson}</code>
              <button type="button" data-testid="assistant-copy-mcp-config-btn" onClick={onCopyMcpConfig} className="px-2.5 py-1 rounded border border-surface-border bg-surface-secondary shrink-0">
                {labels.copyMcpConfigCta} {copiedMcp ? <OrciaIcon name="check" /> : ""}
              </button>
            </div>
          </div>
        </div>
      )}

      {activeTab === "FULL_ASSEMBLY" && (
        <div data-testid="assistant-gov-panel-assembly" className="space-y-3">
          {isDirty && labels.unsavedAssemblyNote && (
            <div
              data-testid="assistant-gov-unsaved-assembly-note"
              role="status"
              className="rounded-lg border px-3 py-2 text-[11px]"
              style={{
                backgroundColor: "var(--color-arbitration-bg)",
                borderColor: "var(--color-arbitration-amber)",
                color: "var(--color-text-primary)",
              }}
            >
              <OrciaIcon name="warning" /> {labels.unsavedAssemblyNote}
            </div>
          )}
          <div className="space-y-2">
            {assembledLayers.map((layer) => (
              <div key={layer.layerCode} data-testid={`assembled-layer-${layer.layerNumber}`} className="p-2.5 rounded-lg border border-surface-border bg-surface-primary space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold">{layer.label}</span>
                  <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-surface-secondary border border-surface-border">
                    {layer.originBadge} · {layer.sha256.slice(0, 12)}
                  </span>
                </div>
                <pre className="text-[11px] font-mono text-text-secondary whitespace-pre-wrap">{layer.content}</pre>
              </div>
            ))}
          </div>

          <AssistantPromptTelemetrySection promptTelemetryLog={promptTelemetryLog} labels={labels} />
        </div>
      )}
    </div>
  );
}
