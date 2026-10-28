import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import {
  UpstreamChallengeRewindModal,
  type UpstreamChallengeModalLabels,
  type UpstreamChallengeWhatIfPreview,
} from "../primitives/UpstreamChallengeRewindModal";

const LABELS: UpstreamChallengeModalLabels = {
  modalTitle: "Challenge Amont & Simulation d'Impact What-If (UX-DR7)",
  modalSubtitle: "Contestez une règle d'un artefact amont",
  targetStepLabel: "Step amont ciblé",
  sectionKeyLabel: "Section / Règle contestée",
  reasonLabel: "Justification technique ou métier du Challenge (>= 10 car.)",
  reasonPlaceholder: "Expliquez l'incohérence...",
  whatIfTitle: "Aperçu de Simulation d'Impact (What-If Impact Preview — AD-7)",
  invalidatedStepsLabel: "Steps aval invalidés",
  invalidatedSectionsLabel: "Sections d'artefacts impactées",
  invalidatedAxiomsLabel: "Axiomes d'Ontologie concernés",
  preservedStepsLabel: "Steps amont préservés (run-lock.json SHA-256)",
  translatedSummaryLabel: "Traduction Ontologique pour l'auteur amont",
  submitChallengeCta: "Envoyer le Challenge Amont (Outbox)",
  replayStepCta: "Relancer Replay ciblé Step N (0 token amont)",
  closeCta: "Fermer",
  challengeSubmittedFeedback: "Challenge Amont transmis via domain_events_outbox ✓",
  replayTriggeredFeedback: "Replay ciblé Step N exécuté ✓",
};

const PREVIEW: UpstreamChallengeWhatIfPreview = {
  runId: "run-001",
  challengerStepKey: "delegate-sub-workflow",
  targetUpstreamStepKey: "frame-architecture-intent",
  challengedSectionKey: "fx_rate_guarantee_rule",
  targetProfileArchetype: "PM_PO",
  translatedSummary: "[Traduction Ontologique -> PM_PO] Impact sur 3 étapes aval.",
  invalidatedDownstreamStepKeys: [
    "frame-architecture-intent",
    "delegate-sub-workflow",
    "human-final-signoff",
  ],
  invalidatedArtifactSections: [
    "frame-architecture-intent:fx_rate_guarantee_rule",
    "delegate-sub-workflow:dependent_on_fx_rate_guarantee_rule",
  ],
  invalidatedOntologyAxiomKeys: ["axiom-l1-strategic-asset-immutable-schema"],
  preservedUpstreamStepKeys: ["step-0-intake-validated"],
  upstreamTokensSaved: 1250,
};

describe("Story 3.5 — UpstreamChallengeRewindModal (UX-DR7)", () => {
  it("renders What-If impact preview, submits challenge, triggers Step N replay, and closes on Escape", () => {
    const onSubmitChallenge = vi.fn();
    const onTriggerReplay = vi.fn();
    const onClose = vi.fn();

    render(
      <UpstreamChallengeRewindModal
        isOpen={true}
        preview={PREVIEW}
        labels={LABELS}
        subWorkflowStepKey="run-sandbox-tests"
        onSubmitChallenge={onSubmitChallenge}
        onTriggerReplay={onTriggerReplay}
        onClose={onClose}
      />
    );

    expect(screen.getByTestId("what-if-invalidated-steps").textContent).toContain(
      "frame-architecture-intent, delegate-sub-workflow, human-final-signoff"
    );
    expect(screen.getByTestId("what-if-preserved-steps").textContent).toContain(
      "step-0-intake-validated"
    );
    expect(screen.getByTestId("what-if-translated-summary").textContent).toContain(
      "PM_PO"
    );

    fireEvent.click(screen.getByTestId("upstream-challenge-submit-btn"));
    expect(onSubmitChallenge).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("upstream-challenge-feedback")).toBeDefined();

    fireEvent.click(screen.getByTestId("upstream-replay-trigger-btn"));
    expect(onTriggerReplay).toHaveBeenCalledWith({
      stepKey: "frame-architecture-intent",
      subWorkflowStepKey: "run-sandbox-tests",
    });
    expect(screen.getByTestId("upstream-replay-feedback")).toBeDefined();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
