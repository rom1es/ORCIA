import React, { useState } from "react";
import type { VsmReturnLoopItem } from "./ReturnLoopsSvgOverlay";

export type StepDetailTabKey =
  | "overview"
  | "agent_substeps"
  | "interactions"
  | "controls_gates"
  | "return_loops"
  | "opportunities";

export interface StepDetailSheetProps {
  step: {
    num: string;
    title: string;
    actor_type: string;
    actor_label: string;
    status_badge: string;
    summary: string;
    deliverable: string;
    attention_point?: string | null;
    linked_workflow_id?: string | null;
    today: {
      actors: string;
      activities: string;
      deliverable: string;
      pain_points: string;
    };
    tomorrow: {
      actors: string;
      activities: string;
      deliverable: string;
      gains: string;
    };
    passage_point?: {
      decision: string;
      question: string;
      actors: string;
      possible_outcomes: string[];
    } | null;
    detail_tabs: {
      agent_sub_steps: Array<Record<string, unknown>>;
      human_ai_interactions: Record<string, unknown>;
      controls_and_gates: Record<string, unknown>;
      complements_and_missing: string[];
      guardrails: string[];
    };
  };
  allLoops: readonly VsmReturnLoopItem[];
  onClose: () => void;
  onOpenStudio: (workflowId: string) => void;
  onExecuteWorkflow: (workflowId: string) => void;
  isFr: boolean;
}

