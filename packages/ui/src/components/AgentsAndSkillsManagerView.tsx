import React, { useState } from "react";
import {
  AgentCreateFormDrawer,
  AgentsAndSkillsHeaderAndToolbar,
} from "./AgentAndSkillCreateForms";
import { AgentStudioCardItem } from "./AgentStudioCardItem";
import {
  matchesAgentQueryAndScope,
  matchesSkillQueryAndScope,
  SkillCreateFormDrawer,
} from "./SkillCreateFormDrawer";
import { SkillStudioCardItem } from "./SkillStudioCardItem";

export type AgentsAndSkillsSubTab = "AGENTS" | "SKILLS" | "CONNECTIONS";
export type UiAgentThinkingLevel = "simple" | "medium" | "complex" | "auto";
export type UiAgentSkillVisibilityScope = "PRIVATE" | "TEAM" | "PACK";
export type UiAgentSkillVisibilityFilter = "ALL" | UiAgentSkillVisibilityScope;

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
  readonly visibilityScope?: UiAgentSkillVisibilityScope;
  readonly sourcePackKey?: string | null;
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
  readonly visibilityScope?: UiAgentSkillVisibilityScope;
  readonly sourcePackKey?: string | null;
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
    visibilityScope?: "PRIVATE" | "TEAM";
  }) => void;
  readonly onToggleAgentSkill: (agentId: string, skillId: string, nextChecked: boolean) => void;
  readonly onExecuteAgent: (agentId: string, prompt: string) => void;
  readonly onDeleteAgent: (agentId: string) => void;
  readonly onUpdateAgentThinkingLevel?: (agentId: string, nextThinkingLevel: UiAgentThinkingLevel) => void;
  readonly onUpdateAgentVisibility?: (agentId: string, nextVisibility: UiAgentSkillVisibilityScope) => void;
  readonly onUseAgentInAssistant?: (agent: UiManagedAgentItem) => void;
  readonly onCreateSkill: (input: {
    name: string;
    objective: string;
    inputParameters: string[];
    instructions: string;
    expectedOutputFormat: string;
    visibilityScope?: "PRIVATE" | "TEAM";
  }) => void;
  readonly onExecuteSkill: (skillId: string, inputText: string) => void;
  readonly onDeleteSkill: (skillId: string) => void;
  readonly onUpdateSkillVisibility?: (skillId: string, nextVisibility: UiAgentSkillVisibilityScope) => void;
  readonly onUseSkillInAssistant?: (skill: UiManagedSkillItem) => void;
  readonly onLoadPackTemplates?: () => void;
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
  onUpdateAgentThinkingLevel,
  onUpdateAgentVisibility,
  onUseAgentInAssistant,
  onCreateSkill,
  onExecuteSkill,
  onDeleteSkill,
  onUpdateSkillVisibility,
  onUseSkillInAssistant,
  onLoadPackTemplates,
  connectionsContent,
}) => {
  const [activeTab, setActiveTab] = useState<AgentsAndSkillsSubTab>(initialTab);
  const [searchQuery, setSearchQuery] = useState("");
  const [visibilityFilter, setVisibilityFilter] = useState<UiAgentSkillVisibilityFilter>("ALL");
  const [isCreateAgentOpen, setIsCreateAgentOpen] = useState(true);
  const [isCreateSkillOpen, setIsCreateSkillOpen] = useState(true);

  const [agentName, setAgentName] = useState("");
  const [agentRole, setAgentRole] = useState("");
  const [agentInstructions, setAgentInstructions] = useState("");
  const [agentThinking, setAgentThinking] = useState<UiAgentThinkingLevel>("medium");
  const [agentVisibility, setAgentVisibility] = useState<"PRIVATE" | "TEAM">("TEAM");
  const [selectedSkillIds, setSelectedSkillIds] = useState<string[]>([]);
  const [agentTestInputs, setAgentTestInputs] = useState<Record<string, string>>({});

  const [skillName, setSkillName] = useState("");
  const [skillObjective, setSkillObjective] = useState("");
  const [skillParamsRaw, setSkillParamsRaw] = useState("");
  const [skillInstructions, setSkillInstructions] = useState("");
  const [skillOutputFormat, setSkillOutputFormat] = useState("");
  const [skillVisibility, setSkillVisibility] = useState<"PRIVATE" | "TEAM">("TEAM");
  const [skillTestInputs, setSkillTestInputs] = useState<Record<string, string>>({});

  const filteredAgents = agents.filter((ag) => matchesAgentQueryAndScope(ag, searchQuery, visibilityFilter));
  const filteredSkills = skills.filter((sk) => matchesSkillQueryAndScope(sk, searchQuery, visibilityFilter));

  const handleSubmitAgent = (e: React.FormEvent) => {
    e.preventDefault();
    if (!agentName.trim() || !agentRole.trim() || !agentInstructions.trim()) return;
    onCreateAgent({
      name: agentName.trim(),
      roleMission: agentRole.trim(),
      instructions: agentInstructions.trim(),
      thinkingLevel: agentThinking,
      skillIds: selectedSkillIds.filter((sid) => skills.some((s) => s.skillId === sid)),
      visibilityScope: agentVisibility,
    });
    setAgentName("");
    setAgentRole("");
    setAgentInstructions("");
    setSelectedSkillIds([]);
  };

  const handleSubmitSkill = (e: React.FormEvent) => {
    e.preventDefault();
    if (!skillName.trim() || !skillObjective.trim() || !skillInstructions.trim()) return;
    const parsedParams = skillParamsRaw.split(",").map((p) => p.trim()).filter(Boolean);
    onCreateSkill({
      name: skillName.trim(),
      objective: skillObjective.trim(),
      inputParameters: parsedParams,
      instructions: skillInstructions.trim(),
      expectedOutputFormat: skillOutputFormat.trim() || "Synthèse structurée",
      visibilityScope: skillVisibility,
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
      <AgentsAndSkillsHeaderAndToolbar
        labels={labels}
        activeTab={activeTab}
        agentsCount={agents.length}
        skillsCount={skills.length}
        searchQuery={searchQuery}
        visibilityFilter={visibilityFilter}
        onSelectTab={setActiveTab}
        onToggleCreateAgent={() => setIsCreateAgentOpen((prev) => !prev)}
        onToggleCreateSkill={() => setIsCreateSkillOpen((prev) => !prev)}
        onChangeSearchQuery={setSearchQuery}
        onChangeVisibilityFilter={setVisibilityFilter}
        onLoadPackTemplates={onLoadPackTemplates}
      />

      {activeTab === "AGENTS" && (
        <div data-testid="agents-subview-panel" className="space-y-4">
          <AgentCreateFormDrawer
            isOpen={isCreateAgentOpen}
            labels={labels}
            skills={skills}
            agentName={agentName}
            agentRole={agentRole}
            agentInstructions={agentInstructions}
            agentThinking={agentThinking}
            agentVisibility={agentVisibility}
            selectedSkillIds={selectedSkillIds}
            onChangeName={setAgentName}
            onChangeRole={setAgentRole}
            onChangeInstructions={setAgentInstructions}
            onChangeThinking={setAgentThinking}
            onChangeVisibility={setAgentVisibility}
            onToggleSkillId={(skillId, checked) =>
              setSelectedSkillIds((prev) => (checked ? [...prev, skillId] : prev.filter((id) => id !== skillId)))
            }
            onSubmit={handleSubmitAgent}
          />

          {filteredAgents.length === 0 ? (
            <div data-testid="agents-empty-state" className="rounded border border-dashed border-[var(--orcia-border-subtle)] p-4 text-center text-xs text-[var(--orcia-text-secondary)]">
              <strong className="block text-[var(--orcia-text-primary)]">{labels.emptyAgentsTitle}</strong>
              <span>{labels.emptyAgentsDescription}</span>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredAgents.map((ag) => (
                <AgentStudioCardItem
                  key={ag.agentId}
                  agent={ag}
                  skills={skills}
                  labels={labels}
                  testInputValue={agentTestInputs[ag.agentId] ?? ""}
                  onChangeTestInput={(agentId, val) => setAgentTestInputs((p) => ({ ...p, [agentId]: val }))}
                  onToggleAgentSkill={onToggleAgentSkill}
                  onExecuteAgent={onExecuteAgent}
                  onDeleteAgent={onDeleteAgent}
                  onUpdateAgentThinkingLevel={onUpdateAgentThinkingLevel}
                  onUpdateAgentVisibility={onUpdateAgentVisibility}
                  onUseAgentInAssistant={onUseAgentInAssistant}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "SKILLS" && (
        <div data-testid="skills-subview-panel" className="space-y-4">
          <div data-testid="skills-usage-guidance-banner" className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-2.5 text-xs text-[var(--orcia-text-secondary)]">
            {labels.skillUsageBanner}
          </div>
          <SkillCreateFormDrawer
            isOpen={isCreateSkillOpen}
            labels={labels}
            skillName={skillName}
            skillObjective={skillObjective}
            skillParamsRaw={skillParamsRaw}
            skillInstructions={skillInstructions}
            skillOutputFormat={skillOutputFormat}
            skillVisibility={skillVisibility}
            onChangeName={setSkillName}
            onChangeObjective={setSkillObjective}
            onChangeParamsRaw={setSkillParamsRaw}
            onChangeInstructions={setSkillInstructions}
            onChangeOutputFormat={setSkillOutputFormat}
            onChangeVisibility={setSkillVisibility}
            onSubmit={handleSubmitSkill}
          />

          {filteredSkills.length === 0 ? (
            <div data-testid="skills-empty-state" className="rounded border border-dashed border-[var(--orcia-border-subtle)] p-4 text-center text-xs text-[var(--orcia-text-secondary)]">
              <strong className="block text-[var(--orcia-text-primary)]">{labels.emptySkillsTitle}</strong>
              <span>{labels.emptySkillsDescription}</span>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredSkills.map((sk) => (
                <SkillStudioCardItem
                  key={sk.skillId}
                  skill={sk}
                  labels={labels}
                  testInputValue={skillTestInputs[sk.skillId] ?? ""}
                  onChangeTestInput={(skillId, val) => setSkillTestInputs((p) => ({ ...p, [skillId]: val }))}
                  onExecuteSkill={onExecuteSkill}
                  onDeleteSkill={onDeleteSkill}
                  onUpdateSkillVisibility={onUpdateSkillVisibility}
                  onUseSkillInAssistant={onUseSkillInAssistant}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "CONNECTIONS" && <div data-testid="connections-subview-panel">{connectionsContent}</div>}
    </section>
  );
};
