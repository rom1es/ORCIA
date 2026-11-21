import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ShellContainer } from "../components/ShellContainer";
import { InboxFeaturePanel } from "../features/inbox";
import { I18nProvider } from "../i18n";
import { SettingsAiModelsSection } from "../routes/SettingsAiModelsSection";
import {
  seedVitestPlatformSetupState,
  setVitestMockReindexStatus,
} from "./vitest.setup";

afterEach(() => {
  cleanup();
});

const dummyTierLabels = {
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

const ACTIVE_CHAT_AND_EMBED_MAPPINGS = [
  {
    id: "mod-chat-1",
    display_name: "GPT-4o Mini",
    inference_tier: "medium",
    effort: "balanced",
    provider_slug: "openai",
    model_family: "OpenAI",
    model_name: "gpt-4o-mini",
    endpoint_uri: "https://api.openai.com/v1",
    auth_mode: "none_local",
    protocol_mode: "openai_compatible",
    usage: "chat",
    is_active: true,
  },
  {
    id: "mod-emb-1",
    display_name: "Text Embedding 3 Small",
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
  },
];

const TEST_WORKSPACE = {
  workspaceId: "ws-claims-alpha",
  name: "Claims Alpha",
  visibilityMode: "STANDARD" as const,
  ownerOrgUnitName: "Claims Team",
  lifecyclePhase: "BUILD" as const,
  suggestedWorkflows: [],
  accessMode: "CONTRIBUTOR_ACTION_REQUIRED" as const,
  finopsCostUsd: 0,
};

describe("Story 19.7 / AD-24 Epic 25 — Non-Blocking RAG Reindexing Notice, Hub Panel & F5 Survival", () => {
  it("displays non-blocking reindexing notice with percentage, keeps Assistant input active, and survives F5 refresh", async () => {
    seedVitestPlatformSetupState(
      {
        workspaces: [TEST_WORKSPACE],
        ai_model_mappings: ACTIVE_CHAT_AND_EMBED_MAPPINGS,
      },
      { email: "admin@orcia.test", displayName: "Admin Test" },
    );

    setVitestMockReindexStatus({
      status: "IN_PROGRESS",
      progress_percentage: 55,
      target_model_name: "text-embedding-3-small",
      total_chunks: 100,
      processed_chunks: 55,
    });

    const onNavigateMock = vi.fn();

    const { unmount } = render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={onNavigateMock}>
          <InboxFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    // 1. Verify non-blocking reindexing notice is displayed with 55%
    await waitFor(() => {
      expect(screen.getByTestId("assistant-rag-inactive-notice")).toBeDefined();
    });

    const notice = screen.getByTestId("assistant-rag-inactive-notice");
    expect(notice.getAttribute("role")).toBe("status");
    expect(notice.textContent).toContain("55%");

    // 2. Verify input and send button remain enabled when an active chat model exists
    const promptInput = screen.getByTestId("assistant-three-speed-input") as HTMLInputElement;
    expect(promptInput.disabled).toBe(false);

    const sendBtn = screen.getByTestId("assistant-three-speed-send-btn") as HTMLButtonElement;
    expect(sendBtn.disabled).toBe(false);

    // 3. F5 Survival: unmount and remount
    unmount();

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
    expect((screen.getByTestId("assistant-three-speed-input") as HTMLInputElement).disabled).toBe(false);
    expect((screen.getByTestId("assistant-three-speed-send-btn") as HTMLButtonElement).disabled).toBe(false);
  });

  it("displays non-blocking failure notice with relaunch action when reindexing failed while keeping Assistant unlocked", async () => {
    seedVitestPlatformSetupState(
      {
        workspaces: [TEST_WORKSPACE],
        ai_model_mappings: ACTIVE_CHAT_AND_EMBED_MAPPINGS,
      },
      { email: "admin@orcia.test", displayName: "Admin Test" },
    );

    setVitestMockReindexStatus({
      status: "FAILED",
      progress_percentage: 20,
      error_message: "Quota provider dépassé",
      target_model_name: "text-embedding-3-small",
    });

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

    const failedNotice = screen.getByTestId("assistant-rag-inactive-notice");
    expect(failedNotice.textContent).toContain("Quota provider dépassé");
    expect((screen.getByTestId("assistant-three-speed-input") as HTMLInputElement).disabled).toBe(false);

    const relaunchBtn = screen.getByTestId("assistant-relaunch-reindex-btn");
    expect(relaunchBtn).toBeDefined();
    fireEvent.click(relaunchBtn);
  });

  it("renders reindex panel and handles manual trigger in SettingsAiModelsSection", async () => {
    seedVitestPlatformSetupState({
      ai_model_mappings: ACTIVE_CHAT_AND_EMBED_MAPPINGS,
    });

    setVitestMockReindexStatus({
      status: "COMPLETED",
      progress_percentage: 100,
      target_model_name: "text-embedding-3-small",
      total_chunks: 80,
      processed_chunks: 80,
    });

    render(
      <I18nProvider initialLocale="fr">
        <SettingsAiModelsSection
          isFr={true}
          tierAndEffortLabels={dummyTierLabels}
          allowedVerbs={["read", "execute"]}
        />
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("ai-model-reindex-panel")).toBeDefined();
    });

    const panel = screen.getByTestId("ai-model-reindex-panel");
    expect(panel.textContent).toContain("Terminée (100%)");
    expect(screen.getByTestId("reindex-status-badge").getAttribute("data-status")).toBe("COMPLETED");
    expect(panel.textContent).toContain("text-embedding-3-small");

    const relaunchBtn = screen.getByTestId("relaunch-reindex-button");
    expect(relaunchBtn).toBeDefined();
    fireEvent.click(relaunchBtn);
  });

  it("when corpus has 0 chunks (Day-0 state), reindexing is immediately COMPLETED without notice or disabled input", async () => {
    seedVitestPlatformSetupState(
      {
        workspaces: [TEST_WORKSPACE],
        ai_model_mappings: ACTIVE_CHAT_AND_EMBED_MAPPINGS,
      },
      { email: "admin@orcia.test", displayName: "Admin Test" },
    );

    setVitestMockReindexStatus({
      status: "COMPLETED",
      progress_percentage: 100,
      target_model_name: "text-embedding-3-small",
      total_chunks: 0,
      processed_chunks: 0,
    });

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={vi.fn()}>
          <InboxFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    await waitFor(() => {
      const input = screen.getByTestId("assistant-three-speed-input") as HTMLInputElement;
      expect(input.disabled).toBe(false);
    });

    expect(screen.queryByTestId("assistant-rag-inactive-notice")).toBeNull();
    expect(screen.queryByTestId("assistant-no-chat-model-banner")).toBeNull();

    const sendBtn = screen.getByTestId("assistant-three-speed-send-btn") as HTMLButtonElement;
    expect(sendBtn.disabled).toBe(false);
  });
});
