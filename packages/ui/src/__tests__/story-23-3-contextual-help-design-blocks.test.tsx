import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import {
  ContextualHelpColumnAndCenter,
  type ContextualHelpColumnAndCenterLabels,
  type UiContextualHelpArticleView,
} from "../index";
import { FourZoneHelpAsideColumn } from "../primitives/FourZoneHelpAsideColumn";

const HELP_LABELS_FR: ContextualHelpColumnAndCenterLabels = {
  columnHeaderTitle: "Aide contextuelle",
  centerHeaderTitle: "Centre d'Aide",
  whatForSectionTitle: "À quoi sert cet écran ?",
  stepByStepAccordionTitle: "Pas-à-pas",
  keyTermsAccordionTitle: "Termes clés",
  faqAccordionTitle: "Questions fréquentes",
  askAssistantOnScreenCta: "Poser une question à Mon Assistant →",
  rollbackButtonLabel: "Revenir à la version précédente",
  rollbackCompletedPrefix: "Version restaurée :",
  mergedLayersPrefix: "Sources du guide :",
  realExampleTitle: "Un exemple réel",
  commonPitfallsTitle: "Ce qui coince souvent",
  technicalDetailsTitle: "Détails techniques",
  stepsBlockPrefix: "En",
  stepsBlockSuffix: "gestes",
};

const SAMPLE_ASSISTANT_ARTICLE: UiContextualHelpArticleView = {
  resourceId: "help-base-assistant-fr",
  uri: "orcia://system/help/assistant/fr",
  title: "Mon Assistant : questions, dossiers et citations vérifiées",
  version: "1.0.0",
  lang: "fr",
  layer: "BASE",
  packName: "core",
  boundRoutes: ["/assistant", "/inbox"],
  summaryWhatFor:
    "Mon Assistant répond à vos questions à partir des documents de votre Espace actif.",
  stepByStepItems: [
    "Choisissez votre modèle et votre mode de réflexion (Polyvalent · Standard ou Approfondi).",
    "Rédigez votre question avec @ pour appeler un agent.",
    "Classez l'échange dans un dossier thématique.",
  ],
  keyTermsItems: [],
  faqItems: [],
  realExampleText:
    "Marc sélectionne son Espace, ouvre le dossier Conformité et obtient des citations cliquables.",
  commonPitfallsItems: [
    "La zone de saisie est verrouillée : configurez un modèle de dialogue dans Modèles IA.",
    "Les notes du dossier ne sont pas appliquées : cliquez sur Enregistrer les notes.",
  ],
  casKey: "cas/1234",
  sha256: "1234",
};

