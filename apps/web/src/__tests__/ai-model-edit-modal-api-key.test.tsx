import type { AiModelMappingItemResponse } from "@orcia/api-client";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AiModelConfigModal } from "../features/admin/ai-models/AiModelConfigModal";
import { I18nProvider } from "../i18n";
import { AI_MODELS_HUB_EN, AI_MODELS_HUB_FR } from "../i18n/locales/ai_models_hub_labels";

afterEach(() => {
  cleanup();
});

const frTierLabels = {
  tierLabel: "Palier Cognitif",
  effortLabel: "Effort",
  simpleBadge: "Simple",
  mediumBadge: "Équilibré",
  complexBadge: "Approfondi",
  autoBadge: "Automatique",
  effortDefault: "Par défaut",
  effortFast: "Rapide",
  effortBalanced: "Équilibré",
  effortDeep: "Approfondi",
};

const baseMapping: AiModelMappingItemResponse = {
  id: "01932900-0001-7000-8000-000000000099",
  scope_level: "GLOBAL",
  scope_id: "",
  display_name: "Google Gemini (Équilibré)",
  inference_tier: "medium",
  effort: "balanced",
  provider_slug: "google",
  model_family: "Google Gemini",
  model_name: "gemini-2.5-flash",
  fallback_model_name: "gemini-2.5-pro",
  endpoint_uri: "https://generativelanguage.googleapis.com/v1beta",
  auth_mode: "api_key",
  protocol_mode: "gemini_native",
  env_var_name: null,
  fallback_order: 1,
  max_tokens_budget: 8192,
  max_cost_usd: 10,
  is_active: true,
  draining: false,
  health_status: "OPERATIONAL",
  last_tested_at: null,
  last_latency_ms: null,
  created_at: "2026-11-23T10:00:00Z",
  updated_at: "2026-11-23T10:00:00Z",
  secret_status: {
    configured: true,
    fingerprint: "sha256:abcd1234",
    masked_hint: "••••••••1234",
    updated_at: "2026-11-23T10:00:00Z",
    updated_by: "admin",
  },
};

describe("AI Model edit modal API key input & localized preset display names", () => {
  it("renders api-key input in create and edit modes with FR/EN placeholders and localized preset name", () => {
    const onSubmitCreate = vi.fn().mockResolvedValue(true);
    const onSubmitPatch = vi.fn().mockResolvedValue(true);
    const onOpenChange = vi.fn();

    const { rerender } = render(
      <I18nProvider initialLocale="fr">
        <AiModelConfigModal
          open={true}
          onOpenChange={onOpenChange}
          mode="create"
          initialMapping={null}
          labels={AI_MODELS_HUB_FR}
          tierLabels={frTierLabels}
          isFr={true}
          onSubmitCreate={onSubmitCreate}
          onSubmitPatch={onSubmitPatch}
        />
      </I18nProvider>,
    );

    const createKeyInput = screen.getByTestId("ai-model-api-key-input") as HTMLInputElement;
    expect(createKeyInput.placeholder).toBe("Saisir la clé d'API secrète...");

    fireEvent.click(screen.getByTestId("llm-provider-preset-google"));
    const displayNameInput = screen.getByTestId("ai-model-display-name-input") as HTMLInputElement;
    expect(displayNameInput.value).toBe("Google Gemini (Équilibré)");

    rerender(
      <I18nProvider initialLocale="fr">
        <AiModelConfigModal
          open={true}
          onOpenChange={onOpenChange}
          mode="edit"
          initialMapping={baseMapping}
          labels={AI_MODELS_HUB_FR}
          tierLabels={frTierLabels}
          isFr={true}
          onSubmitCreate={onSubmitCreate}
          onSubmitPatch={onSubmitPatch}
        />
      </I18nProvider>,
    );

    const editKeyInputFr = screen.getByTestId("ai-model-api-key-input") as HTMLInputElement;
    expect(editKeyInputFr.value).toBe("");
    expect(editKeyInputFr.placeholder).toBe(
      "Laisser vide pour conserver la clé enregistrée (••••••••)...",
    );

    rerender(
      <I18nProvider initialLocale="en">
        <AiModelConfigModal
          open={true}
          onOpenChange={onOpenChange}
          mode="edit"
          initialMapping={baseMapping}
          labels={AI_MODELS_HUB_EN}
          tierLabels={frTierLabels}
          isFr={false}
          onSubmitCreate={onSubmitCreate}
          onSubmitPatch={onSubmitPatch}
        />
      </I18nProvider>,
    );

    const editKeyInputEn = screen.getByTestId("ai-model-api-key-input") as HTMLInputElement;
    expect(editKeyInputEn.placeholder).toBe("Leave blank to keep stored API key (••••••••)...");
  });

  it("omits secret_input when blank in edit mode and sends secret_input when provided", async () => {
    const onSubmitCreate = vi.fn().mockResolvedValue(true);
    const onSubmitPatch = vi.fn().mockResolvedValue(true);
    const onOpenChange = vi.fn();

    render(
      <I18nProvider initialLocale="fr">
        <AiModelConfigModal
          open={true}
          onOpenChange={onOpenChange}
          mode="edit"
          initialMapping={baseMapping}
          labels={AI_MODELS_HUB_FR}
          tierLabels={frTierLabels}
          isFr={true}
          onSubmitCreate={onSubmitCreate}
          onSubmitPatch={onSubmitPatch}
        />
      </I18nProvider>,
    );

    fireEvent.click(screen.getByTestId("save-ai-model-btn"));
    await waitFor(() => {
      expect(onSubmitPatch).toHaveBeenCalledTimes(1);
    });
    expect(onSubmitPatch.mock.calls[0]?.[1]?.secret_input).toBeUndefined();

    const keyInput = screen.getByTestId("ai-model-api-key-input") as HTMLInputElement;
    fireEvent.change(keyInput, { target: { value: "  AIza-new-rotated-secret  " } }); // pragma: allowlist secret
    fireEvent.click(screen.getByTestId("save-ai-model-btn"));

    await waitFor(() => {
      expect(onSubmitPatch).toHaveBeenCalledTimes(2);
    });
    expect(onSubmitPatch.mock.calls[1]?.[1]?.secret_input).toEqual({
      action: "set",
      plaintext_value: "AIza-new-rotated-secret", // pragma: allowlist secret
    });
  });
});
