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

  it("resolves all 7 module routes accurately via resolveModuleFromPathname", () => {
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
  });

  it("renders French by default, switches dynamically to English, navigates modules, and validates Story 1.2 & Story 1.3 Catalog Explorer", () => {
    mockPush.mockClear();
    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <ModuleWorkspaceView moduleKey="cockpit" />
        </ShellContainer>
      </I18nProvider>,
    );

    expect(screen.getByTestId("active-module-heading").textContent).toBe("Cockpit & Chat");
    expect(screen.getByTestId("sidebar-nav-item-inbox").textContent).toContain(
      "2. Boîte & Mes Runs",
    );

    const anchorCard = screen.getByTestId("human-anchor-card-architecture-intent");
    const anchorTextarea = anchorCard.querySelector("textarea") as HTMLTextAreaElement;
    expect(anchorTextarea.value).toBe(frDictionary.humanAnchor.defaultValue);

    // Toggle locale to English -> sidebar and untouched HumanLedAnchorCard default text update
    fireEvent.click(screen.getByTestId("locale-switcher-button"));
    expect(screen.getByTestId("sidebar-nav-item-inbox").textContent).toContain(
      "2. Inbox & My Runs",
    );
    expect(anchorTextarea.value).toBe(enDictionary.humanAnchor.defaultValue);

    // Story 1.3: Verify CatalogExplorerPanel, FederatedUriBadge (UX-DR8), CAS resolve, 4-layer overrides & BMAD import
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

    // Switch persona to Nadia (CONTRIBUTOR) -> Module 7 (Administration) is hidden in GlobalSidebar
    fireEvent.click(screen.getByTestId("persona-switch-nadia"));
    expect(screen.queryByTestId("sidebar-nav-item-admin")).toBeNull();

    // Switch persona to Claire (BU_DIRECTOR) -> Module 7 is visible, WS 3 (CONFIDENTIAL_RESTRICTED) is excluded from roll-up
    fireEvent.click(screen.getByTestId("persona-switch-claire"));
    expect(screen.getByTestId("sidebar-nav-item-admin")).toBeDefined();
    expect(screen.queryByTestId("workspace-card-ws-projet-confidentiel")).toBeNull();
    fireEvent.click(screen.getByTestId("mutation-guard-btn-ws-solution-paiement"));
    expect(screen.getByTestId("mutation-guard-result-ws-solution-paiement").textContent).toContain(
      "ERR_OBSERVER_MODE_READ_ONLY",
    );

    // Claire in Observer mode rejected when promoting DRAFT -> SHARED_WORKSPACE
    fireEvent.click(screen.getByTestId("promote-btn-res-jira-secops-playbook"));
    expect(
      screen.getByTestId("promote-result-res-jira-secops-playbook").textContent,
    ).toContain("ERR_OBSERVER_MODE_READ_ONLY");

    // Inspect black-box catalog resource -> shows ERR_READ_SOURCE_DENIED
    fireEvent.click(screen.getByTestId("inspect-source-btn-res-blackbox-security-agent"));
    expect(
      screen.getByTestId("inspect-source-result-res-blackbox-security-agent").textContent,
    ).toContain("ERR_READ_SOURCE_DENIED");

    // Story 1.4: Claire in Observer mode rejected when clicking Replay Step on PermissionBrokerCard
    fireEvent.click(screen.getByTestId("permission-broker-replay-btn"));
    expect(screen.getByTestId("permission-broker-action-banner").textContent).toContain(
      "ERR_OBSERVER_MODE_READ_ONLY",
    );

    // Switch back to Marc (TEAM_LEAD) + workspace scope -> collapse dock with ']', then trigger 403 Confluence -> dock auto-opens
    fireEvent.click(screen.getByTestId("persona-switch-marc"));
    fireEvent.keyDown(window, { key: "w", ctrlKey: true });
    fireEvent.click(screen.getByTestId("scope-option-scope-ws-orcia"));
    fireEvent.keyDown(window, { key: "]" });
    expect(screen.getByTestId("concierge-dock").getAttribute("data-collapsed")).toBe("true");

    fireEvent.click(screen.getByTestId("simulate-permission-denied-confluence-btn"));
    expect(screen.getByTestId("concierge-dock").getAttribute("data-collapsed")).toBe("false");
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

    // Story 1.5: Verify BootstrapOnboardingPanel, LLM orthogonality gate & Human-Led Anchor Card (#6D28D9)
    expect(screen.getByTestId("bootstrap-onboarding-panel")).toBeDefined();
    expect(screen.getByTestId("human-led-anchor-card").getAttribute("data-human-authored-required")).toBe("true");
    fireEvent.click(screen.getByTestId("simulate-single-llm-family-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain(
      "ERR_MODEL_ORTHOGONALITY_VIOLATION",
    );
    fireEvent.click(screen.getByTestId("simulate-dual-llm-family-btn"));
    fireEvent.click(screen.getByTestId("execute-init-workspace-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain("2 Solution Workspaces");
    fireEvent.click(screen.getByTestId("execute-init-datasource-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain("signed Human Anchor");
    fireEvent.click(screen.getByTestId("execute-init-user-btn"));
    expect(screen.getByTestId("bootstrap-feedback-banner").textContent).toContain("AES-256-GCM");
  });
});
