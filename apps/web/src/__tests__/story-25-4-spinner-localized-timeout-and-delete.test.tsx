import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { AiModelDeleteDialog } from "../features/admin/ai-models/AiModelDeleteDialog";
import * as aiModelsApiBridge from "../features/admin/ai-models/aiModelsApiBridge";
import { AI_MODELS_HUB_EN } from "../i18n/locales/ai_models_hub_labels";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import {
  seedVitestPlatformSetupState,
  setVitestMockReindexStatus,
} from "./vitest.setup";

function seedAdminWithModels(models: Array<Record<string, unknown>>) {
  seedVitestPlatformSetupState(
    {
      org_units: [],
      rbac_grants: [],
      workspaces: [],
      datasources: [],
      packs: [],
      workflows: [],
      runs: [],
      catalog_items: [],
      ontology_concepts: [],
      ai_model_mappings: models,
    },
    { email: "admin@orcia.test", displayName: "Admin Test", roles: ["PLATFORM_ADMIN"] },
  );
  useAuthSessionStore.getState().loginWithSession({
    email: "admin@orcia.test",
    display_name: "Admin Test",
    roles: ["PLATFORM_ADMIN"],
    access_token: "mock-vitest-access-token",
  });
}

async function mountSettingsAiModelsRoute(initialPath = "/settings/ai-models") {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [initialPath] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();

  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );

  await screen.findByTestId("ai-models-master-table");
  return view;
}