describe("Story 23.3 — Zone 4 DESIGN.md 4 Blocks, Admin Technical Details & Scroll Indicator", () => {
  it("renders all 4 DESIGN.md blocks natively in Zone 4 without needing accordions", () => {
    render(
      <ContextualHelpColumnAndCenter
        mode="COLUMN_340PX"
        route="/assistant"
        pack="core"
        redisCacheKey="help:route:/assistant:core:fr"
        mergedLayers={["BASE"]}
        article={SAMPLE_ASSISTANT_ARTICLE}
        isAdmin={false}
        showTechnicalMetadata={false}
        labels={HELP_LABELS_FR}
        onAskAssistantOnScreen={vi.fn()}
      />,
    );

    expect(screen.getByTestId("contextual-help-what-for-box").textContent).toContain(
      "À quoi sert cet écran ?",
    );
    expect(screen.getByTestId("contextual-help-what-for-box").textContent).toContain(
      "documents de votre Espace actif",
    );

    const stepsBox = screen.getByTestId("contextual-help-steps-box");
    expect(stepsBox.textContent).toContain("En 3 gestes");
    expect(screen.getByTestId("help-accordion-steps-content").textContent).toContain(
      "Polyvalent · Standard",
    );

    const exampleBox = screen.getByTestId("contextual-help-real-example-box");
    expect(exampleBox.textContent).toContain("Un exemple réel");
    expect(exampleBox.textContent).toContain("Marc sélectionne son Espace");
    expect(exampleBox.style.backgroundColor).toBe("var(--color-help-example-bg)");

    const pitfallsBox = screen.getByTestId("contextual-help-common-pitfalls-box");
    expect(pitfallsBox.textContent).toContain("Ce qui coince souvent");
    expect(pitfallsBox.textContent).toContain("La zone de saisie est verrouillée");

    // Standard user never sees @version or merged layers plumbing
    expect(screen.queryByTestId("contextual-help-technical-details")).toBeNull();
    expect(screen.queryByTestId("contextual-help-version-pill")).toBeNull();
    expect(screen.queryByTestId("contextual-help-merged-layers")).toBeNull();
  });

  it("renders technical metadata inside a collapsed-by-default <details> drawer for PLATFORM_ADMIN", () => {
    render(
      <ContextualHelpColumnAndCenter
        mode="COLUMN_340PX"
        route="/assistant"
        pack="core"
        redisCacheKey="help:route:/assistant:core:fr"
        mergedLayers={["BASE", "PACK", "WORKSPACE"]}
        article={SAMPLE_ASSISTANT_ARTICLE}
        isAdmin={true}
        showTechnicalMetadata={true}
        labels={HELP_LABELS_FR}
        onAskAssistantOnScreen={vi.fn()}
      />,
    );

    const details = screen.getByTestId("contextual-help-technical-details") as HTMLDetailsElement;
    expect(details.tagName).toBe("DETAILS");
    expect(details.open).toBe(false);
    expect(details.textContent).toContain("Détails techniques");
    expect(screen.getByTestId("contextual-help-version-pill").textContent).toBe("v1.0.0");
    expect(screen.getByTestId("contextual-help-merged-layers").textContent).toContain(
      "Base / Pack / Espace (core)",
    );
  });

  it("displays contextual-help-scroll-indicator on FourZoneHelpAsideColumn when content overflows vertically and hides it at bottom", async () => {
    const { container } = render(
      <FourZoneHelpAsideColumn
        isMobile={false}
        labels={{
          helpColumnTitle: "Aide contextuelle",
          helpColumnExpectedTitle: "À quoi sert cet écran",
          helpColumnExpectedBody: "Contenu.",
          helpColumnScrollMoreLabel: "Défiler pour voir la suite ↓",
        }}
        helpColumnContent={<div>Long guide content</div>}
        onClose={vi.fn()}
      />,
    );

    const aside = container.querySelector(
      '[data-testid="four-zone-contextual-help-column"]',
    ) as HTMLElement;
    expect(aside).toBeTruthy();

    let currentScrollTop = 0;
    Object.defineProperty(aside, "scrollHeight", { configurable: true, value: 900 });
    Object.defineProperty(aside, "clientHeight", { configurable: true, value: 500 });
    Object.defineProperty(aside, "scrollTop", {
      configurable: true,
      get: () => currentScrollTop,
      set: (val: number) => {
        currentScrollTop = val;
      },
    });

    fireEvent(window, new Event("resize"));
    await waitFor(() => {
      const indicator = screen.getByTestId("contextual-help-scroll-indicator");
      expect(indicator.textContent).toContain("Défiler pour voir la suite");
    });

    currentScrollTop = 400;
    fireEvent.scroll(aside);
    await waitFor(() => {
      expect(screen.queryByTestId("contextual-help-scroll-indicator")).toBeNull();
    });
  });

  it("uses English askAssistantPrefillTemplate and targetedHelpBadgeLabel without French leakage", () => {
    const onAskAssistant = vi.fn();
    const enLabels: ContextualHelpColumnAndCenterLabels = {
      columnHeaderTitle: "Contextual Help",
      centerHeaderTitle: "Help Center",
      whatForSectionTitle: "What is this screen for?",
      stepByStepAccordionTitle: "Step-by-step",
      keyTermsAccordionTitle: "Key terms",
      faqAccordionTitle: "FAQ",
      askAssistantOnScreenCta: "Ask My Assistant about this screen",
      rollbackButtonLabel: "Rollback",
      rollbackCompletedPrefix: "Restored version:",
      mergedLayersPrefix: "Guide sources:",
      realExampleTitle: "A real example",
      commonPitfallsTitle: "Common pitfalls",
      technicalDetailsTitle: "Technical details",
      stepsBlockPrefix: "In",
      stepsBlockSuffix: "steps",
      targetedHelpBadgeLabel: "Targeted help",
      askAssistantPrefillTemplate: "Help me use screen {route} ({title})",
    };

    const enArticle: UiContextualHelpArticleView = {
      ...SAMPLE_ASSISTANT_ARTICLE,
      resourceId: "help-base-assistant-en",
      title: "My Assistant: questions and verified citations",
      lang: "en",
      summaryWhatFor: "Answers grounded in your active Space.",
      realExampleText: "Marc reviews compliance risks.",
      commonPitfallsItems: ["Input locked without configured models."],
    };

    render(
      <ContextualHelpColumnAndCenter
        mode="COLUMN_340PX"
        route="/assistant"
        pack="core"
        redisCacheKey="help:route:/assistant:core:en"
        mergedLayers={["BASE"]}
        article={enArticle}
        targetedSections={[
          {
            sectionId: "assistant-modes",
            title: "Model & thinking mode",
            body: "Pick Standard or In-Depth.",
            category: "steps",
          },
        ]}
        activeSectionId="assistant-modes"
        isAdmin={false}
        showTechnicalMetadata={false}
        labels={enLabels}
        onAskAssistantOnScreen={onAskAssistant}
      />,
    );

    const badge = screen.getByTestId("contextual-help-pinned-active-badge");
    expect(badge.textContent).toBe("Targeted help");
    expect(badge.textContent).not.toContain("Aide ciblée");

    fireEvent.click(screen.getByTestId("contextual-help-ask-assistant-btn"));
    expect(onAskAssistant).toHaveBeenCalledWith(
      "/assistant",
      "Help me use screen /assistant (My Assistant: questions and verified citations)",
    );
    expect(onAskAssistant.mock.calls[0]?.[1]).not.toContain("Explique-moi");
  });

  it("does not duplicate realExampleText/commonPitfallsItems into HelpCenterCatalogView accordions and hides empty technical metadata", () => {
    const { rerender } = render(
      <ContextualHelpColumnAndCenter
        mode="HELP_MENU_CENTER"
        route="/help"
        pack="core"
        redisCacheKey="help:route:/help:core:fr"
        mergedLayers={[]}
        article={{
          ...SAMPLE_ASSISTANT_ARTICLE,
          version: "",
          casKey: "",
          sha256: "",
          keyTermsItems: [],
          faqItems: [],
        }}
        isAdmin={true}
        showTechnicalMetadata={true}
        labels={HELP_LABELS_FR}
        onAskAssistantOnScreen={vi.fn()}
      />,
    );

    expect(screen.getByTestId("contextual-help-real-example-box")).toBeDefined();
    expect(screen.getByTestId("contextual-help-common-pitfalls-box")).toBeDefined();
    // No duplicate Key Terms / FAQ accordions when keyTermsItems & faqItems are empty
    expect(screen.queryByTestId("help-accordion-terms-btn")).toBeNull();
    expect(screen.queryByTestId("help-accordion-faq-btn")).toBeNull();
    // <details> is omitted completely when version, mergedLayers, and casKey are all empty
    expect(screen.queryByTestId("contextual-help-technical-details")).toBeNull();

    // When version is present but mergedLayers is empty, <details> renders without empty merged-layers line
    rerender(
      <ContextualHelpColumnAndCenter
        mode="HELP_MENU_CENTER"
        route="/help"
        pack="core"
        redisCacheKey="help:route:/help:core:fr"
        mergedLayers={[]}
        article={{
          ...SAMPLE_ASSISTANT_ARTICLE,
          version: "1.0.0",
          keyTermsItems: [],
          faqItems: [],
        }}
        isAdmin={true}
        showTechnicalMetadata={true}
        labels={HELP_LABELS_FR}
        onAskAssistantOnScreen={vi.fn()}
      />,
    );

    expect(screen.getByTestId("contextual-help-technical-details")).toBeDefined();
    expect(screen.getByTestId("contextual-help-version-pill").textContent).toBe("v1.0.0");
    expect(screen.queryByTestId("contextual-help-merged-layers")).toBeNull();
  });
});
