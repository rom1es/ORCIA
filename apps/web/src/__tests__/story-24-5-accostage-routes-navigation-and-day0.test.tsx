import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { FirstBootAdminSetupModal } from "../components/FirstBootAdminSetupModal";
import {
  buildUnifiedAccostageMilestones,
  type AccostageProgressSummary,
} from "../components/platformSetupAccostage";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { buildShellBreadcrumbItems } from "../components/shellBreadcrumbBuilders";
import { resolveEightMenuKeyFromModule } from "../components/shellPresets";
import { buildShellDisabledMenuKeys } from "../components/shellScopeOptions";
import { enDictionary } from "../i18n/locales/en";
import { frDictionary } from "../i18n/locales/fr";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import {
  resetVitestApiBackend,
  seedVitestPlatformSetupState,
} from "./vitest.setup";

async function renderAppAtRoute(routePath: string) {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [routePath] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...view, router };
}

function collectDeclaredRouterPaths(): Set<string> {
  const router = createOrciaRouter({
    history: createMemoryHistory({ initialEntries: ["/cockpit"] }),
  });
  return new Set(Object.keys(router.routesByPath));
}

describe("Story 24.5 — Accostage Identity, Route Targets (USER24-BUG-2), Zone 4 /inbox & Day-0 Coherence", () => {
  beforeEach(() => {
    clearPlatformSetupStorage();
    resetAuthSessionStore();
    resetVitestApiBackend();
  });

  afterEach(() => {
    cleanup();
    clearPlatformSetupStorage();
    resetAuthSessionStore();
    resetVitestApiBackend();
  });

  it("USER24-BUG-2: validates all 6 Accostage milestones (pre-admin and post-admin) resolve to declared routes in router.tsx without /welcome-setup", () => {
    const declaredPaths = collectDeclaredRouterPaths();
    expect(declaredPaths.has("/profile")).toBe(true);
    expect(declaredPaths.has("/cockpit")).toBe(true);
    expect(declaredPaths.has("/configuration")).toBe(true);
    expect(declaredPaths.has("/organization")).toBe(true);
    expect(declaredPaths.has("/spaces")).toBe(true);
    expect(declaredPaths.has("/processes")).toBe(true);

    for (const adminCreated of [false, true]) {
      const summary: AccostageProgressSummary = {
        adminCreated,
        hasModels: false,
        hasOrgUnits: false,
        hasWorkspaces: false,
        hasSources: false,
        hasWorkflows: false,
        completedCount: adminCreated ? 1 : 0,
        totalCount: 6,
        isDay0Complete: false,
      };
      const milestones = buildUnifiedAccostageMilestones({
        isFr: true,
        summary,
        roles: ["PLATFORM_ADMIN"],
      });
      expect(milestones).toHaveLength(6);
      for (const milestone of milestones) {
        expect(milestone.targetRoute).not.toBe("/welcome-setup");
        expect(declaredPaths.has(milestone.targetRoute)).toBe(true);
      }
      expect(milestones[0]?.key).toBe("first-admin");
      expect(milestones[0]?.targetRoute).toBe(adminCreated ? "/profile" : "/cockpit");
    }
  });

  it("UX23-07: displays real platformAdmin on Cockpit for CONTRIBUTOR, BU_LEAD, and READ_ONLY_OBSERVER while hiding step2 and unauthorized admin milestones", async () => {
    const roleCases: Array<{
      readonly email: string;
      readonly displayName: string;
      readonly roles: string[];
      readonly readOnlyObserver: boolean;
      readonly expectedVisibleKeys: string[];
    }> = [
      {
        email: "claire.contrib@orcia.fr",
        displayName: "Claire Collaboratrice",
        roles: ["CONTRIBUTOR"],
        readOnlyObserver: false,
        expectedVisibleKeys: ["step-workspaces", "step-workflows"],
      },
      {
        email: "marc.bulead@orcia.fr",
        displayName: "Marc Directeur BU",
        roles: ["BU_LEAD"],
        readOnlyObserver: false,
        expectedVisibleKeys: ["step-iam", "step-workspaces", "step-workflows"],
      },
      {
        email: "olivier.obs@orcia.fr",
        displayName: "Olivier Observateur",
        roles: ["READ_ONLY_OBSERVER"],
        readOnlyObserver: true,
        expectedVisibleKeys: [],
      },
    ];

    for (const tc of roleCases) {
      resetVitestApiBackend();
      clearPlatformSetupStorage();
      seedVitestPlatformSetupState(
        {
          first_admin_initialized: true,
          first_admin_display_name: "Alice Administratrice",
          first_admin_email: "alice.admin@orcia.fr",
        },
        {
          email: "alice.admin@orcia.fr",
          displayName: "Alice Administratrice",
          roles: ["PLATFORM_ADMIN", "SECOPS"],
        },
      );
      useAuthSessionStore.getState().setAuthSession({
        isAuthenticated: true,
        isHydrating: false,
        email: tc.email,
        displayName: tc.displayName,
        roles: tc.roles,
        activeHat: tc.roles[0],
        readOnlyObserver: tc.readOnlyObserver,
      });

      const { unmount } = await renderAppAtRoute("/cockpit");

      await waitFor(() => {
        expect(screen.getByTestId("progressive-day0-accostage-banner")).toBeDefined();
        expect(screen.getByTestId("welcome-setup-admin-identity-name").textContent).toBe(
          "Alice Administratrice",
        );
      });

      expect(screen.getByTestId("welcome-setup-admin-identity-name").textContent).not.toContain(
        tc.displayName,
      );
      expect(screen.queryByTestId("welcome-setup-step2-card")).toBeNull();
      expect(screen.queryByTestId("accostage-milestone-first-admin")).toBeNull();
      expect(screen.queryByTestId("accostage-milestone-step-llm")).toBeNull();
      expect(screen.queryByTestId("accostage-milestone-step-connectors")).toBeNull();

      for (const expectedKey of tc.expectedVisibleKeys) {
        expect(screen.getByTestId(`accostage-milestone-${expectedKey}`)).toBeDefined();
      }
      if (!tc.expectedVisibleKeys.includes("step-iam")) {
        expect(screen.queryByTestId("accostage-milestone-step-iam")).toBeNull();
      }
      if (tc.readOnlyObserver) {
        expect(screen.queryByTestId("welcome-setup-step3-card")).toBeNull();
      }

      unmount();
    }
  });

  it("UX23-09 / ARCH24-09: verifies /showcase highlights help, /organization hides Configuration for non-admins, [Espace] injects on scoped routes, Zone 4 /inbox is dedicated, and /settings tabs stay nowrap", async () => {
    expect(resolveEightMenuKeyFromModule("ontology", "/showcase")).toBe("help");
    expect(
      resolveEightMenuKeyFromModule("admin", "/organization", {
        canAccessConfiguration: false,
      }),
    ).toBeNull();

    const orgBreadcrumbWithoutConfig = buildShellBreadcrumbItems({
      pathname: "/organization",
      isFr: true,
      menuEntries: frDictionary.fourZoneShell.menuEntries,
      canAccessConfiguration: false,
    });
    expect(orgBreadcrumbWithoutConfig.map((b) => b.label)).toEqual([
      "ORCIA",
      "Mon Organisation",
    ]);

    const scopedInboxBreadcrumb = buildShellBreadcrumbItems({
      pathname: "/inbox",
      isFr: true,
      menuEntries: frDictionary.fourZoneShell.menuEntries,
      activeTeamLabel: "Équipe Paiement",
      activeWorkspaceLabel: "Espace Paiement Core",
    });
    expect(scopedInboxBreadcrumb.map((b) => b.label)).toEqual([
      "ORCIA",
      "Équipe Paiement",
      "Espace Paiement Core",
      "Boîte de Réception",
    ]);

    const enShowcaseBreadcrumb = buildShellBreadcrumbItems({
      pathname: "/showcase",
      isFr: false,
      menuEntries: enDictionary.fourZoneShell.menuEntries,
    });
    expect(enShowcaseBreadcrumb.map((b) => b.label)).toEqual([
      "ORCIA",
      enDictionary.fourZoneShell.menuEntries.help,
      "ORCIA Showcase",
    ]);

    // Render /showcase -> eight-menu-item-help is active
    seedVitestPlatformSetupState(
      {},
      { email: "admin@orcia.fr", displayName: "Alice Admin", roles: ["PLATFORM_ADMIN", "SECOPS"] },
    );
    const showcaseView = await renderAppAtRoute("/showcase");
    await waitFor(() => {
      expect(screen.getByTestId("eight-menu-item-help").getAttribute("data-active")).toBe("true");
    });
    showcaseView.unmount();

    // Render /inbox -> dedicated Zone 4 inbox help (not assistant)
    const inboxView = await renderAppAtRoute("/inbox");
    await waitFor(() => {
      const helpCol = screen.getByTestId("four-zone-contextual-help-column");
      expect(helpCol).toBeDefined();
      expect(helpCol.textContent).toContain("Boîte de Réception");
      expect(screen.getByTestId("help-section-inbox-claims")).toBeDefined();
      expect(screen.getByTestId("help-section-inbox-vs-activity")).toBeDefined();
    });
    expect(screen.queryByTestId("help-section-assistant-modes")).toBeNull();
    expect(screen.queryByTestId("help-section-assistant-folders")).toBeNull();
    inboxView.unmount();

    // Render /settings -> 6 tabs (5 settings tabs + Mon Organisation link) with flexWrap: "nowrap"
    const settingsView = await renderAppAtRoute("/settings");
    await waitFor(() => {
      const tabsNav = screen.getByTestId("settings-domain-tabs");
      expect(tabsNav.style.flexWrap).toBe("nowrap");
      expect(tabsNav.querySelectorAll("button").length).toBe(6);
    });
    settingsView.unmount();
  });

  it("UX23-15: locks Mes Espaces on Day 0 before first admin creation and enforces non-closable FirstBootAdminSetupModal with mandatory badge", async () => {
    const disabledDay0 = buildShellDisabledMenuKeys({
      isFr: true,
      adminCreated: false,
      llmTiers: [],
      workspaces: [],
    });
    expect(disabledDay0.spaces).toBeTruthy();
    expect(disabledDay0.configuration).toBeTruthy();

    // Render Day-0 /cockpit (no admin yet) -> Mes Espaces is disabled & modal has no close button + mandatory badge
    const day0View = await renderAppAtRoute("/cockpit");
    await waitFor(() => {
      expect(screen.getByTestId("first-boot-admin-setup-modal")).toBeDefined();
      expect(screen.getByTestId("first-boot-admin-mandatory-badge").textContent).toContain(
        "Étape obligatoire · Non ignorable",
      );
    });
    expect(screen.queryByTestId("first-boot-admin-setup-modal-close-btn")).toBeNull();
    const spacesNavBtn = screen.getByTestId("eight-menu-item-spaces") as HTMLButtonElement;
    expect(spacesNavBtn.disabled).toBe(true);
    expect(spacesNavBtn.getAttribute("data-active")).toBe("false");
    day0View.unmount();

    // Standalone modal check
    render(
      <FirstBootAdminSetupModal
        isOpen={true}
        isFr={false}
        onClose={() => {}}
        onCreatePlatformAdmin={() => {}}
      />,
    );
    expect(screen.queryByTestId("first-boot-admin-setup-modal-close-btn")).toBeNull();
    expect(screen.getByTestId("first-boot-admin-mandatory-badge").textContent).toContain(
      "Required step · Cannot be skipped",
    );
  });
});
