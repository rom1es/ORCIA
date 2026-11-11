import React, { useState } from "react";
import {
  AgentCreateFormDrawer,
  AgentsAndSkillsHeaderAndToolbar,
} from "./AgentAndSkillCreateForms";
import { AgentDetailAndSandboxModal } from "./AgentDetailAndSandboxModal";
import type { AgentSixBlocksDraftState } from "./AgentGovernanceTypesAndDefaults";
import { createDefaultAgentSixBlocksDraft } from "./AgentGovernanceTypesAndDefaults";
import { AgentStudioCardItem } from "./AgentStudioCardItem";
import type {
  AgentsAndSkillsManagerLabels,
  AgentsAndSkillsManagerViewProps,
  AgentsAndSkillsSubTab,
  CreateAgentSixBlocksInput,
  UiAgentSkillVisibilityFilter,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
  UiManagedSkillItem,
} from "./AgentsAndSkillsTypes";
import {
  matchesAgentQueryAndScope,
  matchesSkillQueryAndScope,
  SkillCreateFormDrawer,
} from "./SkillCreateFormDrawer";
import { SkillDetailAndSandboxModal } from "./SkillDetailAndSandboxModal";
import { SkillStudioCardItem } from "./SkillStudioCardItem";
import { WorkspaceAssistantPinnedCard } from "./WorkspaceAssistantPinnedCard";

export type {
  AgentsAndSkillsManagerLabels,
  AgentsAndSkillsManagerViewProps,
  AgentsAndSkillsSubTab,
  CreateAgentSixBlocksInput,
  UiAgentSkillVisibilityFilter,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
  UiManagedSkillItem,
};

