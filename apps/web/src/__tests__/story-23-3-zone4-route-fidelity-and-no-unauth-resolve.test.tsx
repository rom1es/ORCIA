import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as helpSectionsModule from "../components/_contextualHelpSections";
import * as helpSectionsEnModule from "../components/_contextualHelpSectionsEn";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import {
  resetAuthSessionStore,
  simulateUnauthenticatedBrowser,
  useAuthSessionStore,
} from "../stores/authSessionStore";
import {
  getRecordedVitestApiCalls,
  resetVitestApiBackend,
  seedVitestPlatformSetupState,
  setVitestMockRefreshFails,
  vitestFetchTransport,
} from "./vitest.setup";
import { resetVitestAutonomousSupervisionMockState } from "./vitestAutonomousSupervisionMockHandlers";

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

function seedSession(roles: readonly string[]) {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: "bu-ops",
          name: "Direction Opérations",
          slug: "direction-operations",
          level: "BU",
          parentId: "scope-global",
          billingEnabled: true,
          leadUserIds: ["user@orcia.test"],
          ontologyLeadUserIds: [],
          memberUserIds: [],
        },
      ],
      workspaces: [],
      llm_tiers: [],
      rbac_grants: [],
      datasources: [],
      packs: [],
      workflows: [],
      runs: [],
      catalog_items: [],
      ontology_concepts: [],
      audit_events: [],
    },
    { email: "user@orcia.test", displayName: "Utilisateur Test", roles: [...roles] },
  );
  useAuthSessionStore.getState().setAuthSession({
    isAuthenticated: true,
    email: "user@orcia.test",
    displayName: "Utilisateur Test",
    roles: [...roles],
    activeHat: roles[0] ?? "MEMBER",
  });
}

