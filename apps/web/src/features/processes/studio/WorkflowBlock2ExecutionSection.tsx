import { OrciaIcon } from "@orcia/ui";
import React from "react";
import type { ProcessOrchestrationModesCopy } from "../../../i18n/locales/process_orchestration_modes_labels";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";
import { AVAILABLE_DELEGATE_AGENTS } from "./studioLabelsAndMappers";

export interface WorkflowBlock2ExecutionSectionProps {
  readonly workflow: WorkflowDefinitionV2Item;
  readonly goalObjectiveDraft: string;
  readonly goalDelegateAgentsDraft: readonly string[];
  readonly copy: ProcessOrchestrationModesCopy;
  readonly isFr: boolean;
  readonly onChangeGoalObjective: (nextObjective: string) => void;
  readonly onToggleDelegateAgent: (agentSlug: string) => void;
  readonly onToggleSubStepEnabled: (subStepId: string) => void;
  readonly onSwitchExecutionMode: (mode: "native_orcia" | "external_delegated") => void;
}

export function WorkflowBlock2ExecutionSection({
  workflow,
  goalObjectiveDraft,
  goalDelegateAgentsDraft,
  copy,
  isFr,
  onChangeGoalObjective,
  onToggleDelegateAgent,
  onToggleSubStepEnabled,
  onSwitchExecutionMode,
}: WorkflowBlock2ExecutionSectionProps) {
  const isGoalDriven = workflow.orchestration_type === "non_deterministic";

  if (isGoalDriven) {
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
            {AVAILABLE_DELEGATE_AGENTS.map((agent) => {
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
                      <span>{isFr ? agent.labelFr : agent.labelEn}</span>
                    </span>
                    {selected ? (
                      <span style={{ color: "var(--color-gate-emerald)" }}>
                        <OrciaIcon name="check" />
                      </span>
                    ) : null}
                  </div>
                  <div style={{ fontSize: "11.5px", color: "var(--color-text-secondary)" }}>
                    {isFr ? agent.roleFr : agent.roleEn}
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

  return (
    <div
      data-testid="studio-block-2-deterministic-substeps"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "10px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <div>
          <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
            {copy.milestoneBlock2Title}
          </strong>
          <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
            {copy.milestoneBlock2Subtitle}
          </div>
        </div>

        <div style={{ display: "flex", gap: "6px" }}>
          <button
            type="button"
            data-testid="mode-switch-native-orcia-btn"
            onClick={() => onSwitchExecutionMode("native_orcia")}
            className={
              workflow.execution_mode === "native_orcia"
                ? "orcia-ds-btn-primary"
                : "orcia-ds-btn-secondary"
            }
          >
            {isFr ? "Exécution guidée ORCIA" : "Guided execution in ORCIA"}
          </button>
          <button
            type="button"
            data-testid="mode-switch-external-delegated-btn"
            onClick={() => onSwitchExecutionMode("external_delegated")}
            className={
              workflow.execution_mode === "external_delegated"
                ? "orcia-ds-btn-primary"
                : "orcia-ds-btn-secondary"
            }
          >
            {isFr ? "Réalisation dans l'IDE / Git" : "Realization in IDE / Git"}
          </button>
        </div>
      </div>

      {workflow.execution_mode === "external_delegated" ? (
        <div
          data-testid="studio-external-delegated-banner"
          className="rounded border p-3 text-xs"
          style={{
            backgroundColor: "var(--color-arbitration-bg)",
            borderColor: "var(--color-arbitration-amber)",
          }}
        >
          <strong>
            {isFr
              ? "Réalisation confiée à l'équipe dans son IDE / Git :"
              : "Realization delegated to the team's IDE / Git:"}
          </strong>{" "}
          {isFr
            ? "ORCIA prépare le dossier de contexte et vérifie automatiquement la conformité dès que la Pull Request est proposée."
            : "ORCIA prepares the context brief and automatically verifies compliance as soon as the Pull Request is opened."}
        </div>
      ) : null}

      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {workflow.sub_steps.map((sub, idx) => (
          <div
            key={sub.id}
            data-testid={`studio-substep-card-${sub.id}`}
            className="rounded border p-3"
            style={{
              backgroundColor: sub.enabled
                ? "var(--color-bg-elevated)"
                : "var(--color-surface-muted)",
              borderColor: sub.enabled
                ? "var(--color-primary-cobalt)"
                : "var(--color-border-subtle)",
              opacity: sub.enabled ? 1 : 0.65,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "8px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                <span
                  style={{
                    fontSize: "12px",
                    fontWeight: 700,
                    color: "var(--color-primary-cobalt)",
                  }}
                >
                  {isFr ? `Étape ${idx + 1}` : `Step ${idx + 1}`}
                </span>
                <strong style={{ fontSize: "13.5px" }}>{sub.name}</strong>
                {sub.requires_human_checkpoint ? (
                  <span
                    className="rounded px-2 py-0.5 text-xs font-semibold"
                    style={{
                      backgroundColor: "var(--color-arbitration-bg)",
                      color: "var(--color-arbitration-amber)",
                    }}
                  >
                    {isFr ? "Validation humaine" : "Human review"}
                  </span>
                ) : null}
                {sub.write_preview_required ? (
                  <span
                    className="rounded px-2 py-0.5 text-xs font-semibold"
                    style={{
                      backgroundColor: "var(--color-gate-emerald-bg)",
                      color: "var(--color-gate-emerald)",
                    }}
                  >
                    {isFr ? "Confirmation avant publication" : "Confirm before publishing"}
                  </span>
                ) : null}
              </div>

              <button
                type="button"
                data-testid={`toggle-substep-enabled-${sub.id}`}
                onClick={() => onToggleSubStepEnabled(sub.id)}
                className="orcia-ds-btn-secondary"
              >
                {sub.enabled
                  ? isFr
                    ? "✓ Étape activée (Ignorer)"
                    : "✓ Step enabled (Skip)"
                  : isFr
                    ? "Étape ignorée (Activer)"
                    : "Step skipped (Enable)"}
              </button>
            </div>

            <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", marginTop: "6px" }}>
              <strong>{isFr ? "Objectif :" : "Goal:"}</strong> {sub.role_description}
            </div>
            <div style={{ fontSize: "12px", marginTop: "3px" }}>
              <strong>{isFr ? "Livrable produit :" : "Expected output:"}</strong> {sub.output_description}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
