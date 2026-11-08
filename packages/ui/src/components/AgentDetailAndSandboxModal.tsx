import React, { useEffect, useState } from "react";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
  UiManagedSkillItem,
} from "./AgentsAndSkillsManagerView";
import { FormattedMarkdownContent } from "./FormattedMarkdownContent";

export interface AgentDetailAndSandboxModalProps {
  readonly agent: UiManagedAgentItem | null;
  readonly skills: readonly UiManagedSkillItem[];
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly testInputValue: string;
  readonly onChangeTestInput: (agentId: string, nextValue: string) => void;
  readonly onToggleAgentSkill: (agentId: string, skillId: string, nextChecked: boolean) => void;
  readonly onExecuteAgent: (agentId: string, prompt: string) => void;
  readonly onUpdateAgentThinkingLevel?: (agentId: string, nextThinkingLevel: UiAgentThinkingLevel) => void;
  readonly onUpdateAgentVisibility?: (agentId: string, nextVisibility: UiAgentSkillVisibilityScope) => void;
  readonly onToggleAgentMcpExposure?: (agentId: string, nextExposed: boolean) => void;
  readonly onUpdateAgentDetails?: (
    agentId: string,
    patch: {
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
  const [name, setName] = useState(agent?.name ?? "");
  const [roleMission, setRoleMission] = useState(agent?.roleMission ?? "");
  const [instructions, setInstructions] = useState(agent?.instructions ?? "");
  const [savedFeedback, setSavedFeedback] = useState(false);

  useEffect(() => {
    if (agent) {
      setName(agent.name);
      setRoleMission(agent.roleMission);
      setInstructions(agent.instructions);
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
  const visibilityScope: UiAgentSkillVisibilityScope = agent.visibilityScope ?? "TEAM";

  const handleSaveDetails = () => {
    onUpdateAgentDetails?.(agent.agentId, {
      name: name.trim() || agent.name,
      roleMission: roleMission.trim() || agent.roleMission,
      instructions: instructions.trim() || agent.instructions,
      thinkingLevel: agent.thinkingLevel,
      visibilityScope: agent.visibilityScope,
      mcpExposed: agent.mcpExposed,
    });
    setSavedFeedback(true);
  };

  const handleRunAgent = () => {
    const raw = testInputValue.trim();
    const prompt = raw || `Bonjour ${agent.name}, présente ton rôle (${agent.roleMission}) et confirme que tu es prêt.`;
    if (!raw) onChangeTestInput(agent.agentId, prompt);
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
      <div className="w-[720px] max-h-[600px] flex flex-col rounded-xl border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] text-[var(--orcia-text-primary)] shadow-xl overflow-hidden text-xs">
        <header className="flex items-center justify-between border-b border-[var(--orcia-border-subtle)] px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold">⚙️ {agent.name}</h3>
            <code className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-1.5 py-0.5 font-mono text-[11px]">
              {agent.handle}
            </code>
            {savedFeedback && (
              <span className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2 py-0.5 text-[11px] font-semibold" style={{ color: "var(--color-status-success)" }}>
                ✓ Enregistré
              </span>
            )}
          </div>
          <button type="button" data-testid={`close-agent-detail-modal-btn-${agent.agentId}`} onClick={onClose} className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1 text-xs font-medium">
            Fermer (Échap)
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <label className="flex flex-col gap-1">
              <span className="font-medium">{labels.agentNameLabel}</span>
              <input type="text" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid={`edit-agent-name-input-${agent.agentId}`} value={name} disabled={isPack} onChange={(e) => setName(e.target.value)} onBlur={handleSaveDetails} className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5 disabled:opacity-50" />
            </label>

            <label className="flex flex-col gap-1">
              <span className="font-medium">{labels.agentThinkingLevelLabel}</span>
              <select
                data-testid={`modal-agent-thinking-select-${agent.agentId}`}
                value={agent.thinkingLevel}
                onChange={(e) => {
                  onUpdateAgentThinkingLevel?.(agent.agentId, e.target.value as UiAgentThinkingLevel);
                  setSavedFeedback(true);
                }}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5"
              >
                {(["simple", "medium", "complex", "auto"] as const).map((lvl) => (
                  <option key={lvl} value={lvl}>{labels.thinkingLevels[lvl]}</option>
                ))}
              </select>
            </label>

            {!isPack && (
              <label className="flex flex-col gap-1">
                <span className="font-medium">Visibilité &amp; Partage</span>
                <select
                  data-testid={`edit-agent-visibility-select-${agent.agentId}`}
                  value={visibilityScope === "PRIVATE" ? "PRIVATE" : "TEAM"}
                  onChange={(e) => {
                    onUpdateAgentVisibility?.(agent.agentId, e.target.value as UiAgentSkillVisibilityScope);
                    setSavedFeedback(true);
                  }}
                  className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5"
                >
                  <option value="TEAM">👥 Équipe / Espace</option>
                  <option value="PRIVATE">🔒 Privé</option>
                </select>
              </label>
            )}

            <label className="inline-flex items-center gap-2 self-end rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5 font-medium">
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
              <span>🔌 Exposer cet agent en MCP</span>
            </label>

            <label className="flex flex-col gap-1 md:col-span-2">
              <span className="font-medium">{labels.agentRoleLabel}</span>
              <input type="text" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid={`edit-agent-role-input-${agent.agentId}`} value={roleMission} disabled={isPack} onChange={(e) => setRoleMission(e.target.value)} onBlur={handleSaveDetails} className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5 disabled:opacity-50" />
            </label>

            <label className="flex flex-col gap-1 md:col-span-2">
              <span className="font-medium">{labels.agentInstructionsLabel}</span>
              <textarea rows={3} autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid={`edit-agent-instructions-input-${agent.agentId}`} value={instructions} disabled={isPack} onChange={(e) => setInstructions(e.target.value)} onBlur={handleSaveDetails} className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5 disabled:opacity-50" />
            </label>
          </div>

          <div className="space-y-1.5">
            <span className="font-semibold">{labels.attachedSkillsLabel}</span>
            {skills.length === 0 ? (
              <p className="text-[11px] text-[var(--orcia-text-secondary)]">{labels.noSkillsAvailableHint}</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {skills.map((sk) => {
                  const attached = agent.skillIds.includes(sk.skillId);
                  return (
                    <label key={sk.skillId} className="inline-flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1">
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
                      <span>🛠️ {sk.name} (<code className="font-mono text-[10px]">{sk.commandHandle}</code>)</span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>

          <div className="space-y-2 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3">
            <h4 className="font-semibold">▷ Tester l&apos;Agent / Dry-Run</h4>
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
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleRunAgent(); } }}
                placeholder={labels.testAgentInputPlaceholder}
                className="flex-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
              />
              <button type="button" data-testid={`run-agent-btn-${agent.agentId}`} onClick={handleRunAgent} className="rounded bg-[var(--orcia-action-primary)] px-3 py-1.5 font-semibold text-[var(--orcia-text-on-action)]">
                ⚡ {labels.runAgentButtonLabel}
              </button>
            </div>
            {agent.lastExecutionOutput && (
              <div data-testid={`agent-execution-output-${agent.agentId}`} className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2.5">
                <FormattedMarkdownContent content={agent.lastExecutionOutput} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