export function StepDetailSheet({
  step,
  allLoops,
  onClose,
  onOpenStudio,
  onExecuteWorkflow,
  isFr,
}: StepDetailSheetProps) {
  const [activeTab, setActiveTab] = useState<StepDetailTabKey>("overview");

  const outgoingLoops = allLoops.filter((l) => l.from_step_num === step.num);
  const incomingLoops = allLoops.filter((l) => l.to_step_num === step.num);

  const tabs: ReadonlyArray<{ key: StepDetailTabKey; label: string }> = [
    {
      key: "overview",
      label: isFr ? "1. Vue d'ensemble & Comparaison" : "1. Overview & Comparison",
    },
    {
      key: "agent_substeps",
      label: isFr ? "2. Schéma de l'Agent & Sous-étapes" : "2. Agent Schema & Sub-steps",
    },
    {
      key: "interactions",
      label: isFr ? "3. Interactions Humain / IA" : "3. Human / AI Interactions",
    },
    {
      key: "controls_gates",
      label: isFr ? "4. Contrôles & Gates" : "4. Controls & Gates",
    },
    {
      key: "return_loops",
      label: isFr
        ? `5. Boucles de retour (${outgoingLoops.length + incomingLoops.length})`
        : `5. Return Loops (${outgoingLoops.length + incomingLoops.length})`,
    },
    {
      key: "opportunities",
      label: isFr ? "6. Compléments & Garde-fous" : "6. Complements & Guardrails",
    },
  ];

  const interactions = step.detail_tabs.human_ai_interactions ?? {};
  const controls = step.detail_tabs.controls_and_gates ?? {};

  return (
    <div
      data-testid={`vsm-step-detail-sheet-${step.num}`}
      className="orcia-bento-card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "14px",
        border: "2px solid var(--color-primary-cobalt)",
      }}
    >
      {/* Header */}
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
              className="rounded px-2 py-0.5 text-xs font-bold"
              style={{
                backgroundColor: "var(--color-action-primary-subtle)",
                color: "var(--color-primary-cobalt)",
                fontFamily: "var(--font-mono)",
              }}
            >
              ÉTAPE {step.num}
            </span>
            <span
              className="rounded px-2 py-0.5 text-xs font-semibold"
              style={{
                backgroundColor: "var(--color-gate-emerald-bg)",
                color: "var(--color-gate-emerald)",
              }}
            >
              {step.actor_label} · {step.status_badge}
            </span>
          </div>
          <h3 style={{ margin: "4px 0 0 0", fontSize: "18px" }}>{step.title}</h3>
          <p style={{ margin: "2px 0 0 0", fontSize: "13px", color: "var(--color-text-secondary)" }}>
            {step.summary}
          </p>
        </div>

        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {step.linked_workflow_id ? (
            <>
              <button
                type="button"
                data-testid={`sheet-open-studio-btn-${step.num}`}
                onClick={() => onOpenStudio(step.linked_workflow_id!)}
                className="orcia-ds-btn-secondary"
              >
                {isFr ? "✏️ Studio 5 Blocs" : "✏️ 5-Block Studio"}
              </button>
              <button
                type="button"
                data-testid={`sheet-execute-wf-btn-${step.num}`}
                onClick={() => onExecuteWorkflow(step.linked_workflow_id!)}
                className="orcia-ds-btn-primary"
              >
                {isFr ? "▷ Exécuter ce Workflow" : "▷ Execute Workflow"}
              </button>
            </>
          ) : null}
          <button
            type="button"
            data-testid="close-step-detail-sheet-btn"
            onClick={onClose}
            className="orcia-ds-btn-secondary"
          >
            {isFr ? "✕ Fermer la fiche" : "✕ Close sheet"}
          </button>
        </div>
      </div>

      {/* 6 Tabs Navigation */}
      <div
        role="tablist"
        aria-label="Fiche détaillée 6 onglets"
        className="orcia-ds-tabs"
      >
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.key}
            data-testid={`step-sheet-tab-${tab.key}`}
            onClick={() => setActiveTab(tab.key)}
            className="orcia-ds-tab"
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Vue d'ensemble & Comparaison Aujourd'hui / Demain */}
      {activeTab === "overview" ? (
        <div
          data-testid="step-sheet-panel-overview"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(290px, 1fr))",
            gap: "12px",
          }}
        >
          <div
            className="rounded border p-3"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div style={{ fontWeight: 700, fontSize: "13px", color: "var(--color-arbitration-amber)" }}>
              {isFr ? "AUJOURD'HUI (Mode actuel)" : "TODAY (Current mode)"}
            </div>
            <p style={{ fontSize: "12.5px", margin: "6px 0" }}>
              <strong>Acteurs :</strong> {step.today.actors}
            </p>
            <p style={{ fontSize: "12.5px", margin: "6px 0" }}>
              <strong>Activités :</strong> {step.today.activities}
            </p>
            <p style={{ fontSize: "12.5px", margin: "6px 0" }}>
              <strong>Livrable :</strong> {step.today.deliverable}
            </p>
            <p style={{ fontSize: "12.5px", margin: "6px 0", color: "var(--color-stale-crimson)" }}>
              <strong> irritants / frictions :</strong> {step.today.pain_points}
            </p>
          </div>

          <div
            className="rounded border p-3"
            style={{
              backgroundColor: "var(--color-gate-emerald-bg)",
              borderColor: "var(--color-gate-emerald)",
            }}
          >
            <div style={{ fontWeight: 700, fontSize: "13px", color: "var(--color-gate-emerald)" }}>
              {isFr ? "AVEC LES AGENTS (Cible ORCIA)" : "WITH AGENTS (ORCIA Target)"}
            </div>
            <p style={{ fontSize: "12.5px", margin: "6px 0" }}>
              <strong>Acteurs :</strong> {step.tomorrow.actors}
            </p>
            <p style={{ fontSize: "12.5px", margin: "6px 0" }}>
              <strong>Activités :</strong> {step.tomorrow.activities}
            </p>
            <p style={{ fontSize: "12.5px", margin: "6px 0" }}>
              <strong>Livrable :</strong> {step.tomorrow.deliverable}
            </p>
            <p style={{ fontSize: "12.5px", margin: "6px 0", fontWeight: 600 }}>
              <strong>Gain attendu :</strong> {step.tomorrow.gains}
            </p>
          </div>
        </div>
      ) : null}

      {/* Tab 2: Schéma de l'Agent & Sous-étapes Déterministes */}
      {activeTab === "agent_substeps" ? (
        <div
          data-testid="step-sheet-panel-agent_substeps"
          style={{ display: "flex", flexDirection: "column", gap: "10px" }}
        >
          {step.detail_tabs.agent_sub_steps.length === 0 ? (
            <div style={{ fontSize: "13px", color: "var(--color-text-secondary)" }}>
              {isFr
                ? "Étape gouvernée par un point de passage humain ou un sas externe."
                : "Step governed by a human checkpoint or external gate."}
            </div>
          ) : (
            step.detail_tabs.agent_sub_steps.map((sub, idx) => (
              <div
                key={String(sub.id ?? idx)}
                data-testid={`sheet-substep-card-${String(sub.id ?? idx)}`}
                className="rounded border p-3"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong style={{ fontSize: "13.5px", color: "var(--color-primary-cobalt)" }}>
                    Sous-étape {idx + 1} — {String(sub.name ?? sub.shortLabel ?? "")}
                  </strong>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      color: "var(--color-text-secondary)",
                    }}
                  >
                    {String(sub.trigger ?? "")}
                  </span>
                </div>
                <div style={{ fontSize: "12.5px", marginTop: "6px" }}>
                  <strong>Rôle :</strong> {String(sub.role ?? "")}
                </div>
                <div style={{ fontSize: "12.5px", marginTop: "4px" }}>
                  <strong>En sortie :</strong> {String(sub.output ?? "")}
                </div>
                {sub.humanCheck ? (
                  <div
                    style={{
                      fontSize: "12px",
                      marginTop: "6px",
                      color: "var(--color-arbitration-amber)",
                      fontWeight: 600,
                    }}
                  >
                    ◆ Point d&apos;arrêt humain : {String(sub.humanCheck)}
                  </div>
                ) : null}
              </div>
            ))
          )}
        </div>
      ) : null}

      {/* Tab 3: Interactions Humain / IA */}
      {activeTab === "interactions" ? (
        <div
          data-testid="step-sheet-panel-interactions"
          style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "13px" }}
        >
          <div className="rounded border p-3" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}>
            <strong>Initiative / Déclencheur :</strong>{" "}
            {String(interactions.initiative ?? step.actor_label)}
          </div>
          <div className="rounded border p-3" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}>
            <strong>Validation & Arbitrage Humain :</strong>{" "}
            {String(interactions.humanValidation ?? step.passage_point?.question ?? "Revue souveraine de fin d'étape")}
          </div>
          <div className="rounded border p-3" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}>
            <strong>Livrable de sortie :</strong> {step.deliverable}
          </div>
        </div>
      ) : null}

      {/* Tab 4: Contrôles & Gates */}
      {activeTab === "controls_gates" ? (
        <div
          data-testid="step-sheet-panel-controls_gates"
          style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "13px" }}
        >
          <div
            className="rounded border p-3"
            style={{
              backgroundColor: "var(--color-gate-emerald-bg)",
              borderColor: "var(--color-gate-emerald)",
            }}
          >
            <strong>Pipeline de Gates (Déterministes puis Agents Contradicteurs) :</strong>
            <div style={{ marginTop: "6px" }}>
              {JSON.stringify(controls)}
            </div>
          </div>
          {step.passage_point ? (
            <div
              className="rounded border p-3"
              style={{
                backgroundColor: "var(--color-arbitration-bg)",
                borderColor: "var(--color-arbitration-amber)",
              }}
            >
              <strong>◆ Point de passage humain : {step.passage_point.decision}</strong>
              <div style={{ marginTop: "4px" }}>{step.passage_point.question}</div>
              <div style={{ marginTop: "4px", fontSize: "12px", color: "var(--color-text-secondary)" }}>
                Issues possibles : {step.passage_point.possible_outcomes.join(" · ")}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Tab 5: Boucles de retour */}
      {activeTab === "return_loops" ? (
        <div
          data-testid="step-sheet-panel-return_loops"
          style={{ display: "flex", flexDirection: "column", gap: "10px" }}
        >
          <div>
            <strong style={{ fontSize: "13px" }}>
              {isFr ? "Boucles déclenchées depuis cette étape :" : "Loops triggered from this step:"}
            </strong>
            {outgoingLoops.length === 0 ? (
              <div style={{ fontSize: "12.5px", color: "var(--color-text-secondary)", marginTop: "4px" }}>
                {isFr ? "Aucune boucle sortante." : "No outgoing loops."}
              </div>
            ) : (
              outgoingLoops.map((loop) => (
                <div
                  key={loop.id}
                  className="rounded border p-2.5 mt-2 text-xs"
                  style={{
                    backgroundColor: "var(--color-arbitration-bg)",
                    borderColor: "var(--color-arbitration-amber)",
                  }}
                >
                  <strong>
                    ↩ {loop.from_step_num} → {loop.to_step_num} ({loop.reentry_mode})
                  </strong>{" "}
                  — {loop.trigger_condition} : {loop.reason}
                </div>
              ))
            )}
          </div>

          <div>
            <strong style={{ fontSize: "13px" }}>
              {isFr ? "Boucles revenant vers cette étape :" : "Loops returning to this step:"}
            </strong>
            {incomingLoops.length === 0 ? (
              <div style={{ fontSize: "12.5px", color: "var(--color-text-secondary)", marginTop: "4px" }}>
                {isFr ? "Aucune boucle entrante." : "No incoming loops."}
              </div>
            ) : (
              incomingLoops.map((loop) => (
                <div
                  key={loop.id}
                  className="rounded border p-2.5 mt-2 text-xs"
                  style={{
                    backgroundColor: "var(--color-bg-elevated)",
                    borderColor: "var(--color-border-subtle)",
                  }}
                >
                  <strong>
                    ↩ Depuis {loop.from_step_num} → {loop.to_step_num} ({loop.reentry_mode})
                  </strong>{" "}
                  — {loop.reason} ({loop.impact_summary})
                </div>
              ))
            )}
          </div>
        </div>
      ) : null}

      {/* Tab 6: Compléments & Garde-fous */}
      {activeTab === "opportunities" ? (
        <div
          data-testid="step-sheet-panel-opportunities"
          style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "13px" }}
        >
          <div>
            <strong>{isFr ? "Garde-fous appliqués :" : "Applied guardrails:"}</strong>
            <ul style={{ margin: "6px 0", paddingLeft: "18px" }}>
              {step.detail_tabs.guardrails.map((g, i) => (
                <li key={i}>{g}</li>
              ))}
            </ul>
          </div>
          {step.detail_tabs.complements_and_missing.length > 0 ? (
            <div>
              <strong>{isFr ? "Points d'attention & compléments :" : "Complements:"}</strong>
              <ul style={{ margin: "6px 0", paddingLeft: "18px" }}>
                {step.detail_tabs.complements_and_missing.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
