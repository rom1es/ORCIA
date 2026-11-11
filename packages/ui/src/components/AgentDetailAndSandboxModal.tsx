import React, { useEffect, useState } from "react";
import type {
  AgentSixBlocksDraftState,
  AgentStudioBlockKey,
} from "./AgentGovernanceTypesAndDefaults";
import {
  computeAgentReadinessChecklist,
  createDefaultAgentSixBlocksDraft,
} from "./AgentGovernanceTypesAndDefaults";
import { AgentSixBlocksEditorBody } from "./AgentSixBlocksFormSections";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
  UiManagedSkillItem,
} from "./AgentsAndSkillsManagerView";
import { FormattedMarkdownContent } from "./FormattedMarkdownContent";
import { OrciaIcon, getOrciaIconGlyph } from "./icons";

export interface AgentDetailAndSandboxModalProps {
  readonly agent: UiManagedAgentItem | null;
  readonly skills: readonly UiManagedSkillItem[];
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly testInputValue: string;
  readonly onChangeTestInput: (agentId: string, nextValue: string) => void;
  readonly onToggleAgentSkill: (agentId: string, skillId: string, nextChecked: boolean) => void;
  readonly onExecuteAgent: (agentId: string, prompt: string) => void;
  readonly onUpdateAgentThinkingLevel?: (
    agentId: string,
    nextThinkingLevel: UiAgentThinkingLevel,
  ) => void;
  readonly onUpdateAgentVisibility?: (
    agentId: string,
    nextVisibility: UiAgentSkillVisibilityScope,
  ) => void;
  readonly onToggleAgentMcpExposure?: (agentId: string, nextExposed: boolean) => void;
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
  ) => void;
  readonly onClose: () => void;
}

