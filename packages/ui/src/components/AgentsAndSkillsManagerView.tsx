import React, { useState } from "react";

export type AgentsAndSkillsSubTab = "AGENTS" | "SKILLS" | "CONNECTIONS";
export type UiAgentThinkingLevel = "simple" | "medium" | "complex" | "auto";

export interface UiManagedSkillItem {
  readonly skillId: string;
  readonly slug: string;
  readonly commandHandle: string;
  readonly name: string;
  readonly objective: string;
  readonly inputParameters: readonly string[];
  readonly instructions: string;
  readonly expectedOutputFormat: string;
  readonly lastExecutionOutput?: string | null;
}

export interface UiManagedAgentItem {
  readonly agentId: string;
  readonly slug: string;
  readonly handle: string;
  readonly name: string;
  readonly roleMission: string;
  readonly instructions: string;
  readonly thinkingLevel: UiAgentThinkingLevel;
  readonly skillIds: readonly string[];
  readonly lastExecutionOutput?: string | null;
  readonly lastInvokedSkills?: readonly string[];
}

export interface AgentsAndSkillsManagerLabels {
  readonly heading: string;
  readonly subtitle: string;
  readonly tabAgents: string;
  readonly tabSkills: string;
  readonly tabConnections: string;
  readonly emptyAgentsTitle: string;
  readonly emptyAgentsDescription: string;
  readonly emptySkillsTitle: string;
  readonly emptySkillsDescription: string;
  readonly createAgentSectionTitle: string;
  readonly agentNameLabel: string;
  readonly agentNamePlaceholder: string;
  readonly agentRoleLabel: string;
  readonly agentRolePlaceholder: string;
  readonly agentInstructionsLabel: string;
  readonly agentInstructionsPlaceholder: string;
  readonly agentThinkingLevelLabel: string;
  readonly thinkingLevels: Record<UiAgentThinkingLevel, string>;
  readonly attachedSkillsLabel: string;
  readonly noSkillsAvailableHint: string;
  readonly createAgentButtonLabel: string;
  readonly testAgentInputPlaceholder: string;
  readonly runAgentButtonLabel: string;
  readonly deleteAgentButtonLabel: string;
  readonly mobilizedSkillsLabel: string;
  readonly createSkillSectionTitle: string;
  readonly skillUsageBanner: string;
  readonly skillNameLabel: string;
  readonly skillNamePlaceholder: string;
  readonly skillObjectiveLabel: string;
  readonly skillObjectivePlaceholder: string;
  readonly skillParamsLabel: string;
  readonly skillParamsPlaceholder: string;
  readonly skillInstructionsLabel: string;
  readonly skillInstructionsPlaceholder: string;
  readonly skillOutputFormatLabel: string;
  readonly skillOutputFormatPlaceholder: string;
  readonly createSkillButtonLabel: string;
  readonly testSkillInputPlaceholder: string;
  readonly runSkillButtonLabel: string;
  readonly deleteSkillButtonLabel: string;
}

export interface AgentsAndSkillsManagerViewProps {
  readonly agents: readonly UiManagedAgentItem[];
  readonly skills: readonly UiManagedSkillItem[];
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly initialTab?: AgentsAndSkillsSubTab;
  readonly onCreateAgent: (input: {
    name: string;
    roleMission: string;
    instructions: string;
    thinkingLevel: UiAgentThinkingLevel;
    skillIds: string[];
  }) => void;
  readonly onToggleAgentSkill: (agentId: string, skillId: string, nextChecked: boolean) => void;
  readonly onExecuteAgent: (agentId: string, prompt: string) => void;
  readonly onDeleteAgent: (agentId: string) => void;
  readonly onCreateSkill: (input: {
    name: string;
    objective: string;
    inputParameters: string[];
    instructions: string;
    expectedOutputFormat: string;
  }) => void;
  readonly onExecuteSkill: (skillId: string, inputText: string) => void;
  readonly onDeleteSkill: (skillId: string) => void;
  readonly connectionsContent?: React.ReactNode;
}

