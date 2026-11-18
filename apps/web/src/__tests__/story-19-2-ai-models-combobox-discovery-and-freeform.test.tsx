import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AiModelConfigModal } from "../features/admin/ai-models/AiModelConfigModal";
import { AI_MODELS_HUB_FR } from "../i18n/locales/ai_models_hub_labels";
import * as presets from "../routes/settingsAiModelsPresets";

const mockTierLabels = {
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

describe("Story 19.2 — AI Models Combobox Discovery, Filtering & Freeform Input (D2)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("allows freeform typing in primary and fallback model comboboxes without restrictions", async () => {
    const handleSubmitCreate = vi.fn().mockResolvedValue(true);
    const handleOpenChange = vi.fn();

    render(
      <AiModelConfigModal
        open={true}
        onOpenChange={handleOpenChange}
        mode="create"
        labels={AI_MODELS_HUB_FR}
        tierLabels={mockTierLabels}
        isFr={true}
        onSubmitCreate={handleSubmitCreate}
        onSubmitPatch={vi.fn()}
      />,
    );

    const primaryInput = screen.getByTestId("ai-model-primary-model-input") as HTMLInputElement;
    const fallbackInput = screen.getByTestId("ai-model-fallback-model-input") as HTMLInputElement;

    // Freeform typing in primary model
    fireEvent.change(primaryInput, { target: { value: "my-unlisted-custom-model:latest" } });
    expect(primaryInput.value).toBe("my-unlisted-custom-model:latest");

    // Freeform typing in fallback model
    fireEvent.change(fallbackInput, { target: { value: "backup-vllm-model" } });
    expect(fallbackInput.value).toBe("backup-vllm-model");
  });

  it("automatically discovers models on modal open and populates combobox suggestions", async () => {
    const discoverSpy = vi.spyOn(presets, "discoverProviderModelsViaApi").mockResolvedValue({
      ok: true,
      models: [
        { id: "gpt-4o", display_name: "GPT-4o Omnimodel", usage_hint: "chat" },
        { id: "gpt-4o-mini", display_name: "GPT-4o Mini", usage_hint: "chat" },
        { id: "text-embedding-3-small", display_name: "Embedding Small", usage_hint: "embedding" },
      ],
    });

    render(
      <AiModelConfigModal
        open={true}
        onOpenChange={vi.fn()}
        mode="create"
        labels={AI_MODELS_HUB_FR}
        tierLabels={mockTierLabels}
        isFr={true}
        onSubmitCreate={vi.fn()}
        onSubmitPatch={vi.fn()}
      />,
    );

    // Wait for the debounced discovery call (500ms)
    await waitFor(
      () => {
        expect(discoverSpy).toHaveBeenCalled();
      },
      { timeout: 1500 },
    );

    const primaryInput = screen.getByTestId("ai-model-primary-model-input");
    fireEvent.focus(primaryInput);

    // Verify discovered chat models appear in suggestions
    await waitFor(() => {
      expect(
        screen.getByTestId("ai-model-primary-model-input-option-gpt-4o"),
      ).toBeDefined();
    });

    // Selecting option fills the input
    const option = screen.getByTestId("ai-model-primary-model-input-option-gpt-4o");
    fireEvent.mouseDown(option);
    expect((primaryInput as HTMLInputElement).value).toBe("gpt-4o");
  });

  it("filters suggestions according to usage chat vs embedding", async () => {
    vi.spyOn(presets, "discoverProviderModelsViaApi").mockResolvedValue({
      ok: true,
      models: [
        { id: "gemini-1.5-pro", display_name: "Gemini 1.5 Pro", usage_hint: "chat" },
        { id: "text-embedding-004", display_name: "Text Embedding 004", usage_hint: "embedding" },
      ],
    });

    render(
      <AiModelConfigModal
        open={true}
        onOpenChange={vi.fn()}
        mode="create"
        labels={AI_MODELS_HUB_FR}
        tierLabels={mockTierLabels}
        isFr={true}
        onSubmitCreate={vi.fn()}
        onSubmitPatch={vi.fn()}
      />,
    );

    await waitFor(
      () => {
        expect(presets.discoverProviderModelsViaApi).toHaveBeenCalled();
      },
      { timeout: 1500 },
    );

    const primaryInput = screen.getByTestId("ai-model-primary-model-input");
    fireEvent.focus(primaryInput);

    // Default usage is chat: should show gemini-1.5-pro and NOT text-embedding-004
    expect(
      screen.getByTestId("ai-model-primary-model-input-option-gemini-1.5-pro"),
    ).toBeDefined();
    expect(
      screen.queryByTestId("ai-model-primary-model-input-option-text-embedding-004"),
    ).toBeNull();

    // Switch provider to Google Gemini so embedding button is enabled
    const geminiPresetBtn = screen.getByTestId("llm-provider-preset-google");
    fireEvent.click(geminiPresetBtn);

    // Switch to embedding usage
    const embeddingBtn = screen.getByTestId("ai-model-usage-embedding-btn");
    fireEvent.click(embeddingBtn);

    // Now should show text-embedding-004 and NOT gemini-1.5-pro
    fireEvent.focus(primaryInput);
    expect(
      screen.getByTestId("ai-model-primary-model-input-option-text-embedding-004"),
    ).toBeDefined();
    expect(
      screen.queryByTestId("ai-model-primary-model-input-option-gemini-1.5-pro"),
    ).toBeNull();
  });

  it("displays explicit error message when discovery fails without blocking manual input", async () => {
    vi.spyOn(presets, "discoverProviderModelsViaApi").mockResolvedValue({
      ok: false,
      models: [],
      error: "Clé d'API invalide ou expirée (HTTP 401)",
    });

    render(
      <AiModelConfigModal
        open={true}
        onOpenChange={vi.fn()}
        mode="create"
        labels={AI_MODELS_HUB_FR}
        tierLabels={mockTierLabels}
        isFr={true}
        onSubmitCreate={vi.fn()}
        onSubmitPatch={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByTestId("ai-model-primary-model-input-refresh-btn"));

    await waitFor(
      () => {
        expect(
          screen.getByTestId("ai-model-primary-model-input-error-msg"),
        ).toBeDefined();
      },
      { timeout: 1500 },
    );

    expect(screen.getByText("Clé d'API invalide ou expirée (HTTP 401)")).toBeDefined();

    // Manual input is still 100% possible
    const primaryInput = screen.getByTestId("ai-model-primary-model-input") as HTMLInputElement;
    fireEvent.change(primaryInput, { target: { value: "fallback-custom-model" } });
    expect(primaryInput.value).toBe("fallback-custom-model");
  });
});
