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

const TEST_WORKSPACE = {
  workspaceId: "ws-test-1",
  name: "Espace Test",
  visibilityMode: "STANDARD" as const,
  ownerOrgUnitName: "Equipe Test",
  lifecyclePhase: "BUILD" as const,
  suggestedWorkflows: [],
  accessMode: "CONTRIBUTOR_ACTION_REQUIRED" as const,
  finopsCostUsd: 0,
};

describe("Story 19.6 / AD-24 Epic 25 — Assistant Chat Gate, Non-Blocking RAG Notice & F5 Survival", () => {
  it("blocks input with assistant-no-chat-model-banner when 0 chat model is configured and survives F5", async () => {
    seedVitestPlatformSetupState(
      {
        workspaces: [TEST_WORKSPACE],
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

    await waitFor(() => {
      expect(screen.getByTestId("assistant-no-chat-model-banner")).toBeDefined();
    });

    const banner = screen.getByTestId("assistant-no-chat-model-banner");
    expect(banner.getAttribute("role")).toBe("alert");

    const promptInput = screen.getByTestId("assistant-three-speed-input") as HTMLInputElement;
    expect(promptInput.disabled).toBe(true);
    const sendBtn = screen.getByTestId("assistant-three-speed-send-btn") as HTMLButtonElement;
    expect(sendBtn.disabled).toBe(true);

    const link = screen.getByTestId("assistant-configure-chat-model-link");
    expect(link.getAttribute("href")).toBe("/settings/ai-models");
    fireEvent.click(link);
    expect(onNavigateMock).toHaveBeenCalledWith("/settings/ai-models");

    // F5 survival
    unmount();

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={onNavigateMock}>
          <InboxFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("assistant-no-chat-model-banner")).toBeDefined();
    });
    expect((screen.getByTestId("assistant-three-speed-input") as HTMLInputElement).disabled).toBe(true);
    expect((screen.getByTestId("assistant-three-speed-send-btn") as HTMLButtonElement).disabled).toBe(true);
  });

  it("keeps Assistant input unlocked with non-blocking assistant-rag-inactive-notice when 1 chat model exists and 0 embedding model exists", async () => {
    seedVitestPlatformSetupState(
      {
        workspaces: [TEST_WORKSPACE],
        ai_model_mappings: [
          {
            id: "chat-model-1",
            scope_level: "GLOBAL",
            scope_id: null,
            inference_tier: "medium",
            usage: "chat",
            is_active: true,
            provider: "openai",
            model_name: "gpt-4o-mini",
          },
        ],
      },
      { email: "admin@orcia.test", displayName: "Admin Test" },
    );

    const onNavigateMock = vi.fn();

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={onNavigateMock}>
          <InboxFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("assistant-rag-inactive-notice")).toBeDefined();
    });
    expect(screen.queryByTestId("assistant-no-chat-model-banner")).toBeNull();

    const promptInput = screen.getByTestId("assistant-three-speed-input") as HTMLInputElement;
    expect(promptInput.disabled).toBe(false);
    const sendBtn = screen.getByTestId("assistant-three-speed-send-btn") as HTMLButtonElement;
    expect(sendBtn.disabled).toBe(false);

    const link = screen.getByTestId("assistant-configure-embedding-link");
    expect(link.getAttribute("href")).toBe("/settings/ai-models");
    fireEvent.click(link);
    expect(onNavigateMock).toHaveBeenCalledWith("/settings/ai-models");
  });

  it("hides both banner and notice when active chat and embedding models are configured", async () => {
    seedVitestPlatformSetupState(
      {
        workspaces: [TEST_WORKSPACE],
        ai_model_mappings: [
          {
            id: "chat-model-1",
            scope_level: "GLOBAL",
            scope_id: null,
            inference_tier: "medium",
            usage: "chat",
            is_active: true,
            provider: "openai",
            model_name: "gpt-4o-mini",
          },
          {
            id: "emb-model-1",
            scope_level: "GLOBAL",
            scope_id: null,
            inference_tier: "simple",
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

    await waitFor(() => {
      expect((screen.getByTestId("assistant-three-speed-input") as HTMLInputElement).disabled).toBe(false);
    });
    expect(screen.queryByTestId("assistant-no-chat-model-banner")).toBeNull();
    expect(screen.queryByTestId("assistant-rag-inactive-notice")).toBeNull();
  });
});
