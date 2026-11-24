import React from "react";
import type {
  AgentSixBlocksDraftState,
  UiAgentDialogueMechanism,
  UiAgentInvocationMode,
} from "./AgentGovernanceTypesAndDefaults";
import type { AgentsAndSkillsManagerLabels } from "./AgentsAndSkillsTypes";

export interface AgentSixBlocksBlockCProps {
  readonly draft: AgentSixBlocksDraftState;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly readOnlyIdentity: boolean;
  readonly testIdPrefix: string;
  readonly onChangeDraft: (patch: Partial<AgentSixBlocksDraftState>) => void;
}

const DIALOGUE_MECH_KEYS: readonly UiAgentDialogueMechanism[] = [
  "questionnaire_prealable",
  "pause_par_bloc",
  "direct",
];

const INVOCATION_MODE_KEYS: readonly UiAgentInvocationMode[] = [
  "generer",
  "corrections",
  "section",
];

export const AgentSixBlocksBlockC: React.FC<AgentSixBlocksBlockCProps> = ({
  draft,
  labels,
  readOnlyIdentity,
  testIdPrefix,
  onChangeDraft,
}) => {
  const studio = labels.studio;
  const toggleArrayItem = (
    list: readonly string[],
    item: string,
    checked: boolean,
  ): string[] =>
    checked ? Array.from(new Set([...list, item])) : list.filter((x) => x !== item);

  return (
    <div
      data-testid={`${testIdPrefix}-agent-block-C`}
      className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
    >
      <strong className="block text-xs font-semibold">
        {studio.blockTitles.C.heading}
      </strong>
      <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
        <label className="flex flex-col gap-1 md:col-span-2">
          <span className="font-medium">
            {labels.agentInstructionsLabel} {studio.systemPromptSuffix}
          </span>
          <textarea
            rows={3}
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid={
              testIdPrefix === "create"
                ? "agent-instructions-input"
                : "edit-agent-instructions-input"
            }
            disabled={readOnlyIdentity}
            value={draft.instructions}
            onChange={(e) => onChangeDraft({ instructions: e.target.value })}
            placeholder={labels.agentInstructionsPlaceholder}
            className="orcia-ds-textarea"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-medium">{studio.promptRefFieldLabel}</span>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid={`${testIdPrefix}-agent-prompt-ref-input`}
            value={draft.promptRef}
            onChange={(e) => onChangeDraft({ promptRef: e.target.value })}
            placeholder={studio.promptRefPlaceholder}
            className="orcia-ds-input font-mono text-[11px]"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-medium">{studio.dialogueMechanismFieldLabel}</span>
          <select
            data-testid={`${testIdPrefix}-agent-dialogue-mechanism-select`}
            value={draft.dialogueMechanism}
            onChange={(e) =>
              onChangeDraft({
                dialogueMechanism: e.target.value as UiAgentDialogueMechanism,
              })
            }
            className="orcia-ds-select"
          >
            {DIALOGUE_MECH_KEYS.map((mech) => (
              <option key={mech} value={mech}>
                {studio.dialogueMechanisms[mech]}
              </option>
            ))}
          </select>
        </label>
        <div className="space-y-1 md:col-span-2">
          <span className="font-medium">{studio.invocationModesFieldLabel}</span>
          <div className="flex flex-wrap gap-2">
            {INVOCATION_MODE_KEYS.map((modeKey) => {
              const checked = draft.invocationModes.includes(modeKey);
              return (
                <label
                  key={modeKey}
                  className="inline-flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1"
                >
                  <input
                    type="checkbox"
                    autoComplete="off"
                    data-lpignore="true"
                    data-1p-ignore="true"
                    data-bwignore="true"
                    data-form-type="other"
                    data-testid={`${testIdPrefix}-agent-mode-${modeKey}`}
                    checked={checked}
                    onChange={(e) =>
                      onChangeDraft({
                        invocationModes: toggleArrayItem(
                          draft.invocationModes,
                          modeKey,
                          e.target.checked,
                        ),
                      })
                    }
                  />
                  <span>{studio.invocationModes[modeKey]}</span>
                </label>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
