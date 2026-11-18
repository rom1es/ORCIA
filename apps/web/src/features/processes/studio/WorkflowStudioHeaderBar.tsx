import { ContextualInfoTriggerButton, OrciaAlertBanner, OrciaIcon } from "@orcia/ui";
import React from "react";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";

export type StudioViewMode = "design" | "what_if" | "yaml";

export interface StudioStatusBannerState {
  readonly message: string;
  readonly tone: "success" | "error";
}

export interface WorkflowStudioHeaderBarProps {
  readonly workflow: WorkflowDefinitionV2Item;
  readonly viewMode: StudioViewMode;
  readonly isFr: boolean;
  readonly statusBanner: StudioStatusBannerState | null;
  readonly hasActiveAutonomyContract: boolean;
  readonly autonomyButtonLabel: string;
  readonly autonomyActiveBadgeLabel: string;
  readonly triggersButtonLabel: string;
  readonly activeTriggersCount: number;
  readonly onBackToHub: () => void;
  readonly onOpenParentVsm: () => void;
  readonly onSelectViewMode: (mode: StudioViewMode) => void;
  readonly onSaveAsDraft: () => void;
  readonly onPublishWorkflow: () => void;
  readonly onOpenRunDrawer: () => void;
  readonly onOpenHelpSection: (sectionId: string) => void;
  readonly onOpenAutonomyContract: () => void;
  readonly onOpenTriggers: () => void;
}