describe("Story 23.3 — Zone 4 Route Fidelity, No Unauthenticated Resolve & Role Gating", () => {
  beforeEach(() => {
    clearPlatformSetupStorage();
    resetVitestApiBackend();
    resetVitestAutonomousSupervisionMockState();
    resetAuthSessionStore();
    globalThis.fetch = vitestFetchTransport as typeof fetch;
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    resetAuthSessionStore();
  });

  it("removes GENERAL_SECTIONS_FR/EN exports and keeps /assistant strictly distinct from /cockpit", async () => {
    expect("GENERAL_SECTIONS_FR" in helpSectionsModule).toBe(false);
    expect("GENERAL_SECTIONS_EN" in helpSectionsModule).toBe(false);
    expect("GENERAL_SECTIONS_EN" in helpSectionsEnModule).toBe(false);

    seedSession(["PLATFORM_ADMIN"]);
    const { router } = await renderAppAtRoute("/assistant");

    const panel = await screen.findByTestId("contextual-help-hybrid-panel");
    await waitFor(() => {
      expect(panel.textContent).toContain("Mon Assistant");
      expect(screen.getByTestId("contextual-help-real-example-box").textContent).toContain("Marc");
      expect(screen.getByTestId("contextual-help-common-pitfalls-box").textContent).toContain(
        "Zone de saisie verrouillée",
      );
    });

    const assistantText = panel.textContent ?? "";
    expect(assistantText).not.toContain("Le Cockpit regroupe");
    expect(assistantText).not.toContain("Réponse rapide");
    expect(assistantText).not.toContain("Avec un agent");
    expect(assistantText).not.toContain("Analyse approfondie");

    await act(async () => {
      await router.navigate({ to: "/cockpit" });
    });
    await waitFor(() => {
      const cockpitText = screen.getByTestId("contextual-help-hybrid-panel").textContent ?? "";
      expect(cockpitText).toContain("/cockpit");
      expect(cockpitText).toContain("Le Cockpit regroupe");
      expect(cockpitText).not.toBe(assistantText);
    });
  });

  it("hides @version and Sources du guide for non-admin users, and collapses them in <details> for PLATFORM_ADMIN", async () => {
    seedSession(["MEMBER"]);
    const memberView = await renderAppAtRoute("/assistant");

    await screen.findByTestId("contextual-help-what-for-box");
    await waitFor(() => {
      expect(
        getRecordedVitestApiCalls().some((c) => c.path === "/api/v1/help/resolve"),
      ).toBe(true);
    });
    expect(screen.queryByTestId("contextual-help-technical-details")).toBeNull();
    expect(screen.queryByTestId("contextual-help-version-pill")).toBeNull();
    expect(screen.queryByTestId("contextual-help-merged-layers")).toBeNull();
    memberView.unmount();

    resetVitestApiBackend();
    resetAuthSessionStore();
    seedSession(["PLATFORM_ADMIN"]);
    await renderAppAtRoute("/assistant");

    const details = (await screen.findByTestId(
      "contextual-help-technical-details",
    )) as HTMLDetailsElement;
    expect(details.tagName).toBe("DETAILS");
    expect(details.open).toBe(false);
    expect(screen.getByTestId("contextual-help-version-pill").textContent).toContain("@");
    expect(screen.getByTestId("contextual-help-merged-layers").textContent).toContain("BASE");
  });

  it("never calls /api/v1/help/resolve when unauthenticated (Day-0 or /login) and logs cleanly without silent catch on error", async () => {
    // Case A: Day-0 before first admin creation (unauthenticated) -> 0 /api/v1/help/resolve calls
    simulateUnauthenticatedBrowser();
    setVitestMockRefreshFails(true);
    const day0View = await renderAppAtRoute("/");
    await waitFor(() => {
      expect(screen.getByTestId("first-boot-admin-setup-modal")).toBeDefined();
    });
    expect(
      getRecordedVitestApiCalls().filter((c) => c.path === "/api/v1/help/resolve"),
    ).toHaveLength(0);
    day0View.unmount();

    // Case B: Admin exists, incognito /login -> BiModeLoginView, no Zone 4, 0 /api/v1/help/resolve calls
    resetVitestApiBackend();
    seedVitestPlatformSetupState({}, { email: "admin@orcia.test", displayName: "Admin Test" });
    simulateUnauthenticatedBrowser();
    const unauthView = await renderAppAtRoute("/login");
    await waitFor(() => {
      expect(screen.getByTestId("bi-mode-login-view")).toBeDefined();
      expect(screen.queryByTestId("four-zone-contextual-help-column")).toBeNull();
    });
    const unauthHelpCalls = getRecordedVitestApiCalls().filter(
      (c) => c.path === "/api/v1/help/resolve",
    );
    expect(unauthHelpCalls).toHaveLength(0);
    unauthView.unmount();
    setVitestMockRefreshFails(false);

    seedSession(["PLATFORM_ADMIN"]);
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const baseFetch = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/v1/help/resolve")) {
        return new Response(
          JSON.stringify({ detail: "Help temporarily unavailable", error_code: "ERR_INTERNAL" }),
          { status: 500, headers: { "Content-Type": "application/problem+json" } },
        );
      }
      return baseFetch(input, init);
    }) as typeof fetch;

    await renderAppAtRoute("/assistant");
    await waitFor(() => {
      expect(warnSpy).toHaveBeenCalledWith(
        "[contextual-help] fallback to local route guide:",
        "/assistant",
        expect.anything(),
      );
    });
    // Local route-specific fallback still renders all 4 DESIGN.md blocks for /assistant
    expect(screen.getByTestId("contextual-help-what-for-box").textContent).toContain(
      "Mon Assistant",
    );
    expect(screen.getByTestId("contextual-help-real-example-box")).toBeDefined();
    expect(screen.getByTestId("contextual-help-common-pitfalls-box")).toBeDefined();
  });

  it("exposes contextual-info-trigger-workspace-sources on /spaces even with 0 workspaces and opens Zone 4", async () => {
    seedSession(["PLATFORM_ADMIN"]);
    await renderAppAtRoute("/spaces");

    const trigger = await screen.findByTestId("contextual-info-trigger-workspace-sources");
    expect(trigger).toBeDefined();
    fireEvent.click(trigger);

    await waitFor(() => {
      const col = screen.getByTestId("four-zone-contextual-help-column");
      expect(col).toBeDefined();
      expect(screen.getByTestId("contextual-help-hybrid-panel").textContent).toMatch(
        /unité d'organisation/i,
      );
    });
  });
});
