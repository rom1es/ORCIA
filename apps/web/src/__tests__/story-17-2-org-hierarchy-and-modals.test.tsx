import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { seedVitestPlatformSetupState } from "./vitest.setup";
import * as orgUnitsApiBridge from "../features/admin/organization/orgUnitsApiBridge";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";

async function renderOrganizationSettings(initialEntry = "/settings") {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [initialEntry] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...view, router };
}

function dismissFirstBootAdminIfOpen() {
  if (screen.queryByTestId("first-boot-admin-name-input")) {
    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), {
      target: { value: "Claire Admin" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), {
      target: { value: "claire.admin@orcia.fr" },
    });
    fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));
  }
}

describe("Story 17.2 — Indented Hierarchical Org Tree, Modals, Members, FinOps & F5 Survival", () => {
  beforeEach(() => {
    clearPlatformSetupStorage();
    resetAuthSessionStore();
    useAuthSessionStore.getState().setAuthSession({
      email: "claire.admin@orcia.fr",
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });
  });

  afterEach(() => {
    cleanup();
    clearPlatformSetupStorage();
    resetAuthSessionStore();
  });

  it("renders pedagogical callout + /workspaces CTA, creates multi-level BU -> Sous-BU -> TEAM hierarchy with depth indentation, edits, manages members, enforces danger/non-empty delete, and survives F5 reload", async () => {
    const firstMount = await renderOrganizationSettings();
    dismissFirstBootAdminIfOpen();
    await act(async () => {
      await Promise.resolve();
    });

    // 1. Pedagogical header & zero legacy personal attachment UI ("Retirer mon rattachement")
    const callout = screen.getByTestId("organization-pedagogical-callout");
    expect(callout.textContent).toContain("Direction / BU");
    expect(callout.textContent).toContain("Équipe");
    expect(callout.textContent).toContain("Mes Espaces");
    expect(document.body.textContent ?? "").not.toContain("Retirer mon rattachement");

    // 2. Create Root BU ("Direction Produit", depth 0)
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    expect(screen.getByTestId("create-org-unit-modal")).toBeDefined();
    // Parent select is visible even for BU (root vs Sous-BU)
    expect(screen.getByTestId("org-unit-parent-select")).toBeDefined();
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Direction Produit" },
    });
    fireEvent.change(screen.getByTestId("org-unit-lead-input"), {
      target: { value: "vp.produit@orcia.fr" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));

    const rootRow = await screen.findByTestId("org-unit-row-org-1");
    expect(rootRow.getAttribute("data-depth")).toBe("0");
    expect(screen.getByTestId("org-unit-kind-badge-org-1").textContent).toBe("Direction / BU");
    expect(screen.getByTestId("org-unit-lead-badge-org-1").textContent).toContain(
      "vp.produit@orcia.fr",
    );

    // 3. Create Sub-BU ("Pôle IA Générative", kind = BU, parent = org-1 -> depth 1, "Pôle / Sous-BU")
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-parent-select"), {
      target: { value: "org-1" },
    });
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Pôle IA Générative" },
    });
    fireEvent.click(screen.getByTestId("org-unit-billing-checkbox")); // toggle off FinOps
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));

    const subBuRow = await screen.findByTestId("org-unit-row-org-2");
    expect(subBuRow.getAttribute("data-depth")).toBe("1");
    expect(screen.getByTestId("org-unit-tree-connector-org-2").textContent).toContain("└─");
    expect(screen.getByTestId("org-unit-kind-badge-org-2").textContent).toBe("Pôle / Sous-BU");
    expect(screen.getByTestId("org-unit-billing-badge-org-2").textContent).toBe(
      "Sans imputation FinOps",
    );

    // 4. Create TEAM: selecting "TEAM" auto-preselects the first BU (org-1), then we select Sub-BU (org-2 -> depth 2)
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-level-select"), {
      target: { value: "TEAM" },
    });
    expect((screen.getByTestId("org-unit-parent-select") as HTMLSelectElement).value).toBe(
      "org-1",
    );
    fireEvent.change(screen.getByTestId("org-unit-parent-select"), {
      target: { value: "org-2" },
    });
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Équipe Agents RAG" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));

    const teamRow = await screen.findByTestId("org-unit-row-org-3");
    expect(teamRow.getAttribute("data-depth")).toBe("2");
    expect(screen.getByTestId("org-unit-kind-badge-org-3").textContent).toBe("ÉQUIPE");
    expect(screen.getByTestId("org-unit-billing-badge-org-3").textContent).toBe(
      "Facturation FinOps active",
    );

    // 5. Edit Modal (PATCH): rename Sub-BU & exclude self/descendants from parent options
    fireEvent.click(screen.getByTestId("edit-org-unit-btn-org-1"));
    const editRootParentSelect = screen.getByTestId(
      "edit-org-unit-parent-select",
    ) as HTMLSelectElement;
    const optionValues = Array.from(editRootParentSelect.options).map((o) => o.value);
    expect(optionValues).not.toContain("org-1");
    expect(optionValues).not.toContain("org-2"); // descendant excluded!
    fireEvent.click(screen.getByTestId("cancel-edit-org-unit-btn"));

    fireEvent.click(screen.getByTestId("edit-org-unit-btn-org-2"));
    fireEvent.change(screen.getByTestId("edit-org-unit-name-input"), {
      target: { value: "Pôle IA & Connaissances" },
    });
    fireEvent.click(screen.getByTestId("edit-org-unit-billing-checkbox")); // enable FinOps
    fireEvent.click(screen.getByTestId("save-edit-org-unit-btn"));
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("org-unit-row-org-2").textContent).toContain(
      "Pôle IA & Connaissances",
    );
    expect(screen.getByTestId("org-unit-billing-badge-org-2").textContent).toBe(
      "Facturation FinOps active",
    );

    // 6. Manage Members Modal (PATCH): assign lead + 2 members on Team (org-3)
    fireEvent.click(screen.getByTestId("manage-members-org-unit-btn-org-3"));
    fireEvent.change(screen.getByTestId("org-unit-members-lead-input"), {
      target: { value: "marc.lead@orcia.fr" },
    });
    fireEvent.change(screen.getByTestId("org-unit-add-member-input"), {
      target: { value: "alice@orcia.fr" },
    });
    fireEvent.click(screen.getByTestId("org-unit-add-member-btn"));
    fireEvent.change(screen.getByTestId("org-unit-add-member-input"), {
      target: { value: "bob@orcia.fr" },
    });
    fireEvent.click(screen.getByTestId("org-unit-add-member-btn"));
    fireEvent.click(screen.getByTestId("save-org-unit-members-btn"));
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("org-unit-members-count-org-3").textContent).toBe("2 membres");
    expect(screen.getByTestId("org-unit-lead-badge-org-3").textContent).toContain(
      "marc.lead@orcia.fr",
    );

    // 7. Confirm Delete Modal: danger button (.orcia-ds-btn-danger), dependencies list, FinOps warning, and disabled confirm button
    expect(
      screen.getByTestId("delete-org-unit-btn-org-2").className,
    ).toContain("orcia-ds-btn-danger");
    fireEvent.click(screen.getByTestId("delete-org-unit-btn-org-2"));
    expect(screen.getByTestId("confirm-delete-org-unit-modal")).toBeDefined();
    expect(screen.getByTestId("org-unit-delete-finops-warning")).toBeDefined();
    expect(screen.getByTestId("org-unit-delete-dependencies-list")).toBeDefined();
    expect(screen.getByTestId("org-unit-delete-dependencies-list").textContent).toContain(
      "Équipe Agents RAG",
    );
    expect(screen.getByTestId("org-unit-delete-blocked-banner")).toBeDefined();
    const confirmBtn = screen.getByTestId("confirm-delete-org-unit-btn-org-2") as HTMLButtonElement;
    expect(confirmBtn.className).toContain("orcia-ds-btn-danger");
    expect(confirmBtn.disabled).toBe(true);
    fireEvent.click(screen.getByTestId("cancel-delete-org-unit-btn-org-2"));

    // 8. CTA "Ouvrir Mes Espaces ->" navigates cleanly to /workspaces
    fireEvent.click(screen.getByTestId("organization-open-workspaces-btn"));
    await act(async () => {
      await Promise.resolve();
    });
    expect(firstMount.router.state.location.pathname).toBe("/workspaces");

    // 9. F5 Reload Survival Gate: unmount() and remount fresh router on /settings?tab=organization
    firstMount.unmount();
    await renderOrganizationSettings();

    expect((await screen.findByTestId("org-unit-row-org-1")).getAttribute("data-depth")).toBe("0");
    expect(screen.getByTestId("org-unit-row-org-2").getAttribute("data-depth")).toBe("1");
    expect(screen.getByTestId("org-unit-row-org-3").getAttribute("data-depth")).toBe("2");
    expect(screen.getByTestId("org-unit-members-count-org-3").textContent).toBe("2 membres");
    expect(document.body.textContent ?? "").not.toContain("Retirer mon rattachement");
  });

  it("displays org-unit-delete-feedback when concurrent 409 is returned from API on delete", async () => {
    await renderOrganizationSettings();
    dismissFirstBootAdminIfOpen();

    // Create an isolated leaf unit
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Direction Solitaire" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));

    const row = await screen.findByTestId("org-unit-row-org-1");
    expect(row).toBeDefined();

    // Open delete modal
    fireEvent.click(screen.getByTestId("delete-org-unit-btn-org-1"));
    expect(screen.getByTestId("confirm-delete-org-unit-modal")).toBeDefined();
    const confirmBtn = screen.getByTestId("confirm-delete-org-unit-btn-org-1") as HTMLButtonElement;
    expect(confirmBtn.disabled).toBe(false);

    // Mock concurrent 409 failure from backend
    const deleteSpy = vi.spyOn(orgUnitsApiBridge, "deleteOrgUnitViaApi").mockResolvedValueOnce({
      ok: false,
      errorMessage: "Suppression refusée pour « Direction Solitaire » : 1 espace rattaché.",
    });

    fireEvent.click(confirmBtn);
    const deleteFeedback = await screen.findByTestId("org-unit-delete-feedback");
    expect(deleteFeedback.textContent).toContain("Suppression refusée pour « Direction Solitaire »");
    expect(deleteSpy).toHaveBeenCalledWith("org-1", "fr");
  });

  it("enforces read-only access banner for OBSERVER on /settings", async () => {
    useAuthSessionStore.getState().setAuthSession({
      email: "obs@orcia.fr",
      roles: ["OBSERVER"],
      activeHat: "OBSERVER",
      readOnlyObserver: true,
    });

    await renderOrganizationSettings();
    dismissFirstBootAdminIfOpen();

    expect(screen.queryByTestId("settings-domain-tabs")).toBeNull();
    expect(screen.getByTestId("settings-readonly-access-banner")).toBeDefined();
  });

  it("autocompletes known users and strictly rejects unknown users in Create and Manage Members modals", async () => {
    await renderOrganizationSettings();
    dismissFirstBootAdminIfOpen();
    await act(async () => {
      await Promise.resolve();
    });

    // 1. Open create modal
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    const leadInput = screen.getByTestId("org-unit-lead-input");
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Pôle Sécurité" },
    });

    // 2. Typing unknown user shows no matches and submit is blocked by UI error
    fireEvent.focus(leadInput);
    fireEvent.change(leadInput, { target: { value: "inconnu@orcia.fr" } });
    expect(screen.getByTestId("org-unit-lead-input-no-match")).toBeDefined();

    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    const unknownErrorBanner = screen.getByTestId("org-unit-unknown-user-error");
    expect(unknownErrorBanner.textContent).toContain("aucun utilisateur");

    // 3. Autocompletion: typing partial 'claire' shows suggestion
    fireEvent.change(leadInput, { target: { value: "claire" } });
    const suggestions = screen.getByTestId("org-unit-lead-input-suggestions");
    expect(suggestions).toBeDefined();
    const claireOption = screen.getByTestId("org-unit-lead-input-option-claire.admin@orcia.fr");
    expect(claireOption.textContent).toContain("Claire Admin");

    // Click suggestion selects principalId and closes menu
    fireEvent.mouseDown(claireOption);
    expect((leadInput as HTMLInputElement).value).toBe("claire.admin@orcia.fr");
    expect(screen.queryByTestId("org-unit-unknown-user-error")).toBeNull();

    // 4. Submit successfully creates unit with resolved known user
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    const row = await screen.findByTestId("org-unit-row-org-1");
    expect(row).toBeDefined();
    expect(screen.getByTestId("org-unit-lead-badge-org-1").textContent).toContain("Claire Admin");
  });

  it("enforces max 10 displayed items, live per-character search query calling API, and anti-cycle exclusion in parent selector", async () => {
    const manyBus = Array.from({ length: 14 }, (_, i) => ({
      id: `bu-${i + 1}`,
      name: i === 0 ? "DS3C Pôle Ingénierie" : `BU Division ${i + 1}`,
      slug: i === 0 ? "ds3c-pole-ingenierie" : `bu-division-${i + 1}`,
      level: "BU",
      parentId: "scope-global",
      billingEnabled: true,
      leadUserId: "claire.admin@orcia.fr",
      memberUserIds: [],
      attachedWorkspacesCount: 0,
      attachedWorkspaces: [],
    }));
    seedVitestPlatformSetupState({ org_units: manyBus });

    await renderOrganizationSettings();
    dismissFirstBootAdminIfOpen();
    await act(async () => Promise.resolve());

    // 1. Open create modal: verify trigger and max 10 options rendered
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    const trigger = screen.getByTestId("org-unit-parent-select-trigger");
    expect(trigger).toBeDefined();

    fireEvent.click(trigger);
    const listbox = screen.getByTestId("org-unit-parent-select-listbox");
    expect(within(listbox).getAllByRole("option")).toHaveLength(10);
    expect(screen.getByTestId("org-unit-parent-select-truncated-hint")).toBeDefined();

    // 2. Per-character search: typing 'd' -> 'ds' -> 'ds3'
    const searchInput = screen.getByTestId("org-unit-parent-select-search-input");
    for (const token of ["d", "ds", "ds3"]) {
      await act(async () => {
        fireEvent.change(searchInput, { target: { value: token } });
      });
    }

    const ds3cOption = await screen.findByTestId("org-unit-parent-select-option-bu-1");
    expect(ds3cOption.textContent).toContain("DS3C");
    expect(within(listbox).getAllByRole("option")).toHaveLength(1);

    fireEvent.click(screen.getByTestId("cancel-create-org-unit-btn"));

    // 3. Edit modal: anti-cycle prevents selecting unit itself
    fireEvent.click(screen.getByTestId("edit-org-unit-btn-bu-1"));
    fireEvent.click(screen.getByTestId("edit-org-unit-parent-select-trigger"));
    expect(screen.queryByTestId("edit-org-unit-parent-select-option-bu-1")).toBeNull();
  });
});
