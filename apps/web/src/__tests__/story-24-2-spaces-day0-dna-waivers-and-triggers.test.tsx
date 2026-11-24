// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { seedVitestPlatformSetupState } from "./vitest.setup";

const SEEDED_WORKSPACE_ID = "0195f000-0000-7000-8000-000000000342";

function seedWorkspaceState() {
  seedVitestPlatformSetupState(
    {
      workspaces: [
        {
          workspaceId: SEEDED_WORKSPACE_ID,
          slug: "ws-story-24-2",
          name: "Espace Story 24.2",
          ownerOrgUnitId: "0192c4e0-0000-7000-8000-000000000101",
          ownerOrgUnitName: "Direction Produit",
          visibilityMode: "STANDARD",
          lifecyclePhase: "BUILD",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
    },
    { email: "admin@orcia.test", displayName: "Admin 24.2", roles: ["PLATFORM_ADMIN"] },
  );
}

describe("Story 24.2 (Couche 1b) — /spaces Day-0, 5 Tabs (USER24-BUG-6), DNA/Waivers await+F5 & Trigger 409", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    seedVitestPlatformSetupState(
      {},
      { email: "admin@orcia.test", displayName: "Admin 24.2", roles: ["PLATFORM_ADMIN"] },
    );
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    cleanup();
  });

  it("does NOT mount WorkspaceDnaAndWaiversSection, WorkspaceFiveTabs, or default-ws on /spaces when 0 workspace exists", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/spaces"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    const { container } = render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    expect(await screen.findByTestId("workspaces-cards-empty-state")).toBeDefined();
    expect(screen.queryByTestId("workspace-dna-and-waivers-section")).toBeNull();
    expect(screen.queryByTestId("workspace-five-tabs-view")).toBeNull();
    expect(screen.queryByTestId("dna-starlark-glossary-view")).toBeNull();
    const bodyText = container.textContent ?? "";
    expect(bodyText).not.toContain("default-ws");
    expect(bodyText).not.toContain("ws-claims-alpha");
    expect(bodyText).not.toContain("ws-mon-compte");
  });

  it("switches all 5 tabs (MEMBERS_TEAM shows workspace-members-panel), awaits waivers & Starlark compilation/activation with submitting state, survives F5, and surfaces errors in [role=alert]", async () => {
    seedWorkspaceState();

    const queryClient1 = createOrciaQueryClient();
    const history1 = createMemoryHistory({ initialEntries: ["/spaces"] });
    const router1 = createOrciaRouter({ queryClient: queryClient1, history: history1 });
    await router1.load();

    const firstRender = render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClient1}>
          <RouterProvider router={router1} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    // 1. Wait for WorkspaceDnaAndWaiversSection & verify real 5-tab switching (USER24-BUG-6)
    expect(await screen.findByTestId("workspace-dna-and-waivers-section")).toBeDefined();
    expect(screen.getByTestId("workspace-overview-panel")).toBeDefined();
    expect(screen.queryByTestId("dna-starlark-glossary-view")).toBeNull();

    fireEvent.click(screen.getByTestId("workspace-tab-MEMBERS_TEAM"));
    const membersPanel = await screen.findByTestId("workspace-members-panel");
    expect(membersPanel.textContent).toContain("Direction Produit");
    expect(screen.queryByTestId("workspace-sources-panel")).toBeNull();
    expect(screen.queryByTestId("dna-starlark-glossary-view")).toBeNull();

    fireEvent.click(screen.getByTestId("workspace-tab-DELIVERABLES_ARTIFACTS")); // pragma: allowlist secret
    expect(await screen.findByTestId("workspace-deliverables-panel")).toBeDefined();
    expect(screen.queryByTestId("dna-starlark-glossary-view")).toBeNull();

    fireEvent.click(screen.getByTestId("workspace-tab-DOCUMENTS_SOURCES"));
    expect(await screen.findByTestId("workspace-sources-panel")).toBeDefined();
    expect(screen.queryByTestId("dna-starlark-glossary-view")).toBeNull();

    fireEvent.click(screen.getByTestId("workspace-tab-OVERVIEW"));
    expect(await screen.findByTestId("workspace-overview-panel")).toBeDefined();

    // 2. Wrap fetch briefly to observe `submitting` (disabled + aria-busy) during waiver POST
    let releaseWaiver!: () => void;
    const waiverGate = new Promise<void>((resolve) => {
      releaseWaiver = resolve;
    });
    const fetchSpy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const urlStr = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      if (urlStr.includes("/exception-waivers") && (init?.method ?? "GET").toUpperCase() === "POST") {
        await waiverGate;
      }
      return originalFetch(input, init);
    });
    globalThis.fetch = fetchSpy as typeof fetch;

    const registerBtn = screen.getByTestId("register-waiver-btn-workspace-default") as HTMLButtonElement;
    fireEvent.click(registerBtn);
    await waitFor(() => {
      expect(registerBtn.disabled).toBe(true);
      expect(registerBtn.getAttribute("aria-busy")).toBe("true");
    });
    releaseWaiver();

    await waitFor(() => {
      expect(registerBtn.disabled).toBe(false);
      expect(screen.getAllByTestId(/^waiver-item-/).length).toBe(1);
    });
    globalThis.fetch = originalFetch;

    // 3. Switch to Tab 4 (GLOSSARY_RULES) to compile & activate Starlark mechanism
    fireEvent.click(screen.getByTestId("workspace-tab-GLOSSARY_RULES"));
    expect(await screen.findByTestId("dna-starlark-glossary-view")).toBeDefined();
    fireEvent.click(screen.getByTestId("compile-starlark-btn"));
    expect(await screen.findByTestId("starlark-compiler-panel")).toBeDefined();

    fireEvent.click(screen.getByTestId("sign-activate-starlark-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("workspaces-action-feedback-banner").textContent).toContain(
        "signé et activé",
      );
    });

    // 4. Simulate F5 reload -> waivers on Tab 1 & Starlark mechanism inside Tab 4 rehydrate from backend
    firstRender.unmount();

    const queryClient2 = createOrciaQueryClient();
    const history2 = createMemoryHistory({ initialEntries: ["/spaces"] });
    const router2 = createOrciaRouter({ queryClient: queryClient2, history: history2 });
    await router2.load();

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClient2}>
          <RouterProvider router={router2} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getAllByTestId(/^waiver-item-/).length).toBe(1);
      expect(screen.queryByTestId("dna-starlark-glossary-view")).toBeNull();
    });

    fireEvent.click(screen.getByTestId("workspace-tab-GLOSSARY_RULES"));
    await waitFor(() => {
      expect(screen.getByTestId("starlark-compiler-panel")).toBeDefined();
    });

    // 5. Error >= 400 (Observer read-only) on Starlark compile -> visible [role="alert"] banner
    useAuthSessionStore.setState({ readOnlyObserver: true, roles: ["OBSERVER"] });
    fireEvent.click(screen.getByTestId("compile-starlark-btn"));
    await waitFor(() => {
      const alertBanner = screen.getByTestId("workspaces-action-feedback-banner");
      expect(alertBanner.getAttribute("role")).toBe("alert");
      expect(alertBanner.textContent).toContain("⚠️");
    });
  });

  it("surfaces 409 ERR_TRIGGER_DUPLICATE_KEY in [role=alert] when WorkflowTriggersModal submits a duplicate trigger_key", async () => {
    seedWorkspaceState();

    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({
      initialEntries: ["/processes/studio/wf-01-qualification-prd"],
    });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    // Sign active autonomy contract
    fireEvent.click(await screen.findByTestId("studio-autonomy-contract-btn"));
    await waitFor(() => {
      const spSelect = screen.getByTestId("autonomy-contract-sp-select") as HTMLSelectElement;
      expect(spSelect.options.length).toBeGreaterThan(0);
    });
    fireEvent.click(screen.getByTestId("autonomy-contract-sign-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("studio-autonomy-contract-active-badge")).toBeDefined();
    });

    // Open triggers modal and create trigger with explicit key
    fireEvent.click(screen.getByTestId("studio-triggers-btn"));
    await screen.findByTestId("workflow-triggers-modal");

    fireEvent.change(screen.getByTestId("trigger-create-type-select"), {
      target: { value: "LOG_SINK_ALERT" },
    });
    fireEvent.change(screen.getByTestId("trigger-create-key-input"), {
      target: { value: "alert-dup-key" },
    });
    fireEvent.click(screen.getByTestId("trigger-create-submit-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("workflow-triggers-list").textContent).toContain("alert-dup-key");
    });

    // Attempt second creation with the same trigger_key -> 409 ERR_TRIGGER_DUPLICATE_KEY in [role="alert"]
    fireEvent.change(screen.getByTestId("trigger-create-key-input"), {
      target: { value: "alert-dup-key" },
    });
    fireEvent.click(screen.getByTestId("trigger-create-submit-btn"));

    await waitFor(() => {
      const errBanner = screen.getByTestId("workflow-triggers-error-banner");
      expect(errBanner.getAttribute("role")).toBe("alert");
      expect(errBanner.textContent).toContain("Identifiant de déclencheur déjà utilisé");
    });
  });
});
