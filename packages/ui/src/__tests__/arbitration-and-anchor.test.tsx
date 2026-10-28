import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import { ArbitrationTieBreakCard, HumanLedAnchorCard } from "../index";

describe("Story 3.4 — HumanLedAnchorCard (>= 30 chars guard) & ArbitrationTieBreakCard (UX-DR3, UX-DR6)", () => {
  it("locks HumanLedAnchorCard submit button when text is < 30 characters and never renders an AI auto-generate button", () => {
    const onSign = vi.fn();
    render(
      <HumanLedAnchorCard
        sectionKey="intent-anchor"
        sectionTitle="Intention Stratégique"
        authorName="Hélène PM"
        value="Trop court (< 30 chars)"
        labels={{
          badgeTitle: "✍️ ANCRAGE HUMAIN OBLIGATOIRE (human_authored_required: true)",
          authorLabel: "Auteur humain",
          placeholderText: "Rédigez votre ancrage humain...",
          submitLabel: "Signer l'ancrage humain",
        }}
        onSignAnchor={onSign}
      />,
    );

    const card = screen.getByTestId("human-anchor-card-intent-anchor");
    expect(card.getAttribute("data-human-authored-required")).toBe("true");
    expect(card.getAttribute("data-ai-generation-forbidden")).toBe("true");
    expect(card.getAttribute("data-anchor-locked")).toBe("true");
    expect(screen.queryByText(/Générer avec l'IA/i)).toBeNull();

    const submitBtn = screen.getByTestId("human-anchor-submit-intent-anchor") as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
    fireEvent.click(submitBtn);
    expect(onSign).not.toHaveBeenCalled();
  });

  it("renders ArbitrationTieBreakCard comparative matrix and resolves human option selection with justification", () => {
    const onSelect = vi.fn();
    render(
      <ArbitrationTieBreakCard
        arbitrationId="arb-test-01"
        stepKey="step-arch"
        questionTitle="Choix du mécanisme de garantie de taux FX"
        contextSummary="Deux options équivalentes identifiées."
        tieBreakPolicy="PAUSE_AND_ESCALATE"
        options={[
          {
            optionKey: "OPT_A",
            title: "Option A — Taux Spot 15 min",
            pros: ["Compatible API v3"],
            cons: ["Fenêtre courte"],
            siImpact: "1 service",
            finopsImpact: "0.02 USD",
            recommended: true,
          },
          {
            optionKey: "OPT_B",
            title: "Option B — Taux Bloqué 48h",
            pros: ["Confort client"],
            cons: ["Incompatible API v3"],
            siImpact: "3 services",
            finopsImpact: "0.18 USD",
          },
        ]}
        labels={{
          badgeTitle: "⚖️ ARBITRAGE HUMAIN REQUIS",
          policyPrefixLabel: "Politique",
          recommendedBadgeLabel: "★ Recommandé",
          prosLabel: "Avantages",
          consLabel: "Inconvénients",
          siImpactLabel: "Impact SI",
          finopsImpactLabel: "FinOps",
          justificationPlaceholder: "Justification...",
          selectOptionButtonLabel: "Choisir cette option",
          resolvedBannerPrefix: "Décision enregistrée",
        }}
        onSelectOption={onSelect}
      />,
    );

    const card = screen.getByTestId("arbitration-tiebreak-card-arb-test-01");
    expect(card.getAttribute("data-tie-break-policy")).toBe("PAUSE_AND_ESCALATE");
    expect(screen.getByText("★ Recommandé")).toBeTruthy();

    fireEvent.change(screen.getByTestId("arbitration-justification-arb-test-01"), {
      target: { value: "Conformité stricte avec l'API partenaire v3." },
    });
    fireEvent.click(screen.getByTestId("arbitration-select-OPT_A"));

    expect(onSelect).toHaveBeenCalledWith(
      "OPT_A",
      "Conformité stricte avec l'API partenaire v3.",
    );
    expect(
      screen.getByTestId("arbitration-resolved-banner-arb-test-01").textContent,
    ).toContain("OPT_A");
  });
});
