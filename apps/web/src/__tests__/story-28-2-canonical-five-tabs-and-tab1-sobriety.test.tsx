// @vitest-environment jsdom
import { createOrciaApiClient } from "@orcia/api-client";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { clearSavedActiveScopeId } from "../components/useShellContainerState";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";
import { seedVitestConnectorsInitialData } from "./vitestConnectorsMockHandlers";

const WS_ID = "0195f000-0000-7000-8000-000000000282";

function seedWorkspace(options: { readonly withActivity?: boolean } = {}) {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: "0195f000-0000-7000-8000-000000000020",
          name: "Équipe Produit",
          slug: "equipe-produit",
          level: "TEAM",
          parentId: null,
          billingEnabled: true,
        },
      ],
      workspaces: [
        {
          workspaceId: WS_ID,
          slug: `personal-${WS_ID}`,
          name: "Espace Canonique",
          ownerUserId: "alice@orcia.fr",
          ownerOrgUnitId: "0195f000-0000-7000-8000-000000000020",
          ownerOrgUnitName: "Équipe Produit",
          visibilityMode: "PRIVATE_USER",
          lifecyclePhase: "BUILD",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
      datasources: options.withActivity
        ? [
            {
              id: "ds-282",
              workspaceName: "Espace Canonique",
              alias: "Docs Architecture",
              scheme: "git",
              uri: "git://internal/docs-arch",
              executionIdentity: "passthrough",
              freshnessTtlDays: 7,
              tripartiteStatus: "ALIGNED",
            },
          ]
        : [],
    },
    { email: "alice@orcia.fr", displayName: "Alice Produit", roles: ["PLATFORM_ADMIN"] },
  );
  seedVitestConnectorsInitialData({
    datasources: options.withActivity
      ? [
          {
            id: "ds-282",
            workspace_id: WS_ID,
            alias: "Docs Architecture",
            scheme: "git",
            uri: "git://internal/docs-arch",
            connector_id: null,
            sync_identity_mode: "SERVICE_ACCOUNT",
            service_account_id: null,
            referent_user_id: null,
            source_nature: "SOURCE_CODE",
            sync_mode: "POLLING_24H",
            freshness_status: "SYNCED",
            created_at_iso: new Date().toISOString(),
          },
        ]
      : [],
  });
  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "test-jwt-token",
    displayName: "Alice Produit",
    email: "alice@orcia.fr",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "PLATFORM_ADMIN",
  });
}

async function mountRoute(initialEntry: string, locale: "fr" | "en") {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [initialEntry] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  return render(
    <I18nProvider initialLocale={locale}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </I18nProvider>,
  );
}

beforeEach(() => {
  resetVitestApiBackend();
  clearPlatformSetupStorage();
  clearSavedActiveScopeId();
});

afterEach(() => {
  cleanup();
});

