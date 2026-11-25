import React from "react";
import type { AgentSixBlocksDraftState } from "./AgentGovernanceTypesAndDefaults";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
  UiManagedSkillItem,
} from "./AgentsAndSkillsTypes";
import { OrciaIcon } from "./icons";

export interface AgentIdentityAndSkillsFieldsProps {
  readonly agent: UiManagedAgentItem;
  readonly draft: AgentSixBlocksDraftState;
  readonly skills: readonly UiManagedSkillItem[];
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly isPack: boolean;
  readonly visibilityScope: UiAgentSkillVisibilityScope;
  readonly onChangeDraft: (patch: Partial<AgentSixBlocksDraftState>) => void;
  readonly onToggleAgentSkill: (
    agentId: string,
    skillId: string,
    checked: boolean,
  ) => void;
}

export function AgentIdentityAndSkillsFields({
  agent,
  draft,
  skills,
  labels,
  isPack,
  visibilityScope,
  onChangeDraft,
  onToggleAgentSkill,
}: AgentIdentityAndSkillsFieldsProps): React.JSX.Element {
  const studio = labels.studio;
  return (
    <>
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
            onChange={(e) => onChangeDraft({ name: e.target.value })}
            className="orcia-ds-input disabled:opacity-50"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-medium">{labels.agentThinkingLevelLabel}</span>
          <select
            data-testid={`modal-agent-thinking-select-${agent.agentId}`}
            value={draft.thinkingLevel}
            onChange={(e) =>
              onChangeDraft({
                thinkingLevel: e.target.value as UiAgentThinkingLevel,
              })
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
            <span className="font-medium">{studio.visibilityFieldLabel}</span>
            <select
              data-testid={`edit-agent-visibility-select-${agent.agentId}`}
              value={visibilityScope === "PRIVATE" ? "PRIVATE" : "TEAM"}
              onChange={(e) =>
                onChangeDraft({
                  visibilityScope: e.target.value as UiAgentSkillVisibilityScope,
                })
              }
              className="orcia-ds-select"
            >
              <option value="TEAM">{studio.visibilityTeamShort}</option>
              <option value="PRIVATE">{studio.visibilityPrivateShort}</option>
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
            onChange={(e) => onChangeDraft({ roleMission: e.target.value })}
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
            onChange={(e) => onChangeDraft({ instructions: e.target.value })}
            className="orcia-ds-textarea disabled:opacity-50"
          />
        </label>
      </div>

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
                    onChange={(e) =>
                      onToggleAgentSkill(agent.agentId, sk.skillId, e.target.checked)
                    }
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
    </>
  );
}
