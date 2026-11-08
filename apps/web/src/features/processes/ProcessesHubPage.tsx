import React, { useState } from "react";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
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

  const filteredWorkflows = workflows.filter((wf) => {
    if (filter === "published") return wf.status === "published";
    if (filter === "draft") return wf.status === "draft";
    if (filter === "external_delegated") return wf.execution_mode === "external_delegated";
    return true;
  });

  return (
    <section
      data-testid="processes-hub-v2-page"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      {/* NIVEAU 1 : CHAÎNE DE VALEUR MÉTIER INTERACTIVE (MACRO-VSM) */}
      <div
        data-testid="processes-hub-vsm-hero-card"
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
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
              <span
                className="rounded px-2 py-0.5 text-xs font-semibold"
                style={{
                  backgroundColor: "var(--color-action-primary-subtle)",
                  color: "var(--color-primary-cobalt)",
                }}
              >
                {isFr
                  ? "NIVEAU 1 — CHAÎNE DE VALEUR INTERACTIVE (MACRO-VSM)"
                  : "LEVEL 1 — INTERACTIVE VALUE STREAM MAP (MACRO-VSM)"}
              </span>
              <span
                className="rounded px-2 py-0.5 text-xs font-semibold"
                style={{
                  backgroundColor: "var(--color-gate-emerald-bg)",
                  color: "var(--color-gate-emerald)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                packs/sdlc/workflows/vsm-mon-compte-idea-to-prod.yaml
              </span>
            </div>
            <h2 style={{ margin: 0, fontSize: "var(--font-size-h2)" }}>
              {INITIAL_VSM_SPEC.title} — {INITIAL_VSM_SPEC.subtitle}
            </h2>
            <p style={{ margin: 0, fontSize: "13px", color: "var(--color-text-secondary)" }}>
              {isFr
                ? "Cartographie bout-en-bout en 11 étapes et 4 phases (01 Cadrage, 02 Priorisation, 03 Réalisation, 04 Mise en production), avec comparaison Aujourd'hui vs Demain, 6 points de passage humains (losanges) et 13 boucles de retour."
                : "End-to-end 11-step Value Stream Map across 4 phases with Today vs Tomorrow comparison, 6 human checkpoints (diamonds), and 13 return loops."}
            </p>
          </div>

          <button
            type="button"
            data-testid="open-interactive-vsm-btn"
            onClick={() => navigateToRoute(`/processes/vsm/${INITIAL_VSM_SPEC.id}`)}
            className="orcia-ds-btn-primary"
          >
            {isFr
              ? "🗺️ Explorer la Chaîne de Valeur Interactive (11 étapes)"
              : "🗺️ Explore Interactive Value Stream Map (11 steps)"}
          </button>
        </div>

        {/* Mini Frieze of the 4 Phases */}
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
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-primary-cobalt)",
                  }}
                >
                  PHASE {phase.num} · {phase.steps_range}
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

      {/* NIVEAU 2 : WORKFLOWS EXÉCUTABLES UNITAIRES BORNÉS (DBOS) */}
      <div
        className="orcia-bento-card"
        style={{ display: "flex", flexDirection: "column", gap: "12px" }}
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
                ? "Niveau 2 — Workflows Exécutables Unitaires Bornés (DBOS Transact)"
                : "Level 2 — Bounded Executable Unit Workflows (DBOS Transact)"}
            </h3>
            <p style={{ margin: 0, fontSize: "12.5px", color: "var(--color-text-secondary)" }}>
              {isFr
                ? "Chaque étape outillée de la VSM est rattachée à un workflow DBOS court et déterministe (0 agent orchestrateur lisant le chat)."
                : "Each instrumented VSM step links to a short deterministic DBOS workflow (0 chat-reading orchestrator agent)."}
            </p>
          </div>

          <div
            role="tablist"
            aria-label="Workflow status filters"
            className="orcia-ds-tabs"
          >
            {(
              [
                { key: "all", label: isFr ? "Tous" : "All" },
                { key: "published", label: isFr ? "Publiés" : "Published" },
                { key: "draft", label: isFr ? "Brouillons (-draft)" : "Drafts (-draft)" },
                {
                  key: "external_delegated",
                  label: isFr ? "Sas Externe Délégué" : "External Gate",
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
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        fontWeight: 700,
                        color: "var(--color-primary-cobalt)",
                      }}
                    >
                      {wf.vsm_step_num ? `Étape ${wf.vsm_step_num} · ` : ""}
                      {wf.id} (v{wf.version})
                    </span>

                    <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                      <span
                        className="rounded px-2 py-0.5 text-xs font-semibold"
                        style={{
                          backgroundColor: isExternal
                            ? "var(--color-arbitration-bg)"
                            : "var(--color-action-primary-subtle)",
                          color: isExternal
                            ? "var(--color-arbitration-amber)"
                            : "var(--color-primary-cobalt)",
                        }}
                      >
                        {isExternal
                          ? isFr
                            ? "Sas Externe Délégué"
                            : "External Delegated Gate"
                          : isFr
                            ? "Natif ORCIA"
                            : "Native ORCIA"}
                      </span>
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
                            ? "Publié"
                            : "Published"
                          : isFr
                            ? "Brouillon"
                            : "Draft"}
                      </span>
                    </div>
                  </div>

                  <h4 style={{ margin: 0, fontSize: "15px" }}>{wf.title}</h4>

                  <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
                    Agent : <strong>{wf.agent_ref}</strong> ·{" "}
                    {wf.sub_steps.filter((s) => s.enabled).length}{" "}
                    {isFr ? "sous-étapes DBOS" : "DBOS sub-steps"} ·{" "}
                    {wf.controls.deterministic_gates.length}{" "}
                    {isFr ? "gate(s) déterministe(s)" : "deterministic gate(s)"}
                  </div>
                </div>

                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    data-testid={`open-studio-btn-${wf.id}`}
                    onClick={() => navigateToRoute(`/processes/studio/${wf.id}`)}
                    className="orcia-ds-btn-secondary"
                  >
                    {isFr ? "✏️ Studio 5 Blocs" : "✏️ 5-Block Studio"}
                  </button>
                  <button
                    type="button"
                    data-testid={`execute-workflow-btn-${wf.id}`}
                    onClick={() => navigateToRoute(`/processes/studio/${wf.id}`)}
                    className="orcia-ds-btn-primary"
                  >
                    {isFr ? "▷ Exécuter / Simuler" : "▷ Execute / Simulate"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
