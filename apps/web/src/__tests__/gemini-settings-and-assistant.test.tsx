import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { buildAssistantModelOptions } from "../features/inbox/savedConversationsStore";
import { SettingsAiModelsSection } from "../routes/SettingsAiModelsSection";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { seedVitestPlatformSetupState } from "./vitest.setup";

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
  return (
    <SettingsAiModelsSection
      isFr={true}
      tierAndEffortLabels={defaultTierAndEffortLabels}
      openHelpSection={() => undefined}
    />
  );
}

describe("Google Gemini Configuration & Assistant Model Options", () => {
  it("selects Google Gemini preset with empty model and generic placeholder, toggles between Mode B (Native /v1beta) and Mode A (/v1beta/openai), and tests connection", async () => {
    seedVitestPlatformSetupState(
      { ai_model_mappings: [] },
      { email: "admin@orcia.test", displayName: "Admin Test", roles: ["PLATFORM_ADMIN"] },
    );
    useAuthSessionStore.getState().loginWithSession({
      email: "admin@orcia.test",
      display_name: "Admin Test",
      roles: ["PLATFORM_ADMIN"],
      access_token: "mock-vitest-access-token",
    });
    render(<Harness />);

    // Click Google Gemini preset
    fireEvent.click(screen.getByTestId("llm-provider-preset-google"));

    const familyInput = screen.getByTestId("llm-family-input") as HTMLInputElement;
    const primaryInput = screen.getByTestId("llm-primary-model-input") as HTMLInputElement;
    const endpointInput = screen.getByTestId("llm-endpoint-url-input") as HTMLInputElement;

    expect(familyInput.value).toBe("Google Gemini");
    expect(primaryInput.value).toBe("");
    expect(primaryInput.placeholder).toBe("Identifiant exact publié par le fournisseur");
    expect(endpointInput.value).toBe("https://generativelanguage.googleapis.com/v1beta");

    // Verify no quick model chips exist and protocol mode selector is rendered
    expect(screen.queryByTestId("ai-model-quick-chip-gemini-argon")).toBeNull();
    expect(screen.queryByTestId("ai-model-quick-chip-gemini-2.5-pro")).toBeNull();
    expect(screen.queryByTestId("ai-model-quick-chip-gemini-2.5-flash")).toBeNull();
    expect(screen.getByTestId("google-gemini-protocol-mode-selector")).toBeDefined();

    // Saisie explicite du modèle utilisateur
    fireEvent.change(primaryInput, { target: { value: "gemini-2.5-flash" } });
    expect(primaryInput.value).toBe("gemini-2.5-flash");

    // Switch to Mode A (OpenAI-Compatible Bridge /v1beta/openai)
    fireEvent.click(screen.getByTestId("google-gemini-mode-openai-btn"));
    expect(endpointInput.value).toBe("https://generativelanguage.googleapis.com/v1beta/openai");

    // Switch back to Mode B (Native Google Gemini API /v1beta)
    fireEvent.click(screen.getByTestId("google-gemini-mode-native-btn"));
    expect(endpointInput.value).toBe("https://generativelanguage.googleapis.com/v1beta");

    // Enter API key and test connection
    fireEvent.change(screen.getByTestId("llm-api-key-input"), {
      target: { value: "AIzaSy-test-key" },
    });
    fireEvent.click(screen.getByTestId("test-llm-connection-btn"));

    await waitFor(() => {
      const banner = screen.getByTestId("llm-connection-test-result");
      expect(banner.getAttribute("data-ok")).toBe("true");
      expect(banner.textContent).toContain("gemini-2.5-flash");
      expect(banner.textContent).toContain("Mode B");
    });

    // Save the tier and verify it appears in the configured list
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));
    await waitFor(() => {
      const rows = document.querySelectorAll('[data-testid^="llm-tier-row-"]');
      expect(rows.length).toBeGreaterThan(0);
      expect(rows[0]?.textContent).toContain("gemini-2.5-flash");
    });
  });

  it("displays distinct configured models (e.g. gemma4:12b on medium and gemini-2.5-pro on complex) in buildAssistantModelOptions", () => {
    const options = buildAssistantModelOptions(
      [
        { tier: "medium", primaryModel: "gemma4:12b" },
        { tier: "complex", primaryModel: "gemini-2.5-pro" },
      ],
      true,
    );

    const mediumOpt = options.find((o) => o.tier === "medium")!;
    const complexOpt = options.find((o) => o.tier === "complex")!;

    expect(mediumOpt.configuredModelName).toBe("gemma4:12b");
    expect(mediumOpt.subtitle).toContain("gemma4:12b");
    expect(mediumOpt.hiddenDuplicate).toBeUndefined();

    expect(complexOpt.configuredModelName).toBe("gemini-2.5-pro");
    expect(complexOpt.subtitle).toContain("gemini-2.5-pro");
    expect(complexOpt.hiddenDuplicate).toBeUndefined();
  });
});
