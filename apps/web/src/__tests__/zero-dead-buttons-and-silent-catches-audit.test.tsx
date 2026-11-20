import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import path from "node:path";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import {
  scanMisplacedStorageErrorHelper,
  scanMisplacedStorageErrorHelperInSource,
  scanPhantomConstantsAndLabels,
  scanPhantomConstantsInSource,
  scanSilentCatchesAst,
  scanSilentCatchesInSource,
} from "./setup/astSilentCatchAndPhantomAudit";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const WEB_SRC_DIR = path.join(REPO_ROOT, "apps/web/src");
const UI_SRC_DIR = path.join(REPO_ROOT, "packages/ui/src");

function seedAuthenticatedAdminState() {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: "0192c4e0-0000-7000-8000-000000000201",
          name: "Direction Opérations",
          slug: "dir-operations",
          level: "BU",
          parentId: null,
          billingEnabled: true,
        },
        {
          id: "0192c4e0-0000-7000-8000-000000000202",
          name: "Équipe Plateforme",
          slug: "equipe-plateforme",
          level: "TEAM",
          parentId: "0192c4e0-0000-7000-8000-000000000201",
          billingEnabled: true,
        },
      ],
      workspaces: [
        {
          workspaceId: "ws-audit-router-1",
          name: "Espace Audit Routeur",
          visibilityMode: "STANDARD",
          ownerOrgUnitName: "Équipe Plateforme",
          lifecyclePhase: "BUILD",
          suggestedWorkflows: [],
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
    },
    {
      email: "admin.audit@orcia.fr",
      displayName: "Admin Audit",
      roles: ["PLATFORM_ADMIN"],
    },
  );
  useAuthSessionStore.getState().setAuthSession({
    isAuthenticated: true,
    email: "admin.audit@orcia.fr",
    displayName: "Admin Audit",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "PLATFORM_ADMIN",
  });
}

async function mountRouteWithRealRouter(initialPath: string) {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [initialPath] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  const rendered = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...rendered, router, queryClient };
}

beforeEach(() => {
  resetVitestApiBackend();
  clearPlatformSetupStorage();
});

afterEach(() => {
  cleanup();
});

