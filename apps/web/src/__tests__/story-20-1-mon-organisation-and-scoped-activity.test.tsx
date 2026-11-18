import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage, writeCachedPlatformAdmin } from "../components/platformSetupStorageHelpers";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

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

function seedMultiBuSetup() {
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
          leadUserIds: ["martin.pecheur@orcia.ia"],
          ontologyLeadUserIds: ["claire.admin@orcia.fr"],
          memberUserIds: [],
        },
        {
          id: "team-ops-1",
          name: "Équipe Support N2",
          slug: "equipe-support-n2",
          level: "TEAM",
          parentId: "bu-ops",
          billingEnabled: true,
          leadUserIds: ["pascal.lacdap@orcia.ia"],
          memberUserIds: ["alice@orcia.fr"],
        },
        {
          id: "bu-finance",
          name: "Direction Finance",
          slug: "direction-finance",
          level: "BU",
          parentId: "scope-global",
          billingEnabled: true,
          leadUserIds: ["vp.produit@orcia.fr"],
          ontologyLeadUserIds: [],
          memberUserIds: [],
        },
        {
          id: "team-finance-1",
          name: "Équipe Contrôle",
          slug: "equipe-controle",
          level: "TEAM",
          parentId: "bu-finance",
          billingEnabled: true,
          leadUserIds: ["marc.lead@orcia.fr"],
          memberUserIds: ["bob@orcia.fr"],
        },
      ],
      workspaces: [
        {
          workspaceId: "ws-ops-1",
          name: "Support Production",
          ownerOrgUnitId: "team-ops-1",
          scopePath: "bu:direction-operations/team:equipe-support-n2/ws:support-production",
        },
        {
          workspaceId: "ws-fin-1",
          name: "Clôture Finance",
          ownerOrgUnitId: "team-finance-1",
          scopePath: "bu:direction-finance/team:equipe-controle/ws:cloture-finance",
        },
      ],
      rbac_grants: [],
      llm_tiers: [],
      datasources: [],
      packs: [],
      workflows: [],
      runs: [],
      catalog_items: [],
      ontology_concepts: [],
      audit_events: [
        {
          id: "evt-ops-1",
          event_type: "ORG_UNIT_UPDATED",
          summary: "Mise à jour Support N2",
          scope_path: "bu:direction-operations/team:equipe-support-n2",
          workspace_id: "ws-ops-1",
          org_unit_id: "team-ops-1",
          actor_name: "Martin Pecheur",
          created_at: "2026-11-18T09:00:00Z",
        },
      ],
    },
    { email: "admin@orcia.test", displayName: "Admin Test", roles: ["PLATFORM_ADMIN"] },
  );
}

