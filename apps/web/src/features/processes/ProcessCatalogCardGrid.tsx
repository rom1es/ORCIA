import { OrciaDataCard, OrciaIcon } from "@orcia/ui";
import React from "react";
import {
  formatI18nTemplate,
  resolveDictionaryForFlag,
  resolveLocaleForFlag,
} from "../../i18n";
import type { ProcessOrchestrationModesCopy } from "../../i18n/locales/process_orchestration_modes_labels";
import { formatAgentHumanLabel } from "./execution/InteractiveRunDrawer";
import type { WorkflowDefinitionV2Item } from "./processStudioV2Data";

export type WorkflowHubFilter = "all" | "published" | "draft" | "external_delegated";

export interface ProcessCatalogCardGridProps {
  readonly workflows: readonly WorkflowDefinitionV2Item[];
  readonly filter: WorkflowHubFilter;
  readonly modesCopy: ProcessOrchestrationModesCopy;
  readonly isFr: boolean;
  readonly launchingWorkflowId?: string | null;
  readonly readOnlyObserver?: boolean;
  readonly onChangeFilter: (nextFilter: WorkflowHubFilter) => void;
  readonly onExecuteWorkflow: (workflowId: string) => void;
  readonly onOpenStudio: (workflowId: string) => void;
  readonly onDeleteWorkflow?: (workflowId: string) => void;
}

export function ProcessCatalogCardGrid({
  workflows,
  filter,
  modesCopy,
  isFr,
  launchingWorkflowId = null,
  readOnlyObserver = false,
  onChangeFilter,
  onExecuteWorkflow,
  onOpenStudio,
  onDeleteWorkflow,
}: ProcessCatalogCardGridProps) {
  const locale = resolveLocaleForFlag(isFr);
  const dict = resolveDictionaryForFlag(isFr);
  const copy = dict.processStudioUi.hub;
  const deleteWorkflowLabel = dict.packsUi.actions.deleteWorkflowConfirmLabel;

  const filteredWorkflows = workflows.filter((wf) => {
    if (filter === "published") return wf.status === "published";
    if (filter === "draft") return wf.status === "draft";
    if (filter === "external_delegated") return wf.execution_mode === "external_delegated";
    return true;
  });

  const filterControls = (
    <div
      role="tablist"
      aria-label={copy.filterProcessesAriaLabel}
      className="orcia-ds-tabs"
    >
      {(
        [
          { key: "all", label: copy.filterAll },
          { key: "published", label: copy.filterActive },
          { key: "draft", label: copy.filterDrafts },
          { key: "external_delegated", label: copy.filterExternalIde },
        ] as const
      ).map((tab) => (
        <button
          key={tab.key}
          type="button"
          role="tab"
          aria-selected={filter === tab.key}
          data-testid={`workflows-hub-filter-${tab.key}`}
          onClick={() => onChangeFilter(tab.key)}
          className="orcia-ds-filter-pill"
        >
          {tab.label}
        </button>
      ))}
    </div>
  );

  return (
    <OrciaDataCard
      testId="processes-catalog-card"
      title={copy.availableProcessesTitle}
      subtitle={copy.availableProcessesSubtitle}
      actions={filterControls}
    >

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
                      ? formatI18nTemplate(copy.stepNumberBadgeTemplate, { num: wf.vsm_step_num })
                      : copy.crossCuttingProcessBadge}
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
                        {copy.ideAndTeamBadge}
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
                        ? copy.statusActiveBadge
                        : copy.statusDraftBadge}
                    </span>
                  </div>
                </div>

                <h4 style={{ margin: 0, fontSize: "15px" }}>{wf.title}</h4>

                <div style={{ fontSize: "12.5px", color: "var(--color-text-secondary)" }}>
                  {formatAgentHumanLabel(wf.agent_ref, locale)} ·{" "}
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
                  disabled={launchingWorkflowId === wf.id}
                  onClick={() => onExecuteWorkflow(wf.id)}
                  className="orcia-ds-btn orcia-ds-btn-cobalt-outline orcia-ds-btn-sm"
                >
                  <OrciaIcon name="play" />
                  <span>
                    {launchingWorkflowId === wf.id
                      ? copy.launchingRunBtn
                      : copy.launchProcessBtn}
                  </span>
                </button>

                <div className="flex flex-wrap items-center gap-1.5">
                  <button
                    type="button"
                    data-testid={`open-studio-btn-${wf.id}`}
                    onClick={() => onOpenStudio(wf.id)}
                    className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
                  >
                    {copy.customizeInStudioBtn}
                  </button>
                  {onDeleteWorkflow && wf.pack_id === "orcia-pack-custom" ? (
                    <button
                      type="button"
                      data-testid={`delete-workflow-btn-${wf.id}`}
                      disabled={readOnlyObserver}
                      onClick={() => onDeleteWorkflow(wf.id)}
                      className="orcia-ds-btn orcia-ds-btn-danger orcia-ds-btn-sm"
                    >
                      {deleteWorkflowLabel}
                    </button>
                  ) : null}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </OrciaDataCard>
  );
}
