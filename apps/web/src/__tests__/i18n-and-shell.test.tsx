import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ModuleWorkspaceView } from "../components/ModuleWorkspaceView";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { resolveModuleFromPathname, ShellContainer } from "../components/ShellContainer";
import { buildCockpitWorkflowPreviewGraph } from "../features/cockpit";
import { InboxFeaturePanel } from "../features/inbox";
import { resetBackgroundAssistantStreamForTests } from "../features/inbox/useAssistantStreamingTurn";
import { I18nProvider } from "../i18n";
import { enDictionary } from "../i18n/locales/en";
import { frDictionary } from "../i18n/locales/fr";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { preloadModuleQueryData, validateOrciaRouteSearch } from "../routes/searchSchema";
import { simulateUnauthenticatedBrowser } from "../stores/authSessionStore";
import { seedVitestPlatformSetupState } from "./vitest.setup";

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
    resetBackgroundAssistantStreamForTests();
    delete (globalThis as Record<string, unknown>).__ORCIA_TEST_KEEP_STREAM_PENDING__;
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

    // 0 / 6 complétées onboarding progress at blank start (zero duplicate badge)
    expect(screen.queryByTestId("onboarding-progress-badge")).toBeNull();
    expect(screen.getByTestId("accostage-progress-pill").textContent).toBe("0 / 6 complétées");
    expect(screen.getByTestId("cockpit-no-workspace-empty-state")).toBeDefined();

    // Unconfigured features (all navigable entries except Cockpit) are greyed out (disabled) at Day 0 without admin
    expect(
      (screen.getByTestId("eight-menu-item-cockpit") as HTMLButtonElement).disabled,
    ).toBe(false);
    expect(
      (screen.getByTestId("eight-menu-item-spaces") as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId("eight-menu-item-configuration") as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId("eight-menu-item-help") as HTMLButtonElement).disabled,
    ).toBe(true);
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
    seedVitestPlatformSetupState(
      {},
      { email: "admin@orcia.fr", displayName: "Admin", roles: ["PLATFORM_ADMIN"] },
    );
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/workspaces"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // Initially empty workspace cards and FinOps is disabled before workspace creation
    expect(screen.getByTestId("workspaces-cards-empty-state")).toBeDefined();
    expect(
      (screen.getByTestId("eight-menu-item-finops") as HTMLButtonElement).disabled,
    ).toBe(true);

    // Create a Workspace via the "+ Nouvel espace" modal form
    fireEvent.click(screen.getByTestId("toggle-create-workspace-form-btn"));
    fireEvent.change(screen.getByTestId("workspace-name-input"), {
      target: { value: "Mon Premier Espace" },
    });
    fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));

    // FinOps is now unlocked in the sidebar!
    await waitFor(() => {
      expect(
        (screen.getByTestId("eight-menu-item-finops") as HTMLButtonElement).disabled,
      ).toBe(false);
    });

    // Navigate to /cockpit -> Onboarding progress is 3 / 6 complétées and Run launcher is unlocked
    await act(async () => {
      await router.navigate({ to: "/cockpit" });
    });
    expect(screen.getByTestId("accostage-progress-pill").textContent).toBe("3 / 6 complétées");
    expect(screen.getByTestId("cockpit-launch-run-form")).toBeDefined();
  });

  it("initializes entities across the 5 dedicated /settings tabs and records Outbox audit events visible in the Activity Log (/activity via FinOps)", async () => {
    seedVitestPlatformSetupState(
      {},
      { email: "admin@orcia.fr", displayName: "Admin", roles: ["PLATFORM_ADMIN"] },
    );
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // Journal d'Activité and Organisation are no longer tabs inside /settings
    expect(screen.queryByTestId("settings-tab-audit")).toBeNull();
    expect(screen.queryByTestId("settings-tab-organization")).toBeNull();

    // Navigate to Mon Organisation (/organization) via dedicated Sidebar menu entry
    expect(screen.queryByTestId("settings-open-organization-link")).toBeNull();
    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    expect(await screen.findByTestId("iam-org-units-empty-state")).toBeDefined();
    await screen.findByTestId("open-create-org-unit-modal-btn");
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Direction Technique" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    expect((await screen.findByTestId("org-unit-row-org-1")).textContent).toContain(
      "Direction Technique",
    );

    // Return to /settings -> Tab 3: AI Models (starts empty, bind tier)
    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    await screen.findByTestId("settings-tab-models");
    fireEvent.click(screen.getByTestId("settings-tab-models"));
    expect(screen.getByTestId("llm-tiers-empty-state")).toBeDefined();
    fireEvent.change(screen.getByTestId("llm-primary-model-input"), {
      target: { value: "model-primary-v1" },
    });
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));
    await waitFor(() => {
      const rows = Array.from(document.querySelectorAll('[data-testid^="llm-tier-row-"]'));
      expect(rows.some((r) => r.textContent?.includes("model-primary-v1"))).toBe(true);
    });

    // Tab 3: Connectors (Direction C deport banner towards /workspaces/$wsId/sources)
    fireEvent.click(screen.getByTestId("settings-tab-connectors"));
    expect(screen.getByTestId("settings-deported-sources-banner")).toBeDefined();
    expect(screen.getByTestId("settings-goto-workspace-sources-btn")).toBeDefined();
    fireEvent.click(screen.getByTestId("settings-goto-workspace-sources-btn"));

    // Navigate to /activity via FinOps -> finops-open-activity-link and verify recorded events
    fireEvent.click(screen.getByTestId("eight-menu-item-finops"));
    const activityLink = await screen.findByTestId("finops-open-activity-link");
    fireEvent.click(activityLink);
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

    await waitFor(() => {
      expect(screen.getByTestId("wizard-step-form-1")).toBeDefined();
    });
    const runnerTextBefore = screen.getByTestId("durable-wizard-runner").textContent ?? "";
    expect(runnerTextBefore).toContain("Étape 1 sur 5");
    expect(runnerTextBefore).toContain("Création d'un Espace de travail d'équipe");
    expect(runnerTextBefore).not.toContain("sdlc_tech_lead");

    fireEvent.change(screen.getByTestId("wizard-input-org-unit"), {
      target: { value: "Équipe Plateforme" },
    });
    fireEvent.click(screen.getByTestId("wizard-complete-step-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("wizard-step-form-2")).toBeDefined();
    });
    expect(screen.getByTestId("durable-wizard-runner").textContent).toContain("Étape 2 sur 5");
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
    expect(screen.queryByTestId("assistant-citations-card-wrapper")).toBeNull();

    // Open the 4-level governance modal/studio
    fireEvent.click(screen.getByTestId("assistant-open-governance-btn"));
    expect(screen.getByTestId("assistant-governance-container")).toBeDefined();
  });

  it("mounts Mes Espaces 5-tabs, DNA Starlark compiler, MCP/A2A Test Bench, Pack Builder Studio, and Help Generator across /spaces, /agents, /processes, and /help (Story 12.3)", async () => {
    seedVitestPlatformSetupState(
      {
        workspaces: [
          {
            workspaceId: "0195f000-0000-7000-8000-000000000311",
            slug: "ws-equipe-alpha",
            name: "Espace Équipe Alpha",
            ownerOrgUnitId: "0192c4e0-0000-7000-8000-000000000101",
            ownerOrgUnitName: "Direction Technique",
            visibilityMode: "STANDARD",
            lifecyclePhase: "BUILD",
            accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
            finopsCostUsd: 0,
          },
        ],
      },
      { email: "admin@orcia.fr", displayName: "Admin", roles: ["PLATFORM_ADMIN"] },
    );
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/spaces"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // /spaces -> WorkspaceFiveTabsAndExternalRebaseView on OVERVIEW (Starlark hidden until Tab 4 GLOSSARY_RULES)
    expect(await screen.findByTestId("workspace-five-tabs-view")).toBeDefined();
    expect(screen.queryByTestId("dna-starlark-glossary-view")).toBeNull();
    fireEvent.click(screen.getByTestId("workspace-tab-GLOSSARY_RULES"));
    expect(await screen.findByTestId("dna-starlark-glossary-view")).toBeDefined();

    // Navigate to /agents -> RemoteServiceTestBenchAndMcpExposureView inside connections tab
    await act(async () => {
      await router.navigate({ to: "/agents" });
    });
    fireEvent.click(screen.getByTestId("agents-subview-tab-connections"));
    expect(screen.getByTestId("remote-service-test-bench")).toBeDefined();

    // Navigate to /processes -> clean tabbed ProcessesHubPage (zero stacked legacy forms or pack builders)
    await act(async () => {
      await router.navigate({ to: "/processes" });
    });
    expect(screen.getByTestId("processes-hub-v2-page")).toBeDefined();
    expect(screen.getByTestId("processes-hub-tabs")).toBeDefined();
    fireEvent.click(screen.getByTestId("processes-tab-validations"));
    expect(screen.getByTestId("processes-active-dossiers-card")).toBeDefined();
    expect(screen.queryByTestId("settings-workflows-section")).toBeNull();
    expect(screen.queryByTestId("pack-builder-studio-view")).toBeNull();

    // Navigate to /gates -> dedicated Adaptive Human Review & Chunk Validation view (zero legacy Process Studio forms)
    await act(async () => {
      await router.navigate({ to: "/gates" });
    });
    expect(screen.getByTestId("gates-dedicated-review-page")).toBeDefined();
    expect(screen.getByTestId("gates-adaptive-human-review-section")).toBeDefined();
    expect(screen.getByTestId("gates-open-human-review-btn")).toBeDefined();
    expect(screen.queryByTestId("settings-workflows-section")).toBeNull();
    expect(screen.queryByTestId("pack-builder-studio-view")).toBeNull();

    // Navigate to /settings/packs -> SimplifiedProcessBuilderSection + PackBuilderProcessesStudioView + HelpArticleGeneratorAndValidatorView
    await act(async () => {
      await router.navigate({ to: "/settings/packs" });
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

    // Story 25.2 (Bug 5): floating ⓘ triggers are removed from main card headers; Zone 4 opens via ? Aide
    expect(screen.queryByTestId("contextual-info-trigger-workflows-overview")).toBeNull();
    if (!screen.queryByTestId("four-zone-contextual-help-column")) {
      fireEvent.click(screen.getByTestId("topbar-contextual-help-toggle"));
    }
    expect(screen.getByTestId("four-zone-contextual-help-column")).toBeDefined();

    // Open "+ Nouveau processus" dialog to access instructions, deliverable contract, and creation form
    fireEvent.click(screen.getByTestId("open-create-process-modal-btn"));
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

    // Verify the dedicated ORCIA Documentation Generation Process card and 1-click actions on /processes
    const docProcessCard = screen.getByTestId("orcia-doc-generation-process-card");
    expect(docProcessCard.textContent).toContain("Génération de la Documentation ORCIA");
    expect(docProcessCard.textContent).toContain("@Rédacteur-Documentation-Orcia");

    // 1-click run: publishes workflow, displays 4 steps summary & FormattedMarkdownContent preview
    fireEvent.click(screen.getByTestId("run-orcia-doc-generation-process-btn"));
    expect(screen.getByTestId("workflow-row-generate-orcia-documentation")).toBeDefined();
    const stepsSummary = screen.getByTestId("orcia-doc-generation-steps-summary");
    expect(stepsSummary.textContent).toContain("Étape 1 — Inventaire du dépôt ORCIA");
    expect(stepsSummary.textContent).toContain(
      "Étape 2 — Génération & Enrichissement des Guides et de la FAQ",
    );
    expect(stepsSummary.textContent).toContain(
      "Étape 3 — Contrôle Qualité Déterministe (validate_help_article)",
    );
    expect(stepsSummary.textContent).toContain(
      "Étape 4 — Publication & Rattachement à Chaud (/showcase & docs/help/)",
    );
    const outputPreview = screen.getByTestId("orcia-doc-generation-output-preview");
    expect(outputPreview.textContent).toContain("Guide Fonctionnel par Écran");
    expect(outputPreview.textContent).toContain("Architecture & Modèle Métier");

    // 1-click load into Process Studio: pre-fills the SimplifiedProcessBuilderSection form
    fireEvent.click(screen.getByTestId("load-orcia-doc-process-in-builder-btn"));
    expect((screen.getByTestId("workflow-key-input") as HTMLInputElement).value).toBe(
      "generate-orcia-documentation",
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

  it("enforces Story 12.4 UX sobriety: First-Boot Platform Admin Modal, zero fictional data (PAY-142/PSD2), zero NFR latency strings, and human-readable Rôle selector", async () => {
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

    // Popover labels exist in FR/EN without emoji prefixes
    expect(frDictionary.userAccountAndSettings.popover.settingsLabel).toBe("Paramètres");
    expect(enDictionary.userAccountAndSettings.popover.settingsLabel).toBe("Settings");

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
    fireEvent.change(screen.getByTestId("first-boot-admin-password-confirm-input"), {
      target: { value: "Secret123456!" },
    });
    fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));

    // Modal closes, top-right login control is gone, and bottom-left account button shows Romain Admin · Administrateur de la plateforme
    await waitFor(() => {
      expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
    });
    expect(screen.queryByTestId("topbar-user-account-trigger")).toBeNull();
    expect(screen.queryByTestId("dropdown-hat-selector")).toBeNull();
    const accountBtn = screen.getByTestId("sidebar-open-my-account-btn");
    expect(accountBtn.textContent).toContain("Romain Admin");
    expect(accountBtn.textContent).toContain("Administrateur de la plateforme");
  });

  it("supports TopHeader workspace dropdown, BU/Espace linkage with orphan-safe deletion, greyed-out section 2 until org exists, single scope selector, zero English parenthetical terms in FR, and contextual help on /settings", async () => {
    seedVitestPlatformSetupState(
      {},
      { email: "admin@orcia.fr", displayName: "Admin", roles: ["PLATFORM_ADMIN", "SECOPS"] },
    );
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // 1. No "(IAM 6 verbes)" jargon in the tabs or header, and no English parenthetical terms in French IAM section
    expect(screen.getByTestId("eight-menu-item-organization").textContent).toContain(
      "Mon Organisation",
    );
    expect(screen.queryByTestId("settings-open-organization-link")).toBeNull();
    expect(screen.getByTestId("settings-tab-iam").textContent).toBe("Comptes & Habilitations");

    fireEvent.click(screen.getByTestId("settings-tab-iam"));
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

    // 1b. Redundant free-text scope/subject inputs and "Tous" verb checkbox are removed; SecOps drawer is collapsed by default
    expect(screen.queryByTestId("rbac-scope-input")).toBeNull();
    expect(screen.queryByTestId("rbac-verb-select")).toBeNull();
    expect(screen.queryByTestId("rbac-subject-input")).toBeNull();
    expect(screen.queryByTestId("rbac-verb-checkbox-all")).toBeNull();
    expect(screen.getByTestId("iam-accounts-directory-card")).toBeDefined();
    expect(screen.queryByTestId("iam-native-role-matrix-card")).toBeNull();
    fireEvent.click(screen.getByTestId("iam-open-role-matrix-modal-btn"));
    expect(screen.getByTestId("iam-native-role-matrix-card")).toBeDefined();
    fireEvent.click(screen.getByTestId("iam-role-matrix-modal-close-btn"));
    expect(screen.queryByTestId("iam-native-role-matrix-card")).toBeNull();
    expect(
      screen.getByTestId("iam-secops-drawer-toggle").getAttribute("aria-expanded"),
    ).toBe("false");

    // 2. Navigate to Mon Organisation (/organization) via Configuration link, create a BU ("BU Finance") and a Team ("Espace Comptabilité")
    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    await screen.findByTestId("open-create-org-unit-modal-btn");
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "BU Finance" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    expect((await screen.findByTestId("org-unit-row-org-1")).textContent).toContain("BU Finance");

    await screen.findByTestId("open-create-org-unit-modal-btn");
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));

    fireEvent.change(screen.getByTestId("org-unit-level-select"), {
      target: { value: "TEAM" },
    });
    // Parent BU selector auto-selects first BU (org-1) when TEAM is selected
    const parentSelect = screen.getByTestId("org-unit-parent-select") as HTMLSelectElement;
    expect(parentSelect.value).toBe("org-1");

    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Espace Comptabilité" },
    });
    fireEvent.change(screen.getByTestId("org-unit-slug-input"), {
      target: { value: "aqwZSX" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    await screen.findByTestId("org-unit-row-org-2");

    // Verify TopHeader workspace selector (when rail is collapsed) opens a dropdown list instead of blindly cycling
    fireEvent.click(screen.getByTestId("sidebar-rail-toggle-btn"));
    const wsTrigger = screen.getByTestId("topbar-fixed-workspace-selector");
    expect(wsTrigger.textContent).toContain("Plateforme Globale ORCIA");
    fireEvent.click(wsTrigger);
    const dropdownMenu = screen.getByTestId("topbar-workspace-dropdown-menu");
    expect(dropdownMenu.textContent).toContain("BU Finance");
    expect(dropdownMenu.textContent).toContain("Espace Comptabilité");
    fireEvent.click(screen.getByTestId("topbar-workspace-option-org-1"));
    expect(wsTrigger.textContent).toContain("BU Finance");
    fireEvent.click(screen.getByTestId("sidebar-rail-toggle-btn"));

    // Attempt to delete parent BU while child Espace is attached -> blocked by orphan protection
    fireEvent.click(screen.getByTestId("delete-org-unit-btn-org-1"));
    expect((screen.getByTestId("confirm-delete-org-unit-btn-org-1") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByTestId("org-unit-delete-blocked-banner").textContent).toContain("Suppression impossible");
    expect(screen.getByTestId("org-unit-row-org-1")).toBeDefined();
    fireEvent.click(screen.getByTestId("cancel-delete-org-unit-btn-org-1"));

    // 3 & 4. Habilitations (Story 17.3 SecOps Drawer): closed Beneficiary select (TEAM_LEAD) vs Target Scope (aqwzsx), individual grant verb, and French display
    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    await screen.findByTestId("settings-tab-iam");
    fireEvent.click(screen.getByTestId("settings-tab-iam"));
    fireEvent.click(screen.getByTestId("iam-secops-drawer-toggle"));
    fireEvent.change(screen.getByTestId("rbac-subject-select"), {
      target: { value: "TEAM_LEAD" },
    });
    fireEvent.change(screen.getByTestId("rbac-scope-preset-select"), {
      target: { value: "aqwzsx" },
    });
    fireEvent.click(screen.getByTestId("rbac-verb-checkbox-grant"));
    fireEvent.click(screen.getByTestId("create-rbac-grant-btn"));

    const grantRow = await screen.findByTestId("rbac-grant-row-grant-1");
    expect(grantRow.textContent).toContain("Rôle : Responsable d'Équipe");
    expect(grantRow.textContent).not.toContain("(ROLE:");
    expect(grantRow.textContent).toContain("Équipe : Espace Comptabilité (aqwzsx)");
    const secopsBodyText = screen.getByTestId("iam-secops-drawer-body").textContent ?? "";
    expect(secopsBodyText).toContain("Déléguer des droits · Autorisé");
    expect(secopsBodyText).not.toContain("(ALLOW)");

    // Select all grants and bulk delete
    fireEvent.click(screen.getByTestId("rbac-grants-select-all-checkbox"));
    fireEvent.click(screen.getByTestId("rbac-grants-bulk-delete-btn"));
    expect(await screen.findByTestId("iam-grants-empty-state")).toBeDefined();

    // 5. Right-hand contextual help explains Target Scope, BU vs Équipe vs Espace de travail, and Beneficiary vs Target Scope without Chef1/aqwZSX
    const helpTerms = screen.getByTestId("help-accordion-terms-content");
    expect(helpTerms.textContent).toContain("Isoler ce périmètre");
    expect(helpTerms.textContent).toContain("Rôle : Responsable Produit");
    expect(helpTerms.textContent).toContain("Équipe Paiement");
    expect(helpTerms.textContent).not.toContain("Chef1");
    expect(helpTerms.textContent).not.toContain("aqwZSX");
    expect(helpTerms.textContent).toContain("BU vs Équipe vs Espace de travail");

    // 6. Story 25.2 (Bug 5): floating ⓘ triggers are removed; ? Aide toggle controls Zone 4 help column
    fireEvent.click(screen.getByTestId("topbar-contextual-help-toggle"));
    expect(screen.queryByTestId("four-zone-contextual-help-column")).toBeNull();

    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    expect(screen.queryByTestId("contextual-info-trigger-iam-org-tree")).toBeNull();
    if (!screen.queryByTestId("four-zone-contextual-help-column")) {
      fireEvent.click(screen.getByTestId("topbar-contextual-help-toggle"));
    }
    expect(screen.getByTestId("four-zone-contextual-help-column")).toBeDefined();
    expect(screen.getByTestId("help-section-org-hierarchy")).toBeDefined();

    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    await screen.findByTestId("settings-tab-iam");
    fireEvent.click(screen.getByTestId("settings-tab-iam"));
    fireEvent.click(screen.getByTestId("iam-open-role-matrix-modal-btn"));
    expect(screen.queryByTestId("contextual-info-trigger-iam-role-grants")).toBeNull();
    fireEvent.click(screen.getByTestId("iam-role-matrix-modal-close-btn"));
    if (!screen.queryByTestId("four-zone-contextual-help-column")) {
      fireEvent.click(screen.getByTestId("topbar-contextual-help-toggle"));
    }
    expect(screen.getByTestId("help-section-iam-role-grants")).toBeDefined();

    const secopsToggle = screen.getByTestId("iam-secops-drawer-toggle");
    if (secopsToggle.getAttribute("aria-expanded") !== "true") {
      fireEvent.click(secopsToggle);
    }
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
    fireEvent.change(screen.getByTestId("first-boot-admin-password-confirm-input"), {
      target: { value: "Secret123456!" },
    });
    fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));
    await waitFor(() => {
      expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
    });

    // 2. Configure an AI model in /settings -> AI Models tab (unlocks Mon Assistant & Mes Agents)
    fireEvent.click(screen.getByTestId("settings-tab-models"));
    fireEvent.change(screen.getByTestId("llm-primary-model-input"), {
      target: { value: "claude-3-7-sonnet-persist" },
    });
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));
    await waitFor(() => {
      expect(
        (screen.getByTestId("eight-menu-item-assistant") as HTMLButtonElement).disabled,
      ).toBe(false);
    });

    // 3. Configure an Organization Unit in /organization (satisfies milestone 2)
    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    await screen.findByTestId("open-create-org-unit-modal-btn");
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Direction Persistance" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    await screen.findByTestId("org-unit-row-org-1");

    // 4. Navigate to /workspaces and create a Workspace (unlocks FinOps)
    await act(async () => {
      await router1.navigate({ to: "/workspaces" });
    });
    fireEvent.click(screen.getByTestId("toggle-create-workspace-form-btn"));
    fireEvent.change(screen.getByTestId("workspace-name-input"), {
      target: { value: "Espace Survie F5" },
    });
    fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));
    await waitFor(() => {
      expect(
        (screen.getByTestId("eight-menu-item-finops") as HTMLButtonElement).disabled,
      ).toBe(false);
    });

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
    expect(screen.getByTestId("sidebar-open-my-account-btn").textContent).toContain(
      "Romain Persistant",
    );

    // Verify all unlocked sidebar items remain unlocked after F5 (hydrated asynchronously from PG18/API)
    await waitFor(() => {
      expect(
        (screen.getByTestId("eight-menu-item-assistant") as HTMLButtonElement).disabled,
      ).toBe(false);
    });
    expect(
      (screen.getByTestId("eight-menu-item-agents") as HTMLButtonElement).disabled,
    ).toBe(false);
    expect(
      (screen.getByTestId("eight-menu-item-processes") as HTMLButtonElement).disabled,
    ).toBe(false);
    expect(
      (screen.getByTestId("eight-menu-item-finops") as HTMLButtonElement).disabled,
    ).toBe(false);

    // Verify onboarding progress badge is 4 / 6 complétées (Admin + AI model + Org Unit + Workspace)
    expect(screen.queryByTestId("onboarding-progress-badge")).toBeNull();
    expect(screen.getByTestId("accostage-progress-pill").textContent).toBe("4 / 6 complétées");
  });

  it("supports creating Skills, creating Agents via modals, configuring & executing both in sandbox modals, and surviving F5 reload on /agents", async () => {
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
    expect(screen.getByTestId("workspace-assistant-pinned-card")).toBeDefined();
    expect(screen.getByTestId("agents-empty-state")).toBeDefined();
    expect(screen.queryByTestId("create-agent-modal")).toBeNull();

    // 1. Switch to Skills tab, open Create Skill Modal, and create a Skill
    fireEvent.click(screen.getByTestId("agents-subview-tab-skills"));
    fireEvent.click(screen.getByTestId("open-create-skill-drawer-btn"));
    expect(screen.getByTestId("create-skill-modal")).toBeDefined();

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
    expect(screen.queryByTestId("create-skill-modal")).toBeNull();

    const skillId = "skill-analyse-conformite-fournisseur";
    expect(screen.getByTestId(`skill-card-${skillId}`)).toBeDefined();

    // Open Skill Detail & Sandbox Modal and execute Skill
    fireEvent.click(screen.getByTestId(`open-skill-detail-modal-btn-${skillId}`));
    expect(screen.getByTestId(`skill-detail-modal-${skillId}`)).toBeDefined();
    fireEvent.change(screen.getByTestId(`skill-test-input-${skillId}`), {
      target: { value: "Article 12 : plafond de responsabilité limité à 1 mois" },
    });
    fireEvent.click(screen.getByTestId(`run-skill-btn-${skillId}`));
    expect(screen.getAllByTestId(`skill-execution-output-${skillId}`)[0]?.textContent).toContain(
      "Analyse Conformité Fournisseur",
    );
    fireEvent.click(screen.getByTestId(`close-skill-detail-modal-btn-${skillId}`));

    // 2. Switch to Agents tab, open Create Agent Modal, create an Agent with the Skill attached, and execute it in Sandbox Modal
    fireEvent.click(screen.getByTestId("agents-subview-tab-agents"));
    fireEvent.click(screen.getByTestId("open-create-agent-drawer-btn"));
    expect(screen.getByTestId("create-agent-modal")).toBeDefined();

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
    expect(screen.queryByTestId("create-agent-modal")).toBeNull();

    const agentId = "agent-expert-achats-it";
    expect(screen.getByTestId(`agent-card-${agentId}`)).toBeDefined();

    fireEvent.click(screen.getByTestId(`open-agent-detail-modal-btn-${agentId}`));
    expect(screen.getByTestId(`agent-detail-modal-${agentId}`)).toBeDefined();
    fireEvent.change(screen.getByTestId(`agent-test-input-${agentId}`), {
      target: { value: "Examine le contrat SaaS Acme" },
    });
    fireEvent.click(screen.getByTestId(`run-agent-btn-${agentId}`));
    expect(screen.getAllByTestId(`agent-execution-output-${agentId}`)[0]?.textContent).toContain(
      "Analyse Conformité Fournisseur",
    );
    // Wait for Test Bench execution API persistence so lifecycle promotes from DRAFT to ACTIVE before unmount
    await waitFor(() => {
      expect(screen.getByTestId(`agent-lifecycle-badge-${agentId}`).textContent).toContain("Actif");
    });
    fireEvent.click(screen.getByTestId(`close-agent-detail-modal-btn-${agentId}`));

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

    // Verify 3rd tab (🔌 Serveurs d'outils & MCP) is visible and interactive, without hidden display:none wrappers
    expect(screen.getByTestId("agents-subview-tab-connections").style.display).not.toBe("none");
    expect(screen.queryByTestId("catalog-explorer-panel-wrapper")).toBeNull();
    expect(screen.queryByTestId("remote-service-test-bench-wrapper")).toBeNull();
    fireEvent.click(screen.getByTestId("agents-subview-tab-connections"));
    expect(screen.getByTestId("connections-subview-panel")).toBeDefined();
    expect(screen.getByTestId("remote-service-test-bench")).toBeDefined();

    // 4. Load Business Pack Agents & Skills and verify 📦 Pack Métier badges + protection against deletion
    const { seedVitestActivePacks } = await import("./setup/installedPacksMockHandler");
    seedVitestActivePacks(["orcia-pack-sdlc"]);
    fireEvent.click(screen.getByTestId("agents-subview-tab-agents"));
    fireEvent.click(screen.getByTestId("load-pack-agents-templates-btn"));
    expect(
      await screen.findByTestId("agent-card-agent-architecte-solution"),
    ).toBeDefined();
    const packBadgeEl = screen.getByTestId(
      "agent-visibility-badge-agent-architecte-solution",
    );
    expect(packBadgeEl.querySelector("svg")).not.toBeNull();
    expect(packBadgeEl.textContent).toContain("Pack Métier (orcia-pack-sdlc)");
    expect(screen.queryByTestId("delete-agent-btn-agent-architecte-solution")).toBeNull();

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

  it("enforces RGAA Escape, Annuler, Unsaved Changes Guard, and Enter submit on First-Boot Admin Setup Modal", async () => {
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

    await waitFor(() => {
      expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
    });
    expect(screen.getByTestId("sidebar-open-my-account-btn").textContent).toContain(
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
    fireEvent.click(screen.getByTestId("settings-tab-models"));
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
    await waitFor(() => {
      expect(screen.getByTestId("llm-connection-test-result").getAttribute("data-ok")).toBe(
        "true",
      );
      expect(screen.getByTestId("llm-connection-test-result").textContent).toContain(
        "Connexion réussie au modèle « claude-3-7-sonnet » (Anthropic) sur https://api.anthropic.com/v1",
      );
    });

    // 4. Save the tier and verify human-readable French labels (no raw "medium", "balanced", "default", or "family-a")
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));
    await waitFor(() => {
      const rows = document.querySelectorAll('[data-testid^="llm-tier-row-"][data-tier="medium"]');
      expect(rows.length).toBeGreaterThan(0);
      const savedRow = rows[0]!;
      expect(savedRow.textContent).toContain("Standard");
      expect(savedRow.textContent).toContain("claude-3-7-sonnet");
      expect(savedRow.textContent).toContain("Anthropic · Équilibré");
      expect(savedRow.textContent).toContain("https://api.anthropic.com/v1");
      expect(savedRow.textContent).toContain("Clé d'API enregistrée");
      expect(savedRow.textContent).not.toContain("family-a");
    });

    // 5. Story 25.2 (Bug 5): floating ⓘ removed from AI Models main card; help-section-ai-models-overview remains in Zone 4
    expect(screen.queryByTestId("contextual-info-trigger-ai-models-overview")).toBeNull();
    if (!screen.queryByTestId("four-zone-contextual-help-column")) {
      fireEvent.click(screen.getByTestId("topbar-contextual-help-toggle"));
    }
    expect(screen.getByTestId("help-section-ai-models-overview")).toBeDefined();
  });

  it("presents the backend-known Business Packs catalog in /settings (Packs Métiers tab) without free-text SemVer or raw 'GLOBAL' input, and supports 1-click activation and deactivation across scopes", async () => {
    seedVitestPlatformSetupState(
      {},
      { email: "admin@orcia.fr", displayName: "Admin", roles: ["PLATFORM_ADMIN"] },
    );
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
    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    await screen.findByTestId("open-create-org-unit-modal-btn");
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Direction Produit" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    await screen.findByTestId("org-unit-row-org-1");

    // Return to /settings and switch to Packs Métiers tab
    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    await screen.findByTestId("settings-tab-packs");
    fireEvent.click(screen.getByTestId("settings-tab-packs"));
    expect(screen.getByTestId("settings-packs-section")).toBeDefined();

    // Free-text version input and redundant header pack selector / button are completely eliminated
    expect(screen.queryByTestId("pack-version-input")).toBeNull();
    expect(screen.queryByTestId("pack-key-input")).toBeNull();
    expect(screen.queryByTestId("save-pack-btn")).toBeNull();

    // Installed packs catalog cards are directly displayed with human-readable titles
    const sdlcCard = await screen.findByTestId("installed-pack-card-orcia-pack-sdlc");
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
    expect(screen.queryByTestId("pack-row-orcia-pack-sdlc")).toBeNull();
    expect(screen.getAllByTestId("pack-card-active-scopes-orcia-pack-sdlc").length).toBe(1);
    expect(screen.getByTestId("pack-card-active-scopes-orcia-pack-sdlc").textContent).toContain(
      "Direction · Direction Produit",
    );

    // 2. Switch scope to "Plateforme entière" (GLOBAL) and activate -> automatically deduplicates the sub-scope activation
    fireEvent.change(scopeSelect, { target: { value: "GLOBAL" } });
    fireEvent.click(screen.getByTestId("activate-pack-btn-orcia-pack-sdlc"));
    const scopesAfterGlobal = screen.getAllByTestId("pack-card-active-scopes-orcia-pack-sdlc");
    expect(scopesAfterGlobal.length).toBe(1);
    expect(scopesAfterGlobal[0]?.textContent).toContain("Plateforme entière");
    expect(scopesAfterGlobal[0]?.textContent).not.toContain("Direction · Direction Produit");

    // 1-click deactivation from the card button
    fireEvent.click(screen.getByTestId("deactivate-pack-btn-orcia-pack-sdlc"));
    expect(screen.getByTestId("packs-empty-state")).toBeDefined();

    // Story 25.2 (Bug 5): floating ⓘ removed from Packs main card; help-section-packs-overview remains in Zone 4
    expect(screen.queryByTestId("contextual-info-trigger-packs-overview")).toBeNull();
    if (!screen.queryByTestId("four-zone-contextual-help-column")) {
      fireEvent.click(screen.getByTestId("topbar-contextual-help-toggle"));
    }
    expect(screen.getByTestId("help-section-packs-overview")).toBeDefined();
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
      const isLoginView = filePath.endsWith("BiModeLoginLocalForm.tsx");

      if (isLoginView) {
        // /login MUST preserve password input mode, autoComplete="current-password", autoComplete="username", and data-allow-password-manager="true"
        expect(
          content.includes('type="password"') || content.includes('maskMode="password"'),
        ).toBe(true);
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

    fireEvent.click(screen.getByTestId("settings-tab-models"));
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

    await waitFor(() => {
      const rows = document.querySelectorAll('[data-testid^="llm-tier-row-"][data-tier="medium"]');
      expect(rows.length).toBeGreaterThan(0);
      const mediumRow = rows[0]!;
      expect(mediumRow.textContent).toContain("Fournisseur principal");
      expect(mediumRow.textContent).not.toContain("family-a");
    });
    unmount();

    // Runtime verification on /login (BiModeLoginView)
    simulateUnauthenticatedBrowser();
    seedVitestPlatformSetupState({}, { email: "admin@orcia.fr", displayName: "Admin ORCIA" });
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
    expect(screen.queryByTestId("login-local-accordion-toggle")).toBeNull();
    const loginEmailInput = await screen.findByTestId("login-local-email");
    const loginPasswordInput = await screen.findByTestId("login-local-password");
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
    fireEvent.change(screen.getByTestId("first-boot-admin-password-input"), {
      target: { value: "Secret123456!" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-password-confirm-input"), {
      target: { value: "Secret123456!" },
    });
    fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));
    await waitFor(() => {
      expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
    });

    // 2. Verify Journal d'Activité is removed from /settings tabs and primary sidebar, and accessible via FinOps / Notifications
    expect(screen.queryByTestId("settings-tab-audit")).toBeNull();
    expect(screen.queryByTestId("eight-menu-item-activity")).toBeNull();

    // 3. Perform actions on two different scopes: a BU ("Direction Produit") and Global Platform (activate/deactivate pack)
    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    await screen.findByTestId("open-create-org-unit-modal-btn");
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Direction Produit" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    await screen.findByTestId("org-unit-row-org-1");

    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    await screen.findByTestId("settings-tab-packs");
    fireEvent.click(screen.getByTestId("settings-tab-packs"));
    fireEvent.click(await screen.findByTestId("activate-pack-btn-orcia-pack-builder"));
    fireEvent.click(screen.getByTestId("deactivate-pack-btn-orcia-pack-builder"));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    // 4. Open Notifications drawer -> Journal d'Activité (/activity)
    fireEvent.click(screen.getByTestId("topbar-notifications-toggle"));
    fireEvent.click(screen.getByTestId("notifications-open-activity-log-btn"));
    await act(async () => {
      await Promise.resolve();
    });

    const activityPage = screen.getByTestId("activity-log-explorer-page");
    expect(activityPage).toBeDefined();
    expect(screen.getByTestId("topbar-breadcrumb").textContent).toContain("Journal d'Activité");
    expect((screen.getByTestId("eight-menu-item-finops") as HTMLButtonElement).disabled).toBe(true);

    // Wait for the async API ledger fetch to populate the table
    const latestEvtTimestamp = await screen.findByTestId("activity-event-timestamp-evt-4");
    const latestEvtActor = screen.getByTestId("activity-event-actor-evt-4");
    const latestEvtScope = screen.getByTestId("activity-event-scope-evt-4");
    expect(latestEvtTimestamp.textContent).toMatch(/\d{2}\/\d{2}\/\d{4}\s+\d{2}:\d{2}:\d{2}/);
    expect(latestEvtActor.textContent).toContain("Romain Admin (romain@orcia.fr)");
    expect(latestEvtScope.textContent).toContain("Plateforme entière");

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

    // 7. Verify default filtering at the connected login's observation level (topbar workspace/scope selector)
    expect(screen.getByTestId("activity-observation-scope-badge").textContent).toContain(
      "Filtré sur votre niveau d'observation : Plateforme entière",
    );
    expect(
      (screen.getByTestId("activity-scope-filter-select") as HTMLSelectElement).value,
    ).toBe("scope-global");

    // Switch the connected user's observation level in the top header bar (rail collapsed) to "Direction Produit" (org-1)
    fireEvent.click(screen.getByTestId("sidebar-rail-toggle-btn"));
    fireEvent.click(screen.getByTestId("topbar-fixed-workspace-selector"));
    fireEvent.click(screen.getByTestId("topbar-workspace-option-org-1"));
    fireEvent.click(screen.getByTestId("sidebar-rail-toggle-btn"));

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

    // 9. Story 25.2 (Bug 5): floating ⓘ removed from Activity Log card; Zone 4 audit-overview explains Activity Log without spending caps
    expect(screen.queryByTestId("contextual-info-trigger-audit-overview")).toBeNull();
    if (!screen.queryByTestId("four-zone-contextual-help-column")) {
      fireEvent.click(screen.getByTestId("topbar-contextual-help-toggle"));
    }
    const auditHelpSection = screen.getByTestId("help-section-audit-overview");
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

    // 1. On Day 0, the First-Boot Admin Submit button is disabled and exposes accessible sr-only reason + tooltip (without red '!' SVG inside primary blue button)
    const adminSubmitBtn = screen.getByTestId("first-boot-admin-submit-btn") as HTMLButtonElement;
    expect(adminSubmitBtn.disabled).toBe(true);
    const adminAlertIcon = screen.getByTestId(
      "disabled-button-alert-icon-first-boot-admin-submit-btn",
    );
    const adminAlertTooltip = screen.getByTestId(
      "disabled-button-alert-tooltip-first-boot-admin-submit-btn",
    );
    expect(adminAlertIcon.querySelector("svg")).toBeNull();
    expect(adminAlertIcon.className).toContain("sr-only");
    expect(adminAlertTooltip.getAttribute("role")).toBe("tooltip");
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
    await waitFor(() => {
      expect(
        screen
          .getByTestId("disabled-button-alert-tooltip-eight-menu-item-assistant")
          .getAttribute("data-tooltip-text"),
      ).toContain("Configurez au moins un modèle IA");
    });

    // 3. In Mon Organisation (/organization) & Configuration > Comptes & Habilitations:
    // - Organization page uses "Structure de l'Organisation (Directions / BU & Équipes)" and "Équipe" (never "Espace (Équipe)")
    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    const orgSection = await screen.findByTestId("settings-organization-section");
    expect(orgSection.textContent).toContain(
      "Structure de l'Organisation (Directions / BU & Équipes)",
    );
    expect(orgSection.textContent).not.toContain("Espace (Équipe)");
    await screen.findByTestId("open-create-org-unit-modal-btn");
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    expect(
      (screen.getByTestId("org-unit-level-select") as HTMLSelectElement).textContent,
    ).toContain("Équipe");
    expect(
      (screen.getByTestId("org-unit-level-select") as HTMLSelectElement).textContent,
    ).not.toContain("Espace");
    fireEvent.click(screen.getByTestId("cancel-create-org-unit-btn"));

    // - IAM tab SecOps drawer "+ Ajouter l'exception" button shows DisabledButtonAlertIndicator when no verb is selected
    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    await screen.findByTestId("settings-tab-iam");
    fireEvent.click(screen.getByTestId("settings-tab-iam"));
    fireEvent.click(screen.getByTestId("iam-secops-drawer-toggle"));
    fireEvent.click(screen.getByTestId("rbac-verb-checkbox-execute"));
    fireEvent.click(screen.getByTestId("rbac-verb-checkbox-read"));
    expect((screen.getByTestId("create-rbac-grant-btn") as HTMLButtonElement).disabled).toBe(
      true,
    );
    expect(
      screen.getByTestId("disabled-button-alert-icon-create-rbac-grant-btn"),
    ).toBeDefined();

    // Re-checking execute re-enables create-rbac-grant-btn (and auto-holds read)
    fireEvent.click(screen.getByTestId("rbac-verb-checkbox-execute"));
    expect((screen.getByTestId("create-rbac-grant-btn") as HTMLButtonElement).disabled).toBe(
      false,
    );
    expect(
      screen.queryByTestId("disabled-button-alert-icon-create-rbac-grant-btn"),
    ).toBeNull();

    // Create a BU ("Direction Tech") and a Team ("Équipe Plateforme") in Mon Organisation (/organization)
    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    await screen.findByTestId("open-create-org-unit-modal-btn");
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Direction Tech" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    await screen.findByTestId("org-unit-row-org-1");
    await screen.findByTestId("open-create-org-unit-modal-btn");
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-level-select"), {
      target: { value: "TEAM" },
    });
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Équipe Plateforme" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    expect((await screen.findByTestId("org-unit-row-org-2")).textContent).toContain("ÉQUIPE");
    expect(screen.getByTestId("org-unit-row-org-1").textContent).toContain(
      "1 Équipe rattachée",
    );

    // 4. Notification Center displays active counter badge, actionable setup prerequisites, and distinction vs Journal d'Activité
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
    fireEvent.click(screen.getByTestId("eight-menu-item-configuration"));
    await screen.findByTestId("settings-tab-models");
    fireEvent.click(screen.getByTestId("settings-tab-models"));
    fireEvent.change(screen.getByTestId("llm-primary-model-input"), {
      target: { value: "claude-3-7-sonnet" },
    });
    fireEvent.change(screen.getByTestId("llm-api-key-input"), {
      target: { value: "sk-ant-test" },
    });
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));

    await waitFor(() => {
      expect(assistantMenuBtn.disabled).toBe(false);
    });
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
    await waitFor(() => {
      expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
    });

    // Verify empty state in /organization before creating any team, and Notification Center alert
    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    expect(await screen.findByTestId("iam-org-units-empty-state")).toBeDefined();
    expect(screen.queryByTestId("admin-team-membership-summary-badge")).toBeNull();

    // Verify Notification Center includes the "setup-billing-team-missing" alert
    fireEvent.click(screen.getByTestId("topbar-notifications-toggle"));
    expect(
      screen.getByTestId("notification-center-item-setup-billing-team-missing").textContent,
    ).toContain("Aucune Équipe de facturation rattachée");
    fireEvent.click(screen.getByTestId("topbar-notifications-close"));

    // 2. Step B: Create a BU ("Direction Produit") and two Teams ("Équipe Core IA" & "Équipe Data") via Story 17.2 modals
    await screen.findByTestId("open-create-org-unit-modal-btn");
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Direction Produit" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    await screen.findByTestId("org-unit-row-org-1");

    await screen.findByTestId("open-create-org-unit-modal-btn");
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-level-select"), {
      target: { value: "TEAM" },
    });
    expect(screen.queryByTestId("org-unit-attach-admin-checkbox")).toBeNull();
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Équipe Core IA" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    await screen.findByTestId("org-unit-row-org-2");

    expect(screen.getByTestId("org-unit-billing-badge-org-2").textContent).toContain(
      "Facturation FinOps active",
    );

    // Create a second Team ("Équipe Data", org-3)
    await screen.findByTestId("open-create-org-unit-modal-btn");
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    fireEvent.change(screen.getByTestId("org-unit-level-select"), {
      target: { value: "TEAM" },
    });
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Équipe Data" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    await screen.findByTestId("org-unit-row-org-3");

    // Manage members of "Équipe Core IA" (org-2) via ManageOrgUnitMembersModal
    fireEvent.click(screen.getByTestId("manage-members-org-unit-btn-org-2"));
    fireEvent.change(screen.getByTestId("org-unit-add-member-input"), {
      target: { value: "romain@orcia.fr" },
    });
    fireEvent.click(screen.getByTestId("org-unit-add-member-btn"));
    fireEvent.click(screen.getByTestId("save-org-unit-members-btn"));
    await act(async () => {
      await Promise.resolve();
    });
    expect(screen.getByTestId("org-unit-members-count-org-2").textContent).toContain(
      "1 membre",
    );

    // 3. Navigate to /workspaces and create both a Collective Workspace (STANDARD) and a Private Workspace (PRIVATE_USER, Option 2 FinOps)
    fireEvent.click(screen.getByTestId("eight-menu-item-spaces"));
    await act(async () => {
      await Promise.resolve();
    });

    // Open "+ Nouvel espace" dialog and verify create-workspace-submit-btn has DisabledButtonAlertIndicator when name is empty
    fireEvent.click(screen.getByTestId("toggle-create-workspace-form-btn"));
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
    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Mon Bac à Sable R&D");
    });

    // Re-open modal and create a collective workspace ("Projet Socle IA", STANDARD) under "Équipe Core IA" (org-2)
    fireEvent.click(screen.getByTestId("toggle-create-workspace-form-btn"));
    fireEvent.change(screen.getByTestId("workspace-owner-team-select"), {
      target: { value: "org-2" },
    });
    fireEvent.change(screen.getByTestId("workspace-visibility-select"), {
      target: { value: "STANDARD" },
    });
    fireEvent.change(screen.getByTestId("workspace-name-input"), {
      target: { value: "Projet Socle IA" },
    });
    fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Projet Socle IA");
    });

    // 4. Open TopHeader Context Switcher and verify the 3 explicit groups without raw emojis
    fireEvent.click(screen.getByTestId("sidebar-rail-toggle-btn"));
    fireEvent.click(screen.getByTestId("topbar-fixed-workspace-selector"));
    const dropdownMenu = screen.getByTestId("topbar-workspace-dropdown-menu");
    expect(dropdownMenu.textContent).toContain("Mes Espaces Privés");
    expect(dropdownMenu.textContent).toContain("Mes Équipes & Espaces");
    expect(dropdownMenu.textContent).toContain("Supervision Organisation");
    expect(dropdownMenu.textContent).toContain("Équipe · Équipe Core IA");
    expect(dropdownMenu.textContent).toContain("Espace privé · Mon Bac à Sable R&D · Équipe Core IA");
    expect(dropdownMenu.textContent).toContain("Espace · Projet Socle IA · Équipe Core IA");

    // Select the Private Workspace (UUIDv7) in the TopHeader -> synchronizes /workspaces compact header
    const privateOption = screen
      .getAllByTestId(/^topbar-workspace-option-/)
      .find((el) => el.textContent?.includes("Mon Bac à Sable R&D"));
    expect(privateOption).toBeDefined();
    expect(privateOption?.getAttribute("data-testid")).not.toBe("topbar-workspace-option-ws-1");
    fireEvent.click(privateOption!);
    expect(screen.getByTestId("topbar-fixed-workspace-selector").textContent).toContain(
      "Mon Bac à Sable R&D",
    );
    fireEvent.click(screen.getByTestId("sidebar-rail-toggle-btn"));
    expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Mon Bac à Sable R&D");

    // 5. Verify orphan protection in /organization: cannot delete "Équipe Core IA" (org-2) while workspaces are attached to it
    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    await screen.findByTestId("delete-org-unit-btn-org-2");
    fireEvent.click(screen.getByTestId("delete-org-unit-btn-org-2"));
    expect((screen.getByTestId("confirm-delete-org-unit-btn-org-2") as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByTestId("org-unit-delete-blocked-banner").textContent).toContain(
      "2 Espaces de Travail rattachés",
    );
    expect(screen.getByTestId("org-unit-row-org-2")).toBeDefined();
    fireEvent.click(screen.getByTestId("cancel-delete-org-unit-btn-org-2"));
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

    // 1. Option A: Verify 📖 Vocabulaire is absent from the left sidebar (display: none purged)
    expect(screen.queryByTestId("eight-menu-item-vocabulary")).toBeNull();

    // 2. Initialize Day-0 Admin and a Billing Team ("Équipe Produit IA")
    fireEvent.change(screen.getByTestId("first-boot-admin-name-input"), {
      target: { value: "Romain Admin" },
    });
    fireEvent.change(screen.getByTestId("first-boot-admin-email-input"), {
      target: { value: "romain@orcia.fr" },
    });
    fireEvent.click(screen.getByTestId("first-boot-admin-submit-btn"));
    await waitFor(() => {
      expect(screen.queryByTestId("first-boot-admin-setup-modal")).toBeNull();
    });

    fireEvent.click(screen.getByTestId("eight-menu-item-organization"));
    await screen.findByTestId("open-create-org-unit-modal-btn");
    fireEvent.click(screen.getByTestId("open-create-org-unit-modal-btn"));
    const levelSelect = screen.getByTestId("org-unit-level-select") as HTMLSelectElement;
    fireEvent.change(levelSelect, { target: { value: "TEAM" } });
    fireEvent.change(screen.getByTestId("org-unit-name-input"), {
      target: { value: "Équipe Produit IA" },
    });
    fireEvent.click(screen.getByTestId("create-org-unit-btn"));
    await screen.findByTestId("org-unit-row-org-1");

    // Verify duplicate Glossary & Rules tab has been removed from /settings (now exclusively in /workspaces)
    expect(screen.queryByTestId("settings-tab-glossary")).toBeNull();

    // 3. Navigate to 🗂️ Mes Espaces (/workspaces)
    fireEvent.click(screen.getByTestId("eight-menu-item-spaces"));
    await act(async () => {
      await Promise.resolve();
    });

    // Legacy redundant panels with display: none have been purged
    expect(screen.queryByTestId("workspaces-legacy-technical-panels")).toBeNull();

    // Open modal and create a Private Workspace ("Mon Labo Perso", PRIVATE_USER) and a Team Workspace ("Espace Produit", STANDARD)
    fireEvent.click(screen.getByTestId("toggle-create-workspace-form-btn"));
    const visibilitySelect = screen.getByTestId(
      "workspace-visibility-select",
    ) as HTMLSelectElement;
    fireEvent.change(visibilitySelect, { target: { value: "PRIVATE_USER" } });
    fireEvent.change(screen.getByTestId("workspace-name-input"), {
      target: { value: "Mon Labo Perso" },
    });
    fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Mon Labo Perso");
    });

    // Modal closes on creation; re-open via "+ Nouvel espace" button and create a 2nd workspace
    const toggleCreateBtn = screen.getByTestId("toggle-create-workspace-form-btn");
    expect(toggleCreateBtn.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByTestId("workspace-name-input")).toBeNull();
    fireEvent.click(toggleCreateBtn);
    fireEvent.change(screen.getByTestId("workspace-visibility-select"), {
      target: { value: "STANDARD" },
    });
    fireEvent.change(screen.getByTestId("workspace-name-input"), {
      target: { value: "Espace Produit" },
    });
    fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Espace Produit");
    });

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

    // 4. Switch to Mon Labo Perso via Left Rail sidebar selector (no duplicate header switcher)
    expect(screen.queryByTestId("workspaces-active-switcher-select")).toBeNull();
    fireEvent.change(sidebarSwitcher, { target: { value: ws1Id } });
    await waitFor(() => {
      expect(screen.getByTestId("workspaces-active-title").textContent).toBe("Mon Labo Perso");
    });

    // 5. Dead Phase control removed; PRIVATE_USER visibility remains locked in Tab 5
    expect(screen.queryByTestId(`workspace-card-phase-select-${ws1Id}`)).toBeNull();
    expect(screen.queryByTestId(`share-private-workspace-btn-${ws1Id}`)).toBeNull();
    fireEvent.click(screen.getByTestId("workspace-tab-MEMBERS_TEAM"));
    expect(
      ((await screen.findByTestId(`workspace-card-visibility-select-${ws1Id}`)) as HTMLSelectElement)
        .disabled,
    ).toBe(true);
    expect(screen.getByTestId(`workspace-visibility-badge-${ws1Id}`).textContent).toContain(
      "Personnel",
    );

    // 6. Test Unified 5-Tab Workspace Container for active workspace ("Mon Labo Perso", UUIDv7)
    expect(screen.queryByTestId("workspace-detail-tabs-panel")).toBeNull();
    // Tab 2: Documents & Sources -> hide filter pills at 0 sources, then connect a source via modal and reveal pills
    fireEvent.click(screen.getByTestId("workspace-tab-DOCUMENTS_SOURCES"));
    expect(screen.getByTestId("workspace-sources-empty-state")).toBeDefined();
    expect(screen.queryByTestId("sources-filter-pill-all")).toBeNull();
    fireEvent.click(screen.getByTestId("open-attach-source-modal-btn"));
    expect(screen.getByTestId("workspace-source-attach-modal")).toBeDefined();
    await waitFor(() => {
      expect(
        (screen.getByTestId("modal-source-nature-select") as HTMLSelectElement).value,
      ).toBe("SOURCE_CODE");
    });

    fireEvent.change(screen.getByTestId("modal-source-alias-input"), {
      target: { value: "Wiki Produit Interne" },
    });
    fireEvent.change(screen.getByTestId("modal-source-uri-input"), {
      target: { value: "https://confluence.orcia.fr/spaces/PROD" },
    });
    fireEvent.click(screen.getByTestId("modal-source-save-btn"));
    await waitFor(() => {
      expect(screen.getAllByText("Wiki Produit Interne").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByTestId("sources-filter-pill-all")).toBeDefined();
    });

    // Tab 4: Glossaire & Règles Métiers (Ontologie) -> multi-level cascade + add term + 1-click upward promotion
    fireEvent.click(screen.getByTestId("workspace-tab-GLOSSARY_RULES"));
    const cascadeBar = screen.getByTestId("glossary-inheritance-cascade-bar");
    expect(cascadeBar.querySelectorAll("svg").length).toBeGreaterThanOrEqual(1);
    expect(cascadeBar.textContent).toContain("Entreprise (Global)");
    expect(cascadeBar.textContent).toContain("Direction (BU)");
    expect(cascadeBar.textContent).toContain("Équipe (Équipe Produit IA)");
    expect(cascadeBar.textContent).toContain("Cet Espace (Mon Labo Perso)");
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

    const conceptCard = await screen.findByTestId(
      `glossary-concept-card-4-workspace-${ws1Id}-marge-brute-r-currente`,
    );
    expect(conceptCard.textContent).toContain("Marge Brute Récurrente");
    expect(
      screen.getByTestId(`glossary-concept-level-badge-4-workspace-${ws1Id}-marge-brute-r-currente`)
        .textContent,
    ).toContain("Mon Labo Perso");

    // Propose step-up promotion (L4 -> L3 Team) -> shows "En attente de validation" badge
    fireEvent.click(
      screen.getByTestId(
        `promote-glossary-concept-btn-4-workspace-${ws1Id}-marge-brute-r-currente`,
      ),
    );
    await waitFor(() => {
      expect(
        screen.getByTestId(`promoted-glossary-badge-4-workspace-${ws1Id}-marge-brute-r-currente`)
          .textContent,
      ).toContain("En attente de validation");
    });

    // Tab 5: Membres & Équipe -> auto-save workspace instructions to PG18
    fireEvent.click(screen.getByTestId("workspace-tab-MEMBERS_TEAM"));
    fireEvent.change(screen.getByTestId("workspace-instructions-textarea"), {
      target: { value: "Toujours citer la source Wiki Produit Interne." },
    });
    await waitFor(() => {
      expect(screen.getByTestId("workspace-instructions-saved-badge").textContent).toContain(
        "Enregistré",
      );
    });

    // 7. F5 Reload Survival Gate: unmount() and re-render() -> verify shared visibility, attached source, and persisted glossary term survive F5
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

    expect(screen.getByTestId(`workspace-visibility-badge-${ws1Id}`).textContent).toContain(
      "Personnel",
    );
    fireEvent.click(screen.getByTestId("workspace-tab-DOCUMENTS_SOURCES"));
    await waitFor(() => {
      expect(screen.getByTestId("workspace-detail-source-row-ds-1").textContent).toContain(
        "Wiki Produit Interne",
      );
    });
    fireEvent.click(screen.getByTestId("workspace-tab-GLOSSARY_RULES"));
    await waitFor(() => {
      expect(
        screen.getByTestId(
          `glossary-concept-level-badge-4-workspace-${ws1Id}-marge-brute-r-currente`,
        ).textContent,
      ).toContain("Mon Labo Perso");
      expect(
        screen.getByTestId(
          `promoted-glossary-badge-4-workspace-${ws1Id}-marge-brute-r-currente`,
        ).textContent,
      ).toContain("En attente de validation");
    });
  });

  it("preserves the user question bubble, animated ThinkingDots spinner, and ongoing thinking counter when navigating away from Mon Assistant (/assistant) and returning while thinking is in progress", () => {
    (globalThis as Record<string, unknown>).__ORCIA_TEST_KEEP_STREAM_PENDING__ = true;

    const { unmount } = render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={mockPush}>
          <InboxFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    const promptInput = screen.getByTestId("assistant-three-speed-input") as HTMLInputElement;
    fireEvent.change(promptInput, {
      target: { value: "affiche une solution du jeu du déplacement du cavalier" },
    });
    fireEvent.click(screen.getByTestId("assistant-three-speed-send-btn"));

    // Verify question bubble and ThinkingDots spinner are active before navigating away
    expect(screen.getByTestId("assistant-user-question-bubble").textContent).toBe(
      "affiche une solution du jeu du déplacement du cavalier",
    );
    expect(screen.getByTestId("assistant-thinking-pulsing-dots")).toBeDefined();
    expect(
      screen.getByTestId("assistant-stop-square-icon").querySelector("svg"),
    ).not.toBeNull();

    // Simulate navigating to another ORCIA screen (unmount InboxFeaturePanel) and returning (remount)
    unmount();

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={mockPush}>
          <InboxFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    // Question bubble, ThinkingDots spinner, and in-progress thinking state are preserved!
    expect(screen.getByTestId("assistant-user-question-bubble").textContent).toBe(
      "affiche une solution du jeu du déplacement du cavalier",
    );
    const pulsingDots = screen.getByTestId("assistant-thinking-pulsing-dots");
    expect(pulsingDots.querySelectorAll(".orcia-thinking-dot").length).toBe(3);
    expect(
      screen.getByTestId("assistant-stop-square-icon").querySelector("svg"),
    ).not.toBeNull();
    expect(
      screen.getByTestId("assistant-thinking-subwindow-header-label").textContent,
    ).toContain("Réflexion en cours");
  });
});
