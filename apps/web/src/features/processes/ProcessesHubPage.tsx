import { ContextualInfoTriggerButton, OrciaIcon } from "@orcia/ui";
import React, { useEffect, useState } from "react";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import {
  formatAgentHumanLabel,
  InteractiveRunDrawer,
} from "./execution/InteractiveRunDrawer";
import {
  ProcessCatalogCardGrid,
  type WorkflowHubFilter,
} from "./ProcessCatalogCardGrid";
import {
  INITIAL_VSM_SPEC,
  loadPersistedWorkflowsV2,
  savePersistedWorkflowV2,
  type WorkflowDefinitionV2Item,
} from "./processStudioV2Data";
import {
  createProcessesApiClient,
  mapApiWorkflowV2ToUiItem,
} from "./studio/studioLabelsAndMappers";
import {
  readPersistedReflexiveId,
  writePersistedReflexiveId,
} from "../shared/reflexiveTraceMappers";

export type { WorkflowHubFilter };

export const ACTIVE_PROCESS_RUN_WORKFLOW_STORAGE_KEY =
  "orcia.processes.active_run_workflow_id.v1";

export function ProcessesHubPage() {
  const { locale, dictionary } = useI18n();
  const { navigateToRoute, openHelpSection } = useShellNavigation();
  const isFr = locale === "fr";
  const modesCopy = dictionary.processOrchestrationModes;

  const [workflows, setWorkflows] = useState<WorkflowDefinitionV2Item[]>(() =>
    loadPersistedWorkflowsV2(),
  );
  const [filter, setFilter] = useState<WorkflowHubFilter>("all");
  const [activeRunWorkflowId, setActiveRunWorkflowIdState] = useState<
    string | null
  >(() => readPersistedReflexiveId(ACTIVE_PROCESS_RUN_WORKFLOW_STORAGE_KEY));
  const setActiveRunWorkflowId = (nextId: string | null) => {
    setActiveRunWorkflowIdState(nextId);
    writePersistedReflexiveId(ACTIVE_PROCESS_RUN_WORKFLOW_STORAGE_KEY, nextId);
  };
  const [hubErrorBanner, setHubErrorBanner] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    createProcessesApiClient(locale)
      .listWorkflowsV2()
      .then((res) => {
        if (cancelled || !Array.isArray(res?.items) || res.items.length === 0) {
          return;
        }
        setWorkflows((prev) => {
          const mapped = res.items.map((apiWf) => {
            const existing = prev.find((p) => p.id === apiWf.id || p.slug === apiWf.slug);
            const uiItem = mapApiWorkflowV2ToUiItem(apiWf, existing);
            savePersistedWorkflowV2(uiItem);
            return uiItem;
          });
          return mapped;
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const detail = err instanceof Error ? err.message : String(err);
        setHubErrorBanner(
          isFr
            ? `Impossible d'actualiser le catalogue de processus depuis le serveur (${detail}).`
            : `Unable to refresh processes catalog from server (${detail}).`,
        );
      });
    return () => {
      cancelled = true;
    };
  }, [locale, isFr]);

  const activeRunWorkflow =
    workflows.find((w) => w.id === activeRunWorkflowId) ?? null;
  const featuredPendingWorkflow = workflows[0] ?? null;

  return (
    <section
      data-testid="processes-hub-v2-page"
      style={{ display: "flex", flexDirection: "column", gap: "18px" }}
    >
      {hubErrorBanner ? (
        <div
          role="alert"
          data-testid="processes-hub-error-banner"
          className="rounded border px-3 py-2 text-xs font-medium"
          style={{
            backgroundColor: "var(--color-stale-bg)",
            borderColor: "var(--color-stale-crimson)",
            color: "var(--color-text-primary)",
          }}
        >
          {hubErrorBanner}
        </div>
      ) : null}

      {/* ZONE 1 (PRIORITÉ 1) : DOSSIERS EN COURS & ACTIONS ATTENDUES */}
      <div
        data-testid="processes-active-dossiers-card"
        className="orcia-bento-card"
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "12px",
          borderLeft: "4px solid var(--color-primary-cobalt)",
        }}
      >
        <div
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
              <span
                className="rounded px-2.5 py-0.5 text-xs font-semibold"
                style={{
                  backgroundColor: "var(--color-arbitration-bg)",
                  color: "var(--color-arbitration-amber)",
                }}
              >
                {isFr ? "1 validation en attente de votre décision" : "1 review awaiting your decision"}
              </span>
              <ContextualInfoTriggerButton
                sectionId="workflows-overview"
                label={isFr ? "Comprendre Mes Processus" : "Understand My Processes"}
                onOpenHelpSection={openHelpSection}
              />
            </div>
            <h2 style={{ margin: "6px 0 0 0", fontSize: "var(--font-size-h2)" }}>
              {isFr
                ? "Mes dossiers en cours & validations à traiter"
                : "Active Dossiers & Pending Reviews"}
            </h2>
            <p style={{ margin: "2px 0 0 0", fontSize: "13px", color: "var(--color-text-secondary)" }}>
              {isFr
                ? "Examinez les livrables préparés par vos agents, validez les étapes clés ou demandez des ajustements sans quitter cette page."
                : "Review deliverables prepared by your agents, approve milestones, or request adjustments directly from this page."}
            </p>
          </div>

          {featuredPendingWorkflow && !activeRunWorkflow ? (
            <button
              type="button"
              data-testid="resume-featured-dossier-btn"
              onClick={() => setActiveRunWorkflowId(featuredPendingWorkflow.id)}
              className="orcia-ds-btn-primary"
              style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
            >
              <OrciaIcon name="play" />
              <span>
                {isFr
                  ? "Examiner & Valider le dossier en attente"
                  : "Review & Approve Pending Dossier"}
              </span>
            </button>
          ) : null}
        </div>

        {featuredPendingWorkflow && !activeRunWorkflow ? (
          <div
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
              <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                <strong style={{ fontSize: "14px" }}>
                  Dossier « Mon Compte » — {featuredPendingWorkflow.title}
                </strong>
                <span
                  className="rounded px-2 py-0.5 text-xs font-semibold"
                  style={{
                    backgroundColor: "var(--color-action-primary-subtle)",
                    color: "var(--color-primary-cobalt)",
                  }}
                >
                  {isFr ? "Étape 1/3 : Qualification du besoin" : "Step 1/3: Qualification"}
                </span>
              </div>
              <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
                {formatAgentHumanLabel(featuredPendingWorkflow.agent_ref)} ·{" "}
                {isFr
                  ? "Livrable prêt pour relecture et validation Product Owner"
                  : "Deliverable ready for Product Owner review"}
              </span>
            </div>

            <button
              type="button"
              onClick={() => setActiveRunWorkflowId(featuredPendingWorkflow.id)}
              className="orcia-ds-btn-secondary"
            >
              {isFr ? "Ouvrir le livrable" : "Open deliverable"}
            </button>
          </div>
        ) : null}

        {activeRunWorkflow ? (
          <InteractiveRunDrawer
            key={activeRunWorkflow.id}
            workflow={activeRunWorkflow}
            onClose={() => setActiveRunWorkflowId(null)}
            isFr={isFr}
          />
        ) : null}
      </div>

      {/* ZONE 2 : PROCESSUS MÉTIERS DISPONIBLES PAR ÉTAPE */}
      <ProcessCatalogCardGrid
        workflows={workflows}
        filter={filter}
        modesCopy={modesCopy}
        isFr={isFr}
        onChangeFilter={setFilter}
        onExecuteWorkflow={(wfId) => setActiveRunWorkflowId(wfId)}
        onOpenStudio={(wfId) => navigateToRoute(`/processes/studio/${wfId}`)}
      />

      {/* ZONE 3 : VUE D'ENSEMBLE DE LA CHAÎNE DE VALEUR (4 PHASES · 11 ÉTAPES) */}
      <div
        data-testid="processes-hub-vsm-hero-card"
        className="orcia-bento-card"
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <span
              style={{
                fontSize: "12px",
                fontWeight: 700,
                color: "var(--color-primary-cobalt)",
              }}
            >
              {isFr
                ? "VUE D'ENSEMBLE DU PARCOURS MÉTIER (4 PHASES · 11 ÉTAPES)"
                : "END-TO-END VALUE STREAM (4 PHASES · 11 STEPS)"}
            </span>
            <h3 style={{ margin: 0, fontSize: "var(--font-size-h3)" }}>
              {INITIAL_VSM_SPEC.title} — {INITIAL_VSM_SPEC.subtitle}
            </h3>
            <p style={{ margin: 0, fontSize: "13px", color: "var(--color-text-secondary)" }}>
              {isFr
                ? "Visualisez comment s'articulent les 11 étapes entre les équipes et les agents IA, les points de validation humaine et l'évolution des pratiques."
                : "Explore how the 11 steps connect teams and AI agents, human decision points, and process improvements."}
            </p>
          </div>

          <button
            type="button"
            data-testid="open-interactive-vsm-btn"
            onClick={() => navigateToRoute(`/processes/vsm/${INITIAL_VSM_SPEC.id}`)}
            className="orcia-ds-btn-secondary"
            style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
          >
            <OrciaIcon name="compass" />
            <span>
              {isFr
                ? "Explorer la chaîne de valeur complète (11 étapes)"
                : "Explore full 11-step Value Stream"}
            </span>
          </button>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
            gap: "10px",
          }}
        >
          {INITIAL_VSM_SPEC.phases.map((phase) => (
            <div
              key={phase.num}
              data-testid={`vsm-hero-phase-${phase.num}`}
              className="rounded border p-2.5"
              style={{
                backgroundColor: "var(--color-bg-elevated)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    color: "var(--color-primary-cobalt)",
                  }}
                >
                  {isFr
                    ? `Phase ${phase.num} · Étapes ${phase.steps_range}`
                    : `Phase ${phase.num} · Steps ${phase.steps_range}`}
                </span>
                <span style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
                  {phase.steps.length} {isFr ? "étapes" : "steps"}
                </span>
              </div>
              <div style={{ fontWeight: 700, fontSize: "13.5px", marginTop: "2px" }}>
                {phase.name}
              </div>
              <div style={{ fontSize: "11.5px", color: "var(--color-text-secondary)", marginTop: "2px" }}>
                {phase.goal}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
