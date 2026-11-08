import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React, { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import type { ConfiguredLlmTierMapping } from "../components/platformSetupStore";
import { buildAssistantModelOptions } from "../features/inbox/savedConversationsStore";
import { SettingsAiModelsSection } from "../routes/SettingsAiModelsSection";

afterEach(() => {
  cleanup();
});

const defaultTierAndEffortLabels = {
  tierLabel: "Niveau",
  effortLabel: "Effort",
  simpleBadge: "Simple",
  mediumBadge: "Standard",
  complexBadge: "Complexe",
  autoBadge: "Auto",
  effortDefault: "Par défaut",
  effortFast: "Rapide",
  effortBalanced: "Équilibré",
  effortDeep: "Approfondi",
  tierSelectorAriaLabel: "Sélectionner le niveau de modèle",
  effortSelectorAriaLabel: "Sélectionner l'effort de réflexion",
};

function Harness(): React.ReactElement {
  const [tiers, setTiers] = useState<readonly ConfiguredLlmTierMapping[]>([]);
  return (
    <SettingsAiModelsSection
      isFr={true}
      llmTiers={tiers}
      tierAndEffortLabels={defaultTierAndEffortLabels}
      openHelpSection={() => undefined}
      upsertLlmTier={(input) =>
        setTiers((prev) => [...prev.filter((t) => t.tier !== input.tier), input])
      }
    />
  );
}

describe("Google Gemini (Gemini Argon / gemini-argon) Configuration & Assistant Model Options", () => {
  it("selects Google Gemini preset with gemini-argon, toggles between Mode B (Native /v1beta) and Mode A (/v1beta/openai), and tests connection", async () => {
    render(<Harness />);

    // Click Google Gemini preset
    fireEvent.click(screen.getByTestId("llm-provider-preset-google"));

    const familyInput = screen.getByTestId("llm-family-input") as HTMLInputElement;
    const primaryInput = screen.getByTestId("llm-primary-model-input") as HTMLInputElement;
    const endpointInput = screen.getByTestId("llm-endpoint-url-input") as HTMLInputElement;

    expect(familyInput.value).toBe("Google Gemini");
    expect(primaryInput.value).toBe("gemini-argon");
    expect(endpointInput.value).toBe("https://generativelanguage.googleapis.com/v1beta");

    // Verify quick model chips and protocol mode selector are rendered
    expect(screen.getByTestId("ai-model-quick-chip-gemini-argon")).toBeDefined();
    expect(screen.getByTestId("ai-model-quick-chip-gemini-2.5-pro")).toBeDefined();
    expect(screen.getByTestId("ai-model-quick-chip-gemini-2.5-flash")).toBeDefined();
    expect(screen.getByTestId("google-gemini-protocol-mode-selector")).toBeDefined();

    // Switch to gemini-2.5-pro via quick chip, then back to gemini-argon in 1 click
    fireEvent.click(screen.getByTestId("ai-model-quick-chip-gemini-2.5-pro"));
    expect(primaryInput.value).toBe("gemini-2.5-pro");
    fireEvent.click(screen.getByTestId("ai-model-quick-chip-gemini-argon"));
    expect(primaryInput.value).toBe("gemini-argon");

    // Switch to Mode A (OpenAI-Compatible Bridge /v1beta/openai)
    fireEvent.click(screen.getByTestId("google-gemini-mode-openai-btn"));
    expect(endpointInput.value).toBe("https://generativelanguage.googleapis.com/v1beta/openai");

    // Switch back to Mode B (Native Google Gemini API /v1beta)
    fireEvent.click(screen.getByTestId("google-gemini-mode-native-btn"));
    expect(endpointInput.value).toBe("https://generativelanguage.googleapis.com/v1beta");

    // Enter API key and test connection
    fireEvent.change(screen.getByTestId("llm-api-key-input"), {
      target: { value: "AIzaSy-test-argon-key" },
    });
    fireEvent.click(screen.getByTestId("test-llm-connection-btn"));

    await waitFor(() => {
      const banner = screen.getByTestId("llm-connection-test-result");
      expect(banner.getAttribute("data-ok")).toBe("true");
      expect(banner.textContent).toContain("gemini-argon");
      expect(banner.textContent).toContain("Mode B");
    });

    // Save the tier and verify it appears in the configured list
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));
    expect(screen.getByTestId("llm-tier-row-medium").textContent).toContain("gemini-argon");
  });

  it("displays distinct configured models (e.g. gemma4:12b on medium and gemini-argon on complex) in buildAssistantModelOptions", () => {
    const options = buildAssistantModelOptions(
      [
        { tier: "medium", primaryModel: "gemma4:12b" },
        { tier: "complex", primaryModel: "gemini-argon" },
      ],
      true,
    );

    const mediumOpt = options.find((o) => o.tier === "medium")!;
    const complexOpt = options.find((o) => o.tier === "complex")!;

    expect(mediumOpt.configuredModelName).toBe("gemma4:12b");
    expect(mediumOpt.subtitle).toContain("gemma4:12b");
    expect(mediumOpt.hiddenDuplicate).toBeUndefined();

    expect(complexOpt.configuredModelName).toBe("gemini-argon");
    expect(complexOpt.subtitle).toContain("gemini-argon");
    expect(complexOpt.hiddenDuplicate).toBeUndefined();
  });
});
