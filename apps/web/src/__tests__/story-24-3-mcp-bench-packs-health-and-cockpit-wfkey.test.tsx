// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import { seedVitestPlatformSetupState } from "./vitest.setup";

const SEEDED_WS_ID = "0195f000-0000-7000-8000-000000000343";

function seedAdminWithWorkspace() {
  resetAuthSessionStore();
  seedVitestPlatformSetupState(
    {
      workspaces: [
        {
          workspaceId: SEEDED_WS_ID,
          slug: "ws-story-24-3",
          name: "Espace Story 24.3",
          ownerOrgUnitId: "0192c4e0-0000-7000-8000-000000000101",
          ownerOrgUnitName: "Direction Produit",
          visibilityMode: "STANDARD",
          lifecyclePhase: "BUILD",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
      workflows: [
        {
          workflowKey: "incident-triage",
          title: "Triage Incident Critique",
          version: "1.0.0",
          status: "PUBLISHED",
          prePrompt: "Analyser l'incident",
          prePromptSha256: "a".repeat(64),
          requiredParams: [],
          requiredMarkdownSections: [],
          triggers: [],
          layers: [],
        },
      ],
    },
    { email: "admin243@orcia.test", displayName: "Admin 24.3", roles: ["PLATFORM_ADMIN"] },
  );
  useAuthSessionStore.getState().setAuthSession({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "vitest-jwt-story-24-3",
    email: "admin243@orcia.test",
    displayName: "Admin 24.3",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "PLATFORM_ADMIN",
  });
}

describe("Story 24.3 (Couche 1b) — No Optimistic PASS, MCP Exposure F5, Packs Health & Cockpit wfKey", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    clearPlatformSetupStorage();
    seedAdminWithWorkspace();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    cleanup();
  });

  it("never shows optimistic PASS while test-and-discover is pending, shows PASS on HTTP 200, surfaces [role=alert] on 502/422, and persists MCP exposure across F5", async () => {
    let releaseBench!: () => void;
    const benchGate = new Promise<void>((resolve) => {
      releaseBench = resolve;
    });
    let persistedExposed = false;
    let persistedTools = ["assistant.ask", "agent.invoke", "agent.list_exposed"];
    let mockLocale: "fr" | "en" = "fr";
    let failBenchWith502 = false;
    let failMcpPutWith422 = false;

    const fetchSpy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const urlStr =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : input.url;
      const method = (init?.method ?? "GET").toUpperCase();

      if (urlStr.includes("/api/v1/users/me/preferences") && method === "GET" && mockLocale === "en") {
        return new Response(
          JSON.stringify({
            user_id: "u-vitest-user",
            theme: "light",
            locale: "en",
            default_hat: "ANALYST_PM_PO",
            default_assistant_hat: "ANALYST_PM_PO",
            assistant_tone: "balanced",
            personal_instructions: "",
            auto_open_contextual_help: true,
            notifications_enabled: true,
            assistant_behavior_redirect_uri: "/assistant?modal=settings",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      if (urlStr.includes("/api/v1/settings/connectors/test-and-discover") && method === "POST") {
        if (failBenchWith502) {
          return new Response(
            JSON.stringify({
              type: "https://orcia.ia/errors/upstream",
              title: "Upstream Unavailable",
              status: 502,
              detail: "Connecteur distant injoignable (502)",
              error_code: "ERR_CONNECTOR_UNREACHABLE",
            }),
            { status: 502, headers: { "Content-Type": "application/problem+json" } },
          );
        }
        await benchGate;
      }

      if (urlStr.includes("/api/v1/mcp/exposure") && method === "GET") {
        return new Response(
          JSON.stringify({
            workspace_slug: "ws-story-24-3",
            agents: persistedExposed
              ? [
                  {
                    agent_slug: "governed-mcp-connector",
                    workspace_slug: "ws-story-24-3",
                    display_name: "Connecteur MCP gouverné",
                    mcp_exposed: true,
                    regime: "GOVERNED_STAGED_COPILOT",
                    human_authored_required: false,
                    exposed_tools: persistedTools,
                  },
                ]
              : [],
            exposed_tools: persistedTools,
            any_exposed: persistedExposed,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      if (urlStr.includes("/api/v1/mcp/exposure") && method === "PUT") {
        if (failMcpPutWith422) {
          return new Response(
            JSON.stringify({
              type: "https://orcia.ia/errors/validation",
              title: "Validation Failed",
              status: 422,
              detail: "Persistence PG18 requise pour l'exposition MCP",
              error_code: "ERR_VALIDATION",
            }),
            { status: 422, headers: { "Content-Type": "application/problem+json" } },
          );
        }
        const parsed =
          typeof init?.body === "string"
            ? (JSON.parse(init.body) as Record<string, unknown>)
            : {};
        persistedExposed = Boolean(parsed.mcp_exposed);
        persistedTools = persistedExposed
          ? [
              "assistant.ask",
              "agent.invoke",
              "agent.list_exposed",
              `agent.${String(parsed.agent_slug ?? "governed-mcp-connector")}`,
            ]
          : ["assistant.ask", "agent.invoke", "agent.list_exposed"];
        return new Response(
          JSON.stringify({
            agent_slug: String(parsed.agent_slug ?? "governed-mcp-connector"),
            workspace_slug: String(parsed.workspace_slug ?? "ws-story-24-3"),
            display_name: String(parsed.display_name ?? "Connecteur MCP gouverné"),
            mcp_exposed: persistedExposed,
            regime: "GOVERNED_STAGED_COPILOT",
            human_authored_required: false,
            exposed_tools: persistedTools,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      return originalFetch(input, init);
    });
    globalThis.fetch = fetchSpy as typeof fetch;

    const qc1 = createOrciaQueryClient();
    const h1 = createMemoryHistory({ initialEntries: ["/agents"] });
    const r1 = createOrciaRouter({ queryClient: qc1, history: h1 });
    await r1.load();

    const firstMount = render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={qc1}>
          <RouterProvider router={r1} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    const connTab = await screen.findByTestId("agents-subview-tab-connections");
    fireEvent.click(connTab);
    expect(await screen.findByTestId("remote-service-test-bench")).toBeDefined();

    // Trigger test bench while HTTP promise is still pending
    const runBtn = screen.getByTestId("run-test-bench-btn") as HTMLButtonElement;
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(runBtn.disabled).toBe(true);
      expect(screen.getByTestId("test-bench-loading-banner")).toBeDefined();
    });
    // Proof: NEVER optimistic synchronous PASS while HTTP is pending
    expect(screen.queryByTestId("test-bench-status-1")).toBeNull();
    expect(screen.queryByText("Validé")).toBeNull();

    // Resolve HTTP 200
    releaseBench();

    await waitFor(() => {
      expect(screen.getByTestId("catalog-action-feedback-banner").textContent).toContain(
        "Banc de test vérifié",
      );
      expect(screen.getByTestId("test-bench-status-1").getAttribute("data-status")).toBe("PASS");
      expect(screen.getByTestId("test-bench-status-4").getAttribute("data-status")).toBe("PASS");
      expect(screen.getByText("Réseau, chiffrement et protection d'adresse", { exact: false })).toBeDefined();
    });

    // Toggle MCP exposure -> persists via PUT /api/v1/mcp/exposure
    const mcpToggle = screen.getByTestId("toggle-mcp-exposure-checkbox") as HTMLInputElement;
    expect(mcpToggle.checked).toBe(false);
    fireEvent.click(mcpToggle);

    await waitFor(() => {
      expect(mcpToggle.checked).toBe(true);
      expect(screen.getByTestId("exposed-mcp-tool-agent.governed-mcp-connector")).toBeDefined();
    });

    // Simulate F5 cold reload -> GET /api/v1/mcp/exposure restores checked state (EN locale verified too)
    firstMount.unmount();
    mockLocale = "en";

    const qc2 = createOrciaQueryClient();
    const h2 = createMemoryHistory({ initialEntries: ["/agents"] });
    const r2 = createOrciaRouter({ queryClient: qc2, history: h2 });
    await r2.load();

    render(
      <I18nProvider initialLocale="en">
        <QueryClientProvider client={qc2}>
          <RouterProvider router={r2} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    fireEvent.click(await screen.findByTestId("agents-subview-tab-connections"));
    await waitFor(() => {
      const reloadedToggle = screen.getByTestId("toggle-mcp-exposure-checkbox") as HTMLInputElement;
      expect(reloadedToggle.checked).toBe(true);
      expect(
        screen.getByText(/External Tool Connection Testing & Code Editor Access/),
      ).toBeDefined();
    });

    // Verify HTTP 502 on test-and-discover renders [role="alert"] and NO PASS
    failBenchWith502 = true;
    failMcpPutWith422 = true;

    fireEvent.click(screen.getByTestId("run-test-bench-btn"));
    await waitFor(() => {
      const alertBanner = screen.getByRole("alert");
      expect(alertBanner.textContent).toContain("502");
    });
    expect(screen.queryByTestId("test-bench-status-1")).toBeNull();

    // Verify HTTP 422 on PUT /api/v1/mcp/exposure surfaces [role="alert"] (no silent catch)
    fireEvent.click(screen.getByTestId("toggle-mcp-exposure-checkbox"));
    await waitFor(() => {
      const alertBanner = screen.getByRole("alert");
      expect(alertBanner.textContent).toContain("Persistence PG18 requise");
    });
  });

  it("renders PacksRegistryPage real healthchecks (healthy, degraded 1/2, and API 500 alert) + manual refresh", async () => {
    let healthMode: "healthy" | "degraded" | "error" = "healthy";

    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const urlStr =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : input.url;
      const method = (init?.method ?? "GET").toUpperCase();
      if (urlStr.includes("/api/v1/packs/health") && method === "GET") {
        if (healthMode === "error") {
          return new Response(
            JSON.stringify({
              type: "https://orcia.ia/errors/health",
              title: "Healthcheck Failed",
              status: 500,
              detail: "Service healthcheck indisponible",
              error_code: "ERR_PACKS_HEALTH",
            }),
            { status: 500, headers: { "Content-Type": "application/problem+json" } },
          );
        }
        if (healthMode === "degraded") {
          return new Response(
            JSON.stringify({
              connectors: [
                {
                  connector_type: "mcp:jira",
                  required_scopes: ["read", "write"],
                  used_for: "Synchronisation des tickets SAFe",
                  health: {
                    connector_type: "mcp:jira",
                    ok: false,
                    latency_ms: 0,
                    error_message: "Jira timeout",
                  },
                },
                {
                  connector_type: "mcp:git",
                  required_scopes: ["read"],
                  used_for: "Analyse des dépôts et PR",
                  health: {
                    connector_type: "mcp:git",
                    ok: true,
                    latency_ms: 9,
                    error_message: null,
                  },
                },
              ],
              healthy_count: 1,
              total_count: 2,
              all_healthy: false,
              checked_at_iso: "2026-11-20T12:00:00Z",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
      }
      return originalFetch(input, init);
    }) as typeof fetch;

    const qc = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings/packs"] });
    const router = createOrciaRouter({ queryClient: qc, history });
    await router.load();

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={qc}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    expect(await screen.findByTestId("packs-registry-v2-page")).toBeDefined();
    expect(await screen.findByTestId("declarative-pack-card-sdlc")).toBeDefined();
    expect(screen.getByText(/✓ Connecté \(12 ms\)/)).toBeDefined();

    // 1. Healthy manual refresh
    fireEvent.click(screen.getByTestId("refresh-pack-connectors-health-btn"));
    await waitFor(() => {
      const statusBanner = screen.getByTestId("packs-registry-status-banner");
      expect(statusBanner.getAttribute("role")).toBe("status");
      expect(statusBanner.textContent).toContain("2/2");
    });

    // 2. Degraded manual refresh -> [role="alert"] + Jira timeout shown on card
    healthMode = "degraded";
    fireEvent.click(screen.getByTestId("refresh-pack-connectors-health-btn"));
    await waitFor(() => {
      const errBanner = screen.getByTestId("packs-registry-error-banner");
      expect(errBanner.getAttribute("role")).toBe("alert");
      expect(errBanner.textContent).toContain("1/2");
      expect(screen.getByText("Jira timeout")).toBeDefined();
    });

    // 3. API 500 error -> [role="alert"]
    healthMode = "error";
    fireEvent.click(screen.getByTestId("refresh-pack-connectors-health-btn"));
    await waitFor(() => {
      const errBanner = screen.getByTestId("packs-registry-error-banner");
      expect(errBanner.getAttribute("role")).toBe("alert");
      expect(errBanner.textContent).toContain("Service healthcheck indisponible");
    });
  });

  it("allows per-pack bundle ZIP export via handleExportPackBundleZip even with 0 workspaces while guarding workspace export", async () => {
    clearPlatformSetupStorage();
    seedVitestPlatformSetupState(
      { workspaces: [] },
      { email: "admin243@orcia.test", displayName: "Admin 24.3", roles: ["PLATFORM_ADMIN"] },
    );
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      isHydrating: false,
      accessToken: "vitest-jwt-story-24-3",
      email: "admin243@orcia.test",
      displayName: "Admin 24.3",
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });

    const qc = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings/packs"] });
    const router = createOrciaRouter({ queryClient: qc, history });
    await router.load();

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={qc}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    expect(await screen.findByTestId("declarative-pack-card-sdlc")).toBeDefined();

    // Header workspace export still requires a workspace
    fireEvent.click(screen.getByTestId("export-workspace-pack-zip-btn"));
    await waitFor(() => {
      const errBanner = screen.getByTestId("packs-registry-error-banner");
      expect(errBanner.getAttribute("role")).toBe("alert");
    });

    // Per-pack card export succeeds on Day-0 with targetWorkspaceId="platform"
    fireEvent.click(screen.getByTestId("export-pack-sdlc-zip-btn"));
    await waitFor(() => {
      const statusBanner = screen.getByTestId("packs-registry-status-banner");
      expect(statusBanner.getAttribute("role")).toBe("status");
      expect(screen.getByTestId("exported-pack-zip-filename").textContent).toContain("sdlc-platform.zip");
    });
  });

  it("transmits real selected wfKey (and assistant-agent) from Cockpit instead of hardcoded claims-engineering-delivery", async () => {
    const capturedBodies: Array<Record<string, unknown>> = [];

    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const urlStr =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : input.url;
      const method = (init?.method ?? "GET").toUpperCase();
      if (urlStr.includes("/api/v1/orchestration/runs/instantiate") && method === "POST") {
        if (typeof init?.body === "string") {
          capturedBodies.push(JSON.parse(init.body) as Record<string, unknown>);
        }
      }
      return originalFetch(input, init);
    }) as typeof fetch;

    const qc = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/cockpit"] });
    const router = createOrciaRouter({ queryClient: qc, history });
    await router.load();

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={qc}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    const wfSelect = (await screen.findByTestId("cockpit-select-workflow")) as HTMLSelectElement;
    const titleInput = screen.getByTestId("cockpit-run-title-input") as HTMLInputElement;
    const submitBtn = screen.getByTestId("cockpit-launch-run-submit-btn");

    // 1. Custom workflow selected
    fireEvent.change(wfSelect, { target: { value: "incident-triage" } });
    fireEvent.change(titleInput, { target: { value: "Incident API Prod" } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(capturedBodies.length).toBeGreaterThanOrEqual(1);
    });
    expect(capturedBodies[0]?.workflow_uri).toBe("orcia://workflows/incident-triage");
    expect(capturedBodies[0]?.workflow_uri).not.toBe(
      "orcia://workflows/claims-engineering-delivery",
    );

    // 2. Built-in assistant-agent selected
    fireEvent.change(wfSelect, { target: { value: "assistant-agent" } });
    fireEvent.change(titleInput, { target: { value: "Analyse rapide" } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(capturedBodies.length).toBeGreaterThanOrEqual(2);
    });
    expect(capturedBodies[1]?.workflow_uri).toBe("orcia://system/workflows/assistant-agent");
  });
});
