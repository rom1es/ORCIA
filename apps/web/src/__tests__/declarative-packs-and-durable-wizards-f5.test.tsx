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

describe("Declarative Packs Registry & Durable Onboarding Wizards F5 Persistence", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    seedVitestPlatformSetupState({});
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    cleanup();
  });

  it("loads declarative packs from API, exports workspace ZIP, and renders alert banner on HTTP errors", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings/packs"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    const { unmount } = render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("declarative-pack-card-sdlc")).toBeDefined();
      expect(screen.getByTestId("declarative-pack-card-orcia-docs")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("export-pack-sdlc-zip-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("packs-registry-status-banner")).toBeDefined();
      expect(screen.getByTestId("exported-pack-zip-filename").textContent).toContain(
        "sdlc-ws-mon-compte.zip",
      );
    });

    // Error >= 400 during ZIP export -> visible [role="alert"]
    useAuthSessionStore.setState({ readOnlyObserver: true, roles: ["OBSERVER"] });
    fireEvent.click(screen.getByTestId("export-pack-sdlc-zip-btn"));
    await waitFor(() => {
      const alert = screen.getByTestId("packs-registry-error-banner");
      expect(alert.getAttribute("role")).toBe("alert");
      expect(alert.textContent).toContain("ERR_OBSERVER_MODE_READ_ONLY");
    });
    unmount();

    // Error >= 400 on initial GET /api/v1/packs -> visible [role="alert"]
    useAuthSessionStore.setState({ readOnlyObserver: false, roles: ["PLATFORM_ADMIN"] });
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const urlStr = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      if (urlStr.includes("/api/v1/packs")) {
        return new Response(
          JSON.stringify({
            type: "https://orcia.io/problems/err-internal",
            title: "Erreur registre packs",
            status: 503,
            detail: "Service packs temporairement indisponible.",
            instance: "/api/v1/packs",
            trace_id: "0195f000000070008000000000000503",
            error_code: "ERR_PACKS_UNAVAILABLE",
          }),
          { status: 503, headers: { "Content-Type": "application/problem+json" } },
        );
      }
      return originalFetch(input, init);
    }) as typeof fetch;

    const queryClientErr = createOrciaQueryClient();
    const historyErr = createMemoryHistory({ initialEntries: ["/settings/packs"] });
    const routerErr = createOrciaRouter({ queryClient: queryClientErr, history: historyErr });
    await routerErr.load();

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClientErr}>
          <RouterProvider router={routerErr} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    await waitFor(() => {
      const alert = screen.getByTestId("packs-registry-error-banner");
      expect(alert.getAttribute("role")).toBe("alert");
      expect(alert.textContent).toContain("ERR_PACKS_UNAVAILABLE");
    });
  });

  it("persists wizard steps, preserves inputs on step-back, survives F5 unmount/render, and renders translated profile labels", async () => {
    const queryClient1 = createOrciaQueryClient();
    const history1 = createMemoryHistory({ initialEntries: ["/wizards"] });
    const router1 = createOrciaRouter({ queryClient: queryClient1, history: history1 });
    await router1.load();

    const firstRender = render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClient1}>
          <RouterProvider router={router1} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("wizard-step-form-1")).toBeDefined();
    });

    const initialRunnerText = screen.getByTestId("durable-wizard-runner").textContent ?? "";
    expect(initialRunnerText).toContain("Création d'un Espace de travail d'équipe");
    expect(initialRunnerText).toContain("Étape 1 sur 5");
    expect(initialRunnerText).not.toContain("sdlc_tech_lead");
    expect(initialRunnerText).not.toContain("1. #1/5 1.");

    // Step 1 -> Step 2
    fireEvent.change(screen.getByTestId("wizard-input-org-unit"), {
      target: { value: "Équipe Architecture" },
    });
    fireEvent.click(screen.getByTestId("wizard-complete-step-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("wizard-step-form-2")).toBeDefined();
    });

    // Step-back -> Step 1 preserves entered org unit name
    fireEvent.change(screen.getByTestId("wizard-input-workspace-name"), {
      target: { value: "Espace Architecture Durable" },
    });
    fireEvent.click(screen.getByTestId("wizard-step-back-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("wizard-step-form-1")).toBeDefined();
    });
    expect((screen.getByTestId("wizard-input-org-unit") as HTMLInputElement).value).toBe(
      "Équipe Architecture",
    );

    // Complete steps 1 -> 5
    fireEvent.click(screen.getByTestId("wizard-complete-step-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("wizard-step-form-2")).toBeDefined();
    });
    expect((screen.getByTestId("wizard-input-workspace-name") as HTMLInputElement).value).toBe(
      "Espace Architecture Durable",
    );
    fireEvent.click(screen.getByTestId("wizard-complete-step-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("wizard-step-form-3")).toBeDefined();
    });
    fireEvent.change(screen.getByTestId("wizard-input-connector-alias"), {
      target: { value: "depot-core" },
    });
    fireEvent.change(screen.getByTestId("wizard-input-connector-uri"), {
      target: { value: "https://git.internal.orcia/core.git" },
    });
    fireEvent.click(screen.getByTestId("wizard-complete-step-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("wizard-step-form-4")).toBeDefined();
    });
    fireEvent.change(screen.getByTestId("wizard-input-primary-model"), {
      target: { value: "qwen2.5:14b" },
    });
    fireEvent.click(screen.getByTestId("wizard-complete-step-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("wizard-step-form-5")).toBeDefined();
    });
    fireEvent.click(screen.getByTestId("wizard-complete-step-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("wizard-completed-badge")).toBeDefined();
      expect(screen.getByTestId("wizard-reciprocity-citation")).toBeDefined();
    });

    // Simulate full F5 page reload with fresh QueryClient and Router
    firstRender.unmount();

    const queryClient2 = createOrciaQueryClient();
    const history2 = createMemoryHistory({ initialEntries: ["/wizards"] });
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
      expect(screen.getByTestId("wizard-completed-badge")).toBeDefined();
      expect(screen.getByTestId("wizard-reciprocity-citation")).toBeDefined();
    });
    const reloadedText = screen.getByTestId("durable-wizard-runner").textContent ?? "";
    expect(reloadedText).toContain("Étape 5 sur 5");
    expect(reloadedText).not.toContain("sdlc_tech_lead");
  });

  it("displays an alert banner on /wizards when a backend mutation returns HTTP >= 400", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/wizards"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("wizard-step-form-1")).toBeDefined();
    });

    useAuthSessionStore.setState({ readOnlyObserver: true, roles: ["OBSERVER"] });
    fireEvent.click(screen.getByTestId("wizard-complete-step-btn"));

    await waitFor(() => {
      const alert = screen.getByTestId("wizards-error-banner");
      expect(alert.getAttribute("role")).toBe("alert");
      expect(alert.textContent).toContain("ERR_OBSERVER_MODE_READ_ONLY");
    });
  });
});
