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
import { AgentsAndSkillsSkillsPanel } from "./AgentsAndSkillsSkillsPanel";
import {
  matchesAgentQueryAndScope,
  matchesSkillQueryAndScope,
} from "./SkillCreateFormDrawer";
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

export const AgentsAndSkillsManagerView: React.FC<
  AgentsAndSkillsManagerViewProps
> = ({
  agents,
  skills,
  labels,
  initialTab = "AGENTS",
  alertSlot,
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
  const [visibilityFilter, setVisibilityFilter] =
    useState<UiAgentSkillVisibilityFilter>("ALL");
  const [isCreateAgentOpen, setIsCreateAgentOpen] = useState(false);
  const [isCreateSkillOpen, setIsCreateSkillOpen] = useState(false);
  const [activeDetailAgentId, setActiveDetailAgentId] = useState<string | null>(
    null,
  );
  const [activeDetailSkillId, setActiveDetailSkillId] = useState<string | null>(
    null,
  );
  const [agentDraft, setAgentDraft] = useState<AgentSixBlocksDraftState>(() =>
    createDefaultAgentSixBlocksDraft(null),
  );
  const [agentTestInputs, setAgentTestInputs] = useState<Record<string, string>>(
    {},
  );

  const filteredAgents = agents.filter((ag) =>
    matchesAgentQueryAndScope(ag, searchQuery, visibilityFilter),
  );
  const filteredSkills = skills.filter((sk) =>
    matchesSkillQueryAndScope(sk, searchQuery, visibilityFilter),
  );
  const activeAgentsCount = agents.filter(
    (a) => a.enabledOnWorkspace !== false,
  ).length;
  const packOrTeamAgentsCount = agents.filter(
    (a) =>
      (a.visibilityScope ?? "TEAM") === "PACK" ||
      (a.visibilityScope ?? "TEAM") === "TEAM",
  ).length;
  const mcpExposedAgentsCount =
    agents.filter((a) => a.mcpExposed).length + (pinnedAssistantMcpExposed ? 1 : 0);
  const activeDetailAgent =
    agents.find((a) => a.agentId === activeDetailAgentId) ?? null;
  const activeDetailSkill =
    skills.find((s) => s.skillId === activeDetailSkillId) ?? null;

  const handleSubmitAgent = (e: React.FormEvent) => {
    e.preventDefault();
    const resolvedInst =
      agentDraft.instructions.trim() || agentDraft.promptRef.trim();
    if (!agentDraft.name.trim() || !agentDraft.roleMission.trim() || !resolvedInst) {
      return;
    }
    onCreateAgent({
      name: agentDraft.name.trim(),
      roleMission: agentDraft.roleMission.trim(),
      instructions: resolvedInst,
      thinkingLevel: agentDraft.thinkingLevel,
      skillIds: agentDraft.skillIds.filter((sid) =>
        skills.some((s) => s.skillId === sid),
      ),
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

  return (
    <section
      aria-label={labels.heading}
      data-testid="agents-and-skills-manager-view"
      className="orcia-ds-page text-[var(--orcia-text-primary)]"
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
        alertSlot={alertSlot}
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
            labels={labels.studio}
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
            onChangeDraft={(patch) =>
              setAgentDraft((prev) => ({ ...prev, ...patch }))
            }
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
              className="orcia-bento-card orcia-ds-data-card border-dashed p-4 text-center text-xs text-[var(--orcia-text-secondary)]"
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
              activeDetailAgent
                ? (agentTestInputs[activeDetailAgent.agentId] ?? "")
                : ""
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
        <AgentsAndSkillsSkillsPanel
          labels={labels}
          filteredSkills={filteredSkills}
          isCreateSkillOpen={isCreateSkillOpen}
          activeDetailSkill={activeDetailSkill}
          onCloseCreateSkill={() => setIsCreateSkillOpen(false)}
          onOpenDetailModal={(item) => setActiveDetailSkillId(item.skillId)}
          onCloseDetailModal={() => setActiveDetailSkillId(null)}
          onCreateSkill={onCreateSkill}
          onExecuteSkill={onExecuteSkill}
          onDeleteSkill={onDeleteSkill}
          onUpdateSkillVisibility={onUpdateSkillVisibility}
          onUseSkillInAssistant={onUseSkillInAssistant}
        />
      )}
      {activeTab === "CONNECTIONS" && (
        <div data-testid="connections-subview-panel">{connectionsContent}</div>
      )}
    </section>
  );
};
