import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { seedVitestPlatformSetupState, setVitestPublicAuthMode } from "./vitest.setup";

afterEach(() => {
  cleanup();
  clearPlatformSetupStorage();
  setVitestPublicAuthMode("LOCAL");
});

async function mountSettingsHub(initialPath = "/settings") {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [initialPath] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { view, router };
}

describe("Story 17.3 — IAM Accounts Directory Purged Row 1, Dark Teams Row 2 & BU/Team Leads", () => {
  it("purges Row 1 (no 'Utilisateur' badge, no auth_source badge) and conditionally displays password reset button based on authMode", async () => {
    seedVitestPlatformSetupState(
      {
        org_units: [],
        rbac_grants: [],
        llm_tiers: [],
        workspaces: [],
      },
      { email: "alice.lead@orcia.fr", displayName: "Alice Lead" },
    );

    // 1. In LOCAL mode, password reset button is visible
    setVitestPublicAuthMode("LOCAL");
    const { view } = await mountSettingsHub("/settings");

    fireEvent.click(screen.getByTestId("settings-tab-iam"));
    const accountRow = await screen.findByTestId("iam-account-row-acc-1");

    // Row 1 assertions
    expect(accountRow.textContent).toContain("Alice Lead");
    expect(accountRow.textContent).not.toContain("Utilisateur");
    expect(accountRow.textContent).not.toContain("Compte initial local");
    expect(accountRow.textContent).not.toContain("SSO d'entreprise");
    expect(accountRow.textContent).toContain("Actif");
    expect(screen.getByTestId("iam-reset-password-account-btn-acc-1")).toBeDefined();

    view.unmount();

    // 2. In SSO mode, password reset button must be hidden
    setVitestPublicAuthMode("SSO");
    await mountSettingsHub("/settings");
    fireEvent.click(screen.getByTestId("settings-tab-iam"));
    await screen.findByTestId("iam-account-row-acc-1");

    expect(screen.queryByTestId("iam-reset-password-account-btn-acc-1")).toBeNull();
  });

  it("dynamically shows BU and Team lead fieldsets in modal, saves led BUs/Teams, and displays dark Row 2 with amber unassigned fallback", async () => {
    seedVitestPlatformSetupState(
      {
        org_units: [
          { id: "bu-tech", name: "Direction Technique", slug: "dir-tech", level: "BU", parentId: "scope-global" },
          { id: "bu-rh", name: "Direction RH", slug: "dir-rh", level: "BU", parentId: "scope-global" },
          { id: "team-fe", name: "Équipe Frontend", slug: "team-fe", level: "TEAM", parentId: "bu-tech" },
          { id: "team-be", name: "Équipe Backend", slug: "team-be", level: "TEAM", parentId: "bu-tech" },
        ],
        rbac_grants: [],
        llm_tiers: [],
        workspaces: [],
      },
      { email: "admin@orcia.fr", displayName: "Super Admin" },
    );

    await mountSettingsHub("/settings");
    fireEvent.click(screen.getByTestId("settings-tab-iam"));
    await screen.findByTestId("iam-account-row-acc-1");

    // Open Create Account Modal
    fireEvent.click(screen.getByTestId("iam-open-create-account-btn"));
    expect(screen.getByTestId("iam-account-modal")).toBeDefined();

    // Fieldsets are not visible when BU_LEAD / TEAM_LEAD are unchecked
    expect(screen.queryByTestId("iam-account-led-bus-fieldset")).toBeNull();
    expect(screen.queryByTestId("iam-account-led-teams-fieldset")).toBeNull();

    // Toggle BU_LEAD -> shows BU lead fieldset
    fireEvent.click(screen.getByTestId("iam-account-role-checkbox-BU_LEAD"));
    expect(screen.getByTestId("iam-account-led-bus-fieldset")).toBeDefined();
    expect(screen.getByTestId("iam-account-led-bu-checkbox-bu-tech")).toBeDefined();
    expect(screen.getByTestId("iam-account-led-bu-checkbox-bu-rh")).toBeDefined();

    // Toggle TEAM_LEAD -> shows Team lead fieldset
    fireEvent.click(screen.getByTestId("iam-account-role-checkbox-TEAM_LEAD"));
    expect(screen.getByTestId("iam-account-led-teams-fieldset")).toBeDefined();
    expect(screen.getByTestId("iam-account-led-team-checkbox-team-fe")).toBeDefined();

    // Fill form without selecting specific BUs or Teams (creates an unassigned lead)
    fireEvent.change(screen.getByTestId("iam-account-display-name-input"), {
      target: { value: "Marc Manager" },
    });
    fireEvent.change(screen.getByTestId("iam-account-principal-input"), {
      target: { value: "marc.manager@orcia.fr" },
    });
    fireEvent.click(screen.getByTestId("iam-account-modal-submit-btn"));

    // Account row displays amber indicators for unassigned BU and Team lead roles
    const unassignedRow = await screen.findByTestId("iam-account-row-acc-2");
    expect(unassignedRow.textContent).toContain("Marc Manager");

    const buUnassigned = screen.getByTestId("iam-account-led-bus-unassigned-acc-2");
    expect(buUnassigned.textContent).toContain("Direction (BU) : aucune assignée");
    expect(buUnassigned.style.color).toBe("var(--color-arbitration-amber)");

    const teamUnassigned = screen.getByTestId("iam-account-led-teams-unassigned-acc-2");
    expect(teamUnassigned.textContent).toContain("Équipe dirigée : aucune assignée");
    expect(teamUnassigned.style.color).toBe("var(--color-arbitration-amber)");

    // Edit account to assign Direction Technique and Équipe Frontend + member in Équipe Backend
    fireEvent.click(screen.getByTestId("iam-edit-account-btn-acc-2"));
    expect(screen.getByTestId("iam-account-modal")).toBeDefined();

    // Check BU checkbox
    fireEvent.click(screen.getByTestId("iam-account-led-bu-checkbox-bu-tech"));
    // Check Team lead checkbox
    fireEvent.click(screen.getByTestId("iam-account-led-team-checkbox-team-fe"));
    // Check Team member checkbox (backend)
    fireEvent.click(screen.getByTestId("iam-account-team-checkbox-team-be"));

    fireEvent.click(screen.getByTestId("iam-account-modal-submit-btn"));

    // Wait for row update and verify dark bold styling
    await waitFor(() => {
      const ledBuEl = screen.getByTestId("iam-account-led-bus-acc-2");
      expect(ledBuEl.textContent).toContain("Direction (BU) : Direction Technique");
      expect(ledBuEl.style.color).toBe("var(--color-foreground)");
      expect(ledBuEl.style.fontWeight).toBe("600");
    });

    const ledTeamEl = screen.getByTestId("iam-account-led-teams-acc-2");
    expect(ledTeamEl.textContent).toContain("Équipe dirigée : Équipe Frontend");
    expect(ledTeamEl.style.color).toBe("var(--color-foreground)");
    expect(ledTeamEl.style.fontWeight).toBe("600");

    const memberTeamEl = screen.getByTestId("iam-account-member-teams-acc-2");
    expect(memberTeamEl.textContent).toContain("Équipe : Équipe Backend");
    expect(memberTeamEl.style.color).toBe("var(--color-foreground)");
    expect(memberTeamEl.style.fontWeight).toBe("600");
  });

  it("persists led BU and Team assignments across F5 reload (unmount & remount)", async () => {
    seedVitestPlatformSetupState(
      {
        org_units: [
          { id: "bu-tech", name: "Direction Technique", slug: "dir-tech", level: "BU", parentId: "scope-global" },
          { id: "team-fe", name: "Équipe Frontend", slug: "team-fe", level: "TEAM", parentId: "bu-tech" },
        ],
        rbac_grants: [],
        llm_tiers: [],
        workspaces: [],
      },
      { email: "persisted.admin@orcia.fr", displayName: "Persisted Admin" },
    );

    const firstMount = await mountSettingsHub("/settings");
    fireEvent.click(screen.getByTestId("settings-tab-iam"));
    await screen.findByTestId("iam-account-row-acc-1");

    // Create a BU_LEAD account assigned to bu-tech
    fireEvent.click(screen.getByTestId("iam-open-create-account-btn"));
    fireEvent.change(screen.getByTestId("iam-account-display-name-input"), {
      target: { value: "Directrice Tech" },
    });
    fireEvent.change(screen.getByTestId("iam-account-principal-input"), {
      target: { value: "directrice.tech@orcia.fr" },
    });
    fireEvent.click(screen.getByTestId("iam-account-role-checkbox-BU_LEAD"));
    fireEvent.click(screen.getByTestId("iam-account-led-bu-checkbox-bu-tech"));
    fireEvent.click(screen.getByTestId("iam-account-modal-submit-btn"));

    await screen.findByTestId("iam-account-row-acc-2");
    expect(screen.getByTestId("iam-account-led-bus-acc-2").textContent).toContain(
      "Direction (BU) : Direction Technique",
    );

    // Simulate F5 page reload: unmount view and remount from storage
    firstMount.view.unmount();

    await mountSettingsHub("/settings");
    fireEvent.click(screen.getByTestId("settings-tab-iam"));
    await screen.findByTestId("iam-account-row-acc-2");

    const reloadedLedBu = screen.getByTestId("iam-account-led-bus-acc-2");
    expect(reloadedLedBu.textContent).toContain("Direction (BU) : Direction Technique");
    expect(reloadedLedBu.style.fontWeight).toBe("600");
  });
});