describe("Anti-False-Positive Lock 4 — RouterProvider Real Mount Audit, AST Silent Catches, Phantom Constants & Error Alerts", () => {
  it("forbids bare/empty catch {}, silent .catch(() => null|undefined|{}|[]), and phantom /5 or profile constants across 100% of apps/web/src and packages/ui/src", () => {
    const catchViolations = scanSilentCatchesAst(REPO_ROOT, [WEB_SRC_DIR, UI_SRC_DIR]);
    expect(catchViolations).toEqual([]);

    const phantomViolations = scanPhantomConstantsAndLabels(REPO_ROOT, [WEB_SRC_DIR]);
    expect(phantomViolations).toEqual([]);

    const storageHelperViolations = scanMisplacedStorageErrorHelper(REPO_ROOT, [WEB_SRC_DIR, UI_SRC_DIR]);
    expect(storageHelperViolations).toEqual([]);
  }, 15_000);

  it("explicitly rejects synthetic bare/empty catches, silent .catch(() => null|undefined|{}|[]), and phantom constants", () => {
    const badCatches = `
      async function broken(p: Promise<unknown>) {
        try { await p; } catch {}
        try { await p; } catch (err) {}
        await p.catch(() => {});
        await p.catch(() => null);
        await p.catch(() => undefined);
        await p.catch(() => ({}));
        await p.catch(() => []);
        await p.catch(() => { return null; });
      }
    `;
    const catchHits = scanSilentCatchesInSource("synthetic/badCatches.ts", badCatches);
    expect(catchHits).toHaveLength(8);

    const safeCatch = `
      async function handled(p: Promise<unknown>, setErr: (m: string) => void) {
        try {
          await p;
        } catch (err) {
          setErr(err instanceof Error ? err.message : "Erreur");
        }
      }
    `;
    expect(scanSilentCatchesInSource("synthetic/safeCatch.ts", safeCatch)).toEqual([]);

    const badPhantoms = `
      const x = DEFAULT_HUMAN_PROFILE;
      const y = GENERAL_SECTIONS_LEGACY;
      const label = "Afficher les 5 étapes";
    `;
    const phantomHits = scanPhantomConstantsInSource("synthetic/badPhantoms.ts", badPhantoms);
    expect(phantomHits).toHaveLength(3);

    const misplacedApiCatch = `
      async function loadSetup(client: { getState: () => Promise<void> }) {
        try { await client.getState(); } catch (err) { ignoreBenignStorageError("hydration", err); }
      }
    `;
    const misplacedHits = scanMisplacedStorageErrorHelperInSource(
      "apps/web/src/components/platformSetupHydration.ts",
      misplacedApiCatch,
    );
    expect(misplacedHits.length).toBeGreaterThanOrEqual(2);
  });

  it("mounts all 10 key SPA routes under a real RouterProvider with single visible primary panels and active interactive actions", async () => {
    const routeExpectations: ReadonlyArray<{
      readonly path: string;
      readonly primaryTestId: string;
      readonly actionButtonTestId?: string;
      readonly postClickTestId?: string;
    }> = [
      { path: "/cockpit", primaryTestId: "cockpit-block-accostage" },
      {
        path: "/spaces",
        primaryTestId: "spaces-open-glossary-link",
        actionButtonTestId: "toggle-create-workspace-form-btn",
        postClickTestId: "create-workspace-modal",
      },
      { path: "/catalog", primaryTestId: "catalog-explorer-panel" },
      {
        path: "/agents",
        primaryTestId: "agents-subview-tab-connections",
        actionButtonTestId: "agents-subview-tab-connections",
        postClickTestId: "remote-service-test-bench",
      },
      {
        path: "/processes",
        primaryTestId: "processes-hub-v2-page",
        actionButtonTestId: "open-create-process-modal-btn",
        postClickTestId: "create-process-modal",
      },
      { path: "/gates", primaryTestId: "gates-dedicated-review-page" },
      { path: "/finops", primaryTestId: "finops-feature-panel" },
      { path: "/settings", primaryTestId: "settings-hub-page" },
      {
        path: "/help",
        primaryTestId: "help-menu-center-view",
        actionButtonTestId: "help-accordion-steps-btn",
        postClickTestId: "help-accordion-steps-content",
      },
      { path: "/wizards", primaryTestId: "wizards-route-page" },
    ];

    for (const routeCase of routeExpectations) {
      seedAuthenticatedAdminState();
      const view = await mountRouteWithRealRouter(routeCase.path);

      const matches = await screen.findAllByTestId(routeCase.primaryTestId);
      expect(matches, `Expected exactly 1 '${routeCase.primaryTestId}' on ${routeCase.path}`).toHaveLength(1);
      const primaryEl = matches[0]!;
      expect(primaryEl.style.display).not.toBe("none");
      expect(primaryEl.hidden).toBe(false);

      const enabledButtons = Array.from(view.container.querySelectorAll("button")).filter(
        (btn) => !btn.disabled,
      );
      expect(
        enabledButtons.length,
        `Expected interactive enabled buttons on ${routeCase.path}`,
      ).toBeGreaterThan(0);

      if (routeCase.actionButtonTestId && routeCase.postClickTestId) {
        const trigger = await screen.findByTestId(routeCase.actionButtonTestId);
        fireEvent.click(trigger);
        const target = await screen.findByTestId(routeCase.postClickTestId);
        expect(target).toBeDefined();
      }

      view.unmount();
      cleanup();
      resetVitestApiBackend();
      clearPlatformSetupStorage();
    }
  }, 20_000);

  it("exposes a visible [role='alert'] banner when an interactive user mutation receives HTTP >= 400", async () => {
    seedAuthenticatedAdminState();
    const view = await mountRouteWithRealRouter("/spaces");

    fireEvent.click(await screen.findByTestId("toggle-create-workspace-form-btn"));
    await screen.findByTestId("create-workspace-modal");

    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/v1/workspaces") && (init?.method ?? "GET").toUpperCase() === "POST") {
        return new Response(
          JSON.stringify({
            type: "https://orcia.io/problems/err-validation-failed",
            title: "Validation",
            status: 422,
            detail: "Nom d'espace déjà utilisé",
            error_code: "ERR_VALIDATION_FAILED",
          }),
          { status: 422, headers: { "Content-Type": "application/problem+json" } },
        );
      }
      return originalFetch(input, init);
    }) as typeof fetch;

    try {
      fireEvent.change(screen.getByTestId("workspace-name-input"), {
        target: { value: "Espace En Erreur" },
      });
      fireEvent.change(screen.getByTestId("workspace-slug-input"), {
        target: { value: "espace-erreur" },
      });
      fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));

      await waitFor(() => {
        const banner = screen.getByTestId("workspaces-action-feedback-banner");
        expect(banner.getAttribute("role")).toBe("alert");
        expect((banner.textContent ?? "").trim().length).toBeGreaterThan(0);
      });
      // Close modal so Radix aria-hidden releases the page and getByRole("alert") resolves directly
      fireEvent.click(screen.getByTestId("create-workspace-modal-close-btn"));
      expect(screen.getByRole("alert").textContent?.trim().length).toBeGreaterThan(0);
    } finally {
      globalThis.fetch = originalFetch;
      view.unmount();
    }
  });
});
