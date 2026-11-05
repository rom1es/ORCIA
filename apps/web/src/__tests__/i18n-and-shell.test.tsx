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

  it("initializes entities across the 6 dedicated /settings tabs and records Outbox audit events", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

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

    // Tab 6: Audit shows the recorded configuration events
    fireEvent.click(screen.getByTestId("settings-tab-audit"));
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
      "e3b0c44298fc",
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
    expect(grantRow.textContent).toContain("Espace : Espace Comptabilité (aqwZSX)");
    expect(grantRow.textContent).toContain("Déléguer des droits · Autorisé");
    expect(grantRow.textContent).not.toContain("(ALLOW)");

    // Select all grants via "Tous" checkbox and bulk delete
    fireEvent.click(screen.getByTestId("rbac-grants-select-all-checkbox"));
    fireEvent.click(screen.getByTestId("rbac-grants-bulk-delete-btn"));
    expect(screen.getByTestId("iam-grants-empty-state")).toBeDefined();

    // 5. Right-hand contextual help explains Target Scope, BU vs Espace, and Beneficiary vs Target Scope
    const helpTerms = screen.getByTestId("help-accordion-terms-content");
    expect(helpTerms.textContent).toContain("INHERITANCE_BLOCK");
    expect(helpTerms.textContent).toContain("Rôle : Chef1");
    expect(helpTerms.textContent).toContain("aqwZSX");
    expect(helpTerms.textContent).toContain("BU vs Espace");

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
});
