import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PlatformSetupProvider } from "../components/platformSetupStore";
import { ShellContainer } from "../components/ShellContainer";
import { InboxFeaturePanel } from "../features/inbox";
import { clearAssistantFoldersAndPrefsStorage } from "../features/inbox/assistantFoldersAndPrefsStore";
import { resetBackgroundAssistantStreamForTests } from "../features/inbox/assistantBackgroundStreamStore";
import { clearSavedAssistantConversationsStorage } from "../features/inbox/savedConversationsStore";
import { I18nProvider } from "../i18n";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

afterEach(() => {
  cleanup();
  clearSavedAssistantConversationsStorage();
  clearAssistantFoldersAndPrefsStorage();
  resetBackgroundAssistantStreamForTests();
  resetAuthSessionStore();
  resetVitestApiBackend();
});

const WORKSPACE_ITEM = {
  workspaceId: "01a26729-1111-7000-8000-000000000042",
  name: "Espace Pilotage",
  visibilityMode: "STANDARD" as const,
  ownerOrgUnitName: "Product Team",
  lifecyclePhase: "BUILD" as const,
  suggestedWorkflows: [],
  accessMode: "CONTRIBUTOR_ACTION_REQUIRED" as const,
  finopsCostUsd: 0,
};

function setupUserRole(role: "PLATFORM_ADMIN" | "TEAM_LEAD" | "CONTRIBUTOR") {
  useAuthSessionStore.getState().setAuthSession({
    isAuthenticated: true,
    email: `${role.toLowerCase()}@orcia.test`,
    displayName: `${role} User`,
    roles: [role],
    activeHat: role,
    readOnlyObserver: false,
  });
}

describe("Story 29.3 - Mon Assistant Speed Alignment & RBAC Composer Notices", () => {
  it("hides admin AI-model navigation links for TEAM_LEAD and CONTRIBUTOR while keeping compact non-stacked notices", async () => {
    setupUserRole("TEAM_LEAD");
    seedVitestPlatformSetupState(
      {
        workspaces: [WORKSPACE_ITEM],
        ai_model_mappings: [
          {
            id: "chat-no-tools-1",
            scope_level: "GLOBAL",
            scope_id: null,
            inference_tier: "medium",
            usage: "chat",
            is_active: true,
            supports_tools: false,
            provider: "ollama",
            model_name: "gemma3:4b",
          },
        ],
      },
      { email: "team_lead@orcia.test", displayName: "Team Lead User", roles: ["TEAM_LEAD"] },
    );

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={vi.fn()}>
          <InboxFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("assistant-rag-inactive-notice")).toBeDefined();
    });

    // Non-admin TEAM_LEAD must NEVER see clickable /settings/ai-models links.
    expect(screen.queryByTestId("assistant-configure-embedding-link")).toBeNull();
    expect(screen.queryByTestId("assistant-configure-chat-model-link")).toBeNull();
    expect(screen.getByTestId("assistant-rag-admin-guidance")).toBeDefined();
    expect(screen.getByTestId("assistant-composer-status-strip")).toBeDefined();
    expect(screen.getByTestId("assistant-tools-unsupported-notice")).toBeDefined();

    // When tools are unsupported, speed falls back to SPEED_1_FAST with aligned Fast/Rapide label (not Standard).
    const pickerTrigger = screen.getByTestId("assistant-model-and-effort-picker-trigger");
    expect(pickerTrigger.textContent).toContain("Rapide");
  });

  it("hides admin chat-model link for CONTRIBUTOR when 0 chat models are configured", async () => {
    setupUserRole("CONTRIBUTOR");
    seedVitestPlatformSetupState(
      {
        workspaces: [WORKSPACE_ITEM],
        ai_model_mappings: [],
      },
      { email: "contributor@orcia.test", displayName: "Contributor User", roles: ["CONTRIBUTOR"] },
    );

    render(
      <I18nProvider initialLocale="en">
        <PlatformSetupProvider>
          <InboxFeaturePanel />
        </PlatformSetupProvider>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("assistant-no-chat-model-banner")).toBeDefined();
    });
    expect(screen.queryByTestId("assistant-configure-chat-model-link")).toBeNull();
    expect(screen.getByTestId("assistant-no-chat-admin-guidance").textContent).toContain(
      "platform administrator",
    );
  });

  it("aligns composer tier/effort display with dispatched speed and active user hat in EN and FR", async () => {
    setupUserRole("TEAM_LEAD");
    seedVitestPlatformSetupState(
      {
        workspaces: [WORKSPACE_ITEM],
        ai_model_mappings: [
          {
            id: "chat-tools-1",
            scope_level: "GLOBAL",
            scope_id: null,
            inference_tier: "medium",
            usage: "chat",
            is_active: true,
            supports_tools: true,
            provider: "openai",
            model_name: "gpt-4o-mini",
          },
          {
            id: "emb-1",
            scope_level: "GLOBAL",
            scope_id: null,
            inference_tier: "simple",
            usage: "embedding",
            is_active: true,
            provider: "openai",
            model_name: "text-embedding-3-small",
          },
        ],
      },
      { email: "team_lead@orcia.test", displayName: "Team Lead User", roles: ["TEAM_LEAD"] },
    );

    const turnPayloads: Array<Record<string, unknown>> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      if (url.includes("/api/v1/assistant/turns") && init?.method === "POST" && typeof init.body === "string") {
        turnPayloads.push(JSON.parse(init.body) as Record<string, unknown>);
      }
      return origFetch(input, init);
    };

    try {
      render(
        <I18nProvider initialLocale="en">
          <ShellContainer onNavigate={vi.fn()}>
            <InboxFeaturePanel />
          </ShellContainer>
        </I18nProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("assistant-model-and-effort-picker-trigger")).toBeDefined();
      });

      const pickerTrigger = screen.getByTestId("assistant-model-and-effort-picker-trigger");
      expect(pickerTrigger.textContent).toContain("Standard");

      const input = screen.getByTestId("assistant-three-speed-input") as HTMLInputElement;
      fireEvent.change(input, { target: { value: "Summarize team risks" } });
      fireEvent.click(screen.getByTestId("assistant-three-speed-send-btn"));

      await waitFor(() => {
        expect(turnPayloads.length).toBeGreaterThan(0);
      });

      // Standard balanced mode must dispatch SPEED_2_AGENT_TOOLS (never SPEED_1_FAST) and real TEAM_LEAD hat.
      expect(turnPayloads[0]?.requested_speed).toBe("SPEED_2_AGENT_TOOLS");
      expect(turnPayloads[0]?.hat).toBe("TEAM_LEAD");
    } finally {
      globalThis.fetch = origFetch;
    }
  });
});
