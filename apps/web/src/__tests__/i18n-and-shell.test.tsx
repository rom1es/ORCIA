import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, fireEvent, render, screen } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import { ModuleWorkspaceView } from "../components/ModuleWorkspaceView";
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

  it("starts 100% empty of sample data by default and displays the 0/5 Platform Onboarding Checklist", () => {
    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer onNavigate={mockPush}>
          <ModuleWorkspaceView moduleKey="cockpit" />
        </ShellContainer>
      </I18nProvider>,
    );

    // 0/5 onboarding progress at blank start
    expect(screen.getByTestId("onboarding-progress-badge").textContent).toBe("0/5");
    expect(screen.getByTestId("cockpit-no-workspace-empty-state")).toBeDefined();

    // Only scope-applicable entries are visible when no Workspace exists yet
    expect(screen.getByTestId("sidebar-nav-item-cockpit")).toBeDefined();
    expect(screen.getByTestId("sidebar-nav-item-catalog")).toBeDefined();
    expect(screen.getByTestId("sidebar-nav-item-admin")).toBeDefined();
    expect(screen.getByTestId("sidebar-nav-item-bootstrap")).toBeDefined();
    expect(screen.queryByTestId("sidebar-nav-item-inbox")).toBeNull();
    expect(screen.queryByTestId("sidebar-nav-item-ontology")).toBeNull();
    expect(screen.queryByTestId("sidebar-nav-item-gates")).toBeNull();
    expect(screen.queryByTestId("sidebar-nav-item-finops")).toBeNull();

    // Navigate to Catalog -> Empty state, zero sample items
    fireEvent.click(screen.getByTestId("sidebar-nav-item-catalog"));
    expect(screen.getByTestId("catalog-explorer-empty-state")).toBeDefined();
    expect(screen.getByTestId("catalog-setup-guidance-card")).toBeDefined();
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

    // Initially empty topology
    expect(screen.getByTestId("workspace-topology-empty-state")).toBeDefined();

    // Create a Workspace via the setup form
    fireEvent.change(screen.getByTestId("workspace-name-input"), {
      target: { value: "Mon Premier Espace" },
    });
    fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));

    // Workspace-scoped modules are now unlocked in the sidebar!
    expect(screen.getByTestId("sidebar-nav-item-inbox")).toBeDefined();
    expect(screen.getByTestId("sidebar-nav-item-ontology")).toBeDefined();
    expect(screen.getByTestId("sidebar-nav-item-gates")).toBeDefined();
    expect(screen.getByTestId("sidebar-nav-item-finops")).toBeDefined();

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
});
