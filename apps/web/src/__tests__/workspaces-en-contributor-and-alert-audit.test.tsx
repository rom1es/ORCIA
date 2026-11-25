// @vitest-environment jsdom
import { createOrciaApiClient } from "@orcia/api-client";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { clearSavedActiveScopeId } from "../components/useShellContainerState";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";
import { seedVitestConnectorsInitialData } from "./vitestConnectorsMockHandlers";

const PERSONAL_WS_ID = "0195f000-0000-7000-8000-000000000401";
const PERSONAL_WS_SLUG = `personal-${PERSONAL_WS_ID}`;
const TEAM_ID = "0195f000-0000-7000-8000-000000000040";

function seedContributorAuditWorkspace() {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: TEAM_ID,
          name: "Équipe Audit UX",
          slug: "equipe-audit-ux",
          kind: "TEAM",
          level: "TEAM",
          parentId: null,
          billingEnabled: true,
        },
      ],
      workspaces: [
        {
          workspaceId: PERSONAL_WS_ID,
          slug: PERSONAL_WS_SLUG,
          name: "Mon Espace Sobre",
          ownerUserId: "nadia@orcia.fr",
          ownerOrgUnitId: TEAM_ID,
          ownerOrgUnitName: "Équipe Audit UX",
          visibilityMode: "PRIVATE_USER",
          lifecyclePhase: "BUILD",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
    },
    { email: "nadia@orcia.fr", displayName: "Nadia Onto", roles: ["PLATFORM_ADMIN"] },
  );
  seedVitestConnectorsInitialData({ datasources: [] });
}

async function mountWorkspaces(locale: "fr" | "en") {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: ["/workspaces"] });
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

describe("Workspaces EN Localization, Contributor Non-Escalation & Single Alert Audit", () => {
  it("localizes compiled rule mechanism badge & explanation in English (en) and enforces contributor non-escalation + single error alert on Tab 2", async () => {
    seedContributorAuditWorkspace();
    await createOrciaApiClient({ baseUrl: "" }).updateUserPreferences({ locale: "en" });

    const enView = await mountWorkspaces("en");
    await screen.findByTestId("workspace-five-tabs-view");

    // Compile rule mechanism in English -> localized badge & explanation without French leakage
    fireEvent.click(screen.getByTestId("workspace-tab-GLOSSARY_RULES"));
    await screen.findByTestId("dna-starlark-glossary-view");
    fireEvent.click(screen.getByTestId("compile-starlark-btn"));
    await screen.findByTestId("starlark-compiler-panel");

    expect(screen.getByTestId("starlark-verified-badge").textContent).toContain(
      "Automatically verified",
    );
    expect(screen.getByTestId("starlark-compiler-panel").textContent).toContain(
      "Automatically checks compliance",
    );
    expect(screen.getByTestId("dna-causal-breadcrumb").textContent).toContain("Directive ➔ Rule");
    expect(screen.getByTestId("dna-starlark-glossary-view").textContent).not.toContain("Vérifié");
    enView.unmount();
    cleanup();

    // Non-lead contributor does NOT get escalated to lead on Tab 2, and load failure surfaces strictly 1 [role="alert"]
    seedContributorAuditWorkspace();
    seedVitestConnectorsInitialData({
      datasources: [
        {
          id: "ds-contrib-1",
          workspace_id: PERSONAL_WS_ID,
          alias: "Contrib Repo",
          scheme: "git",
          uri: "https://git.internal.orcia/contrib/repo.git",
          connector_id: null,
          sync_identity_mode: "SERVICE_ACCOUNT",
          service_account_id: null,
          referent_user_id: null,
          source_nature: "SOURCE_CODE",
          sync_mode: "POLLING_24H",
          freshness_status: "SYNCED",
          codegraph_enabled: false,
          created_at_iso: new Date().toISOString(),
        },
      ],
    });
    useAuthSessionStore.setState({
      isAuthenticated: true,
      isHydrating: false,
      accessToken: "test-jwt-token",
      displayName: "Contrib User",
      email: "contrib@orcia.fr",
      roles: ["CONTRIBUTOR"],
      activeHat: "CONTRIBUTOR",
      readOnlyObserver: false,
    });

    const contribView = await mountWorkspaces("fr");
    fireEvent.click(await screen.findByTestId("workspace-tab-DOCUMENTS_SOURCES"));
    const gitnexusSwitch = (await screen.findByTestId(
      "gitnexus-toggle-ds-contrib-1",
    )) as HTMLButtonElement;
    expect(gitnexusSwitch.disabled).toBe(true);
    contribView.unmount();
    cleanup();

    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes(`/api/v1/workspaces/${PERSONAL_WS_ID}/datasources`)) {
        return new Response(
          JSON.stringify({
            type: "https://orcia.io/problems/err-forbidden",
            title: "Forbidden",
            status: 403,
            detail: "Access denied to workspace datasources",
            error_code: "ERR_SCOPE_ACCESS_DENIED",
          }),
          { status: 403, headers: { "Content-Type": "application/problem+json" } },
        );
      }
      return originalFetch(input, init);
    }) as typeof fetch;

    try {
      const errView = await mountWorkspaces("fr");
      fireEvent.click(await screen.findByTestId("workspace-tab-DOCUMENTS_SOURCES"));
      const alertBox = await screen.findByTestId("workspaces-action-feedback-banner");
      expect(alertBox.getAttribute("role")).toBe("alert");
      expect((alertBox.textContent ?? "").trim().length).toBeGreaterThan(0);
      expect(screen.queryByTestId("sources-error-alert")).toBeNull();
      expect(screen.getAllByRole("alert")).toHaveLength(1);
      errView.unmount();
    } finally {
      globalThis.fetch = originalFetch;
    }
  }, 15_000);
});
