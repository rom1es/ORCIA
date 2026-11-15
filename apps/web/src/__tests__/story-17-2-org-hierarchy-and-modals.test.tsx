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

  it("creates multi-level BU -> Sous-BU -> TEAM hierarchy, edits, manages members, and survives F5", async () => {
    const firstMount = await renderOrganizationSettings();
    dismissFirstBootAdminIfOpen();
    await act(async () => Promise.resolve());

    // 1. Create Root BU ("Direction Produit")
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-name-input"), { target: { value: "Direction Produit" } });
    fireEvent.change(screen.getByTestId("org-unit-lead-input"), { target: { value: "vp.produit@orcia.fr" } });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    const rootRow = await screen.findByTestId("org-unit-row-org-1");
    expect(rootRow.getAttribute("data-depth")).toBe("0");
    const nameStrong = screen.getByTestId("org-unit-name-org-1");
    expect(nameStrong.textContent).toBe("Direction Produit");
    expect(nameStrong.className).toContain("text-base font-semibold tracking-tight");
    const leadBadge = screen.getByTestId("org-unit-lead-badge-org-1");
    expect(leadBadge.getAttribute("data-tone")).toBe("neutral");
    expect(screen.getByTestId("org-unit-kind-badge-org-1").getAttribute("data-tone")).toBe("cobalt");
    // BU has no direct members button nor members badge
    expect(screen.queryByTestId("manage-members-org-unit-btn-org-1")).toBeNull();
    expect(screen.queryByTestId("org-unit-members-count-org-1")).toBeNull();

    // 2. Create Sub-BU ("Pôle IA Générative", parent = org-1)
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-parent-select"), { target: { value: "org-1" } });
    fireEvent.change(screen.getByTestId("org-unit-name-input"), { target: { value: "Pôle IA Générative" } });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    expect((await screen.findByTestId("org-unit-row-org-2")).getAttribute("data-depth")).toBe("1");

    // 3. Create TEAM (parent = org-2)
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-level-select"), { target: { value: "TEAM" } });
    fireEvent.change(screen.getByTestId("org-unit-parent-select"), { target: { value: "org-2" } });
    fireEvent.change(screen.getByTestId("org-unit-name-input"), { target: { value: "Équipe Agents RAG" } });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    expect((await screen.findByTestId("org-unit-row-org-3")).getAttribute("data-depth")).toBe("2");
    expect(screen.getByTestId("manage-members-org-unit-btn-org-3")).toBeDefined();
    expect(screen.getByTestId("org-unit-members-count-org-3")).toBeDefined();

    // 4. Edit Sub-BU
    fireEvent.click(screen.getByTestId("edit-org-unit-btn-org-2"));
    fireEvent.change(screen.getByTestId("edit-org-unit-name-input"), { target: { value: "Pôle IA & Connaissances" } });
    fireEvent.click(screen.getByTestId("save-edit-org-unit-btn"));
    await act(async () => Promise.resolve());
    expect(screen.getByTestId("org-unit-row-org-2").textContent).toContain("Pôle IA & Connaissances");

    // 5. Delete modal blocked on non-empty unit
    fireEvent.click(screen.getByTestId("delete-org-unit-btn-org-2"));
    expect(screen.getByTestId("org-unit-delete-blocked-banner")).toBeDefined();
    expect((screen.getByTestId("confirm-delete-org-unit-btn-org-2") as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByTestId("cancel-delete-org-unit-btn-org-2"));

    // 6. F5 Survival
    firstMount.unmount();
    await renderOrganizationSettings();
    expect((await screen.findByTestId("org-unit-row-org-1")).getAttribute("data-depth")).toBe("0");
    expect(screen.getByTestId("org-unit-row-org-2").getAttribute("data-depth")).toBe("1");
    expect(screen.getByTestId("org-unit-row-org-3").getAttribute("data-depth")).toBe("2");
  });

  it("displays org-unit-delete-feedback when concurrent 409 is returned from API on delete", async () => {
    await renderOrganizationSettings();
    dismissFirstBootAdminIfOpen();
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-name-input"), { target: { value: "Direction Solitaire" } });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    await screen.findByTestId("org-unit-row-org-1");

    fireEvent.click(screen.getByTestId("delete-org-unit-btn-org-1"));
    vi.spyOn(orgUnitsApiBridge, "deleteOrgUnitViaApi").mockResolvedValueOnce({
      ok: false,
      errorMessage: "Suppression refusée pour « Direction Solitaire » : 1 espace rattaché.",
    });
    fireEvent.click(screen.getByTestId("confirm-delete-org-unit-btn-org-1"));
    const feedback = await screen.findByTestId("org-unit-delete-feedback");
    expect(feedback.textContent).toContain("Suppression refusée");
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

  it("autocompletes known users and strictly rejects unknown users in Create Org Unit modal", async () => {
    await renderOrganizationSettings();
    dismissFirstBootAdminIfOpen();
    await act(async () => Promise.resolve());

    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    const leadInput = screen.getByTestId("org-unit-lead-input");
    expect(leadInput.getAttribute("type")).toBe("search");
    expect(leadInput.getAttribute("name")).toBe("orcia_directory_filter_q");
    expect(leadInput.getAttribute("data-lpignore")).toBe("true");
    expect(leadInput.getAttribute("data-1p-ignore")).toBe("true");
    expect(leadInput.getAttribute("data-bwignore")).toBe("true");
    expect(leadInput.getAttribute("data-protonpass-ignore")).toBe("true");
    expect(leadInput.getAttribute("data-form-type")).toBe("other");
    expect(leadInput.getAttribute("placeholder")).toBe("Rechercher un membre par nom (ex. : Claire Martin)...");
    fireEvent.change(screen.getByTestId("org-unit-name-input"), { target: { value: "Pôle Sécurité" } });

    fireEvent.focus(leadInput);
    fireEvent.change(leadInput, { target: { value: "inconnu@orcia.fr" } });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    expect(screen.getByTestId("org-unit-unknown-user-error").textContent).toContain("aucun utilisateur");

    fireEvent.change(leadInput, { target: { value: "claire" } });
    const claireOption = await screen.findByTestId("org-unit-lead-input-option-claire.admin@orcia.fr");
    fireEvent.mouseDown(claireOption);
    expect(screen.getByTestId("org-unit-lead-input-pill-claire.admin@orcia.fr")).toBeDefined();

    // Add a second lead (Marc Lead) to verify multi-leads pills and plural badge
    fireEvent.change(leadInput, { target: { value: "marc" } });
    const marcOption = await screen.findByTestId("org-unit-lead-input-option-marc.lead@orcia.fr");
    fireEvent.mouseDown(marcOption);
    expect(screen.getByTestId("org-unit-lead-input-pill-marc.lead@orcia.fr")).toBeDefined();

    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    const row = await screen.findByTestId("org-unit-row-org-1");
    const leadBadge = screen.getByTestId("org-unit-lead-badge-org-1");
    expect(leadBadge.textContent).toContain("Responsables :");
    expect(leadBadge.textContent).toContain("Claire Admin");
    expect(leadBadge.textContent).toContain("Marc Lead");
  });

  it("enforces max 10 in parent selector with incremental query and anti-cycle", async () => {
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

    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    const trigger = screen.getByTestId("org-unit-parent-select-trigger");
    fireEvent.click(trigger);
    const listbox = screen.getByTestId("org-unit-parent-select-listbox");
    expect(within(listbox).getAllByRole("option")).toHaveLength(10);
    expect(screen.getByTestId("org-unit-parent-select-truncated-hint")).toBeDefined();

    const searchInput = screen.getByTestId("org-unit-parent-select-search-input");
    for (const token of ["d", "ds", "ds3"]) {
      await act(async () => { fireEvent.change(searchInput, { target: { value: token } }); });
    }
    const ds3cOption = await screen.findByTestId("org-unit-parent-select-option-bu-1");
    expect(ds3cOption.textContent).toContain("DS3C");
    fireEvent.click(screen.getByTestId("cancel-create-org-unit-btn"));
  });

  it("enforces combobox live search (ceiling 10) & chained IamAccountModal creation -> auto-attachment -> PATCH", async () => {
    seedVitestPlatformSetupState({
      org_units: [
        {
          id: "team-alpha",
          name: "Équipe Alpha",
          slug: "equipe-alpha",
          level: "TEAM",
          parentId: "scope-global",
          billingEnabled: true,
          leadUserId: null,
          memberUserIds: [],
          attachedWorkspacesCount: 0,
          attachedWorkspaces: [],
        },
      ],
    });

    await renderOrganizationSettings();
    dismissFirstBootAdminIfOpen();
    await act(async () => Promise.resolve());

    // 1. Open ManageOrgUnitMembersModal on team-alpha
    fireEvent.click(await screen.findByTestId("manage-members-org-unit-btn-team-alpha"));
    expect(screen.getByTestId("manage-org-unit-members-modal")).toBeDefined();

    // 2. Typing into member combobox triggers live search
    const memberInput = screen.getByTestId("org-unit-add-member-input");
    expect(memberInput.getAttribute("type")).toBe("search");
    expect(memberInput.getAttribute("name")).toBe("orcia_directory_filter_q");
    expect(memberInput.getAttribute("data-lpignore")).toBe("true");
    expect(memberInput.getAttribute("data-1p-ignore")).toBe("true");
    expect(memberInput.getAttribute("data-bwignore")).toBe("true");
    expect(memberInput.getAttribute("data-protonpass-ignore")).toBe("true");
    expect(memberInput.getAttribute("data-form-type")).toBe("other");
    expect(memberInput.getAttribute("placeholder")).toBe("Rechercher un collaborateur par nom...");
    fireEvent.focus(memberInput);
    fireEvent.change(memberInput, { target: { value: "nouveau.collaborateur@orcia.fr" } });
    await act(async () => Promise.resolve());

    // 3. Click "+ Nouveau membre" button -> opens chained IamAccountModal on top
    const newMemberBtn = screen.getByTestId("org-unit-new-member-btn");
    expect(newMemberBtn).toBeDefined();
    fireEvent.click(newMemberBtn);

    const iamModal = await screen.findByTestId("iam-account-modal");
    expect(iamModal).toBeDefined();
    // Prefill verification: draft contains "@" -> prefilled in principal/email input
    const principalInput = screen.getByTestId("iam-account-principal-input") as HTMLInputElement;
    expect(principalInput.value).toBe("nouveau.collaborateur@orcia.fr");

    // Provide display name
    fireEvent.change(screen.getByTestId("iam-account-display-name-input"), {
      target: { value: "Nouveau Collaborateur" },
    });

    // Submit IamAccountModal -> POST /api/v1/settings/iam/accounts
    fireEvent.click(screen.getByTestId("iam-account-modal-submit-btn"));
    await act(async () => Promise.resolve());

    // 4. IamAccountModal is closed, ManageOrgUnitMembersModal is STILL open
    expect(screen.queryByTestId("iam-account-modal")).toBeNull();
    expect(screen.getByTestId("manage-org-unit-members-modal")).toBeDefined();

    // 5. Newly created member is automatically attached in members list
    expect(
      await screen.findByTestId("org-unit-member-item-nouveau.collaborateur@orcia.fr"),
    ).toBeDefined();

    // 6. Save members -> calls PATCH /api/v1/org-units/team-alpha
    fireEvent.click(screen.getByTestId("save-org-unit-members-btn"));
    await act(async () => Promise.resolve());

    // 7. Team row reflects updated count
    expect(
      (await screen.findByTestId("org-unit-members-count-team-alpha")).textContent,
    ).toContain("1 membre");
  });
});
