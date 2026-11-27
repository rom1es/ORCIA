import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import {
  completeFirstBootAdminModal,
  createOrgUnitViaModal,
  ensureZone4HelpOpen,
  renderOrciaRoute,
  resetShellTestState,
} from "./setup/shellTestHelpers";
import { seedVitestPlatformSetupState } from "./vitest.setup";

describe("@orcia/web Settings, AI Models, Business Packs, Wizards, and Activity Log", () => {
  beforeEach(() => {
    resetShellTestState();
  });

  it("initializes entities across /settings tabs and records Outbox audit events visible in /activity", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.fr", displayName: "Admin", roles: ["PLATFORM_ADMIN"] });
    await renderOrciaRoute("/settings");
    expect(screen.queryByTestId("settings-tab-audit")).toBeNull();
    expect(screen.queryByTestId("settings-tab-organization")).toBeNull();
    expect(screen.queryByTestId("settings-open-organization-link")).toBeNull();

    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    expect(await screen.findByTestId("iam-org-units-empty-state")).toBeDefined();
    await createOrgUnitViaModal({ name: "Direction Technique", expectedRowTestId: "org-unit-row-org-1" });
    expect(screen.getByTestId("org-unit-row-org-1").textContent).toContain("Direction Technique");

    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    fireEvent.click(await screen.findByTestId("settings-tab-models"));
    expect(screen.getByTestId("llm-tiers-empty-state")).toBeDefined();
    fireEvent.change(screen.getByTestId("llm-primary-model-input"), { target: { value: "model-primary-v1" } });
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));
    await waitFor(() => {
      const rows = Array.from(document.querySelectorAll('[data-testid^="llm-tier-row-"]'));
      expect(rows.some((r) => r.textContent?.includes("model-primary-v1"))).toBe(true);
    });

    fireEvent.click(screen.getByTestId("settings-tab-connectors"));
    expect(screen.getByTestId("settings-deported-sources-banner")).toBeDefined();
    expect(screen.getByTestId("settings-goto-workspace-sources-btn")).toBeDefined();
    fireEvent.click(screen.getByTestId("settings-goto-workspace-sources-btn"));
    fireEvent.click(screen.getByTestId("eight-menu-item-finops"));
    fireEvent.click(await screen.findByTestId("finops-open-activity-link"));
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByTestId("activity-log-explorer-page")).toBeDefined();
    expect(screen.getByTestId("audit-event-row-evt-1")).toBeDefined();
  });

  it("runs the step-by-step Guided Onboarding Wizard (/wizards) starting at step 1/5", async () => {
    await renderOrciaRoute("/wizards");
    await waitFor(() => { expect(screen.getByTestId("wizard-step-form-1")).toBeDefined(); });
    const runnerTextBefore = screen.getByTestId("durable-wizard-runner").textContent ?? "";
    expect(runnerTextBefore).toContain("Étape 1 sur 5");
    expect(runnerTextBefore).toContain("Création d'un Espace de travail d'équipe");
    expect(runnerTextBefore).not.toContain("sdlc_tech_lead");

    fireEvent.change(screen.getByTestId("wizard-input-org-unit"), { target: { value: "Équipe Plateforme" } });
    fireEvent.click(screen.getByTestId("wizard-complete-step-btn"));
    await waitFor(() => { expect(screen.getByTestId("wizard-step-form-2")).toBeDefined(); });
    expect(screen.getByTestId("durable-wizard-runner").textContent).toContain("Étape 2 sur 5");
  });

  it("supports TopHeader workspace dropdown, BU/Espace linkage with orphan-safe deletion, single scope selector, zero English parenthetical terms in FR, and contextual help on /settings", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.fr", displayName: "Admin", roles: ["PLATFORM_ADMIN", "SECOPS"] });
    await renderOrciaRoute("/settings");
    expect(screen.getByTestId("settings-tab-iam").textContent).toBe("Comptes & Habilitations");
    fireEvent.click(screen.getByTestId("settings-tab-iam"));
    const iamText = screen.getByTestId("settings-iam-section").textContent ?? "";
    for (const forbidden of ["(ROLE)", "(USER)", "(ALLOW)", "(DENY)", "GLOBAL (Plateforme)"]) {
      expect(iamText).not.toContain(forbidden);
    }
    expect(screen.getByTestId("iam-secops-drawer-toggle").getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    await createOrgUnitViaModal({ name: "BU Finance", expectedRowTestId: "org-unit-row-org-1" });
    await createOrgUnitViaModal({ name: "Espace Comptabilité", level: "TEAM", slug: "aqwZSX", expectedRowTestId: "org-unit-row-org-2" });

    fireEvent.click(screen.getByTestId("sidebar-rail-toggle-btn"));
    const wsTrigger = screen.getByTestId("topbar-fixed-workspace-selector");
    fireEvent.click(wsTrigger);
    expect(screen.getByTestId("topbar-workspace-dropdown-menu").textContent).toContain("BU Finance");
    fireEvent.click(screen.getByTestId("topbar-workspace-option-org-1"));
    expect(wsTrigger.textContent).toContain("BU Finance");
    fireEvent.click(screen.getByTestId("sidebar-rail-toggle-btn"));

    fireEvent.click(screen.getByTestId("delete-org-unit-btn-org-1"));
    expect((screen.getByTestId("confirm-delete-org-unit-btn-org-1") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByTestId("org-unit-delete-blocked-banner").textContent).toContain("Suppression impossible");
    expect(screen.getByTestId("org-unit-row-org-1")).toBeDefined();
    fireEvent.click(screen.getByTestId("cancel-delete-org-unit-btn-org-1"));

    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    fireEvent.click(await screen.findByTestId("settings-tab-iam"));
    fireEvent.click(screen.getByTestId("iam-secops-drawer-toggle"));
    fireEvent.change(screen.getByTestId("rbac-subject-select"), { target: { value: "TEAM_LEAD" } });
    fireEvent.change(screen.getByTestId("rbac-scope-preset-select"), { target: { value: "aqwzsx" } });
    fireEvent.click(screen.getByTestId("rbac-verb-checkbox-grant"));
    fireEvent.click(screen.getByTestId("create-rbac-grant-btn"));
    const grantRow = await screen.findByTestId("rbac-grant-row-grant-1");
    expect(grantRow.textContent).toContain("Rôle : Responsable d'Équipe");
    expect(grantRow.textContent).not.toContain("(ROLE:");
    expect(grantRow.textContent).toContain("Équipe : Espace Comptabilité (aqwzsx)");
    const secopsBodyText = screen.getByTestId("iam-secops-drawer-body").textContent ?? "";
    expect(secopsBodyText).toContain("Déléguer des droits · Autorisé");
    expect(secopsBodyText).not.toContain("(ALLOW)");

    fireEvent.click(screen.getByTestId("rbac-grants-select-all-checkbox"));
    fireEvent.click(screen.getByTestId("rbac-grants-bulk-delete-btn"));
    expect(await screen.findByTestId("iam-grants-empty-state")).toBeDefined();

    const helpTerms = screen.getByTestId("help-accordion-terms-content");
    expect(helpTerms.textContent).toContain("Isoler ce périmètre");
    expect(helpTerms.textContent).toContain("Équipe Paiement");
    expect(helpTerms.textContent).not.toContain("Chef1");
    expect(helpTerms.textContent).not.toContain("aqwZSX");
    expect(helpTerms.textContent).toContain("BU vs Équipe vs Espace de travail");

    ensureZone4HelpOpen();
    fireEvent.click(screen.getByTestId("contextual-info-trigger-iam-target-scope"));
    const targetScopeHelp = screen.getByTestId("help-section-iam-target-scope");
    expect(targetScopeHelp.getAttribute("data-active")).toBe("true");
    expect(targetScopeHelp.textContent).toContain("Qu'est-ce que le Périmètre cible");
  });

  it("configures AI Models, tests LLM connectivity, displays French labels without 'medium' or 'family-a', and activates Business Packs across scopes", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.fr", displayName: "Admin", roles: ["PLATFORM_ADMIN"] });
    await renderOrciaRoute("/settings");

    expect((screen.getByTestId("four-zone-central-workspace") as HTMLElement).style.overflowY).toBe("auto");
    expect((screen.getByTestId("four-zone-contextual-help-column") as HTMLElement).style.overflowY).toBe("auto");

    fireEvent.click(screen.getByTestId("settings-tab-models"));
    expect(screen.getByTestId("settings-ai-models-section").textContent).not.toContain("family-a");
    expect((screen.getByTestId("llm-family-input") as HTMLInputElement).value).toBe("Anthropic");
    expect((screen.getByTestId("llm-endpoint-url-input") as HTMLInputElement).value).toBe("https://api.anthropic.com/v1");
    fireEvent.click(screen.getByTestId("test-llm-connection-btn"));
    expect(screen.getByTestId("llm-connection-test-result").getAttribute("data-ok")).toBe("false");
    expect(screen.getByTestId("llm-connection-test-result").textContent).toContain("Échec du test");

    fireEvent.change(screen.getByTestId("llm-primary-model-input"), { target: { value: "claude-3-7-sonnet" } });
    fireEvent.click(screen.getByTestId("test-llm-connection-btn"));
    expect(screen.getByTestId("llm-connection-test-result").textContent).toContain("clé d'API");
    fireEvent.change(screen.getByTestId("llm-api-key-input"), { target: { value: "sk-ant-test-key-12345" } });
    fireEvent.click(screen.getByTestId("test-llm-connection-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("llm-connection-test-result").getAttribute("data-ok")).toBe("true");
      expect(screen.getByTestId("llm-connection-test-result").textContent).toContain("Connexion réussie au modèle « claude-3-7-sonnet »");
    });
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));
    await waitFor(() => {
      const savedRow = document.querySelector('[data-testid^="llm-tier-row-"][data-tier="medium"]')!;
      expect(savedRow.textContent).toContain("Standard");
      expect(savedRow.textContent).toContain("claude-3-7-sonnet");
      expect(savedRow.textContent).toContain("Anthropic · Équilibré");
      expect(savedRow.textContent).toContain("Clé d'API enregistrée");
      expect(savedRow.textContent).not.toContain("family-a");
    });

    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    await createOrgUnitViaModal({ name: "Direction Produit", expectedRowTestId: "org-unit-row-org-1" });
    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    fireEvent.click(await screen.findByTestId("settings-tab-packs"));
    expect(screen.queryByTestId("pack-version-input")).toBeNull();
    expect(screen.queryByTestId("pack-key-input")).toBeNull();
    expect(screen.queryByTestId("save-pack-btn")).toBeNull();

    const sdlcCard = await screen.findByTestId("installed-pack-card-orcia-pack-sdlc");
    expect(sdlcCard.textContent).toContain("Ingénierie Logicielle & Cycle de Vie Produit");
    expect(sdlcCard.textContent).toContain("4 processus · 6 agents spécialisés");
    expect(screen.getByTestId("installed-pack-card-orcia-pack-builder").textContent).toContain("Atelier de Création & Gouvernance de Packs Métiers");
    const scopeSelect = screen.getByTestId("pack-scope-input") as HTMLSelectElement;
    expect(scopeSelect.textContent).toContain("Plateforme entière");
    expect(scopeSelect.textContent).toContain("Direction · Direction Produit");
    expect(screen.getByTestId("packs-empty-state")).toBeDefined();
    fireEvent.change(scopeSelect, { target: { value: "direction-produit" } });
    fireEvent.click(screen.getByTestId("activate-pack-btn-orcia-pack-sdlc"));
    expect(screen.queryByTestId("pack-row-orcia-pack-sdlc")).toBeNull();
    expect(screen.getAllByTestId("pack-card-active-scopes-orcia-pack-sdlc").length).toBe(1);
    expect(screen.getByTestId("pack-card-active-scopes-orcia-pack-sdlc").textContent).toContain("Direction · Direction Produit");
    fireEvent.change(scopeSelect, { target: { value: "GLOBAL" } });
    fireEvent.click(screen.getByTestId("activate-pack-btn-orcia-pack-sdlc"));
    expect(screen.getAllByTestId("pack-card-active-scopes-orcia-pack-sdlc")[0]?.textContent).toContain("Plateforme entière");
    expect(screen.getAllByTestId("pack-card-active-scopes-orcia-pack-sdlc")[0]?.textContent).not.toContain("Direction · Direction Produit");
    fireEvent.click(screen.getByTestId("deactivate-pack-btn-orcia-pack-sdlc"));
    expect(screen.getByTestId("packs-empty-state")).toBeDefined();
  });

  it("mounts /activity via Notifications, displays French timestamps/authors, filters by observation scope, and enforces disabled button alert badges", async () => {
    await renderOrciaRoute("/settings");
    const adminSubmitBtn = screen.getByTestId("first-boot-admin-submit-btn") as HTMLButtonElement;
    expect(adminSubmitBtn.disabled).toBe(true);
    expect(screen.getByTestId("disabled-button-alert-tooltip-first-boot-admin-submit-btn").getAttribute("role")).toBe("tooltip");

    await completeFirstBootAdminModal({ name: "Romain Admin", email: "romain@orcia.fr", password: "Secret123456!" }); // pragma: allowlist secret
    expect(screen.getByTestId("disabled-button-alert-icon-eight-menu-item-assistant")).toBeDefined();

    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    await createOrgUnitViaModal({ name: "Direction Produit", expectedRowTestId: "org-unit-row-org-1" });
    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    fireEvent.click(await screen.findByTestId("settings-tab-packs"));
    fireEvent.click(await screen.findByTestId("activate-pack-btn-orcia-pack-builder"));
    fireEvent.click(screen.getByTestId("deactivate-pack-btn-orcia-pack-builder"));
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 50)); });

    fireEvent.click(screen.getByTestId("topbar-notifications-toggle"));
    expect(screen.getByTestId("notifications-vs-activity-log-box").textContent).toContain("Journal d'Activité");
    fireEvent.click(screen.getByTestId("notifications-open-activity-log-btn"));
    await act(async () => { await Promise.resolve(); });

    const activityPage = screen.getByTestId("activity-log-explorer-page");
    expect(screen.getByTestId("topbar-breadcrumb").textContent).toContain("Journal d'Activité");
    expect((await screen.findByTestId("activity-event-timestamp-evt-4")).textContent).toMatch(/\d{2}\/\d{2}\/\d{4}\s+\d{2}:\d{2}:\d{2}/);
    expect(screen.getByTestId("activity-event-actor-evt-4").textContent).toContain("Romain Admin (romain@orcia.fr)");
    expect(screen.getByTestId("activity-event-scope-evt-4").textContent).toContain("Plateforme entière");
    for (const raw of ["PackDeactivated", "PackRegistered", "OrgUnitCreated", "PlatformAdminInitialized", "sur GLOBAL"]) {
      expect(activityPage.textContent).not.toContain(raw);
    }
    expect(activityPage.textContent).toContain("Pack désactivé");
    expect(activityPage.textContent).toContain("Pack activé");
    expect(screen.getByTestId("activity-observation-scope-badge").textContent).toContain("Filtré sur votre niveau d'observation : Plateforme entière");
    expect((screen.getByTestId("activity-scope-filter-select") as HTMLSelectElement).value).toBe("scope-global");

    fireEvent.click(screen.getByTestId("sidebar-rail-toggle-btn"));
    fireEvent.click(screen.getByTestId("topbar-fixed-workspace-selector"));
    fireEvent.click(screen.getByTestId("topbar-workspace-option-org-1"));
    fireEvent.click(screen.getByTestId("sidebar-rail-toggle-btn"));
    expect((screen.getByTestId("activity-scope-filter-select") as HTMLSelectElement).value).toBe("org-1");
    expect(screen.getByTestId("activity-observation-scope-badge").textContent).toContain("Direction · Direction Produit");
    expect(screen.getByTestId("audit-event-row-evt-2")).toBeDefined();
    expect(screen.queryByTestId("audit-event-row-evt-4")).toBeNull();

    fireEvent.change(screen.getByTestId("activity-scope-filter-select"), { target: { value: "scope-global" } });
    expect(screen.getByTestId("audit-event-row-evt-4")).toBeDefined();
    fireEvent.click(screen.getByTestId("activity-reset-observation-scope-btn"));
    expect((screen.getByTestId("activity-scope-filter-select") as HTMLSelectElement).value).toBe("org-1");

    fireEvent.change(screen.getByTestId("activity-scope-filter-select"), { target: { value: "scope-global" } });
    const maxLimitSelect = screen.getByTestId("activity-max-limit-select") as HTMLSelectElement;
    expect(maxLimitSelect.value).toBe("100");
    expect(maxLimitSelect.textContent).toContain("100 derniers");
    fireEvent.change(maxLimitSelect, { target: { value: "200" } });
    expect(maxLimitSelect.value).toBe("200");
    fireEvent.change(screen.getByTestId("activity-time-window-select"), { target: { value: "24H" } });
    expect(screen.getByTestId("audit-event-row-evt-4")).toBeDefined();
    fireEvent.change(screen.getByTestId("activity-user-filter-select"), { target: { value: "Romain Admin" } });
    expect(screen.getByTestId("audit-event-row-evt-4")).toBeDefined();
    fireEvent.change(screen.getByTestId("activity-user-search-input"), { target: { value: "utilisateur-inexistant" } });
    expect(screen.getByTestId("audit-events-empty-state")).toBeDefined();
  });
});
