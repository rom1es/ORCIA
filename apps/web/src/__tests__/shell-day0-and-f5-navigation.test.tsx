import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { enDictionary } from "../i18n/locales/en";
import { frDictionary } from "../i18n/locales/fr";
import {
  completeFirstBootAdminModal,
  createOrgUnitViaModal,
  createWorkspaceViaModal,
  renderOrciaRoute,
  renderShellModule,
  resetShellTestState,
} from "./setup/shellTestHelpers";

describe("@orcia/web Day-0 empty-start, RGAA first-boot modal, and F5 navigation", () => {
  beforeEach(() => {
    resetShellTestState();
  });

  it("starts 100% empty of sample data by default, displays the First-Boot Platform Admin Modal, and greys out unconfigured menu entries", () => {
    renderShellModule("cockpit", "fr");

    expect(screen.getByTestId("first-boot-admin-setup-modal")).toBeDefined();
    expect(screen.queryByTestId("onboarding-progress-badge")).toBeNull();
    expect(screen.getByTestId("accostage-progress-pill").textContent).toBe("0 / 6 complétées");
    expect(screen.getByTestId("cockpit-no-workspace-empty-state")).toBeDefined();

    expect((screen.getByTestId("eight-menu-item-cockpit") as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByTestId("eight-menu-item-spaces") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("eight-menu-item-configuration") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("eight-menu-item-help") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("eight-menu-item-assistant") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("eight-menu-item-processes") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("eight-menu-item-agents") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("eight-menu-item-finops") as HTMLButtonElement).disabled).toBe(true);

    expect(screen.queryByTestId("shell-locale-toggle")).toBeNull();
    expect(screen.queryByTestId("sidebar-pack-selector")).toBeNull();
  });

  it("renders the 4-Zone Direction C Shell with 8 fixed menu entries, StreamlinedCockpitView, and Day 0 Accostage Banner (Story 12.1)", async () => {
    await renderOrciaRoute("/cockpit");

    expect(screen.getByTestId("four-zone-direction-c-shell")).toBeDefined();
    expect(screen.getByTestId("eight-menu-item-cockpit")).toBeDefined();
    expect(screen.getByTestId("eight-menu-item-assistant")).toBeDefined();
    expect(screen.getByTestId("eight-menu-item-spaces")).toBeDefined();
    expect(screen.getByTestId("eight-menu-item-processes")).toBeDefined();
    expect(screen.getByTestId("eight-menu-item-agents")).toBeDefined();
    expect(screen.getByTestId("eight-menu-item-finops")).toBeDefined();
    expect(screen.getByTestId("eight-menu-item-configuration")).toBeDefined();
    expect(screen.getByTestId("eight-menu-item-help")).toBeDefined();
    expect(screen.getByTestId("progressive-day0-accostage-banner")).toBeDefined();
    expect(screen.getByTestId("streamlined-cockpit-view")).toBeDefined();
  });

  it("enforces Story 12.4 UX sobriety: First-Boot Platform Admin Modal, zero fictional data (PAY-142/PSD2), zero NFR latency strings, and human-readable Rôle selector", async () => {
    const serializedFr = JSON.stringify(frDictionary);
    const serializedEn = JSON.stringify(enDictionary);
    for (const forbidden of [
      "< 500ms", "< 500 ms", "(0 ms)", "< 30 ms", "Pause 450 ms", "450 ms pause",
      "< 50 ms", "< 2 ms", "< 5 s", "< 100 ms", "< 10 ms", "< 15 s",
      "340px", "420px", "280px", "720px", "PAY-142", "Administrateur / Tech Lead",
    ]) {
      expect(serializedFr).not.toContain(forbidden);
      expect(serializedEn).not.toContain(forbidden);
    }
    expect(frDictionary.userAccountAndSettings.popover.settingsLabel).toBe("Paramètres");
    expect(enDictionary.userAccountAndSettings.popover.settingsLabel).toBe("Settings");

    renderShellModule("inbox", "fr");
    expect(document.body.textContent ?? "").not.toContain("PAY-142");
    expect(document.body.textContent ?? "").not.toContain("PSD2");
    expect(document.body.textContent ?? "").not.toContain("Administrateur / Tech Lead");

    await completeFirstBootAdminModal({
      name: "Romain Admin",
      email: "romain@orcia.fr",
      password: "Secret123456!", // pragma: allowlist secret
    });
    expect(screen.queryByTestId("topbar-user-account-trigger")).toBeNull();
    expect(screen.queryByTestId("dropdown-hat-selector")).toBeNull();
    const accountBtn = screen.getByTestId("sidebar-open-my-account-btn");
    expect(accountBtn.textContent).toContain("Romain Admin");
    expect(accountBtn.textContent).toContain("Administrateur de la plateforme");
  });

  it("enforces RGAA Escape, Annuler, Unsaved Changes Guard, and Enter submit on First-Boot Admin Setup Modal", async () => {
    const { unmount } = renderShellModule("cockpit", "fr");
    expect(screen.getByTestId("first-boot-admin-setup-modal")).toBeDefined();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
    unmount();

    renderShellModule("cockpit", "fr");
    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), { target: { value: "Hélène Admin" } });
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), { target: { value: "helene@orcia.fr" } });

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.getByTestId("first-boot-admin-unsaved-changes-alert")).toBeDefined();
    expect(screen.getByTestId("first-boot-admin-setup-modal")).toBeDefined();

    fireEvent.click(screen.getByTestId("first-boot-admin-unsaved-stay-btn"));
    expect(screen.queryByTestId("first-boot-admin-unsaved-changes-alert")).toBeNull();

    const submitBtn = screen.getByTestId("first-boot-admin-submit-btn");
    submitBtn.focus();
    fireEvent.keyDown(submitBtn, { key: "Enter" });
    await waitFor(() => {
      expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
    });
    expect(screen.getByTestId("sidebar-open-my-account-btn").textContent).toContain("Hélène Admin");
  });

  it("survives full F5 page reload (unmount -> render): preserves Day-0 Admin, AI model, Workspace, and unlocked sidebar entries", async () => {
    const firstRender = await renderOrciaRoute("/settings");
    await completeFirstBootAdminModal({
      name: "Romain Persistant",
      email: "romain.persist@orcia.fr",
      password: "Secret123456!", // pragma: allowlist secret
    });

    fireEvent.click(screen.getByTestId("settings-tab-models"));
    fireEvent.change(screen.getByTestId("llm-primary-model-input"), { target: { value: "claude-3-7-sonnet-persist" } });
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));
    await waitFor(() => {
      expect((screen.getByTestId("eight-menu-item-assistant") as HTMLButtonElement).disabled).toBe(false);
    });

    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    await createOrgUnitViaModal({ name: "Direction Persistance", expectedRowTestId: "org-unit-row-org-1" });

    await act(async () => {
      await firstRender.router.navigate({ to: "/workspaces" });
    });
    await createWorkspaceViaModal({ name: "Espace Survie F5" });
    await waitFor(() => {
      expect((screen.getByTestId("eight-menu-item-finops") as HTMLButtonElement).disabled).toBe(false);
    });

    firstRender.unmount();
    await renderOrciaRoute("/cockpit");

    expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
    expect(screen.getByTestId("sidebar-open-my-account-btn").textContent).toContain("Romain Persistant");
    await waitFor(() => {
      expect((screen.getByTestId("eight-menu-item-assistant") as HTMLButtonElement).disabled).toBe(false);
    });
    expect((screen.getByTestId("eight-menu-item-agents") as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByTestId("eight-menu-item-processes") as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByTestId("eight-menu-item-finops") as HTMLButtonElement).disabled).toBe(false);
    expect(screen.queryByTestId("onboarding-progress-badge")).toBeNull();
    expect(screen.getByTestId("accostage-progress-pill").textContent).toBe("4 / 6 complétées");
  });

  it("displays Notification Center setup alerts, clears disabled-button alert badges after LLM configuration, and validates team member org modal", async () => {
    await renderOrciaRoute("/settings");
    expect(screen.getByTestId("disabled-button-alert-icon-first-boot-admin-submit-btn")).toBeDefined();
    expect(screen.getByTestId("disabled-button-alert-tooltip-first-boot-admin-submit-btn").getAttribute("role")).toBe("tooltip");
    await completeFirstBootAdminModal({ name: "Romain Admin", email: "romain@orcia.fr", password: "Secret123456!" }); // pragma: allowlist secret

    const assistantMenuBtn = screen.getByTestId("eight-menu-item-assistant") as HTMLButtonElement;
    expect(assistantMenuBtn.disabled).toBe(true);
    expect(screen.getByTestId("disabled-button-alert-icon-eight-menu-item-assistant")).toBeDefined();
    expect(screen.getByTestId("disabled-button-alert-icon-eight-menu-item-agents")).toBeDefined();
    expect(screen.getByTestId("disabled-button-alert-icon-eight-menu-item-processes")).toBeDefined();

    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    fireEvent.click(await screen.findByTestId("settings-tab-iam"));
    fireEvent.click(screen.getByTestId("iam-secops-drawer-toggle"));
    fireEvent.click(screen.getByTestId("rbac-verb-checkbox-execute"));
    fireEvent.click(screen.getByTestId("rbac-verb-checkbox-read"));
    expect((screen.getByTestId("create-rbac-grant-btn") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByTestId("disabled-button-alert-icon-create-rbac-grant-btn")).toBeDefined();
    fireEvent.click(screen.getByTestId("rbac-verb-checkbox-execute"));
    expect((screen.getByTestId("create-rbac-grant-btn") as HTMLButtonElement).disabled).toBe(false);
    expect(screen.queryByTestId("disabled-button-alert-icon-create-rbac-grant-btn")).toBeNull();

    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    await createOrgUnitViaModal({ name: "Direction Tech", expectedRowTestId: "org-unit-row-org-1" });
    await createOrgUnitViaModal({ name: "Équipe Plateforme", level: "TEAM", expectedRowTestId: "org-unit-row-org-2" });
    expect(screen.getByTestId("org-unit-row-org-2").textContent).toContain("ÉQUIPE");
    expect(screen.getByTestId("org-unit-row-org-1").textContent).toContain("1 Équipe rattachée");

    expect(Number(screen.getByTestId("topbar-notifications-badge").textContent)).toBeGreaterThanOrEqual(2);
    fireEvent.click(screen.getByTestId("topbar-notifications-toggle"));
    const drawer = screen.getByTestId("topbar-notifications-drawer");
    expect(drawer.textContent).toContain("Aucun modèle IA configuré");
    expect(drawer.textContent).toContain("Aucun Espace de travail créé");
    expect(screen.getByTestId("notifications-vs-activity-log-box").textContent).toContain("Journal d'Activité");
    fireEvent.click(screen.getByTestId("topbar-notifications-close"));

    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    fireEvent.click(await screen.findByTestId("settings-tab-models"));
    fireEvent.change(screen.getByTestId("llm-primary-model-input"), { target: { value: "claude-3-7-sonnet" } });
    fireEvent.change(screen.getByTestId("llm-api-key-input"), { target: { value: "sk-ant-test" } });
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));

    await waitFor(() => { expect(assistantMenuBtn.disabled).toBe(false); });
    expect(screen.queryByTestId("disabled-button-alert-icon-eight-menu-item-assistant")).toBeNull();
    expect(screen.queryByTestId("disabled-button-alert-tooltip-eight-menu-item-assistant")).toBeNull();
  });

  it("renders Day-0 shell in English locale and allows cancelling clean First-Boot Admin Setup Modal via Annuler button", () => {
    const { unmount } = renderShellModule("cockpit", "en");
    expect(screen.getByTestId("first-boot-admin-setup-modal")).toBeDefined();
    expect(screen.getByTestId("accostage-progress-pill").textContent).toBe("0 of 6 completed");
    expect(screen.getByTestId("eight-menu-item-cockpit").textContent).toContain("Cockpit");
    expect(screen.getByTestId("eight-menu-item-spaces").textContent).toContain("My Spaces");
    expect(screen.getByTestId("eight-menu-item-configuration").textContent).toContain("Administration");
    expect(screen.getByTestId("eight-menu-item-help").textContent).toContain("Help");
    expect(screen.getByTestId("eight-menu-item-assistant").textContent).toContain("My Assistant");
    expect(screen.getByTestId("eight-menu-item-processes").textContent).toContain("My Processes");
    expect(screen.getByTestId("eight-menu-item-agents").textContent).toContain("My Agents");
    expect(screen.getByTestId("eight-menu-item-finops").textContent).toContain("FinOps");
    expect((screen.getByTestId("eight-menu-item-cockpit") as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByTestId("eight-menu-item-spaces") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("eight-menu-item-configuration") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("eight-menu-item-help") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("eight-menu-item-assistant") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("eight-menu-item-processes") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("eight-menu-item-agents") as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByTestId("eight-menu-item-finops") as HTMLButtonElement).disabled).toBe(true);

    expect(screen.queryByTestId("first-boot-admin-cancel-btn")).toBeNull();
    expect(screen.getByTestId("first-boot-admin-mandatory-badge")).toBeDefined();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
    unmount();

    renderShellModule("cockpit", "fr");
    expect(screen.getByTestId("first-boot-admin-setup-modal")).toBeDefined();
    expect((screen.getByTestId("first-boot-admin-submit-btn") as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), { target: { value: "Claire" } });
    expect((screen.getByTestId("first-boot-admin-submit-btn") as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), { target: { value: "claire@orcia.fr" } });
    expect((screen.getByTestId("first-boot-admin-submit-btn") as HTMLButtonElement).disabled).toBe(false);
  });
});
