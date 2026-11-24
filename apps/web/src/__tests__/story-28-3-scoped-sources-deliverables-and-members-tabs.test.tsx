// @vitest-environment jsdom
import { createOrciaApiClient } from "@orcia/api-client";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { clearSavedActiveScopeId } from "../components/useShellContainerState";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";
import { seedVitestConnectorsInitialData } from "./vitestConnectorsMockHandlers";

const WS_ALPHA_ID = "0195f000-0000-7000-8000-000000000283";
const WS_BETA_ID = "0195f000-0000-7000-8000-000000000284";
const TEAM_ID = "0195f000-0000-7000-8000-000000000030";

function seedWorkspacesFor283(options: { readonly withRuns?: boolean } = {}) {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: TEAM_ID,
          name: "Équipe Plateforme",
          slug: "equipe-plateforme",
          kind: "TEAM",
          level: "TEAM",
          parentId: null,
          billingEnabled: true,
          lead_user_id: "alice.lead@orcia.fr",
          lead_user_ids: ["alice.lead@orcia.fr"],
          member_user_ids: ["bob.dev@orcia.fr"],
        },
      ],
      workspaces: [
        {
          workspaceId: WS_ALPHA_ID,
          slug: "mon-labo-alpha",
          name: "Mon Labo Alpha",
          ownerUserId: "alice.lead@orcia.fr",
          ownerOrgUnitId: TEAM_ID,
          ownerOrgUnitName: "Équipe Plateforme",
          visibilityMode: "PRIVATE_USER",
          lifecyclePhase: "BUILD",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
        {
          workspaceId: WS_BETA_ID,
          slug: "espace-beta",
          name: "Espace Beta",
          ownerOrgUnitId: TEAM_ID,
          ownerOrgUnitName: "Équipe Plateforme",
          visibilityMode: "STANDARD",
          lifecyclePhase: "RUN",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
      runs: options.withRuns
        ? [
            {
              runId: "run-283-1",
              workspaceId: WS_ALPHA_ID,
              workspaceName: "Mon Labo Alpha",
              title: "Dossier Architecture Core",
              status: "COMPLETED",
              currentStepKey: "publish",
              executionMode: "COACHING",
              accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
              budgetConsumedUsd: 0.42,
              blackboardSummary: "Livrable validé",
            },
          ]
        : [],
    },
    { email: "alice.lead@orcia.fr", displayName: "Alice Lead", roles: ["PLATFORM_ADMIN"] },
  );
  seedVitestConnectorsInitialData({
    datasources: [
      {
        id: "ds-alpha-1",
        workspace_id: WS_ALPHA_ID,
        alias: "Confluence Alpha",
        scheme: "confluence",
        uri: "https://confluence.corp.internal/alpha",
        connector_id: null,
        sync_identity_mode: "SERVICE_ACCOUNT",
        service_account_id: null,
        referent_user_id: null,
        source_nature: "DOCUMENT_KB",
        sync_mode: "POLLING_24H",
        freshness_status: "SYNCED",
        created_at_iso: new Date().toISOString(),
      },
    ],
  });
  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "test-jwt-token",
    displayName: "Alice Lead",
    email: "alice.lead@orcia.fr",
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

describe("Story 28.3 — Scoped PG18 Tab 2 Sources, Tab 3 Deliverables & Tab 5 Members/Settings", () => {
  it("scopes datasources strictly by activeWorkspaceId, hides Tab 2 filter pills at 0 sources, and reveals them at >= 1 source", async () => {
    seedWorkspacesFor283({ withRuns: false });
    const view = await mountRoute("/workspaces", "fr");

    // Alpha has 1 scoped source -> Tab 1 KPI grid & Tab 2 badge "1"
    expect(await screen.findByTestId("workspace-overview-kpi-grid")).toBeDefined();
    expect(screen.getByTestId("workspace-tab-badge-DOCUMENTS_SOURCES").textContent).toBe("1");

    // Tab 2 on Alpha shows the 5 filter pills & Alpha's source
    fireEvent.click(screen.getByTestId("workspace-tab-DOCUMENTS_SOURCES"));
    await screen.findByTestId("workspace-sources-table");
    expect(screen.getByText("Confluence Alpha")).toBeDefined();
    expect(screen.getByTestId("sources-filter-pill-all")).toBeDefined();
    expect(screen.getByTestId("sources-filter-pill-document_kb")).toBeDefined();

    // Switch to Beta (0 sources) -> filter pills hidden, attach & reconcile buttons stay visible
    await act(async () => {
      fireEvent.change(screen.getByTestId("workspaces-active-switcher-select"), {
        target: { value: WS_BETA_ID },
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId("workspace-sources-empty-state")).toBeDefined();
      expect(screen.queryByTestId("sources-filter-pill-all")).toBeNull();
      expect(screen.queryByTestId("sources-filter-pill-source_code")).toBeNull();
    });
    expect(screen.getByTestId("open-attach-source-modal-btn")).toBeDefined();
    expect(screen.getByTestId("workspace-sources-reconcile-btn")).toBeDefined();
    expect(screen.getByTestId("workspace-tab-badge-DOCUMENTS_SOURCES").textContent).toBe("0");

    // Attach a source to Beta -> badge updates to 1 and 5 filter pills appear
    fireEvent.click(screen.getByTestId("open-attach-source-modal-btn"));
    await screen.findByTestId("workspace-source-attach-modal");
    fireEvent.change(screen.getByTestId("modal-source-alias-input"), {
      target: { value: "Repo Beta Core" },
    });
    fireEvent.change(screen.getByTestId("modal-source-uri-input"), {
      target: { value: "https://git.corp.internal/beta/core.git" },
    });
    fireEvent.click(screen.getByTestId("modal-source-save-btn"));

    await waitFor(() => {
      expect(screen.getAllByText("Repo Beta Core").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByTestId("sources-filter-pill-all")).toBeDefined();
      expect(screen.getByTestId("sources-filter-pill-source_code")).toBeDefined();
      expect(screen.getByTestId("workspace-tab-badge-DOCUMENTS_SOURCES").textContent).toBe("1");
    });

    view.unmount();
  }, 15_000);

  it("renders Tab 3 sanitized deliverables catalog & empty state, persists Tab 5 PG18 instructions/members/settings across F5, and works in EN", async () => {
    seedWorkspacesFor283({ withRuns: true });
    const first = await mountRoute("/workspaces", "fr");

    await screen.findByTestId("workspace-five-tabs-view");
    // Tab 3 on Alpha: displays scoped deliverable with sanitized orcia:// CAS URI (zero personal-<uuid>)
    fireEvent.click(screen.getByTestId("workspace-tab-DELIVERABLES_ARTIFACTS")); // pragma: allowlist secret
    const delivPanel = await screen.findByTestId("workspace-deliverables-panel");
    expect(delivPanel.textContent).toContain("Dossier Architecture Core");
    expect(delivPanel.textContent).toContain(
      "orcia://workspaces/mon-labo-alpha/artifacts/dossier-architecture-core@v1",
    );
    expect(delivPanel.textContent).not.toContain(`personal-${WS_ALPHA_ID}`);

    // Tab 5 on Alpha: team roster, PG18 persisted instructions, and lifecycle/sharing settings
    fireEvent.click(screen.getByTestId("workspace-tab-MEMBERS_TEAM"));
    await screen.findByTestId("workspace-members-panel");
    expect(screen.getByTestId("workspace-member-lead-alice.lead@orcia.fr")).toBeDefined();
    expect(screen.getByTestId("workspace-member-item-bob.dev@orcia.fr")).toBeDefined();

    const textarea = screen.getByTestId("workspace-instructions-textarea") as HTMLTextAreaElement;
    await waitFor(() => {
      expect(textarea.value).toContain("S'appuyer sur les documents");
    });

    fireEvent.change(textarea, {
      target: { value: "Respecter le modèle d'architecture Alpha et citer les ADR." },
    });
    fireEvent.click(screen.getByTestId("workspace-instructions-save-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("workspace-instructions-saved-badge").textContent).toContain(
        "Enregistré",
      );
    });

    fireEvent.change(screen.getByTestId(`workspace-settings-phase-select-${WS_ALPHA_ID}`), {
      target: { value: "MIGRATION" },
    });
    await waitFor(() => {
      expect(screen.getByTestId(`workspace-phase-badge-${WS_ALPHA_ID}`).textContent).toContain(
        "Évolution",
      );
    });

    fireEvent.click(screen.getByTestId(`workspace-settings-share-btn-${WS_ALPHA_ID}`));
    await waitFor(() => {
      expect(screen.getByTestId(`workspace-visibility-badge-${WS_ALPHA_ID}`).textContent).toContain(
        "Équipe",
      );
    });

    // F5 cold remount survival
    first.unmount();
    cleanup();

    const reloaded = await mountRoute("/workspaces", "fr");
    fireEvent.click(await screen.findByTestId("workspace-tab-MEMBERS_TEAM"));
    await waitFor(() => {
      expect(
        (screen.getByTestId("workspace-instructions-textarea") as HTMLTextAreaElement).value,
      ).toBe("Respecter le modèle d'architecture Alpha et citer les ADR.");
      expect(screen.getByTestId(`workspace-phase-badge-${WS_ALPHA_ID}`).textContent).toContain(
        "Évolution",
      );
      expect(screen.getByTestId(`workspace-visibility-badge-${WS_ALPHA_ID}`).textContent).toContain(
        "Équipe",
      );
    });
    reloaded.unmount();
    cleanup();

    // English (en) verification on empty Beta workspace
    seedWorkspacesFor283({ withRuns: false });
    await createOrciaApiClient({ baseUrl: "" }).updateUserPreferences({ locale: "en" });
    const enView = await mountRoute(`/workspaces/${WS_BETA_ID}/sources`, "en");
    await screen.findByTestId("workspace-sources-empty-state");
    expect(screen.queryByTestId("sources-filter-pill-all")).toBeNull();
    expect(screen.getByTestId("workspace-sources-empty-state").textContent).toContain(
      "No sources connected yet",
    );

    fireEvent.click(screen.getByTestId("workspace-tab-DELIVERABLES_ARTIFACTS")); // pragma: allowlist secret
    expect(await screen.findByTestId("workspace-deliverables-empty-state")).toBeDefined();
    expect(screen.getByTestId("workspace-deliverables-empty-state").textContent).toContain(
      "No deliverable edited directly yet",
    );

    fireEvent.click(screen.getByTestId("workspace-tab-MEMBERS_TEAM"));
    expect((await screen.findByTestId("workspace-instructions-save-btn")).textContent).toContain(
      "Save instructions",
    );
    enView.unmount();
  }, 15_000);
});
