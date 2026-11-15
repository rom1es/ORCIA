import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AiModelConfigModal } from "../features/admin/ai-models/AiModelConfigModal";
import { I18nProvider } from "../i18n";
import { AI_MODELS_HUB_EN, AI_MODELS_HUB_FR } from "../i18n/locales/ai_models_hub_labels";
import { AI_PROVIDER_PRESETS } from "../routes/settingsAiModelsPresets";

afterEach(() => {
  cleanup();
});

const sampleTierLabels = {
  tierLabel: "Palier Cognitif",
  effortLabel: "Effort",
  simpleBadge: "Simple",
  mediumBadge: "Standard",
  complexBadge: "Approfondi",
  autoBadge: "Automatique",
  effortDefault: "Par défaut",
  effortFast: "Rapide",
  effortBalanced: "Équilibré",
  effortDeep: "Approfondi",
};

describe("Story 19.1 Guard Test — Empty Model Fields, Dynamic Placeholders & No Hardcoded Chips (D1)", () => {
  it("strictly enforces empty model inputs and zero chips across all provider presets in French", () => {
    const onSubmitCreate = vi.fn().mockResolvedValue(true);
    const onSubmitPatch = vi.fn().mockResolvedValue(true);
    const onOpenChange = vi.fn();

    render(
      <I18nProvider initialLocale="fr">
        <AiModelConfigModal
          open={true}
          onOpenChange={onOpenChange}
          mode="create"
          initialMapping={null}
          labels={AI_MODELS_HUB_FR}
          tierLabels={sampleTierLabels}
          isFr={true}
          onSubmitCreate={onSubmitCreate}
          onSubmitPatch={onSubmitPatch}
        />
      </I18nProvider>,
    );

    const primaryInput = screen.getByTestId("ai-model-primary-model-input") as HTMLInputElement;
    const fallbackInput = screen.getByTestId("ai-model-fallback-model-input") as HTMLInputElement;
    const endpointInput = screen.getByTestId("ai-model-endpoint-uri-input") as HTMLInputElement;

    // 1. Initial state must be completely empty
    expect(primaryInput.value).toBe("");
    expect(fallbackInput.value).toBe("");
    expect(document.querySelectorAll('[data-testid^="ai-model-quick-chip-"]').length).toBe(0);

    // 2. Iterate every provider preset: model fields must remain empty and placeholders must match
    for (const preset of AI_PROVIDER_PRESETS) {
      fireEvent.click(screen.getByTestId(`llm-provider-preset-${preset.id}`));

      // Model inputs must NOT be prefilled
      expect(primaryInput.value).toBe("");
      expect(fallbackInput.value).toBe("");
      expect(endpointInput.value).toBe(preset.defaultEndpointUrl);

      // Absolutely zero quick chip buttons in the DOM
      expect(document.querySelectorAll('[data-testid^="ai-model-quick-chip-"]').length).toBe(0);

      // Verify dynamic placeholder expectations per D1
      if (preset.id === "mistral") {
        expect(primaryInput.placeholder).toBe("ex. : mistral-large-latest");
      } else if (preset.id === "local-ollama") {
        expect(primaryInput.placeholder).toBe("ex. : llama3.2");
      } else {
        expect(primaryInput.placeholder).toBe("Identifiant exact publié par le fournisseur");
      }

      expect(fallbackInput.placeholder).toBe("Modèle de secours optionnel");
    }
  });

  it("strictly enforces empty model inputs and dynamic placeholders in English", () => {
    const onSubmitCreate = vi.fn().mockResolvedValue(true);
    const onSubmitPatch = vi.fn().mockResolvedValue(true);
    const onOpenChange = vi.fn();

    render(
      <I18nProvider initialLocale="en">
        <AiModelConfigModal
          open={true}
          onOpenChange={onOpenChange}
          mode="create"
          initialMapping={null}
          labels={AI_MODELS_HUB_EN}
          tierLabels={sampleTierLabels}
          isFr={false}
          onSubmitCreate={onSubmitCreate}
          onSubmitPatch={onSubmitPatch}
        />
      </I18nProvider>,
    );

    const primaryInput = screen.getByTestId("ai-model-primary-model-input") as HTMLInputElement;
    const fallbackInput = screen.getByTestId("ai-model-fallback-model-input") as HTMLInputElement;

    expect(primaryInput.value).toBe("");
    expect(fallbackInput.value).toBe("");

    // Test Mistral preset in English
    fireEvent.click(screen.getByTestId("llm-provider-preset-mistral"));
    expect(primaryInput.value).toBe("");
    expect(primaryInput.placeholder).toBe("e.g. mistral-large-latest");
    expect(fallbackInput.placeholder).toBe("Optional fallback model");

    // Test Ollama preset in English
    fireEvent.click(screen.getByTestId("llm-provider-preset-local-ollama"));
    expect(primaryInput.value).toBe("");
    expect(primaryInput.placeholder).toBe("e.g. llama3.2");

    // Test OpenAI preset in English
    fireEvent.click(screen.getByTestId("llm-provider-preset-openai"));
    expect(primaryInput.value).toBe("");
    expect(primaryInput.placeholder).toBe("Exact identifier published by provider");

    // Zero chips
    expect(document.querySelectorAll('[data-testid^="ai-model-quick-chip-"]').length).toBe(0);
  });

  it("fails if any preset spec contains legacy hardcoded model properties", () => {
    for (const preset of AI_PROVIDER_PRESETS) {
      const untyped = preset as unknown as Record<string, unknown>;
      expect(untyped["samplePrimaryModel"]).toBeUndefined();
      expect(untyped["sampleSecondaryModel"]).toBeUndefined();
      expect(untyped["recommendedModels"]).toBeUndefined();
    }
  });
});
