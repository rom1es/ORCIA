import { OrciaIcon } from "@orcia/ui";
import React from "react";
import { resolveLocaleForFlag } from "../../../i18n";
import type { ProcessOrchestrationModesCopy } from "../../../i18n/locales/process_orchestration_modes_labels";
import { getDelegateAgents } from "./studioLabelsAndMappers";

export interface WorkflowBlock2GoalDrivenSectionProps {
  readonly goalObjectiveDraft: string;
  readonly goalDelegateAgentsDraft: readonly string[];
  readonly copy: ProcessOrchestrationModesCopy;
  readonly isFr: boolean;
  readonly onChangeGoalObjective: (nextObjective: string) => void;
  readonly onToggleDelegateAgent: (agentSlug: string) => void;
}

export function WorkflowBlock2GoalDrivenSection({
  goalObjectiveDraft,
  goalDelegateAgentsDraft,
  copy,
  isFr,
  onChangeGoalObjective,
  onToggleDelegateAgent,
}: WorkflowBlock2GoalDrivenSectionProps): React.JSX.Element {
  const delegateAgents = getDelegateAgents(resolveLocaleForFlag(isFr));

  return (
    <div
      data-testid="studio-block-2-goal-driven"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
    >
      <div>
        <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
          {copy.goalBlock2Title}
        </strong>
        <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
          {copy.goalBlock2Subtitle}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <label
          htmlFor="studio-goal-reflexive-objective"
          style={{ fontSize: "12.5px", fontWeight: 600 }}
        >
          {copy.goalObjectiveLabel}
        </label>
        <textarea
          id="studio-goal-reflexive-objective"
          data-testid="studio-goal-reflexive-objective-input"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          rows={4}
          value={goalObjectiveDraft}
          placeholder={copy.goalObjectivePlaceholder}
          onChange={(e) => onChangeGoalObjective(e.target.value)}
          className="orcia-ds-textarea"
          style={{ fontSize: "13px" }}
        />
      </div>

      <div
        data-testid="studio-goal-delegate-agents-picker"
        style={{ display: "flex", flexDirection: "column", gap: "8px" }}
      >
        <div>
          <div style={{ fontSize: "12.5px", fontWeight: 600 }}>
            {copy.goalDelegateAgentsLabel}
          </div>
          <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
            {copy.goalDelegateAgentsHint}
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))",
            gap: "8px",
          }}
        >
          {delegateAgents.map((agent) => {
            const selected = goalDelegateAgentsDraft.includes(agent.slug);
            return (
              <button
                key={agent.slug}
                type="button"
                aria-pressed={selected}
                data-testid={`toggle-delegate-agent-${agent.slug}`}
                onClick={() => onToggleDelegateAgent(agent.slug)}
                className="rounded border p-2.5 text-left"
                style={{
                  backgroundColor: selected
                    ? "var(--color-ontology-bg)"
                    : "var(--color-bg-elevated)",
                  borderColor: selected
                    ? "var(--color-ontology-cyan)"
                    : "var(--color-border-subtle)",
                  cursor: "pointer",
                  display: "flex",
                  flexDirection: "column",
                  gap: "4px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      fontSize: "12.5px",
                      fontWeight: 700,
                    }}
                  >
                    <OrciaIcon name="agents" />
                    <span>{agent.label}</span>
                  </span>
                  {selected ? (
                    <span style={{ color: "var(--color-gate-emerald)" }}>
                      <OrciaIcon name="check" />
                    </span>
                  ) : null}
                </div>
                <div style={{ fontSize: "11.5px", color: "var(--color-text-secondary)" }}>
                  {agent.role}
                </div>
              </button>
            );
          })}
        </div>

        {goalDelegateAgentsDraft.length === 0 ? (
          <div
            className="rounded border px-3 py-2 text-xs"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-secondary)",
            }}
          >
            {copy.goalNoDelegateAgentsNotice}
          </div>
        ) : null}
      </div>
    </div>
  );
}
