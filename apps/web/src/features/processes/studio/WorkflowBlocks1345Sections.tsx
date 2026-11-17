import { OrciaIcon } from "@orcia/ui";
import React from "react";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";
import {
  HUMAN_KB_LABELS,
  HUMAN_SKILL_LABELS,
  HUMAN_TOOL_LABELS,
} from "./studioLabelsAndMappers";

export {
  WorkflowDeclarativePreviewPanel,
  WorkflowWhatIfSandboxPanel,
  type WhatIfSummaryState,
} from "./WorkflowPreviewAndWhatIfPanels";

export function WorkflowBlock1ContractSection({
  workflow,
  isFr,
}: {
  readonly workflow: WorkflowDefinitionV2Item;
  readonly isFr: boolean;
}) {
  return (
    <div
      data-testid="studio-block-1-triggers-contract"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "8px" }}
    >
      <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
        {isFr
          ? "1. Éléments d'entrée & Livrable attendu"
          : "1. Inputs & Expected Deliverable"}
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
          <strong>{isFr ? "Éléments en entrée :" : "Inputs:"}</strong>
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
          <strong>
            {isFr ? "Rubriques attendues dans le livrable :" : "Expected deliverable headings:"}
          </strong>
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
          <strong>{isFr ? "Conditions de validation :" : "Approval criteria:"}</strong>
          <div style={{ marginTop: "4px", color: "var(--color-gate-emerald)" }}>
            {isFr
              ? "Contrôles de complétude validés · Approbation du responsable"
              : "Completeness checks passed · Owner sign-off"}
          </div>
        </div>
      </div>
    </div>
  );
}

export function WorkflowBlocks345Sections({
  workflow,
  isFr,
}: {
  readonly workflow: WorkflowDefinitionV2Item;
  readonly isFr: boolean;
}) {
  const langKey = isFr ? "fr" : "en";
  return (
    <>
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
            {isFr ? "3. Outils connectés mobilisés" : "3. Connected Tools"}
          </strong>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
            {Array.from(
              new Set(workflow.sub_steps.flatMap((s) => s.mcp_tools_allowed)),
            ).map((tool) => (
              <span
                key={tool}
                className="rounded border px-2.5 py-1 text-xs font-medium"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <OrciaIcon name="plug" />
                <span>{HUMAN_TOOL_LABELS[tool]?.[langKey] ?? tool}</span>
              </span>
            ))}
          </div>
        </div>

        <div
          data-testid="studio-block-4-skills-knowledge"
          className="orcia-bento-card"
          style={{ display: "flex", flexDirection: "column", gap: "8px" }}
        >
          <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
            {isFr
              ? "4. Savoir-faire métier & Socle documentaire"
              : "4. Business Skills & Knowledge Base"}
          </strong>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
            {workflow.skills_refs.map((skill) => (
              <span
                key={skill}
                className="rounded px-2.5 py-1 text-xs font-medium"
                style={{
                  backgroundColor: "var(--color-ontology-bg)",
                  color: "var(--color-ontology-cyan)",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <OrciaIcon name="sparkles" />
                <span>{HUMAN_SKILL_LABELS[skill]?.[langKey] ?? skill}</span>
              </span>
            ))}
            {workflow.knowledge_base_refs.map((kb) => (
              <span
                key={kb}
                className="rounded px-2.5 py-1 text-xs font-medium"
                style={{
                  backgroundColor: "var(--color-action-primary-subtle)",
                  color: "var(--color-primary-cobalt)",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <OrciaIcon name="document" />
                <span>{HUMAN_KB_LABELS[kb]?.[langKey] ?? kb}</span>
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
          {isFr
            ? "5. Contrôles de qualité avant validation humaine"
            : "5. Quality Checks Before Human Sign-Off"}
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
              {isFr
                ? "1. Vérifications automatiques de complétude"
                : "1. Automated Completeness Checks"}
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
            <div style={{ fontWeight: 700, fontSize: "12.5px", color: "var(--color-arbitration-amber)" }}>
              {isFr
                ? "2. Relecture critique par un agent contradicteur"
                : "2. Critical Review by Challenger Agent"}
            </div>
            {workflow.controls.probabilistic_evaluations.map((pg) => (
              <div key={pg.id} style={{ marginTop: "6px", fontSize: "12.5px" }}>
                <strong>{pg.name}</strong> — {pg.rubric_ref}
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
