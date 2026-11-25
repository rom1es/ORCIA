// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { clearSavedActiveScopeId } from "../components/useShellContainerState";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { seedVitestPlatformSetupState } from "./vitest.setup";

const BU_ID = "0195f000-0000-7000-8000-00000000b001";
const TEAM_ID = "0195f000-0000-7000-8000-00000000b002";
const WS_ID = "0195f000-0000-7000-8000-00000000b003";

function seedAdminAndWorkspace() {
  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "mock-token",
    email: "admin@orcia.test",
    displayName: "Admin User",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "ARCHITECT",
    readOnlyObserver: false,
    mustChangePassword: false,
  });
  seedVitestPlatformSetupState({
    org_units: [
      { id: BU_ID, name: "Product Division", slug: "bu-prod", level: "BU", parent_id: null },
      { id: TEAM_ID, name: "Core Team", slug: "team-core", level: "TEAM", parent_id: BU_ID },
    ],
    rbac_grants: [],
    llm_tiers: [
      {
        id: "llm-1",
        provider: "openai",
        model_id: "gpt-4o-mini",
        tier: "standard",
        enabled: true,
      },
    ],
    workspaces: [
      {
        workspaceId: WS_ID,
        name: "Core Workspace",
        visibilityMode: "STANDARD",
        ownerOrgUnitId: TEAM_ID,
        ownerOrgUnitName: "Core Team",
        lifecyclePhase: "RUN",
        suggestedWorkflows: [],
        accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
        finopsCostUsd: 0,
      },
    ],
    datasources: [
      {
        id: "ds-1",
        uri: "https://mcp.internal.example/v1",
        alias: "MCP Gateway",
        kind: "mcp_server",
        workspaceId: WS_ID,
      },
    ],
    packs: [],
    workflows: [],
    runs: [],
    catalog_items: [],
    ontology_concepts: [],
  });
}

async function mountRoute(path: string, locale: "fr" | "en") {
  seedAdminAndWorkspace();
  const origFetch = globalThis.fetch;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = typeof input === "string" ? input : (input as Request).url;
    if (url.includes("/api/v1/users/me/preferences") && (!init?.method || init.method === "GET")) {
      return new Response(
        JSON.stringify({
          theme: "light",
          locale,
          default_assistant_hat: "ARCHITECT",
          auto_open_contextual_help: false,
          notifications_enabled: true,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    return origFetch(input, init);
  });
  const qc = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [path] });
  const router = createOrciaRouter({ queryClient: qc, history });
  await router.load();
  return render(
    <I18nProvider initialLocale={locale}>
      <QueryClientProvider client={qc}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </I18nProvider>,
  );
}

