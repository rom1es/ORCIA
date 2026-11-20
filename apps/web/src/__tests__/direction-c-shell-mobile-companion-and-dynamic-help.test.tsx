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

  it("enforces strictly 8 Direction C sidebar entries, stacked double scope selector, clickable breadcrumb, and no Cockpit active state on /profile, /help, /showcase", async () => {
    const { router } = await renderAppAtRoute("/cockpit");

    const sidebar = await screen.findByTestId("four-zone-sidebar");
    const menuItems = sidebar.querySelectorAll('[data-testid^="eight-menu-item-"]');
    expect(menuItems).toHaveLength(8);
    for (const expectedKey of [
      "cockpit",
      "assistant",
      "processes",
      "agents",
      "spaces",
      "finops",
      "configuration",
      "help",
    ]) {
      expect(screen.getByTestId(`eight-menu-item-${expectedKey}`)).toBeDefined();
    }
    expect(screen.queryByTestId("eight-menu-item-organization")).toBeNull();
    expect(screen.queryByTestId("eight-menu-item-activity")).toBeNull();
    expect(screen.queryByTestId("eight-menu-item-glossary")).toBeNull();

    // Stacked double scope selector (Équipe / Direction + Espace)
    expect(screen.getByTestId("sidebar-double-scope-selector")).toBeDefined();
    expect(screen.getByTestId("sidebar-team-bu-selector")).toBeDefined();
    expect(screen.getByTestId("sidebar-workspace-selector")).toBeDefined();

    // Clickable breadcrumb on /organization navigates back to /configuration
    await act(async () => {
      await router.navigate({ to: "/organization" });
    });
    const breadcrumbParent = await screen.findByTestId("topbar-breadcrumb-link-0");
    expect(breadcrumbParent.textContent).toContain("Configuration");
    fireEvent.click(breadcrumbParent);
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/configuration");
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

  it("checks/collapses Step 1 when adminCreated=true, keeps Step 2 unchecked with 0 org_units, renders Accostage X/5, and omits LOCK TABLE jargon", async () => {
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

    const step1Card = await screen.findByTestId("welcome-setup-step1-card");
    await waitFor(() => {
      expect(step1Card.getAttribute("data-completed")).toBe("true");
    });
    expect(screen.getByTestId("welcome-setup-step1-checked-icon")).toBeDefined();
    expect(screen.getByTestId("welcome-setup-admin-created-badge")).toBeDefined();

    const step2OrgMilestone = screen.getByTestId("accostage-milestone-step-iam");
    expect(step2OrgMilestone.getAttribute("data-completed")).toBe("false");

    const accostageBadge = screen.getByTestId("accostage-progress-pill");
    expect(accostageBadge.textContent).toMatch(/^Accostage \d+\/6$/);
    expect(screen.queryByTestId("onboarding-progress-badge")).toBeNull();

    const banner = screen.getByTestId("progressive-day0-accostage-banner");
    expect(banner.textContent).not.toContain("LOCK TABLE users IN EXCLUSIVE MODE");

    // Cockpit renders at most 3 major blocks
    expect(screen.getByTestId("cockpit-block-accostage")).toBeDefined();
    expect(screen.getByTestId("cockpit-block-decisions")).toBeDefined();
    expect(screen.getByTestId("cockpit-block-governance")).toBeDefined();
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

    // Click ⓘ trigger on /cockpit -> opens help column & activates target section
    await act(async () => {
      await router.navigate({ to: "/cockpit" });
    });
    fireEvent.click(screen.getByTestId("topbar-contextual-help-toggle"));
    expect(screen.queryByTestId("four-zone-contextual-help-column")).toBeNull();

    fireEvent.click(screen.getByTestId("contextual-info-trigger-cockpit-decisions"));
    expect(screen.getByTestId("four-zone-contextual-help-column")).toBeDefined();
    expect(
      screen.getByTestId("help-section-cockpit-decisions").getAttribute("data-active"),
    ).toBe("true");

    // Static hygiene guard on _contextualHelpSections.ts
    const sectionsSource = fs.readFileSync(
      path.resolve(__dirname, "../components/_contextualHelpSections.ts"),
      "utf8",
    );
    expect(sectionsSource).not.toContain("Chef1");
    expect(sectionsSource).not.toContain("aqwZSX");
  });
});
