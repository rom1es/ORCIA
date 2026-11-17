import React from "react";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";

const HUMAN_TOOL_LABELS: Record<string, string> = {
  "mcp:atlassian-jira (read)": "Jira — Consultation des demandes & tickets",
  "mcp:atlassian-jira (write_preview)": "Jira — Création / mise à jour (avec confirmation)",
  "mcp:atlassian-confluence (read)": "Confluence — Lecture du socle documentaire",
  "mcp:atlassian-confluence (write_preview)": "Confluence — Publication de page (avec confirmation)",
  "mcp:git-provider (read)": "Git — Lecture du code & des Pull Requests",
  "mcp:git-provider (write_preview)": "Git — Préparation de branche / Pull Request",
};

const HUMAN_SKILL_LABELS: Record<string, string> = {
  "pack://sdlc/skills/qualification-besoin": "Qualification structurée du besoin",
  "pack://sdlc/skills/redaction-prd-wsjf": "Rédaction du PRD & calcul de priorité (WSJF)",
  "pack://sdlc/skills/diagrammes-mermaid": "Schémas d'architecture & parcours",
  "pack://sdlc/skills/decoupe-us-invest": "Découpage en User Stories (INVEST & Gherkin)",
  "pack://orcia-docs/skills/redaction-aide-bilingue": "Rédaction de guides utilisateurs FR/EN",
};

const HUMAN_KB_LABELS: Record<string, string> = {
  "pack://sdlc/agents/crl-socle-generateur.md":
    "Socle de connaissance produit & architecture (Confluence)",
  "pack://orcia-docs/agents/redacteur-documentation-orcia.md": "Référentiel documentaire ORCIA",
};

export interface StudioFiveBlocksGridProps {
  readonly workflow: WorkflowDefinitionV2Item;
  readonly isFr: boolean;
  readonly onToggleSubStepEnabled: (subStepId: string) => void;
  readonly onSwitchExecutionMode: (mode: "native_orcia" | "external_delegated") => void;
}

