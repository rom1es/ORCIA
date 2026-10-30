import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  ChunkValidationCard,
  CognitiveReviewBriefingGrid,
  type UiChunkValidationItem,
} from "../index";

describe("Story 4.3 — CognitiveReviewBriefingGrid (UX-DR4) & ChunkValidationCard (UX-DR5, UX-DR10)", () => {
  it("highlights Block 4 (Retained Hypotheses) in amber until inspected", () => {
    const onInspect = vi.fn();
    const { rerender } = render(
      <CognitiveReviewBriefingGrid
        executiveSummary="Executive summary"
        keyElementsAndTransverse={["Step 1 aligned"]}
        decisionsTaken={["Use Postgres 18"]}
        retainedHypotheses={["Hypothesis A"]}
        hypothesesInspected={false}
        onInspectHypotheses={onInspect}
        labels={{
          gridTitle: "Briefing 4 Blocs",
          block1Title: "1. Résumé Exécutif",
          block2Title: "2. Éléments Clés",
          block3Title: "3. Décisions Prises",
          block4Title: "4. Hypothèses Retenues",
          inspectHypothesesButtonLabel: "Inspecter",
          hypothesesInspectedBadgeLabel: "Inspecté",
          hypothesesPendingBadgeLabel: "En attente",
        }}
      />
    );

    const block4 = screen.getByTestId("review-briefing-block-4");
    expect(block4.getAttribute("data-amber-highlighted")).toBe("true");
    fireEvent.click(screen.getByTestId("inspect-hypotheses-btn"));
    expect(onInspect).toHaveBeenCalledTimes(1);

    rerender(
      <CognitiveReviewBriefingGrid
        executiveSummary="Executive summary"
        keyElementsAndTransverse={["Step 1 aligned"]}
        decisionsTaken={["Use Postgres 18"]}
        retainedHypotheses={["Hypothesis A"]}
        hypothesesInspected={true}
        onInspectHypotheses={onInspect}
        labels={{
          gridTitle: "Briefing 4 Blocs",
          block1Title: "1. Résumé Exécutif",
          block2Title: "2. Éléments Clés",
          block3Title: "3. Décisions Prises",
          block4Title: "4. Hypothèses Retenues",
          inspectHypothesesButtonLabel: "Inspecter",
          hypothesesInspectedBadgeLabel: "Inspecté",
          hypothesesPendingBadgeLabel: "En attente",
        }}
      />
    );
    expect(
      screen
        .getByTestId("review-briefing-block-4")
        .getAttribute("data-amber-highlighted")
    ).toBe("false");
  });

  it("disables final approval while chunks are pending, navigates with Alt+Arrows, and triggers <15s Anti-Rubber-Stamping Guard", () => {
    const onDecide = vi.fn();
    const onFinalize = vi.fn();
    const chunks: UiChunkValidationItem[] = [
      {
        chunkKey: "sec-1",
        sectionTitle: "Section 1",
        sectionIndex: 0,
        contentMarkdown: "Contenu 1",
        wordCount: 600,
        status: "APPROVED",
      },
      {
        chunkKey: "sec-2",
        sectionTitle: "Section 2",
        sectionIndex: 1,
        contentMarkdown: "Contenu 2",
        wordCount: 600,
        status: "CO_EDITED",
      },
    ];

    render(
      <ChunkValidationCard
        chunks={chunks}
        totalWordCount={1200}
        reviewDurationMs={5000}
        hypothesesInspected={true}
        retainedHypotheses={["Hypothèse 1"]}
        onDecideChunk={onDecide}
        onFinalizeGate={onFinalize}
        labels={{
          sectionListTitle: "Sections",
          keyboardNavHint: "Alt + ↑ / ↓",
          approveSectionLabel: "Valider",
          coEditSectionLabel: "Co-éditer",
          challengeSectionLabel: "Challenger",
          finalizeGateButtonLabel: "Approuver la Gate",
          pendingSectionsNotice: "Valider chaque section",
          guardModalTitle: "Garde-fou Anti-Rubber-Stamping",
          guardModalDescription: "Lecture < 15s sur > 1000 mots",
          guardConfirmCheckboxLabel: "Je confirme les hypothèses",
          guardConfirmButtonLabel: "Confirmer",
          guardCancelButtonLabel: "Annuler",
        }}
      />
    );

    // Keyboard navigation Alt + ArrowDown moves focus from sec-1 to sec-2
    expect(
      screen.getByTestId("chunk-validation-card-sec-1").getAttribute("data-active")
    ).toBe("true");
    fireEvent.keyDown(window, { key: "ArrowDown", altKey: true });
    expect(
      screen.getByTestId("chunk-validation-card-sec-2").getAttribute("data-active")
    ).toBe("true");

    // Clicking finalize on >1000 words in 5000ms (<15000ms) opens Anti-Rubber-Stamping Guard modal
    fireEvent.click(screen.getByTestId("finalize-human-gate-btn"));
    expect(
      screen.getByTestId("anti-rubber-stamping-guard-modal")
    ).toBeDefined();
    expect(onFinalize).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId("rubber-stamp-confirm-checkbox"));
    fireEvent.click(screen.getByTestId("rubber-stamp-confirm-submit-btn"));
    expect(onFinalize).toHaveBeenCalledWith({
      explicitHypothesesConfirmation: true,
      fastApprovalWarning: true,
    });
  });
});
