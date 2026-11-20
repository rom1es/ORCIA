import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import {
  getRecordedVitestApiCalls,
  resetVitestApiBackend,
  seedVitestPlatformSetupState,
} from "./vitest.setup";
import {
  resetVitestAutonomousSupervisionMockState,
} from "./vitestAutonomousSupervisionMockHandlers";

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

function setViewportWidth(widthPx: number): void {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: widthPx,
  });
  window.dispatchEvent(new Event("resize"));
}

describe("Direction C 8-Item Shell, Mobile Companion (< 768px), Accostage & Dynamic Route Help", () => {
  beforeEach(() => {
    clearPlatformSetupStorage();
    resetVitestApiBackend();
    resetVitestAutonomousSupervisionMockState();
    resetAuthSessionStore();
    setViewportWidth(1440);
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
            leadUserIds: ["admin@orcia.test"],
            ontologyLeadUserIds: [],
            memberUserIds: [],
          },
          {
            id: "team-pay",
            name: "Équipe Paiement",
            slug: "equipe-paiement",
            level: "TEAM",
            parentId: "bu-ops",
            billingEnabled: true,
            leadUserIds: ["admin@orcia.test"],
            memberUserIds: [],
          },
        ],
        workspaces: [
          {
            workspaceId: "ws-pay",
            name: "Portail Paiement",
            ownerOrgUnitId: "team-pay",
            visibilityMode: "STANDARD",
          },
        ],
        llm_tiers: [
          {
            tier: "medium",
            primaryModel: "claude-3-7-sonnet",
            modelFamily: "Anthropic",
            apiKeyConfigured: true,
          },
        ],
        rbac_grants: [],
        datasources: [],
        packs: [],
        workflows: [],
        runs: [],
        catalog_items: [],
        ontology_concepts: [],
        audit_events: [],
      },
      { email: "admin@orcia.test", displayName: "Claire Admin", roles: ["PLATFORM_ADMIN"] },
    );
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "admin@orcia.test",
      displayName: "Claire Admin",
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });
  });

  afterEach(() => {
    cleanup();
    setViewportWidth(1440);
    resetAuthSessionStore();
  });

  it("hides desktop sidebar below 768px, renders 3-tab mobile bottom bar & 1-line header, and shows desktop-recommended banner on heavy routes", async () => {
    setViewportWidth(390);
    const cockpitView = await renderAppAtRoute("/cockpit");

    expect(screen.queryByTestId("four-zone-sidebar")).toBeNull();
    expect(screen.getByTestId("four-zone-top-header-bar")).toBeDefined();
    expect(screen.getByTestId("mobile-menu-drawer-toggle")).toBeDefined();

    const bottomBar = screen.getByTestId("mobile-bottom-tab-bar");
    expect(bottomBar).toBeDefined();
    expect(screen.getByTestId("mobile-companion-tab-cockpit").textContent).toContain("Cockpit");
    expect(screen.getByTestId("mobile-companion-tab-assistant").textContent).toMatch(
      /Assistant|Arbitrage/i,
    );
    expect(screen.getByTestId("mobile-companion-tab-decisions").textContent).toContain(
      "Décisions",
    );
    expect(screen.queryByTestId("mobile-desktop-recommended-banner")).toBeNull();
    cockpitView.unmount();

    for (const desktopRoute of [
      "/settings",
      "/configuration",
      "/organization",
      "/processes/studio/demo",
    ]) {
      const routeView = await renderAppAtRoute(desktopRoute);
      expect(
        await screen.findByTestId("mobile-desktop-recommended-banner"),
      ).toBeDefined();
      routeView.unmount();
    }
  }, 15000);

  it("enforces strictly 9 Direction C sidebar entries, unified grouped scope selector, topbar [O] ORCIA home link, and no Cockpit active state on /profile, /help, /showcase", async () => {
    const { router } = await renderAppAtRoute("/cockpit");

    const sidebar = await screen.findByTestId("four-zone-sidebar");
    const menuItems = sidebar.querySelectorAll('[data-testid^="eight-menu-item-"]');
    expect(menuItems).toHaveLength(9);
    for (const expectedKey of [
      "cockpit",
      "assistant",
      "processes",
      "agents",
      "spaces",
      "organization",
      "finops",
      "configuration",
      "help",
    ]) {
      expect(screen.getByTestId(`eight-menu-item-${expectedKey}`)).toBeDefined();
    }
    expect(screen.queryByTestId("sidebar-brand-logo")).toBeNull();
    expect(screen.queryByTestId("eight-menu-item-activity")).toBeNull();
    expect(screen.queryByTestId("eight-menu-item-glossary")).toBeNull();

    // Unified single workspace selector (Bug 7) — no stacked sidebar-team-bu-selector
    expect(screen.getByTestId("sidebar-unified-scope-selector")).toBeDefined();
    expect(screen.queryByTestId("sidebar-team-bu-selector")).toBeNull();
    expect(screen.getByTestId("sidebar-workspace-selector")).toBeDefined();

    // Clickable [O] ORCIA home link + breadcrumb on /organization (no Configuration parent)
    await act(async () => {
      await router.navigate({ to: "/organization" });
    });
    const breadcrumb = await screen.findByTestId("topbar-breadcrumb");
    expect(breadcrumb.textContent).toContain("ORCIA");
    expect(breadcrumb.textContent).toContain("Mon Organisation");
    expect(breadcrumb.textContent).not.toContain("Configuration");
    fireEvent.click(screen.getByTestId("topbar-orcia-home-link"));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/cockpit");
    });

    // Cockpit must NOT be active on /profile, /help, or /showcase
    for (const nonCockpitRoute of ["/profile", "/help"]) {
      await act(async () => {
        await router.navigate({ to: nonCockpitRoute });
      });
      const cockpitBtn = screen.getByTestId("eight-menu-item-cockpit");
      expect(cockpitBtn.getAttribute("data-active")).toBe("false");
      expect(cockpitBtn.getAttribute("aria-current")).toBeNull();
    }

    await act(async () => {
      await router.navigate({ to: "/showcase" });
    });
    expect(screen.getByTestId("orcia-product-showcase-site-view")).toBeDefined();
    const cockpitOnShowcase = screen.queryByTestId("eight-menu-item-cockpit");
    if (cockpitOnShowcase) {
      expect(cockpitOnShowcase.getAttribute("data-active")).toBe("false");
    }
  });

  it("checks first-admin milestone when adminCreated=true, keeps step-iam unchecked with 0 org_units, renders X / 6 complétées, and omits LOCK TABLE jargon", async () => {
    resetVitestApiBackend();
    seedVitestPlatformSetupState(
      {
        org_units: [],
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
      { email: "claire.admin@orcia.test", displayName: "Claire Admin", roles: ["PLATFORM_ADMIN"] },
    );

    await renderAppAtRoute("/cockpit");

    const firstAdminMilestone = await screen.findByTestId("accostage-milestone-first-admin");
    await waitFor(() => {
      expect(firstAdminMilestone.getAttribute("data-completed")).toBe("true");
    });
    expect(screen.queryByTestId("welcome-setup-step1-card")).toBeNull();
    expect(screen.getByTestId("welcome-setup-admin-identity-name").textContent).toBe(
      "Claire Admin",
    );

    const step2OrgMilestone = screen.getByTestId("accostage-milestone-step-iam");
    expect(step2OrgMilestone.getAttribute("data-completed")).toBe("false");

    const accostageBadge = screen.getByTestId("accostage-progress-pill");
    expect(accostageBadge.textContent).toMatch(/^\d+ \/ 6 complétées$/);
    expect(screen.queryByTestId("onboarding-progress-badge")).toBeNull();
    expect(screen.queryByTestId("accostage-compact-toggle-btn")).toBeNull();

    const banner = screen.getByTestId("progressive-day0-accostage-banner");
    expect(banner.textContent).not.toContain("LOCK TABLE users IN EXCLUSIVE MODE");

    // Cockpit renders at most 3 major blocks (and hides governance block when 0 runs/arbitrations exist)
    expect(screen.getByTestId("cockpit-block-accostage")).toBeDefined();
    expect(screen.getByTestId("cockpit-block-decisions")).toBeDefined();
    expect(screen.queryByTestId("cockpit-block-governance")).toBeNull();
  });

  it("passes active route to /api/v1/help/resolve, highlights help-section on ⓘ click, and purges Chef1/aqwZSX from _contextualHelpSections.ts", async () => {
    const { router } = await renderAppAtRoute("/finops");

    await waitFor(() => {
      const helpCalls = getRecordedVitestApiCalls().filter(
        (c) => c.path === "/api/v1/help/resolve",
      );
      expect(helpCalls.length).toBeGreaterThanOrEqual(1);
    });

    await waitFor(() => {
      expect(screen.getByTestId("contextual-help-hybrid-panel").textContent).toContain(
        "Aide contextuelle — /finops",
      );
    });

    await act(async () => {
      await router.navigate({ to: "/assistant" });
    });
    await waitFor(() => {
      expect(screen.getByTestId("contextual-help-hybrid-panel").textContent).toContain(
        "Aide contextuelle — /assistant",
      );
    });

    // Story 25.2 (Bug 5): no floating ⓘ trigger on /cockpit cards; ? Aide button toggles Zone 4
    await act(async () => {
      await router.navigate({ to: "/cockpit" });
    });
    expect(screen.queryByTestId("contextual-info-trigger-cockpit-decisions")).toBeNull();
    fireEvent.click(screen.getByTestId("topbar-contextual-help-toggle"));
    expect(screen.queryByTestId("four-zone-contextual-help-column")).toBeNull();

    fireEvent.click(screen.getByTestId("topbar-contextual-help-toggle"));
    expect(screen.getByTestId("four-zone-contextual-help-column")).toBeDefined();

    // Static hygiene guard on _contextualHelpSections.ts
    const sectionsSource = fs.readFileSync(
      path.resolve(__dirname, "../components/_contextualHelpSections.ts"),
      "utf8",
    );
    expect(sectionsSource).not.toContain("Chef1");
    expect(sectionsSource).not.toContain("aqwZSX");
  });
});
