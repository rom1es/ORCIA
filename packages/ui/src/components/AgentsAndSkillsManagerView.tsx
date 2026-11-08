import React, { useState } from "react";
import {
  AgentCreateFormDrawer,
  AgentsAndSkillsHeaderAndToolbar,
} from "./AgentAndSkillCreateForms";
import { AgentDetailAndSandboxModal } from "./AgentDetailAndSandboxModal";
import { AgentStudioCardItem } from "./AgentStudioCardItem";
import {
  matchesAgentQueryAndScope,
  matchesSkillQueryAndScope,
  SkillCreateFormDrawer,
} from "./SkillCreateFormDrawer";
import { SkillDetailAndSandboxModal } from "./SkillDetailAndSandboxModal";
import { SkillStudioCardItem } from "./SkillStudioCardItem";
import { WorkspaceAssistantPinnedCard } from "./WorkspaceAssistantPinnedCard";

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
  readonly enabledOnWorkspace?: boolean;
  readonly mcpExposed?: boolean;
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
  readonly onCreateAgent: (input: { name: string; roleMission: string; instructions: string; thinkingLevel: UiAgentThinkingLevel; skillIds: string[]; visibilityScope?: "PRIVATE" | "TEAM" }) => void;
  readonly onToggleAgentSkill: (agentId: string, skillId: string, nextChecked: boolean) => void;
  readonly onExecuteAgent: (agentId: string, prompt: string) => void;
  readonly onDeleteAgent: (agentId: string) => void;
  readonly onDuplicateAgent?: (agent: UiManagedAgentItem) => void;
  readonly onToggleAgentEnabled?: (agentId: string, nextEnabled: boolean) => void;
  readonly onToggleAgentMcpExposure?: (agentId: string, nextExposed: boolean) => void;
  readonly onUpdateAgentDetails?: (agentId: string, patch: { name: string; roleMission: string; instructions: string; thinkingLevel: UiAgentThinkingLevel; visibilityScope?: UiAgentSkillVisibilityScope; mcpExposed?: boolean }) => void;
  readonly onUpdateAgentThinkingLevel?: (agentId: string, nextThinkingLevel: UiAgentThinkingLevel) => void;
  readonly onUpdateAgentVisibility?: (agentId: string, nextVisibility: UiAgentSkillVisibilityScope) => void;
  readonly onUseAgentInAssistant?: (agent: UiManagedAgentItem) => void;
  readonly onCreateSkill: (input: { name: string; objective: string; inputParameters: string[]; instructions: string; expectedOutputFormat: string; visibilityScope?: "PRIVATE" | "TEAM" }) => void;
  readonly onExecuteSkill: (skillId: string, inputText: string) => void;
  readonly onDeleteSkill: (skillId: string) => void;
  readonly onUpdateSkillVisibility?: (skillId: string, nextVisibility: UiAgentSkillVisibilityScope) => void;
  readonly onUseSkillInAssistant?: (skill: UiManagedSkillItem) => void;
  readonly onLoadPackTemplates?: () => void;
  readonly onOpenMcpTestBench?: () => void;
  readonly pinnedAssistantMcpExposed?: boolean;
  readonly onTogglePinnedAssistantMcp?: (nextExposed: boolean) => void;
  readonly onOpenAssistantSettings?: () => void;
  readonly onOpenAssistant?: () => void;
  readonly connectionsContent?: React.ReactNode;
}

