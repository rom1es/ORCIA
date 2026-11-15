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

describe("Story 19.7 — RAG Reindexing Banner, Input Lock, Hub Panel & F5 Survival", () => {
  it("displays reindexing banner with percentage, disables input and send button, and survives F5 refresh", async () => {
    // Platform setup with an active embedding model and reindexing IN_PROGRESS at 55%
    seedVitestPlatformSetupState(
      {
        workspaces: [
          {
            workspaceId: "ws-claims-alpha",
            name: "Claims Alpha",
            visibilityMode: "STANDARD",
            ownerOrgUnitName: "Claims Team",
            lifecyclePhase: "BUILD",
            suggestedWorkflows: [],
            accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
            finopsCostUsd: 0,
          },
        ],
        ai_model_mappings: [
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
        ],
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

    // 1. Verify reindexing banner is displayed with 55%
    await waitFor(() => {
      expect(screen.getByTestId("assistant-reindexing-banner")).toBeDefined();
    });

    const banner = screen.getByTestId("assistant-reindexing-banner");
    expect(banner.textContent).toContain("55%");
    expect(banner.textContent).toContain("Réindexation sémantique en cours");

    // 2. Verify input and send button are disabled
    const promptInput = screen.getByTestId("assistant-three-speed-input") as HTMLInputElement;
    expect(promptInput.disabled).toBe(true);

    const sendBtn = screen.getByTestId("assistant-three-speed-send-btn") as HTMLButtonElement;
    expect(sendBtn.disabled).toBe(true);

    // 3. F5 Survival: unmount and remount (simulates page refresh)
    unmount();

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={onNavigateMock}>
          <InboxFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("assistant-reindexing-banner")).toBeDefined();
    });
    expect((screen.getByTestId("assistant-three-speed-input") as HTMLInputElement).disabled).toBe(true);
    expect((screen.getByTestId("assistant-three-speed-send-btn") as HTMLButtonElement).disabled).toBe(true);
  });

  it("displays failure banner with relaunch action when reindexing failed", async () => {
    seedVitestPlatformSetupState(
      {
        workspaces: [
          {
            workspaceId: "ws-claims-alpha",
            name: "Claims Alpha",
            visibilityMode: "STANDARD",
            ownerOrgUnitName: "Claims Team",
            lifecyclePhase: "BUILD",
            suggestedWorkflows: [],
            accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
            finopsCostUsd: 0,
          },
        ],
        ai_model_mappings: [
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
        ],
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
      expect(screen.getByTestId("assistant-reindex-failed-banner")).toBeDefined();
    });

    const failedBanner = screen.getByTestId("assistant-reindex-failed-banner");
    expect(failedBanner.textContent).toContain("Quota provider dépassé");

    const relaunchBtn = screen.getByTestId("assistant-relaunch-reindex-btn");
    expect(relaunchBtn).toBeDefined();
    fireEvent.click(relaunchBtn);
  });

  it("renders reindex panel and handles manual trigger in SettingsAiModelsSection", async () => {
    seedVitestPlatformSetupState({
      ai_model_mappings: [
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
      ],
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
    expect(panel.textContent).toContain("COMPLETED (100%)");
    expect(panel.textContent).toContain("text-embedding-3-small");

    const relaunchBtn = screen.getByTestId("relaunch-reindex-button");
    expect(relaunchBtn).toBeDefined();
    fireEvent.click(relaunchBtn);
  });

  it("when corpus has 0 chunks (Day-0 state), reindexing is immediately COMPLETED without blocking banner or disabled input", async () => {
    seedVitestPlatformSetupState(
      {
        workspaces: [
          {
            workspaceId: "ws-claims-alpha",
            name: "Claims Alpha",
            visibilityMode: "STANDARD",
            ownerOrgUnitName: "Claims Team",
            lifecyclePhase: "BUILD",
            suggestedWorkflows: [],
            accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
            finopsCostUsd: 0,
          },
        ],
        ai_model_mappings: [
          {
            id: "model-active-embed",
            scope_level: "GLOBAL",
            scope_id: "global",
            display_name: "Active OpenAI Embedding",
            inference_tier: "auto",
            effort: "default",
            provider_slug: "openai",
            model_family: "OpenAI",
            model_name: "text-embedding-3-small",
            endpoint_uri: "https://api.openai.com/v1",
            is_active: true,
            usage: "embedding",
          },
        ],
      },
      { email: "admin@orcia.test", displayName: "Admin Test" },
    );

    // Day-0 state: COMPLETED directly with 0 chunks and 100%
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

    const promptInput = (await screen.findByTestId("assistant-three-speed-input")) as HTMLInputElement;
    expect(promptInput).toBeDefined();
    expect(promptInput.disabled).toBe(false);

    const sendBtn = screen.getByTestId("assistant-three-speed-send-btn") as HTMLButtonElement;
    expect(sendBtn.disabled).toBe(false);

    expect(screen.queryByTestId("assistant-reindexing-banner")).toBeNull();
  });
});
