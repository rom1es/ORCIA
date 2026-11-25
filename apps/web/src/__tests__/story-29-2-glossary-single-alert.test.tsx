// @vitest-environment jsdom
import type { ControlCenterWorkspaceGovItem } from "@orcia/ui";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { clearSavedActiveScopeId } from "../components/useShellContainerState";
import { WorkspaceGlossaryAndOntologyTab } from "../features/workspaces/WorkspaceGlossaryAndOntologyTab";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

const TEAM_ID = "0195f292-0000-7000-8000-000000000021";
const WS_ID = "0195f292-0000-7000-8000-000000000201";
const WS_ITEM: ControlCenterWorkspaceGovItem = {
  workspaceId: WS_ID,
  slug: "platform-ws",
  name: "Platform Workspace",
  visibilityMode: "STANDARD",
  lifecyclePhase: "BUILD",
  suggestedWorkflows: [],
  accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
  finopsCostUsd: 0,
};

function seedAdminWorkspace() {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: TEAM_ID,
          name: "Platform Team",
          slug: "platform-team",
          kind: "TEAM",
          level: "TEAM",
          parentId: null,
          billingEnabled: true,
        },
      ],
      workspaces: [WS_ITEM],
    },
    { email: "admin@orcia.fr", displayName: "Admin", roles: ["PLATFORM_ADMIN"] },
  );
  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "test-jwt-token",
    displayName: "Admin",
    email: "admin@orcia.fr",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "PLATFORM_ADMIN",
  });
}

function mockGlossaryConcepts403(originalFetch: typeof fetch): typeof fetch {
  return (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url.includes("/api/v1/ontology-rag/ontology/concepts")) {
      return new Response(
        JSON.stringify({
          type: "https://orcia.io/problems/err-forbidden",
          title: "Forbidden",
          status: 403,
          detail: "Access denied to ontology concepts",
          error_code: "ERR_SCOPE_ACCESS_DENIED",
        }),
        { status: 403, headers: { "Content-Type": "application/problem+json" } },
      );
    }
    return originalFetch(input, init);
  }) as typeof fetch;
}

beforeEach(() => {
  resetVitestApiBackend();
  clearPlatformSetupStorage();
  clearSavedActiveScopeId();
});

afterEach(() => {
  cleanup();
});

describe("Story 29.2 (P2-3) — WorkspaceGlossaryAndOntologyTab Single Alert Banner", () => {
  it("routes errors to onFeedback without duplicate local alert, keeps local alert standalone, and renders 1 role=alert in live Tab 4", async () => {
    seedAdminWorkspace();
    const originalFetch = globalThis.fetch;
    globalThis.fetch = mockGlossaryConcepts403(originalFetch);

    try {
      const onFeedback = vi.fn();
      const withParentFeedback = render(
        <I18nProvider initialLocale="en">
          <WorkspaceGlossaryAndOntologyTab
            isFr={false}
            selectedWorkspace={WS_ITEM}
            orgUnits={[]}
            ontologyConcepts={[]}
            openHelpSection={() => {}}
            onAddConcept={() => {}}
            onPromoteConcept={() => {}}
            onFeedback={onFeedback}
          />
        </I18nProvider>,
      );

      await waitFor(() => {
        expect(onFeedback).toHaveBeenCalledWith(expect.objectContaining({ tone: "crimson" }));
      });
      expect(screen.queryByTestId("workspace-glossary-error-banner")).toBeNull();
      expect(screen.queryAllByRole("alert")).toHaveLength(0);
      withParentFeedback.unmount();
      cleanup();

      const standalone = render(
        <I18nProvider initialLocale="en">
          <WorkspaceGlossaryAndOntologyTab
            isFr={false}
            selectedWorkspace={WS_ITEM}
            orgUnits={[]}
            ontologyConcepts={[]}
            openHelpSection={() => {}}
            onAddConcept={() => {}}
            onPromoteConcept={() => {}}
          />
        </I18nProvider>,
      );
      expect(await screen.findByTestId("workspace-glossary-error-banner")).toBeDefined();
      expect(screen.getAllByRole("alert")).toHaveLength(1);
      standalone.unmount();
      cleanup();

      const queryClient = createOrciaQueryClient();
      const history = createMemoryHistory({ initialEntries: ["/workspaces"] });
      const router = createOrciaRouter({ queryClient, history });
      await router.load();
      const liveView = render(
        <I18nProvider initialLocale="en">
          <QueryClientProvider client={queryClient}>
            <RouterProvider router={router} />
          </QueryClientProvider>
        </I18nProvider>,
      );
      fireEvent.click(await screen.findByTestId("workspace-tab-GLOSSARY_RULES"));
      const banner = await screen.findByTestId("workspaces-action-feedback-banner");
      expect(banner.getAttribute("role")).toBe("alert");
      expect(screen.queryByTestId("workspace-glossary-error-banner")).toBeNull();
      expect(screen.getAllByRole("alert")).toHaveLength(1);
      liveView.unmount();
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
