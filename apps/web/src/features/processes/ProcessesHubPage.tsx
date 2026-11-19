import { ContextualInfoTriggerButton, OrciaAlertBanner, OrciaIcon } from "@orcia/ui";
import React, { useEffect, useState } from "react";
import { CreateProcessFormDialog } from "../../components/CreateProcessFormDialog";
import { useOptionalPlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import {
  formatAgentHumanLabel,
  InteractiveRunDrawer,
} from "./execution/InteractiveRunDrawer";
import {
  ProcessCatalogCardGrid,
  type WorkflowHubFilter,
} from "./ProcessCatalogCardGrid";
import {
  loadPersistedWorkflowsV2,
  savePersistedWorkflowV2,
  type WorkflowDefinitionV2Item,
} from "./processStudioV2Data";
import { AutonomousRunsSupervisionPanel } from "./AutonomousRunsSupervisionPanel";
import { ProcessesValueStreamOverviewCard } from "./ProcessesValueStreamOverviewCard";
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
  const setupCtx = useOptionalPlatformSetup();
  const isFr = locale === "fr";
  const modesCopy = dictionary.processOrchestrationModes;
  const [isCreateProcessOpen, setIsCreateProcessOpen] = useState(false);

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
        const formatted = formatRfc9457ErrorToBanner(
          err,
          isFr ? "fr" : "en",
          isFr ? "Catalogue de processus" : "Processes catalog",
        );
        setHubErrorBanner(formatted.fullText);
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
        <OrciaAlertBanner tone="crimson" role="alert" testId="processes-hub-error-banner">
          {hubErrorBanner}
        </OrciaAlertBanner>
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
        onOpenCreateProcess={() => setIsCreateProcessOpen(true)}
      />

      <CreateProcessFormDialog
        open={isCreateProcessOpen}
        onOpenChange={setIsCreateProcessOpen}
        isFr={isFr}
        openHelpSection={openHelpSection}
        upsertWorkflow={(item) => {
          setupCtx?.upsertWorkflow(item);
          const createdV2: WorkflowDefinitionV2Item = {
            id: item.workflowKey,
            slug: item.workflowKey,
            title: item.title,
            pack_id: "orcia-pack-custom",
            vsm_step_num: null,
            version: item.version,
            status: item.status === "PUBLISHED" ? "published" : "draft",
            orchestration_type: "deterministic_dbos",
            reflexive_objective: item.prePrompt || item.title,
            execution_mode: "native_orcia",
            agent_ref: "@assistant",
            skills_refs: [],
            knowledge_base_refs: [],
            triggers: [],
            contract: {
              inputs: [],
              outputs: [],
              exit_criteria: [],
            },
            sub_steps: [],
            controls: {
              deterministic_gates: [],
              probabilistic_evaluations: [],
            },
            guardrails: [],
          };
          savePersistedWorkflowV2(createdV2);
          setWorkflows((prev) => [
            createdV2,
            ...prev.filter((p) => p.id !== createdV2.id),
          ]);
        }}
      />

      {/* ZONE 2B : SUPERVISION DES EXÉCUTIONS AUTOMATISÉES SOUS CONTRAT (STORY 7.4) */}
      <AutonomousRunsSupervisionPanel />

      {/* ZONE 3 : VUE D'ENSEMBLE DE LA CHAÎNE DE VALEUR (4 PHASES · 11 ÉTAPES) */}
      <ProcessesValueStreamOverviewCard
        isFr={isFr}
        onOpenInteractiveVsm={(vsmId) => navigateToRoute(`/processes/vsm/${vsmId}`)}
      />
    </section>
  );
}