export function WorkflowStudioHeaderBar({
  workflow,
  viewMode,
  isFr,
  statusBanner,
  hasActiveAutonomyContract,
  autonomyButtonLabel,
  autonomyActiveBadgeLabel,
  triggersButtonLabel,
  activeTriggersCount,
  onBackToHub,
  onOpenParentVsm,
  onSelectViewMode,
  onSaveAsDraft,
  onPublishWorkflow,
  onOpenRunDrawer,
  onOpenHelpSection,
  onOpenAutonomyContract,
  onOpenTriggers,
}: WorkflowStudioHeaderBarProps) {
  return (
    <>
      <header
        className="orcia-bento-card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <button
              type="button"
              data-testid="studio-back-to-hub-btn"
              onClick={onBackToHub}
              className="orcia-ds-btn-secondary"
            >
              {isFr ? "← Retour à Mes Processus" : "← Back to My Processes"}
            </button>
            {workflow.vsm_step_num ? (
              <button
                type="button"
                data-testid="studio-open-parent-vsm-btn"
                onClick={onOpenParentVsm}
                className="orcia-ds-btn-secondary"
                style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
              >
                <OrciaIcon name="compass" />
                <span>
                  {isFr
                    ? `Voir l'Étape ${workflow.vsm_step_num} dans la chaîne de valeur`
                    : `View Step ${workflow.vsm_step_num} in Value Stream`}
                </span>
              </button>
            ) : null}
            <span
              data-testid="studio-workflow-version-badge"
              className="rounded px-2.5 py-0.5 text-xs font-semibold"
              style={{
                backgroundColor:
                  workflow.status === "published"
                    ? "var(--color-gate-emerald-bg)"
                    : "var(--color-arbitration-bg)",
                color:
                  workflow.status === "published"
                    ? "var(--color-gate-emerald)"
                    : "var(--color-arbitration-amber)",
              }}
            >
              {workflow.status === "published"
                ? isFr
                  ? `Actif · v${workflow.version}`
                  : `Active · v${workflow.version}`
                : isFr
                  ? `En préparation · v${workflow.version}`
                  : `Draft · v${workflow.version}`}
              <span className="sr-only">{` v${workflow.version} (${workflow.status})`}</span>
            </span>
            {hasActiveAutonomyContract ? (
              <span
                data-testid="studio-autonomy-contract-active-badge"
                className="inline-flex items-center gap-1 rounded px-2.5 py-0.5 text-xs font-semibold"
                style={{
                  backgroundColor: "var(--color-ontology-bg)",
                  color: "var(--color-ontology-cyan)",
                }}
              >
                <OrciaIcon name="shield" size={12} />
                <span>{autonomyActiveBadgeLabel}</span>
              </span>
            ) : null}
            <ContextualInfoTriggerButton
              sectionId="workflows-overview"
              label={
                isFr
                  ? "Comprendre l'Atelier de Processus"
                  : "Understand the Process Studio"
              }
              onOpenHelpSection={onOpenHelpSection}
            />
          </div>
          <h1 style={{ margin: "6px 0 0 0", fontSize: "var(--font-size-h2)" }}>
            {isFr
              ? `Atelier d'adaptation — ${workflow.title}`
              : `Process Studio — ${workflow.title}`}
          </h1>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <div
            role="tablist"
            aria-label={isFr ? "Modes de l'atelier" : "Studio view modes"}
            className="orcia-ds-tabs"
          >
            {(
              [
                {
                  key: "design",
                  testId: "studio-view-mode-design",
                  label: isFr ? "Étapes & Règles" : "Steps & Rules",
                },
                {
                  key: "what_if",
                  testId: "studio-view-mode-whatif",
                  label: isFr ? "Simuler l'impact" : "Simulate impact",
                },
                {
                  key: "yaml",
                  testId: "studio-view-mode-yaml",
                  label: isFr ? "Définition" : "Specification",
                },
              ] as const
            ).map((tab) => (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={viewMode === tab.key}
                data-testid={tab.testId}
                onClick={() => onSelectViewMode(tab.key)}
                className="orcia-ds-tab"
              >
                {tab.label}
              </button>
            ))}
          </div>

          <button
            type="button"
            data-testid="studio-autonomy-contract-btn"
            onClick={onOpenAutonomyContract}
            className="orcia-ds-btn-secondary inline-flex items-center gap-1.5"
          >
            <OrciaIcon name="shield" size={14} />
            <span>{autonomyButtonLabel}</span>
          </button>

          <button
            type="button"
            data-testid="studio-triggers-btn"
            onClick={onOpenTriggers}
            className="orcia-ds-btn-secondary inline-flex items-center gap-1.5"
          >
            <OrciaIcon name="lightning" size={14} />
            <span>
              {activeTriggersCount > 0
                ? `${triggersButtonLabel} (${activeTriggersCount})`
                : triggersButtonLabel}
            </span>
          </button>

          <button
            type="button"
            data-testid="studio-save-draft-btn"
            onClick={onSaveAsDraft}
            className="orcia-ds-btn-secondary"
          >
            {isFr ? "Enregistrer le brouillon" : "Save draft"}
          </button>

          <button
            type="button"
            data-testid="studio-publish-workflow-btn"
            onClick={onPublishWorkflow}
            className="orcia-ds-btn-secondary"
          >
            {isFr ? "Publier" : "Publish"}
          </button>

          <button
            type="button"
            data-testid="studio-launch-interactive-run-btn"
            onClick={onOpenRunDrawer}
            className="orcia-ds-btn-primary"
            style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
          >
            <OrciaIcon name="play" />
            <span>{isFr ? "Tester l'exécution" : "Test run"}</span>
          </button>
        </div>
      </header>

      {statusBanner ? (
        statusBanner.tone === "error" ? (
          <OrciaAlertBanner tone="crimson" role="alert" testId="studio-status-banner">
            {statusBanner.message}
          </OrciaAlertBanner>
        ) : (
          <div
            role="status"
            data-testid="studio-status-banner"
            className="rounded border px-3 py-2 text-xs font-medium"
            style={{
              backgroundColor: "var(--color-gate-emerald-bg)",
              borderColor: "var(--color-gate-emerald)",
              color: "var(--color-text-primary)",
            }}
          >
            {statusBanner.message}
          </div>
        )
      ) : null}
    </>
  );
}
