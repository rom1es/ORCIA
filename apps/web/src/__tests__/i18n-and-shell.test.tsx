import { fireEvent, render, screen } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import React from "react";
import { describe, expect, it, vi } from "vitest";
import { ModuleWorkspaceView } from "../components/ModuleWorkspaceView";
import { resolveModuleFromPathname, ShellContainer } from "../components/ShellContainer";
import { I18nProvider } from "../i18n";
import { enDictionary } from "../i18n/locales/en";
import { frDictionary } from "../i18n/locales/fr";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/cockpit",
  useRouter: () => ({
    push: mockPush,
  }),
}));

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

describe("@orcia/web i18n dictionary parity, French default, and 7-module shell integration", () => {
  it("enforces 100% recursive key parity between fr.ts and en.ts", () => {
    const frKeys = collectNestedKeys(frDictionary as unknown as Record<string, unknown>);
    const enKeys = collectNestedKeys(enDictionary as unknown as Record<string, unknown>);
    expect(frKeys).toEqual(enKeys);
  });

  it("never uses raw hex colors inside apps/web/src", () => {
    const webSrcDir = path.resolve(__dirname, "..");
    const tsFiles = walkTsFiles(webSrcDir);
    const hexColorRegex = /#[0-9a-fA-F]{3,8}\b/;
    for (const filePath of tsFiles) {
      const content = fs.readFileSync(filePath, "utf-8");
      expect(
        hexColorRegex.test(content),
        `Found forbidden hex color in ${path.relative(webSrcDir, filePath)}`,
      ).toBe(false);
    }
  });

  it("resolves all 8 module routes accurately via resolveModuleFromPathname", () => {
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
  });

  it("starts empty of sample data by default (fixtureMode=false) and filters menu entries by scope", () => {
    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <ModuleWorkspaceView moduleKey="cockpit" />
        </ShellContainer>
      </I18nProvider>,
    );

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
    expect(screen.queryByTestId("uri-badge-res-blackbox-security-agent")).toBeNull();

    // Navigate to Admin -> Empty state, zero sample workspaces and no persona simulator bar
    fireEvent.click(screen.getByTestId("sidebar-nav-item-admin"));
    expect(screen.getByTestId("workspace-topology-empty-state")).toBeDefined();
    expect(screen.queryByTestId("persona-switch-marc")).toBeNull();
  });

  it("renders French by default, switches dynamically to English, navigates modules, and validates Story 1.2 & Story 1.3 Catalog Explorer with automated test dataset", () => {
    mockPush.mockClear();
    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer fixtureMode={true}>
          <ModuleWorkspaceView moduleKey="cockpit" />
        </ShellContainer>
      </I18nProvider>,
    );

    expect(screen.getByTestId("active-module-heading").textContent).toBe("Cockpit & Chat");
    expect(screen.getByTestId("sidebar-nav-item-inbox").textContent).toContain(
      "Boîte & Mes Runs",
    );

    const anchorCard = screen.getByTestId("human-anchor-card-architecture-intent");
    const anchorTextarea = anchorCard.querySelector("textarea") as HTMLTextAreaElement;
    expect(anchorTextarea.value).toBe(frDictionary.humanAnchor.defaultValue);

    // Toggle locale to English -> sidebar and untouched HumanLedAnchorCard default text update
    fireEvent.click(screen.getByTestId("locale-switcher-button"));
    expect(screen.getByTestId("sidebar-nav-item-inbox").textContent).toContain(
      "Inbox & My Runs",
    );
    expect(anchorTextarea.value).toBe(enDictionary.humanAnchor.defaultValue);

    // Story 1.3: Navigate to Catalog module -> Verify CatalogExplorerPanel (single theme in central panel)
    fireEvent.click(screen.getByTestId("sidebar-nav-item-catalog"));
    expect(mockPush).toHaveBeenCalledWith("/catalog");
    expect(screen.getByTestId("catalog-explorer-panel")).toBeDefined();
    expect(screen.getByTestId("uri-badge-res-blackbox-security-agent").getAttribute("data-uri-scheme")).toBe("git");
    expect(screen.getByTestId("uri-badge-res-nexus-bmad-architecture-pack").getAttribute("data-uri-scheme")).toBe("nexus");
    expect(screen.getByTestId("uri-badge-res-payment-delivery-workflow").getAttribute("data-uri-scheme")).toBe("db");
    expect(screen.getByTestId("run-lock-manifest-preview")).toBeDefined();

    fireEvent.click(screen.getByTestId("resolve-cas-btn-res-open-checkout-skill"));
    expect(
      screen.getByTestId("resolve-cas-result-res-open-checkout-skill").textContent,
    ).toContain("cas/4b72d9a1c30e");

    fireEvent.click(screen.getByTestId("bmad-import-trigger-btn"));
    expect(screen.getByTestId("bmad-import-result").textContent).toContain("BMAD_PACK");

    // Click module 4 (ontology) -> calls router.push and updates active module heading
    fireEvent.click(screen.getByTestId("sidebar-nav-item-ontology"));
    expect(mockPush).toHaveBeenCalledWith("/ontology");
    expect(screen.getByTestId("active-module-heading").textContent).toBe("Ontology & KB");

    // Open ScopeSwitcher (Ctrl+W) and select scope-global -> updates access mode badge to READ_ONLY_OBSERVER
    fireEvent.keyDown(window, { key: "w", ctrlKey: true });
    fireEvent.click(screen.getByTestId("scope-option-scope-global"));
    expect(screen.getByTestId("sidebar-access-mode-badge").textContent).toBe(
      enDictionary.shell.accessModes.READ_ONLY_OBSERVER,
    );

    // Navigate to Admin module -> Verify WorkspaceTopologyPanel and masked source inspection
    fireEvent.click(screen.getByTestId("sidebar-nav-item-admin"));
    expect(screen.getByTestId("workspace-topology-panel")).toBeDefined();
    fireEvent.click(screen.getByTestId("inspect-source-btn-res-blackbox-security-agent"));
    expect(
      screen.getByTestId("inspect-source-result-res-blackbox-security-agent").textContent,
    ).toContain("ERR_READ_SOURCE_DENIED");

    // Switch persona to Nadia (CONTRIBUTOR) -> Admin, Bootstrap, and FinOps entries are hidden in GlobalSidebar
    fireEvent.click(screen.getByTestId("persona-switch-nadia"));
    expect(screen.queryByTestId("sidebar-nav-item-admin")).toBeNull();
    expect(screen.queryByTestId("sidebar-nav-item-bootstrap")).toBeNull();
    expect(screen.queryByTestId("sidebar-nav-item-finops")).toBeNull();

    // Story 1.4: Navigate to Gates & Permissions -> collapse dock with ']', then trigger 403 Confluence -> dock auto-opens
    fireEvent.click(screen.getByTestId("sidebar-nav-item-gates"));
    fireEvent.keyDown(window, { key: "w", ctrlKey: true });
    fireEvent.click(screen.getByTestId("scope-option-scope-ws-orcia"));
    fireEvent.keyDown(window, { key: "]" });
    expect(screen.getByTestId("assistant-dock").getAttribute("data-collapsed")).toBe("true");

    fireEvent.click(screen.getByTestId("simulate-permission-denied-confluence-btn"));
    expect(screen.getByTestId("assistant-dock").getAttribute("data-collapsed")).toBe("false");
    expect(screen.getByTestId("permission-broker-required-role").textContent).toBe(
      "CONFLUENCE_PAY_ADR_READER",
    );

    fireEvent.click(screen.getByTestId("permission-broker-pause-btn"));
    expect(screen.getByTestId("permission-broker-card").getAttribute("data-ticket-status")).toBe(
      "PAUSED",
    );

    fireEvent.click(screen.getByTestId("permission-broker-replay-btn"));
    expect(screen.getByTestId("permission-broker-card").getAttribute("data-ticket-status")).toBe(
      "REPLAYED",
    );

    fireEvent.click(screen.getByTestId("simulate-confused-deputy-btn"));
    expect(screen.getByTestId("permission-broker-action-banner").textContent).toContain(
      "ERR_CONFUSED_DEPUTY_BLOCKED",
    );
  });

  it("renders Admin WorkspaceTopologyPanel and BootstrapOnboardingPanel as dedicated menu entries", () => {
    render(
      <I18nProvider initialLocale="en">
        <ShellContainer fixtureMode={true}>
          <ModuleWorkspaceView moduleKey="admin" />
        </ShellContainer>
      </I18nProvider>,
    );

    fireEvent.click(screen.getByTestId("sidebar-nav-item-admin"));
    expect(screen.getByTestId("workspace-topology-panel")).toBeDefined();

    // Switch persona to Claire (BU_DIRECTOR) -> WS 3 (CONFIDENTIAL_RESTRICTED) is excluded from roll-up
    fireEvent.click(screen.getByTestId("persona-switch-claire"));
    expect(screen.queryByTestId("workspace-card-ws-projet-confidentiel")).toBeNull();
    fireEvent.click(screen.getByTestId("mutation-guard-btn-ws-solution-paiement"));
    expect(screen.getByTestId("mutation-guard-result-ws-solution-paiement").textContent).toContain(
      "ERR_OBSERVER_MODE_READ_ONLY",
    );

    // Switch to Marc and select the dedicated Bootstrap entry in the left sidebar
    fireEvent.click(screen.getByTestId("persona-switch-marc"));
    fireEvent.click(screen.getByTestId("sidebar-nav-item-bootstrap"));
    expect(screen.getByTestId("bootstrap-onboarding-panel")).toBeDefined();
    expect(
      screen.getByTestId("human-led-anchor-card").getAttribute("data-human-authored-required"),
    ).toBe("true");
    fireEvent.click(screen.getByTestId("simulate-single-llm-family-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain(
      "ERR_MODEL_ORTHOGONALITY_VIOLATION",
    );
    fireEvent.click(screen.getByTestId("simulate-dual-llm-family-btn"));
    fireEvent.click(screen.getByTestId("execute-init-workspace-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain(
      "2 Solution Workspaces",
    );
    fireEvent.click(screen.getByTestId("execute-init-datasource-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain(
      "signed Human Anchor",
    );
    fireEvent.click(screen.getByTestId("execute-init-user-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain("AES-256-GCM");
  });
});
