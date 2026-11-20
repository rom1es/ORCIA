import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { ShellContainer } from "../components/ShellContainer";
import { CockpitFeaturePanel } from "../features/cockpit";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import {
  ALL_SETTINGS_TABS,
  formatCountNoun,
  resetAuthSessionStore,
  resolveSessionHatLabel,
  resolveSettingsAccess,
  useAuthSessionStore,
} from "../stores/authSessionStore";

import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

afterEach(() => {
  cleanup();
  resetAuthSessionStore();
  resetVitestApiBackend();
});

describe("Settings Tabs (5 Tabs), Exclusive PLATFORM_ADMIN Visibility & Mon Compte Sidebar", () => {
  it("grants /settings tabs exclusively to PLATFORM_ADMIN and restricts all non-admin roles across the 7 governance roles", () => {
    const adminAccess = resolveSettingsAccess({
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });
    expect(adminAccess.visibleTabs).toEqual(ALL_SETTINGS_TABS);
    expect(adminAccess.visibleTabs).toContain("authentication");
    expect(adminAccess.canMutate).toBe(true);
    expect(adminAccess.isReadOnlyRestricted).toBe(false);
    expect(adminAccess.allowedVerbs).toEqual([
      "create",
      "read",
      "update",
      "delete",
      "execute",
      "grant",
    ]);

    const secopsAccess = resolveSettingsAccess({
      roles: ["SECOPS"],
      activeHat: "SECOPS",
    });
    expect(secopsAccess.visibleTabs).toEqual(["iam"]);
    expect(secopsAccess.canMutate).toBe(true);
    expect(secopsAccess.isReadOnlyRestricted).toBe(false);

    for (const nonAdminRole of [
      "BU_LEAD",
      "TEAM_LEAD",
      "ONTOLOGY_LEAD",
      "CONTRIBUTOR",
      "OBSERVER",
    ] as const) {
      const access = resolveSettingsAccess({
        roles: [nonAdminRole],
        activeHat: nonAdminRole,
      });
      expect(access.visibleTabs).toEqual([]);
      expect(access.allowedVerbs).toEqual(["read"]);
      expect(access.canMutate).toBe(false);
      expect(access.isReadOnlyRestricted).toBe(true);
    }

    const observerAccess = resolveSettingsAccess({
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
      readOnlyObserver: true,
    });
    expect(observerAccess.visibleTabs).toEqual([]);
    expect(observerAccess.allowedVerbs).toEqual(["read"]);
    expect(observerAccess.canMutate).toBe(false);
    expect(observerAccess.isReadOnlyRestricted).toBe(true);
  });

  it("formats singular and plural counts without raw '(s)' suffixes in FR and EN", () => {
    expect(formatCountNoun(0, "Équipe rattachée", "Équipes rattachées", "fr")).toBe(
      "0 Équipe rattachée",
    );
    expect(formatCountNoun(1, "Équipe rattachée", "Équipes rattachées", "fr")).toBe(
      "1 Équipe rattachée",
    );
    expect(formatCountNoun(2, "Équipe rattachée", "Équipes rattachées", "fr")).toBe(
      "2 Équipes rattachées",
    );
    expect(formatCountNoun(1, "attached Team", "attached Teams", "en")).toBe(
      "1 attached Team",
    );
    expect(formatCountNoun(2, "attached Team", "attached Teams", "en")).toBe(
      "2 attached Teams",
    );
  });

  it("renders all 5 wireframe-icon tabs including Authentification & Connecteurs for PLATFORM_ADMIN, separates Mon Organisation into /organization, and applies .orcia-ds-btn-danger", async () => {
    seedVitestPlatformSetupState(
      {},
      { email: "admin@orcia.fr", displayName: "Admin", roles: ["PLATFORM_ADMIN"] },
    );
    useAuthSessionStore.getState().setAuthSession({
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });

    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    const tablist = screen.getByTestId("settings-domain-tabs");
    const tabButtons = tablist.querySelectorAll('[role="tab"]');
    expect(tabButtons.length).toBe(5);

    for (const key of ALL_SETTINGS_TABS) {
      const btn = screen.getByTestId(`settings-tab-${key}`);
      expect(btn.querySelector("svg")).not.toBeNull();
    }
    expect(screen.getByTestId("settings-tab-authentication").textContent).toBe("Authentification");
    expect(screen.getByTestId("settings-tab-connectors").textContent).toBe("Connecteurs");

    expect(screen.queryByTestId("settings-tab-organization")).toBeNull();
    expect(screen.queryByTestId("settings-tab-workflows")).toBeNull();
    expect(screen.queryByTestId("settings-tab-glossary")).toBeNull();
    expect(screen.queryByTestId("settings-tab-ai-models")).toBeNull();

    // Default tab 1 (iam) shows IAM Permission Grants ONLY, not Organization Units
    expect(screen.getByTestId("settings-iam-section")).toBeDefined();
    expect(screen.queryByTestId("settings-organization-section")).toBeNull();

    // Navigate to Mon Organisation (/organization) via dedicated Sidebar entry (5 tabs only in Administration)
    expect(screen.queryByTestId("settings-open-organization-link")).toBeNull();
    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    expect(await screen.findByTestId("settings-organization-section")).toBeDefined();

    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Direction Risques" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));

    const deleteOrgBtn = await screen.findByTestId("delete-org-unit-btn-org-1");
    expect(deleteOrgBtn.className).toContain("orcia-ds-btn-danger");
  });

  it("grants SECOPS access ONLY to IAM tab in Configuration, hides platform settings tabs from BU_LEAD/CONTRIBUTOR, and shows Mon Compte shortcut", async () => {
    useAuthSessionStore.getState().setAuthSession({
      roles: ["SECOPS"],
      activeHat: "SECOPS",
    });

    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    expect(screen.getByTestId("eight-menu-item-configuration")).toBeDefined();
    expect(screen.getByTestId("settings-tab-iam")).toBeDefined();
    expect(screen.queryByTestId("settings-tab-authentication")).toBeNull();
    expect(screen.queryByTestId("settings-tab-models")).toBeNull();
    expect(screen.queryByTestId("settings-tab-connectors")).toBeNull();
    expect(screen.queryByTestId("settings-tab-packs")).toBeNull();
    expect(screen.getByTestId("settings-iam-section")).toBeDefined();

    // Switch role dynamically to CONTRIBUTOR -> restricted with Open My Account CTA
    act(() => {
      useAuthSessionStore.getState().setAuthSession({
        roles: ["CONTRIBUTOR"],
        activeHat: "CONTRIBUTOR",
      });
    });

    expect(screen.queryByTestId("settings-domain-tabs")).toBeNull();
    expect(screen.queryByTestId("eight-menu-item-configuration")).toBeNull();
    const banner = screen.getByTestId("settings-readonly-access-banner");
    expect(banner.textContent).toContain("lecture seule");

    fireEvent.click(screen.getByTestId("open-my-account-from-settings-btn"));
    expect(screen.getByTestId("user-settings-modal")).toBeDefined();
  });

  it("displays dynamic localized userHatLabel (FR & EN), exposes IAM-scoped Configuration menu for SECOPS, and opens UserSettingsModal", () => {
    useAuthSessionStore.getState().setAuthSession({
      roles: ["SECOPS"],
      activeHat: "SECOPS",
      displayName: "Sophie SecOps",
    });

    expect(
      resolveSessionHatLabel({ roles: ["SECOPS"], activeHat: "SECOPS" }, "fr"),
    ).toBe("Responsable Sécurité & Habilitations");
    expect(
      resolveSessionHatLabel({ roles: ["SECOPS"], activeHat: "SECOPS" }, "en"),
    ).toBe("Security & Access Officer");

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <CockpitFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    expect(screen.getByTestId("eight-menu-item-configuration")).toBeDefined();
    expect(screen.queryByTestId("user-account-dropdown-trigger")).toBeNull();

    const sidebarAccountBtn = screen.getByTestId("sidebar-open-my-account-btn");
    expect(sidebarAccountBtn.className).toContain("orcia-sidebar-nav-btn");
    expect(sidebarAccountBtn.querySelector("svg")).not.toBeNull();
    expect(sidebarAccountBtn.textContent).toContain("Sophie SecOps");
    expect(sidebarAccountBtn.textContent).toContain("Responsable Sécurité & Habilitations");
    expect(sidebarAccountBtn.textContent).not.toContain("Administrateur de la plateforme");

    fireEvent.keyDown(sidebarAccountBtn, { key: "Enter" });
    fireEvent.click(screen.getByTestId("account-popover-personalization-btn"));
    expect(screen.getByTestId("user-settings-modal")).toBeDefined();
  });
});
