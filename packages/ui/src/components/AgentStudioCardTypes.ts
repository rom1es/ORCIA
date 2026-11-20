import type {
  AgentsAndSkillsManagerLabels,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
  UiManagedSkillItem,
} from "./AgentsAndSkillsManagerView";

export interface AgentStudioCardItemProps {
  readonly agent: UiManagedAgentItem;
  readonly skills: readonly UiManagedSkillItem[];
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly testInputValue?: string;
  readonly onChangeTestInput?: (agentId: string, nextValue: string) => void;
  readonly onToggleAgentSkill?: (agentId: string, skillId: string, nextChecked: boolean) => void;
  readonly onExecuteAgent?: (agentId: string, prompt: string) => void;
  readonly onDeleteAgent: (agentId: string) => void;
  readonly onDuplicateAgent?: (agent: UiManagedAgentItem) => void;
  readonly onToggleAgentEnabled?: (agentId: string, nextEnabled: boolean) => void;
  readonly onOpenDetailModal?: (agent: UiManagedAgentItem) => void;
  readonly onUpdateAgentThinkingLevel?: (
    agentId: string,
    nextThinkingLevel: UiAgentThinkingLevel,
  ) => void;
  readonly onUpdateAgentVisibility?: (
    agentId: string,
    nextVisibility: UiAgentSkillVisibilityScope,
  ) => void;
  readonly onUseAgentInAssistant?: (agent: UiManagedAgentItem) => void;
}
