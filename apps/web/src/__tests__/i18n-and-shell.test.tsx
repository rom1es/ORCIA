import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, fireEvent, render, screen } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ModuleWorkspaceView } from "../components/ModuleWorkspaceView";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { resolveModuleFromPathname, ShellContainer } from "../components/ShellContainer";
import { buildCockpitWorkflowPreviewGraph } from "../features/cockpit";
import { I18nProvider } from "../i18n";
import { enDictionary } from "../i18n/locales/en";
import { frDictionary } from "../i18n/locales/fr";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { preloadModuleQueryData, validateOrciaRouteSearch } from "../routes/searchSchema";

const mockPush = vi.fn();
if (typeof window !== "undefined") {
  window.scrollTo = vi.fn();
}

function collectNestedKeys(obj: Record<string, unknown>, prefix = ""): string[] {
  const keys: string[] = [];
  for (const [k, v] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object" && !Array.isArray(v)) {
      keys.push(...collectNestedKeys(v as Record<string, unknown>, fullKey));
    } else {
      keys.push(fullKey);
    }
  }
  return keys.sort();
}

function walkTsFiles(dir: string): string[] {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== "__tests__") {
        files.push(...walkTsFiles(fullPath));
      }
    } else if (entry.isFile() && /\.(ts|tsx)$/.test(entry.name)) {
      files.push(fullPath);
    }
  }
  return files;
}

