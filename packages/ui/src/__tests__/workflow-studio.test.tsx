import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it } from "vitest";
import { WorkflowStudioSection, type UiWorkflowStudioLabels } from "../index";

const STUDIO_LABELS: UiWorkflowStudioLabels = {
  studioTitle: "Studio Workflow-as-Code (YAML/JSON) & Gabarits Multi-Audience (Story 3.1)",
  studioSubtitle:
    "Validez vos DAGs, l'ordre Intention → Code, les Sous-Workflows fractals (<= 3) et l'arbre run-lock.json.",
  validateNominalLabel: "Valider le DAG & l'Ordre Intention → Code",
  simulateCriticalAutonomousLabel: "Simuler Rejet : HIGH_CRITICAL + AUTONOMOUS_CONTRACT (Ligne 6)",
  simulateMissingIntentionLabel: "Simuler Rejet : Code sans Intention préalable (Ligne 11)",
  simulateMaxDepthLabel: "Simuler Rejet : Profondeur SUB_WORKFLOW 4 > 3 (Ligne 10)",
  validDagBanner:
    "✓ DAG VALIDE — Ordre Topologique [frame-architecture-intent -> delegate-remediation-subworkflow -> post-deploy-verification] & Profondeur SUB_WORKFLOW = 2 / 3",
  criticalAutonomousErrorBanner:
    "✕ Ligne 6 [ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE] : Un workflow HIGH_CRITICAL ne peut pas utiliser execution_regime: AUTONOMOUS_CONTRACT (FR-29).",
  missingIntentionErrorBanner:
    "✕ Ligne 11 [ERR_INTENTION_BEFORE_CODE_REQUIRED] : L'étape 'implement-code-fix' modifie du code ('writes_code: true') sans étape amont déclarant l'intention (FR-13).",
  maxDepthErrorBanner:
    "✕ Ligne 10 [ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED] : Profondeur SUB_WORKFLOW 4 > 3 pour 'orcia://workflows/sub-verify-regression-suite' (FR-30).",
  templatePreviewTitle:
    "Gabarit d'Artefact Multi-Audience (Vue Humaine vs Contrat JSON Schema)",
  humanMarkdownTabLabel: "Vue Humaine (Markdown Chunks <= 800 mots)",
  agentSchemaTabLabel: "Contrat Agent IA (JSON Schema Draft 2020-12 Ontologique)",
  sampleHumanMarkdown:
    "# 1. Intention Stratégique & Arbitrage Humain [✍️ ANCRE HUMAINE OBLIGATOIRE]\n\nIntention directrice pour **Portail Paiement** (Ticket `CLAIMS-402`).",
  sampleAgentJsonSchema:
    '{\n  "$schema": "https://json-schema.org/draft/2020-12/schema",\n  "x-ontology-concept-key": "strategic_asset"\n}',
  subWorkflowLocksTitle:
    "Arbre Récursif run-lock.json & Sous-Workflows Verrouillés (SHA-256)",
};

describe("WorkflowStudioSection (Story 3.1)", () => {
  it("renders valid DAG topological order, recursive run-lock.json tree and switches multi-audience tabs", () => {
    render(<WorkflowStudioSection labels={STUDIO_LABELS} />);

    expect(screen.getByTestId("workflow-studio-section")).toBeDefined();
    expect(screen.getByTestId("sub-lock-depth-0").textContent).toContain(
      "depth=0 : orcia://workflows/claims-engineering-delivery@2.0.0",
    );
    expect(screen.getByTestId("sub-lock-depth-1").textContent).toContain(
      "depth=1 : orcia://workflows/sub-remediate-and-verify@1.2.0",
    );
    expect(screen.getByTestId("sub-lock-depth-2").textContent).toContain(
      "depth=2 : orcia://workflows/sub-verify-regression-suite@1.1.0",
    );

    // Click nominal validation button
    fireEvent.click(screen.getByTestId("wf-validate-nominal-btn"));
    expect(screen.getByTestId("wf-validation-result-banner").textContent).toContain(
      "✓ DAG VALIDE — Ordre Topologique",
    );

    // Default tab is Human Markdown view with Human Anchor indicator
    expect(screen.getByTestId("template-compiled-output").textContent).toContain(
      "✍️ ANCRE HUMAINE OBLIGATOIRE",
    );

    // Switch to Agent JSON Schema Draft 2020-12 tab
    fireEvent.click(screen.getByTestId("template-tab-schema-btn"));
    expect(screen.getByTestId("template-compiled-output").textContent).toContain(
      "https://json-schema.org/draft/2020-12/schema",
    );
  });

  it("displays deterministic line-number diagnostics for HIGH_CRITICAL, missing Intention, and SUB_WORKFLOW depth > 3", () => {
    render(<WorkflowStudioSection labels={STUDIO_LABELS} />);

    // 1. Trigger HIGH_CRITICAL + AUTONOMOUS_CONTRACT preset
    fireEvent.click(screen.getByTestId("wf-simulate-critical-autonomous-btn"));
    expect(screen.getByTestId("wf-validation-result-banner").textContent).toContain(
      "ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE",
    );
    expect(screen.getByTestId("wf-validation-result-banner").textContent).toContain("Ligne 6");

    // 2. Trigger Missing Intention before Code preset
    fireEvent.click(screen.getByTestId("wf-simulate-missing-intention-btn"));
    expect(screen.getByTestId("wf-validation-result-banner").textContent).toContain(
      "ERR_INTENTION_BEFORE_CODE_REQUIRED",
    );
    expect(screen.getByTestId("wf-validation-result-banner").textContent).toContain("Ligne 11");

    // 3. Trigger SUB_WORKFLOW depth 4 > 3 preset
    fireEvent.click(screen.getByTestId("wf-simulate-max-depth-btn"));
    expect(screen.getByTestId("wf-validation-result-banner").textContent).toContain(
      "ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED",
    );
    expect(screen.getByTestId("wf-validation-result-banner").textContent).toContain("Ligne 10");
  });
});