export const AgentsAndSkillsManagerView: React.FC<AgentsAndSkillsManagerViewProps> = ({
  agents,
  skills,
  labels,
  initialTab = "AGENTS",
  onCreateAgent,
  onToggleAgentSkill,
  onExecuteAgent,
  onDeleteAgent,
  onCreateSkill,
  onExecuteSkill,
  onDeleteSkill,
  connectionsContent,
}) => {
  const [activeTab, setActiveTab] = useState<AgentsAndSkillsSubTab>(initialTab);
  const [agentName, setAgentName] = useState("");
  const [agentRole, setAgentRole] = useState("");
  const [agentInstructions, setAgentInstructions] = useState("");
  const [agentThinking, setAgentThinking] = useState<UiAgentThinkingLevel>("medium");
  const [selectedSkillIds, setSelectedSkillIds] = useState<string[]>([]);
  const [agentTestInputs, setAgentTestInputs] = useState<Record<string, string>>({});

  const [skillName, setSkillName] = useState("");
  const [skillObjective, setSkillObjective] = useState("");
  const [skillParamsRaw, setSkillParamsRaw] = useState("");
  const [skillInstructions, setSkillInstructions] = useState("");
  const [skillOutputFormat, setSkillOutputFormat] = useState("");
  const [skillTestInputs, setSkillTestInputs] = useState<Record<string, string>>({});

  const handleSubmitAgent = (e: React.FormEvent) => {
    e.preventDefault();
    if (!agentName.trim() || !agentRole.trim() || !agentInstructions.trim()) return;
    onCreateAgent({
      name: agentName.trim(),
      roleMission: agentRole.trim(),
      instructions: agentInstructions.trim(),
      thinkingLevel: agentThinking,
      skillIds: selectedSkillIds.filter((sid) => skills.some((s) => s.skillId === sid)),
    });
    setAgentName("");
    setAgentRole("");
    setAgentInstructions("");
    setSelectedSkillIds([]);
  };

  const handleSubmitSkill = (e: React.FormEvent) => {
    e.preventDefault();
    if (!skillName.trim() || !skillObjective.trim() || !skillInstructions.trim()) return;
    const parsedParams = skillParamsRaw
      .split(",")
      .map((p) => p.trim())
      .filter(Boolean);
    onCreateSkill({
      name: skillName.trim(),
      objective: skillObjective.trim(),
      inputParameters: parsedParams,
      instructions: skillInstructions.trim(),
      expectedOutputFormat: skillOutputFormat.trim() || "Synthèse structurée",
    });
    setSkillName("");
    setSkillObjective("");
    setSkillParamsRaw("");
    setSkillInstructions("");
    setSkillOutputFormat("");
  };

  return (
    <section
      aria-label={labels.heading}
      data-testid="agents-and-skills-manager-view"
      className="space-y-4 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-4 text-[var(--orcia-text-primary)]"
    >
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--orcia-border-subtle)] pb-3">
        <div>
          <h2 className="text-base font-semibold">{labels.heading}</h2>
          <p className="text-xs text-[var(--orcia-text-secondary)]">{labels.subtitle}</p>
        </div>
        <div role="tablist" className="orcia-ds-tabs">
          {(
            [
              ["AGENTS", "agents-subview-tab-agents", `${labels.tabAgents} (${agents.length})`],
              ["SKILLS", "agents-subview-tab-skills", `${labels.tabSkills} (${skills.length})`],
              ["CONNECTIONS", "agents-subview-tab-connections", labels.tabConnections],
            ] as const
          ).map(([tabKey, testId, tabLabel]) => (
            <button
              key={tabKey}
              type="button"
              role="tab"
              aria-selected={activeTab === tabKey}
              data-testid={testId}
              onClick={() => setActiveTab(tabKey)}
              className="orcia-ds-tab"
            >
              {tabLabel}
            </button>
          ))}
        </div>
      </header>

      {activeTab === "AGENTS" && (
        <div data-testid="agents-subview-panel" className="space-y-4">
          <form
            onSubmit={handleSubmitAgent}
            autoComplete="off"
            data-lpignore="true"
            data-form-type="other"
            data-testid="create-agent-form"
            className="grid grid-cols-1 gap-3 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3 text-xs md:grid-cols-2"
          >
            <h3 className="font-semibold md:col-span-2">{labels.createAgentSectionTitle}</h3>
            <label className="flex flex-col gap-1">
              <span>{labels.agentNameLabel}</span>
              <input
                type="text"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="agent-name-input"
                value={agentName}
                onChange={(e) => setAgentName(e.target.value)}
                placeholder={labels.agentNamePlaceholder}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span>{labels.agentThinkingLevelLabel}</span>
              <select
                data-testid="agent-thinking-level-select"
                value={agentThinking}
                onChange={(e) => setAgentThinking(e.target.value as UiAgentThinkingLevel)}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
              >
                {(["simple", "medium", "complex", "auto"] as const).map((lvl) => (
                  <option key={lvl} value={lvl}>
                    {labels.thinkingLevels[lvl]}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 md:col-span-2">
              <span>{labels.agentRoleLabel}</span>
              <input
                type="text"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="agent-role-input"
                value={agentRole}
                onChange={(e) => setAgentRole(e.target.value)}
                placeholder={labels.agentRolePlaceholder}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
              />
            </label>
            <label className="flex flex-col gap-1 md:col-span-2">
              <span>{labels.agentInstructionsLabel}</span>
              <textarea
                rows={2}
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="agent-instructions-input"
                value={agentInstructions}
                onChange={(e) => setAgentInstructions(e.target.value)}
                placeholder={labels.agentInstructionsPlaceholder}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
              />
            </label>
            <div className="space-y-1 md:col-span-2">
              <span className="font-medium">{labels.attachedSkillsLabel}</span>
              {skills.length === 0 ? (
                <p className="text-[11px] text-[var(--orcia-text-secondary)]">
                  {labels.noSkillsAvailableHint}
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {skills.map((sk) => {
                    const checked = selectedSkillIds.includes(sk.skillId);
                    return (
                      <label
                        key={sk.skillId}
                        className="inline-flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-1"
                      >
                        <input
                          type="checkbox"
                          autoComplete="off"
                          data-lpignore="true"
                          data-1p-ignore="true"
                          data-bwignore="true"
                          data-form-type="other"
                          data-testid={`create-agent-skill-checkbox-${sk.skillId}`}
                          checked={checked}
                          onChange={(e) =>
                            setSelectedSkillIds((prev) =>
                              e.target.checked
                                ? [...prev, sk.skillId]
                                : prev.filter((id) => id !== sk.skillId),
                            )
                          }
                        />
                        <span>
                          {sk.name} (<code>{sk.commandHandle}</code>)
                        </span>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="md:col-span-2">
              <button
                type="submit"
                data-testid="create-agent-submit-btn"
                disabled={!agentName.trim() || !agentRole.trim() || !agentInstructions.trim()}
                className="rounded bg-[var(--orcia-action-primary)] px-3 py-1.5 text-xs font-semibold text-[var(--orcia-text-on-action)] disabled:opacity-50"
              >
                {labels.createAgentButtonLabel}
              </button>
            </div>
          </form>

          {agents.length === 0 ? (
            <div
              data-testid="agents-empty-state"
              className="rounded border border-dashed border-[var(--orcia-border-subtle)] p-4 text-center text-xs text-[var(--orcia-text-secondary)]"
            >
              <strong className="block text-[var(--orcia-text-primary)]">
                {labels.emptyAgentsTitle}
              </strong>
              <span>{labels.emptyAgentsDescription}</span>
            </div>
          ) : (
            <div className="space-y-3">
              {agents.map((ag) => (
                <div
                  key={ag.agentId}
                  data-testid={`agent-card-${ag.agentId}`}
                  className="space-y-2 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3 text-xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <strong className="text-sm">{ag.name}</strong>{" "}
                      <code className="font-mono text-[11px]">{ag.handle}</code>
                      <span className="ml-2 rounded border border-[var(--orcia-border-subtle)] px-1.5 py-0.5 text-[11px]">
                        {labels.thinkingLevels[ag.thinkingLevel]}
                      </span>
                    </div>
                    <button
                      type="button"
                      data-testid={`delete-agent-btn-${ag.agentId}`}
                      onClick={() => onDeleteAgent(ag.agentId)}
                      className="rounded border border-[var(--orcia-border-subtle)] px-2 py-1 text-[11px]"
                    >
                      {labels.deleteAgentButtonLabel}
                    </button>
                  </div>
                  <p className="text-[var(--orcia-text-secondary)]">{ag.roleMission}</p>
                  {skills.length > 0 && (
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <span className="font-medium">{labels.attachedSkillsLabel} :</span>
                      {skills.map((sk) => {
                        const attached = ag.skillIds.includes(sk.skillId);
                        return (
                          <label
                            key={sk.skillId}
                            className="inline-flex items-center gap-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5"
                          >
                            <input
                              type="checkbox"
                              autoComplete="off"
                              data-lpignore="true"
                              data-1p-ignore="true"
                              data-bwignore="true"
                              data-form-type="other"
                              data-testid={`agent-attach-skill-${ag.agentId}-${sk.skillId}`}
                              checked={attached}
                              onChange={(e) =>
                                onToggleAgentSkill(ag.agentId, sk.skillId, e.target.checked)
                              }
                            />
                            <span>{sk.name}</span>
                          </label>
                        );
                      })}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-2 pt-1">
                    <input
                      type="text"
                      autoComplete="off"
                      data-lpignore="true"
                      data-1p-ignore="true"
                      data-bwignore="true"
                      data-form-type="other"
                      data-testid={`agent-test-input-${ag.agentId}`}
                      value={agentTestInputs[ag.agentId] ?? ""}
                      onChange={(e) =>
                        setAgentTestInputs((p) => ({ ...p, [ag.agentId]: e.target.value }))
                      }
                      placeholder={labels.testAgentInputPlaceholder}
                      className="flex-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1"
                    />
                    <button
                      type="button"
                      data-testid={`run-agent-btn-${ag.agentId}`}
                      onClick={() => {
                        const prompt = (agentTestInputs[ag.agentId] ?? "").trim();
                        if (prompt) onExecuteAgent(ag.agentId, prompt);
                      }}
                      className="rounded bg-[var(--orcia-action-primary)] px-3 py-1 font-semibold text-[var(--orcia-text-on-action)]"
                    >
                      {labels.runAgentButtonLabel}
                    </button>
                  </div>
                  {ag.lastExecutionOutput && (
                    <pre
                      data-testid={`agent-execution-output-${ag.agentId}`}
                      className="whitespace-pre-wrap rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2 font-mono text-[11px]"
                    >
                      {ag.lastExecutionOutput}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "SKILLS" && (
        <div data-testid="skills-subview-panel" className="space-y-4">
          <div
            data-testid="skills-usage-guidance-banner"
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-2.5 text-xs text-[var(--orcia-text-secondary)]"
          >
            {labels.skillUsageBanner}
          </div>
          <form
            onSubmit={handleSubmitSkill}
            autoComplete="off"
            data-lpignore="true"
            data-form-type="other"
            data-testid="create-skill-form"
            className="grid grid-cols-1 gap-3 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3 text-xs md:grid-cols-2"
          >
            <h3 className="font-semibold md:col-span-2">{labels.createSkillSectionTitle}</h3>
            <label className="flex flex-col gap-1">
              <span>{labels.skillNameLabel}</span>
              <input
                type="text"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="skill-name-input"
                value={skillName}
                onChange={(e) => setSkillName(e.target.value)}
                placeholder={labels.skillNamePlaceholder}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span>{labels.skillOutputFormatLabel}</span>
              <input
                type="text"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="skill-output-format-input"
                value={skillOutputFormat}
                onChange={(e) => setSkillOutputFormat(e.target.value)}
                placeholder={labels.skillOutputFormatPlaceholder}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span>{labels.skillObjectiveLabel}</span>
              <input
                type="text"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="skill-objective-input"
                value={skillObjective}
                onChange={(e) => setSkillObjective(e.target.value)}
                placeholder={labels.skillObjectivePlaceholder}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span>{labels.skillParamsLabel}</span>
              <input
                type="text"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="skill-params-input"
                value={skillParamsRaw}
                onChange={(e) => setSkillParamsRaw(e.target.value)}
                placeholder={labels.skillParamsPlaceholder}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
              />
            </label>
            <label className="flex flex-col gap-1 md:col-span-2">
              <span>{labels.skillInstructionsLabel}</span>
              <textarea
                rows={2}
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="skill-instructions-input"
                value={skillInstructions}
                onChange={(e) => setSkillInstructions(e.target.value)}
                placeholder={labels.skillInstructionsPlaceholder}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
              />
            </label>
            <div className="md:col-span-2">
              <button
                type="submit"
                data-testid="create-skill-submit-btn"
                disabled={!skillName.trim() || !skillObjective.trim() || !skillInstructions.trim()}
                className="rounded bg-[var(--orcia-action-primary)] px-3 py-1.5 text-xs font-semibold text-[var(--orcia-text-on-action)] disabled:opacity-50"
              >
                {labels.createSkillButtonLabel}
              </button>
            </div>
          </form>

          {skills.length === 0 ? (
            <div
              data-testid="skills-empty-state"
              className="rounded border border-dashed border-[var(--orcia-border-subtle)] p-4 text-center text-xs text-[var(--orcia-text-secondary)]"
            >
              <strong className="block text-[var(--orcia-text-primary)]">
                {labels.emptySkillsTitle}
              </strong>
              <span>{labels.emptySkillsDescription}</span>
            </div>
          ) : (
            <div className="space-y-3">
              {skills.map((sk) => (
                <div
                  key={sk.skillId}
                  data-testid={`skill-card-${sk.skillId}`}
                  className="space-y-2 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3 text-xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <strong className="text-sm">{sk.name}</strong>{" "}
                      <code
                        data-testid={`skill-command-handle-${sk.skillId}`}
                        className="font-mono text-[11px]"
                      >
                        {sk.commandHandle}
                      </code>
                    </div>
                    <button
                      type="button"
                      data-testid={`delete-skill-btn-${sk.skillId}`}
                      onClick={() => onDeleteSkill(sk.skillId)}
                      className="rounded border border-[var(--orcia-border-subtle)] px-2 py-1 text-[11px]"
                    >
                      {labels.deleteSkillButtonLabel}
                    </button>
                  </div>
                  <p className="text-[var(--orcia-text-secondary)]">{sk.objective}</p>
                  <div className="flex flex-wrap gap-2 pt-1">
                    <input
                      type="text"
                      autoComplete="off"
                      data-lpignore="true"
                      data-1p-ignore="true"
                      data-bwignore="true"
                      data-form-type="other"
                      data-testid={`skill-test-input-${sk.skillId}`}
                      value={skillTestInputs[sk.skillId] ?? ""}
                      onChange={(e) =>
                        setSkillTestInputs((p) => ({ ...p, [sk.skillId]: e.target.value }))
                      }
                      placeholder={labels.testSkillInputPlaceholder}
                      className="flex-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1"
                    />
                    <button
                      type="button"
                      data-testid={`run-skill-btn-${sk.skillId}`}
                      onClick={() => {
                        const txt = (skillTestInputs[sk.skillId] ?? "").trim();
                        if (txt) onExecuteSkill(sk.skillId, txt);
                      }}
                      className="rounded bg-[var(--orcia-action-primary)] px-3 py-1 font-semibold text-[var(--orcia-text-on-action)]"
                    >
                      {labels.runSkillButtonLabel}
                    </button>
                  </div>
                  {sk.lastExecutionOutput && (
                    <pre
                      data-testid={`skill-execution-output-${sk.skillId}`}
                      className="whitespace-pre-wrap rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2 font-mono text-[11px]"
                    >
                      {sk.lastExecutionOutput}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "CONNECTIONS" && (
        <div data-testid="connections-subview-panel">{connectionsContent}</div>
      )}
    </section>
  );
};