export const AgentsAndSkillsManagerView: React.FC<AgentsAndSkillsManagerViewProps> = ({
  agents,
  skills,
  labels,
  initialTab = "AGENTS",
  onCreateAgent,
  onToggleAgentSkill,
  onExecuteAgent,
  onDeleteAgent,
  onDuplicateAgent,
  onToggleAgentEnabled,
  onToggleAgentMcpExposure,
  onUpdateAgentDetails,
  onUpdateAgentThinkingLevel,
  onUpdateAgentVisibility,
  onUseAgentInAssistant,
  onCreateSkill,
  onExecuteSkill,
  onDeleteSkill,
  onUpdateSkillVisibility,
  onUseSkillInAssistant,
  onLoadPackTemplates,
  onOpenMcpTestBench,
  pinnedAssistantMcpExposed = false,
  onTogglePinnedAssistantMcp,
  onOpenAssistantSettings,
  onOpenAssistant,
  connectionsContent,
  renderAgentSandboxSlot,
}) => {
  const [activeTab, setActiveTab] = useState<AgentsAndSkillsSubTab>(initialTab);
  const [searchQuery, setSearchQuery] = useState("");
  const [visibilityFilter, setVisibilityFilter] = useState<UiAgentSkillVisibilityFilter>("ALL");
  const [isCreateAgentOpen, setIsCreateAgentOpen] = useState(false);
  const [isCreateSkillOpen, setIsCreateSkillOpen] = useState(false);
  const [activeDetailAgentId, setActiveDetailAgentId] = useState<string | null>(null);
  const [activeDetailSkillId, setActiveDetailSkillId] = useState<string | null>(null);

  const [agentDraft, setAgentDraft] = useState<AgentSixBlocksDraftState>(() =>
    createDefaultAgentSixBlocksDraft(null),
  );
  const [agentTestInputs, setAgentTestInputs] = useState<Record<string, string>>({});

  const [skillName, setSkillName] = useState("");
  const [skillObjective, setSkillObjective] = useState("");
  const [skillParamsRaw, setSkillParamsRaw] = useState("");
  const [skillInstructions, setSkillInstructions] = useState("");
  const [skillOutputFormat, setSkillOutputFormat] = useState("");
  const [skillVisibility, setSkillVisibility] = useState<"PRIVATE" | "TEAM">("TEAM");
  const [skillTestInputs, setSkillTestInputs] = useState<Record<string, string>>({});

  const filteredAgents = agents.filter((ag) =>
    matchesAgentQueryAndScope(ag, searchQuery, visibilityFilter),
  );
  const filteredSkills = skills.filter((sk) =>
    matchesSkillQueryAndScope(sk, searchQuery, visibilityFilter),
  );

  const activeAgentsCount = agents.filter((a) => a.enabledOnWorkspace !== false).length;
  const packOrTeamAgentsCount = agents.filter(
    (a) => (a.visibilityScope ?? "TEAM") === "PACK" || (a.visibilityScope ?? "TEAM") === "TEAM",
  ).length;
  const mcpExposedAgentsCount =
    agents.filter((a) => a.mcpExposed).length + (pinnedAssistantMcpExposed ? 1 : 0);

  const activeDetailAgent = agents.find((a) => a.agentId === activeDetailAgentId) ?? null;
  const activeDetailSkill = skills.find((s) => s.skillId === activeDetailSkillId) ?? null;

  const handleSubmitAgent = (e: React.FormEvent) => {
    e.preventDefault();
    const resolvedInst = agentDraft.instructions.trim() || agentDraft.promptRef.trim();
    if (!agentDraft.name.trim() || !agentDraft.roleMission.trim() || !resolvedInst) return;
    onCreateAgent({
      name: agentDraft.name.trim(),
      roleMission: agentDraft.roleMission.trim(),
      instructions: resolvedInst,
      thinkingLevel: agentDraft.thinkingLevel,
      skillIds: agentDraft.skillIds.filter((sid) => skills.some((s) => s.skillId === sid)),
      visibilityScope: agentDraft.visibilityScope === "PRIVATE" ? "PRIVATE" : "TEAM",
      posture: agentDraft.posture,
      humanPartnerRole: agentDraft.humanPartnerRole,
      llmModelTier: agentDraft.llmModelTier,
      temperature: agentDraft.temperature,
      maxTokens: agentDraft.maxTokens,
      promptRef: agentDraft.promptRef.trim() || undefined,
      invocationModes: agentDraft.invocationModes,
      dialogueMechanism: agentDraft.dialogueMechanism,
      allowedRagSources: agentDraft.allowedRagSources,
      ontologyViews: agentDraft.ontologyViews,
      mcpToolPermissions: agentDraft.mcpToolPermissions,
      guardrails: agentDraft.guardrails,
      outputContractFormat: agentDraft.outputContractFormat,
      writePreviewRequired: agentDraft.writePreviewRequired,
    });
    setAgentDraft(createDefaultAgentSixBlocksDraft(null));
    setIsCreateAgentOpen(false);
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
        labels={labels}
        activeTab={activeTab}
        agentsCount={agents.length}
        activeAgentsCount={activeAgentsCount}
        skillsCount={skills.length}
        packOrTeamAgentsCount={packOrTeamAgentsCount}
        mcpExposedAgentsCount={mcpExposedAgentsCount}
        searchQuery={searchQuery}
        visibilityFilter={visibilityFilter}
        onSelectTab={setActiveTab}
        onToggleCreateAgent={() => setIsCreateAgentOpen((prev) => !prev)}
        onToggleCreateSkill={() => setIsCreateSkillOpen((prev) => !prev)}
        onOpenMcpTestBench={onOpenMcpTestBench}
        onChangeSearchQuery={setSearchQuery}
        onChangeVisibilityFilter={setVisibilityFilter}
        onLoadPackTemplates={onLoadPackTemplates}
      />

      {activeTab === "AGENTS" && (
        <div data-testid="agents-subview-panel" className="space-y-4">
          <WorkspaceAssistantPinnedCard
            mcpExposed={pinnedAssistantMcpExposed}
            onToggleMcpExposed={onTogglePinnedAssistantMcp}
            onOpenSettings={onOpenAssistantSettings}
            onOpenAssistant={onOpenAssistant}
          />
          <AgentCreateFormDrawer
            isOpen={isCreateAgentOpen}
            labels={labels}
            skills={skills}
            draft={agentDraft}
            onChangeDraft={(patch) => setAgentDraft((prev) => ({ ...prev, ...patch }))}
            onToggleSkillId={(skillId, checked) =>
              setAgentDraft((prev) => ({
                ...prev,
                skillIds: checked
                  ? [...prev.skillIds, skillId]
                  : prev.skillIds.filter((id) => id !== skillId),
              }))
            }
            onSubmit={handleSubmitAgent}
            onClose={() => setIsCreateAgentOpen(false)}
          />
          {filteredAgents.length === 0 ? (
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
              {filteredAgents.map((ag) => (
                <AgentStudioCardItem
                  key={ag.agentId}
                  agent={ag}
                  skills={skills}
                  labels={labels}
                  onDeleteAgent={onDeleteAgent}
                  onDuplicateAgent={onDuplicateAgent}
                  onToggleAgentEnabled={onToggleAgentEnabled}
                  onOpenDetailModal={(item) => setActiveDetailAgentId(item.agentId)}
                  onUpdateAgentThinkingLevel={onUpdateAgentThinkingLevel}
                  onUpdateAgentVisibility={onUpdateAgentVisibility}
                  onUseAgentInAssistant={onUseAgentInAssistant}
                />
              ))}
            </div>
          )}
          <AgentDetailAndSandboxModal
            agent={activeDetailAgent}
            skills={skills}
            labels={labels}
            testInputValue={
              activeDetailAgent ? (agentTestInputs[activeDetailAgent.agentId] ?? "") : ""
            }
            onChangeTestInput={(agentId, val) =>
              setAgentTestInputs((p) => ({ ...p, [agentId]: val }))
            }
            onToggleAgentSkill={onToggleAgentSkill}
            onExecuteAgent={onExecuteAgent}
            onUpdateAgentThinkingLevel={onUpdateAgentThinkingLevel}
            onUpdateAgentVisibility={onUpdateAgentVisibility}
            onToggleAgentMcpExposure={onToggleAgentMcpExposure}
            onUpdateAgentDetails={onUpdateAgentDetails}
            sandboxTraceSlot={
              activeDetailAgent && renderAgentSandboxSlot
                ? renderAgentSandboxSlot(activeDetailAgent)
                : null
            }
            onClose={() => setActiveDetailAgentId(null)}
          />
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
            onClose={() => setIsCreateSkillOpen(false)}
          />
          {filteredSkills.length === 0 ? (
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
              {filteredSkills.map((sk) => (
                <SkillStudioCardItem
                  key={sk.skillId}
                  skill={sk}
                  labels={labels}
                  onDeleteSkill={onDeleteSkill}
                  onOpenDetailModal={(item) => setActiveDetailSkillId(item.skillId)}
                  onUpdateSkillVisibility={onUpdateSkillVisibility}
                  onUseSkillInAssistant={onUseSkillInAssistant}
                />
              ))}
            </div>
          )}
          <SkillDetailAndSandboxModal
            skill={activeDetailSkill}
            labels={labels}
            testInputValue={
              activeDetailSkill ? (skillTestInputs[activeDetailSkill.skillId] ?? "") : ""
            }
            onChangeTestInput={(skillId, val) =>
              setSkillTestInputs((p) => ({ ...p, [skillId]: val }))
            }
            onExecuteSkill={onExecuteSkill}
            onUpdateSkillVisibility={onUpdateSkillVisibility}
            onClose={() => setActiveDetailSkillId(null)}
          />
        </div>
      )}

      {activeTab === "CONNECTIONS" && (
        <div data-testid="connections-subview-panel">{connectionsContent}</div>
      )}
    </section>
  );
};
