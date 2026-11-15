import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { seedVitestPlatformSetupState } from "./vitest.setup";

afterEach(() => {
  cleanup();
  clearPlatformSetupStorage();
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

describe("Story 17.3 — Accounts Directory, Native 6-Role Matrix, SecOps Drawer & Zero Exposed Secrets", () => {
  it("eradicates 'Lire / Voir les secrets', displays AD-21 Write-Only secret banner, and renders all 6 roles including BU_LEAD", async () => {
    seedVitestPlatformSetupState(
      { org_units: [], rbac_grants: [], llm_tiers: [], workspaces: [] },
      { email: "claire.admin@orcia.fr", displayName: "Claire Fondatrice" },
    );
    await mountSettingsHub("/settings");

    fireEvent.click(screen.getByTestId("settings-tab-iam"));
    await screen.findByTestId("iam-account-row-acc-1");

    // Expand SecOps drawer as well so all 3 sections are in the DOM
    fireEvent.click(screen.getByTestId("iam-secops-drawer-toggle"));

    const fullText = document.body.textContent ?? "";
    expect(fullText).not.toContain("Lire / Voir les secrets");
    expect(fullText).not.toContain("Read / View secrets");
    expect(fullText).toContain("Consulter les ressources");

    // AD-21 Write-Only secret banner is visible
    const secretBanner = screen.getByTestId("iam-write-only-secrets-banner");
    expect(secretBanner.textContent).toContain("saisie seule");
    expect(secretBanner.textContent).toContain("Aucun rôle");

    // All 6 official roles including BU_LEAD are rendered in Section 2
    for (const roleKey of [
      "PLATFORM_ADMIN",
      "SECOPS",
      "BU_LEAD",
      "TEAM_LEAD",
      "CONTRIBUTOR",
      "OBSERVER",
    ]) {
      expect(screen.getByTestId(`iam-matrix-role-row-${roleKey}`)).toBeDefined();
    }
    expect(screen.getByTestId("iam-matrix-role-row-BU_LEAD").textContent).toContain(
      "Responsable de Direction (BU)",
    );
  });

  it("auto-seeds Day-0 admin (PLATFORM_ADMIN + SECOPS), allows RSSI separation & SERVICE_PRINCIPAL creation, and enforces anti-lockout (422)", async () => {
    seedVitestPlatformSetupState(
      {
        org_units: [
          { id: "org-bu-1", name: "Pôle Produit", slug: "pole-produit", level: "BU", parentId: "scope-global" },
          { id: "org-team-1", name: "Équipe Sécurité", slug: "equipe-securite", level: "TEAM", parentId: "org-bu-1" },
        ],
        rbac_grants: [],
        llm_tiers: [],
        workspaces: [],
      },
      { email: "fondateur@orcia.fr", displayName: "Jean Fondateur" },
    );
    await mountSettingsHub("/settings");

    fireEvent.click(screen.getByTestId("settings-tab-iam"));
    const adminRow = await screen.findByTestId("iam-account-row-acc-1");
    expect(adminRow.textContent).toContain("Jean Fondateur");
    expect(adminRow.textContent).toContain("Administrateur Plateforme");
    expect(adminRow.textContent).toContain("Responsable Sécurité (SecOps)");

    // Attempt to delete the last active PLATFORM_ADMIN -> blocked with 422 crimson banner!
    fireEvent.click(screen.getByTestId("iam-delete-account-btn-acc-1"));
    const lockoutBanner = await screen.findByTestId("iam-accounts-error-banner");
    expect(lockoutBanner.textContent).toContain(
      "Impossible de supprimer le dernier Administrateur Plateforme actif",
    );
    expect(screen.getByTestId("iam-account-row-acc-1")).toBeDefined();

    // Create a dedicated RSSI account (SECOPS) attached to Équipe Sécurité
    fireEvent.click(screen.getByTestId("iam-open-create-account-btn"));
    fireEvent.change(screen.getByTestId("iam-account-display-name-input"), {
      target: { value: "Nadia RSSI" },
    });
    fireEvent.change(screen.getByTestId("iam-account-principal-input"), {
      target: { value: "nadia.rssi@orcia.fr" },
    });
    fireEvent.click(screen.getByTestId("iam-account-role-checkbox-CONTRIBUTOR"));
    fireEvent.click(screen.getByTestId("iam-account-role-checkbox-SECOPS"));
    fireEvent.click(screen.getByTestId("iam-account-team-checkbox-org-team-1"));
    fireEvent.click(screen.getByTestId("iam-account-modal-submit-btn"));

    const rssiRow = await screen.findByTestId("iam-account-row-acc-2");
    expect(rssiRow.textContent).toContain("Nadia RSSI");
    expect(rssiRow.textContent).toContain("Responsable Sécurité (SecOps)");
    expect(rssiRow.textContent).toContain("Équipe Sécurité");

    // Create a technical SERVICE_PRINCIPAL account
    fireEvent.click(screen.getByTestId("iam-open-create-account-btn"));
    fireEvent.change(screen.getByTestId("iam-account-kind-select"), {
      target: { value: "SERVICE_PRINCIPAL" },
    });
    fireEvent.change(screen.getByTestId("iam-account-display-name-input"), {
      target: { value: "Connecteur Indexation" },
    });
    fireEvent.change(screen.getByTestId("iam-account-principal-input"), {
      target: { value: "sp-indexation-worker" },
    });
    fireEvent.click(screen.getByTestId("iam-account-modal-submit-btn"));

    const spRow = await screen.findByTestId("iam-account-row-acc-3");
    expect(spRow.textContent).toContain("Compte technique");
    expect(spRow.textContent).toContain("sp-indexation-worker");

    // Detach SECOPS from initial Day-0 admin while keeping PLATFORM_ADMIN -> succeeds cleanly!
    fireEvent.click(screen.getByTestId("iam-edit-account-btn-acc-1"));
    fireEvent.click(screen.getByTestId("iam-account-role-checkbox-SECOPS"));
    fireEvent.click(screen.getByTestId("iam-account-modal-submit-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("iam-account-row-acc-1").textContent).not.toContain(
        "Responsable Sécurité (SecOps)",
      );
    });
  });

  it("enforces SecOps drawer confinement, closed beneficiary select, GLOBAL amber warning, auto-read verb dependency, and F5 reload survival", async () => {
    seedVitestPlatformSetupState(
      {
        org_units: [
          { id: "org-bu-1", name: "Direction Finance", slug: "dir-finance", level: "BU", parentId: "scope-global" },
        ],
        rbac_grants: [],
        llm_tiers: [],
        workspaces: [],
      },
      { email: "secops.admin@orcia.fr", displayName: "Karim SecOps" },
    );

    // 1. Non-SecOps user (PLATFORM_ADMIN without SECOPS) sees locked read-only notice inside drawer
    useAuthSessionStore.getState().setAuthSession({
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });

    const firstMount = await mountSettingsHub("/settings");
    fireEvent.click(screen.getByTestId("settings-tab-iam"));
    await screen.findByTestId("iam-account-row-acc-1");

    const drawerToggle = screen.getByTestId("iam-secops-drawer-toggle");
    expect(drawerToggle.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(drawerToggle);
    expect(drawerToggle.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByTestId("iam-secops-locked-notice")).toBeDefined();
    expect((screen.getByTestId("create-rbac-grant-btn") as HTMLButtonElement).disabled).toBe(true);

    // 2. Grant SECOPS role to PLATFORM_ADMIN session -> unlocks exception form
    await waitFor(() => {
      useAuthSessionStore.getState().setAuthSession({
        roles: ["PLATFORM_ADMIN", "SECOPS"],
        activeHat: "PLATFORM_ADMIN",
      });
      expect(screen.queryByTestId("iam-secops-locked-notice")).toBeNull();
    });

    // Dynamic beneficiary label switches between Role and Account (closed <select>, zero free-text)
    expect(screen.getByTestId("rbac-subject-dynamic-label").textContent).toBe(
      "Rôle bénéficiaire",
    );
    fireEvent.change(screen.getByTestId("rbac-subject-type-select"), {
      target: { value: "USER" },
    });
    expect(screen.getByTestId("rbac-subject-dynamic-label").textContent).toBe(
      "Compte bénéficiaire",
    );
    expect(
      (screen.getByTestId("rbac-subject-select") as HTMLSelectElement).value,
    ).toBe("secops.admin@orcia.fr");

    // Pre-selected scope is the restricted BU ("dir-finance"), NOT "GLOBAL"; selecting "GLOBAL" triggers amber warning
    const scopeSelect = screen.getByTestId("rbac-scope-preset-select") as HTMLSelectElement;
    expect(scopeSelect.value).toBe("dir-finance");
    expect(screen.queryByTestId("iam-global-scope-amber-warning")).toBeNull();
    fireEvent.change(scopeSelect, { target: { value: "GLOBAL" } });
    expect(screen.getByTestId("iam-global-scope-amber-warning")).toBeDefined();
    fireEvent.change(scopeSelect, { target: { value: "dir-finance" } });
    expect(screen.queryByTestId("iam-global-scope-amber-warning")).toBeNull();

    // Auto-read dependency: while "execute" is checked, "read" is checked and locked!
    const readCheckbox = screen.getByTestId("rbac-verb-checkbox-read") as HTMLInputElement;
    const execCheckbox = screen.getByTestId("rbac-verb-checkbox-execute") as HTMLInputElement;
    expect(execCheckbox.checked).toBe(true);
    expect(readCheckbox.checked).toBe(true);
    expect(readCheckbox.disabled).toBe(true);

    // Unchecking "execute" unlocks "read"
    fireEvent.click(execCheckbox);
    expect(readCheckbox.disabled).toBe(false);
    // Re-checking "update" automatically re-checks and locks "read"
    fireEvent.click(screen.getByTestId("rbac-verb-checkbox-update"));
    expect(readCheckbox.checked).toBe(true);
    expect(readCheckbox.disabled).toBe(true);

    // Submit button is positioned AFTER the verb checkbox group in DOM order
    const verbsGroup = screen.getByTestId("rbac-verbs-checkbox-group");
    const submitBtn = screen.getByTestId("create-rbac-grant-btn");
    expect(
      Boolean(
        verbsGroup.compareDocumentPosition(submitBtn) & Node.DOCUMENT_POSITION_FOLLOWING,
      ),
    ).toBe(true);

    // Create an ISOLATE (INHERITANCE_BLOCK) exception on DATASOURCE family
    fireEvent.change(screen.getByTestId("rbac-resource-kind-select"), {
      target: { value: "DATASOURCE" },
    });
    fireEvent.change(screen.getByTestId("rbac-effect-select"), {
      target: { value: "INHERITANCE_BLOCK" },
    });
    fireEvent.click(submitBtn);

    const createdRow = await screen.findByTestId("rbac-grant-row-grant-1");
    expect(createdRow.textContent).toContain("secops.admin@orcia.fr");
    expect(createdRow.textContent).toContain("Sources documentaires uniquement");
    expect(createdRow.textContent).toContain("Périmètre isolé");

    // 3. F5 Page Reload Survival: unmount entire React tree and re-mount from scratch!
    firstMount.view.unmount();

    await mountSettingsHub("/settings");
    fireEvent.click(screen.getByTestId("settings-tab-iam"));
    expect(await screen.findByTestId("iam-account-row-acc-1")).toBeDefined();
    fireEvent.click(screen.getByTestId("iam-secops-drawer-toggle"));
    const persistedRow = await screen.findByTestId("rbac-grant-row-grant-1");
    expect(persistedRow.textContent).toContain("Périmètre isolé");
  });
});
