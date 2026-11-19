import type {
  AiModelCreateRequest,
  AiModelMappingItemResponse,
} from "@orcia/api-client";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AiModelConfigModal } from "../features/admin/ai-models/AiModelConfigModal";
import { AiModelsMasterTable } from "../features/admin/ai-models/AiModelsMasterTable";
import { I18nProvider } from "../i18n";
import { AI_MODELS_HUB_FR } from "../i18n/locales/ai_models_hub_labels";

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

const sampleEmbeddingMapping: AiModelMappingItemResponse = {
  id: "01932900-0002-7000-8000-000000000002",
  scope_level: "GLOBAL",
  scope_id: "",
  display_name: "Text Embedding 3 Large (1024)",
  inference_tier: "auto",
  effort: "default",
  usage: "embedding",
  provider_slug: "openai",
  model_family: "OpenAI",
  model_name: "text-embedding-3-large",
  fallback_model_name: null,
  endpoint_uri: "https://api.openai.com/v1",
  auth_mode: "api_key",
  protocol_mode: "openai_compatible",
  env_var_name: null,
  fallback_order: 1,
  max_tokens_budget: 8192,
  max_cost_usd: 5,
  is_active: true,
  draining: false,
  health_status: "OPERATIONAL",
  last_tested_at: "2026-11-15T10:00:00Z",
  last_latency_ms: 85,
  created_at: "2026-11-15T09:00:00Z",
  updated_at: "2026-11-15T09:00:00Z",
  secret_status: {
    configured: true,
    fingerprint: "sha256:11223344",
    masked_hint: "••••••••1122",
    updated_at: "2026-11-15T09:00:00Z",
    updated_by: "admin",
  },
};

const sampleChatMapping: AiModelMappingItemResponse = {
  id: "01932900-0001-7000-8000-000000000001",
  scope_level: "GLOBAL",
  scope_id: "",
  display_name: "Claude 3.7 Sonnet (Standard)",
  inference_tier: "medium",
  effort: "balanced",
  usage: "chat",
  provider_slug: "anthropic",
  model_family: "Anthropic",
  model_name: "claude-3-7-sonnet",
  fallback_model_name: null,
  endpoint_uri: "https://api.anthropic.com/v1",
  auth_mode: "api_key",
  protocol_mode: "openai_compatible",
  env_var_name: null,
  fallback_order: 1,
  max_tokens_budget: 4096,
  max_cost_usd: 10,
  is_active: true,
  draining: false,
  health_status: "OPERATIONAL",
  last_tested_at: "2026-11-14T10:00:00Z",
  last_latency_ms: 142,
  created_at: "2026-11-14T09:00:00Z",
  updated_at: "2026-11-14T09:00:00Z",
  secret_status: {
    configured: true,
    fingerprint: "sha256:48f2abcd",
    masked_hint: "••••••••48f2",
    updated_at: "2026-11-14T09:00:00Z",
    updated_by: "marc",
  },
};