export function StudioFiveBlocksGrid({
  workflow,
  isFr,
  onToggleSubStepEnabled,
  onSwitchExecutionMode,
}: StudioFiveBlocksGridProps): React.ReactElement {
  return (
    <div
      data-testid="studio-five-blocks-canvas"
      style={{ display: "flex", flexDirection: "column", gap: "14px" }}
    >
      <div
        data-testid="studio-block-1-triggers-contract"
        className="orcia-bento-card"
        style={{ display: "flex", flexDirection: "column", gap: "8px" }}
      >
        <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
          1. Éléments d&apos;entrée &amp; Livrable attendu
        </strong>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "10px",
            fontSize: "12.5px",
          }}
        >
          <div
            className="rounded border p-2.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <strong>Éléments en entrée :</strong>
            <div style={{ marginTop: "4px", color: "var(--color-text-secondary)" }}>
              {workflow.contract.inputs.join(" · ")}
            </div>
          </div>
          <div
            className="rounded border p-2.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <strong>Rubriques attendues dans le livrable :</strong>
            <div style={{ marginTop: "4px", fontSize: "12px" }}>
              {workflow.contract.outputs.map((h) => h.replace(/^#+\s*/, "")).join(" · ")}
            </div>
          </div>
          <div
            className="rounded border p-2.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <strong>Conditions de validation :</strong>
            <div style={{ marginTop: "4px", color: "var(--color-gate-emerald)" }}>
              {isFr
                ? "Contrôles de complétude validés · Approbation du responsable"
                : "Completeness checks passed · Owner sign-off"}
            </div>
          </div>
        </div>
      </div>

      <div
        data-testid="studio-block-2-deterministic-substeps"
        className="orcia-bento-card"
        style={{ display: "flex", flexDirection: "column", gap: "10px" }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "8px",
          }}
        >
          <div>
            <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
              2. Déroulement des étapes du processus
            </strong>
            <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
              Activez ou ignorez chaque étape selon les besoins de votre projet.
            </div>
          </div>

          <div style={{ display: "flex", gap: "6px" }}>
            <button
              type="button"
              data-testid="mode-switch-native-orcia-btn"
              onClick={() => onSwitchExecutionMode("native_orcia")}
              className={
                workflow.execution_mode === "native_orcia"
                  ? "orcia-ds-btn-primary"
                  : "orcia-ds-btn-secondary"
              }
            >
              Exécution guidée ORCIA
            </button>
            <button
              type="button"
              data-testid="mode-switch-external-delegated-btn"
              onClick={() => onSwitchExecutionMode("external_delegated")}
              className={
                workflow.execution_mode === "external_delegated"
                  ? "orcia-ds-btn-primary"
                  : "orcia-ds-btn-secondary"
              }
            >
              Réalisation dans l&apos;IDE / Git
            </button>
          </div>
        </div>

        {workflow.execution_mode === "external_delegated" ? (
          <div
            data-testid="studio-external-delegated-banner"
            className="rounded border p-3 text-xs"
            style={{
              backgroundColor: "var(--color-arbitration-bg)",
              borderColor: "var(--color-arbitration-amber)",
            }}
          >
            <strong>🛠️ Réalisation confiée à l&apos;équipe dans son IDE / Git :</strong> ORCIA
            prépare le dossier de contexte et vérifie automatiquement la conformité dès que la Pull
            Request est proposée.
          </div>
        ) : null}

        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {workflow.sub_steps.map((sub, idx) => (
            <div
              key={sub.id}
              data-testid={`studio-substep-card-${sub.id}`}
              className="rounded border p-3"
              style={{
                backgroundColor: sub.enabled
                  ? "var(--color-bg-elevated)"
                  : "var(--color-surface-muted)",
                borderColor: sub.enabled
                  ? "var(--color-primary-cobalt)"
                  : "var(--color-border-subtle)",
                opacity: sub.enabled ? 1 : 0.65,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "8px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  <span
                    style={{
                      fontSize: "12px",
                      fontWeight: 700,
                      color: "var(--color-primary-cobalt)",
                    }}
                  >
                    Étape {idx + 1}
                  </span>
                  <strong style={{ fontSize: "13.5px" }}>{sub.name}</strong>
                  {sub.requires_human_checkpoint ? (
                    <span
                      className="rounded px-2 py-0.5 text-xs font-semibold"
                      style={{
                        backgroundColor: "var(--color-arbitration-bg)",
                        color: "var(--color-arbitration-amber)",
                      }}
                    >
                      Validation humaine
                    </span>
                  ) : null}
                  {sub.write_preview_required ? (
                    <span
                      className="rounded px-2 py-0.5 text-xs font-semibold"
                      style={{
                        backgroundColor: "var(--color-gate-emerald-bg)",
                        color: "var(--color-gate-emerald)",
                      }}
                    >
                      Confirmation avant publication
                    </span>
                  ) : null}
                </div>

                <button
                  type="button"
                  data-testid={`toggle-substep-enabled-${sub.id}`}
                  onClick={() => onToggleSubStepEnabled(sub.id)}
                  className="orcia-ds-btn-secondary"
                >
                  {sub.enabled
                    ? isFr
                      ? "✓ Étape activée (Ignorer)"
                      : "✓ Step enabled (Skip)"
                    : isFr
                      ? "Étape ignorée (Activer)"
                      : "Step skipped (Enable)"}
                </button>
              </div>

              <div
                style={{ fontSize: "12px", color: "var(--color-text-secondary)", marginTop: "6px" }}
              >
                <strong>Objectif :</strong> {sub.role_description}
              </div>
              <div style={{ fontSize: "12px", marginTop: "3px" }}>
                <strong>Livrable produit :</strong> {sub.output_description}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "12px",
        }}
      >
        <div
          data-testid="studio-block-3-mcp-toolboxes"
          className="orcia-bento-card"
          style={{ display: "flex", flexDirection: "column", gap: "8px" }}
        >
          <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
            3. Outils connectés mobilisés
          </strong>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
            {Array.from(new Set(workflow.sub_steps.flatMap((s) => s.mcp_tools_allowed))).map(
              (tool) => (
                <span
                  key={tool}
                  className="rounded border px-2.5 py-1 text-xs font-medium"
                  style={{
                    backgroundColor: "var(--color-bg-elevated)",
                    borderColor: "var(--color-border-subtle)",
                  }}
                >
                  🔌 {HUMAN_TOOL_LABELS[tool] ?? tool}
                </span>
              ),
            )}
          </div>
        </div>

        <div
          data-testid="studio-block-4-skills-knowledge"
          className="orcia-bento-card"
          style={{ display: "flex", flexDirection: "column", gap: "8px" }}
        >
          <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
            4. Savoir-faire métier &amp; Socle documentaire
          </strong>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
            {workflow.skills_refs.map((skill) => (
              <span
                key={skill}
                className="rounded px-2.5 py-1 text-xs font-medium"
                style={{
                  backgroundColor: "var(--color-ontology-bg)",
                  color: "var(--color-ontology-cyan)",
                }}
              >
                📘 {HUMAN_SKILL_LABELS[skill] ?? skill}
              </span>
            ))}
            {workflow.knowledge_base_refs.map((kb) => (
              <span
                key={kb}
                className="rounded px-2.5 py-1 text-xs font-medium"
                style={{
                  backgroundColor: "var(--color-action-primary-subtle)",
                  color: "var(--color-primary-cobalt)",
                }}
              >
                🏛️ {HUMAN_KB_LABELS[kb] ?? kb}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div
        data-testid="studio-block-5-gates-pipeline"
        className="orcia-bento-card"
        style={{ display: "flex", flexDirection: "column", gap: "10px" }}
      >
        <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
          5. Contrôles de qualité avant validation humaine
        </strong>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "10px",
          }}
        >
          <div
            className="rounded border p-3"
            style={{
              backgroundColor: "var(--color-gate-emerald-bg)",
              borderColor: "var(--color-gate-emerald)",
            }}
          >
            <div style={{ fontWeight: 700, fontSize: "12.5px", color: "var(--color-gate-emerald)" }}>
              1. Vérifications automatiques de complétude
            </div>
            {workflow.controls.deterministic_gates.map((dg) => (
              <div key={dg.id} style={{ marginTop: "6px", fontSize: "12.5px" }}>
                ✓ <strong>{dg.name}</strong>
              </div>
            ))}
          </div>

          <div
            className="rounded border p-3"
            style={{
              backgroundColor: "var(--color-arbitration-bg)",
              borderColor: "var(--color-arbitration-amber)",
            }}
          >
            <div
              style={{
                fontWeight: 700,
                fontSize: "12.5px",
                color: "var(--color-arbitration-amber)",
              }}
            >
              2. Relecture critique par un agent contradicteur
            </div>
            {workflow.controls.probabilistic_evaluations.map((pg) => (
              <div key={pg.id} style={{ marginTop: "6px", fontSize: "12.5px" }}>
                🔍 <strong>{pg.name}</strong> — {pg.rubric_ref}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
