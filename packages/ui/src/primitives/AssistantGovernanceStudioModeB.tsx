import React from "react";
import { handleRgaaSubmitKeyDown } from "../components/RgaaModalDialog";
import type {
  AssistantGovernanceModalAndStudioLabels,
  UiAssistantStudioNode,
} from "./AssistantGovernanceModalAndStudio";

export interface AssistantGovernanceStudioModeBProps {
  readonly workspaceId: string;
  readonly studioScope: "WORKSPACE" | "TEAM";
  readonly studioPrePrompt: string;
  readonly nodes: readonly UiAssistantStudioNode[];
  readonly dryRunOutput: string | null;
  readonly resetBanner: boolean;
  readonly cancelLabel: string;
  readonly labels: AssistantGovernanceModalAndStudioLabels;
  readonly onChangeStudioScope: (scope: "WORKSPACE" | "TEAM") => void;
  readonly onChangeStudioPrePrompt: (prePrompt: string) => void;
  readonly onToggleNodeSubAgent: (nodeId: string) => void;
  readonly onRunDryRun: () => void;
  readonly onSaveOverride: () => void;
  readonly onResetDefault: () => void;
  readonly onCancel: () => void;
}

export function AssistantGovernanceStudioModeB({
  workspaceId,
  studioScope,
  studioPrePrompt,
  nodes,
  dryRunOutput,
  resetBanner,
  cancelLabel,
  labels,
  onChangeStudioScope,
  onChangeStudioPrePrompt,
  onToggleNodeSubAgent,
  onRunDryRun,
  onSaveOverride,
  onResetDefault,
  onCancel,
}: AssistantGovernanceStudioModeBProps): React.ReactElement {
  return (
    <div data-testid="assistant-governance-mode-b-studio" className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <select
          data-testid="studio-override-scope-select"
          value={studioScope}
          onChange={(e) =>
            onChangeStudioScope(e.target.value as "WORKSPACE" | "TEAM")
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
          onChange={(e) => onChangeStudioPrePrompt(e.target.value)}
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
                onClick={() => onToggleNodeSubAgent(node.nodeId)}
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

      <div className="flex items-center justify-between gap-2 pt-1 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            data-testid="studio-test-dryrun-btn"
            onClick={onRunDryRun}
            className="px-3 py-1.5 rounded border border-surface-border bg-surface-secondary font-medium"
          >
            {labels.studioTestDryRunCta}
          </button>
          <button
            type="button"
            data-testid="studio-save-override-btn"
            onClick={onSaveOverride}
            onKeyDown={(e) => handleRgaaSubmitKeyDown(e, onSaveOverride, false)}
            className="px-3 py-1.5 rounded bg-brand-primary text-surface-elevated font-medium"
          >
            {labels.studioSaveOverrideCta}
          </button>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            data-testid="studio-reset-default-btn"
            onClick={onResetDefault}
            className="px-3 py-1.5 rounded border border-surface-border bg-surface-primary text-text-secondary"
          >
            {labels.studioResetDefaultCta}
          </button>
          <button
            type="button"
            data-testid="studio-cancel-btn"
            onClick={onCancel}
            className="px-3 py-1.5 rounded border border-surface-border bg-surface-secondary text-text-primary"
          >
            {cancelLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
