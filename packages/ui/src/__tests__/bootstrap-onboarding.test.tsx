import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it } from "vitest";
import {
  BootstrapOnboardingPanel,
  type UiBootstrapOnboardingLabels,
  type UiBootstrapWorkflowView,
} from "../index";

const MOCK_WORKFLOWS: UiBootstrapWorkflowView[] = [
  {
    uri: "orcia://system/bootstrap/init-organization",
    title: "init-organization",
    requiredRole: "PLATFORM_ADMIN",
    scopeLevel: "GLOBAL",
    gateRules: ["GATE-LLM-ORTHOGONALITY-MIN-2-FAMILIES"],
  },
  {
    uri: "orcia://system/bootstrap/init-workspace",
    title: "init-workspace",
    requiredRole: "TEAM_LEAD",
    scopeLevel: "TEAM",
    gateRules: ["GATE-ONTOLOGY-L3-NO-UPSTREAM-CONFLICT"],
  },
  {
    uri: "orcia://system/bootstrap/init-datasource",
    title: "init-datasource",
    requiredRole: "TEAM_LEAD",
    scopeLevel: "WORKSPACE",
    gateRules: ["GATE-PERMISSION-BROKER-HUMAN-ANCHOR-SIGNED"],
  },
  {
    uri: "orcia://system/bootstrap/init-user",
    title: "init-user",
    requiredRole: "CONTRIBUTOR",
    scopeLevel: "WORKSPACE",
    gateRules: ["GATE-PASSTHROUGH-AES256GCM-ENCRYPTED"],
  },
];

const MOCK_LABELS: UiBootstrapOnboardingLabels = {
  panelTitle: "Workflows Système d'Amorçage Gouverné Jour 0",
  panelSubtitle: "6 workflows pré-embarqués",
  orthogonalityTitle: "Gate Jour 0 (init-organization)",
  orthogonalityPassBadge: "Orthogonalité LLM vérifiée (3 familles)",
  orthogonalityFailBanner: "HTTP 422 ERR_MODEL_ORTHOGONALITY_VIOLATION",
  simulateSingleFamilyLabel: "Tester 1 seule famille LLM",
  simulateDualFamilyLabel: "Valider >= 2 familles LLM",
  initWorkspaceTitle: "Onboarding Autonome d'Équipe (init-workspace)",
  initWorkspaceButtonLabel: "Exécuter init-workspace",
  initWorkspaceSuccessBanner: "HTTP 200 OK — Équipe et 2 Workspaces créés",
  initDatasourceTitle: "Rattachement Gouverné Multi-Sources (init-datasource)",
  initDatasourceButtonLabel: "Publier la source fédérée",
  initDatasourceSuccessBanner: "HTTP 200 OK — Source publiée avec Ancre Humaine signée",
  humanAnchorErrorBanner: "HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED",
  initUserTitle: "Onboarding Première Connexion (init-user)",
  initUserButtonLabel: "Exécuter init-user",
  initUserSuccessBanner: "HTTP 200 OK — Jetons Passthrough chiffrés AES-256-GCM",
  observerDeniedBanner: "HTTP 403 ERR_OBSERVER_MODE_READ_ONLY",
  humanAnchorCardLabels: {
    badgeTitle: "✍️ ANCRAGE HUMAIN OBLIGATOIRE (human_authored_required: true)",
    authorLabel: "Signataire humain",
    sectionTitle: "Justification de sécurité & périmètre du connecteur fédéré",
    placeholderText: "Rédigez la justification humaine obligatoire (>= 30 caractères)...",
    signatureLabel: "Signature de l'auteur humain",
    signaturePlaceholder: "Ex: Marc (Tech Lead Checkout)",
    submitLabel: "Signer l'ancre humaine",
  },
};

describe("BootstrapOnboardingPanel & HumanLedAnchorCard (Story 1.5, UX-DR3, FR-28)", () => {
  it("renders governed workflows, LLM orthogonality gate, Human-Led Anchor Card, and executes init-workspace/init-datasource/init-user", () => {
    render(
      <BootstrapOnboardingPanel
        activePersona="marc"
        workflows={MOCK_WORKFLOWS}
        labels={MOCK_LABELS}
      />,
    );

    expect(screen.getByTestId("bootstrap-onboarding-panel")).toBeDefined();
    expect(screen.getByTestId("bootstrap-wf-init-organization")).toBeDefined();
    expect(screen.getByTestId("bootstrap-wf-init-workspace")).toBeDefined();
    expect(screen.getByTestId("bootstrap-wf-init-datasource")).toBeDefined();
    expect(screen.getByTestId("bootstrap-wf-init-user")).toBeDefined();

    const anchorCard = screen.getByTestId("human-led-anchor-card");
    expect(anchorCard.getAttribute("data-human-authored-required")).toBe("true");

    // Simulate single LLM family violation (422) then restore dual family
    fireEvent.click(screen.getByTestId("simulate-single-llm-family-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain(
      "ERR_MODEL_ORTHOGONALITY_VIOLATION",
    );
    fireEvent.click(screen.getByTestId("simulate-dual-llm-family-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain(
      "Orthogonalité LLM vérifiée",
    );

    // Execute init-workspace
    fireEvent.click(screen.getByTestId("execute-init-workspace-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain(
      "HTTP 200 OK — Équipe et 2 Workspaces créés",
    );

    // Test Human Anchor validation error when justification is too short (< 30 chars)
    fireEvent.change(screen.getByTestId("human-anchor-justification-input"), {
      target: { value: "Trop court" },
    });
    fireEvent.click(screen.getByTestId("execute-init-datasource-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain(
      "ERR_HUMAN_ANCHOR_REQUIRED",
    );

    // Restore valid justification & signature -> 200 OK
    fireEvent.change(screen.getByTestId("human-anchor-justification-input"), {
      target: {
        value:
          "Validation architecturale et sécurité du périmètre Git BFF et Confluence CQL par le Tech Lead.",
      },
    });
    fireEvent.change(screen.getByTestId("human-anchor-signature-input"), {
      target: { value: "Marc (Tech Lead Checkout)" },
    });
    fireEvent.click(screen.getByTestId("execute-init-datasource-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain(
      "HTTP 200 OK — Source publiée avec Ancre Humaine signée",
    );

    // Execute init-user
    fireEvent.click(screen.getByTestId("execute-init-user-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain(
      "AES-256-GCM",
    );
  });

  it("blocks all bootstrap mutations in READ_ONLY_OBSERVER mode (claire)", () => {
    render(
      <BootstrapOnboardingPanel
        activePersona="claire"
        workflows={MOCK_WORKFLOWS}
        labels={MOCK_LABELS}
      />,
    );

    fireEvent.click(screen.getByTestId("simulate-single-llm-family-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain(
      "ERR_OBSERVER_MODE_READ_ONLY",
    );

    fireEvent.click(screen.getByTestId("simulate-dual-llm-family-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain(
      "ERR_OBSERVER_MODE_READ_ONLY",
    );

    fireEvent.click(screen.getByTestId("execute-init-workspace-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain(
      "ERR_OBSERVER_MODE_READ_ONLY",
    );

    fireEvent.click(screen.getByTestId("execute-init-datasource-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain(
      "ERR_OBSERVER_MODE_READ_ONLY",
    );

    fireEvent.click(screen.getByTestId("execute-init-user-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain(
      "ERR_OBSERVER_MODE_READ_ONLY",
    );
  });
});