export const AgentsAndSkillsManagerView: React.FC<AgentsAndSkillsManagerViewProps> = ({
  agents, skills, labels, initialTab = "AGENTS", onCreateAgent, onToggleAgentSkill, onExecuteAgent, onDeleteAgent,
  onDuplicateAgent, onToggleAgentEnabled, onToggleAgentMcpExposure, onUpdateAgentDetails, onUpdateAgentThinkingLevel,
  onUpdateAgentVisibility, onUseAgentInAssistant, onCreateSkill, onExecuteSkill, onDeleteSkill, onUpdateSkillVisibility,
  onUseSkillInAssistant, onLoadPackTemplates, onOpenMcpTestBench, pinnedAssistantMcpExposed = false,
  onTogglePinnedAssistantMcp, onOpenAssistantSettings, onOpenAssistant, connectionsContent,
}) => {
  const [activeTab, setActiveTab] = useState<AgentsAndSkillsSubTab>(initialTab);
  const [searchQuery, setSearchQuery] = useState("");
  const [visibilityFilter, setVisibilityFilter] = useState<UiAgentSkillVisibilityFilter>("ALL");
  const [isCreateAgentOpen, setIsCreateAgentOpen] = useState(false);
  const [isCreateSkillOpen, setIsCreateSkillOpen] = useState(false);
  const [activeDetailAgentId, setActiveDetailAgentId] = useState<string | null>(null);
  const [activeDetailSkillId, setActiveDetailSkillId] = useState<string | null>(null);

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

  const activeAgentsCount = agents.filter((a) => a.enabledOnWorkspace !== false).length;
  const packOrTeamAgentsCount = agents.filter((a) => (a.visibilityScope ?? "TEAM") === "PACK" || (a.visibilityScope ?? "TEAM") === "TEAM").length;
  const mcpExposedAgentsCount = agents.filter((a) => a.mcpExposed).length + (pinnedAssistantMcpExposed ? 1 : 0);

  const activeDetailAgent = agents.find((a) => a.agentId === activeDetailAgentId) ?? null;
  const activeDetailSkill = skills.find((s) => s.skillId === activeDetailSkillId) ?? null;

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
    setIsCreateAgentOpen(false);
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
    setIsCreateSkillOpen(false);
  };

  return (
    <section
      aria-label={labels.heading}
      data-testid="agents-and-skills-manager-view"
      className="space-y-4 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-4 text-[var(--orcia-text-primary)]"
    >
      <AgentsAndSkillsHeaderAndToolbar
        labels={labels} activeTab={activeTab} agentsCount={agents.length} activeAgentsCount={activeAgentsCount}
        skillsCount={skills.length} packOrTeamAgentsCount={packOrTeamAgentsCount} mcpExposedAgentsCount={mcpExposedAgentsCount}
        searchQuery={searchQuery} visibilityFilter={visibilityFilter} onSelectTab={setActiveTab}
        onToggleCreateAgent={() => setIsCreateAgentOpen((prev) => !prev)} onToggleCreateSkill={() => setIsCreateSkillOpen((prev) => !prev)}
        onOpenMcpTestBench={onOpenMcpTestBench} onChangeSearchQuery={setSearchQuery}
        onChangeVisibilityFilter={setVisibilityFilter} onLoadPackTemplates={onLoadPackTemplates}
      />

      {activeTab === "AGENTS" && (
        <div data-testid="agents-subview-panel" className="space-y-4">
          <WorkspaceAssistantPinnedCard
            mcpExposed={pinnedAssistantMcpExposed} onToggleMcpExposed={onTogglePinnedAssistantMcp}
            onOpenSettings={onOpenAssistantSettings} onOpenAssistant={onOpenAssistant}
          />
          <AgentCreateFormDrawer
            isOpen={isCreateAgentOpen} labels={labels} skills={skills} agentName={agentName} agentRole={agentRole}
            agentInstructions={agentInstructions} agentThinking={agentThinking} agentVisibility={agentVisibility}
            selectedSkillIds={selectedSkillIds} onChangeName={setAgentName} onChangeRole={setAgentRole}
            onChangeInstructions={setAgentInstructions} onChangeThinking={setAgentThinking} onChangeVisibility={setAgentVisibility}
            onToggleSkillId={(skillId, checked) => setSelectedSkillIds((prev) => (checked ? [...prev, skillId] : prev.filter((id) => id !== skillId)))}
            onSubmit={handleSubmitAgent} onClose={() => setIsCreateAgentOpen(false)}
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
                  key={ag.agentId} agent={ag} skills={skills} labels={labels} onDeleteAgent={onDeleteAgent}
                  onDuplicateAgent={onDuplicateAgent} onToggleAgentEnabled={onToggleAgentEnabled}
                  onOpenDetailModal={(item) => setActiveDetailAgentId(item.agentId)}
                  onUpdateAgentThinkingLevel={onUpdateAgentThinkingLevel}
                  onUpdateAgentVisibility={onUpdateAgentVisibility} onUseAgentInAssistant={onUseAgentInAssistant}
                />
              ))}
            </div>
          )}
          <AgentDetailAndSandboxModal
            agent={activeDetailAgent} skills={skills} labels={labels}
            testInputValue={activeDetailAgent ? (agentTestInputs[activeDetailAgent.agentId] ?? "") : ""}
            onChangeTestInput={(agentId, val) => setAgentTestInputs((p) => ({ ...p, [agentId]: val }))}
            onToggleAgentSkill={onToggleAgentSkill} onExecuteAgent={onExecuteAgent}
            onUpdateAgentThinkingLevel={onUpdateAgentThinkingLevel} onUpdateAgentVisibility={onUpdateAgentVisibility}
            onToggleAgentMcpExposure={onToggleAgentMcpExposure} onUpdateAgentDetails={onUpdateAgentDetails}
            onClose={() => setActiveDetailAgentId(null)}
          />
        </div>
      )}

      {activeTab === "SKILLS" && (
        <div data-testid="skills-subview-panel" className="space-y-4">
          <div data-testid="skills-usage-guidance-banner" className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-2.5 text-xs text-[var(--orcia-text-secondary)]">
            {labels.skillUsageBanner}
          </div>
          <SkillCreateFormDrawer
            isOpen={isCreateSkillOpen} labels={labels} skillName={skillName} skillObjective={skillObjective}
            skillParamsRaw={skillParamsRaw} skillInstructions={skillInstructions} skillOutputFormat={skillOutputFormat}
            skillVisibility={skillVisibility} onChangeName={setSkillName} onChangeObjective={setSkillObjective}
            onChangeParamsRaw={setSkillParamsRaw} onChangeInstructions={setSkillInstructions}
            onChangeOutputFormat={setSkillOutputFormat} onChangeVisibility={setSkillVisibility}
            onSubmit={handleSubmitSkill} onClose={() => setIsCreateSkillOpen(false)}
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
                  key={sk.skillId} skill={sk} labels={labels} onDeleteSkill={onDeleteSkill}
                  onOpenDetailModal={(item) => setActiveDetailSkillId(item.skillId)}
                  onUpdateSkillVisibility={onUpdateSkillVisibility} onUseSkillInAssistant={onUseSkillInAssistant}
                />
              ))}
            </div>
          )}
          <SkillDetailAndSandboxModal
            skill={activeDetailSkill} labels={labels}
            testInputValue={activeDetailSkill ? (skillTestInputs[activeDetailSkill.skillId] ?? "") : ""}
            onChangeTestInput={(skillId, val) => setSkillTestInputs((p) => ({ ...p, [skillId]: val }))}
            onExecuteSkill={onExecuteSkill} onUpdateSkillVisibility={onUpdateSkillVisibility}
            onClose={() => setActiveDetailSkillId(null)}
          />
        </div>
      )}

      {activeTab === "CONNECTIONS" && <div data-testid="connections-subview-panel">{connectionsContent}</div>}
    </section>
  );
};
