import { OrciaIcon } from "@orcia/ui";
import React from "react";
import type { ProcessOrchestrationModesCopy } from "../../i18n/locales/process_orchestration_modes_labels";
import { formatAgentHumanLabel } from "./execution/InteractiveRunDrawer";
import type { WorkflowDefinitionV2Item } from "./processStudioV2Data";

export type WorkflowHubFilter = "all" | "published" | "draft" | "external_delegated";

export interface ProcessCatalogCardGridProps {
  readonly workflows: readonly WorkflowDefinitionV2Item[];
  readonly filter: WorkflowHubFilter;
  readonly modesCopy: ProcessOrchestrationModesCopy;
  readonly isFr: boolean;
  readonly onChangeFilter: (nextFilter: WorkflowHubFilter) => void;
  readonly onExecuteWorkflow: (workflowId: string) => void;
  readonly onOpenStudio: (workflowId: string) => void;
}

export function ProcessCatalogCardGrid({
  workflows,
  filter,
  modesCopy,
  isFr,
  onChangeFilter,
  onExecuteWorkflow,
  onOpenStudio,
}: ProcessCatalogCardGridProps) {
  const filteredWorkflows = workflows.filter((wf) => {
    if (filter === "published") return wf.status === "published";
    if (filter === "draft") return wf.status === "draft";
    if (filter === "external_delegated") return wf.execution_mode === "external_delegated";
    return true;
  });

  return (
    <div
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "14px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        <div>
          <h3 style={{ margin: 0, fontSize: "var(--font-size-h3)" }}>
            {isFr
              ? "Processus métiers disponibles"
              : "Available Business Processes"}
          </h3>
          <p style={{ margin: "2px 0 0 0", fontSize: "12.5px", color: "var(--color-text-secondary)" }}>
            {isFr
              ? "Lancez une étape métier sur un dossier ou ouvrez l'Atelier (Studio) si vous souhaitez adapter son déroulement."
              : "Launch a business step on a dossier, or open the Studio if you want to customize its flow."}
          </p>
        </div>

        <div
          role="tablist"
          aria-label={isFr ? "Filtrer les processus" : "Filter processes"}
          className="orcia-ds-tabs"
        >
          {(
            [
              { key: "all", label: isFr ? "Tous" : "All" },
              { key: "published", label: isFr ? "Actifs" : "Active" },
              { key: "draft", label: isFr ? "En préparation" : "Drafts" },
              {
                key: "external_delegated",
                label: isFr ? "Réalisation IDE / Git" : "External IDE / Git",
              },
            ] as const
          ).map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={filter === tab.key}
              data-testid={`workflows-hub-filter-${tab.key}`}
              onClick={() => onChangeFilter(tab.key)}
              className="orcia-ds-tab"
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(310px, 1fr))",
          gap: "12px",
        }}
      >
        {filteredWorkflows.map((wf) => {
          const isExternal = wf.execution_mode === "external_delegated";
          const isGoalDriven = wf.orchestration_type === "non_deterministic";
          const activeSubStepsCount = wf.sub_steps.filter((s) => s.enabled).length;
          return (
            <article
              key={`${wf.id}-${wf.version}`}
              data-testid={`bounded-workflow-card-${wf.id}`}
              className="rounded border p-3.5"
              style={{
                backgroundColor: "var(--color-bg-elevated)",
                borderColor: "var(--color-border-subtle)",
                display: "flex",
                flexDirection: "column",
                gap: "10px",
                justifyContent: "space-between",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "6px",
                    flexWrap: "wrap",
                  }}
                >
                  <span
                    style={{
                      fontSize: "12px",
                      fontWeight: 700,
                      color: "var(--color-primary-cobalt)",
                    }}
                  >
                    {wf.vsm_step_num
                      ? isFr
                        ? `Étape ${wf.vsm_step_num} du parcours`
                        : `Step ${wf.vsm_step_num}`
                      : isFr
                        ? "Processus transverse"
                        : "Cross-cutting process"}
                  </span>

                  <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                    <span
                      data-testid={`workflow-card-mode-badge-${wf.id}`}
                      className="rounded px-2 py-0.5 text-xs font-semibold"
                      style={{
                        backgroundColor: isGoalDriven
                          ? "var(--color-ontology-bg)"
                          : "var(--color-action-primary-subtle)",
                        color: isGoalDriven
                          ? "var(--color-ontology-cyan)"
                          : "var(--color-primary-cobalt)",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "4px",
                      }}
                    >
                      <OrciaIcon name={isGoalDriven ? "compass" : "processes"} />
                      <span>
                        {isGoalDriven
                          ? modesCopy.goalDrivenBadge
                          : modesCopy.milestoneDrivenBadge}
                      </span>
                    </span>
                    {isExternal ? (
                      <span
                        className="rounded px-2 py-0.5 text-xs font-semibold"
                        style={{
                          backgroundColor: "var(--color-arbitration-bg)",
                          color: "var(--color-arbitration-amber)",
                        }}
                      >
                        {isFr ? "Équipe & IDE" : "IDE & Team"}
                      </span>
                    ) : null}
                    <span
                      className="rounded px-2 py-0.5 text-xs font-semibold"
                      style={{
                        backgroundColor:
                          wf.status === "published"
                            ? "var(--color-gate-emerald-bg)"
                            : "var(--color-arbitration-bg)",
                        color:
                          wf.status === "published"
                            ? "var(--color-gate-emerald)"
                            : "var(--color-arbitration-amber)",
                      }}
                    >
                      {wf.status === "published"
                        ? isFr
                          ? "Actif"
                          : "Active"
                        : isFr
                          ? "En préparation"
                          : "Draft"}
                    </span>
                  </div>
                </div>

                <h4 style={{ margin: 0, fontSize: "15px" }}>{wf.title}</h4>

                <div style={{ fontSize: "12.5px", color: "var(--color-text-secondary)" }}>
                  {formatAgentHumanLabel(wf.agent_ref)} ·{" "}
                  {isGoalDriven
                    ? modesCopy.goalSummaryPrefix
                    : `${activeSubStepsCount} ${modesCopy.milestoneSummarySuffix}`}
                </div>
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "8px",
                  flexWrap: "wrap",
                  paddingTop: "4px",
                }}
              >
                <button
                  type="button"
                  data-testid={`execute-workflow-btn-${wf.id}`}
                  onClick={() => onExecuteWorkflow(wf.id)}
                  className="orcia-ds-btn-primary"
                  style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
                >
                  <OrciaIcon name="play" />
                  <span>{isFr ? "Lancer ce processus" : "Launch process"}</span>
                </button>

                <button
                  type="button"
                  data-testid={`open-studio-btn-${wf.id}`}
                  onClick={() => onOpenStudio(wf.id)}
                  className="orcia-ds-btn-secondary"
                >
                  {isFr ? "Adapter dans le Studio" : "Customize in Studio"}
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
