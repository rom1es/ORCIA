import React from "react";
import type {
  AgentSixBlocksDraftState,
  UiAgentLlmModelTier,
} from "./AgentGovernanceTypesAndDefaults";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentThinkingLevel,
} from "./AgentsAndSkillsTypes";

const LLM_TIER_KEYS: readonly UiAgentLlmModelTier[] = [
  "team_default",
  "fast",
  "deep",
  "discovery",
];
const TEMP_KEYS = ["0", "0.2", "0.4", "0.7"] as const;
const TOKEN_KEYS = ["2048", "4096", "8192", "16384"] as const;

export interface AgentSixBlocksBlockBProps {
  readonly draft: AgentSixBlocksDraftState;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly readOnlyIdentity?: boolean;
  readonly testIdPrefix: string;
  readonly onChangeDraft: (patch: Partial<AgentSixBlocksDraftState>) => void;
}

export const AgentSixBlocksBlockB: React.FC<AgentSixBlocksBlockBProps> = ({
  draft,
  labels,
  readOnlyIdentity = false,
  testIdPrefix,
  onChangeDraft,
}) => {
  const studio = labels.studio;
  return (
    <div
      data-testid={`${testIdPrefix}-agent-block-B`}
      className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
    >
      <strong className="block text-xs font-semibold">
        {studio.blockTitles.B.heading}
      </strong>
      <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
        <label className="flex flex-col gap-1">
          <span className="font-medium">{studio.llmModelFieldLabel}</span>
          <select
            data-testid={`${testIdPrefix}-agent-llm-model-tier-select`}
            disabled={readOnlyIdentity}
            value={draft.llmModelTier}
            onChange={(e) =>
              onChangeDraft({
                llmModelTier: e.target.value as UiAgentLlmModelTier,
              })
            }
            className="orcia-ds-select"
          >
            {LLM_TIER_KEYS.map((tier) => (
              <option key={tier} value={tier}>
                {studio.llmModelTiers[tier]}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-medium">{labels.agentThinkingLevelLabel}</span>
          <select
            data-testid={
              testIdPrefix === "create"
                ? "agent-thinking-level-select"
                : "modal-agent-thinking-select"
            }
            disabled={readOnlyIdentity}
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
        <label className="flex flex-col gap-1">
          <span className="font-medium">{studio.temperatureFieldLabel}</span>
          <select
            data-testid={`${testIdPrefix}-agent-temperature-select`}
            disabled={readOnlyIdentity}
            value={String(draft.temperature)}
            onChange={(e) =>
              onChangeDraft({ temperature: Number(e.target.value) })
            }
            className="orcia-ds-select"
          >
            {TEMP_KEYS.map((tk) => (
              <option key={tk} value={tk}>
                {studio.temperatureOptions[tk]}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-medium">{studio.maxTokensFieldLabel}</span>
          <select
            data-testid={`${testIdPrefix}-agent-max-tokens-select`}
            disabled={readOnlyIdentity}
            value={String(draft.maxTokens)}
            onChange={(e) =>
              onChangeDraft({ maxTokens: Number(e.target.value) })
            }
            className="orcia-ds-select"
          >
            {TOKEN_KEYS.map((mk) => (
              <option key={mk} value={mk}>
                {studio.maxTokensOptions[mk]}
              </option>
            ))}
          </select>
        </label>
      </div>
    </div>
  );
};
