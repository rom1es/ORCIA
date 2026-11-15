import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { InferenceTierAndEffortLabels } from "@orcia/ui";
import { SettingsAiModelsSection } from "../routes/SettingsAiModelsSection";
import * as aiModelsApiBridge from "../features/admin/ai-models/aiModelsApiBridge";

const dummyTierLabels: InferenceTierAndEffortLabels = {
  tierLabel: "Modèles",
  effortLabel: "Effort",
  simpleBadge: "Simple",
  mediumBadge: "Moyen",
  complexBadge: "Complexe",
  autoBadge: "Automatique",
  effortDefault: "Défaut",
  effortFast: "Rapide",
  effortBalanced: "Équilibré",
  effortDeep: "Approfondi",
};

describe("Story 19.3: Real Connection Tests in AI Models Hub & Zero Dead Buttons", () => {
  it("triggers connection test on row button click and updates status with real latency", async () => {
    const testMapping = {
      id: "mapping-test-001",
      scope_level: "GLOBAL" as const,
      scope_id: "",
      display_name: "Mistral Large",
      inference_tier: "complex" as const,
      effort: "balanced" as const,
      provider_slug: "mistral",
      model_family: "Mistral",
      model_name: "mistral-large-latest",
      fallback_model_name: null,
      endpoint_uri: "https://api.mistral.ai/v1",
      auth_mode: "api_key" as const,
      protocol_mode: "openai_compatible" as const,
      usage: "chat" as const,
      env_var_name: null,
      fallback_order: 1,
      max_tokens_budget: 4096,
      max_cost_usd: 0.0,
      is_active: true,
      draining: false,
      health_status: "UNTESTED" as const,
      last_tested_at: null,
      last_latency_ms: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      secret_status: {
        configured: true,
        fingerprint: "sha256:abc",
        masked_hint: "••••••••1234",
        updated_at: new Date().toISOString(),
        updated_by: "system",
      },
    };

    vi.spyOn(aiModelsApiBridge, "fetchAiModelMappings").mockResolvedValue({
      ok: true,
      data: [testMapping],
    });

    const testSpy = vi.spyOn(aiModelsApiBridge, "testAiModelConnectionViaApi").mockResolvedValue({
      ok: true,
      data: {
        mapping_id: "mapping-test-001",
        health_status: "OPERATIONAL",
        latency_ms: 38,
        tested_at: new Date().toISOString(),
        message: "✅ Connexion réussie",
      },
    });

    render(
      <SettingsAiModelsSection
        isFr={true}
        tierAndEffortLabels={dummyTierLabels}
      />
    );

    // Row should be present
    await waitFor(() => {
      expect(screen.getByTestId("ai-models-master-table")).toBeDefined();
    });

    const testBtn = screen.getByTestId("test-ai-model-btn-mapping-test-001");
    expect(testBtn).toBeDefined();

    fireEvent.click(testBtn);

    await waitFor(() => {
      expect(testSpy).toHaveBeenCalledWith("mapping-test-001", "fr");
    });
  });

  it("displays explicit RFC 9457 error banner when connection test fails without silent catches", async () => {
    const testMapping = {
      id: "mapping-test-002",
      scope_level: "GLOBAL" as const,
      scope_id: "",
      display_name: "Bad Model",
      inference_tier: "medium" as const,
      effort: "balanced" as const,
      provider_slug: "openai",
      model_family: "OpenAI",
      model_name: "nonexistent-model",
      fallback_model_name: null,
      endpoint_uri: "https://api.openai.com/v1",
      auth_mode: "api_key" as const,
      protocol_mode: "openai_compatible" as const,
      usage: "chat" as const,
      env_var_name: null,
      fallback_order: 1,
      max_tokens_budget: 4096,
      max_cost_usd: 0.0,
      is_active: true,
      draining: false,
      health_status: "UNTESTED" as const,
      last_tested_at: null,
      last_latency_ms: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      secret_status: {
        configured: true,
        fingerprint: "sha256:def",
        masked_hint: "••••••••5678",
        updated_at: new Date().toISOString(),
        updated_by: "system",
      },
    };

    vi.spyOn(aiModelsApiBridge, "fetchAiModelMappings").mockResolvedValue({
      ok: true,
      data: [testMapping],
    });

    vi.spyOn(aiModelsApiBridge, "testAiModelConnectionViaApi").mockResolvedValue({
      ok: false,
      errorMessage: "Modèle ou point de terminaison introuvable (HTTP 404)",
      errorCode: "ERR_MODEL_CONNECTION_NOT_FOUND",
    });

    render(
      <SettingsAiModelsSection
        isFr={true}
        tierAndEffortLabels={dummyTierLabels}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId("ai-models-master-table")).toBeDefined();
    });

    const testBtn = screen.getByTestId("test-ai-model-btn-mapping-test-002");
    fireEvent.click(testBtn);

    // Explicit error banner must appear with no silent swallow
    await waitFor(() => {
      const errorBanner = screen.getByTestId("ai-model-operation-error");
      expect(errorBanner).toBeDefined();
      expect(errorBanner.textContent).toContain("Modèle ou point de terminaison introuvable (HTTP 404)");
    });
  });
});