describe("@orcia/web empty-start UX, entity setup screens, and i18n parity", () => {
  beforeEach(() => {
    clearPlatformSetupStorage();
  });

  it("enforces 100% recursive key parity between fr.ts and en.ts", () => {
    const frKeys = collectNestedKeys(frDictionary as unknown as Record<string, unknown>);
    const enKeys = collectNestedKeys(enDictionary as unknown as Record<string, unknown>);
    expect(frKeys).toEqual(enKeys);
  });

  it("never uses raw hex colors, next/* imports, or workspaceFixtures in apps/web/src", () => {
    const webSrcDir = path.resolve(__dirname, "..");
    const tsFiles = walkTsFiles(webSrcDir);
    const hexColorRegex = /#[0-9a-fA-F]{3,8}\b/;
    for (const filePath of tsFiles) {
      const content = fs.readFileSync(filePath, "utf-8");
      expect(
        hexColorRegex.test(content),
        `Found forbidden hex color in ${path.relative(webSrcDir, filePath)}`,
      ).toBe(false);
      expect(content).not.toMatch(/from\s+["']next(\/|["'])/);
      expect(content).not.toMatch(/workspaceFixtures/);
    }
  });

  it("enforces feature-sliced boundary isolation across all 8 features/<domaine>/ modules (M11, AD-19)", () => {
    const featuresDir = path.resolve(__dirname, "../features");
    const domains = [
      "cockpit",
      "inbox",
      "catalog",
      "ontology",
      "gates",
      "finops",
      "admin",
      "workspaces",
    ];
    for (const domain of domains) {
      const domainDir = path.join(featuresDir, domain);
      expect(fs.existsSync(domainDir)).toBe(true);
      const files = walkTsFiles(domainDir);
      expect(files.length).toBeGreaterThan(0);
      for (const filePath of files) {
        const content = fs.readFileSync(filePath, "utf-8");
        for (const other of domains) {
          if (other === domain) continue;
          const relPattern = new RegExp(`from\\s+["'](?:\\.\\./)+${other}(?:/|["'])`);
          const aliasPattern = new RegExp(`from\\s+["']@/features/${other}(?:/|["'])`);
          expect(relPattern.test(content)).toBe(false);
          expect(aliasPattern.test(content)).toBe(false);
        }
      }
    }
  });

  it("resolves all module routes including /settings and /wizards via resolveModuleFromPathname", () => {
    expect(resolveModuleFromPathname(null)).toBe("cockpit");
    expect(resolveModuleFromPathname("/")).toBe("cockpit");
    expect(resolveModuleFromPathname("/cockpit")).toBe("cockpit");
    expect(resolveModuleFromPathname("/inbox")).toBe("inbox");
    expect(resolveModuleFromPathname("/catalog")).toBe("catalog");
    expect(resolveModuleFromPathname("/ontology")).toBe("ontology");
    expect(resolveModuleFromPathname("/gates")).toBe("gates");
    expect(resolveModuleFromPathname("/finops")).toBe("finops");
    expect(resolveModuleFromPathname("/workspaces")).toBe("admin");
    expect(resolveModuleFromPathname("/admin")).toBe("admin");
    expect(resolveModuleFromPathname("/bootstrap")).toBe("bootstrap");
    expect(resolveModuleFromPathname("/settings")).toBe("bootstrap");
    expect(resolveModuleFromPathname("/wizards")).toBe("bootstrap");
  });

  it("validates typed URL search params, QueryClient route preloading, and @xyflow/react cockpit graph", async () => {
    expect(validateOrciaRouteSearch({})).toEqual({});
    expect(validateOrciaRouteSearch({ q: "  pay-142  " })).toEqual({
      q: "pay-142",
    });

    const queryClient = createOrciaQueryClient();
    const preloaded = await preloadModuleQueryData(queryClient, "catalog", false);
    expect(preloaded).toEqual({ moduleKey: "catalog", fixture: false });

    const graph = buildCockpitWorkflowPreviewGraph();
    expect(graph.nodes).toHaveLength(5);
    expect(graph.edges).toHaveLength(4);
  });

  it("starts 100% empty of sample data by default, displays the First-Boot Platform Admin Modal, and greys out unconfigured menu entries", () => {
    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={mockPush}>
          <ModuleWorkspaceView moduleKey="cockpit" />
        </ShellContainer>
      </I18nProvider>,
    );

    // First-boot Platform Administrator creation modal is displayed on 1st startup
    expect(screen.getByTestId("first-boot-admin-setup-modal")).toBeDefined();

    // 0/5 onboarding progress at blank start
    expect(screen.getByTestId("onboarding-progress-badge").textContent).toBe("0/5");
    expect(screen.getByTestId("cockpit-no-workspace-empty-state")).toBeDefined();

    // Unconfigured features are greyed out (disabled) in the 8-entry sidebar
    expect(
      (screen.getByTestId("eight-menu-item-cockpit") as HTMLButtonElement).disabled,
    ).toBe(false);
    expect(
      (screen.getByTestId("eight-menu-item-spaces") as HTMLButtonElement).disabled,
    ).toBe(false);
    expect(
      (screen.getByTestId("eight-menu-item-configuration") as HTMLButtonElement).disabled,
    ).toBe(false);
    expect(
      (screen.getByTestId("eight-menu-item-help") as HTMLButtonElement).disabled,
    ).toBe(false);
    expect(
      (screen.getByTestId("eight-menu-item-assistant") as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId("eight-menu-item-processes") as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId("eight-menu-item-agents") as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId("eight-menu-item-finops") as HTMLButtonElement).disabled,
    ).toBe(true);

    // Redundant TopHeaderBar locale toggle and sidebar pack selector are removed
    expect(screen.queryByTestId("shell-locale-toggle")).toBeNull();
    expect(screen.queryByTestId("sidebar-pack-selector")).toBeNull();
  });

  it("guides workspace creation from /workspaces and dynamically unlocks workspace-scoped modules and runs", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/workspaces"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // Initially empty topology and FinOps is disabled before workspace creation
    expect(screen.getByTestId("workspace-topology-empty-state")).toBeDefined();
    expect(
      (screen.getByTestId("eight-menu-item-finops") as HTMLButtonElement).disabled,
    ).toBe(true);

    // Create a Workspace via the setup form
    fireEvent.change(screen.getByTestId("workspace-name-input"), {
      target: { value: "Mon Premier Espace" },
    });
    fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));

    // FinOps is now unlocked in the sidebar!
    expect(
      (screen.getByTestId("eight-menu-item-finops") as HTMLButtonElement).disabled,
    ).toBe(false);

    // Navigate to /cockpit -> Onboarding progress is 1/5 and Run launcher is unlocked
    await act(async () => {
      await router.navigate({ to: "/cockpit" });
    });
    expect(screen.getByTestId("onboarding-progress-badge").textContent).toBe("1/5");
    expect(screen.getByTestId("cockpit-launch-run-form")).toBeDefined();
  });

  it("initializes entities across the 5 dedicated /settings tabs and records Outbox audit events visible in the dedicated left-menu Activity Log (/activity)", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // Journal d'Activité is no longer a tab inside /settings
    expect(screen.queryByTestId("settings-tab-audit")).toBeNull();

    // Tab 1: IAM (starts empty, create Org Unit)
    expect(screen.getByTestId("iam-org-units-empty-state")).toBeDefined();
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Direction Technique" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    expect(screen.getByTestId("org-unit-row-org-1").textContent).toContain("Direction Technique");

    // Tab 2: AI Models (starts empty, bind tier)
    fireEvent.click(screen.getByTestId("settings-tab-ai-models"));
    expect(screen.getByTestId("llm-tiers-empty-state")).toBeDefined();
    fireEvent.change(screen.getByTestId("llm-primary-model-input"), {
      target: { value: "model-primary-v1" },
    });
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));
    expect(screen.getByTestId("llm-tier-row-medium").textContent).toContain("model-primary-v1");

    // Tab 3: Connectors (starts empty, register connector)
    fireEvent.click(screen.getByTestId("settings-tab-connectors"));
    expect(screen.getByTestId("connectors-empty-state")).toBeDefined();
    fireEvent.change(screen.getByTestId("connector-alias-input"), {
      target: { value: "git-principal" },
    });
    fireEvent.change(screen.getByTestId("connector-uri-input"), {
      target: { value: "git://entreprise.local/core" },
    });
    fireEvent.click(screen.getByTestId("save-connector-btn"));
    expect(screen.getByTestId("connector-row-ds-1").textContent).toContain("git-principal");

    // Dedicated left-menu entry eight-menu-item-activity navigates to /activity and displays the recorded events
    fireEvent.click(screen.getByTestId("eight-menu-item-activity"));
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("activity-log-explorer-page")).toBeDefined();
    expect(screen.getByTestId("audit-event-row-evt-1")).toBeDefined();
  });

  it("runs the step-by-step Guided Onboarding Wizard (/wizards) starting at step 1/5", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/wizards"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    expect(screen.getByTestId("wizard-step-form-1")).toBeDefined();
    fireEvent.change(screen.getByTestId("wizard-input-org-unit"), {
      target: { value: "Équipe Plateforme" },
    });
    fireEvent.click(screen.getByTestId("wizard-complete-step-btn"));
    expect(screen.getByTestId("wizard-step-form-2")).toBeDefined();
  });

  it("renders the 4-Zone Direction C Shell with 8 fixed menu entries, StreamlinedCockpitView, and Day 0 Accostage Banner (Story 12.1)", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/cockpit"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

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

  it("mounts the all-in-one Mon Assistant screen on /assistant with 3-Speed selector, Folders, Citations, and 4-Level Governance (Story 12.2)", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/assistant"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    expect(screen.getByTestId("inbox-feature-panel")).toBeDefined();
    expect(screen.getByTestId("assistant-folders-and-collaborative-thread-view")).toBeDefined();
    expect(screen.getByTestId("assistant-speed-selector-and-stream")).toBeDefined();
    expect(screen.getByTestId("assistant-citation-pills-and-artifact-card")).toBeDefined();

    // Open the 4-level governance modal/studio
    fireEvent.click(screen.getByTestId("assistant-open-governance-btn"));
    expect(screen.getByTestId("assistant-governance-container")).toBeDefined();
  });

  it("mounts Mes Espaces 5-tabs, DNA Starlark compiler, MCP/A2A Test Bench, Pack Builder Studio, and Help Generator across /spaces, /agents, /processes, and /help (Story 12.3)", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/spaces"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // /spaces -> WorkspaceFiveTabsAndExternalRebaseView + DnaStarlarkCompilerAndGlossaryLifecycleView
    expect(screen.getByTestId("workspace-five-tabs-view")).toBeDefined();
    expect(screen.getByTestId("dna-starlark-glossary-view")).toBeDefined();

    // Navigate to /agents -> RemoteServiceTestBenchAndMcpExposureView
    await act(async () => {
      await router.navigate({ to: "/agents" });
    });
    expect(screen.getByTestId("remote-service-test-bench")).toBeDefined();

    // Navigate to /processes -> SimplifiedProcessBuilderSection + PackBuilderProcessesStudioView + HelpArticleGeneratorAndValidatorView
    await act(async () => {
      await router.navigate({ to: "/processes" });
    });
    const processStudioSection = screen.getByTestId("settings-workflows-section");
    expect(processStudioSection).toBeDefined();
    expect(screen.getByTestId("pack-builder-studio-view")).toBeDefined();
    expect(screen.getByTestId("help-article-generator-validator-view")).toBeDefined();

    // Zero raw English lifecycle badges or cryptic counters in the Process Studio
    const processStudioText = processStudioSection.textContent ?? "";
    for (const forbiddenRawBadge of [
      "PUBLISHED 0",
      "DRAFT 0",
      "TRASH 0",
      "ACTIVE_RUNS",
      "PAUSED_ARBITRATION",
      "(0p / 0s)",
      "e3b0c44298fc", // pragma: allowlist secret
    ]) {
      expect(processStudioText).not.toContain(forbiddenRawBadge);
    }

    // Clicking the ⓘ contextual help buttons opens the right-hand contextual help column on the targeted section
    fireEvent.click(screen.getByTestId("contextual-info-trigger-workflows-overview"));
    expect(screen.getByTestId("four-zone-contextual-help-column")).toBeDefined();
    expect(
      screen.getByTestId("help-section-workflows-overview").getAttribute("data-active"),
    ).toBe("true");

    fireEvent.click(screen.getByTestId("contextual-info-trigger-workflows-instructions"));
    expect(
      screen.getByTestId("help-section-workflows-instructions").getAttribute("data-active"),
    ).toBe("true");

    fireEvent.click(screen.getByTestId("contextual-info-trigger-workflows-deliverable-contract"));
    expect(
      screen
        .getByTestId("help-section-workflows-deliverable-contract")
        .getAttribute("data-active"),
    ).toBe("true");

    // Creating a process directly from /processes by entering only the title auto-generates the key and saves it
    fireEvent.change(screen.getByTestId("workflow-title-input"), {
      target: { value: "Revue de contrat fournisseur" },
    });
    fireEvent.click(screen.getByTestId("save-workflow-btn"));
    expect(screen.getByTestId("workflow-row-revue-de-contrat-fournisseur").textContent).toContain(
      "Revue de contrat fournisseur",
    );

    // Navigate to /help -> ContextualHelpColumnAndCenter (HELP_MENU_CENTER)
    await act(async () => {
      await router.navigate({ to: "/help" });
    });
    const helpPanels = screen.getAllByTestId("contextual-help-hybrid-panel");
    expect(helpPanels.some((el) => el.getAttribute("data-mode") === "HELP_MENU_CENTER")).toBe(
      true,
    );
  });

  it("enforces Story 12.4 UX sobriety: First-Boot Platform Admin Modal, zero fictional data (PAY-142/PSD2), zero NFR latency strings, and human-readable Rôle selector", () => {
    const serializedFr = JSON.stringify(frDictionary);
    const serializedEn = JSON.stringify(enDictionary);

    // Zero NFR latency or pixel dimension strings in dictionaries
    for (const forbidden of [
      "< 500ms",
      "< 500 ms",
      "(0 ms)",
      "< 30 ms",
      "Pause 450 ms",
      "450 ms pause",
      "< 50 ms",
      "< 2 ms",
      "< 5 s",
      "< 100 ms",
      "< 10 ms",
      "< 15 s",
      "340px",
      "420px",
      "280px",
      "720px",
      "PAY-142",
      "Administrateur / Tech Lead",
    ]) {
      expect(serializedFr).not.toContain(forbidden);
      expect(serializedEn).not.toContain(forbidden);
    }

    // Role label is "Rôle" / "Role"
    expect(frDictionary.userAccountAndSettings.hatSelectorLabel).toBe("Rôle");
    expect(enDictionary.userAccountAndSettings.hatSelectorLabel).toBe("Role");

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={mockPush}>
          <ModuleWorkspaceView moduleKey="inbox" />
        </ShellContainer>
      </I18nProvider>,
    );

    // Zero PAY-142 or PSD2 sample data on /assistant
    expect(document.body.textContent ?? "").not.toContain("PAY-142");
    expect(document.body.textContent ?? "").not.toContain("PSD2");
    expect(document.body.textContent ?? "").not.toContain("Administrateur / Tech Lead");

    // Complete First-Boot Platform Admin Modal
    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), {
      target: { value: "Romain Admin" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), {
      target: { value: "romain@orcia.fr" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-password-input"), {
      target: { value: "Secret123456!" },
    });
    fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));

    // Modal closes and header shows Romain Admin · Administrateur de la plateforme
    expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
    const userTrigger = screen.getByTestId("user-account-dropdown-trigger");
    expect(userTrigger.textContent).toContain("Romain Admin");
    expect(userTrigger.textContent).toContain("Administrateur de la plateforme");

    // Open user dropdown and check Role selector ("Rôle")
    fireEvent.click(userTrigger);
    const roleSelect = screen.getByTestId("dropdown-hat-selector") as HTMLSelectElement;
    expect(roleSelect.value).toBe("PLATFORM_ADMIN");
  });

  it("supports TopHeader workspace dropdown, BU/Espace linkage with orphan-safe deletion, greyed-out section 2 until org exists, single scope selector, zero English parenthetical terms in FR, and contextual help on /settings", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // 1. No "(IAM 6 verbes)" jargon in the tab or header, and no English parenthetical terms in French IAM section
    expect(screen.getByTestId("settings-tab-iam").textContent).toBe(
      "Organisation & Habilitations",
    );
    const iamSectionInitialText = screen.getByTestId("settings-iam-section").textContent ?? "";
    for (const forbiddenEnglishParen of [
      "(ROLE)",
      "(USER)",
      "(ALLOW)",
      "(DENY)",
      "(INHERITANCE_BLOCK)",
      "(create)",
      "(read)",
      "(update)",
      "(delete)",
      "(execute)",
      "(grant)",
      "GLOBAL (Plateforme)",
      "BU (Business Unit / Direction)",
    ]) {
      expect(iamSectionInitialText).not.toContain(forbiddenEnglishParen);
    }

    // 1b. Redundant free-text scope input and competing "Action principale" select are removed
    expect(screen.queryByTestId("rbac-scope-input")).toBeNull();
    expect(screen.queryByTestId("rbac-verb-select")).toBeNull();

    // 1c. Section 2 is initially greyed out (disabled) when no organization (BU or Espace) exists in DB
    expect(screen.getByTestId("rbac-grants-disabled-no-org-hint")).toBeDefined();
    expect((screen.getByTestId("rbac-subject-type-select") as HTMLSelectElement).disabled).toBe(
      true,
    );
    expect((screen.getByTestId("rbac-subject-input") as HTMLInputElement).disabled).toBe(true);
    expect((screen.getByTestId("rbac-scope-preset-select") as HTMLSelectElement).disabled).toBe(
      true,
    );
    expect((screen.getByTestId("rbac-effect-select") as HTMLSelectElement).disabled).toBe(true);
    expect((screen.getByTestId("rbac-verb-checkbox-all") as HTMLInputElement).disabled).toBe(true);
    expect((screen.getByTestId("create-rbac-grant-btn") as HTMLButtonElement).disabled).toBe(true);

    // 2. Create a BU ("BU Finance") and a linked Espace ("Espace Comptabilité") -> unlocks Section 2!
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "BU Finance" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    expect(screen.getByTestId("org-unit-row-org-1").textContent).toContain("BU Finance");

    // Section 2 is now unlocked!
    expect(screen.queryByTestId("rbac-grants-disabled-no-org-hint")).toBeNull();
    expect((screen.getByTestId("rbac-subject-input") as HTMLInputElement).disabled).toBe(false);
    expect((screen.getByTestId("rbac-scope-preset-select") as HTMLSelectElement).disabled).toBe(
      false,
    );
    expect((screen.getByTestId("create-rbac-grant-btn") as HTMLButtonElement).disabled).toBe(false);

    fireEvent.change(screen.getByTestId("org-unit-level-select"), {
      target: { value: "TEAM" },
    });
    // Parent BU selector is displayed for Espace (TEAM)
    const parentSelect = screen.getByTestId("org-unit-parent-select") as HTMLSelectElement;
    expect(parentSelect.value).toBe("org-1");

    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Espace Comptabilité" },
    });
    fireEvent.change(screen.getByTestId("org-unit-slug-input"), {
      target: { value: "aqwZSX" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));

    // Verify TopHeader workspace selector opens a dropdown list instead of blindly cycling
    const wsTrigger = screen.getByTestId("topbar-fixed-workspace-selector");
    expect(wsTrigger.textContent).toContain("Plateforme Globale ORCIA");
    fireEvent.click(wsTrigger);
    const dropdownMenu = screen.getByTestId("topbar-workspace-dropdown-menu");
    expect(dropdownMenu.textContent).toContain("BU Finance");
    expect(dropdownMenu.textContent).toContain("Espace Comptabilité");
    fireEvent.click(screen.getByTestId("topbar-workspace-option-org-1"));
    expect(wsTrigger.textContent).toContain("BU Finance");

    // Attempt to delete parent BU while child Espace is attached -> blocked by orphan protection
    fireEvent.click(screen.getByTestId("delete-org-unit-btn-org-1"));
    fireEvent.click(screen.getByTestId("confirm-delete-org-unit-btn-org-1"));
    const feedback = screen.getByTestId("org-unit-delete-feedback");
    expect(feedback.textContent).toContain("Suppression refusée");
    expect(screen.getByTestId("org-unit-row-org-1")).toBeDefined();

    // 3 & 4. Habilitations: Beneficiary (Chef1) vs Target Scope selected from the single dropdown (aqwZSX), "Tous" checkbox, and French display
    fireEvent.change(screen.getByTestId("rbac-subject-input"), {
      target: { value: "Chef1" },
    });
    fireEvent.change(screen.getByTestId("rbac-scope-preset-select"), {
      target: { value: "aqwZSX" },
    });
    // Click "Tous" verb checkbox to select all 6 verbs
    fireEvent.click(screen.getByTestId("rbac-verb-checkbox-all"));
    fireEvent.click(screen.getByTestId("create-rbac-grant-btn"));

    const grantRow = screen.getByTestId("rbac-grant-row-grant-1");
    expect(grantRow.textContent).toContain("Rôle : Chef1");
    expect(grantRow.textContent).not.toContain("(ROLE:");
    expect(grantRow.textContent).toContain("Périmètre cible :");
    expect(grantRow.textContent).toContain("Équipe : Espace Comptabilité (aqwZSX)");
    expect(grantRow.textContent).toContain("Déléguer des droits · Autorisé");
    expect(grantRow.textContent).not.toContain("(ALLOW)");

    // Select all grants via "Tous" checkbox and bulk delete
    fireEvent.click(screen.getByTestId("rbac-grants-select-all-checkbox"));
    fireEvent.click(screen.getByTestId("rbac-grants-bulk-delete-btn"));
    expect(screen.getByTestId("iam-grants-empty-state")).toBeDefined();

    // 5. Right-hand contextual help explains Target Scope, BU vs Équipe vs Espace de travail, and Beneficiary vs Target Scope
    const helpTerms = screen.getByTestId("help-accordion-terms-content");
    expect(helpTerms.textContent).toContain("INHERITANCE_BLOCK");
    expect(helpTerms.textContent).toContain("Rôle : Chef1");
    expect(helpTerms.textContent).toContain("aqwZSX");
    expect(helpTerms.textContent).toContain("BU vs Équipe vs Espace de travail");

    // 6. Clicking ContextualInfoTriggerButton ('i') re-opens the right-hand contextual help column if closed and highlights the targeted section (including iam-target-scope)
    fireEvent.click(screen.getByTestId("topbar-contextual-help-toggle"));
    expect(screen.queryByTestId("four-zone-contextual-help-column")).toBeNull();

    fireEvent.click(screen.getByTestId("contextual-info-trigger-iam-org-tree"));
    expect(screen.getByTestId("four-zone-contextual-help-column")).toBeDefined();
    expect(
      screen.getByTestId("help-section-iam-org-tree").getAttribute("data-active"),
    ).toBe("true");

    fireEvent.click(screen.getByTestId("contextual-info-trigger-iam-role-grants"));
    expect(
      screen.getByTestId("help-section-iam-role-grants").getAttribute("data-active"),
    ).toBe("true");
    expect(
      screen.getByTestId("help-section-iam-org-tree").getAttribute("data-active"),
    ).toBe("false");

    fireEvent.click(screen.getByTestId("contextual-info-trigger-iam-target-scope"));
    const targetScopeHelpSection = screen.getByTestId("help-section-iam-target-scope");
    expect(targetScopeHelpSection.getAttribute("data-active")).toBe("true");
    expect(targetScopeHelpSection.textContent).toContain("Qu'est-ce que le Périmètre cible");
  });

  it("enforces zero internal ORCIA implementation jargon across all user-facing FR and EN i18n dictionaries", () => {
    const collectLeafStrings = (obj: unknown): string[] => {
      if (typeof obj === "string") {
        return [obj];
      }
      if (Array.isArray(obj)) {
        return obj.flatMap(collectLeafStrings);
      }
      if (typeof obj === "object" && obj !== null) {
        return Object.values(obj).flatMap(collectLeafStrings);
      }
      return [];
    };

    const allStrings = [
      ...collectLeafStrings(frDictionary),
      ...collectLeafStrings(enDictionary),
    ].join("\n");

    const forbiddenJargonPatterns: RegExp[] = [
      /\bDBOS\b/i,
      /\bPostgreSQL 18\b/i,
      /\bPG18\b/i,
      /\bpgvector\b/i,
      /\bhalfvec\b/i,
      /\bdomain_events_outbox\b/i,
      /\bWasmtime\b/i,
      /\bStarlark\b/i,
      /\bArgon2id\b/i,
      /\bOIDC PKCE\b/i,
      /\bRubber-Stamping\b/i,
      /\bhuman_authored_required\b/i,
      /\bWAITING_FOR_HUMAN_ARBITRATION\b/i,
      /\bCONTRIBUTOR_ACTION_REQUIRED\b/i,
      /\bREAD_ONLY_OBSERVER\b/i,
      /\bORCIA_BOOTSTRAP_TOKEN\b/i,
    ];

    for (const pattern of forbiddenJargonPatterns) {
      expect(allStrings).not.toMatch(pattern);
    }
  });

  it("survives full F5 page reload (unmount -> render): preserves Day-0 Admin, AI model, Workspace, and unlocked sidebar entries", async () => {
    const queryClient1 = createOrciaQueryClient();
    const history1 = createMemoryHistory({ initialEntries: ["/settings"] });
    const router1 = createOrciaRouter({ queryClient: queryClient1, history: history1 });
    await router1.load();

    const firstRender = render(
      <QueryClientProvider client={queryClient1}>
        <RouterProvider router={router1} />
      </QueryClientProvider>,
    );

    // 1. Complete First-Boot Platform Admin Modal
    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), {
      target: { value: "Romain Persistant" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), {
      target: { value: "romain.persist@orcia.fr" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-password-input"), {
      target: { value: "Secret123456!" },
    });
    fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));
    expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();

    // 2. Configure an AI model in /settings -> AI Models tab (unlocks Mon Assistant & Mes Agents)
    fireEvent.click(screen.getByTestId("settings-tab-ai-models"));
    fireEvent.change(screen.getByTestId("llm-primary-model-input"), {
      target: { value: "claude-3-7-sonnet-persist" },
    });
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));

    // 3. Configure a Workflow in /settings -> Workflows tab (unlocks Mes Processus)
    fireEvent.click(screen.getByTestId("settings-tab-workflows"));
    fireEvent.change(screen.getByTestId("workflow-key-input"), {
      target: { value: "wf-persist" },
    });
    fireEvent.change(screen.getByTestId("workflow-title-input"), {
      target: { value: "Workflow Persistant" },
    });
    fireEvent.click(screen.getByTestId("save-workflow-btn"));

    // 4. Navigate to /workspaces and create a Workspace (unlocks FinOps)
    await act(async () => {
      await router1.navigate({ to: "/workspaces" });
    });
    fireEvent.change(screen.getByTestId("workspace-name-input"), {
      target: { value: "Espace Survie F5" },
    });
    fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));

    // Simulate F5 full browser reload by unmounting the entire React tree and mounting a fresh router
    firstRender.unmount();

    const queryClient2 = createOrciaQueryClient();
    const history2 = createMemoryHistory({ initialEntries: ["/cockpit"] });
    const router2 = createOrciaRouter({ queryClient: queryClient2, history: history2 });
    await router2.load();

    render(
      <QueryClientProvider client={queryClient2}>
        <RouterProvider router={router2} />
      </QueryClientProvider>,
    );

    // Verify First-Boot Admin Modal does NOT reappear after F5
    expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
    expect(screen.getByTestId("user-account-dropdown-trigger").textContent).toContain(
      "Romain Persistant",
    );

    // Verify all unlocked sidebar items remain unlocked after F5
    expect(
      (screen.getByTestId("eight-menu-item-assistant") as HTMLButtonElement).disabled,
    ).toBe(false);
    expect(
      (screen.getByTestId("eight-menu-item-agents") as HTMLButtonElement).disabled,
    ).toBe(false);
    expect(
      (screen.getByTestId("eight-menu-item-processes") as HTMLButtonElement).disabled,
    ).toBe(false);
    expect(
      (screen.getByTestId("eight-menu-item-finops") as HTMLButtonElement).disabled,
    ).toBe(false);

    // Verify onboarding progress badge is 3/5 (AI model + Workspace + Workflow)
    expect(screen.getByTestId("onboarding-progress-badge").textContent).toBe("3/5");
  });

  it("supports creating Skills, creating Agents, attaching Skills in 1 click, executing both, and surviving F5 reload on /agents", async () => {
    const { resetCachedAgentsAndSkillsForTest } = await import(
      "../features/catalog/index"
    );
    resetCachedAgentsAndSkillsForTest();

    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/agents"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    const firstRender = render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    expect(screen.getByTestId("agents-and-skills-manager-view")).toBeDefined();
    expect(screen.getByTestId("agents-empty-state")).toBeDefined();

    // 1. Switch to Skills tab and create a Skill
    fireEvent.click(screen.getByTestId("agents-subview-tab-skills"));
    fireEvent.change(screen.getByTestId("skill-name-input"), {
      target: { value: "Analyse Conformité Fournisseur" },
    });
    fireEvent.change(screen.getByTestId("skill-objective-input"), {
      target: { value: "Détecter les clauses contractuelles à risque" },
    });
    fireEvent.change(screen.getByTestId("skill-instructions-input"), {
      target: { value: "Vérifier la responsabilité, la réversibilité et la juridiction." },
    });
    fireEvent.click(screen.getByTestId("create-skill-submit-btn"));

    const skillId = "skill-analyse-conformite-fournisseur";
    expect(screen.getByTestId(`skill-card-${skillId}`)).toBeDefined();

    // Execute Skill in 1 click
    fireEvent.change(screen.getByTestId(`skill-test-input-${skillId}`), {
      target: { value: "Article 12 : plafond de responsabilité limité à 1 mois" },
    });
    fireEvent.click(screen.getByTestId(`run-skill-btn-${skillId}`));
    expect(screen.getByTestId(`skill-execution-output-${skillId}`).textContent).toContain(
      "Analyse Conformité Fournisseur",
    );

    // 2. Switch to Agents tab, create an Agent with the Skill attached, and execute it
    fireEvent.click(screen.getByTestId("agents-subview-tab-agents"));
    fireEvent.change(screen.getByTestId("agent-name-input"), {
      target: { value: "Expert Achats IT" },
    });
    fireEvent.change(screen.getByTestId("agent-role-input"), {
      target: { value: "Sécuriser les contrats logiciels et cloud" },
    });
    fireEvent.change(screen.getByTestId("agent-instructions-input"), {
      target: { value: "Toujours produire une synthèse claire avec recommandations." },
    });
    fireEvent.click(screen.getByTestId(`create-agent-skill-checkbox-${skillId}`));
    fireEvent.click(screen.getByTestId("create-agent-submit-btn"));

    const agentId = "agent-expert-achats-it";
    expect(screen.getByTestId(`agent-card-${agentId}`)).toBeDefined();

    fireEvent.change(screen.getByTestId(`agent-test-input-${agentId}`), {
      target: { value: "Examine le contrat SaaS Acme" },
    });
    fireEvent.click(screen.getByTestId(`run-agent-btn-${agentId}`));
    expect(screen.getByTestId(`agent-execution-output-${agentId}`).textContent).toContain(
      "Analyse Conformité Fournisseur",
    );

    // 3. Simulate F5 reload: unmount and re-render on /agents
    firstRender.unmount();

    const queryClientAfterF5 = createOrciaQueryClient();
    const historyAfterF5 = createMemoryHistory({ initialEntries: ["/agents"] });
    const routerAfterF5 = createOrciaRouter({
      queryClient: queryClientAfterF5,
      history: historyAfterF5,
    });
    await routerAfterF5.load();

    render(
      <QueryClientProvider client={queryClientAfterF5}>
        <RouterProvider router={routerAfterF5} />
      </QueryClientProvider>,
    );

    // Verify Agent and its execution output survived F5
    expect(screen.getByTestId(`agent-card-${agentId}`)).toBeDefined();
    expect(screen.getByTestId(`agent-execution-output-${agentId}`).textContent).toContain(
      "Examine le contrat SaaS Acme",
    );

    // Verify Skill also survived F5
    fireEvent.click(screen.getByTestId("agents-subview-tab-skills"));
    expect(screen.getByTestId(`skill-card-${skillId}`)).toBeDefined();

    // Verify visual removal of Connections tab, CatalogExplorerPanel, and RemoteServiceTestBench at bottom of /agents
    expect(screen.getByTestId("agents-subview-tab-connections").style.display).toBe("none");
    expect(screen.getByTestId("catalog-explorer-panel-wrapper").style.display).toBe("none");
    expect(screen.getByTestId("remote-service-test-bench-wrapper").style.display).toBe("none");

    // 4. Load Business Pack Agents & Skills in 1 click and verify 📦 Pack Métier badges appear
    fireEvent.click(screen.getByTestId("agents-subview-tab-agents"));
    fireEvent.click(screen.getByTestId("load-pack-agents-templates-btn"));
    expect(screen.getByTestId("agent-card-agent-architecte-solution")).toBeDefined();
    expect(
      screen.getByTestId("agent-visibility-badge-agent-architecte-solution").textContent,
    ).toContain("📦 Pack Métier (orcia-pack-sdlc)");

    // 5. Click '💬 Utiliser dans Mon Assistant' -> redirects to /assistant with @architecte-solution pre-filled!
    fireEvent.click(
      screen.getByTestId("use-agent-in-assistant-btn-agent-architecte-solution"),
    );

    const assistantInput = screen.getByTestId(
      "assistant-three-speed-input",
    ) as HTMLInputElement;
    expect(assistantInput.value).toBe("@architecte-solution ");

    // Verify @ autocomplete dropdown works with created agents in Mon Assistant
    fireEvent.change(assistantInput, { target: { value: "@expert" } });
    expect(screen.getByTestId("assistant-autocomplete-dropdown")).toBeDefined();
    fireEvent.click(
      screen.getByTestId("assistant-autocomplete-option-expert-achats-it"),
    );
    expect(assistantInput.value).toBe("@expert-achats-it ");

    resetCachedAgentsAndSkillsForTest();
  });

  it("enforces RGAA Escape, Annuler, Unsaved Changes Guard, and Enter submit on First-Boot Admin Setup Modal", () => {
    const { unmount } = render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={mockPush}>
          <ModuleWorkspaceView moduleKey="cockpit" />
        </ShellContainer>
      </I18nProvider>,
    );

    // 1. Clean modal closes immediately on Escape
    expect(screen.getByTestId("first-boot-admin-setup-modal")).toBeDefined();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
    unmount();

    // 2. Re-mount, type in inputs -> dirty state -> Escape triggers unsaved changes alertdialog
    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={mockPush}>
          <ModuleWorkspaceView moduleKey="cockpit" />
        </ShellContainer>
      </I18nProvider>,
    );

    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), {
      target: { value: "Hélène Admin" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), {
      target: { value: "helene@orcia.fr" },
    });

    // Press Escape while dirty -> alertdialog appears, modal stays open
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.getByTestId("first-boot-admin-unsaved-changes-alert")).toBeDefined();
    expect(screen.getByTestId("first-boot-admin-setup-modal")).toBeDefined();

    // Click "Continuer l'édition" (stay)
    fireEvent.click(screen.getByTestId("first-boot-admin-unsaved-stay-btn"));
    expect(screen.queryByTestId("first-boot-admin-unsaved-changes-alert")).toBeNull();

    // 3. Focus the submit button and press Enter -> creates admin and closes modal
    const submitBtn = screen.getByTestId("first-boot-admin-submit-btn");
    submitBtn.focus();
    fireEvent.keyDown(submitBtn, { key: "Enter" });

    expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
    expect(screen.getByTestId("user-account-dropdown-trigger").textContent).toContain(
      "Hélène Admin",
    );
  });

  it("configures AI Models with Provider, Model, Endpoint URL, Authentication Mode (API Key or Local), tests LLM connectivity via 'Tester la connexion au modèle', displays French labels without 'medium' or 'family-a', and pins contextual help at top with independent scroll", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // Verify independent scroll containers on Zone 3 (main) and Zone 4 (help column)
    const mainZone = screen.getByTestId("four-zone-central-workspace");
    const helpZone = screen.getByTestId("four-zone-contextual-help-column");
    expect(mainZone.style.overflowY).toBe("auto");
    expect(helpZone.style.overflowY).toBe("auto");

    // Switch to AI Models tab
    fireEvent.click(screen.getByTestId("settings-tab-ai-models"));
    const aiSection = screen.getByTestId("settings-ai-models-section");
    expect(aiSection.textContent).not.toContain("family-a");

    // Default provider is "Anthropic", not "family-a"
    const familyInput = screen.getByTestId("llm-family-input") as HTMLInputElement;
    expect(familyInput.value).toBe("Anthropic");
    const endpointInput = screen.getByTestId("llm-endpoint-url-input") as HTMLInputElement;
    expect(endpointInput.value).toBe("https://api.anthropic.com/v1");

    // 1. Click "Tester la connexion au modèle" while model is empty -> explicit error banner
    fireEvent.click(screen.getByTestId("test-llm-connection-btn"));
    expect(screen.getByTestId("llm-connection-test-result").getAttribute("data-ok")).toBe(
      "false",
    );
    expect(screen.getByTestId("llm-connection-test-result").textContent).toContain(
      "Échec du test",
    );

    // 2. Fill model name, keep authMode = "api_key" without key -> explicit error asking for API key
    fireEvent.change(screen.getByTestId("llm-primary-model-input"), {
      target: { value: "claude-3-7-sonnet" },
    });
    fireEvent.click(screen.getByTestId("test-llm-connection-btn"));
    expect(screen.getByTestId("llm-connection-test-result").getAttribute("data-ok")).toBe(
      "false",
    );
    expect(screen.getByTestId("llm-connection-test-result").textContent).toContain(
      "clé d'API",
    );

    // 3. Enter API key and click "Tester la connexion au modèle" -> Success!
    fireEvent.change(screen.getByTestId("llm-api-key-input"), {
      target: { value: "sk-ant-test-key-12345" },
    });
    fireEvent.click(screen.getByTestId("test-llm-connection-btn"));
    expect(screen.getByTestId("llm-connection-test-result").getAttribute("data-ok")).toBe(
      "true",
    );
    expect(screen.getByTestId("llm-connection-test-result").textContent).toContain(
      "Connexion réussie au modèle « claude-3-7-sonnet » (Anthropic) sur https://api.anthropic.com/v1",
    );

    // 4. Save the tier and verify human-readable French labels (no raw "medium", "balanced", "default", or "family-a")
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));
    const savedRow = screen.getByTestId("llm-tier-row-medium");
    expect(savedRow.textContent).toContain("Standard");
    expect(savedRow.textContent).toContain("claude-3-7-sonnet");
    expect(savedRow.textContent).toContain("Anthropic · Équilibré");
    expect(savedRow.textContent).toContain("https://api.anthropic.com/v1");
    expect(savedRow.textContent).toContain("Clé d'API enregistrée");
    expect(savedRow.textContent).not.toContain("family-a");

    // 5. Click 'i' (contextual-info-trigger-ai-models-overview) -> pins ai-models-overview to index 0 of contextual help sections
    fireEvent.click(screen.getByTestId("contextual-info-trigger-ai-models-overview"));
    const helpSectionsList = screen.getByTestId("contextual-help-sections-list");
    expect(helpSectionsList.children[0]?.getAttribute("data-testid")).toBe(
      "help-section-ai-models-overview",
    );
    expect(helpSectionsList.children[0]?.getAttribute("data-active")).toBe("true");
  });

  it("presents the backend-known Business Packs catalog in /settings (Packs Métiers tab) without free-text SemVer or raw 'GLOBAL' input, and supports 1-click activation and deactivation across scopes", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // Create a BU so it appears in the scope selector
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Direction Produit" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));

    // Switch to Packs Métiers tab
    fireEvent.click(screen.getByTestId("settings-tab-packs"));
    expect(screen.getByTestId("settings-packs-section")).toBeDefined();

    // Free-text version input and redundant header pack selector / button are completely eliminated
    expect(screen.queryByTestId("pack-version-input")).toBeNull();
    expect(screen.queryByTestId("pack-key-input")).toBeNull();
    expect(screen.queryByTestId("save-pack-btn")).toBeNull();

    // Installed packs catalog cards are directly displayed with human-readable titles
    const sdlcCard = screen.getByTestId("installed-pack-card-orcia-pack-sdlc");
    expect(sdlcCard.textContent).toContain("Ingénierie Logicielle & Cycle de Vie Produit");
    expect(sdlcCard.textContent).toContain("4 processus · 6 agents spécialisés");

    const builderCard = screen.getByTestId("installed-pack-card-orcia-pack-builder");
    expect(builderCard.textContent).toContain(
      "Atelier de Création & Gouvernance de Packs Métiers",
    );

    // Scope selector displays "Plateforme entière" (not raw "GLOBAL" in visible text) and the created BU
    const scopeSelect = screen.getByTestId("pack-scope-input") as HTMLSelectElement;
    expect(scopeSelect.textContent).toContain("Plateforme entière");
    expect(scopeSelect.textContent).toContain("Direction · Direction Produit");

    // 1. Activate orcia-pack-sdlc on "Direction · Direction Produit" first
    expect(screen.getByTestId("packs-empty-state")).toBeDefined();
    fireEvent.change(scopeSelect, { target: { value: "direction-produit" } });
    fireEvent.click(screen.getByTestId("activate-pack-btn-orcia-pack-sdlc"));
    expect(screen.getAllByTestId("pack-row-orcia-pack-sdlc").length).toBe(1);
    expect(screen.getByTestId("pack-row-orcia-pack-sdlc").textContent).toContain(
      "Direction · Direction Produit",
    );

    // 2. Switch scope to "Plateforme entière" (GLOBAL) and activate -> automatically deduplicates the sub-scope activation
    fireEvent.change(scopeSelect, { target: { value: "GLOBAL" } });
    fireEvent.click(screen.getByTestId("activate-pack-btn-orcia-pack-sdlc"));
    const rowsAfterGlobal = screen.getAllByTestId("pack-row-orcia-pack-sdlc");
    expect(rowsAfterGlobal.length).toBe(1);
    expect(rowsAfterGlobal[0]?.textContent).toContain("Plateforme entière");
    expect(rowsAfterGlobal[0]?.textContent).not.toContain("Direction · Direction Produit");

    // 1-click deactivation from the card button
    fireEvent.click(screen.getByTestId("deactivate-pack-btn-orcia-pack-sdlc"));
    expect(screen.getByTestId("packs-empty-state")).toBeDefined();

    // Contextual info trigger ('i') opens the right-hand help column on 'packs-overview'
    fireEvent.click(screen.getByTestId("contextual-info-trigger-packs-overview"));
    expect(
      screen.getByTestId("help-section-packs-overview").getAttribute("data-active"),
    ).toBe("true");
  });

  it("enforces anti-LastPass / password-manager attributes on 100% of <form>, <input>, and <textarea> elements across @orcia/ui and apps/web while explicitly preserving /login (BiModeLoginView)", async () => {
    const webSrcDir = path.resolve(__dirname, "..");
    const uiSrcDir = path.resolve(__dirname, "../../../../packages/ui/src");
    const allTsxFiles = [...walkTsFiles(webSrcDir), ...walkTsFiles(uiSrcDir)].filter((f) =>
      f.endsWith(".tsx"),
    );

    const extractOpeningTags = (source: string, tagName: "input" | "textarea" | "form"): string[] => {
      const results: string[] = [];
      const regex = new RegExp(`<${tagName}\\b`, "g");
      let match: RegExpExecArray | null = null;
      while ((match = regex.exec(source)) !== null) {
        const startIdx = match.index;
        let idx = startIdx + match[0].length;
        let braceDepth = 0;
        let inSingleQuote = false;
        let inDoubleQuote = false;
        let inTemplate = false;
        while (idx < source.length) {
          const ch = source[idx];
          const prev = source[idx - 1];
          if (inSingleQuote) {
            if (ch === "'" && prev !== "\\") inSingleQuote = false;
          } else if (inDoubleQuote) {
            if (ch === '"' && prev !== "\\") inDoubleQuote = false;
          } else if (inTemplate) {
            if (ch === "`" && prev !== "\\") inTemplate = false;
          } else {
            if (ch === "'") inSingleQuote = true;
            else if (ch === '"') inDoubleQuote = true;
            else if (ch === "`") inTemplate = true;
            else if (ch === "{") braceDepth++;
            else if (ch === "}") braceDepth = Math.max(0, braceDepth - 1);
            else if (ch === ">" && braceDepth === 0) {
              idx++;
              break;
            }
          }
          idx++;
        }
        results.push(source.slice(startIdx, idx));
      }
      return results;
    };

    let auditedFormsCount = 0;
    let auditedInputsCount = 0;
    let auditedTextareasCount = 0;

    for (const filePath of allTsxFiles) {
      const content = fs.readFileSync(filePath, "utf-8");
      const relPath = path.relative(path.resolve(__dirname, "../../../.."), filePath);
      const isLoginView = filePath.endsWith("BiModeLoginView.tsx");

      if (isLoginView) {
        // /login MUST preserve type="password", autoComplete="current-password", autoComplete="username", and data-allow-password-manager="true"
        expect(content).toContain('type="password"');
        expect(content).toContain('autoComplete="current-password"');
        expect(content).toContain('autoComplete="username"');
        expect(content).toContain('data-allow-password-manager="true"');
        expect(content).not.toContain('data-lpignore="true"');
        continue;
      }

      // Zero type="password" allowed outside BiModeLoginView.tsx
      expect(
        content.includes('type="password"'),
        `Forbidden type="password" outside BiModeLoginView.tsx in ${relPath}`,
      ).toBe(false);

      const forms = extractOpeningTags(content, "form");
      for (const formTag of forms) {
        auditedFormsCount++;
        expect(
          formTag.includes('autoComplete="off"'),
          `Missing autoComplete="off" on <form> in ${relPath}: ${formTag}`,
        ).toBe(true);
        expect(
          formTag.includes('data-lpignore="true"'),
          `Missing data-lpignore="true" on <form> in ${relPath}: ${formTag}`,
        ).toBe(true);
        expect(
          formTag.includes('data-form-type="other"'),
          `Missing data-form-type="other" on <form> in ${relPath}: ${formTag}`,
        ).toBe(true);
      }

      const inputs = extractOpeningTags(content, "input");
      for (const inputTag of inputs) {
        if (inputTag.includes("{...loginProps}")) continue;
        auditedInputsCount++;
        expect(
          inputTag.includes('autoComplete="off"'),
          `Missing autoComplete="off" on <input> in ${relPath}: ${inputTag}`,
        ).toBe(true);
        expect(
          inputTag.includes('data-lpignore="true"'),
          `Missing data-lpignore="true" on <input> in ${relPath}: ${inputTag}`,
        ).toBe(true);
        expect(
          inputTag.includes('data-1p-ignore="true"'),
          `Missing data-1p-ignore="true" on <input> in ${relPath}: ${inputTag}`,
        ).toBe(true);
        expect(
          inputTag.includes('data-bwignore="true"'),
          `Missing data-bwignore="true" on <input> in ${relPath}: ${inputTag}`,
        ).toBe(true);
        expect(
          inputTag.includes('data-form-type="other"'),
          `Missing data-form-type="other" on <input> in ${relPath}: ${inputTag}`,
        ).toBe(true);
      }

      const textareas = extractOpeningTags(content, "textarea");
      for (const textareaTag of textareas) {
        if (textareaTag.includes("{...loginProps}")) continue;
        auditedTextareasCount++;
        expect(
          textareaTag.includes('autoComplete="off"'),
          `Missing autoComplete="off" on <textarea> in ${relPath}: ${textareaTag}`,
        ).toBe(true);
        expect(
          textareaTag.includes('data-lpignore="true"'),
          `Missing data-lpignore="true" on <textarea> in ${relPath}: ${textareaTag}`,
        ).toBe(true);
        expect(
          textareaTag.includes('data-1p-ignore="true"'),
          `Missing data-1p-ignore="true" on <textarea> in ${relPath}: ${textareaTag}`,
        ).toBe(true);
        expect(
          textareaTag.includes('data-bwignore="true"'),
          `Missing data-bwignore="true" on <textarea> in ${relPath}: ${textareaTag}`,
        ).toBe(true);
        expect(
          textareaTag.includes('data-form-type="other"'),
          `Missing data-form-type="other" on <textarea> in ${relPath}: ${textareaTag}`,
        ).toBe(true);
      }
    }

    expect(auditedFormsCount).toBeGreaterThanOrEqual(14);
    expect(auditedInputsCount).toBeGreaterThanOrEqual(65);
    expect(auditedTextareasCount).toBeGreaterThanOrEqual(8);

    // Runtime verification on /settings (Modèles IA) + legacy "family-a" normalization
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    const { unmount } = render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByTestId("settings-tab-ai-models"));
    const primaryModelInput = screen.getByTestId("llm-primary-model-input") as HTMLInputElement;
    const apiKeyInput = screen.getByTestId("llm-api-key-input") as HTMLInputElement;

    expect(primaryModelInput.getAttribute("data-lpignore")).toBe("true");
    expect(primaryModelInput.getAttribute("autocomplete")).toBe("off");
    expect(apiKeyInput.getAttribute("type")).toBe("text");
    expect(apiKeyInput.getAttribute("data-lpignore")).toBe("true");
    expect(apiKeyInput.getAttribute("autocomplete")).toBe("off");
    expect(apiKeyInput.className).toContain("orcia-masked-secret-input");

    // Submit a tier with legacy "family-a" value and verify it normalizes to "Fournisseur principal"
    fireEvent.change(screen.getByTestId("llm-family-input"), {
      target: { value: "family-a" },
    });
    fireEvent.change(primaryModelInput, {
      target: { value: "mistral-small-latest" },
    });
    fireEvent.change(apiKeyInput, {
      target: { value: "sk-test-12345" },
    });
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));

    const mediumRow = screen.getByTestId("llm-tier-row-medium");
    expect(mediumRow.textContent).toContain("Fournisseur principal");
    expect(mediumRow.textContent).not.toContain("family-a");
    unmount();

    // Runtime verification on /login (BiModeLoginView)
    const loginHistory = createMemoryHistory({ initialEntries: ["/login"] });
    const loginRouter = createOrciaRouter({ queryClient, history: loginHistory });
    await loginRouter.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={loginRouter} />
      </QueryClientProvider>,
    );

    expect(
      screen.getByTestId("login-page-container").getAttribute("data-allow-password-manager"),
    ).toBe("true");
    fireEvent.click(screen.getByTestId("login-local-accordion-toggle"));
    const loginEmailInput = screen.getByTestId("login-local-email");
    const loginPasswordInput = screen.getByTestId("login-local-password");
    expect(loginEmailInput.getAttribute("autocomplete")).toBe("username");
    expect(loginPasswordInput.getAttribute("type")).toBe("password");
    expect(loginPasswordInput.getAttribute("autocomplete")).toBe("current-password");
    expect(loginPasswordInput.getAttribute("data-lpignore")).toBeNull();
  });

  it("mounts dedicated left-menu '📜 Journal d'Activité' (/activity), removes it from /settings tabs, displays timestamps & author names in French without PackDeactivated/PackRegistered/GLOBAL, filters by default to the connected login's observation scope, supports user / max 100-200 / time-window filters, and separates contextual help from spending caps", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // 1. Initialize connected administrator login ("Romain Admin", "romain@orcia.fr")
    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), {
      target: { value: "Romain Admin" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), {
      target: { value: "romain@orcia.fr" },
    });
    fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));

    // 2. Verify Journal d'Activité is removed from /settings tabs and has its own left-menu entry
    expect(screen.queryByTestId("settings-tab-audit")).toBeNull();
    const activityMenuBtn = screen.getByTestId("eight-menu-item-activity");
    expect(activityMenuBtn.textContent).toContain("Journal d'Activité");

    // 3. Perform actions on two different scopes: a BU ("Direction Produit") and Global Platform (activate/deactivate pack)
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Direction Produit" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));

    fireEvent.click(screen.getByTestId("settings-tab-packs"));
    fireEvent.click(screen.getByTestId("activate-pack-btn-orcia-pack-builder"));
    fireEvent.click(screen.getByTestId("deactivate-pack-btn-orcia-pack-builder"));

    // 4. Click the dedicated left-menu entry '📜 Journal d'Activité' -> navigates to /activity
    fireEvent.click(activityMenuBtn);
    await act(async () => {
      await Promise.resolve();
    });

    const activityPage = screen.getByTestId("activity-log-explorer-page");
    expect(activityPage).toBeDefined();
    expect(activityMenuBtn.getAttribute("aria-current")).toBe("page");

    // 5. Verify zero raw English eventType badges ("PackDeactivated", "PackRegistered", "OrgUnitCreated") or raw "GLOBAL"
    const pageText = activityPage.textContent ?? "";
    for (const forbiddenRaw of [
      "PackDeactivated",
      "PackRegistered",
      "OrgUnitCreated",
      "PlatformAdminInitialized",
      "sur GLOBAL",
      "(PUBLISHED)",
    ]) {
      expect(pageText).not.toContain(forbiddenRaw);
    }
    expect(pageText).toContain("Pack désactivé");
    expect(pageText).toContain("Pack activé");
    expect(pageText).toContain("Plateforme entière");

    // 6. Verify every row displays its timestamp, author name ("Romain Admin (romain@orcia.fr)"), and scope
    const latestEvtTimestamp = screen.getByTestId("activity-event-timestamp-evt-4");
    const latestEvtActor = screen.getByTestId("activity-event-actor-evt-4");
    const latestEvtScope = screen.getByTestId("activity-event-scope-evt-4");
    expect(latestEvtTimestamp.textContent).toMatch(/\d{2}\/\d{2}\/\d{4}\s+\d{2}:\d{2}:\d{2}/);
    expect(latestEvtActor.textContent).toContain("Romain Admin (romain@orcia.fr)");
    expect(latestEvtScope.textContent).toContain("Plateforme entière");

    // 7. Verify default filtering at the connected login's observation level (topbar workspace/scope selector)
    expect(screen.getByTestId("activity-observation-scope-badge").textContent).toContain(
      "Filtré sur votre niveau d'observation : Plateforme entière",
    );
    expect(
      (screen.getByTestId("activity-scope-filter-select") as HTMLSelectElement).value,
    ).toBe("scope-global");

    // Switch the connected user's observation level in the top header bar to "Direction Produit" (org-1)
    fireEvent.click(screen.getByTestId("topbar-fixed-workspace-selector"));
    fireEvent.click(screen.getByTestId("topbar-workspace-option-org-1"));

    // The Activity Log automatically filters to the observed BU ("Direction · Direction Produit")!
    expect(
      (screen.getByTestId("activity-scope-filter-select") as HTMLSelectElement).value,
    ).toBe("org-1");
    expect(screen.getByTestId("activity-observation-scope-badge").textContent).toContain(
      "Direction · Direction Produit",
    );
    // Only the event on Direction Produit (evt-2) is shown; global pack events (evt-3, evt-4) are filtered out
    expect(screen.getByTestId("audit-event-row-evt-2")).toBeDefined();
    expect(screen.queryByTestId("audit-event-row-evt-4")).toBeNull();

    // User can broaden the filter to "Plateforme entière" and reset back to their observation scope in 1 click
    fireEvent.change(screen.getByTestId("activity-scope-filter-select"), {
      target: { value: "scope-global" },
    });
    expect(screen.getByTestId("audit-event-row-evt-4")).toBeDefined();
    fireEvent.click(screen.getByTestId("activity-reset-observation-scope-btn"));
    expect(
      (screen.getByTestId("activity-scope-filter-select") as HTMLSelectElement).value,
    ).toBe("org-1");

    // Switch back to Plateforme entière to test User, Max Limit (100 / 200), and Time Window filters
    fireEvent.change(screen.getByTestId("activity-scope-filter-select"), {
      target: { value: "scope-global" },
    });

    // 8. Test User filter & search, Max Limit (50 / 100 / 200 / 500), and Time Window filter
    const maxLimitSelect = screen.getByTestId("activity-max-limit-select") as HTMLSelectElement;
    expect(maxLimitSelect.value).toBe("100");
    expect(maxLimitSelect.textContent).toContain("100 derniers");
    expect(maxLimitSelect.textContent).toContain("200 derniers");
    fireEvent.change(maxLimitSelect, { target: { value: "200" } });
    expect(maxLimitSelect.value).toBe("200");

    const timeWindowSelect = screen.getByTestId("activity-time-window-select") as HTMLSelectElement;
    expect(timeWindowSelect.value).toBe("ALL");
    fireEvent.change(timeWindowSelect, { target: { value: "24H" } });
    expect(screen.getByTestId("audit-event-row-evt-4")).toBeDefined();

    const userSelect = screen.getByTestId("activity-user-filter-select") as HTMLSelectElement;
    expect(userSelect.textContent).toContain("Romain Admin");
    fireEvent.change(userSelect, { target: { value: "Romain Admin" } });
    expect(screen.getByTestId("audit-event-row-evt-4")).toBeDefined();

    fireEvent.change(screen.getByTestId("activity-user-search-input"), {
      target: { value: "utilisateur-inexistant" },
    });
    expect(screen.getByTestId("audit-events-empty-state")).toBeDefined();

    // 9. Verify the contextual help icon 'i' (audit-overview) explains Activity Log without confusing it with spending caps
    fireEvent.click(screen.getByTestId("contextual-info-trigger-audit-overview"));
    const auditHelpSection = screen.getByTestId("help-section-audit-overview");
    expect(auditHelpSection.getAttribute("data-active")).toBe("true");
    expect(auditHelpSection.textContent).toContain("auteurs, horodatage et filtres d'observation");
    expect(auditHelpSection.textContent).not.toContain("définissez un plafond de dépense par espace");
  });

  it("displays right-aligned red '!' circle badge and red tooltip on all disabled buttons until enabled, populates the Notification Center vs Activity Log, and uses 'Équipe' instead of 'Espace' in Organization management", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // 1. On Day 0, the First-Boot Admin Submit button is disabled and shows the red '!' badge + red tooltip
    const adminSubmitBtn = screen.getByTestId("first-boot-admin-submit-btn") as HTMLButtonElement;
    expect(adminSubmitBtn.disabled).toBe(true);
    const adminAlertIcon = screen.getByTestId(
      "disabled-button-alert-icon-first-boot-admin-submit-btn",
    );
    const adminAlertTooltip = screen.getByTestId(
      "disabled-button-alert-tooltip-first-boot-admin-submit-btn",
    );
    expect(adminAlertIcon.textContent).toContain("!");
    expect(adminAlertTooltip.style.color).toBe("var(--color-status-error)");
    expect(adminAlertTooltip.getAttribute("data-tooltip-text")).toContain(
      "Renseignez le nom complet et l'adresse e-mail",
    );

    // Fill admin form -> button becomes enabled and the red '!' badge + red tooltip disappear!
    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), {
      target: { value: "Romain Admin" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), {
      target: { value: "romain@orcia.fr" },
    });
    expect(adminSubmitBtn.disabled).toBe(false);
    expect(
      screen.queryByTestId("disabled-button-alert-icon-first-boot-admin-submit-btn"),
    ).toBeNull();
    expect(
      screen.queryByTestId("disabled-button-alert-tooltip-first-boot-admin-submit-btn"),
    ).toBeNull();
    fireEvent.click(adminSubmitBtn);

    // 2. Sidebar disabled buttons (assistant, agents, processes, finops) display red '!' circle badge + red tooltip
    const assistantMenuBtn = screen.getByTestId("eight-menu-item-assistant") as HTMLButtonElement;
    expect(assistantMenuBtn.disabled).toBe(true);
    expect(
      screen.getByTestId("disabled-button-alert-icon-eight-menu-item-assistant"),
    ).toBeDefined();
    expect(
      screen
        .getByTestId("disabled-button-alert-tooltip-eight-menu-item-assistant")
        .getAttribute("data-tooltip-text"),
    ).toContain("Configurez au moins un modèle IA");

    // 3. In /settings > Organisation & Habilitations:
    // - Section 1 uses "Directions / BU & Équipes" and "Équipe" (never "Espace (Équipe)")
    const iamSection = screen.getByTestId("settings-iam-section");
    expect(iamSection.textContent).toContain(
      "1. Structure de l'Organisation (Directions / BU & Équipes)",
    );
    expect(iamSection.textContent).not.toContain("Espace (Équipe)");
    const levelSelect = screen.getByTestId("org-unit-level-select") as HTMLSelectElement;
    expect(levelSelect.textContent).toContain("Équipe");
    expect(levelSelect.textContent).not.toContain("Espace");

    // - Section 2 "+ Ajouter la règle" button is disabled and shows the red '!' circle badge + red tooltip
    const createGrantBtn = screen.getByTestId("create-rbac-grant-btn") as HTMLButtonElement;
    expect(createGrantBtn.disabled).toBe(true);
    expect(
      screen.getByTestId("disabled-button-alert-icon-create-rbac-grant-btn"),
    ).toBeDefined();
    expect(
      screen
        .getByTestId("disabled-button-alert-tooltip-create-rbac-grant-btn")
        .getAttribute("data-tooltip-text"),
    ).toContain("Créez d'abord au moins une Direction (BU) ou une Équipe");

    // Create a BU ("Direction Tech") and a Team ("Équipe Plateforme") -> createGrantBtn becomes enabled and its red '!' badge disappears!
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Direction Tech" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    expect(createGrantBtn.disabled).toBe(false);
    expect(
      screen.queryByTestId("disabled-button-alert-icon-create-rbac-grant-btn"),
    ).toBeNull();

    fireEvent.change(levelSelect, { target: { value: "TEAM" } });
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Équipe Plateforme" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    expect(screen.getByTestId("org-unit-row-org-2").textContent).toContain("ÉQUIPE");
    expect(screen.getByTestId("org-unit-row-org-1").textContent).toContain(
      "1 Équipe(s) rattachée(s)",
    );

    // 4. Notification Center (🔔 Notifications) displays active counter badge, actionable setup prerequisites, and distinction vs Journal d'Activité
    const notifBadge = screen.getByTestId("topbar-notifications-badge");
    expect(Number(notifBadge.textContent)).toBeGreaterThanOrEqual(2);
    fireEvent.click(screen.getByTestId("topbar-notifications-toggle"));
    const notifDrawer = screen.getByTestId("topbar-notifications-drawer");
    expect(notifDrawer.textContent).toContain("Aucun modèle IA configuré");
    expect(notifDrawer.textContent).toContain("Aucun Espace de travail créé");
    expect(
      screen.getByTestId("notifications-vs-activity-log-box").textContent,
    ).toContain("Journal d'Activité");

    // Configure an AI model -> assistant & agents menu buttons become enabled and their red '!' badges disappear!
    fireEvent.click(screen.getByTestId("topbar-notifications-close"));
    fireEvent.click(screen.getByTestId("settings-tab-ai-models"));
    fireEvent.change(screen.getByTestId("llm-primary-model-input"), {
      target: { value: "claude-3-7-sonnet" },
    });
    fireEvent.change(screen.getByTestId("llm-api-key-input"), {
      target: { value: "sk-ant-test" },
    });
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));

    expect(assistantMenuBtn.disabled).toBe(false);
    expect(
      screen.queryByTestId("disabled-button-alert-icon-eight-menu-item-assistant"),
    ).toBeNull();
    expect(
      screen.queryByTestId("disabled-button-alert-tooltip-eight-menu-item-assistant"),
    ).toBeNull();

    // Open Notifications drawer and click "📜 Ouvrir le Journal d'Activité →" -> navigates to /activity
    fireEvent.click(screen.getByTestId("topbar-notifications-toggle"));
    fireEvent.click(screen.getByTestId("notifications-open-activity-log-btn"));
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("activity-log-explorer-page")).toBeDefined();
  });

  it("supports Day-0 1st Admin 2-step onboarding (Option 1), multi-team membership, Private Workspaces billed to a Team (Option 2 FinOps), orphan-safe Team deletion, and 3-group TopHeader context switcher", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // 1. Step A: Create Day-0 1st Admin without any pre-existing Team -> memberTeamIds starts empty
    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), {
      target: { value: "Romain Admin" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), {
      target: { value: "romain@orcia.fr" },
    });
    fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));

    // Verify the warning badge in /settings > Organisation & Habilitations shows 0 billing Team attached
    const membershipSummaryBadge = screen.getByTestId("admin-team-membership-summary-badge");
    expect(membershipSummaryBadge.textContent).toContain(
      "Aucune Équipe de facturation rattachée",
    );

    // Verify Notification Center includes the "setup-billing-team-missing" alert
    fireEvent.click(screen.getByTestId("topbar-notifications-toggle"));
    expect(
      screen.getByTestId("notification-center-item-setup-billing-team-missing").textContent,
    ).toContain("Aucune Équipe de facturation rattachée");
    fireEvent.click(screen.getByTestId("topbar-notifications-close"));

    // 2. Step B: Create a BU ("Direction Produit") and two Teams ("Équipe Core IA" & "Équipe Data")
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Direction Produit" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));

    const levelSelect = screen.getByTestId("org-unit-level-select") as HTMLSelectElement;
    fireEvent.change(levelSelect, { target: { value: "TEAM" } });

    // Verify the "Rattacher mon compte à cette équipe" checkbox appears and is checked by default
    const attachCheckbox = screen.getByTestId(
      "org-unit-attach-admin-checkbox",
    ) as HTMLInputElement;
    expect(attachCheckbox.checked).toBe(true);

    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Équipe Core IA" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));

    // Admin is now attached to "Équipe Core IA" (org-2)
    expect(screen.getByTestId("admin-team-membership-summary-badge").textContent).toContain(
      "Équipe Core IA",
    );
    expect(screen.getByTestId("org-unit-member-badge-org-2").textContent).toContain(
      "Membre (Facturation active)",
    );

    // Create a second Team ("Équipe Data", org-3) with attachCheckbox unchecked, then attach in 1 click (Multi-Teams!)
    fireEvent.click(screen.getByTestId("org-unit-attach-admin-checkbox"));
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Équipe Data" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    expect(screen.getByTestId("org-unit-member-badge-org-3").textContent).toContain(
      "Non rattaché",
    );

    // Click "+ Rattacher mon compte" on org-3 -> Admin now belongs to BOTH teams!
    fireEvent.click(screen.getByTestId("toggle-team-membership-btn-org-3"));
    expect(screen.getByTestId("org-unit-member-badge-org-3").textContent).toContain(
      "Membre (Facturation active)",
    );
    expect(screen.getByTestId("admin-team-membership-summary-badge").textContent).toContain(
      "Équipe Core IA, Équipe Data",
    );

    // 3. Navigate to /workspaces and create both a Collective Workspace (STANDARD) and a Private Workspace (PRIVATE_USER, Option 2 FinOps)
    fireEvent.click(screen.getByTestId("eight-menu-item-spaces"));
    await act(async () => {
      await Promise.resolve();
    });

    // Verify create-workspace-submit-btn has DisabledButtonAlertIndicator when name is empty
    const createWsBtn = screen.getByTestId("create-workspace-submit-btn") as HTMLButtonElement;
    expect(createWsBtn.disabled).toBe(true);
    expect(
      screen.getByTestId("disabled-button-alert-icon-create-workspace-submit-btn"),
    ).toBeDefined();

    // Select billing team "Équipe Core IA" (org-2) and visibility "PRIVATE_USER"
    const ownerTeamSelect = screen.getByTestId(
      "workspace-owner-team-select",
    ) as HTMLSelectElement;
    expect(ownerTeamSelect.textContent).toContain("Équipe Core IA");
    expect(ownerTeamSelect.textContent).toContain("Équipe Data");
    fireEvent.change(ownerTeamSelect, { target: { value: "org-2" } });

    const visibilitySelect = screen.getByTestId(
      "workspace-visibility-select",
    ) as HTMLSelectElement;
    expect(visibilitySelect.textContent).toContain("Privé personnel (Facturé à l'équipe)");
    fireEvent.change(visibilitySelect, { target: { value: "PRIVATE_USER" } });

    fireEvent.change(screen.getByTestId("workspace-name-input"), {
      target: { value: "Mon Bac à Sable R&D" },
    });
    expect(createWsBtn.disabled).toBe(false);
    fireEvent.click(createWsBtn);

    // Also create a collective workspace ("Projet Socle IA", STANDARD) under "Équipe Core IA" (org-2)
    fireEvent.change(ownerTeamSelect, { target: { value: "org-2" } });
    fireEvent.change(visibilitySelect, { target: { value: "STANDARD" } });
    fireEvent.change(screen.getByTestId("workspace-name-input"), {
      target: { value: "Projet Socle IA" },
    });
    fireEvent.click(createWsBtn);

    // 4. Open TopHeader Context Switcher and verify the 3 explicit groups:
    // - 🔒 Mes Espaces Privés
    // - 👥 Mes Équipes & Espaces
    // - 🏢 Supervision Organisation
    fireEvent.click(screen.getByTestId("topbar-fixed-workspace-selector"));
    const dropdownMenu = screen.getByTestId("topbar-workspace-dropdown-menu");
    expect(dropdownMenu.textContent).toContain("🔒 Mes Espaces Privés");
    expect(dropdownMenu.textContent).toContain("👥 Mes Équipes & Espaces");
    expect(dropdownMenu.textContent).toContain("🏢 Supervision Organisation");
    expect(dropdownMenu.textContent).toContain("Mon Bac à Sable R&D · Équipe Core IA");
    expect(dropdownMenu.textContent).toContain("Projet Socle IA · Équipe Core IA");

    // Select the Private Workspace ("ws-1") in the TopHeader -> filters /workspaces to that private workspace
    fireEvent.click(screen.getByTestId("topbar-workspace-option-ws-1"));
    expect(screen.getByTestId("workspace-active-scope-banner").textContent).toContain(
      "Mon Bac à Sable R&D",
    );

    // 5. Verify orphan protection in /settings: cannot delete "Équipe Core IA" (org-2) while workspaces are attached to it
    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    await act(async () => {
      await Promise.resolve();
    });
    fireEvent.click(screen.getByTestId("delete-org-unit-btn-org-2"));
    fireEvent.click(screen.getByTestId("confirm-delete-org-unit-btn-org-2"));
    expect(screen.getByTestId("org-unit-delete-feedback").textContent).toContain(
      "2 Espace(s) de Travail sont rattachés à « Équipe Core IA »",
    );
    expect(screen.getByTestId("org-unit-row-org-2")).toBeDefined();
  });

  it("delivers the redesigned Workspaces studio view with quick filters, 1-click private-to-team sharing, inline datasource connection, integrated multi-level Glossary & Business Rules with 1-click promotion, F5 reload survival, and Option A (no visible 📖 Vocabulaire in sidebar)", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    const { unmount } = render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // 1. Option A: Verify 📖 Vocabulaire is visually hidden in the left sidebar (display: none)
    const vocabMenuItem = screen.getByTestId("eight-menu-item-vocabulary");
    expect(vocabMenuItem.style.display).toBe("none");

    // 2. Initialize Day-0 Admin and a Billing Team ("Équipe Produit IA")
    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), {
      target: { value: "Romain Admin" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), {
      target: { value: "romain@orcia.fr" },
    });
    fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));

    const levelSelect = screen.getByTestId("org-unit-level-select") as HTMLSelectElement;
    fireEvent.change(levelSelect, { target: { value: "TEAM" } });
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Équipe Produit IA" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));

    // Verify Global Glossary & Rules tab is accessible in /settings
    fireEvent.click(screen.getByTestId("settings-tab-glossary"));
    expect(screen.getByTestId("workspace-glossary-and-ontology-tab")).toBeDefined();

    // 3. Navigate to 🗂️ Mes Espaces (/workspaces)
    fireEvent.click(screen.getByTestId("eight-menu-item-spaces"));
    await act(async () => {
      await Promise.resolve();
    });

    // Legacy redundant panels are visually hidden (display: none)
    expect(screen.getByTestId("workspaces-legacy-technical-panels").style.display).toBe(
      "none",
    );

    // Create a Private Workspace ("Mon Labo Perso", PRIVATE_USER) and a Team Workspace ("Espace Produit", STANDARD)
    const visibilitySelect = screen.getByTestId(
      "workspace-visibility-select",
    ) as HTMLSelectElement;
    fireEvent.change(visibilitySelect, { target: { value: "PRIVATE_USER" } });
    fireEvent.change(screen.getByTestId("workspace-name-input"), {
      target: { value: "Mon Labo Perso" },
    });
    fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));

    // Expand creation form via "+ Créer un Espace de Travail" button and create a 2nd workspace
    const toggleCreateBtn = screen.getByTestId("toggle-create-workspace-form-btn");
    fireEvent.click(toggleCreateBtn);
    fireEvent.change(visibilitySelect, { target: { value: "STANDARD" } });
    fireEvent.change(screen.getByTestId("workspace-name-input"), {
      target: { value: "Espace Produit" },
    });
    fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));

    // 4. Verify Quick Filters (Tous (2), 👥 Espaces d'Équipe (1), 🔒 Mes Espaces Privés (1))
    expect(screen.getByTestId("workspaces-filter-all").textContent).toContain("Tous (2)");
    expect(screen.getByTestId("workspaces-filter-team").textContent).toContain("(1)");
    expect(screen.getByTestId("workspaces-filter-private").textContent).toContain("(1)");

    fireEvent.click(screen.getByTestId("workspaces-filter-private"));
    expect(screen.getByTestId("workspace-studio-card-ws-1")).toBeDefined();
    expect(screen.queryByTestId("workspace-studio-card-ws-2")).toBeNull();
    fireEvent.click(screen.getByTestId("workspaces-filter-all"));

    // 5. Test 1-click sharing of Private Workspace ("ws-1") to Team ("STANDARD") + Phase auto-save with "✓ Enregistré" badge
    fireEvent.click(screen.getByTestId("share-private-workspace-btn-ws-1"));
    expect(screen.getByTestId("workspace-visibility-badge-ws-1").textContent).toContain(
      "Collectif d'équipe",
    );
    expect(screen.getByTestId("workspace-autosaved-badge-ws-1").textContent).toContain(
      "✓ Enregistré",
    );

    fireEvent.change(screen.getByTestId("workspace-card-phase-select-ws-1"), {
      target: { value: "RUN" },
    });
    expect(
      (screen.getByTestId("workspace-card-phase-select-ws-1") as HTMLSelectElement).value,
    ).toBe("RUN");

    // 6. Test Unified 3-Tab Detail Panel for active workspace ("Mon Labo Perso", ws-1)
    // Tab 1: 📚 Sources & Documents de l'Espace -> connect a source inline without navigating to /settings
    expect(screen.getByTestId("workspace-detail-sources-empty")).toBeDefined();
    const dsSubmitBtn = screen.getByTestId(
      "workspace-inline-ds-submit-btn",
    ) as HTMLButtonElement;
    expect(dsSubmitBtn.disabled).toBe(true);

    fireEvent.change(screen.getByTestId("workspace-inline-ds-alias-input"), {
      target: { value: "Wiki Produit Interne" },
    });
    fireEvent.change(screen.getByTestId("workspace-inline-ds-uri-input"), {
      target: { value: "https://confluence.orcia.fr/spaces/PROD" },
    });
    expect(dsSubmitBtn.disabled).toBe(false);
    fireEvent.click(dsSubmitBtn);
    expect(screen.getByTestId("workspace-detail-source-row-ds-1").textContent).toContain(
      "Wiki Produit Interne",
    );

    // Tab 2: 📖 Glossaire & Règles Métiers (Ontologie) -> multi-level cascade + add term + 1-click upward promotion
    fireEvent.click(screen.getByTestId("workspace-detail-tab-glossary"));
    const cascadeBar = screen.getByTestId("glossary-inheritance-cascade-bar");
    expect(cascadeBar.textContent).toContain("🏢 Entreprise (Global)");
    expect(cascadeBar.textContent).toContain("🏛️ Direction (BU)");
    expect(cascadeBar.textContent).toContain("👥 Équipe (Équipe Produit IA)");
    expect(cascadeBar.textContent).toContain("🗂️ Cet Espace (Mon Labo Perso)");
    // Zero internal ORCIA enum codes in user-facing labels
    expect(cascadeBar.textContent).not.toContain("1_ENTERPRISE");
    expect(cascadeBar.textContent).not.toContain("3_WORKSPACE");

    fireEvent.change(screen.getByTestId("workspace-glossary-term-input"), {
      target: { value: "Marge Brute Récurrente" },
    });
    fireEvent.change(screen.getByTestId("workspace-glossary-definition-input"), {
      target: {
        value: "Revenu récurrent mensuel diminué des coûts directs d'infrastructure IA.",
      },
    });
    fireEvent.click(screen.getByTestId("workspace-glossary-submit-btn"));

    const conceptCard = screen.getByTestId(
      "glossary-concept-card-marge-brute-r-currente",
    );
    expect(conceptCard.textContent).toContain("Marge Brute Récurrente");
    expect(
      screen.getByTestId("glossary-concept-level-badge-marge-brute-r-currente").textContent,
    ).toContain("🗂️ Cet Espace");

    // Promote in 1 click from Workspace (3_WORKSPACE) to Organization/BU (2_DOMAIN) -> shows "✓ Promu" badge
    fireEvent.click(
      screen.getByTestId("promote-glossary-concept-btn-marge-brute-r-currente"),
    );
    expect(
      screen.getByTestId("promoted-glossary-badge-marge-brute-r-currente").textContent,
    ).toContain("✓ Promu");
    expect(
      screen.getByTestId("glossary-concept-level-badge-marge-brute-r-currente").textContent,
    ).toContain("🏛️ Direction (BU)");

    // Tab 3: 👥 Membres, Accès & Consignes -> auto-save workspace instructions
    fireEvent.click(screen.getByTestId("workspace-detail-tab-members"));
    fireEvent.change(screen.getByTestId("workspace-instructions-textarea"), {
      target: { value: "Toujours citer la source Wiki Produit Interne." },
    });
    expect(screen.getByTestId("workspace-instructions-saved-badge").textContent).toContain(
      "✓ Enregistré",
    );

    // 7. F5 Reload Survival Gate: unmount() and re-render() -> verify shared visibility, attached source, and promoted glossary term persist
    unmount();

    const reloadedRouter = createOrciaRouter({
      queryClient: createOrciaQueryClient(),
      history: createMemoryHistory({ initialEntries: ["/workspaces"] }),
    });
    await reloadedRouter.load();
    render(
      <QueryClientProvider client={createOrciaQueryClient()}>
        <RouterProvider router={reloadedRouter} />
      </QueryClientProvider>,
    );

    expect(screen.getByTestId("workspace-visibility-badge-ws-1").textContent).toContain(
      "Collectif d'équipe",
    );
    expect(screen.getByTestId("workspace-detail-source-row-ds-1").textContent).toContain(
      "Wiki Produit Interne",
    );
    fireEvent.click(screen.getByTestId("workspace-detail-tab-glossary"));
    expect(
      screen.getByTestId("glossary-concept-level-badge-marge-brute-r-currente").textContent,
    ).toContain("🏛️ Direction (BU)");
  });
});
