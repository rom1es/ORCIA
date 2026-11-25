// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { ORCIA_ACTIVE_SCOPE_STORAGE_KEY } from "../components/useShellContainerState";
import { InviteOrganizationUserModal } from "../features/admin/organization/InviteOrganizationUserModal";
import { frDictionary } from "../i18n/locales/fr";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

function ensureWorkingLocalStorage(): void {
  if (typeof window !== "undefined" && typeof window.localStorage?.getItem === "function") {
    return;
  }
  const backing = new Map<string, string>();
  const memoryStorage: Storage = {
    get length() {
      return backing.size;
    },
    clear() {
      backing.clear();
    },
    getItem(key: string) {
      return backing.get(key) ?? null;
    },
    key(index: number) {
      return Array.from(backing.keys())[index] ?? null;
    },
    removeItem(key: string) {
      backing.delete(key);
    },
    setItem(key: string, value: string) {
      backing.set(key, String(value));
    },
  };
  Object.defineProperty(window, "localStorage", { value: memoryStorage, configurable: true });
  Object.defineProperty(globalThis, "localStorage", { value: memoryStorage, configurable: true });
}

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

function seedStory252Fixture() {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: "bu-eng",
          name: "Direction Ingénierie",
          slug: "direction-ingenierie",
          level: "BU",
          parentId: null,
          billingEnabled: true,
          leadUserIds: ["admin@orcia.test"],
          ontologyLeadUserIds: [],
          memberUserIds: [],
        },
        {
          id: "team-core",
          name: "Équipe Plateforme",
          slug: "equipe-plateforme",
          level: "TEAM",
          parentId: "bu-eng",
          billingEnabled: true,
          leadUserIds: ["admin@orcia.test"],
          memberUserIds: ["contrib@orcia.test", "observer@orcia.test"],
        },
      ],
      workspaces: [
        {
          workspaceId: "ws-personal-1",
          name: "Mon Espace Perso",
          slug: "mon-espace-perso",
          visibilityMode: "PRIVATE_USER",
          ownerUserId: "admin@orcia.test",
        },
        {
          workspaceId: "ws-team-core",
          name: "Espace Socle Core",
          slug: "espace-socle-core",
          ownerOrgUnitId: "team-core",
          ownerOrgUnitName: "Équipe Plateforme",
          visibilityMode: "STANDARD",
          scopePath: "bu:direction-ingenierie/team:equipe-plateforme/ws:espace-socle-core",
        },
        {
          workspaceId: "ws-team-data",
          name: "Espace Analytics Data",
          slug: "espace-analytics-data",
          ownerOrgUnitId: "team-core",
          ownerOrgUnitName: "Équipe Plateforme",
          visibilityMode: "STANDARD",
          scopePath: "bu:direction-ingenierie/team:equipe-plateforme/ws:espace-analytics-data",
        },
      ],
      llm_tiers: [
        {
          tier: "PRIMARY",
          provider: "OPENAI",
          model_name: "gpt-4o-mini",
          endpoint_url: "https://api.openai.com/v1",
          status: "VERIFIED",
        },
      ],
      packs: [],
      workflows: [
        {
          workflowKey: "sdlc/ticket-to-tech-spec",
          title: "Spécification Technique",
          version: 1,
          status: "PUBLISHED",
          workspaceId: "ws-team-data",
          layers: [],
        },
      ],
      runs: [],
      catalog_items: [],
      ontology_concepts: [],
      audit_events: [],
    },
    { email: "admin@orcia.test", displayName: "Romain Admin", roles: ["PLATFORM_ADMIN"] },
  );
}