describe("Story 19.5 — AI Models Hub Usage Selector & Active Embedding Badge", () => {
  it("renders active embedding badge and custom usage badge in AiModelsMasterTable without counting embedding towards chat cognitive tiers", () => {
    const onTest = vi.fn();
    const onCreate = vi.fn();
    const onEdit = vi.fn();
    const onRotate = vi.fn();
    const onToggle = vi.fn();
    const onDelete = vi.fn();

    render(
      <I18nProvider initialLocale="fr">
        <AiModelsMasterTable
          isFr={true}
          labels={AI_MODELS_HUB_FR}
          tierLabels={sampleTierLabels}
          mappings={[sampleEmbeddingMapping, sampleChatMapping]}
          allowedVerbs={["read", "create", "update", "delete", "execute", "grant"]}
          testingId={null}
          onOpenCreateModal={onCreate}
          onOpenEditModal={onEdit}
          onOpenRotateKeyModal={onRotate}
          onToggleActive={onToggle}
          onOpenDeleteDialog={onDelete}
          onTestConnection={onTest}
        />
      </I18nProvider>,
    );

    // Active global embedding badge is displayed for the embedding mapping
    const activeBadge = screen.getByTestId(`active-embedding-badge-${sampleEmbeddingMapping.id}`);
    expect(activeBadge).toBeDefined();
    expect(activeBadge.textContent).toContain(AI_MODELS_HUB_FR.activeEmbeddingBadge);

    // Custom usage badge is displayed
    const usageBadge = screen.getByTestId(`usage-badge-embedding-${sampleEmbeddingMapping.id}`);
    expect(usageBadge).toBeDefined();
    expect(usageBadge.textContent).toContain(AI_MODELS_HUB_FR.usageEmbedding);

    // Embedding mapping row data attributes
    const embeddingRow = screen.getByTestId(`llm-tier-row-${sampleEmbeddingMapping.id}`);
    expect(embeddingRow.getAttribute("data-usage")).toBe("embedding");

    // Chat mapping row data attributes
    const chatRow = screen.getByTestId(`llm-tier-row-${sampleChatMapping.id}`);
    expect(chatRow.getAttribute("data-usage")).toBe("chat");

    // Chat coverage bar should NOT cover auto tier just from the embedding mapping
    // Medium is covered by sampleChatMapping
    expect(screen.getByTestId("coverage-tier-chip-medium").getAttribute("data-covered")).toBe("true");
    // Auto tier is false because embedding doesn't count towards chat cognitive tier coverage
    expect(screen.getByTestId("coverage-tier-chip-auto").getAttribute("data-covered")).toBe("false");
  });

  it("handles usage selection in AiModelConfigModal and disables embedding for Anthropic", async () => {
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

    // By default Anthropic is selected in create mode -> embedding button should be disabled
    const embeddingBtn = screen.getByTestId("ai-model-usage-embedding-btn") as HTMLButtonElement;
    const chatBtn = screen.getByTestId("ai-model-usage-chat-btn") as HTMLButtonElement;
    expect(embeddingBtn.disabled).toBe(true);
    expect(screen.getByTestId("anthropic-no-embedding-warning")).toBeDefined();

    // Switch provider to OpenAI via preset button
    const openaiPresetBtn = screen.getByTestId("llm-provider-preset-openai");
    fireEvent.click(openaiPresetBtn);

    // Embedding button should now be enabled
    expect(embeddingBtn.disabled).toBe(false);

    // Select embedding
    fireEvent.click(embeddingBtn);

    // Effort selector should be hidden when usage is embedding
    expect(screen.queryByTestId("ai-model-effort-selector")).toBeNull();

    // Fill required fields
    fireEvent.change(screen.getByTestId("ai-model-primary-model-input"), {
      target: { value: "text-embedding-3-large" },
    });
    fireEvent.change(screen.getByTestId("ai-model-endpoint-uri-input"), {
      target: { value: "https://api.openai.com/v1" },
    });

    // Save
    const saveBtn = screen.getByTestId("save-ai-model-btn");
    fireEvent.click(saveBtn);

    expect(onSubmitCreate).toHaveBeenCalledTimes(1);
    const firstCall = onSubmitCreate.mock.calls[0];
    expect(firstCall).toBeDefined();
    const savedPayload = (firstCall?.[0] ?? {}) as AiModelCreateRequest;
    expect(savedPayload.usage).toBe("embedding");
    expect(savedPayload.provider_slug).toBe("openai");
    expect(savedPayload.model_name).toBe("text-embedding-3-large");
  });

  it("rehydrates edit modal with existing usage='embedding'", () => {
    const onSubmitCreate = vi.fn().mockResolvedValue(true);
    const onSubmitPatch = vi.fn().mockResolvedValue(true);
    const onOpenChange = vi.fn();

    render(
      <I18nProvider initialLocale="fr">
        <AiModelConfigModal
          open={true}
          onOpenChange={onOpenChange}
          mode="edit"
          initialMapping={sampleEmbeddingMapping}
          labels={AI_MODELS_HUB_FR}
          tierLabels={sampleTierLabels}
          isFr={true}
          onSubmitCreate={onSubmitCreate}
          onSubmitPatch={onSubmitPatch}
        />
      </I18nProvider>,
    );

    const embeddingBtn = screen.getByTestId("ai-model-usage-embedding-btn") as HTMLButtonElement;
    expect(embeddingBtn).toBeDefined();
    // In edit mode with openai provider, embedding button is enabled
    expect(embeddingBtn.disabled).toBe(false);
    expect(screen.queryByTestId("ai-model-effort-selector")).toBeNull();
  });
});
