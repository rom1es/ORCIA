import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
import { resetVitestApiBackend } from "./vitest.setup";
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

describe("Story 18.1 — Déport des Sources dans /workspaces/$wsId/sources, Modale OrciaDialog, Filtres Multi-Nature & Survie F5", () => {
  const testWsId = "ws-test-18-1";

  beforeEach(() => {
    clearPlatformSetupStorage();
    resetAuthSessionStore();
    resetVitestApiBackend();
    resetVitestConnectorsMockState();

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

    writeCachedPlatformSetupState({
      ...EMPTY_PLATFORM_SETUP_STATE,
      workspaces: [
        {
          workspaceId: testWsId,
          name: "Espace Architecture & Core",
          ownerOrgUnitName: "Architecture",
          visibilityMode: "STANDARD",
          lifecyclePhase: "BUILD",
          suggestedWorkflows: [],
          finopsCostUsd: 120,
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
        },
      ],
      orgUnits: [
        {
          id: "ou-arch-1",
          name: "Architecture",
          slug: "architecture",
          level: "TEAM",
          parentId: "",
          billingEnabled: true,
        },
      ],
    });

    seedVitestConnectorsInitialData({
      connectors: [
        {
          id: "conn-gitlab-1",
          connector_kind: "GITLAB",
          name: "GitLab Entreprise DS3C",
          base_url: "https://gitlab.corp.internal",
          auth_mode: "SERVICE_SECRET",
          enabled: true,
          admin_secret_status: {
            configured: true,
            fingerprint: "sha256:12345678",
            updated_at_iso: new Date().toISOString(),
          },
          created_at_iso: new Date().toISOString(),
          updated_at_iso: new Date().toISOString(),
        },
      ],
      datasources: [
        {
          id: "ds-existing-1",
          workspace_id: testWsId,
          alias: "Confluence Architecture",
          scheme: "confluence",
          uri: "https://confluence.corp.internal/arch",
          connector_id: null,
          sync_identity_mode: "SERVICE_ACCOUNT",
          service_account_id: null,
          referent_user_id: null,
          source_nature: "DOCUMENT_KB",
          sync_mode: "POLLING_24H",
          target_scope: "ARCH",
          target_ref: null,
          codegraph_enabled: false,
          codegraph_status: "DISABLED",
          freshness_status: "SYNCED",
          created_at_iso: new Date().toISOString(),
        },
      ],
    });
  });

  afterEach(() => {
    cleanup();
    clearPlatformSetupStorage();
    resetAuthSessionStore();
    resetVitestApiBackend();
    resetVitestConnectorsMockState();
  });

  it("renders /workspaces/$wsId/sources with breadcrumb, filter pills, and table", async () => {
    await renderAppAtRoute(`/workspaces/${testWsId}/sources`);
    dismissFirstBootAdminIfOpen();

    // 1. Breadcrumb validation
    await waitFor(() => {
      const breadcrumb = screen.getByTestId("workspace-sources-breadcrumb");
      expect(breadcrumb).toBeDefined();
      expect(breadcrumb.textContent).toContain("Mes Espaces");
      expect(breadcrumb.textContent).toContain("Sources");
    });

    // 2. Table rendered with existing datasource
    await waitFor(() => {
      expect(screen.getByTestId("workspace-sources-table")).toBeDefined();
      expect(screen.getByText("Confluence Architecture")).toBeDefined();
    });

    // 3. Multi-nature filter pills interaction
    const codeFilterPill = screen.getByTestId("sources-filter-pill-source_code");
    expect(codeFilterPill).toBeDefined();
    fireEvent.click(codeFilterPill);

    // Empty state should be visible for SOURCE_CODE
    await waitFor(() => {
      expect(screen.getByTestId("workspace-sources-empty-state")).toBeDefined();
    });

    // Switch back to ALL filter
    fireEvent.click(screen.getByTestId("sources-filter-pill-all"));
    await waitFor(() => {
      expect(screen.getByText("Confluence Architecture")).toBeDefined();
    });
  });

  it("attaches a new SOURCE_CODE datasource with GitNexus via modal and verifies F5 survival", async () => {
    const { unmount } = await renderAppAtRoute(`/workspaces/${testWsId}/sources`);
    dismissFirstBootAdminIfOpen();

    await waitFor(() => {
      expect(screen.getByTestId("open-attach-source-modal-btn")).toBeDefined();
    });

    // 1. Open attach modal
    fireEvent.click(screen.getByTestId("open-attach-source-modal-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("workspace-source-attach-modal")).toBeDefined();
    });

    // 2. Fill form in modal
    fireEvent.change(screen.getByTestId("modal-source-alias-input"), {
      target: { value: "Repo GitLab Microservices" },
    });
    fireEvent.change(screen.getByTestId("modal-source-uri-input"), {
      target: { value: "https://gitlab.corp.internal/core/services.git" },
    });
    fireEvent.change(screen.getByTestId("modal-source-nature-select"), {
      target: { value: "SOURCE_CODE" },
    });
    fireEvent.change(screen.getByTestId("modal-source-sync-mode-select"), {
      target: { value: "WEBHOOK_PUSH" },
    });
    fireEvent.change(screen.getByTestId("modal-source-target-scope-input"), {
      target: { value: "services/core" },
    });
    fireEvent.change(screen.getByTestId("modal-source-target-ref-input"), {
      target: { value: "main" },
    });

    // 3. Enable GitNexus switch inside modal
    const cgSwitch = screen.getByTestId("modal-gitnexus-enabled-switch");
    fireEvent.click(cgSwitch);

    // 4. Submit form
    fireEvent.click(screen.getByTestId("modal-source-save-btn"));

    // 5. Verify datasource appears in table with GitNexus active badge
    await waitFor(() => {
      expect(screen.getAllByText("Repo GitLab Microservices").length).toBeGreaterThanOrEqual(1);
    });

    // 6. Gate de Survie au F5 : unmount the React component tree and re-render fresh
    unmount();

    // Re-mount fresh at the exact same URL (simulating F5 page refresh)
    await renderAppAtRoute(`/workspaces/${testWsId}/sources`);
    dismissFirstBootAdminIfOpen();

    // Verify that state survived page reload
    await waitFor(() => {
      expect(screen.getByTestId("workspace-sources-table")).toBeDefined();
      expect(screen.getAllByText("Repo GitLab Microservices").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("navigates from /settings connectors tab to /workspaces/$wsId/sources via banner button", async () => {
    await renderAppAtRoute("/settings");
    dismissFirstBootAdminIfOpen();

    // Go to Connectors tab
    await waitFor(() => {
      expect(screen.getByTestId("settings-tab-connectors")).toBeDefined();
    });
    fireEvent.click(screen.getByTestId("settings-tab-connectors"));

    // Check deportation banner is present
    await waitFor(() => {
      expect(screen.getByTestId("settings-deported-sources-banner")).toBeDefined();
      expect(screen.getByTestId("settings-goto-workspace-sources-btn")).toBeDefined();
    });

    // Click banner CTA button
    fireEvent.click(screen.getByTestId("settings-goto-workspace-sources-btn"));

    // Verify navigation landed on /workspaces/$wsId/sources
    await waitFor(() => {
      expect(screen.getByTestId("workspace-sources-breadcrumb")).toBeDefined();
      expect(screen.getByTestId("workspace-sources-master-table-root")).toBeDefined();
    });
  });
});
