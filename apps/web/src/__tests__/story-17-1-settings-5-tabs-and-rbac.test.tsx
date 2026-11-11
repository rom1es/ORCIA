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
  SCOPED_LEAD_SETTINGS_TABS,
  formatCountNoun,
  resetAuthSessionStore,
  resolveSessionHatLabel,
  resolveSettingsAccess,
  useAuthSessionStore,
} from "../stores/authSessionStore";

afterEach(() => {
  cleanup();
  resetAuthSessionStore();
});

describe("Story 17.1 — 5 Adaptive /settings Tabs, Dynamic RBAC, Danger Buttons & Mon Compte Sidebar", () => {
  it("resolves deterministic /settings tab visibility and permission verbs across all 6 governance roles", () => {
    const adminAccess = resolveSettingsAccess({
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });
    expect(adminAccess.visibleTabs).toEqual(ALL_SETTINGS_TABS);
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
    expect(secopsAccess.visibleTabs).toEqual(ALL_SETTINGS_TABS);
    expect(secopsAccess.canMutate).toBe(true);

    const buLeadAccess = resolveSettingsAccess({
      roles: ["BU_LEAD"],
      activeHat: "BU_LEAD",
    });
    expect(buLeadAccess.visibleTabs).toEqual(SCOPED_LEAD_SETTINGS_TABS);
    expect(buLeadAccess.canMutate).toBe(true);

    const teamLeadAccess = resolveSettingsAccess({
      roles: ["TEAM_LEAD"],
      activeHat: "TEAM_LEAD",
    });
    expect(teamLeadAccess.visibleTabs).toEqual(["organization", "iam"]);
    expect(teamLeadAccess.canMutate).toBe(true);

    const contributorAccess = resolveSettingsAccess({
      roles: ["CONTRIBUTOR"],
      activeHat: "CONTRIBUTOR",
    });
    expect(contributorAccess.visibleTabs).toEqual([]);
    expect(contributorAccess.allowedVerbs).toEqual(["read"]);
    expect(contributorAccess.canMutate).toBe(false);
    expect(contributorAccess.isReadOnlyRestricted).toBe(true);

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

  it("renders exactly 5 wireframe-icon tabs for PLATFORM_ADMIN, separates Organization from IAM, removes Workflows & Glossary tabs, and applies .orcia-ds-btn-danger", async () => {
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

    expect(screen.queryByTestId("settings-tab-workflows")).toBeNull();
    expect(screen.queryByTestId("settings-tab-glossary")).toBeNull();
    expect(screen.queryByTestId("settings-tab-ai-models")).toBeNull();

    // Tab 1 (organization) shows Organization Units ONLY, not IAM grants
    expect(screen.getByTestId("settings-organization-section")).toBeDefined();
    expect(screen.queryByTestId("settings-iam-section")).toBeNull();

    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Direction Risques" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));

    const deleteOrgBtn = screen.getByTestId("delete-org-unit-btn-org-1");
    expect(deleteOrgBtn.className).toContain("orcia-ds-btn-danger");

    // Tab 2 (iam) shows IAM Permission Grants ONLY, not Organization Units
    fireEvent.click(screen.getByTestId("settings-tab-iam"));
    expect(screen.getByTestId("settings-iam-section")).toBeDefined();
    expect(screen.queryByTestId("settings-organization-section")).toBeNull();
  });

  it("restricts BU_LEAD / TEAM_LEAD to 2 adaptive tabs (organization, iam) and shows read-only notice + Mon Compte modal shortcut for CONTRIBUTOR / OBSERVER", async () => {
    useAuthSessionStore.getState().setAuthSession({
      roles: ["BU_LEAD"],
      activeHat: "BU_LEAD",
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

    expect(screen.getByTestId("settings-tab-organization")).toBeDefined();
    expect(screen.getByTestId("settings-tab-iam")).toBeDefined();
    expect(screen.queryByTestId("settings-tab-models")).toBeNull();
    expect(screen.queryByTestId("settings-tab-connectors")).toBeNull();
    expect(screen.queryByTestId("settings-tab-packs")).toBeNull();

    // Switch role dynamically to CONTRIBUTOR -> 0 admin tabs, read-only banner + Open My Account CTA
    act(() => {
      useAuthSessionStore.getState().setAuthSession({
        roles: ["CONTRIBUTOR"],
        activeHat: "CONTRIBUTOR",
      });
    });

    expect(screen.queryByTestId("settings-domain-tabs")).toBeNull();
    const banner = screen.getByTestId("settings-readonly-access-banner");
    expect(banner.textContent).toContain("lecture seule");

    fireEvent.click(screen.getByTestId("open-my-account-from-settings-btn"));
    expect(screen.getByTestId("user-settings-modal")).toBeDefined();
  });

  it("displays dynamic localized userHatLabel (FR & EN) and opens UserSettingsModal from the Sidebar 'Mon Compte' entry as well as Topbar", () => {
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

    const dropdownTrigger = screen.getByTestId("user-account-dropdown-trigger");
    expect(dropdownTrigger.textContent).toContain("Sophie SecOps");
    expect(screen.getByTestId("user-account-role-pill").textContent).toContain(
      "Responsable Sécurité & Habilitations",
    );
    expect(dropdownTrigger.textContent).not.toContain("Administrateur de la plateforme");

    const sidebarAccountBtn = screen.getByTestId("sidebar-open-my-account-btn");
    expect(sidebarAccountBtn.className).toContain("orcia-sidebar-nav-btn");
    expect(sidebarAccountBtn.querySelector("svg")).not.toBeNull();
    expect(sidebarAccountBtn.textContent).toContain("Mon Compte");

    fireEvent.click(sidebarAccountBtn);
    expect(screen.getByTestId("user-settings-modal")).toBeDefined();
  });
});