describe("Story 20.1 — Menu Mon Organisation, Délégation BU/Team, Invitation, ONTOLOGY_LEAD & Scope /activity", () => {
  beforeEach(() => {
    clearPlatformSetupStorage();
    resetVitestApiBackend();
    resetAuthSessionStore();
    seedMultiBuSetup();
  });

  afterEach(() => {
    cleanup();
    resetAuthSessionStore();
  });

  it("exposes Mon Organisation directly below Mes Espaces only for PLATFORM_ADMIN, BU_LEAD, TEAM_LEAD", async () => {
    for (const visibleRole of ["PLATFORM_ADMIN", "BU_LEAD", "TEAM_LEAD"] as const) {
      useAuthSessionStore.getState().setAuthSession({
        isAuthenticated: true,
        email: visibleRole === "BU_LEAD" ? "martin.pecheur@orcia.ia" : visibleRole === "TEAM_LEAD" ? "pascal.lacdap@orcia.ia" : "admin@orcia.test",
        displayName: visibleRole,
        roles: [visibleRole],
        activeHat: visibleRole,
      });
      const { unmount } = await renderAppAtRoute("/");
      const spacesBtn = await screen.findByTestId("eight-menu-item-spaces");
      const orgBtn = await screen.findByTestId("eight-menu-item-organization");
      expect(orgBtn.textContent).toContain("Mon Organisation");
      expect(Boolean(spacesBtn.compareDocumentPosition(orgBtn) & Node.DOCUMENT_POSITION_FOLLOWING)).toBe(true);
      unmount();
    }

    for (const hiddenRole of ["SECOPS", "ONTOLOGY_LEAD", "CONTRIBUTOR", "OBSERVER"] as const) {
      useAuthSessionStore.getState().setAuthSession({
        isAuthenticated: true,
        email: `${hiddenRole.toLowerCase()}@orcia.ia`,
        displayName: hiddenRole,
        roles: [hiddenRole],
        activeHat: hiddenRole,
      });
      const { unmount } = await renderAppAtRoute("/");
      await screen.findByTestId("eight-menu-item-spaces");
      expect(screen.queryByTestId("eight-menu-item-organization")).toBeNull();
      unmount();
    }
  }, 15000);

  it("redirects /settings?tab=organization to /organization and exposes 5 tabs on /settings", async () => {
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "admin@orcia.test",
      displayName: "Admin Test",
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });
    const { router } = await renderAppAtRoute("/settings?tab=organization");
    expect(await screen.findByTestId("organization-page")).toBeTruthy();
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/organization");
    });

    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    const settingsTabs = await screen.findByTestId("settings-domain-tabs");
    expect(within(settingsTabs).queryByTestId("settings-tab-organization")).toBeNull();
    expect(within(settingsTabs).getByTestId("settings-tab-iam")).toBeTruthy();
  }, 10000);

  it("lets BU_LEAD manage own BU subtree, invite users (temp password modal), assign ONTOLOGY_LEAD, blocks root delete, and survives F5", async () => {
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "martin.pecheur@orcia.ia",
      displayName: "Martin Pecheur",
      roles: ["BU_LEAD"],
      activeHat: "BU_LEAD",
    });
    writeCachedPlatformAdmin({
      email: "martin.pecheur@orcia.ia",
      displayName: "Martin Pecheur",
      role: "BU_LEAD",
    });

    const firstMount = await renderAppAtRoute("/organization");
    await screen.findByTestId("organization-page");

    await waitFor(() => {
      expect(screen.getByText("Direction Opérations")).toBeTruthy();
      expect(screen.getByText("Équipe Support N2")).toBeTruthy();
    });
    expect(screen.queryByText("Direction Finance")).toBeNull();
    expect(screen.getByTestId("org-unit-ontology-lead-badge-bu-ops")).toBeTruthy();

    const rootDeleteBtn = screen.queryByTestId("delete-org-unit-btn-bu-ops") as HTMLButtonElement | null;
    if (rootDeleteBtn) {
      expect(rootDeleteBtn.disabled).toBe(true);
    }

    fireEvent.click(screen.getByTestId("open-invite-org-user-modal-btn"));
    const inviteModal = await screen.findByTestId("invite-org-user-modal");
    fireEvent.change(within(inviteModal).getByTestId("invite-org-user-display-name"), {
      target: { value: "Lucie Glossaire" },
    });
    fireEvent.change(within(inviteModal).getByTestId("invite-org-user-email"), {
      target: { value: "lucie.glossaire@orcia.ia" },
    });
    fireEvent.change(within(inviteModal).getByTestId("invite-org-unit-select"), {
      target: { value: "bu-ops" },
    });
    fireEvent.change(within(inviteModal).getByTestId("invite-org-user-role-select"), {
      target: { value: "ONTOLOGY_LEAD" },
    });
    fireEvent.click(within(inviteModal).getByTestId("submit-invite-org-user-btn"));

    const tempPwdModal = await screen.findByTestId("temp-password-modal");
    expect(tempPwdModal.textContent).toContain("OrciaMock!2026");

    // F5 persistence check: unmount and remount at /organization
    firstMount.unmount();
    await renderAppAtRoute("/organization");
    await screen.findByTestId("organization-page");
    await waitFor(() => {
      expect(screen.getByText("Direction Opérations")).toBeTruthy();
      expect(screen.getByTestId("org-unit-ontology-lead-badge-bu-ops").textContent).toContain(
        "Lucie Glossaire",
      );
    });
  });

  it("renders read-only ancestor BU and editable directed team for TEAM_LEAD", async () => {
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "pascal.lacdap@orcia.ia",
      displayName: "Pascal Lacdap",
      roles: ["TEAM_LEAD"],
      activeHat: "TEAM_LEAD",
    });

    await renderAppAtRoute("/organization");
    await screen.findByTestId("organization-page");

    await waitFor(() => {
      expect(screen.getByTestId("org-scoped-view-notice")).toBeTruthy();
      expect(screen.getByTestId("org-unit-readonly-badge-bu-ops")).toBeTruthy();
      expect(screen.getByText("Équipe Support N2")).toBeTruthy();
    });
    expect(screen.queryByTestId("open-invite-org-user-modal-btn")).toBeNull();
    expect((screen.getByTestId("open-create-org-unit-modal-btn") as HTMLButtonElement).disabled).toBe(true);

    const editTeamBtn = screen.getByTestId("edit-org-unit-btn-team-ops-1") as HTMLButtonElement;
    expect(editTeamBtn.disabled).toBe(false);
    expect((screen.getByTestId("delete-org-unit-btn-team-ops-1") as HTMLButtonElement).disabled).toBe(true);
  });

  it("never exposes or preselects global platform scope in /activity for BU_LEAD or TEAM_LEAD, but keeps it for PLATFORM_ADMIN & SECOPS", async () => {
    for (const scopedRole of ["BU_LEAD", "TEAM_LEAD", "CONTRIBUTOR"] as const) {
      useAuthSessionStore.getState().setAuthSession({
        isAuthenticated: true,
        email: scopedRole === "BU_LEAD" ? "martin.pecheur@orcia.ia" : "pascal.lacdap@orcia.ia",
        displayName: scopedRole,
        roles: [scopedRole],
        activeHat: scopedRole,
      });
      const { unmount } = await renderAppAtRoute("/activity");
      const scopeSelect = (await screen.findByTestId("activity-scope-filter-select")) as HTMLSelectElement;
      const optionValues = Array.from(scopeSelect.options).map((o) => o.value);
      expect(optionValues).not.toContain("ALL");
      expect(optionValues).not.toContain("scope-global");
      expect(scopeSelect.textContent).not.toContain("Plateforme entière");
      expect(scopeSelect.value).not.toBe("ALL");
      expect(scopeSelect.value).not.toBe("scope-global");
      unmount();
    }

    for (const globalRole of ["PLATFORM_ADMIN", "SECOPS"] as const) {
      useAuthSessionStore.getState().setAuthSession({
        isAuthenticated: true,
        email: `${globalRole.toLowerCase()}@orcia.test`,
        displayName: globalRole,
        roles: [globalRole],
        activeHat: globalRole,
      });
      const { unmount } = await renderAppAtRoute("/activity");
      const scopeSelect = (await screen.findByTestId("activity-scope-filter-select")) as HTMLSelectElement;
      const optionValues = Array.from(scopeSelect.options).map((o) => o.value);
      expect(optionValues).toContain("ALL");
      unmount();
    }
  });
});
