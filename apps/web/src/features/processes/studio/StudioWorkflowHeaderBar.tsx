import { OrciaIcon } from "@orcia/ui";
import React from "react";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";

export type StudioViewMode = "design" | "what_if" | "yaml";

export interface StudioWorkflowHeaderBarProps {
  readonly workflow: WorkflowDefinitionV2Item;
  readonly viewMode: StudioViewMode;
  readonly isFr: boolean;
  readonly hasWhatIfResult: boolean;
  readonly hasActiveAutonomyContract: boolean;
  readonly autonomyButtonLabel: string;
  readonly autonomyActiveBadgeLabel: string;
  readonly onNavigateBack: () => void;
  readonly onNavigateVsm: () => void;
  readonly onSelectViewMode: (mode: StudioViewMode) => void;
  readonly onRunWhatIf: () => void;
  readonly onSaveDraft: () => void;
  readonly onPublish: () => void;
  readonly onLaunchRun: () => void;
  readonly onOpenAutonomyContract: () => void;
}

export function StudioWorkflowHeaderBar({
  workflow,
  viewMode,
  isFr,
  hasWhatIfResult,
  hasActiveAutonomyContract,
  autonomyButtonLabel,
  autonomyActiveBadgeLabel,
  onNavigateBack,
  onNavigateVsm,
  onSelectViewMode,
  onRunWhatIf,
  onSaveDraft,
  onPublish,
  onLaunchRun,
  onOpenAutonomyContract,
}: StudioWorkflowHeaderBarProps): React.ReactElement {
  return (
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
            onClick={onNavigateBack}
            className="orcia-ds-btn-secondary"
          >
            {isFr ? "← Retour à Mes Processus" : "← Back to My Processes"}
          </button>
          {workflow.vsm_step_num ? (
            <button
              type="button"
              data-testid="studio-open-parent-vsm-btn"
              onClick={onNavigateVsm}
              className="orcia-ds-btn-secondary"
            >
              {isFr
                ? `🗺️ Voir l'Étape ${workflow.vsm_step_num} dans la chaîne de valeur`
                : `🗺️ View Step ${workflow.vsm_step_num} in Value Stream`}
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
        </div>
        <h1 style={{ margin: "6px 0 0 0", fontSize: "var(--font-size-h2)" }}>
          {isFr ? `Atelier d'adaptation — ${workflow.title}` : `Process Studio — ${workflow.title}`}
        </h1>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
        <div role="tablist" aria-label="Modes de l'atelier" className="orcia-ds-tabs">
          {(
            [
              { key: "design", label: isFr ? "Étapes & Règles" : "Steps & Rules" },
              { key: "what_if", label: isFr ? "Tester à blanc" : "Dry-Run Test" },
              { key: "yaml", label: isFr ? "Définition (YAML)" : "YAML Spec" },
            ] as const
          ).map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={viewMode === tab.key}
              data-testid={`studio-view-mode-${tab.key}`}
              onClick={() => {
                if (tab.key === "what_if" && !hasWhatIfResult) {
                  onRunWhatIf();
                } else {
                  onSelectViewMode(tab.key);
                }
              }}
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
          data-testid="studio-save-draft-btn"
          onClick={onSaveDraft}
          className="orcia-ds-btn-secondary"
        >
          {isFr ? "Enregistrer le brouillon" : "Save draft"}
        </button>

        <button
          type="button"
          data-testid="studio-publish-workflow-btn"
          onClick={onPublish}
          className="orcia-ds-btn-secondary"
        >
          {isFr ? "Publier" : "Publish"}
        </button>

        <button
          type="button"
          data-testid="studio-launch-interactive-run-btn"
          onClick={onLaunchRun}
          className="orcia-ds-btn-primary"
        >
          {isFr ? "▷ Tester l'exécution" : "▷ Test run"}
        </button>
      </div>
    </header>
  );
}
