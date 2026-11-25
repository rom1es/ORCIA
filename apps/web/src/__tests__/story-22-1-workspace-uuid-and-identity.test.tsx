import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { ShellContainer } from "../components/ShellContainer";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { CockpitFeaturePanel } from "../features/cockpit";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { getRecordedVitestApiCalls, resetVitestApiBackend } from "./vitest.setup";

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

beforeEach(() => {
  resetVitestApiBackend();
  clearPlatformSetupStorage();
});

afterEach(() => {
  cleanup();
});

describe("Story 22.1 — UUIDv7 Workspace Creation, F5 Survival & Identity Wiring", () => {
  it("awaits POST /api/v1/workspaces, stores server UUIDv7 & exact slug (never ws-1), and survives unmount/render F5", async () => {
    const queryClient1 = createOrciaQueryClient();
    const history1 = createMemoryHistory({ initialEntries: ["/settings"] });
    const router1 = createOrciaRouter({ queryClient: queryClient1, history: history1 });
    await router1.load();

    const firstRender = render(
      <QueryClientProvider client={queryClient1}>
        <RouterProvider router={router1} />
      </QueryClientProvider>,
    );

    // Day-0 admin setup
    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), {
      target: { value: "Admin E2E" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), {
      target: { value: "admin@orcia.fr" },
    });
    fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));

    await router1.navigate({ to: "/spaces" });
    fireEvent.click(await screen.findByTestId("toggle-create-workspace-form-btn"));
    await screen.findByTestId("create-workspace-form");

    fireEvent.change(screen.getByTestId("workspace-name-input"), {
      target: { value: "Espace E2E Comptabilité" },
    });
    fireEvent.change(screen.getByTestId("workspace-slug-input"), {
      target: { value: "espace-e2e-compta" },
    });
    fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe(
        "Espace E2E Comptabilité",
      );
    });

    const switcher = screen.getByTestId("workspaces-active-switcher-select") as HTMLSelectElement;
    expect(switcher.options.length).toBe(1);
    const createdWsId = switcher.value;
    expect(createdWsId).not.toBe("ws-1");
    expect(createdWsId).toMatch(UUID_REGEX);
    expect(screen.getByTestId("workspaces-action-feedback-banner").textContent).toContain(
      "espace-e2e-compta",
    );

    const postCall = getRecordedVitestApiCalls().find(
      (c) => c.method === "POST" && c.path === "/api/v1/workspaces",
    );
    expect(postCall).toBeDefined();
    expect((postCall!.body as Record<string, unknown>).slug).toBe("espace-e2e-compta");

    // F5 cycle: unmount + fresh render
    firstRender.unmount();

    const queryClient2 = createOrciaQueryClient();
    const history2 = createMemoryHistory({ initialEntries: ["/spaces"] });
    const router2 = createOrciaRouter({ queryClient: queryClient2, history: history2 });
    await router2.load();

    render(
      <QueryClientProvider client={queryClient2}>
        <RouterProvider router={router2} />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe(
        "Espace E2E Comptabilité",
      );
      expect(screen.getByTestId(`workspace-visibility-badge-${createdWsId}`)).toBeDefined();
    });
  });

  it("displays an actionable error banner without silent .catch when POST /api/v1/workspaces fails", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/spaces"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    fireEvent.click(await screen.findByTestId("toggle-create-workspace-form-btn"));
    await screen.findByTestId("create-workspace-form");

    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/v1/workspaces") && (init?.method ?? "GET").toUpperCase() === "POST") {
        return new Response(
          JSON.stringify({
            type: "https://orcia.io/problems/err-observer-mode-read-only",
            title: "Mode observateur en lecture seule",
            status: 403,
            detail: "Création refusée pour test d'erreur explicite.",
            error_code: "ERR_OBSERVER_MODE_READ_ONLY",
          }),
          { status: 403, headers: { "Content-Type": "application/problem+json" } },
        );
      }
      return originalFetch(input, init);
    }) as typeof fetch;

    try {
      fireEvent.change(screen.getByTestId("workspace-name-input"), {
        target: { value: "Espace Bloqué" },
      });
      fireEvent.change(screen.getByTestId("workspace-slug-input"), {
        target: { value: "espace-bloque" },
      });
      fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));

      const feedback = await screen.findByTestId("workspaces-action-feedback-banner");
      expect(feedback.getAttribute("role")).toBe("alert");
      expect(feedback.className).toContain("orcia-ds-alert-error");
      expect(feedback.querySelector(".orcia-ds-alert-icon")).not.toBeNull();
      expect(feedback.textContent).not.toContain("⚠️");
      expect(feedback.textContent?.trim().length).toBeGreaterThan(0);
      expect(screen.queryByTestId("workspace-visibility-badge-ws-1")).toBeNull();
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("never sends hardcoded 'marc' identity from Cockpit and uses authenticated session user", async () => {
    useAuthSessionStore.setState({
      isAuthenticated: true,
      isHydrating: false,
      accessToken: "test-jwt-token",
      displayName: "Sophie Directrice",
      email: "sophie@orcia.fr",
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <CockpitFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(
        getRecordedVitestApiCalls().some(
          (c) => c.path.startsWith("/api/v1/orchestration/state"),
        ),
      ).toBe(true);
    });

    const allCalls = getRecordedVitestApiCalls();
    expect(allCalls.some((c) => c.path.includes("persona_key=marc"))).toBe(false);

    const cockpitGovSrc = readFileSync(
      join(__dirname, "..", "features", "cockpit", "CockpitHumanLedGovernanceSection.tsx"),
      "utf8",
    );
    const cockpitIndexSrc = readFileSync(
      join(__dirname, "..", "features", "cockpit", "index.tsx"),
      "utf8",
    );
    expect(cockpitGovSrc).not.toContain('"marc"');
    expect(cockpitIndexSrc).not.toContain('"marc"');
  });
});