describe("Story 28.2 — Canonical 5-Tab Workspace Container & Tab 1 Sobriety", () => {
  it("renders strictly one [role=tablist] with 5 canonical tabs, zero 3-tab duplicate, and hides 0/0/0 KPI cards on Tab 1 when total == 0", async () => {
    seedWorkspace({ withActivity: false });
    const view = await mountRoute("/workspaces", "fr");

    const fiveTabsSection = await screen.findByTestId("workspace-five-tabs-view");
    expect(fiveTabsSection.querySelectorAll('[role="tablist"]').length).toBe(1);
    expect(screen.getAllByRole("tablist").length).toBe(1);

    expect(screen.getByTestId("workspace-tab-OVERVIEW")).toBeDefined();
    expect(screen.getByTestId("workspace-tab-DOCUMENTS_SOURCES")).toBeDefined();
    expect(screen.getByTestId("workspace-tab-DELIVERABLES_ARTIFACTS")).toBeDefined(); // pragma: allowlist secret
    expect(screen.getByTestId("workspace-tab-GLOSSARY_RULES")).toBeDefined();
    expect(screen.getByTestId("workspace-tab-MEMBERS_TEAM")).toBeDefined();

    // Competing 3-tab panel is completely removed from the DOM
    expect(screen.queryByTestId("workspace-detail-tabs-panel")).toBeNull();
    expect(screen.queryByTestId("workspace-detail-tab-sources")).toBeNull();
    expect(screen.queryByTestId("workspace-detail-tab-glossary")).toBeNull();
    expect(screen.queryByTestId("workspace-detail-tab-members")).toBeNull();

    // Tab 1 sobriety: total == 0 hides KPI grid and displays 1-sentence empty-state hint
    expect(screen.getByTestId("workspace-overview-panel")).toBeDefined();
    expect(screen.queryByTestId("workspace-overview-kpi-grid")).toBeNull();
    expect(screen.getByTestId("workspace-overview-empty-hint").textContent).toContain(
      "Cet espace est prêt",
    );

    // Tab 2 mounts real WorkspaceSourcesRagTab inside workspace-sources-panel
    fireEvent.click(screen.getByTestId("workspace-tab-DOCUMENTS_SOURCES"));
    const sourcesPanel = await screen.findByTestId("workspace-sources-panel");
    expect(sourcesPanel.querySelector('[data-testid="workspace-sources-master-table-root"]')).not.toBeNull();

    // Tab 4 mounts real WorkspaceGlossaryAndOntologyTab inside workspace-glossary-rules-panel
    fireEvent.click(screen.getByTestId("workspace-tab-GLOSSARY_RULES"));
    const glossaryPanel = await screen.findByTestId("workspace-glossary-rules-panel");
    expect(glossaryPanel.querySelector('[data-testid="workspace-glossary-and-ontology-tab"]')).not.toBeNull();

    // Tab 5 mounts real members & instructions inside workspace-members-panel
    fireEvent.click(screen.getByTestId("workspace-tab-MEMBERS_TEAM"));
    const membersPanel = await screen.findByTestId("workspace-members-panel");
    expect(membersPanel.querySelector('[data-testid="workspace-detail-members-content"]')).not.toBeNull();
    expect(screen.getByTestId("workspace-instructions-textarea")).toBeDefined();

    view.unmount();
  });

  it("opens DOCUMENTS_SOURCES directly on /workspaces/$wsId/sources and shows KPI cards on Tab 1 when total >= 1 in both FR and EN", async () => {
    seedWorkspace({ withActivity: true });
    const sourcesRouteView = await mountRoute(`/workspaces/${WS_ID}/sources`, "fr");

    expect(await screen.findByTestId("workspace-sources-panel")).toBeDefined();
    expect(await screen.findByTestId("workspace-sources-master-table-root")).toBeDefined();
    expect(screen.queryByTestId("workspace-overview-panel")).toBeNull();

    // Switching back to OVERVIEW shows KPI cards when >= 1 source exists
    fireEvent.click(screen.getByTestId("workspace-tab-OVERVIEW"));
    expect(await screen.findByTestId("workspace-overview-kpi-grid")).toBeDefined();
    expect(screen.queryByTestId("workspace-overview-empty-hint")).toBeNull();
    sourcesRouteView.unmount();
    cleanup();

    // Bilingual English (en) verification for total == 0 sobriety
    seedWorkspace({ withActivity: false });
    await createOrciaApiClient({ baseUrl: "" }).updateUserPreferences({ locale: "en" });
    const enView = await mountRoute("/workspaces", "en");

    await screen.findByTestId("workspace-overview-panel");
    expect(screen.queryByTestId("workspace-overview-kpi-grid")).toBeNull();
    expect(screen.getByTestId("workspace-overview-empty-hint").textContent).toContain(
      "This workspace is ready",
    );
    expect(screen.getByTestId("workspace-tab-DOCUMENTS_SOURCES").textContent).toContain(
      "Documents & Sources",
    );
    enView.unmount();
  });
});
