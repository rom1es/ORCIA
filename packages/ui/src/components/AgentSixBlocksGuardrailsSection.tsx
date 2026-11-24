import React from "react";
import type {
  AgentSixBlocksDraftState,
  UiAgentOutputContractFormat,
} from "./AgentGovernanceTypesAndDefaults";
import type { AgentsAndSkillsManagerLabels } from "./AgentsAndSkillsTypes";

export interface AgentSixBlocksGuardrailsSectionProps {
  readonly draft: AgentSixBlocksDraftState;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly testIdPrefix: string;
  readonly onChangeDraft: (patch: Partial<AgentSixBlocksDraftState>) => void;
}

const OUTPUT_FORMAT_KEYS: readonly UiAgentOutputContractFormat[] = [
  "markdown_structure",
  "confluence_draft",
  "jira_draft",
  "gate_risk_json",
];

const GUARDRAIL_KEYS = [
  "citations_obligatoires",
  "aucun_fait_invente",
  "isolation_prompt_injection",
  "filtrage_dcp_pii",
  "lecture_seule_code",
] as const;

export const AgentSixBlocksGuardrailsSection: React.FC<
  AgentSixBlocksGuardrailsSectionProps
> = ({ draft, labels, testIdPrefix, onChangeDraft }) => {
  const studio = labels.studio;
  const toggleArrayItem = (
    list: readonly string[],
    item: string,
    checked: boolean,
  ): string[] =>
    checked ? Array.from(new Set([...list, item])) : list.filter((x) => x !== item);

  return (
    <div
      data-testid={`${testIdPrefix}-agent-block-F`}
      className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
    >
      <strong className="block text-xs font-semibold">
        {studio.blockTitles.F.heading}
      </strong>
      <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
        <label className="flex flex-col gap-1">
          <span className="font-medium">{studio.outputContractFieldLabel}</span>
          <select
            data-testid={`${testIdPrefix}-agent-output-contract-select`}
            value={draft.outputContractFormat}
            onChange={(e) =>
              onChangeDraft({
                outputContractFormat: e.target.value as UiAgentOutputContractFormat,
              })
            }
            className="orcia-ds-select"
          >
            {OUTPUT_FORMAT_KEYS.map((fmt) => (
              <option key={fmt} value={fmt}>
                {studio.outputContractFormats[fmt]}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 self-end rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5 font-medium">
          <input
            type="checkbox"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid={`${testIdPrefix}-agent-write-preview-checkbox`}
            checked={draft.writePreviewRequired}
            onChange={(e) =>
              onChangeDraft({ writePreviewRequired: e.target.checked })
            }
          />
          <span>{studio.writePreviewRequiredLabel}</span>
        </label>
      </div>
      <div className="space-y-1">
        <span className="font-medium">{studio.guardrailsFieldLabel}</span>
        <div className="grid grid-cols-1 gap-1.5 md:grid-cols-2">
          {GUARDRAIL_KEYS.map((grId) => {
            const checked = draft.guardrails.includes(grId);
            return (
              <label
                key={grId}
                className="flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-1"
              >
                <input
                  type="checkbox"
                  autoComplete="off"
                  data-lpignore="true"
                  data-1p-ignore="true"
                  data-bwignore="true"
                  data-form-type="other"
                  data-testid={`${testIdPrefix}-agent-guardrail-${grId}`}
                  checked={checked}
                  onChange={(e) =>
                    onChangeDraft({
                      guardrails: toggleArrayItem(
                        draft.guardrails,
                        grId,
                        e.target.checked,
                      ),
                    })
                  }
                />
                <span>{studio.guardrailOptions[grId] ?? grId}</span>
              </label>
            );
          })}
        </div>
      </div>
    </div>
  );
};
