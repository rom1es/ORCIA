import React from "react";
import type {
  AgentSixBlocksDraftState,
  UiAgentDialogueMechanism,
  UiAgentHumanPartnerRole,
  UiAgentLlmModelTier,
  UiAgentOutputContractFormat,
  UiAgentPosture,
} from "./AgentGovernanceTypesAndDefaults";

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
  readonly posture?: UiAgentPosture;
  readonly humanPartnerRole?: UiAgentHumanPartnerRole;
  readonly llmModelTier?: UiAgentLlmModelTier;
  readonly temperature?: number;
  readonly maxTokens?: number;
  readonly promptRef?: string | null;
  readonly invocationModes?: readonly string[];
  readonly dialogueMechanism?: UiAgentDialogueMechanism;
  readonly allowedRagSources?: readonly string[];
  readonly ontologyViews?: readonly string[];
  readonly mcpToolPermissions?: Readonly<Record<string, string>>;
  readonly guardrails?: readonly string[];
  readonly outputContractFormat?: UiAgentOutputContractFormat;
  readonly writePreviewRequired?: boolean;
  readonly testBenchValidated?: boolean;
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

export interface CreateAgentSixBlocksInput {
  readonly name: string;
  readonly roleMission: string;
  readonly instructions: string;
  readonly thinkingLevel: UiAgentThinkingLevel;
  readonly skillIds: string[];
  readonly visibilityScope?: "PRIVATE" | "TEAM";
  readonly posture?: UiAgentPosture;
  readonly humanPartnerRole?: UiAgentHumanPartnerRole;
  readonly llmModelTier?: UiAgentLlmModelTier;
  readonly temperature?: number;
  readonly maxTokens?: number;
  readonly promptRef?: string;
  readonly invocationModes?: readonly string[];
  readonly dialogueMechanism?: UiAgentDialogueMechanism;
  readonly allowedRagSources?: readonly string[];
  readonly ontologyViews?: readonly string[];
  readonly mcpToolPermissions?: Readonly<Record<string, string>>;
  readonly guardrails?: readonly string[];
  readonly outputContractFormat?: UiAgentOutputContractFormat;
  readonly writePreviewRequired?: boolean;
}

export interface AgentsAndSkillsManagerViewProps {
  readonly agents: readonly UiManagedAgentItem[];
  readonly skills: readonly UiManagedSkillItem[];
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly initialTab?: AgentsAndSkillsSubTab;
  readonly onCreateAgent: (input: CreateAgentSixBlocksInput) => void;
  readonly onToggleAgentSkill: (agentId: string, skillId: string, nextChecked: boolean) => void;
  readonly onExecuteAgent: (agentId: string, prompt: string) => void;
  readonly onDeleteAgent: (agentId: string) => void;
  readonly onDuplicateAgent?: (agent: UiManagedAgentItem) => void;
  readonly onToggleAgentEnabled?: (agentId: string, nextEnabled: boolean) => void;
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
  readonly onUpdateAgentThinkingLevel?: (
    agentId: string,
    nextThinkingLevel: UiAgentThinkingLevel,
  ) => void;
  readonly onUpdateAgentVisibility?: (
    agentId: string,
    nextVisibility: UiAgentSkillVisibilityScope,
  ) => void;
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
  readonly onUpdateSkillVisibility?: (
    skillId: string,
    nextVisibility: UiAgentSkillVisibilityScope,
  ) => void;
  readonly onUseSkillInAssistant?: (skill: UiManagedSkillItem) => void;
  readonly onLoadPackTemplates?: () => void;
  readonly onOpenMcpTestBench?: () => void;
  readonly pinnedAssistantMcpExposed?: boolean;
  readonly onTogglePinnedAssistantMcp?: (nextExposed: boolean) => void;
  readonly onOpenAssistantSettings?: () => void;
  readonly onOpenAssistant?: () => void;
  readonly connectionsContent?: React.ReactNode;
  readonly renderAgentSandboxSlot?: (agent: UiManagedAgentItem) => React.ReactNode;
}
