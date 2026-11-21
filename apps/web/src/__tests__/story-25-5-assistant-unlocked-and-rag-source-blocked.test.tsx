import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  clearPlatformSetupStorage,
  EMPTY_PLATFORM_SETUP_STATE,
  writeCachedPlatformAdmin,
  writeCachedPlatformSetupState,
} from "../components/platformSetupStorageHelpers";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";
import { resetVitestConnectorsMockState, seedVitestConnectorsInitialData } from "./vitestConnectorsMockHandlers";

async function renderAppAtRoute(initialEntry: string) {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [initialEntry] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...view, router, queryClient };
}

function dismissFirstBootAdminIfOpen() {
  if (screen.queryByTestId("first-boot-admin-name-input")) {
    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), {
      target: { value: "Karim Admin" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), {
      target: { value: "karim.admin@orcia.fr" },
    });
    fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));
  }
}

const TEST_WS_ID = "ws-story-25-5";

function seedAdminAndWorkspace(aiModelMappings: Array<Record<string, unknown>>) {
  useAuthSessionStore.getState().setAuthSession({
    email: "karim.admin@orcia.fr",
    roles: ["PLATFORM_ADMIN", "TEAM_LEAD"],
    activeHat: "PLATFORM_ADMIN",
  });
  writeCachedPlatformAdmin({
    email: "karim.admin@orcia.fr",
    displayName: "Karim Admin",
    role: "PLATFORM_ADMIN",
  });
  const ws = {
    workspaceId: TEST_WS_ID,
    name: "Espace Story 25.5",
    ownerOrgUnitName: "Architecture",
    visibilityMode: "STANDARD" as const,
    lifecyclePhase: "BUILD" as const,
    suggestedWorkflows: [],
    finopsCostUsd: 0,
    accessMode: "CONTRIBUTOR_ACTION_REQUIRED" as const,
  };
  writeCachedPlatformSetupState({
    ...EMPTY_PLATFORM_SETUP_STATE,
    workspaces: [ws],
    orgUnits: [
      {
        id: "ou-arch-25-5",
        name: "Architecture",
        slug: "architecture",
        level: "TEAM",
        parentId: "",
        billingEnabled: true,
      },
    ],
  });
  seedVitestPlatformSetupState(
    {
      workspaces: [ws],
      ai_model_mappings: aiModelMappings,
    },
    { email: "karim.admin@orcia.fr", displayName: "Karim Admin" },
  );
}