describe("Story 25.2 — 9-Item Shell, Mon Organisation, Administration 5 Tabs, TopBar [O] ORCIA & Unified Scope Selector", () => {
  beforeEach(() => {
    ensureWorkingLocalStorage();
    clearPlatformSetupStorage();
    window.localStorage.removeItem(ORCIA_ACTIVE_SCOPE_STORAGE_KEY);
    resetVitestApiBackend();
    resetAuthSessionStore();
    seedStory252Fixture();
  });

  afterEach(() => {
    cleanup();
    resetAuthSessionStore();
  });

  it("renders exactly 9 fixed sidebar entries, [O] ORCIA top-left home link, zero sidebar logo, zero ⓘ triggers, zero Configuration/Plateforme Globale ORCIA, and 5 Administration tabs", async () => {
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "admin@orcia.test",
      displayName: "Romain Admin",
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });

    const { router } = await renderAppAtRoute("/cockpit");
    const sidebar = await screen.findByTestId("four-zone-sidebar");

    const expectedKeysAndLabels: Array<[string, string]> = [
      ["cockpit", "Cockpit"],
      ["assistant", "Mon Assistant"],
      ["processes", "Mes Processus"],
      ["agents", "Mes Agents"],
      ["spaces", "Mes Espaces"],
      ["organization", "Mon Organisation"],
      ["finops", "FinOps"],
      ["configuration", "Administration"],
      ["help", "Aide"],
    ];

    const items = sidebar.querySelectorAll('[data-testid^="eight-menu-item-"]');
    expect(items).toHaveLength(9);
    for (const [idx, [key, label]] of expectedKeysAndLabels.entries()) {
      expect(items[idx]?.getAttribute("data-testid")).toBe(`eight-menu-item-${key}`);
      expect(items[idx]?.textContent).toContain(label);
    }

    // No sidebar logo, no cockpit-active-scope-badge, no floating ⓘ buttons, no "Configuration" or "Plateforme Globale ORCIA"
    expect(screen.queryByTestId("sidebar-brand-logo")).toBeNull();
    expect(screen.queryByTestId("cockpit-active-scope-badge")).toBeNull();
    expect(document.querySelectorAll(".orcia-info-trigger-btn")).toHaveLength(0);
    expect(sidebar.textContent).not.toContain("Configuration");
    expect(sidebar.textContent).not.toContain("Plateforme Globale ORCIA");

    // TopBar [O] ORCIA link is present top-left and navigates to /cockpit from /settings
    const topbar = screen.getByTestId("four-zone-top-header-bar");
    const homeLink = screen.getByTestId("topbar-orcia-home-link");
    expect(topbar.contains(homeLink)).toBe(true);
    expect(homeLink.textContent).toContain("ORCIA");

    // Navigate to Administration (/settings) -> strictly 5 tabs and no settings-open-organization-link
    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    const tablist = await screen.findByTestId("settings-domain-tabs");
    expect(tablist.querySelectorAll('[role="tab"]')).toHaveLength(5);
    expect(screen.queryByTestId("settings-open-organization-link")).toBeNull();
    expect(screen.getByTestId("topbar-breadcrumb").textContent).toContain("Administration");
    expect(screen.getByTestId("topbar-breadcrumb").textContent).not.toContain("Configuration");

    // Click [O] ORCIA top-left -> navigates back to /cockpit
    fireEvent.click(screen.getByTestId("topbar-orcia-home-link"));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/cockpit");
    });
  });

  it("shows Mon Organisation in read-only mode to CONTRIBUTOR and OBSERVER while hiding Administration", async () => {
    for (const role of ["CONTRIBUTOR", "OBSERVER"] as const) {
      useAuthSessionStore.getState().setAuthSession({
        isAuthenticated: true,
        email: role === "OBSERVER" ? "observer@orcia.test" : "contrib@orcia.test",
        displayName: role,
        roles: [role],
        activeHat: role,
        readOnlyObserver: role === "OBSERVER",
      });

      const { unmount, router } = await renderAppAtRoute("/cockpit");
      const orgMenuItem = await screen.findByTestId("eight-menu-item-organization");
      expect(orgMenuItem).toBeDefined();
      expect(screen.queryByTestId("eight-menu-item-configuration")).toBeNull();

      fireEvent.click(orgMenuItem);
      await waitFor(() => {
        expect(router.state.location.pathname).toBe("/organization");
      });

      const banner = await screen.findByTestId("organization-readonly-access-banner");
      expect(banner).toBeDefined();
      const orgRow = await screen.findByTestId("org-unit-row-bu-eng");
      expect(within(orgRow).getByText("Direction Ingénierie")).toBeDefined();
      expect((screen.getByTestId("open-create-org-unit-modal-btn") as HTMLButtonElement).disabled).toBe(true);
      expect((screen.getByTestId("open-invite-org-user-modal-btn") as HTMLButtonElement).disabled).toBe(true);
      expect(screen.queryByTestId("edit-org-unit-btn-bu-eng")).toBeNull();
      expect(screen.queryByTestId("delete-org-unit-btn-bu-eng")).toBeNull();
      expect(document.querySelectorAll(".orcia-info-trigger-btn")).toHaveLength(0);
      unmount();
    }

    // SECOPS sees Administration (with IAM tab only) AND Mon Organisation
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "secops@orcia.test",
      displayName: "SecOps",
      roles: ["SECOPS"],
      activeHat: "SECOPS",
      readOnlyObserver: false,
    });
    const secView = await renderAppAtRoute("/cockpit");
    expect(await screen.findByTestId("eight-menu-item-organization")).toBeDefined();
    expect(screen.getByTestId("eight-menu-item-configuration")).toBeDefined();
    secView.unmount();
  });

  it("provides a single grouped sidebar-workspace-selector that persists across F5 and propagates to Assistant, Processes, Agents, FinOps, Cockpit & Spaces", async () => {
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "admin@orcia.test",
      displayName: "Romain Admin",
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });

    const firstView = await renderAppAtRoute("/cockpit");
    expect(screen.queryByTestId("sidebar-team-bu-selector")).toBeNull();

    const selector = (await screen.findByTestId("sidebar-workspace-selector")) as HTMLSelectElement;
    const optgroups = Array.from(selector.querySelectorAll("optgroup")).map((g) => g.label);
    expect(optgroups).toContain("Personnel");
    expect(optgroups).toContain("Équipe Plateforme");
    expect(selector.textContent).not.toContain("Plateforme Globale ORCIA");

    // Select Espace Analytics Data (ws-team-data)
    await act(async () => {
      fireEvent.change(selector, { target: { value: "ws-team-data" } });
    });
    expect(window.localStorage.getItem(ORCIA_ACTIVE_SCOPE_STORAGE_KEY)).toBe("ws-team-data");

    // Simulate F5 reload (unmount + remount) -> persisted selection survives
    firstView.unmount();
    const reloaded = await renderAppAtRoute("/cockpit");
    const reloadedSelector = (await screen.findByTestId(
      "sidebar-workspace-selector",
    )) as HTMLSelectElement;
    await waitFor(() => {
      expect(reloadedSelector.value).toBe("ws-team-data");
    });
    expect(screen.queryByTestId("cockpit-active-scope-badge")).toBeNull();

    // Propagates to /spaces (synchronized to ws-team-data via single Left Rail selector)
    fireEvent.click(screen.getByTestId("eight-menu-item-spaces"));
    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe(
        "Espace Analytics Data",
      );
      expect(
        (screen.getByTestId("sidebar-workspace-selector") as HTMLSelectElement).value,
      ).toBe("ws-team-data");
      expect(screen.queryByTestId("workspaces-active-switcher-select")).toBeNull();
    });

    // Propagates to /assistant, /processes, /agents, /finops
    for (const [menuKey, routePath] of [
      ["assistant", "/assistant"],
      ["processes", "/processes"],
      ["agents", "/agents"],
      ["finops", "/finops"],
    ] as const) {
      fireEvent.click(screen.getByTestId(`eight-menu-item-${menuKey}`));
      await waitFor(() => {
        expect(reloaded.router.state.location.pathname).toBe(routePath);
      });
      const currentSelector = screen.getByTestId("sidebar-workspace-selector") as HTMLSelectElement;
      expect(currentSelector.value).toBe("ws-team-data");
      expect(document.querySelectorAll(".orcia-info-trigger-btn")).toHaveLength(0);
    }

    // FinOps scope filter synchronizes with active workspace
    const finopsScopeSelect = screen.queryByTestId(
      "finops-scope-filter-select",
    ) as HTMLSelectElement | null;
    if (finopsScopeSelect) {
      expect(finopsScopeSelect.value).toContain("ws-team-data");
    }

    // Switching selector to ws-personal-1 updates localStorage & active scope immediately
    await act(async () => {
      fireEvent.change(screen.getByTestId("sidebar-workspace-selector"), {
        target: { value: "ws-personal-1" },
      });
    });
    expect(window.localStorage.getItem(ORCIA_ACTIVE_SCOPE_STORAGE_KEY)).toBe("ws-personal-1");
    expect((screen.getByTestId("sidebar-workspace-selector") as HTMLSelectElement).value).toBe(
      "ws-personal-1",
    );
    within(screen.getByTestId("four-zone-sidebar"));
  });

  it("preserves InviteOrganizationUserModal fields when invitableUnits array reference refreshes while open", () => {
    const unit = {
      id: "0192c4e0-0000-7000-8000-000000000001",
      name: "Racine (TEAM)",
      slug: "orcia-root",
      level: "TEAM" as const,
      parentId: "",
      billingEnabled: true,
    };
    const { rerender } = render(
      <InviteOrganizationUserModal
        open={true}
        onOpenChange={() => undefined}
        invitableUnits={[unit]}
        labels={frDictionary.settingsHub.organizationTab.inviteModal}
        errorMessage={null}
        isSubmitting={false}
        onSubmit={() => undefined}
      />,
    );
    const nameInput = screen.getByTestId("invite-org-user-display-name") as HTMLInputElement;
    const emailInput = screen.getByTestId("invite-org-user-email") as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: "Oscar Observateur" } });
    fireEvent.change(emailInput, { target: { value: "oscar.observer@orcia.test" } });

    rerender(
      <InviteOrganizationUserModal
        open={true}
        onOpenChange={() => undefined}
        invitableUnits={[{ ...unit }]}
        labels={frDictionary.settingsHub.organizationTab.inviteModal}
        errorMessage={null}
        isSubmitting={false}
        onSubmit={() => undefined}
      />,
    );
    expect((screen.getByTestId("invite-org-user-display-name") as HTMLInputElement).value).toBe(
      "Oscar Observateur",
    );
    expect((screen.getByTestId("invite-org-user-email") as HTMLInputElement).value).toBe(
      "oscar.observer@orcia.test",
    );
    expect((screen.getByTestId("submit-invite-org-user-btn") as HTMLButtonElement).disabled).toBe(
      false,
    );
  });
});
