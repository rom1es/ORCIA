import React, { useState } from "react";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import {
  formatAgentHumanLabel,
  InteractiveRunDrawer,
} from "./execution/InteractiveRunDrawer";
import {
  INITIAL_VSM_SPEC,
  loadPersistedWorkflowsV2,
  type WorkflowDefinitionV2Item,
} from "./processStudioV2Data";

export type WorkflowHubFilter = "all" | "published" | "draft" | "external_delegated";

export function ProcessesHubPage() {
  const { locale } = useI18n();
  const { navigateToRoute } = useShellNavigation();
  const isFr = locale === "fr";

  const [workflows] = useState<WorkflowDefinitionV2Item[]>(() => loadPersistedWorkflowsV2());
  const [filter, setFilter] = useState<WorkflowHubFilter>("all");
  const [activeRunWorkflowId, setActiveRunWorkflowId] = useState<string | null>(null);

  const filteredWorkflows = workflows.filter((wf) => {
    if (filter === "published") return wf.status === "published";
    if (filter === "draft") return wf.status === "draft";
    if (filter === "external_delegated") return wf.execution_mode === "external_delegated";
    return true;
  });

  const activeRunWorkflow =
    workflows.find((w) => w.id === activeRunWorkflowId) ?? null;
  const featuredPendingWorkflow = workflows[0] ?? null;

  return (
    <section
      data-testid="processes-hub-v2-page"
      style={{ display: "flex", flexDirection: "column", gap: "18px" }}
    >
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
            <span
              className="rounded px-2.5 py-0.5 text-xs font-semibold"
              style={{
                backgroundColor: "var(--color-arbitration-bg)",
                color: "var(--color-arbitration-amber)",
              }}
            >
              {isFr ? "1 validation en attente de votre décision" : "1 review awaiting your decision"}
            </span>
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
            >
              {isFr
                ? "▷ Examiner & Valider le dossier en attente"
                : "▷ Review & Approve Pending Dossier"}
            </button>
          ) : null}
        </div>

        {/* Résumé du dossier en attente lorsque le tiroir n'est pas encore déployé */}
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

        {/* Espace d'Exécution & Revue de Livrable directement intégré dans Mes Processus */}
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
            aria-label="Filtrer les processus"
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
                onClick={() => setFilter(tab.key)}
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
                    {formatAgentHumanLabel(wf.agent_ref)} · {activeSubStepsCount}{" "}
                    {isFr ? "étape(s) guidée(s)" : "guided step(s)"}
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
                    onClick={() => setActiveRunWorkflowId(wf.id)}
                    className="orcia-ds-btn-primary"
                  >
                    {isFr ? "▷ Lancer ce processus" : "▷ Launch process"}
                  </button>

                  <button
                    type="button"
                    data-testid={`open-studio-btn-${wf.id}`}
                    onClick={() => navigateToRoute(`/processes/studio/${wf.id}`)}
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
          >
            {isFr
              ? "🗺️ Explorer la chaîne de valeur complète (11 étapes)"
              : "🗺️ Explore full 11-step Value Stream"}
          </button>
        </div>

        {/* Synthèse des 4 Phases */}
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
                  Phase {phase.num} · Étapes {phase.steps_range}
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