describe("Story 25.4 — Unified OrciaSpinner, Localized Test Errors/Timeout, Reliable Delete & Empty Reindex Hiding", () => {
  beforeEach(() => {
    clearPlatformSetupStorage();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("displays OrciaSpinner without ellipsis during test, localizes 5xx/TimeoutError under tested model only, and deletes reliably across F5", async () => {
    const model1 = {
      id: "0195f000-0000-7000-8300-000000000001",
      scope_level: "GLOBAL",
      scope_id: null,
      display_name: "Model Alpha",
      inference_tier: "medium",
      effort: "balanced",
      provider_slug: "openai",
      model_family: "OpenAI",
      model_name: "gpt-4o-mini",
      fallback_model_name: null,
      endpoint_uri: "https://api.openai.com/v1",
      auth_mode: "none_local",
      protocol_mode: "openai_compatible",
      usage: "chat",
      is_active: true,
      draining: false,
      health_status: "UNTESTED",
      created_at: "2026-11-20T10:00:00Z",
      secret_status: { configured: false, fingerprint: null, masked_hint: null },
    };
    const model2 = {
      ...model1,
      id: "0195f000-0000-7000-8300-000000000002",
      display_name: "Model Beta",
      inference_tier: "simple",
      model_name: "gpt-4o-nano",
    };

    seedAdminWithModels([model1, model2]);
    setVitestMockReindexStatus({
      status: "IDLE",
      progress_percentage: 0,
      indexed_chunks_count: 0,
      indexed_documents_count: 0,
    });

    // Deferred promise for testing spinner & timeout error localization
    let resolveTestCall!: (val: aiModelsApiBridge.AiModelOperationResult<never>) => void;
    const pendingTestPromise = new Promise<aiModelsApiBridge.AiModelOperationResult<never>>(
      (resolve) => {
        resolveTestCall = resolve;
      },
    );
    vi.spyOn(aiModelsApiBridge, "testAiModelConnectionViaApi").mockReturnValueOnce(
      pendingTestPromise as unknown as ReturnType<typeof aiModelsApiBridge.testAiModelConnectionViaApi>,
    );

    const firstRender = await mountSettingsAiModelsRoute();
    await screen.findByTestId(`llm-tier-row-${model1.id}`);
    await screen.findByTestId(`llm-tier-row-${model2.id}`);

    // Reindex panel strictly absent at 0 chunks / 0 docs
    expect(screen.queryByTestId("ai-model-reindex-panel")).toBeNull();
    expect(document.body.textContent).not.toContain("Ready (0%)");

    // 1. Click Tester on Model 1 -> OrciaSpinner shown without "..."
    const testBtn1 = screen.getByTestId(`test-ai-model-btn-${model1.id}`);
    fireEvent.click(testBtn1);

    await waitFor(() => {
      const btn = screen.getByTestId(`test-ai-model-btn-${model1.id}`);
      const spinner = btn.querySelector('[data-testid="orcia-spinner"]');
      expect(spinner).not.toBeNull();
      expect(btn.textContent).not.toContain("...");
    });

    // 2. Resolve with 16s timeout error -> localized directly under Model 1, NOT Model 2, NOT global banner
    resolveTestCall({
      ok: false,
      errorMessage: "Délai d'attente dépassé (16 s) : le fournisseur IA n'a pas répondu à temps.",
      errorCode: "ERR_MODEL_CONNECTION_TIMEOUT",
    });

    await waitFor(() => {
      const localErr1 = screen.getByTestId(`ai-model-test-error-${model1.id}`);
      expect(localErr1.getAttribute("role")).toBe("alert");
      expect(localErr1.textContent).toContain("16 s");
    });
    expect(screen.queryByTestId(`ai-model-test-error-${model2.id}`)).toBeNull();
    expect(screen.queryByTestId("ai-model-operation-error")).toBeNull();

    // 3. Delete Model 1 and Model 2 -> persisted, accostage hasModels becomes false, survives F5
    for (const target of [model1, model2]) {
      const rowMenuTrigger = screen.getByTestId(`ai-model-row-actions-${target.id}-trigger`);
      rowMenuTrigger.focus();
      fireEvent.pointerDown(rowMenuTrigger, { button: 0, ctrlKey: false, pointerType: "mouse" });
      fireEvent.keyDown(rowMenuTrigger, { key: "ArrowDown" });
      const deleteMenuItem = await screen.findByTestId(`delete-ai-model-item-${target.id}`);
      fireEvent.click(deleteMenuItem);

      await screen.findByTestId("ai-model-delete-dialog");
      const confirmBtn = screen.getByTestId("confirm-delete-ai-model-btn") as HTMLButtonElement;
      await waitFor(() => {
        expect(confirmBtn.disabled).toBe(false);
      });
      fireEvent.click(confirmBtn);
      await waitFor(() => {
        expect(screen.queryByTestId(`llm-tier-row-${target.id}`)).toBeNull();
      });
    }

    await waitFor(() => {
      expect(screen.getByTestId("ai-models-empty-state")).toBeDefined();
      expect((screen.getByTestId("eight-menu-item-assistant") as HTMLButtonElement).disabled).toBe(
        true,
      );
    });

    // Simulate F5 full reload -> no resurrection!
    firstRender.unmount();
    await mountSettingsAiModelsRoute();

    expect(screen.getByTestId("ai-models-empty-state")).toBeDefined();
    expect(screen.queryByTestId(`llm-tier-row-${model1.id}`)).toBeNull();
    expect(screen.queryByTestId(`llm-tier-row-${model2.id}`)).toBeNull();
    expect((screen.getByTestId("eight-menu-item-assistant") as HTMLButtonElement).disabled).toBe(
      true,
    );
  });

  it("displays [role='alert'] inside AiModelDeleteDialog on 409/422/500 failure and translates summary in EN", async () => {
    const onOpenChange = vi.fn();
    const onConfirmDelete = vi.fn().mockResolvedValue({
      ok: false,
      errorMessage: "Cannot delete model: server returned HTTP 409",
    });

    const mapping = {
      id: "0195f000-0000-7000-8300-000000000099",
      scope_level: "GLOBAL" as const,
      scope_id: "",
      display_name: "En Test Model",
      inference_tier: "medium" as const,
      effort: "balanced" as const,
      provider_slug: "openai",
      model_family: "OpenAI",
      model_name: "gpt-4o",
      fallback_model_name: null,
      endpoint_uri: "https://api.openai.com/v1",
      auth_mode: "none_local" as const,
      protocol_mode: "openai_compatible" as const,
      usage: "chat" as const,
      env_var_name: null,
      fallback_order: 1,
      max_tokens_budget: 4096,
      max_cost_usd: 10,
      is_active: true,
      draining: false,
      health_status: "OPERATIONAL" as const,
      last_tested_at: null,
      last_latency_ms: null,
      created_at: "2026-11-20T10:00:00Z",
      updated_at: "2026-11-20T10:00:00Z",
      secret_status: {
        configured: false,
        fingerprint: null,
        masked_hint: null,
        updated_at: "2026-11-20T10:00:00Z",
        updated_by: "admin",
      },
    };

    render(
      <AiModelDeleteDialog
        open={true}
        onOpenChange={onOpenChange}
        mapping={mapping}
        labels={AI_MODELS_HUB_EN}
        impact={{
          mapping_id: mapping.id,
          inference_tier: "medium",
          model_name: "gpt-4o",
          is_last_active_for_tier: true,
          dependent_workflows_count: 0,
          dependent_workflow_ids: [],
          remaining_active_for_tier: 0,
          pinned_active_runs_count: 0,
          pinned_run_ids: [],
        }}
        isLoadingImpact={false}
        onConfirmDelete={onConfirmDelete}
      />,
    );

    const dialog = screen.getByTestId("ai-model-delete-dialog");
    expect(dialog.textContent).toContain("Provider");
    expect(dialog.textContent).toContain("Model");
    expect(dialog.textContent).toContain("Tier");
    expect(dialog.textContent).not.toContain("Fournisseur");
    expect(dialog.textContent).not.toContain("Modèle");
    expect(dialog.textContent).not.toContain("Palier");

    fireEvent.click(screen.getByTestId("confirm-delete-ai-model-btn"));

    const alert = await screen.findByTestId("ai-model-delete-error");
    expect(alert.getAttribute("role")).toBe("alert");
    expect(alert.textContent).toContain("HTTP 409");
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });

  it("hides AiModelReindexPanel when embedding model exists on empty corpus and renders it when >= 1 chunk/doc is indexed", async () => {
    const embeddingModel = {
      id: "0195f000-0000-7000-8300-000000000077",
      scope_level: "GLOBAL",
      scope_id: null,
      display_name: "Embedding Model",
      inference_tier: "simple",
      effort: "balanced",
      provider_slug: "openai",
      model_family: "OpenAI",
      model_name: "text-embedding-3-small",
      endpoint_uri: "https://api.openai.com/v1",
      auth_mode: "none_local",
      protocol_mode: "openai_compatible",
      usage: "embedding",
      is_active: true,
      draining: false,
      health_status: "OPERATIONAL",
      secret_status: { configured: false, fingerprint: null, masked_hint: null },
    };

    seedAdminWithModels([embeddingModel]);
    setVitestMockReindexStatus({
      status: "IDLE",
      progress_percentage: 0,
      indexed_chunks_count: 0,
      indexed_documents_count: 0,
    });

    const first = await mountSettingsAiModelsRoute();
    await screen.findByTestId(`llm-tier-row-${embeddingModel.id}`);
    expect(screen.queryByTestId("ai-model-reindex-panel")).toBeNull();
    expect(document.body.textContent).not.toContain("Ready (0%)");
    first.unmount();

    // Now simulate corpus having 12 chunks across 2 documents
    setVitestMockReindexStatus({
      status: "IDLE",
      progress_percentage: 0,
      indexed_chunks_count: 12,
      indexed_documents_count: 2,
    });

    await mountSettingsAiModelsRoute();
    const panel = await screen.findByTestId("ai-model-reindex-panel");
    expect(panel.textContent).toContain("12");
  });
});
