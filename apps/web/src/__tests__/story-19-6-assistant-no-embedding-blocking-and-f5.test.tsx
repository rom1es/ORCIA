import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ShellContainer } from "../components/ShellContainer";
import { InboxFeaturePanel } from "../features/inbox";
import { I18nProvider } from "../i18n";
import { seedVitestPlatformSetupState } from "./vitest.setup";

afterEach(() => {
  cleanup();
});

describe("Story 19.6 — Assistant Blocking without Active Embedding Model & F5 Survival", () => {
  it("displays explicit banner, disables prompt input and send button, and offers a link to /settings/ai-models when no embedding model exists", async () => {
    // Day-0 initial state: platform admin exists, but zero active embedding model mappings
    seedVitestPlatformSetupState(
      {
        workspaces: [
          {
            workspaceId: "ws-test-1",
            name: "Espace Test",
            visibilityMode: "STANDARD",
            ownerOrgUnitName: "Equipe Test",
            lifecyclePhase: "BUILD",
            suggestedWorkflows: [],
            accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
            finopsCostUsd: 0,
          },
        ],
        ai_model_mappings: [],
      },
      { email: "admin@orcia.test", displayName: "Admin Test" },
    );

    const onNavigateMock = vi.fn();

    const { unmount } = render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={onNavigateMock}>
          <InboxFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    // 1. Verify banner is displayed with warning text
    await waitFor(() => {
      expect(screen.getByTestId("assistant-no-embedding-banner")).toBeDefined();
    });

    const banner = screen.getByTestId("assistant-no-embedding-banner");
    expect(banner.textContent).toContain("Modèle d'embedding sémantique requis");

    // 2. Verify prompt input is disabled
    const promptInput = screen.getByTestId("assistant-three-speed-input") as HTMLInputElement;
    expect(promptInput.disabled).toBe(true);

    // 3. Verify send button is disabled
    const sendBtn = screen.getByTestId("assistant-three-speed-send-btn") as HTMLButtonElement;
    expect(sendBtn.disabled).toBe(true);

    // 4. Verify configure link points to /settings/ai-models and triggers navigation
    const link = screen.getByTestId("assistant-configure-embedding-link");
    expect(link.getAttribute("href")).toBe("/settings/ai-models");
    fireEvent.click(link);
    expect(onNavigateMock).toHaveBeenCalledWith("/settings/ai-models");

    // 5. Test F5 survival: unmount and remount (simulates page refresh)
    unmount();

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={onNavigateMock}>
          <InboxFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("assistant-no-embedding-banner")).toBeDefined();
    });
    expect((screen.getByTestId("assistant-three-speed-input") as HTMLInputElement).disabled).toBe(true);
    expect((screen.getByTestId("assistant-three-speed-send-btn") as HTMLButtonElement).disabled).toBe(true);
  });

  it("unlocks Assistant input and removes banner when an active embedding model is configured", async () => {
    seedVitestPlatformSetupState(
      {
        workspaces: [
          {
            workspaceId: "ws-test-1",
            name: "Espace Test",
            visibilityMode: "STANDARD",
            ownerOrgUnitName: "Equipe Test",
            lifecyclePhase: "BUILD",
            suggestedWorkflows: [],
            accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
            finopsCostUsd: 0,
          },
        ],
        ai_model_mappings: [
          {
            id: "emb-model-1",
            scope_level: "GLOBAL",
            scope_id: null,
            inference_tier: "light",
            usage: "embedding",
            is_active: true,
            provider: "ollama",
            model_name: "bge-m3:latest",
          },
        ],
      },
      { email: "admin@orcia.test", displayName: "Admin Test" },
    );

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <InboxFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    // Banner should NOT be present
    expect(screen.queryByTestId("assistant-no-embedding-banner")).toBeNull();

    // Input and send button should NOT be disabled
    const promptInput = screen.getByTestId("assistant-three-speed-input") as HTMLInputElement;
    expect(promptInput.disabled).toBe(false);
    const sendBtn = screen.getByTestId("assistant-three-speed-send-btn") as HTMLButtonElement;
    expect(sendBtn.disabled).toBe(false);
  });
});