export const AgentDetailAndSandboxModal: React.FC<AgentDetailAndSandboxModalProps> = ({
  agent,
  skills,
  labels,
  testInputValue,
  onChangeTestInput,
  onToggleAgentSkill,
  onExecuteAgent,
  onUpdateAgentThinkingLevel,
  onUpdateAgentVisibility,
  onToggleAgentMcpExposure,
  onUpdateAgentDetails,
  onClose,
}) => {
  const [draft, setDraft] = useState<AgentSixBlocksDraftState>(() =>
    createDefaultAgentSixBlocksDraft(agent),
  );
  const [activeBlock, setActiveBlock] = useState<AgentStudioBlockKey>("A");
  const [showAllBlocks, setShowAllBlocks] = useState<boolean>(true);
  const [savedFeedback, setSavedFeedback] = useState<boolean>(false);

  useEffect(() => {
    if (agent) {
      setDraft(createDefaultAgentSixBlocksDraft(agent));
      setSavedFeedback(false);
    }
  }, [agent]);

  useEffect(() => {
    if (!agent) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [agent, onClose]);

  if (!agent) return null;

  const isPack = agent.visibilityScope === "PACK";
  const visibilityScope: UiAgentSkillVisibilityScope = draft.visibilityScope ?? "TEAM";
  const readiness = computeAgentReadinessChecklist(draft);

  const applyDraftPatch = (patch: Partial<AgentSixBlocksDraftState>) => {
    const next: AgentSixBlocksDraftState = { ...draft, ...patch };
    setDraft(next);
    setSavedFeedback(true);
    if (patch.thinkingLevel) {
      onUpdateAgentThinkingLevel?.(agent.agentId, patch.thinkingLevel);
    }
    if (patch.visibilityScope) {
      onUpdateAgentVisibility?.(agent.agentId, patch.visibilityScope);
    }
    onUpdateAgentDetails?.(agent.agentId, {
      ...next,
      name: next.name.trim() || agent.name,
      roleMission: next.roleMission.trim() || agent.roleMission,
      instructions: next.instructions.trim() || agent.instructions,
      thinkingLevel: next.thinkingLevel,
      visibilityScope: next.visibilityScope,
      mcpExposed: next.mcpExposed,
    });
  };

  const handleRunAgent = () => {
    const raw = testInputValue.trim();
    const prompt =
      raw ||
      `Bonjour ${agent.name}, présente ton rôle (${agent.roleMission}) et confirme que tu es prêt.`;
    if (!raw) onChangeTestInput(agent.agentId, prompt);
    setDraft((prev) => ({ ...prev, testBenchValidated: true }));
    onExecuteAgent(agent.agentId, prompt);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Configuration & Bac à sable — ${agent.name}`}
      data-testid={`agent-detail-modal-${agent.agentId}`}
      className="fixed inset-0 z-40 flex items-center justify-center p-4"
      style={{ backgroundColor: "var(--color-modal-backdrop)" }}
    >
      <div
        className="w-[960px] max-h-[680px] flex flex-col rounded-xl border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] text-[var(--orcia-text-primary)] shadow-xl overflow-hidden text-xs"
        style={{
          backgroundColor: "var(--color-surface-card)",
          borderColor: "var(--color-border)",
          color: "var(--color-foreground)",
        }}
      >
        <header className="flex items-center justify-between border-b border-[var(--orcia-border-subtle)] px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold">
              <OrciaIcon name="configuration" /> {agent.name}
            </h3>
            <code className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-1.5 py-0.5 font-mono text-[11px]">
              {agent.handle}
            </code>
            <span
              data-testid={`agent-bench-status-badge-${agent.agentId}`}
              className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2 py-0.5 text-[11px] font-semibold"
            >
              {draft.testBenchValidated || Boolean(agent.lastExecutionOutput)
                ? "🧪 Validé au Banc de Test"
                : "📝 À tester au Banc de Test"}
            </span>
            {savedFeedback && (
              <span
                className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2 py-0.5 text-[11px] font-semibold"
                style={{ color: "var(--color-status-success)" }}
              >
                <OrciaIcon name="check" /> Enregistré
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <label className="inline-flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1 font-medium">
              <input
                type="checkbox"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid={`agent-mcp-expose-checkbox-${agent.agentId}`}
                checked={Boolean(agent.mcpExposed)}
                onChange={(e) => {
                  onToggleAgentMcpExposure?.(agent.agentId, e.target.checked);
                  setSavedFeedback(true);
                }}
              />
              <span>
                <OrciaIcon name="plug" /> Exposer en MCP
              </span>
            </label>
            <button
              type="button"
              data-testid={`close-agent-detail-modal-btn-${agent.agentId}`}
              onClick={onClose}
              className="orcia-ds-btn orcia-ds-btn-secondary text-xs"
            >
              Fermer (Échap)
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Quick Backward-Compatible Top Controls for Existing Unit Tests */}
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3">
            <label className="flex flex-col gap-1">
              <span className="font-medium">{labels.agentNameLabel}</span>
              <input
                type="text"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid={`edit-agent-name-input-${agent.agentId}`}
                value={draft.name}
                disabled={isPack}
                onChange={(e) => applyDraftPatch({ name: e.target.value })}
                className="orcia-ds-input disabled:opacity-50"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-medium">{labels.agentThinkingLevelLabel}</span>
              <select
                data-testid={`modal-agent-thinking-select-${agent.agentId}`}
                value={draft.thinkingLevel}
                onChange={(e) =>
                  applyDraftPatch({ thinkingLevel: e.target.value as UiAgentThinkingLevel })
                }
                className="orcia-ds-select"
              >
                {(["simple", "medium", "complex", "auto"] as const).map((lvl) => (
                  <option key={lvl} value={lvl}>
                    {labels.thinkingLevels[lvl]}
                  </option>
                ))}
              </select>
            </label>
            {!isPack && (
              <label className="flex flex-col gap-1">
                <span className="font-medium">Visibilité &amp; Partage</span>
                <select
                  data-testid={`edit-agent-visibility-select-${agent.agentId}`}
                  value={visibilityScope === "PRIVATE" ? "PRIVATE" : "TEAM"}
                  onChange={(e) =>
                    applyDraftPatch({
                      visibilityScope: e.target.value as UiAgentSkillVisibilityScope,
                    })
                  }
                  className="orcia-ds-select"
                >
                  <option value="TEAM">{getOrciaIconGlyph("team")} Équipe / Espace</option>
                  <option value="PRIVATE">{getOrciaIconGlyph("lock")} Privé</option>
                </select>
              </label>
            )}
            <label className="flex flex-col gap-1">
              <span className="font-medium">{labels.agentRoleLabel}</span>
              <input
                type="text"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid={`edit-agent-role-input-${agent.agentId}`}
                value={draft.roleMission}
                disabled={isPack}
                onChange={(e) => applyDraftPatch({ roleMission: e.target.value })}
                className="orcia-ds-input disabled:opacity-50"
              />
            </label>
            <label className="flex flex-col gap-1 md:col-span-2">
              <span className="font-medium">{labels.agentInstructionsLabel}</span>
              <textarea
                rows={2}
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid={`edit-agent-instructions-input-${agent.agentId}`}
                value={draft.instructions}
                disabled={isPack}
                onChange={(e) => applyDraftPatch({ instructions: e.target.value })}
                className="orcia-ds-textarea disabled:opacity-50"
              />
            </label>
          </div>

          {/* 1-Click Skill Attachment */}
          <div className="space-y-1.5">
            <span className="font-semibold">{labels.attachedSkillsLabel}</span>
            {skills.length === 0 ? (
              <p className="text-[11px] text-[var(--orcia-text-secondary)]">
                {labels.noSkillsAvailableHint}
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {skills.map((sk) => {
                  const attached = agent.skillIds.includes(sk.skillId);
                  return (
                    <label
                      key={sk.skillId}
                      className="inline-flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1"
                    >
                      <input
                        type="checkbox"
                        autoComplete="off"
                        data-lpignore="true"
                        data-1p-ignore="true"
                        data-bwignore="true"
                        data-form-type="other"
                        data-testid={`agent-attach-skill-${agent.agentId}-${sk.skillId}`}
                        checked={attached}
                        onChange={(e) => {
                          onToggleAgentSkill(agent.agentId, sk.skillId, e.target.checked);
                          setSavedFeedback(true);
                        }}
                      />
                      <span>
                        <OrciaIcon name="tools" /> {sk.name} (
                        <code className="font-mono text-[10px]">{sk.commandHandle}</code>)
                      </span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>

          {/* Integrated 6-Block Governance Inspector & Editor */}
          <AgentSixBlocksEditorBody
            draft={draft}
            labels={labels}
            skills={skills}
            activeBlock={activeBlock}
            showAllBlocks={showAllBlocks}
            readOnlyIdentity={isPack}
            testIdPrefix={`detail-${agent.agentId}`}
            onSelectBlock={(blk) => {
              setActiveBlock(blk);
              setShowAllBlocks(false);
            }}
            onToggleShowAllBlocks={() => setShowAllBlocks((p) => !p)}
            onChangeDraft={applyDraftPatch}
            onToggleSkillId={(skillId, checked) => {
              onToggleAgentSkill(agent.agentId, skillId, checked);
              setSavedFeedback(true);
            }}
          />

          {/* Condition 1: Integrated Test Bench & Dry-Run Validation */}
          <div className="space-y-2 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h4 className="font-semibold">
                <OrciaIcon name="playOutline" /> Banc de Test Intégré (Dry-Run &amp; Validation pour « 💬 Mon Assistant »)
              </h4>
              <span className="text-[11px] text-[var(--orcia-text-secondary)]">
                Conditions réunies : {readiness.filter((r) => r.satisfied).length}/6
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              <input
                type="text"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid={`agent-test-input-${agent.agentId}`}
                value={testInputValue}
                onChange={(e) => onChangeTestInput(agent.agentId, e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleRunAgent();
                  }
                }}
                placeholder={labels.testAgentInputPlaceholder}
                className="orcia-ds-input flex-1"
              />
              <button
                type="button"
                data-testid={`run-agent-btn-${agent.agentId}`}
                onClick={handleRunAgent}
                className="orcia-ds-btn orcia-ds-btn-primary text-xs"
              >
                <OrciaIcon name="lightning" /> {labels.runAgentButtonLabel}
              </button>
            </div>
            {agent.lastExecutionOutput && (
              <div
                data-testid={`agent-execution-output-${agent.agentId}`}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2.5"
              >
                <FormattedMarkdownContent content={agent.lastExecutionOutput} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
