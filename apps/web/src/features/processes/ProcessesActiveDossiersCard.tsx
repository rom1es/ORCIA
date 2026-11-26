import type { ProcessPendingRunItemResponse } from "@orcia/api-client";
import { OrciaDataCard, OrciaIcon, StatusBadge } from "@orcia/ui";
import React from "react";
import { formatI18nTemplate, useI18n } from "../../i18n";
import {
  extractAgentSlugFromRef,
  formatAgentHumanLabel,
} from "./execution/interactiveRunFormatters";
import type { WorkflowDefinitionV2Item } from "./processStudioV2Data";

export interface ProcessesActiveDossiersCardProps {
  readonly pendingRuns: readonly ProcessPendingRunItemResponse[];
  readonly workflows: readonly WorkflowDefinitionV2Item[];
  readonly isLoadingPendingRuns: boolean;
  readonly onOpenPendingRun: (run: ProcessPendingRunItemResponse) => void;
}

export function resolveWorkflowForPendingRun(
  run: ProcessPendingRunItemResponse,
  workflows: readonly WorkflowDefinitionV2Item[],
): WorkflowDefinitionV2Item {
  const exact = workflows.find(
    (w) =>
      (run.workflow_id && w.id === run.workflow_id) ||
      (run.workflow_slug && w.slug === run.workflow_slug),
  );
  if (exact) return exact;

  const byActor = workflows.find(
    (w) => extractAgentSlugFromRef(w.agent_ref) === run.actor_slug,
  );
  if (byActor) return byActor;

  return {
    id: run.workflow_id || run.run_id,
    slug: run.workflow_slug || run.run_id,
    title: run.workflow_title || run.run_id,
    pack_id: "orcia-pack-custom",
    vsm_step_num: null,
    version: "1.0.0",
    status: "published",
    orchestration_type: "non_deterministic",
    reflexive_objective: run.workflow_title || null,
    execution_mode: "native_orcia",
    agent_ref: run.actor_slug || "@assistant",
    skills_refs: [],
    knowledge_base_refs: [],
    triggers: [],
    contract: { inputs: [], outputs: [], exit_criteria: [] },
    sub_steps: [],
    controls: { deterministic_gates: [], probabilistic_evaluations: [] },
    guardrails: [],
  };
}

export function ProcessesActiveDossiersCard({
  pendingRuns,
  workflows,
  isLoadingPendingRuns,
  onOpenPendingRun,
}: ProcessesActiveDossiersCardProps): React.JSX.Element {
  const { locale, dictionary } = useI18n();
  const copy = dictionary.processStudioUi.hub;
  const pendingCount = pendingRuns.filter((r) => r.is_pending).length;
  const featuredPendingRun = pendingRuns[0] ?? null;

  const metaBadgeLabel =
    pendingCount === 0
      ? copy.noPendingValidationsBadge
      : pendingCount === 1
        ? copy.pendingValidationSingleBadge
        : formatI18nTemplate(copy.pendingValidationsPluralBadgeTemplate, {
            count: pendingCount,
          });

  return (
    <OrciaDataCard
      testId="processes-active-dossiers-card"
      title={copy.activeDossiersTitle}
      subtitle={copy.activeDossiersSubtitle}
      metaBadge={
        <StatusBadge
          tone={pendingCount > 0 ? "amber" : "neutral"}
          label={metaBadgeLabel}
        />
      }
      actions={
        featuredPendingRun ? (
          <button
            type="button"
            data-testid="resume-featured-dossier-btn"
            onClick={() => onOpenPendingRun(featuredPendingRun)}
            className="orcia-ds-btn orcia-ds-btn-cobalt-outline orcia-ds-btn-sm orcia-ds-nowrap"
          >
            <OrciaIcon name="play" />
            <span>{copy.reviewPendingDossierBtn}</span>
          </button>
        ) : null
      }
    >
      {pendingRuns.length === 0 ? (
        <div
          data-testid="processes-empty-pending-runs"
          className="rounded border p-3 text-xs"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-secondary)",
          }}
        >
          <strong
            className="block text-sm font-semibold"
            style={{ color: "var(--color-text-primary)" }}
          >
            {isLoadingPendingRuns
              ? copy.loadingPendingRunsLabel
              : copy.emptyPendingRunsTitle}
          </strong>
          {!isLoadingPendingRuns ? (
            <p className="mt-1 mb-0">{copy.emptyPendingRunsBody}</p>
          ) : null}
        </div>
      ) : null}

      {pendingRuns.length > 0 ? (
        <div className="space-y-2" data-testid="processes-pending-runs-list">
          {pendingRuns.map((run) => {
            const matchedWf = workflows.find(
              (w) =>
                (run.workflow_id && w.id === run.workflow_id) ||
                (run.workflow_slug && w.slug === run.workflow_slug),
            );
            const title =
              run.workflow_title || matchedWf?.title || run.workflow_slug || run.run_id;
            const statusLabel =
              copy.pendingRunStatusLabels[run.status] ?? run.status;
            const actorLabel = formatAgentHumanLabel(
              matchedWf?.agent_ref ?? run.actor_slug,
              locale,
            );
            return (
              <div
                key={run.run_id}
                data-testid={`pending-run-row-${run.run_id}`}
                className="rounded border p-3"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      flexWrap: "wrap",
                    }}
                  >
                    <strong style={{ fontSize: "14px" }}>
                      {copy.featuredDossierPrefix} — {title}
                    </strong>
                    <span
                      data-testid={`pending-run-status-${run.run_id}`}
                      className="rounded px-2 py-0.5 text-xs font-semibold"
                      style={{
                        backgroundColor: "var(--color-action-primary-subtle)",
                        color: "var(--color-primary-cobalt)",
                      }}
                    >
                      {statusLabel}
                    </span>
                  </div>
                  <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
                    {actorLabel} · {run.run_id}
                  </span>
                </div>

                <button
                  type="button"
                  data-testid={`open-pending-run-btn-${run.run_id}`}
                  onClick={() => onOpenPendingRun(run)}
                  className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
                >
                  {copy.openDeliverableBtn}
                </button>
              </div>
            );
          })}
        </div>
      ) : null}
    </OrciaDataCard>
  );
}