describe("Story 29.5 — Header & Layout Convergence Across Assistant, Processes, Agents & FinOps", () => {
  afterEach(() => {
    cleanup();
    clearSavedActiveScopeId();
    vi.restoreAllMocks();
  });

  it("converges Mon Assistant (/assistant) onto OrciaPageHeader, OrciaTabStrip, and OrciaDataCard in FR & EN", async () => {
    await mountRoute("/assistant", "fr");
    const header = await screen.findByTestId("assistant-page-header");
    expect(header.tagName.toLowerCase()).toBe("header");
    expect(header.className).toContain("orcia-ds-page-header");
    expect(screen.getByTestId("assistant-page-header-title").tagName.toLowerCase()).toBe("h1");
    expect(screen.getByTestId("assistant-header-tabs").className).toContain("orcia-ds-tab-strip");
    expect(screen.getByTestId("assistant-new-conversation-btn").className).toContain("orcia-ds-btn-primary");
    expect(screen.getByTestId("assistant-open-governance-btn").className).toContain("orcia-ds-btn-secondary");
    expect(screen.getByTestId("assistant-saved-conversations-toggle-btn")).toBeDefined();
    expect(screen.getByTestId("assistant-folders-toggle-btn")).toBeDefined();
    expect(screen.getByTestId("assistant-stream-card").className).toContain("orcia-ds-data-card");

    cleanup();
    vi.restoreAllMocks();
    await mountRoute("/assistant", "en");
    await waitFor(() => {
      expect(screen.getByTestId("assistant-page-header-title").textContent).toBe("My Assistant");
    });
    expect(screen.getByTestId("assistant-active-discussion-tab").textContent).toContain("Active discussion");
  });

  it("converges Mes Processus (/processes) with 1 Cobalt header CTA, outline card launches, filter pills & zero account leakage", async () => {
    await mountRoute("/processes", "fr");
    const header = await screen.findByTestId("processes-page-header");
    expect(header.className).toContain("orcia-ds-page-header");
    expect(screen.getByTestId("processes-page-header-title").tagName.toLowerCase()).toBe("h1");

    const hub = screen.getByTestId("processes-hub-v2-page");
    const solidPrimaryBtns = hub.querySelectorAll(".orcia-ds-btn-primary");
    expect(solidPrimaryBtns.length).toBe(1);
    expect(screen.getByTestId("open-create-process-modal-btn").className).toContain("orcia-ds-btn-primary");
    expect(screen.getByTestId("workflows-hub-filter-all").className).toContain("orcia-ds-filter-pill");
    expect(screen.getByTestId("processes-catalog-card").className).toContain("orcia-ds-data-card");

    const activeDossiers = screen.getByTestId("processes-active-dossiers-card");
    expect(activeDossiers.className).toContain("orcia-ds-data-card");
    expect(activeDossiers.textContent ?? "").not.toContain("Mon Compte");
    expect(screen.getByTestId("resume-featured-dossier-btn").className).toContain(
      "orcia-ds-btn-cobalt-outline",
    );

    const launchBtn = hub.querySelector("[data-testid^='execute-workflow-btn-']");
    expect(launchBtn?.className).toContain("orcia-ds-btn-cobalt-outline");

    cleanup();
    vi.restoreAllMocks();
    await mountRoute("/processes", "en");
    await waitFor(() => {
      expect(screen.getByTestId("processes-page-header-title").textContent).toBe("My Processes");
    });
    expect(screen.getByTestId("processes-active-dossiers-card").textContent ?? "").not.toContain("Mon Compte");
  });

  it("converges Mes Agents (/agents) without mega-card, hides KPIs/filters on Tab 3, separates MCP/IDE cards & removes raw RPC jargon", async () => {
    await mountRoute("/agents", "fr");
    const manager = await screen.findByTestId("agents-and-skills-manager-view");
    expect(manager.className).toContain("orcia-ds-page");
    expect(manager.className).not.toContain("p-4");

    const header = screen.getByTestId("agents-page-header");
    expect(header.className).toContain("orcia-ds-page-header");
    expect(screen.getByTestId("agents-page-header-title").textContent).toBe("Mes Agents & Compétences");
    expect(screen.getByTestId("agents-tab-strip").className).toContain("orcia-ds-tab-strip");
    expect(screen.getByTestId("agents-subview-tab-agents").textContent).not.toMatch(/🤖/);
    expect(screen.getByTestId("agents-subview-tab-skills").textContent).not.toMatch(/🛠️/);
    expect(screen.getByTestId("agents-subview-tab-connections").textContent).not.toMatch(/🔌/);
    expect(screen.getByTestId("agents-kpi-and-filters-card")).toBeDefined();
    expect(screen.getByTestId("visibility-filter-all").className).toContain("orcia-ds-filter-pill");
    expect(screen.getByTestId("pinned-assistant-open-btn").className).toContain("orcia-ds-btn-cobalt-outline");

    fireEvent.click(screen.getByTestId("agents-subview-tab-connections"));
    await waitFor(() => {
      expect(screen.queryByTestId("agents-kpi-and-filters-card")).toBeNull();
      expect(screen.queryByTestId("agents-kpi-strip")).toBeNull();
      expect(screen.queryByTestId("agents-skills-search-input")).toBeNull();
    });

    const outboundCard = screen.getByTestId("outbound-mcp-server-card");
    const inboundCard = screen.getByTestId("governed-mcp-exposure-panel");
    expect(outboundCard.className).toContain("orcia-ds-data-card");
    expect(inboundCard.className).toContain("orcia-ds-data-card");
    expect(outboundCard.contains(inboundCard)).toBe(false);
    expect(inboundCard.textContent ?? "").not.toContain("assistant.ask");
    expect(inboundCard.textContent ?? "").not.toContain("agent.invoke");
    expect(inboundCard.textContent ?? "").not.toContain("agent.list_exposed");

    cleanup();
    vi.restoreAllMocks();
    await mountRoute("/agents", "en");
    await waitFor(() => {
      expect(screen.getByTestId("agents-page-header-title").textContent).toBe("My Agents & Skills");
    });
  });

  it("converges FinOps (/finops) onto OrciaPageHeader, OrciaTabStrip, distinct scope pills & OrciaDataCard framing in FR & EN", async () => {
    await mountRoute("/finops", "fr");
    const header = await screen.findByTestId("finops-page");
    expect(header.className).toContain("orcia-ds-page-header");
    expect(screen.getByTestId("finops-page-title").tagName.toLowerCase()).toBe("h1");
    expect(screen.getByTestId("finops-configure-budget-btn").className).toContain("orcia-ds-btn-primary");
    expect(screen.getByTestId("finops-open-activity-link").className).toContain("orcia-ds-nowrap");
    expect(screen.getByTestId("finops-tab-strip").className).toContain("orcia-ds-tab-strip");
    expect(screen.getByTestId("finops-scope-workspace").className).toContain("orcia-ds-filter-pill");
    expect(screen.getByTestId("finops-processes-card").className).toContain("orcia-ds-data-card");

    fireEvent.click(screen.getByTestId("finops-tab-tiers"));
    expect(screen.getByTestId("finops-tiers-card").className).toContain("orcia-ds-data-card");

    cleanup();
    vi.restoreAllMocks();
    await mountRoute("/finops", "en");
    await waitFor(() => {
      expect(screen.getByTestId("finops-page-title").textContent).toBe("FinOps and Economic Governance");
    });
    expect(screen.getByTestId("finops-scope-global")).toBeDefined();
  });
});