describe("Story 25.5 — Assistant Unlocked with Chat-Only Model & RAG Datasource Guard (RouterProvider)", () => {
  beforeEach(() => {
    clearPlatformSetupStorage();
    resetAuthSessionStore();
    resetVitestApiBackend();
    resetVitestConnectorsMockState();
  });

  afterEach(() => {
    cleanup();
    clearPlatformSetupStorage();
    resetAuthSessionStore();
    resetVitestApiBackend();
    resetVitestConnectorsMockState();
  });

  it("keeps /assistant unlocked with non-blocking notice and allows sending a message when 1 chat model and 0 embedding model are active", async () => {
    seedAdminAndWorkspace([
      {
        id: "chat-only-1",
        scope_level: "GLOBAL",
        scope_id: null,
        inference_tier: "medium",
        usage: "chat",
        is_active: true,
        provider_slug: "openai",
        model_family: "OpenAI",
        model_name: "gpt-4o-mini",
        endpoint_uri: "https://api.openai.com/v1",
      },
    ]);

    await renderAppAtRoute("/assistant");
    dismissFirstBootAdminIfOpen();

    await waitFor(() => {
      expect(screen.getByTestId("assistant-rag-inactive-notice")).toBeDefined();
    });
    expect(screen.queryByTestId("assistant-no-chat-model-banner")).toBeNull();

    const link = screen.getByTestId("assistant-configure-embedding-link");
    expect(link.getAttribute("href")).toBe("/settings/ai-models");

    const input = screen.getByTestId("assistant-three-speed-input") as HTMLInputElement;
    const sendBtn = screen.getByTestId("assistant-three-speed-send-btn") as HTMLButtonElement;
    expect(input.disabled).toBe(false);
    expect(sendBtn.disabled).toBe(false);

    fireEvent.change(input, { target: { value: "Explique notre architecture sans RAG." } });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(screen.getByText("Explique notre architecture sans RAG.")).toBeDefined();
    });
  });

  it("displays blocking assistant-no-chat-model-banner on /assistant when 0 chat model exists (even with an embedding model)", async () => {
    seedAdminAndWorkspace([
      {
        id: "emb-only-1",
        scope_level: "GLOBAL",
        scope_id: null,
        inference_tier: "simple",
        usage: "embedding",
        is_active: true,
        provider_slug: "ollama",
        model_family: "BGE",
        model_name: "bge-m3:latest",
        endpoint_uri: "http://localhost:11434/v1",
      },
    ]);

    await renderAppAtRoute("/assistant");
    dismissFirstBootAdminIfOpen();

    await waitFor(() => {
      expect(screen.getByTestId("assistant-no-chat-model-banner")).toBeDefined();
    });
    expect(screen.getByTestId("assistant-no-chat-model-banner").getAttribute("role")).toBe("alert");
    expect((screen.getByTestId("assistant-three-speed-input") as HTMLInputElement).disabled).toBe(true);
    expect((screen.getByTestId("assistant-three-speed-send-btn") as HTMLButtonElement).disabled).toBe(true);
  });

  it("disables RAG source natures in WorkspaceSourceAttachModal without embedding model, allows SOURCE_CODE, and displays [role=alert] on 422 API error", async () => {
    seedAdminAndWorkspace([
      {
        id: "chat-only-1",
        scope_level: "GLOBAL",
        scope_id: null,
        inference_tier: "medium",
        usage: "chat",
        is_active: true,
        provider_slug: "openai",
        model_family: "OpenAI",
        model_name: "gpt-4o-mini",
        endpoint_uri: "https://api.openai.com/v1",
      },
    ]);
    seedVitestConnectorsInitialData({ connectors: [], datasources: [] });

    let force422OnNextPost = false;
    const origFetch = globalThis.fetch;
    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      if (
        force422OnNextPost &&
        url.includes(`/api/v1/workspaces/${TEST_WS_ID}/datasources`) &&
        init?.method === "POST"
      ) {
        return new Response(
          JSON.stringify({
            type: "https://orcia.io/problems/no-active-embedding-model",
            title: "Modèle d'embedding requis",
            status: 422,
            detail: "Aucun modèle d'embedding actif configuré au niveau GLOBAL.",
            error_code: "ERR_NO_ACTIVE_EMBEDDING_MODEL",
          }),
          { status: 422, headers: { "content-type": "application/problem+json" } },
        );
      }
      return origFetch(input, init);
    };

    try {
      await renderAppAtRoute(`/workspaces/${TEST_WS_ID}/sources`);
      dismissFirstBootAdminIfOpen();

      await waitFor(() => {
        expect(screen.getByTestId("open-attach-source-modal-btn")).toBeDefined();
      });
      fireEvent.click(screen.getByTestId("open-attach-source-modal-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("datasource-rag-embedding-required-notice")).toBeDefined();
      });
      expect(screen.getByTestId("datasource-configure-embedding-link").getAttribute("href")).toBe(
        "/settings/ai-models",
      );

      const natureSelect = screen.getByTestId("modal-source-nature-select") as HTMLSelectElement;
      expect(natureSelect.value).toBe("SOURCE_CODE");

      const options = Array.from(natureSelect.options);
      const byValue = new Map(options.map((opt) => [opt.value, opt]));
      expect(byValue.get("DOCUMENT_KB")?.disabled).toBe(true);
      expect(byValue.get("WORK_TRACKER")?.disabled).toBe(true);
      expect(byValue.get("RELATIONAL_SCHEMA")?.disabled).toBe(true);
      expect(byValue.get("SOURCE_CODE")?.disabled).toBe(false);

      // Creating SOURCE_CODE succeeds
      fireEvent.change(screen.getByTestId("modal-source-alias-input"), {
        target: { value: "Repo Code Sans Embedding" },
      });
      fireEvent.change(screen.getByTestId("modal-source-uri-input"), {
        target: { value: "https://gitlab.corp.local/core/repo.git" },
      });
      fireEvent.click(screen.getByTestId("modal-source-save-btn"));

      await waitFor(() => {
        expect(screen.getAllByText("Repo Code Sans Embedding").length).toBeGreaterThanOrEqual(1);
      });

      // Verify 422 ERR_NO_ACTIVE_EMBEDDING_MODEL is surfaced in [role="alert"] without silent close
      force422OnNextPost = true;
      fireEvent.click(screen.getByTestId("open-attach-source-modal-btn"));
      await waitFor(() => {
        expect(screen.getByTestId("workspace-source-attach-modal")).toBeDefined();
      });
      fireEvent.change(screen.getByTestId("modal-source-alias-input"), {
        target: { value: "Source Rejetee 422" },
      });
      fireEvent.change(screen.getByTestId("modal-source-uri-input"), {
        target: { value: "https://confluence.corp.local/spaces/DOC" },
      });
      fireEvent.click(screen.getByTestId("modal-source-save-btn"));

      await waitFor(() => {
        const alertEl = screen.getByTestId("modal-source-error-alert");
        expect(alertEl.getAttribute("role")).toBe("alert");
        expect(alertEl.textContent).toContain("Aucun modèle d'indexation sémantique actif");
      });
    } finally {
      globalThis.fetch = origFetch;
    }
  });

  it("does NOT unlock RAG source natures in WorkspaceSourceAttachModal for non-GLOBAL or draining embedding models", async () => {
    for (const variant of [
      {
        id: "emb-ws-scoped",
        scope_level: "WORKSPACE",
        scope_id: TEST_WS_ID,
        draining: false,
      },
      {
        id: "emb-global-draining",
        scope_level: "GLOBAL",
        scope_id: null,
        draining: true,
      },
    ]) {
      clearPlatformSetupStorage();
      resetAuthSessionStore();
      resetVitestApiBackend();
      resetVitestConnectorsMockState();

      seedAdminAndWorkspace([
        {
          id: "chat-global-1",
          scope_level: "GLOBAL",
          scope_id: null,
          inference_tier: "medium",
          usage: "chat",
          is_active: true,
          draining: false,
          provider_slug: "openai",
          model_family: "OpenAI",
          model_name: "gpt-4o-mini",
          endpoint_uri: "https://api.openai.com/v1",
        },
        {
          id: variant.id,
          scope_level: variant.scope_level,
          scope_id: variant.scope_id,
          inference_tier: "simple",
          usage: "embedding",
          is_active: true,
          draining: variant.draining,
          provider_slug: "openai",
          model_family: "OpenAI",
          model_name: "text-embedding-3-small",
          endpoint_uri: "https://api.openai.com/v1",
        },
      ]);
      seedVitestConnectorsInitialData({ connectors: [], datasources: [] });

      const view = await renderAppAtRoute(`/workspaces/${TEST_WS_ID}/sources`);
      dismissFirstBootAdminIfOpen();

      await waitFor(() => {
        expect(screen.getByTestId("open-attach-source-modal-btn")).toBeDefined();
      });
      fireEvent.click(screen.getByTestId("open-attach-source-modal-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("datasource-rag-embedding-required-notice")).toBeDefined();
      });
      const natureSelect = screen.getByTestId("modal-source-nature-select") as HTMLSelectElement;
      const byValue = new Map(Array.from(natureSelect.options).map((opt) => [opt.value, opt]));
      expect(byValue.get("DOCUMENT_KB")?.disabled).toBe(true);
      expect(byValue.get("WORK_TRACKER")?.disabled).toBe(true);
      expect(byValue.get("RELATIONAL_SCHEMA")?.disabled).toBe(true);
      expect(byValue.get("SOURCE_CODE")?.disabled).toBe(false);

      view.unmount();
      cleanup();
    }
  });
});
