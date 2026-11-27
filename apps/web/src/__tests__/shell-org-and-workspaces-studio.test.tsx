import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import {
  completeFirstBootAdminModal,
  createOrgUnitViaModal,
  createWorkspaceViaModal,
  renderOrciaRoute,
  resetShellTestState,
} from "./setup/shellTestHelpers";
import { seedVitestPlatformSetupState } from "./vitest.setup";

describe("@orcia/web Organization hierarchy, Workspaces studio, and F5 survival", () => {
  beforeEach(() => {
    resetShellTestState();
  });

  it("guides workspace creation from /workspaces and dynamically unlocks workspace-scoped modules and runs", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.fr", displayName: "Admin", roles: ["PLATFORM_ADMIN"] });
    const { router } = await renderOrciaRoute("/workspaces");

    expect(screen.getByTestId("workspaces-cards-empty-state")).toBeDefined();
    expect((screen.getByTestId("eight-menu-item-finops") as HTMLButtonElement).disabled).toBe(true);

    await createWorkspaceViaModal({ name: "Mon Premier Espace" });
    await waitFor(() => {
      expect((screen.getByTestId("eight-menu-item-finops") as HTMLButtonElement).disabled).toBe(false);
    });

    await act(async () => {
      await router.navigate({ to: "/cockpit" });
    });
    expect(screen.getByTestId("accostage-progress-pill").textContent).toBe("3 / 6 complétées");
    expect(screen.getByTestId("cockpit-launch-run-form")).toBeDefined();
  });

  it("supports Day-0 1st Admin 2-step onboarding (Option 1), multi-team membership, Private Workspaces billed to a Team (Option 2 FinOps), orphan-safe Team deletion, and 3-group TopHeader context switcher", async () => {
    await renderOrciaRoute("/settings");
    await completeFirstBootAdminModal();

    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    expect(await screen.findByTestId("iam-org-units-empty-state")).toBeDefined();
    expect(screen.queryByTestId("admin-team-membership-summary-badge")).toBeNull();

    fireEvent.click(screen.getByTestId("topbar-notifications-toggle"));
    expect(screen.getByTestId("notification-center-item-setup-billing-team-missing").textContent).toContain("Aucune Équipe de facturation rattachée");
    fireEvent.click(screen.getByTestId("topbar-notifications-close"));

    await createOrgUnitViaModal({ name: "Direction Produit", expectedRowTestId: "org-unit-row-org-1" });
    await screen.findByTestId("open-create-org-unit-modal-btn");
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-level-select"), { target: { value: "TEAM" } });
    expect(screen.queryByTestId("org-unit-attach-admin-checkbox")).toBeNull();
    fireEvent.change(screen.getByTestId("org-unit-name-input"), { target: { value: "Équipe Core IA" } });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    await screen.findByTestId("org-unit-row-org-2");
    expect(screen.getByTestId("org-unit-row-org-2").textContent).toContain("Équipe Core IA");
    expect(screen.getByTestId("org-unit-billing-badge-org-2").textContent).toContain("Facturation FinOps active");

    await createOrgUnitViaModal({ name: "Équipe Data", level: "TEAM", expectedRowTestId: "org-unit-row-org-3" });
    expect(screen.getByTestId("org-unit-row-org-3").textContent).toContain("Équipe Data");
    expect(screen.getByTestId("org-unit-billing-badge-org-3").textContent).toContain("Facturation FinOps active");

    fireEvent.click(screen.getByTestId("manage-members-org-unit-btn-org-2"));
    expect(screen.getByTestId("org-unit-add-member-input")).toBeDefined();
    fireEvent.change(screen.getByTestId("org-unit-add-member-input"), { target: { value: "romain@orcia.fr" } });
    fireEvent.click(screen.getByTestId("org-unit-add-member-btn"));
    fireEvent.click(screen.getByTestId("save-org-unit-members-btn"));
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByTestId("org-unit-members-count-org-2").textContent).toContain("1 membre");
    expect(screen.getByTestId("org-unit-row-org-1").textContent).toContain("Direction Produit");
    expect(screen.getByTestId("manage-members-org-unit-btn-org-2")).toBeDefined();

    fireEvent.click(screen.getByTestId("eight-menu-item-spaces"));
    await act(async () => { await Promise.resolve(); });

    fireEvent.click(screen.getByTestId("toggle-create-workspace-form-btn"));
    const createWsBtn = screen.getByTestId("create-workspace-submit-btn") as HTMLButtonElement;
    expect(createWsBtn.disabled).toBe(true);
    expect(screen.getByTestId("disabled-button-alert-icon-create-workspace-submit-btn")).toBeDefined();

    const ownerTeamSelect = screen.getByTestId("workspace-owner-team-select") as HTMLSelectElement;
    expect(ownerTeamSelect.textContent).toContain("Équipe Core IA");
    expect(ownerTeamSelect.textContent).toContain("Équipe Data");
    fireEvent.change(ownerTeamSelect, { target: { value: "org-2" } });
    const visibilitySelect = screen.getByTestId("workspace-visibility-select") as HTMLSelectElement;
    expect(visibilitySelect.textContent).toContain("Privé personnel (Facturé à l'équipe)");
    fireEvent.change(visibilitySelect, { target: { value: "PRIVATE_USER" } });
    fireEvent.change(screen.getByTestId("workspace-name-input"), { target: { value: "Mon Bac à Sable R&D" } });
    expect(createWsBtn.disabled).toBe(false);
    fireEvent.click(createWsBtn);
    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Mon Bac à Sable R&D");
    });

    await createWorkspaceViaModal({ name: "Projet Socle IA", visibility: "STANDARD", ownerTeamId: "org-2" });
    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Projet Socle IA");
    });
    expect(screen.getByTestId("sidebar-workspace-selector").textContent).toContain("Projet Socle IA");
    expect(screen.getByTestId("sidebar-workspace-selector").textContent).toContain("Mon Bac à Sable R&D");

    fireEvent.click(screen.getByTestId("sidebar-rail-toggle-btn"));
    fireEvent.click(screen.getByTestId("topbar-fixed-workspace-selector"));
    const dropdownMenu = screen.getByTestId("topbar-workspace-dropdown-menu");
    expect(dropdownMenu.textContent).toContain("Mes Espaces Privés");
    expect(dropdownMenu.textContent).toContain("Mes Équipes & Espaces");
    expect(dropdownMenu.textContent).toContain("Supervision Organisation");
    expect(dropdownMenu.textContent).toContain("Équipe · Équipe Core IA");
    expect(dropdownMenu.textContent).toContain("Espace privé · Mon Bac à Sable R&D · Équipe Core IA");
    expect(dropdownMenu.textContent).toContain("Espace · Projet Socle IA · Équipe Core IA");

    const privateOption = screen.getAllByTestId(/^topbar-workspace-option-/).find((el) => el.textContent?.includes("Mon Bac à Sable R&D"));
    expect(privateOption).toBeDefined();
    expect(privateOption?.getAttribute("data-testid")).not.toBe("topbar-workspace-option-ws-1");
    fireEvent.click(privateOption!);
    expect(screen.getByTestId("topbar-fixed-workspace-selector").textContent).toContain("Mon Bac à Sable R&D");
    fireEvent.click(screen.getByTestId("sidebar-rail-toggle-btn"));
    expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Mon Bac à Sable R&D");

    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    await screen.findByTestId("delete-org-unit-btn-org-2");
    fireEvent.click(screen.getByTestId("delete-org-unit-btn-org-2"));
    expect((screen.getByTestId("confirm-delete-org-unit-btn-org-2") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByTestId("org-unit-delete-blocked-banner").textContent).toContain("2 Espaces de Travail rattachés");
    expect(screen.getByTestId("org-unit-row-org-2")).toBeDefined();
    fireEvent.click(screen.getByTestId("cancel-delete-org-unit-btn-org-2"));
    expect(screen.queryByTestId("org-unit-delete-blocked-banner")).toBeNull();
  });

  it("delivers the redesigned Workspaces studio view with quick filters, 1-click private-to-team sharing, inline datasource connection, integrated multi-level Glossary & Business Rules with 1-click promotion, F5 reload survival, and Option A (no visible 📖 Vocabulaire in sidebar)", async () => {
    const { unmount } = await renderOrciaRoute("/settings");
    expect(screen.queryByTestId("eight-menu-item-vocabulary")).toBeNull();
    await completeFirstBootAdminModal();

    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    await createOrgUnitViaModal({ name: "Équipe Produit IA", level: "TEAM", expectedRowTestId: "org-unit-row-org-1" });
    expect(screen.queryByTestId("settings-tab-glossary")).toBeNull();

    fireEvent.click(screen.getByTestId("eight-menu-item-spaces"));
    await act(async () => { await Promise.resolve(); });
    expect(screen.queryByTestId("workspaces-legacy-technical-panels")).toBeNull();

    await createWorkspaceViaModal({ name: "Mon Labo Perso", visibility: "PRIVATE_USER" });
    await waitFor(() => { expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Mon Labo Perso"); });
    const toggleCreateBtn = screen.getByTestId("toggle-create-workspace-form-btn");
    expect(toggleCreateBtn.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByTestId("workspace-name-input")).toBeNull();

    await createWorkspaceViaModal({ name: "Espace Produit", visibility: "STANDARD" });
    await waitFor(() => { expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Espace Produit"); });

    const sidebarSwitcher = screen.getByTestId("sidebar-workspace-selector") as HTMLSelectElement;
    const switcherOptions = Array.from(sidebarSwitcher.options);
    const ws1Opt = switcherOptions.find((o) => o.textContent?.includes("Mon Labo Perso"));
    const ws2Opt = switcherOptions.find((o) => o.textContent?.includes("Espace Produit"));
    expect(ws1Opt).toBeDefined();
    expect(ws2Opt).toBeDefined();
    const ws1Id = ws1Opt!.value;
    const ws2Id = ws2Opt!.value;
    expect(ws1Id).not.toBe("ws-1");
    expect(ws2Id).not.toBe("ws-2");
    expect(ws1Id).toMatch(/^[0-9a-f-]{36}$/);
    expect(ws2Id).toMatch(/^[0-9a-f-]{36}$/);
    expect(screen.queryByTestId("workspaces-active-switcher-select")).toBeNull();
    fireEvent.change(sidebarSwitcher, { target: { value: ws1Id } });
    await waitFor(() => { expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Mon Labo Perso"); });

    expect(screen.queryByTestId(`workspace-card-phase-select-${ws1Id}`)).toBeNull();
    expect(screen.queryByTestId(`share-private-workspace-btn-${ws1Id}`)).toBeNull();
    fireEvent.click(screen.getByTestId("workspace-tab-MEMBERS_TEAM"));
    expect(((await screen.findByTestId(`workspace-card-visibility-select-${ws1Id}`)) as HTMLSelectElement).disabled).toBe(true);
    expect(screen.getByTestId(`workspace-visibility-badge-${ws1Id}`).textContent).toContain("Personnel");

    expect(screen.queryByTestId("workspace-detail-tabs-panel")).toBeNull();
    fireEvent.click(screen.getByTestId("workspace-tab-DOCUMENTS_SOURCES"));
    expect(screen.getByTestId("workspace-sources-empty-state")).toBeDefined();
    expect(screen.queryByTestId("sources-filter-pill-all")).toBeNull();
    fireEvent.click(screen.getByTestId("open-attach-source-modal-btn"));
    expect(screen.getByTestId("workspace-source-attach-modal")).toBeDefined();
    await waitFor(() => { expect((screen.getByTestId("modal-source-nature-select") as HTMLSelectElement).value).toBe("SOURCE_CODE"); });
    fireEvent.change(screen.getByTestId("modal-source-alias-input"), { target: { value: "Wiki Produit Interne" } });
    fireEvent.change(screen.getByTestId("modal-source-uri-input"), { target: { value: "https://confluence.orcia.fr/spaces/PROD" } });
    fireEvent.click(screen.getByTestId("modal-source-save-btn"));
    await waitFor(() => {
      expect(screen.getAllByText("Wiki Produit Interne").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByTestId("sources-filter-pill-all")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("workspace-tab-GLOSSARY_RULES"));
    const cascadeBar = screen.getByTestId("glossary-inheritance-cascade-bar");
    expect(cascadeBar.querySelectorAll("svg").length).toBeGreaterThanOrEqual(1);
    expect(cascadeBar.textContent).toContain("Entreprise (Global)");
    expect(cascadeBar.textContent).toContain("Direction (BU)");
    expect(cascadeBar.textContent).toContain("Équipe (Équipe Produit IA)");
    expect(cascadeBar.textContent).toContain("Cet Espace (Mon Labo Perso)");
    expect(cascadeBar.textContent).not.toContain("1_ENTERPRISE");
    expect(cascadeBar.textContent).not.toContain("3_WORKSPACE");

    fireEvent.change(screen.getByTestId("workspace-glossary-term-input"), { target: { value: "Marge Brute Récurrente" } });
    fireEvent.change(screen.getByTestId("workspace-glossary-definition-input"), { target: { value: "Revenu récurrent mensuel diminué des coûts directs d'infrastructure IA." } });
    fireEvent.click(screen.getByTestId("workspace-glossary-submit-btn"));
    const conceptSlug = `4-workspace-${ws1Id}-marge-brute-r-currente`;
    expect((await screen.findByTestId(`glossary-concept-card-${conceptSlug}`)).textContent).toContain("Marge Brute Récurrente");
    expect(screen.getByTestId(`glossary-concept-level-badge-${conceptSlug}`).textContent).toContain("Mon Labo Perso");

    fireEvent.click(screen.getByTestId(`promote-glossary-concept-btn-${conceptSlug}`));
    await waitFor(() => {
      expect(screen.getByTestId(`promoted-glossary-badge-${conceptSlug}`).textContent).toContain("En attente de validation");
    });

    fireEvent.click(screen.getByTestId("workspace-tab-MEMBERS_TEAM"));
    fireEvent.change(screen.getByTestId("workspace-instructions-textarea"), { target: { value: "Toujours citer la source Wiki Produit Interne." } });
    await waitFor(() => { expect(screen.getByTestId("workspace-instructions-saved-badge").textContent).toContain("Enregistré"); });

    unmount();
    await renderOrciaRoute("/workspaces");
    expect(screen.getByTestId(`workspace-visibility-badge-${ws1Id}`).textContent).toContain("Personnel");
    fireEvent.click(screen.getByTestId("workspace-tab-DOCUMENTS_SOURCES"));
    await waitFor(() => { expect(screen.getByTestId("workspace-detail-source-row-ds-1").textContent).toContain("Wiki Produit Interne"); });
    fireEvent.click(screen.getByTestId("workspace-tab-GLOSSARY_RULES"));
    await waitFor(() => {
      expect(screen.getByTestId(`glossary-concept-level-badge-${conceptSlug}`).textContent).toContain("Mon Labo Perso");
      expect(screen.getByTestId(`promoted-glossary-badge-${conceptSlug}`).textContent).toContain("En attente de validation");
    });
  });
});
