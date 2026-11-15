import type {
  AiModelDeleteImpactResponse,
  AiModelMappingItemResponse,
} from "@orcia/api-client";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React, { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AiModelConfigModal } from "../features/admin/ai-models/AiModelConfigModal";
import { AiModelDeleteDialog } from "../features/admin/ai-models/AiModelDeleteDialog";
import { AiModelsMasterTable } from "../features/admin/ai-models/AiModelsMasterTable";
import { I18nProvider } from "../i18n";
import { AI_MODELS_HUB_FR } from "../i18n/locales/ai_models_hub_labels";
import { SettingsAiModelsSection } from "../routes/SettingsAiModelsSection";

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

const sampleMappings: readonly AiModelMappingItemResponse[] = [
  {
    id: "01932900-0001-7000-8000-000000000001",
    scope_level: "GLOBAL",
    scope_id: "",
    display_name: "Claude 3.7 Sonnet (Standard)",
    inference_tier: "medium",
    effort: "balanced",
    provider_slug: "anthropic",
    model_family: "Anthropic",
    model_name: "claude-3-7-sonnet",
    fallback_model_name: "claude-3-5-haiku",
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
  },
];

describe("Story 17.5 — AI Models Hub UI Lifecycle, Modals & F5 Survival", () => {
  it("renders AiModelsMasterTable with coverage bar, active count, latency, and maskedHint", () => {
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
          mappings={sampleMappings}
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

    expect(screen.getByTestId("ai-models-master-table")).toBeDefined();
    expect(screen.getByTestId("ai-models-coverage-bar")).toBeDefined();
    expect(screen.getByTestId("coverage-tier-chip-medium").getAttribute("data-covered")).toBe("true");
    expect(screen.getByTestId("coverage-tier-chip-simple").getAttribute("data-covered")).toBe("false");

    const row = screen.getByTestId("llm-tier-row-01932900-0001-7000-8000-000000000001");
    expect(row.textContent).toContain("Claude 3.7 Sonnet (Standard)");
    expect(row.textContent).toContain("142 ms");

    const secretHint = screen.getByTestId("ai-model-secret-hint");
    expect(secretHint.textContent).toBe("••••••••48f2");

    const testBtn = screen.getByTestId("test-ai-model-btn-01932900-0001-7000-8000-000000000001");
    fireEvent.click(testBtn);
    expect(onTest).toHaveBeenCalledWith("01932900-0001-7000-8000-000000000001");
  });

  it("handles AiModelConfigModal in create, gemini protocol toggle, and rotate-key modes", async () => {
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
          tierLabels={sampleTierLabels}
          isFr={true}
          onSubmitCreate={onSubmitCreate}
          onSubmitPatch={onSubmitPatch}
        />
      </I18nProvider>,
    );

    expect(screen.getByTestId("ai-model-config-modal")).toBeDefined();

    // Select Google Gemini preset to trigger protocol selector
    fireEvent.click(screen.getByTestId("llm-provider-preset-google"));
    expect(screen.getByTestId("google-gemini-protocol-mode-selector")).toBeDefined();

    fireEvent.click(screen.getByTestId("google-gemini-mode-openai-btn"));
    const endpointInput = screen.getByTestId("ai-model-endpoint-uri-input") as HTMLInputElement;
    expect(endpointInput.value).toContain("/v1beta/openai");

    // Verify fields are empty and no quick chips exist
    const modelInput = screen.getByTestId("ai-model-primary-model-input") as HTMLInputElement;
    expect(modelInput.value).toBe("");
    expect(modelInput.placeholder).toBe("Identifiant exact publié par le fournisseur");
    expect(screen.queryByTestId("ai-model-quick-chip-gemini-argon")).toBeNull();

    // Type model explicitly
    fireEvent.change(modelInput, { target: { value: "gemini-2.5-flash" } });
    expect(modelInput.value).toBe("gemini-2.5-flash");

    // Submit form
    fireEvent.click(screen.getByTestId("save-ai-model-btn"));
    await waitFor(() => {
      expect(onSubmitCreate).toHaveBeenCalled();
    });

    // Switch to rotate-key mode
    rerender(
      <I18nProvider initialLocale="fr">
        <AiModelConfigModal
          open={true}
          onOpenChange={onOpenChange}
          mode="rotate-key"
          initialMapping={sampleMappings[0]!}
          labels={AI_MODELS_HUB_FR}
          tierLabels={sampleTierLabels}
          isFr={true}
          onSubmitCreate={onSubmitCreate}
          onSubmitPatch={onSubmitPatch}
        />
      </I18nProvider>,
    );

    expect(screen.getByTestId("secret-field-container")).toBeDefined();
    expect(screen.getByTestId("secret-field-masked-hint").textContent).toBe("••••••••48f2");
  });

  it("handles AiModelDeleteDialog impact evaluation: blocked when last tier model, drain button when pinned runs", async () => {
    const onConfirmDelete = vi.fn().mockResolvedValue(true);
    const onOpenChange = vi.fn();

    const blockedImpact: AiModelDeleteImpactResponse = {
      mapping_id: "01932900-0001-7000-8000-000000000001",
      inference_tier: "medium",
      model_name: "claude-3-7-sonnet",
      is_last_active_for_tier: true,
      dependent_workflows_count: 3,
      dependent_workflow_ids: ["wf-1", "wf-2", "wf-3"],
      remaining_active_for_tier: 0,
      pinned_active_runs_count: 2,
      pinned_run_ids: ["run-1", "run-2"],
    };

    render(
      <I18nProvider initialLocale="fr">
        <AiModelDeleteDialog
          open={true}
          onOpenChange={onOpenChange}
          mapping={sampleMappings[0]!}
          labels={AI_MODELS_HUB_FR}
          impact={blockedImpact}
          isLoadingImpact={false}
          onConfirmDelete={onConfirmDelete}
        />
      </I18nProvider>,
    );

    expect(screen.getByTestId("ai-model-delete-dialog")).toBeDefined();
    expect(screen.getByTestId("delete-blocked-banner")).toBeDefined();
    expect(screen.getByTestId("delete-active-runs-banner")).toBeDefined();

    // Confirm delete button should be disabled because deletion is blocked
    const confirmBtn = screen.getByTestId("confirm-delete-ai-model-btn");
    expect(confirmBtn.hasAttribute("disabled")).toBe(true);

    // Drain button is enabled
    const drainBtn = screen.getByTestId("drain-ai-model-btn");
    expect(drainBtn.hasAttribute("disabled")).toBe(false);
    fireEvent.click(drainBtn);
    await waitFor(() => {
      expect(onConfirmDelete).toHaveBeenCalledWith("01932900-0001-7000-8000-000000000001", "drain");
    });
  });

  it("survives F5 unmount -> render lifecycle and preserves configured model list", () => {
    function Host(): React.ReactElement {
      return (
        <I18nProvider initialLocale="fr">
          <SettingsAiModelsSection
            isFr={true}
            llmTiers={[
              {
                tier: "medium",
                primaryModel: "claude-3-7-sonnet",
                secondaryModel: "claude-3-5-haiku",
                modelFamily: "Anthropic",
                defaultEffort: "balanced",
                endpointUrl: "https://api.anthropic.com/v1",
                authMode: "api_key",
                apiKeyConfigured: true,
              },
            ]}
            tierAndEffortLabels={sampleTierLabels}
          />
        </I18nProvider>
      );
    }

    const { unmount } = render(<Host />);
    expect(screen.getByTestId("ai-models-master-table")).toBeDefined();
    expect(screen.getByTestId("llm-tier-row-medium").textContent).toContain("claude-3-7-sonnet");

    // Simulate F5 page reload
    unmount();

    // Re-mount
    render(<Host />);
    expect(screen.getByTestId("ai-models-master-table")).toBeDefined();
    expect(screen.getByTestId("llm-tier-row-medium").textContent).toContain("claude-3-7-sonnet");
  });

  it("enforces PermissionGuard: hides create CTA when verb 'create' is absent", () => {
    render(
      <I18nProvider initialLocale="fr">
        <AiModelsMasterTable
          isFr={true}
          labels={AI_MODELS_HUB_FR}
          tierLabels={sampleTierLabels}
          mappings={sampleMappings}
          allowedVerbs={["read"]}
          testingId={null}
          onOpenCreateModal={() => undefined}
          onOpenEditModal={() => undefined}
          onOpenRotateKeyModal={() => undefined}
          onToggleActive={() => undefined}
          onOpenDeleteDialog={() => undefined}
          onTestConnection={() => undefined}
        />
      </I18nProvider>,
    );

    expect(screen.queryByTestId("open-create-ai-model-modal-btn")).toBeNull();
    const testBtn = screen.getByTestId("test-ai-model-btn-01932900-0001-7000-8000-000000000001");
    expect(testBtn.hasAttribute("disabled")).toBe(true);
  });
});
